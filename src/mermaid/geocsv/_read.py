"""Parse self-describing GeoCSV datasets into typed pandas tables."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone, tzinfo
import math
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from itertools import chain
from os import PathLike
from pathlib import Path
from types import MappingProxyType
from typing import TextIO

import pandas as pd

from ._fetch import GeoCSVDownload, GeoCSVFetchResult, _verify_file


@dataclass(frozen=True)
class GeoCSVComment:
    """Immutable comment preserved from a GeoCSV source line.

    Attributes
    ----------
    raw : str
        Original text without the line ending, retaining quotes and whitespace.
    line_number : int
        One-based physical line number in the source file.
    key : str or None
        Case-sensitive keyword, or None if no colon is present.
    value : str or None
        Text following the declaration prefix, or None if no colon is present.
    """

    raw: str
    line_number: int
    key: str | None
    value: str | None


@dataclass(frozen=True)
class GeoCSVMetadata:
    """Immutable dataset metadata stored at ``frame.attrs["geocsv"]``.

    Attributes
    ----------
    source_path : pathlib.Path or None
        Resolved absolute path opened by the reader, or None for memory input.
    comments : tuple of GeoCSVComment
        Source comments in order, including repeated and unknown keywords.
    field_types : mapping of str to str
        Required schema types by exact column name.
    field_units : mapping of str to str
        Required schema units by exact column name.
    field_long_names : mapping of str to str
        Declared long names by column name; empty values mean no description.
    field_standard_names : mapping of str to str
        Declared standard names by column name; empty values mean no description.
    schema_version : str
        Required MERMAID payload schema revision.
    created : str
        Literal six-digit UTC file-creation identity.
    delimiter : str
        Decoded, single-character CSV delimiter.
    datetime_resolution_ns : mapping of str to mapping of int to int
        Datetime column names mapped to source record indices and timestamp
        spelling resolutions in nanoseconds. Missing timestamps have no entry.
    download : GeoCSVDownload or None
        Retrieval provenance from a fetch result, or None for bare paths/bytes.
    record_line_numbers : mapping of int to int
        Source record indices mapped to one-based physical starting lines,
        including records spanning multiple lines.

    Notes
    -----
    All mappings are read-only, including nested timestamp-resolution mappings.
    Resolution describes source notation, not clock accuracy. Metadata is
    guaranteed on freshly parsed frames; pandas transformations may discard it.
    See the reader specification for metadata and format details:
    https://github.com/Bathymetrix/mermaid-geocsv/blob/main/docs/reader-spec.md
    """

    source_path: Path | None
    comments: tuple[GeoCSVComment, ...]
    field_types: Mapping[str, str]
    field_units: Mapping[str, str]
    field_long_names: Mapping[str, str]
    field_standard_names: Mapping[str, str]
    schema_version: str
    created: str
    delimiter: str
    datetime_resolution_ns: Mapping[str, Mapping[int, int]] = field(default_factory=dict)
    download: GeoCSVDownload | None = None
    record_line_numbers: Mapping[int, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Freeze comments and metadata mappings, including nested resolutions."""
        object.__setattr__(self, "comments", tuple(self.comments))
        for name in (
            "field_types",
            "field_units",
            "field_long_names",
            "field_standard_names",
            "record_line_numbers",
        ):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))
        object.__setattr__(self, "datetime_resolution_ns", MappingProxyType({
            name: MappingProxyType(dict(resolutions))
            for name, resolutions in self.datetime_resolution_ns.items()
        }))

    def __deepcopy__(self, memo: dict) -> GeoCSVMetadata:
        """Return this immutable value when frame metadata is deep-copied."""
        # pandas copies attrs during normal selection. This value is immutable,
        # so sharing it is safe and avoids copying read-only mapping proxies.
        return self


class GeoCSVError(ValueError):
    """Error raised for invalid or unsupported GeoCSV content."""


