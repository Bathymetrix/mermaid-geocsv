"""Immutable source metadata attached to a parsed GeoCSV frame."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType


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
    The mappings are read-only. ``delimiter`` is the decoded CSV character.
    """

    source_path: Path
    comments: tuple[GeoCSVComment, ...]
    field_types: Mapping[str, str]
    field_units: Mapping[str, str]
    field_missing: Mapping[str, str]
    delimiter: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "comments", tuple(self.comments))
        for name in ("field_types", "field_units", "field_missing"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))

    def __deepcopy__(self, memo: dict) -> GeoCSVMetadata:
        # pandas copies attrs during normal selection. This value is immutable,
        # so sharing it is safe and avoids copying read-only mapping proxies.
        return self
