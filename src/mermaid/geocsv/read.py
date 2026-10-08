"""Parse self-describing GeoCSV datasets into typed pandas tables."""

from __future__ import annotations

import csv
from datetime import tzinfo
import math
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from decimal import Decimal
from itertools import chain
from os import PathLike
from pathlib import Path
from types import MappingProxyType
from typing import TextIO

import pandas as pd


@dataclass(frozen=True)
class GeoCSVComment:
    """One source comment, with its physical line number and original text.

    ``raw`` excludes the line ending but retains quoting and whitespace.
    ``key`` is stripped and lowercased, and ``value`` is stripped. Both are
    ``None`` for free-text comments without a keyword/value pair.
    """

    raw: str
    line_number: int
    key: str | None
    value: str | None


@dataclass(frozen=True)
class GeoCSVMetadata:
    """Source provenance and GeoCSV declarations at ``frame.attrs["geocsv"]``.

    ``source_path`` is the resolved absolute path opened by the reader, not a
    declaration found in the file.

    Comments retain source order and repeated or unknown keys. Field mappings
    use the exact header names; values are the stripped source declarations.
    An empty ``field_types`` value means the type was undeclared and the reader
    represented that column as a string. Empty values in the other field
    mappings mean those attributes were undeclared or empty. The mappings are
    read-only. ``delimiter`` is the decoded CSV character.
    """

    source_path: Path
    comments: tuple[GeoCSVComment, ...]
    field_types: Mapping[str, str]
    field_units: Mapping[str, str]
    field_long_names: Mapping[str, str]
    field_standard_names: Mapping[str, str]
    field_missing: Mapping[str, str]
    delimiter: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "comments", tuple(self.comments))
        for name in (
            "field_types",
            "field_units",
            "field_long_names",
            "field_standard_names",
            "field_missing",
        ):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))

    def __deepcopy__(self, memo: dict) -> GeoCSVMetadata:
        # pandas copies attrs during normal selection. This value is immutable,
        # so sharing it is safe and avoids copying read-only mapping proxies.
        return self


class GeoCSVError(ValueError):
    """A GeoCSV declaration, CSV record, or typed field is invalid/unsupported."""


# Adding a keyword here may also require handling its parsing semantics below.
_KNOWN_KEYWORDS = {
    "dataset",
    "field_unit",
    "field_type",
    "field_long_name",
    "field_standard_name",
    "field_missing",
    "delimiter",
    "attribution",
    "standard_name_cv",
    "title",
    "history",
    "institution",
    "source",
    "comment",
    "references",
}
_FIELD_TYPES = {"string", "datetime", "float", "integer"}
_FIELD_ATTRIBUTE_KEYS = {key for key in _KNOWN_KEYWORDS if key.startswith("field_")}
_INTEGER = re.compile(r"[+-]?[0-9]+$")
# Supported datetime spelling: extended calendar date, optionally followed by
# time, fractional seconds, and an ISO timezone designator.
_ISO_DATETIME = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}"
    r"(?:[Tt ][0-9]{2}:[0-9]{2}"
    r"(?::[0-9]{2}(?:\.[0-9]{1,9})?)?"
    r"(?:[Zz]|[+-][0-9]{2}(?::?[0-9]{2})?)?)?\Z"
)
# Include nonpadded time components accepted by pandas so they cannot bypass
# the precision check. This does not define the supported datetime syntax.
_TIME_FRACTION = re.compile(r"[Tt ][0-9]+(?::[0-9]+){0,2}[.,]([0-9]+)")


