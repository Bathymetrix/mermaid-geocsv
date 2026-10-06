"""Parse self-describing GeoCSV datasets into typed pandas tables."""

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
_INTEGER = re.compile(r"[+-]?[0-9]+$")


def read(path: str | PathLike[str]) -> list[pd.DataFrame]:
    """Read UTF-8 GeoCSV datasets into one DataFrame per dataset.

    Requires ``dataset`` before the header. ``field_type`` and ``field_unit``
    are optional; undeclared field types are read as strings, and undeclared
    units remain empty. The delimiter defaults to comma. Source field names and
    data order are unchanged. Datetimes follow ISO 8601; timezone-free values remain naive,
    and explicit timezone offsets are preserved. Duplicate times are retained.
    ``nan`` (case-insensitive) becomes the native pandas missing value for
    every declared type. Other strings remain literal unless a per-column
    ``field_missing`` is declared.
    Comments and keyword declarations begin with a literal ``#`` at record
    boundaries. Quoted cells beginning with ``#`` are header or data values;
    lines inside multiline quoted cells remain cell content.

    Returns a list of DataFrames, one per dataset. Each frame is indexed by the
    file-wide, zero-based data-record position (``source_record_index``) and
    stores immutable GeoCSV metadata, including the resolved source path, at
    ``frame.attrs["geocsv"]``. The file is read once and all tables are loaded
    into memory. Raises ``GeoCSVError`` for malformed or unsupported content.
    """
    source = Path(path).resolve()
    with source.open(encoding="utf-8-sig", newline="") as stream:
        try:
            return _read_datasets(iter(enumerate(stream, start=1)), source)
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
    if declaration.value == "":
        values = [""]
    else:
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


def _read_datasets(
    lines: Iterator[tuple[int, str]], source_path: Path
) -> list[pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    comments: list[GeoCSVComment] = []
    declarations: dict[str, GeoCSVComment] = {}
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
                    # No source timestamps exist from which to infer a timezone.
                    array = pd.to_datetime(values, format="ISO8601", utc=True, errors="raise")
                else:
                    try:
                        array = pd.to_datetime(values, format="ISO8601", utc=False, errors="raise")
                    except (ValueError, OverflowError):
                        # Mixed zones cannot share pandas' native datetime dtype.
                        parsed_values = []
                        for value, line_number in zip(values, data_lines):
                            try:
                                parsed_values.append(
                                    pd.to_datetime(value, format="ISO8601", utc=False, errors="raise")
                                )
                            except (ValueError, OverflowError) as row_exc:
                                raise GeoCSVError(
                                    f"line {line_number}, field {name!r}: invalid datetime value {value!r}"
                                ) from row_exc
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
            field_missing=(
                dict(zip(header, field_missing)) if "field_missing" in declarations else {}
            ),
            delimiter=delimiter,
        )
        return frame

    def reset_dataset(dataset_comment: GeoCSVComment) -> None:
        nonlocal comments, declarations, header, columns, data_lines, delimiter
        comments = [dataset_comment]
        declarations = {"dataset": dataset_comment}
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
                continue

            previous = declarations.get(key)
            if previous is None:
                if header is not None:
                    raise GeoCSVError(
                        f"line {line_number}: #{key} requires a new #dataset boundary"
                    )
                declarations[key] = comment
            elif previous.value != comment.value:
                raise GeoCSVError(
                    f"line {line_number}: #{key} changed; a new #dataset boundary is required"
                )
            continue

        if header is None:
            if "dataset" not in declarations or not declarations["dataset"].value:
                raise GeoCSVError(f"line {line_number}: missing required #dataset declaration")
            if "delimiter" in declarations:
                delimiter = _decode_delimiter(declarations["delimiter"].value)
            header = _csv_record(line, lines, delimiter, line_number)
            if any(not name.strip() for name in header) or len(set(header)) != len(header):
                raise GeoCSVError(f"line {line_number}: header names must be nonempty and unique")
            field_types = (
                _field_values(declarations["field_type"], delimiter, len(header))
                if "field_type" in declarations else [""] * len(header)
            )
            field_units = (
                _field_values(declarations["field_unit"], delimiter, len(header))
                if "field_unit" in declarations else [""] * len(header)
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
    if value == "" or value.strip().lower() == "nan" or (missing and value == missing):
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
    return value