_SCHEMA = "1.0.0"
_SCHEMA_LINE = f"# MERMAID GeoCSV schema: {_SCHEMA}"
_COLUMNS = (
    "MethodIdentifier", "Time", "Network", "Station", "Location", "Channel",
    "DataQuality", "Latitude", "Longitude", "Elevation", "WaterPressure",
    "InstrumentDescription", "SampleRate", "SampleCount", "ClockOffset",
    "TimeCorrectionApplied",
)
_TYPES = ("string", "datetime", "string", "string", "string", "string", "string",
          "float", "float", "float", "float", "string", "float", "integer", "float", "float")
_UNITS = ("unitless", "iso8601", "unitless", "unitless", "unitless", "unitless", "unitless",
          "degrees_north", "degrees_east", "meters", "mbar", "unitless", "hertz", "unitless",
          "seconds", "seconds")
_REQUIRED_HEADERS = {"dataset", "created", "delimiter", "lineterminator", "field_type", "field_unit"}
_FIELD_HEADERS = {"field_type", "field_unit", "field_long_name", "field_standard_name"}
_INTEGER = re.compile(r"[+-]?[0-9]+\Z")
_FLOAT = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
_UTC = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z\Z")
_METHODS = {
    ("Measurement", "Position"), ("Measurement", "Pressure-Absolute"),
    ("Derivation", "Recording"), ("Interpolation", "Crossing-Descent"),
    ("Interpolation", "Crossing-Ascent"),
}


def read(
    source: str | PathLike[str] | bytes | GeoCSVFetchResult | list[GeoCSVFetchResult]
    | tuple[GeoCSVFetchResult, ...],
    *, datetime_timezone: str | tzinfo | None = None,
) -> list[pd.DataFrame]:
    """Read controlled MERMAID GeoCSV schema 1.0.0 into typed tables.

    Parameters
    ----------
    source : str, path-like, bytes, GeoCSVFetchResult, list, or tuple
        Local path, UTF-8 bytes, or results returned by ``fetch``. Fetch results
        retain retrieval provenance; saved files are checked against their byte
        count and checksum before parsing. Bare paths and bytes do not infer
        retrieval provenance from adjacent files. Lists and tuples may contain
        only fetch results.
    datetime_timezone : str or datetime.tzinfo, optional
        Target display timezone accepted by pandas. Default None retains UTC.
        Input timestamps always require the schema's six-digit UTC spelling.

    Returns
    -------
    frames : list of pandas.DataFrame
        One typed table per file, in source order. Batches are flattened in
        result order. Each file has a zero-based ``source_record_index``. Original column names and duplicate
        timestamps are retained. Immutable ``GeoCSVMetadata`` is stored at
        ``frame.attrs["geocsv"]`` on each freshly parsed frame.

    Raises
    ------
    GeoCSVError
        Content is malformed or unsupported, or timezone conversion is requested
        for a non-missing timezone-naive datetime.
    GeoCSVFetchError
        A saved fetch result no longer matches its recorded size or checksum.
    TypeError
        The source type is unsupported, or a batch contains non-fetch results.
    OSError
        A local input file cannot be opened or read.

    See Also
    --------
    fetch : Retrieve verified GeoCSV files to disk or memory.
    associate : Attach parsed station metadata to ObsPy waveforms.

    Notes
    -----
    All datasets are loaded into memory. Supported syntax, missing values,
    datetime handling, and metadata guarantees are defined in the specification:
    https://github.com/Bathymetrix/mermaid-geocsv/blob/main/docs/reader-spec.md
    """
    if isinstance(source, (list, tuple)):
        if any(not isinstance(item, GeoCSVFetchResult) for item in source):
            raise TypeError("batch input must contain GeoCSVFetchResult values")
        return [frame for item in source
                for frame in read(item, datetime_timezone=datetime_timezone)]
    download = None
    if isinstance(source, GeoCSVFetchResult):
        download = source.provenance
        if source.path is not None:
            _verify_file(source.path, download)
            source = source.path
        else:
            source = source.content
    source_path = None
    if isinstance(source, bytes):
        stream = io.TextIOWrapper(io.BytesIO(source), encoding="utf-8", newline="")
    else:
        source_path = Path(source).resolve()
        stream = source_path.open(encoding="utf-8", newline="")
    label = source_path or (download.url if download is not None else "<memory>")
    with stream:
        try:
            return _read_datasets(_source_lines(stream), source_path, datetime_timezone, download)
        except GeoCSVError as exc:
            raise GeoCSVError(f"{label}: {exc}") from exc
        except UnicodeDecodeError as exc:
            raise GeoCSVError(f"{label}: invalid UTF-8 input: {exc}") from exc


