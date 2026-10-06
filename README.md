# mermaid-geocsv

`mermaid-geocsv` reads MERMAID GeoCSV files into typed pandas DataFrames.

Developed and maintained by [Bathymetrix®](https://bathymetrix.com).

GeoCSV is self-describing: it carries its field names, declared field types,
units, delimiter, and descriptive comments with the tabular data. This package
preserves that information while providing a standard Python analysis surface.

## Use

Install from the repository with Python 3.12 or newer:

```bash
python -m pip install .
```

```python
from mermaid import geocsv
import pandas as pd

tables = geocsv.read("P0006.geocsv")
records = tables[0]  # P0006 contains one dataset
```

For a hands-on introduction using the included P0006 file, see the
[pandas tutorial](TUTORIAL.md).

`geocsv.read` returns a list of typed DataFrames, one per dataset in file
order. Select a table from that list before using pandas. Each table's columns
use the exact field names from its GeoCSV header. The zero-based
`source_record_index` counts data records in file order, excluding headers and
comments; it is not a physical line number. Datetime values preserve their
source timezone: timezone-free values remain naive, and values with explicit
offsets retain those offsets. A column with one consistent timezone has a
pandas datetime dtype; if it mixes naive and timezone-aware values or different
offsets, its values are preserved as `Timestamp` objects in an `object` column.

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
values. Optional `field_missing` declarations are preserved as well.
`metadata.source_path` is the resolved absolute path opened by the reader;
it is reader provenance, not a GeoCSV header declaration.

As of writing, pandas documents [`DataFrame.attrs`](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.attrs.html)
as experimental. We use it
deliberately because GeoCSV is self-describing: its format metadata belongs
with its parsed table. Metadata, including the source path, is guaranteed on
the freshly parsed DataFrame, but may not survive arbitrary pandas
transformations or file exports. For example, concatenating DataFrames from
different files does not retain their differing `attrs`. If provenance must
survive a longer workflow, keep the input path separately.

## Scope

The reader loads UTF-8 GeoCSV datasets in one pass and returns one DataFrame
per dataset. It requires each `dataset` declaration's value to contain `GeoCSV`
(case-insensitively); versions and marker placement are not currently
validated. `field_type` and `field_unit` are optional, and the delimiter
defaults to comma. Comments may also appear between data records.
Header names must be nonempty and unique so source columns and their metadata
remain unambiguous. This is a restriction of this reader, not a v2.0.4
requirement. The reader preserves column spellings and does not assign
latitude/longitude roles from column names.
Comments and keyword declarations begin with a literal `#` at a record
boundary, with no preceding whitespace. Declaration syntax permits whitespace
after `#` and around `:`, as in `# field_type : string`. Raw comments and parsed
keyword/value pairs are retained in the GeoCSV metadata, including unknown
keywords; supported declarations also control parsing.
Every present `field_*` declaration must have exactly one entry per header
column. For `A,B`, `#field_type: ,` declares two empty type entries, while bare
`#field_type:` has only one and raises an error. The declaration may be omitted
entirely when no type is specified.

Quoted cells such as `"#Label"` and `"#dataset: hello"` are header or data values,
including in one-column datasets. A line starting with `#` inside a multiline
quoted cell remains part of that cell. Since 0.3.0, legacy preambles with entire
comments wrapped in CSV quotes are unsupported; those comments must be written
with literal leading `#`. Unquoted double quotes, whitespace immediately
outside quotation marks, and lines without LF or CRLF endings raise errors,
including a final line terminated only by EOF. Valid doubled quotes, embedded
delimiters, and quoted multiline cells remain supported. Blank lines before
the header are skipped. After the header, an empty record fails the row-width
check, and whitespace-only fields raise a field-conversion error.

Declared `string`, `float`, `integer`, and `datetime` fields become nullable
pandas `string`, `Float64`, `Int64`, and datetime columns, respectively. An
omitted or empty `field_type` entry is represented as a string column; its
`metadata.field_types` value remains empty to show that the source did not
declare the type. An omitted or empty `field_unit` entry remains empty in
`metadata.field_units`; the reader never invents a unit. Unknown nonempty type
names raise an error.
Empty CSV fields, including quoted empty fields, case-insensitive `nan`, and
nonempty per-column `field_missing` sentinels become `pd.NA` or `pd.NaT`
according to the declared type. This universal `nan` rule is a MERMAID policy,
not a requirement of GeoCSV v2.0.4; it applies even to string columns with a
different declared sentinel. A record must contain exactly as many cells as
the header; a blank line is not expanded into an all-missing record. A
nonempty whitespace-only cell is an error for every type. Leading and trailing
whitespace is trimmed from numeric and datetime cells before checking missing
markers and converting values. String cells retain their whitespace, so
`" nan "` remains literal text while `"nan"` is missing. Declared sentinels
match the resulting cell value exactly. Other strings, including `NA`, remain
literal.

Integers use pandas' nullable signed 64-bit dtype and must fall between
−2⁶³ and 2⁶³−1. Finite float values that overflow to infinity or underflow to
zero are rejected; an explicit infinity token is retained. Datetimes must use
ISO 8601 and at most nine fractional digits, pandas' nanosecond precision;
date-only forms become midnight without a timezone. Values that cannot be
represented within these limits raise errors rather than being silently
changed. Other finite decimal values have the usual binary floating-point
rounding of pandas `Float64`. Typed-field errors include the source path, line
number, and field name; CSV syntax errors include the path and line number.

Malformed records or declarations and invalid typed values raise
`geocsv.GeoCSVError` (a `ValueError`). The reader preserves row order and
duplicate timestamps. It does not derive scientific quantities, interpolate
locations, or choose between same-time records.