def read(
    path: str | PathLike[str], *, datetime_timezone: str | tzinfo | None = None
) -> list[pd.DataFrame]:
    """Read UTF-8 GeoCSV datasets into one DataFrame per dataset.

    Requires ``dataset`` before the header. ``field_type`` and ``field_unit``
    are optional; undeclared field types are read as strings, and undeclared
    units remain empty. The delimiter defaults to comma. Source field names and
    data order are unchanged. Datetimes use extended calendar dates
    (``YYYY-MM-DD``), optionally with ``HH:MM``, seconds, a period fraction of
    at most nine digits, and ``Z`` or a numeric offset (``±HH``, ``±HHMM``, or
    ``±HH:MM``). ``T`` is strongly recommended between date and time, though a
    space is accepted. By default, explicit timezones are preserved
    and timezone-free values remain naive. Mixed timezone entries are retained
    as objects and may produce a pandas warning or become unsupported in a
    future pandas version. Set ``datetime_timezone`` to a timezone accepted by
    pandas' ``DatetimeIndex.tz_convert`` to convert aware values. When set,
    every non-missing datetime must include a timezone; naive values raise
    ``GeoCSVError``. Conversion is performed by pandas. Duplicate times are
    retained.
    ``nan`` (case-insensitive) becomes the native pandas missing value for
    every declared type. Numeric and datetime cells are trimmed; string cells
    retain their whitespace. A per-column ``field_missing`` sentinel also
    denotes missing data. In datetime columns, ``NaT`` (case-insensitive) also
    denotes missing data by default.
    Comments and keyword declarations begin with a literal ``#`` at record
    boundaries. Quoted cells beginning with ``#`` are header or data values;
    lines inside multiline quoted cells remain cell content.
    Malformed CSV quotes and lines without LF or CRLF endings are rejected.

    Returns a list of DataFrames, one per dataset. Each frame is indexed by the
    file-wide, zero-based data-record position (``source_record_index``) and
    stores immutable GeoCSV metadata, including the resolved source path, at
    ``frame.attrs["geocsv"]``. The file is read once and all tables are loaded
    into memory. Raises ``GeoCSVError`` for malformed or unsupported content.
    """
    source = Path(path).resolve()
    with source.open(encoding="utf-8-sig", newline="") as stream:
        try:
            return _read_datasets(_source_lines(stream), source, datetime_timezone)
        except GeoCSVError as exc:
            raise GeoCSVError(f"{source}: {exc}") from exc


def _source_lines(stream: TextIO) -> Iterator[tuple[int, str]]:
    for line_number, line in enumerate(stream, start=1):
        if line.count("\r") != int(line.endswith("\r\n")):
            raise GeoCSVError(f"line {line_number}: lone CR line ending is not supported")
        if not line.endswith("\n"):
            raise GeoCSVError(f"line {line_number}: line must end with LF or CRLF")
        yield line_number, line


def _comment(line: str, line_number: int) -> GeoCSVComment | None:
    raw = line.rstrip("\r\n")
    if not raw.startswith("#"):
        return None
    key, separator, value = raw[1:].partition(":")
    return GeoCSVComment(
        raw=raw,
        line_number=line_number,
        key=key.strip().lower() if separator else None,
        value=value.strip() if separator else None,
    )


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


def _decode_delimiter(value: str) -> str:
    # Accept both standard bare declarations and the writer's repr-style quotes.
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    value = {r"\s": " ", r"\t": "\t", r"\\": "\\"}.get(value, value)
    if len(value) != 1 or value in '\r\n"':
        raise GeoCSVError("delimiter must be a single character other than a quote or newline")
    return value


def _field_values(
    declaration: GeoCSVComment, delimiter: str, width: int
) -> list[str]:
    # _comment strips outer whitespace. With space or tab delimiters, quote an
    # empty edge entry as "" so its separator cannot be mistaken for padding.
    # Double quotes are the only quoting syntax in these metadata lists.
    values = []
    cell: list[str] = []
    state = "start"
    for character in declaration.value + delimiter:
        if character == delimiter and state != "quoted":
            values.append("".join(cell).strip())
            cell = []
            state = "start"
        elif state == "start":
            if character.isspace():
                continue
            if character == '"':
                state = "quoted"
            else:
                cell.append(character)
                state = "unquoted"
        elif state == "unquoted":
            if character == '"':
                raise GeoCSVError(
                    f"line {declaration.line_number}: invalid {declaration.key} quote"
                )
            cell.append(character)
        elif state == "quoted":
            if character == '"':
                state = "after_quote"
            else:
                cell.append(character)
        elif character == '"':
            cell.append('"')
            state = "quoted"
        elif not character.isspace():
            raise GeoCSVError(
                f"line {declaration.line_number}: invalid {declaration.key} quote"
            )
    if state == "quoted":
        raise GeoCSVError(
            f"line {declaration.line_number}: unterminated {declaration.key} quote"
        )
    if len(values) != width:
        raise GeoCSVError(
            f"line {declaration.line_number}: {declaration.key} has {len(values)} "
            f"fields; header has {width}"
        )
    return values


def _declaration_value(
    declaration: GeoCSVComment, delimiter: str, width: int
) -> str | tuple[str, ...]:
    if declaration.key in _FIELD_ATTRIBUTE_KEYS:
        return tuple(_field_values(declaration, delimiter, width))
    if declaration.key == "delimiter":
        return _decode_delimiter(declaration.value)
    return declaration.value


def _parse_datetime_value(value: str, line_number: int, field_name: str) -> pd.Timestamp:
    try:
        return pd.to_datetime(value, format="ISO8601", utc=False, errors="raise")
    except (ValueError, OverflowError) as exc:
        raise GeoCSVError(
            f"line {line_number}, field {field_name!r}: invalid datetime value {value!r}"
        ) from exc


