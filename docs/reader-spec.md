# MERMAID GeoCSV reader specification

`mermaid-geocsv` reads MERMAID GeoCSV files into typed pandas DataFrames.

MERMAID-specific format details, including missing-value spellings such as
`nan`, are not yet formally codified. This document defines the package's
current supported conventions. Compatibility with arbitrary GeoCSV producers
or every container version is not guaranteed. Formal format clarification will
be incorporated through explicit documented changes, not silent reinterpretation
of existing scientific values.

GeoCSV is self-describing: it carries its field names, declared field types,
units, delimiter, and descriptive comments with the tabular data. This package
preserves that information while providing a standard Python analysis surface.

## Python API

```python
from mermaid import geocsv
import pandas as pd

tables = geocsv.read("P0006.geocsv")
records = tables[0]  # P0006 contains one dataset
```

For a hands-on introduction using the included P0006 file, see the
[pandas tutorial](../tutorials/read.md).
For retrieval into memory or local files, see [Fetching GeoCSV](../tutorials/fetch.md).
Association is documented in the [association tutorial](../tutorials/associate.md);
unresolved scope is recorded in [open questions](open-questions.md).

`geocsv.read(source, *, datetime_timezone=None)` accepts a local path, raw
UTF-8 bytes, one `GeoCSVFetchResult`, or a list/tuple of fetch results. It
returns a list of typed DataFrames, one per dataset in source order. A batch
returns a flat list in result order followed by dataset order; it does not
concatenate tables or impose a shared schema. Record indices restart for each
file and continue across datasets within that file. Saved fetch results are
reverified against their original checksum and byte count before parsing.
Passing a bare path or bytes does not infer retrieval provenance from adjacent
manifests. Select a table from the list before using pandas. Each table's columns
use the exact field names from its GeoCSV header. The zero-based
`source_record_index` counts data records in file order, excluding headers and
comments; it is not a physical line number. Datetime values preserve their
source timezone by default: timezone-free values remain naive, and values with
explicit offsets retain those offsets. A column with one consistent timezone
has a pandas datetime dtype; if it mixes naive and timezone-aware values or
different offsets, its values are preserved as `Timestamp` objects in an
`object` column. Depending on pandas version, parsing mixed timezone entries
may issue a warning. If pandas rejects a mixed-timezone array, the reader
parses its entries individually and retains them in an object column; it does
not normalize them by default.

Pass `datetime_timezone` to convert datetime values to a common timezone:

```python
tables = geocsv.read("P0006.geocsv", datetime_timezone="UTC")
```

The value may be any timezone accepted by pandas' `DatetimeIndex.tz_convert`,
such as `"UTC"` or `"America/Los_Angeles"`. This conversion is performed by
pandas. When requested, each non-missing source datetime must include an
explicit timezone; naive values raise `GeoCSVError` rather than being assumed
to be UTC. Missing values remain missing.
If a declared datetime column has no non-missing source timestamps, it has a
timezone-naive datetime dtype even when `datetime_timezone` is requested:
there is no timestamp to convert. This includes header-only datasets.

```python
# Select position-bearing records for a trajectory map.
trajectory = records.loc[
    records["Latitude"].notna() & records["Longitude"].notna()
].sort_values("StartTime")

# Find every record at an exact timestamp. Timestamps need not be unique.
time = pd.Timestamp("2019-04-23T19:31:14Z")
matches = records.loc[
    records["StartTime"].eq(time),
    ["MethodIdentifier", "DataQuality", "Latitude"],
]
```

## GeoCSV metadata

GeoCSV metadata is available on the returned DataFrame:

```python
metadata = records.attrs["geocsv"]

metadata.field_types["SampleCount"]
metadata.field_units["Latitude"]
metadata.field_long_names["Latitude"]
metadata.field_standard_names["Latitude"]
metadata.comments
metadata.source_path
```

