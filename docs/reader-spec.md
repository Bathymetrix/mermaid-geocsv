# MERMAID GeoCSV reader

`geocsv.read(source, *, datetime_timezone=None)` parses only the controlled
[MERMAID GeoCSV schema 1.0.0](format-spec.md). That document defines the exact
header, field types and units, row matrix, finite numeric domains, CSV grammar,
six-digit UTC timestamps and acceptance/rejection cases. Generic GeoCSV dialects
and legacy MERMAID payloads are unsupported. There are no aliases or fallback.

## Input and output

Inputs are local paths, UTF-8 bytes, a `GeoCSVFetchResult`, or a list/tuple of
fetch results. Saved results are verified against their size and SHA-256 before
parsing. A bare path or bytes never inherits adjacent download provenance.

The return is always a list, with one DataFrame per file in input order. Every
file contains one instrument and one table with the fixed 16 columns. Column
labels retain exact source spellings. The `Time` column contains UTC timestamps;
`datetime_timezone` converts their display timezone without changing instants.
Timezone-free or alternate input spellings are rejected before conversion.

Every frame has a zero-based `RangeIndex` named `source_record_index`, excluding
comments and the column header. Original order and equal timestamps are retained;
reading never sorts, deduplicates or infers segment identity. Nullable pandas
`string`, `Float64` and `Int64` types represent the declared string, float and
integer fields; `Time` is a timezone-aware datetime column. It uses nanosecond storage when
representable, otherwise microsecond storage to preserve valid four-digit
Gregorian years without losing any of the six source fractional digits.

```python
from mermaid import geocsv

records, = geocsv.read("data/fixtures/schema-1.0.0/P0006/P0006.geocsv")
recordings = records.loc[records.MethodIdentifier.str.startswith("Derivation:Recording:")]
print(recordings[["Time", "SampleCount", "Elevation"]].head())
```

## Source preservation and missingness

Only a decoded empty CSV cell is missing, including a quoted empty cell.
Nonempty `nan`, `NA`, `NULL` and `NaT` remain literal string values; they are
invalid numeric/datetime input. Leading-zero identity codes remain strings.
Exactly two ASCII spaces in Recording Location are a present known blank code;
an empty Location is unknown and fails the Recording requirement. Other
whitespace-only cells are invalid. No values are trimmed, repaired, defaulted
or borrowed from other rows. Required missing and populated inapplicable fields
raise. `field_missing` is unsupported.

Finite signed Pressure-Absolute readings preserve sensor error. Recording
pressure and crossing proxies remain nonnegative. Elevation is required only
on Recording rows and must explicitly be zero metres; reading never supplies it.

## Immutable metadata and provenance

Each newly parsed frame has one immutable `GeoCSVMetadata` value at
`frame.attrs["geocsv"]`:

| Attribute | Source meaning |
| --- | --- |
| `schema_version` | Required literal supported schema revision, `1.0.0`. |
| `created` | Exact six-digit UTC `#created` spelling. |
| `source_path` | Resolved absolute opened path, or `None` for memory input. |
| `download` | Immutable fetch provenance when supplied; otherwise `None`. |
| `comments` | Ordered immutable `GeoCSVComment` values with raw text, physical line, case-sensitive key and declaration text. |
| `field_types`, `field_units` | Required exact schema declarations mapped by column name. |
| `field_long_names`, `field_standard_names` | Optional descriptive lists when supplied; empty mappings otherwise. |
| `delimiter` | Required comma delimiter. |
| `datetime_resolution_ns` | `Time` source indices mapped to 1000 ns, describing six-digit notation, not clock accuracy. |
| `record_line_numbers` | Source indices mapped to one-based physical starting lines, including multiline CSV records. |

Mappings, nested timestamp maps and comment tuples are immutable. pandas uses
experimental `attrs`: this guarantee applies to freshly parsed frames, not
arbitrary transformations or file exports. Keep provenance separately when
needed. The former public `field_missing` metadata attribute is removed with
legacy missing-marker support. Schema and literal creation identity are also
retained through association's attached metadata.

## Errors and references

`GeoCSVError` identifies malformed/unsupported content with the source path or
retrieval URL and, where applicable, the physical line and field. Invalid UTF-8,
missing/duplicate declarations, wrong columns, malformed CSV and invalid row
values raise. `GeoCSVFetchError` identifies changed saved downloads. OS errors
retain their normal meaning. Parsing preserves bytes on disk.

See [read tutorial](../tutorials/read.md), [fetch](fetch.md), [association](obspy-association.md),
and the complete [format specification](format-spec.md).