def _read_datasets(
    lines: Iterator[tuple[int, str]],
    source_path: Path,
    datetime_timezone: str | tzinfo | None,
) -> list[pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    comments: list[GeoCSVComment] = []
    declarations: dict[str, GeoCSVComment] = {}
    repeated_declarations: list[GeoCSVComment] = []
    header: list[str] | None = None
    columns: dict[str, list] = {}
    data_lines: list[int] = []
    delimiter = ","
    source_record_start = 0
    saw_dataset = False

    def finish_dataset() -> pd.DataFrame:
        if header is None:
            raise GeoCSVError("dataset has no header")

        typed_columns = {}
        for name, field_type in zip(header, field_types):
            effective_type = field_type.lower() or "string"
            values = columns[name]
            if effective_type == "datetime":
                if not any(not pd.isna(value) for value in values):
                    # No source timestamp exists to establish or convert a timezone.
                    array = pd.to_datetime(values, format="ISO8601", errors="raise")
                elif datetime_timezone is not None:
                    parsed_values = []
                    for value, line_number in zip(values, data_lines):
                        if pd.isna(value):
                            parsed_values.append(pd.NaT)
                            continue
                        parsed = _parse_datetime_value(value, line_number, name)
                        if parsed.tzinfo is None:
                            raise GeoCSVError(
                                f"line {line_number}, field {name!r}: datetime_timezone requires "
                                "a timezone on every non-missing datetime value"
                            )
                        parsed_values.append(parsed)
                    array = pd.to_datetime(parsed_values, utc=True, errors="raise")
                    array = array.tz_convert(datetime_timezone)
                else:
                    try:
                        array = pd.to_datetime(values, format="ISO8601", utc=False, errors="raise")
                    except (ValueError, OverflowError):
                        # Mixed zones cannot share pandas' native datetime dtype.
                        parsed_values = []
                        for value, line_number in zip(values, data_lines):
                            if pd.isna(value):
                                parsed_values.append(pd.NaT)
                            else:
                                parsed_values.append(
                                    _parse_datetime_value(value, line_number, name)
                                )
                        array = pd.array(parsed_values, dtype=object)
            else:
                dtype = {"string": "string", "integer": "Int64", "float": "Float64"}[effective_type]
                array = pd.array(values, dtype=dtype)
            typed_columns[name] = array

        frame = pd.DataFrame(typed_columns)
        frame.index = pd.RangeIndex(
            source_record_start,
            source_record_start + len(frame),
            name="source_record_index",
        )
        frame.attrs["geocsv"] = GeoCSVMetadata(
            source_path=source_path,
            comments=tuple(comments),
            field_types=dict(zip(header, field_types)),
            field_units=dict(zip(header, field_units)),
            field_long_names=dict(zip(header, field_long_names)),
            field_standard_names=dict(zip(header, field_standard_names)),
            field_missing=(
                dict(zip(header, field_missing)) if "field_missing" in declarations else {}
            ),
            delimiter=delimiter,
        )
        return frame

    def reset_dataset(dataset_comment: GeoCSVComment) -> None:
        nonlocal comments, declarations, repeated_declarations
        nonlocal header, columns, data_lines, delimiter
        comments = [dataset_comment]
        declarations = {"dataset": dataset_comment}
        repeated_declarations = []
        header = None
        columns = {}
        data_lines = []
        delimiter = ","

    for line_number, line in lines:
        if header is None and not line.strip():
            continue

        comment = _comment(line, line_number)
        if comment is not None:
            key = comment.key
            if key == "dataset":
                if not comment.value or "geocsv" not in comment.value.casefold():
                    raise GeoCSVError(
                        f"line {line_number}: #dataset value must contain 'GeoCSV'"
                    )
                if saw_dataset:
                    if header is None:
                        raise GeoCSVError(f"line {line_number}: previous dataset has no header")
                    frames.append(finish_dataset())
                    source_record_start += len(frames[-1])
                    reset_dataset(comment)
                else:
                    saw_dataset = True
                    comments.append(comment)
                    declarations[key] = comment
                continue

            comments.append(comment)
            if key not in _KNOWN_KEYWORDS:
                if key:
                    previous = declarations.get(key)
                    if (
                        header is not None
                        and previous is not None
                        and previous.value != comment.value
                    ):
                        raise GeoCSVError(
                            f"line {line_number}: #{key} changed; "
                            "a new #dataset boundary is required"
                        )
                    declarations[key] = comment
                continue

            previous = declarations.get(key)
            if previous is None:
                if header is not None:
                    raise GeoCSVError(
                        f"line {line_number}: #{key} requires a new #dataset boundary"
                    )
                declarations[key] = comment
            elif header is None:
                repeated_declarations.append(comment)
            elif _declaration_value(previous, delimiter, len(header)) != _declaration_value(
                comment, delimiter, len(header)
            ):
                raise GeoCSVError(
                    f"line {line_number}: #{key} changed; a new #dataset boundary is required"
                )
            continue

        if header is None:
            if "dataset" not in declarations or not declarations["dataset"].value:
                raise GeoCSVError(f"line {line_number}: missing required #dataset declaration")
            if "delimiter" in declarations:
                delimiter = _decode_delimiter(declarations["delimiter"].value)
            for repeated in repeated_declarations:
                if repeated.key not in _FIELD_ATTRIBUTE_KEYS:
                    previous = declarations[repeated.key]
                    if _declaration_value(previous, delimiter, 0) != _declaration_value(
                        repeated, delimiter, 0
                    ):
                        raise GeoCSVError(
                            f"line {repeated.line_number}: #{repeated.key} changed; "
                            "a new #dataset boundary is required"
                        )
            header = _csv_record(line, lines, delimiter, line_number)
            if any(not name.strip() for name in header) or len(set(header)) != len(header):
                raise GeoCSVError(f"line {line_number}: header names must be nonempty and unique")
            for repeated in repeated_declarations:
                if repeated.key in _FIELD_ATTRIBUTE_KEYS:
                    previous = declarations[repeated.key]
                    if _declaration_value(previous, delimiter, len(header)) != _declaration_value(
                        repeated, delimiter, len(header)
                    ):
                        raise GeoCSVError(
                            f"line {repeated.line_number}: #{repeated.key} changed; "
                            "a new #dataset boundary is required"
                        )
            field_types = (
                _field_values(declarations["field_type"], delimiter, len(header))
                if "field_type" in declarations else [""] * len(header)
            )
            field_units = (
                _field_values(declarations["field_unit"], delimiter, len(header))
                if "field_unit" in declarations else [""] * len(header)
            )
            field_long_names = (
                _field_values(declarations["field_long_name"], delimiter, len(header))
                if "field_long_name" in declarations else [""] * len(header)
            )
            field_standard_names = (
                _field_values(declarations["field_standard_name"], delimiter, len(header))
                if "field_standard_name" in declarations else [""] * len(header)
            )
            field_missing = (
                _field_values(declarations["field_missing"], delimiter, len(header))
                if "field_missing" in declarations else [""] * len(header)
            )
            for name, field_type in zip(header, field_types):
                if field_type and field_type.lower() not in _FIELD_TYPES:
                    raise GeoCSVError(f"field {name!r}: unsupported field type {field_type!r}")
            columns = {name: [] for name in header}
            continue

        row = _csv_record(line, lines, delimiter, line_number)
        if len(row) != len(header):
            raise GeoCSVError(
                f"line {line_number}: data row has {len(row)} fields; header has {len(header)}"
            )
        for name, value, field_type, missing in zip(header, row, field_types, field_missing):
            effective_type = field_type.lower() or "string"
            try:
                columns[name].append(_convert_value(value, effective_type, missing))
            except (ValueError, OverflowError) as exc:
                raise GeoCSVError(
                    f"line {line_number}, field {name!r}: invalid {effective_type} "
                    f"value {value!r}: {exc}"
                ) from exc
        data_lines.append(line_number)

    if header is None:
        raise GeoCSVError("no header found")
    frames.append(finish_dataset())
    return frames


def _convert_value(value: str, field_type: str, missing: str) -> object:
    if value and not value.strip():
        raise ValueError(
            "whitespace-only values are not missing; use an empty field or nan"
        )
    if field_type != "string":
        value = value.strip()
    if value == "" or value.lower() == "nan" or (missing and value == missing):
        return pd.NaT if field_type == "datetime" else pd.NA
    if field_type == "datetime" and value.lower() == "nat":
        return pd.NaT
    if field_type == "string":
        return value
    if field_type == "float":
        number = float(value)
        if math.isnan(number):
            raise ValueError("use nan to denote missing data")
        if math.isinf(number) and value.lower() not in {
            "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"
        }:
            raise ValueError("finite value overflows Float64")
        if number == 0.0 and Decimal(value) != 0:
            raise ValueError("nonzero value underflows to zero in Float64")
        return number
    if field_type == "integer":
        if not _INTEGER.fullmatch(value):
            raise ValueError("expected an integer or nan")
        integer = int(value)
        if not -(2**63) <= integer < 2**63:
            raise ValueError("outside the nullable Int64 range")
        return integer
    match = _TIME_FRACTION.search(value)
    if match and len(match.group(1)) > 9:
        raise ValueError("datetime has more than nine fractional digits")
    if not _ISO_DATETIME.fullmatch(value):
        raise ValueError("expected a supported ISO 8601 datetime spelling")
    return value