def _source_lines(stream: TextIO) -> Iterator[tuple[int, str]]:
    for line_number, line in enumerate(stream, start=1):
        if line.count("\r") != int(line.endswith("\r\n")):
            raise GeoCSVError(f"line {line_number}: lone CR line ending is not supported")
        if not line.endswith("\n"):
            raise GeoCSVError(f"line {line_number}: line must end with LF or CRLF")
        yield line_number, line


def _comment(line: str, line_number: int) -> GeoCSVComment:
    raw = line.rstrip("\r\n")
    key, separator, value = raw[1:].partition(":")
    return GeoCSVComment(raw, line_number, key if separator else None,
                         value[1:] if value.startswith(" ") else value if separator else None)


def _csv_record(
    line: str, remaining: Iterator[tuple[int, str]], delimiter: str, line_number: int
) -> list[str]:
    # csv consumes continuation lines only when a quoted cell spans newlines.
    # Validate their quoting without classifying them as GeoCSV comments.
    state = "start"

    def checked_lines() -> Iterator[str]:
        nonlocal state
        for physical_line, text in chain([(line_number, line)], remaining):
            for character in text.rstrip("\r\n"):
                if state == "quoted":
                    if character == '"':
                        state = "after_quote"
                elif character == delimiter:
                    state = "start"
                elif character == '"':
                    if state == "start":
                        state = "quoted"
                    elif state == "after_quote":
                        state = "quoted"
                    else:
                        raise GeoCSVError(
                            f"line {physical_line}: quote in an unquoted CSV field"
                        )
                elif state == "after_quote":
                    raise GeoCSVError(
                        f"line {physical_line}: content after a closing CSV quote"
                    )
                elif state == "start":
                    state = "unquoted"
            yield text

    reader = csv.reader(checked_lines(), delimiter=delimiter, strict=True)
    try:
        return next(reader)
    except csv.Error as exc:
        raise GeoCSVError(f"line {line_number}: invalid CSV: {exc}") from exc


def _timestamp(value: str) -> pd.Timestamp:
    if not _UTC.fullmatch(value):
        raise ValueError("requires YYYY-MM-DDTHH:MM:SS.ffffffZ")
    parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
    return pd.Timestamp(parsed.replace(tzinfo=timezone.utc))


def _convert_value(value: str, field_type: str, field_name: str) -> object:
    if value == "":
        return pd.NaT if field_type == "datetime" else pd.NA
    if not value.strip() and not (field_name == "Location" and value == "  "):
        raise ValueError("whitespace-only values are invalid")
    if field_type == "string":
        return value
    if field_type == "datetime":
        return _timestamp(value)
    if field_type == "float":
        if not _FLOAT.fullmatch(value):
            raise ValueError("expected a finite decimal number")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("value overflows finite Float64")
        if number == 0 and Decimal(value) != 0:
            raise ValueError("nonzero value underflows to zero in Float64")
        return number
    if not _INTEGER.fullmatch(value):
        raise ValueError("expected a base-ten integer")
    number = int(value)
    if not -(2**63) <= number < 2**63:
        raise ValueError("outside the nullable Int64 range")
    return number


