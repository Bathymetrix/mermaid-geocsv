"""Parse one self-describing GeoCSV dataset into a typed pandas table."""

from __future__ import annotations

import csv
import re
from collections.abc import Iterator
from itertools import chain
from os import PathLike
from pathlib import Path

import pandas as pd

from .metadata import GeoCSVComment, GeoCSVMetadata


class GeoCSVError(ValueError):
    """A GeoCSV declaration, CSV record, or typed field is invalid/unsupported."""


_SCHEMA_KEYS = {"delimiter", "field_type", "field_unit", "field_missing"}
_FIELD_TYPES = {"string", "datetime", "float", "integer"}
_TIMEZONE = re.compile(r"[Tt ].*(?:Z|[+-][0-9]{2}:?[0-9]{2})$")
_INTEGER = re.compile(r"[+-]?[0-9]+$")


def read(path: str | PathLike[str]) -> pd.DataFrame:
    """Read a UTF-8 file containing one GeoCSV dataset.

    Requires ``dataset``, ``field_type``, and ``field_unit`` before the header.
    The delimiter defaults to comma. Source field names and data order are
    unchanged. Declared datetimes must include a timezone and are converted to
    UTC; duplicate times are retained. ``nan`` (case-insensitive) becomes the
    native pandas missing value for every declared type. Other strings remain
    literal unless a per-column ``field_missing`` is declared.
    Comments and keyword declarations begin with a literal ``#`` at record
    boundaries. Quoted cells beginning with ``#`` are header or data values;
    lines inside multiline quoted cells remain cell content.

    Returns a pandas DataFrame indexed by the file-wide, zero-based data-record
    position (``source_record_index``), with immutable GeoCSV metadata and the
    resolved source path at ``frame.attrs["geocsv"]``. The entire dataset is
    loaded into memory. Raises ``GeoCSVError`` for malformed or unsupported
    content; filesystem and decoding errors propagate normally.
    """
    source = Path(path).resolve()
    with source.open(encoding="utf-8-sig", newline="") as stream:
        try:
            return _read_dataset(iter(enumerate(stream, start=1)), source)
        except GeoCSVError as exc:
            raise GeoCSVError(f"{source}: {exc}") from exc


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
    # Do not classify those continuation lines as GeoCSV comments.
    reader = csv.reader(
        chain([line], (text for _, text in remaining)),
        delimiter=delimiter,
        strict=True,
    )
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
    try:
        values = next(csv.reader([declaration.value], delimiter=delimiter, strict=True))
    except csv.Error as exc:
        raise GeoCSVError(
            f"line {declaration.line_number}: invalid {declaration.key} CSV: {exc}"
        ) from exc
    if len(values) != width:
        raise GeoCSVError(
            f"line {declaration.line_number}: {declaration.key} has {len(values)} "
            f"fields; header has {width}"
        )
    return [value.strip() for value in values]


def _read_dataset(lines: Iterator[tuple[int, str]], source_path: Path) -> pd.DataFrame:
    comments: list[GeoCSVComment] = []
    declarations: dict[str, GeoCSVComment] = {}
    header: list[str] | None = None
    columns: dict[str, list] = {}
    data_lines: list[int] = []
    delimiter = ","

    for line_number, line in lines:
        if not line.strip():
            continue
        comment = _comment(line, line_number)
        if comment is not None:
            comments.append(comment)
            key = comment.key
            if key == "dataset" and key in declarations:
                raise GeoCSVError(f"line {line_number}: multiple datasets are not supported")
            if key in _SCHEMA_KEYS and (header is not None or key in declarations):
                raise GeoCSVError(
                    f"line {line_number}: repeated or late schema declaration {key!r}"
                )
            if key == "dataset" or key in _SCHEMA_KEYS:
                declarations[key] = comment
            continue

        if header is None:
            for key in ("dataset", "field_type", "field_unit"):
                if key not in declarations or not declarations[key].value:
                    raise GeoCSVError(f"line {line_number}: missing required #{key} declaration")
            if "delimiter" in declarations:
                delimiter = _decode_delimiter(declarations["delimiter"].value)
            header = _csv_record(line, lines, delimiter, line_number)
            if any(not name.strip() for name in header) or len(set(header)) != len(header):
                raise GeoCSVError(f"line {line_number}: header names must be nonempty and unique")
            field_types = _field_values(declarations["field_type"], delimiter, len(header))
            field_units = _field_values(declarations["field_unit"], delimiter, len(header))
            field_missing = (
                _field_values(declarations["field_missing"], delimiter, len(header))
                if "field_missing" in declarations else [""] * len(header)
            )
            for name, field_type in zip(header, field_types):
                if field_type.lower() not in _FIELD_TYPES:
                    raise GeoCSVError(f"field {name!r}: unsupported field type {field_type!r}")
            columns = {name: [] for name in header}
            continue

        row = _csv_record(line, lines, delimiter, line_number)
        if len(row) != len(header):
            raise GeoCSVError(
                f"line {line_number}: data row has {len(row)} fields; header has {len(header)}"
            )
        for name, value, field_type, missing in zip(header, row, field_types, field_missing):
            try:
                columns[name].append(_convert_value(value, field_type.lower(), missing))
            except (ValueError, OverflowError) as exc:
                raise GeoCSVError(
                    f"line {line_number}, field {name!r}: invalid {field_type} value {value!r}: {exc}"
                ) from exc
        data_lines.append(line_number)

    if header is None:
        raise GeoCSVError("no header found")

    typed_columns = {}
    for name, field_type in zip(header, field_types):
        values = columns.pop(name)
        if field_type.lower() == "datetime":
            try:
                array = pd.to_datetime(values, format="ISO8601", utc=True, errors="raise")
            except (ValueError, OverflowError) as exc:
                # Diagnose only on failure; normal datetime parsing is column-wise.
                for value, line_number in zip(values, data_lines):
                    try:
                        pd.to_datetime(value, format="ISO8601", utc=True, errors="raise")
                    except (ValueError, OverflowError) as row_exc:
                        raise GeoCSVError(
                            f"line {line_number}, field {name!r}: invalid datetime value {value!r}"
                        ) from row_exc
                raise GeoCSVError(f"field {name!r}: invalid datetime column") from exc
        else:
            dtype = {"string": "string", "integer": "Int64", "float": "Float64"}[field_type.lower()]
            array = pd.array(values, dtype=dtype)
        typed_columns[name] = array

    frame = pd.DataFrame(typed_columns)
    frame.index.name = "source_record_index"
    frame.attrs["geocsv"] = GeoCSVMetadata(
        source_path=source_path,
        comments=tuple(comments),
        field_types=dict(zip(header, field_types)),
        field_units=dict(zip(header, field_units)),
        field_missing=dict(zip(header, field_missing)) if "field_missing" in declarations else {},
        delimiter=delimiter,
    )
    return frame


def _convert_value(value: str, field_type: str, missing: str) -> object:
    if value.strip().lower() == "nan" or (missing and value == missing):
        return pd.NaT if field_type == "datetime" else pd.NA
    if field_type == "string":
        return value
    if field_type == "float":
        return float(value)
    if field_type == "integer":
        if not _INTEGER.fullmatch(value):
            raise ValueError("expected an integer or nan")
        integer = int(value)
        if not -(2**63) <= integer < 2**63:
            raise ValueError("outside the nullable Int64 range")
        return integer
    if not _TIMEZONE.search(value):
        raise ValueError("expected an ISO-8601 datetime with an explicit timezone")
    return value