`metadata` is an immutable `GeoCSVMetadata` value. Its `comments` tuple retains
each comment's original text (`raw`), physical `line_number`, and parsed
`key`/`value`, including repeated and unknown keywords. Declaration mappings
use the exact source header names; `metadata.delimiter` is the decoded CSV
character. `field_long_names` and `field_standard_names` contain individually
trimmed values aligned with the source columns; absent attributes have empty
values. Optional `field_missing` declarations are preserved as well. If the
declaration is absent, `metadata.field_missing` is an empty mapping; if present,
it has one entry per column, and empty entries add no missing-value marker.
`metadata.source_path` is the resolved absolute path opened by the reader,
or None for in-memory input. `metadata.record_line_numbers` is a read-only
mapping from file-wide source record indices to one-based physical starting
line numbers. Comments, dataset boundaries and multiline CSV cells are counted
as physical lines, while the record index counts only data records. The mapping
also exists for bytes and fetched in-memory inputs. It is reader provenance,
not a GeoCSV header
declaration. `metadata.download` is None for bare paths and bytes, or the
immutable `GeoCSVDownload` provenance supplied by a fetch result. It retains
the instrument and release IDs, requested file and manifest URLs, verified byte
count and SHA-256, test-collection flag, and original manifest bytes. It does
not retain the GeoCSV payload. See the [fetch reference](fetch.md#provenance).

`metadata.datetime_resolution_ns` is a read-only nested mapping from datetime
column names to source record indices and source-spelling resolutions in
nanoseconds. Missing timestamps have no entry. Fractional digit counts include
trailing zeros; this records notation, not clock accuracy or pandas storage
resolution. Timestamp values are unchanged.

| Source timestamp spelling | Nominal resolution |
| --- | --- |
| Date only | One day |
| Hours and minutes | One minute |
| Seconds without a fraction | One second |
| Fractional seconds with `n` digits | `10 ** (9 - n)` nanoseconds |

As of writing, pandas documents [`DataFrame.attrs`](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.attrs.html)
as experimental. We use it
deliberately because GeoCSV is self-describing: its format metadata belongs
with its parsed table. Metadata, including local or download provenance, is guaranteed on
the freshly parsed DataFrame, but may not survive arbitrary pandas
transformations or file exports. For example, concatenating DataFrames from
different files does not retain their differing `attrs`. If provenance must
survive a longer workflow, keep the metadata or retrieval result separately.

## Supported GeoCSV semantics

### Dataset structure

The reader loads UTF-8 GeoCSV datasets in one pass and returns one DataFrame
per dataset. It requires each `dataset` declaration's value to contain `GeoCSV`
(case-insensitively); versions are not validated. The specification recommends
placing `#dataset` first, but the reader permits preceding comments for existing
MERMAID files. `field_type` and `field_unit` are optional, and
the delimiter defaults to comma. Comments may also appear between data records.
Header names must be nonempty and unique so source columns and their metadata
remain unambiguous. This is a restriction of this reader, not a v2.0.4
requirement. The reader preserves column spellings and does not assign
latitude/longitude roles from column names.

### Comments and metadata declarations

Comments and keyword declarations begin with a literal `#` at a record
boundary, with no preceding whitespace. Declaration syntax permits whitespace
after `#` and around `:`, as in `# field_type : string`. Raw comments and parsed
keyword/value pairs are retained in the GeoCSV metadata, including unknown
keywords; supported declarations also control parsing.
Apart from the `dataset` marker, the specification's known keywords are
treated as dataset-wide declarations: adding or changing one after the header
requires a new `#dataset` marker and header. For any unknown `#key: value`
line, the first occurrence may appear before or after the header. If the same
key repeats with a changed value after the header, the reader requires a new
`#dataset` marker and header. Identical repetitions are retained, as are
different values before the header; the last pre-header value is the baseline
for later comparisons. Free-text comments are not compared. This is a
provisional reader policy; the scope of custom keys remains an
[open format question](open-questions.md#1-do-custom-keyword-lines-define-dataset-wide-metadata).
Every present `field_*` declaration must have exactly one entry per header
column. For `A,B`, `#field_type: ,` declares two empty type entries, while bare
`#field_type:` has only one and raises an error. The declaration may be omitted
entirely when no type is specified.
For space- or tab-delimited metadata lists, outer whitespace around a
declaration is trimmed. Quote an empty first or last list entry with ASCII
double quotes (`""`) so it is not mistaken for padding; for example,
`#field_type:"" integer` with a space delimiter places an undeclared type in
the first column and `integer` in the second. With a tab delimiter, put an
actual tab between `""` and `integer`. Single quotes and backticks do not quote
metadata values.

### CSV quoting, whitespace, and line endings

Quoted cells such as `"#Label"` and `"#dataset: hello"` are header or data values,
including in one-column datasets. A line starting with `#` inside a multiline
quoted cell remains part of that cell. Legacy preambles with entire
comments wrapped in CSV quotes are unsupported; those comments must be written
with literal leading `#`. Unquoted double quotes, whitespace immediately
outside quotation marks, and lines without LF or CRLF endings raise errors,
including a final line terminated only by EOF. Valid doubled quotes, embedded
delimiters, and quoted multiline cells remain supported. Blank lines before
the header are skipped. After the header, an empty record fails the row-width
check, and whitespace-only fields raise a field-conversion error.

### Field types and missing values

Declared `string`, `float`, `integer`, and `datetime` fields become nullable
pandas `string`, `Float64`, `Int64`, and datetime columns, respectively. An
omitted or empty `field_type` entry is represented as a string column; its
`metadata.field_types` value remains empty to show that the source did not
declare the type. An omitted or empty `field_unit` entry remains empty in
`metadata.field_units`; the reader never invents a unit. Unknown nonempty type
names raise an error.
Empty CSV fields, including quoted empty fields, become typed missing values
except in a string-valued column named exactly `Location`. There, both `,,`
and `,"",` preserve the empty string `""`, representing a known empty SEED
location code. This also applies when `Location` has an undeclared type and
therefore defaults to string; numeric/datetime `Location` columns retain
their usual typed missingness. No other column gets this exception.
Case-insensitive `nan` and nonempty per-column `field_missing` sentinels become
`pd.NA` or `pd.NaT` according to the declared type, including in `Location`.
**`nan` is always missing, including in string
columns and when `field_missing` declares a different sentinel.** Literal
`nan` and quoted `"nan"` cannot be represented as string values; quoted empty
strings are missing outside string-valued `Location`. These missing-value and
empty-Location conventions are MERMAID policies, not requirements of GeoCSV
v2.0.4. The FDSN [SEED 2.4 mapping](https://docs.fdsn.org/projects/source-identifiers/en/latest/definition.html#mapping-of-seed-2-4-codes)
allows zero-character locations; it does not prescribe their CSV representation.
A record must contain exactly as many cells as
the header; a blank line is not expanded into an all-missing record. A
nonempty whitespace-only cell is an error for every type. Leading and trailing
whitespace is trimmed from numeric and datetime cells before checking missing
markers and converting values. String cells retain their whitespace, so
`" nan "` remains literal text while `"nan"` is missing. Declared sentinels
match the resulting cell value exactly. Other strings, including `NA`, remain
literal. In datetime columns, case-insensitive `NaT` is also a default missing
marker. In string columns, `NaT` remains literal text unless it matches an
explicit `field_missing` sentinel. Numeric columns reject it as an invalid
value unless it matches their declared sentinel.

### Numeric limits and datetime syntax

Integers use pandas' nullable signed 64-bit dtype and must fall between
−2⁶³ and 2⁶³−1. Finite float values that overflow to infinity or underflow to
zero are rejected; an explicit infinity token is retained. Datetime spellings
use an extended calendar date (`YYYY-MM-DD`), optionally followed by `HH:MM`,
optional seconds, a period fraction of one to nine digits, and an optional
timezone: `Z`, `±HH`, `±HHMM`, or `±HH:MM`. Other ISO 8601 forms, including
alternate date separators and unpadded components, are rejected rather than
normalized by pandas. `T` is strongly recommended between date and time; a
space is also accepted. Date-only forms become midnight without a timezone.
Datetime storage resolution depends on the pandas version and parsed values;
it does not establish measurement accuracy. Values that cannot be represented
within these limits raise errors rather than being silently
changed. Other finite decimal values have the usual binary floating-point
rounding of pandas `Float64`. Typed-field errors include the source path, line
number, and field name; CSV syntax errors include the path and line number.

### Errors and scientific scope

Malformed records or declarations, invalid UTF-8 input, and invalid typed
values raise `geocsv.GeoCSVError` (a `ValueError`). The reader preserves row
order and duplicate timestamps. It does not derive scientific quantities, interpolate
locations, or choose between same-time records.

The [open questions](open-questions.md) document format details that GeoCSV
v2.0.4 does not settle and the reader's current choices for those cases.