def _validate_row(row: Mapping, line_number: int) -> None:
    """Check the selected row matrix without repairing source values."""
    def require(fields):
        for name in fields:
            if pd.isna(row[name]):
                raise GeoCSVError(f"line {line_number}: missing required {name}")

    require(("MethodIdentifier", "Time", "Network", "Station", "InstrumentDescription"))
    parts = row["MethodIdentifier"].split(":")
    if (len(parts) != 3 or tuple(parts[:2]) not in _METHODS or not parts[2]
            or any(character.isspace() for character in parts[2])):
        raise GeoCSVError(f"line {line_number}: unsupported MethodIdentifier {row['MethodIdentifier']!r}")
    subject = parts[1]
    if parts[0] != "Measurement" and (not parts[2].startswith("automaid-") or not parts[2][9:]):
        raise GeoCSVError(f"line {line_number}: derivation/interpolation requires an automaid version")
    model = row["InstrumentDescription"]
    if not model.startswith("MERMAID_") or not model[8:].strip():
        raise GeoCSVError(f"line {line_number}: InstrumentDescription requires MERMAID_<model>")
    applicable = {"MethodIdentifier", "Time", "Network", "Station", "InstrumentDescription"}
    if subject == "Position":
        require(("Latitude", "Longitude"))
        applicable.update(("Latitude", "Longitude", "ClockOffset"))
    elif subject == "Pressure-Absolute":
        require(("WaterPressure",))
        applicable.add("WaterPressure")
    elif subject == "Recording":
        require(("Location", "Channel", "DataQuality", "Latitude", "Longitude", "Elevation",
                 "SampleRate", "SampleCount", "TimeCorrectionApplied"))
        applicable.update(("Location", "Channel", "DataQuality", "Latitude", "Longitude", "Elevation",
                           "WaterPressure", "SampleRate", "SampleCount", "TimeCorrectionApplied"))
        if row["DataQuality"] not in {"Q", "D"}:
            raise GeoCSVError(f"line {line_number}: Recording DataQuality must be Q or D")
        if row["DataQuality"] == "Q":
            require(("WaterPressure",))
        if row["Elevation"] != 0:
            raise GeoCSVError(f"line {line_number}: Recording Elevation must be zero meters")
    else:
        require(("Latitude", "Longitude", "WaterPressure"))
        applicable.update(("Latitude", "Longitude", "WaterPressure"))
    for name in _COLUMNS:
        value = row[name]
        if name not in applicable and not pd.isna(value):
            raise GeoCSVError(f"line {line_number}: {name} is inapplicable to {subject}")
    for name, lower, upper in (("Latitude", -90, 90), ("Longitude", -180, 180)):
        if not pd.isna(row[name]) and not lower <= row[name] <= upper:
            raise GeoCSVError(f"line {line_number}: {name} outside [{lower}, {upper}]")
    for name in ("WaterPressure", "SampleRate", "SampleCount"):
        value = row[name]
        if not pd.isna(value) and ((value < 0 and not (name == "WaterPressure" and subject == "Pressure-Absolute"))
                                      or (name != "WaterPressure" and value == 0)):
            raise GeoCSVError(f"line {line_number}: {name} outside its permitted domain")


def _read_datasets(lines, source_path, datetime_timezone, download=None) -> list[pd.DataFrame]:
    first = next(lines, None)
    if first is None or first[1].rstrip("\r\n") != _SCHEMA_LINE:
        raise GeoCSVError(f"first line must be exactly {_SCHEMA_LINE!r}; missing or unsupported schema")
    comments = [GeoCSVComment(_SCHEMA_LINE, 1, "MERMAID GeoCSV schema", _SCHEMA)]
    declarations = {}
    columns = {name: [] for name in _COLUMNS}
    data_lines = []
    header_seen = False
    identities = {}
    for line_number, line in lines:
        if line.startswith("#"):
            if header_seen:
                raise GeoCSVError(f"line {line_number}: comments after the column header are invalid")
            comment = _comment(line, line_number)
            key = comment.key
            if key == " MERMAID GeoCSV schema":
                raise GeoCSVError(f"line {line_number}: duplicate schema declaration")
            if key and key.startswith("field_") and key not in _FIELD_HEADERS:
                raise GeoCSVError(f"line {line_number}: unsupported #{key} declaration")
            if key in _REQUIRED_HEADERS | _FIELD_HEADERS:
                if not comment.raw.startswith(f"#{key}: "):
                    raise GeoCSVError(f"line {line_number}: requires literal '#{key}: ' prefix")
                if key in declarations:
                    raise GeoCSVError(f"line {line_number}: duplicate #{key} declaration")
                declarations[key] = comment
            comments.append(comment)
            continue
        if not header_seen:
            missing = _REQUIRED_HEADERS - declarations.keys()
            if missing:
                raise GeoCSVError(f"line {line_number}: missing required declarations {sorted(missing)}")
            for key, expected in (("dataset", "GeoCSV"), ("delimiter", "','"),
                                  ("lineterminator", "'\\n'")):
                if declarations[key].value != expected:
                    raise GeoCSVError(f"line {declarations[key].line_number}: #{key} must be {expected!r}")
            try:
                _timestamp(declarations["created"].value)
            except (ValueError, OverflowError) as exc:
                raise GeoCSVError(f"invalid #created timestamp: {exc}") from exc
            for key in _FIELD_HEADERS & declarations.keys():
                declaration = declarations[key]
                values = _csv_record(declaration.value + "\n", iter(()), ",", declaration.line_number)
                if len(values) != 16:
                    raise GeoCSVError(f"line {declaration.line_number}: #{key} requires 16 entries")
                expected = {"field_type": _TYPES, "field_unit": _UNITS}.get(key)
                if expected is not None and tuple(values) != expected:
                    raise GeoCSVError(f"line {declaration.line_number}: #{key} differs from schema {_SCHEMA}")
                declarations[key] = values
            if tuple(_csv_record(line, lines, ",", line_number)) != _COLUMNS:
                raise GeoCSVError(f"line {line_number}: column header differs from schema {_SCHEMA}")
            header_seen = True
            continue
        cells = _csv_record(line, lines, ",", line_number)
        if len(cells) != 16:
            raise GeoCSVError(f"line {line_number}: data row has {len(cells)} fields; expected 16")
        row = {}
        for name, value, field_type in zip(_COLUMNS, cells, _TYPES):
            try:
                row[name] = _convert_value(value, field_type, name)
            except (ValueError, OverflowError) as exc:
                raise GeoCSVError(f"line {line_number}, field {name!r}: invalid {field_type} value {value!r}: {exc}") from exc
        _validate_row(row, line_number)
        for name in ("Network", "Station", "InstrumentDescription"):
            if name in identities and row[name] != identities[name]:
                raise GeoCSVError(f"line {line_number}: mixed {name} within one instrument file")
            identities[name] = row[name]
        for name in _COLUMNS:
            columns[name].append(row[name])
        data_lines.append(line_number)
    if not header_seen:
        raise GeoCSVError("no column header found")
    typed = {}
    for name, kind in zip(_COLUMNS, _TYPES):
        if kind == "datetime":
            try:
                array = pd.array(columns[name], dtype="datetime64[ns, UTC]")
            except pd.errors.OutOfBoundsDatetime:
                # Six-digit Gregorian epochs can exceed pandas' nanosecond range.
                # Microsecond storage preserves their complete source precision.
                array = pd.array(columns[name], dtype="datetime64[us, UTC]")
            if datetime_timezone is not None:
                array = array.tz_convert(datetime_timezone)
        else:
            array = pd.array(columns[name], dtype={"string": "string", "float": "Float64", "integer": "Int64"}[kind])
        typed[name] = array
    frame = pd.DataFrame(typed, index=pd.RangeIndex(len(data_lines), name="source_record_index"))
    frame.attrs["geocsv"] = GeoCSVMetadata(
        source_path=source_path, comments=tuple(comments), schema_version=_SCHEMA,
        created=declarations["created"].value, field_types=dict(zip(_COLUMNS, _TYPES)),
        field_units=dict(zip(_COLUMNS, _UNITS)),
        field_long_names=dict(zip(_COLUMNS, declarations["field_long_name"])) if "field_long_name" in declarations else {},
        field_standard_names=dict(zip(_COLUMNS, declarations["field_standard_name"])) if "field_standard_name" in declarations else {},
        delimiter=",", datetime_resolution_ns={"Time": {i: 1000 for i in frame.index}},
        download=download, record_line_numbers=dict(enumerate(data_lines)),
    )
    return [frame]
