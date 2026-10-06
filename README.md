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

records = geocsv.read("P0006.geocsv")
```

For a hands-on introduction using the included P0006 file, see the
[pandas tutorial](TUTORIAL.md).

`records` is the only return value: a typed pandas `DataFrame`. Its columns use
the exact field names from the GeoCSV header. The zero-based
`source_record_index` counts data records in file order, excluding headers and
comments; it is not a physical line number. `StartTime` is a timezone-aware
UTC column.

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
metadata.comments
metadata.source_path
```

`metadata` is an immutable `GeoCSVMetadata` value. Its `comments` tuple retains
each comment's original text (`raw`), physical `line_number`, and parsed
`key`/`value`, including repeated and unknown keywords. Declaration mappings
use the exact source header names; `metadata.delimiter` is the decoded CSV
character. Optional `field_missing` declarations are preserved as well.
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

The reader loads one UTF-8 GeoCSV dataset into memory. It requires `dataset`,
`field_type`, and `field_unit` declarations before the header; the delimiter
defaults to comma. Comments may also appear between data records.
Comments and keyword declarations begin with a literal `#` at a record
boundary, with no preceding whitespace. Declaration syntax permits whitespace
after `#` and around `:`, as in `# field_type : string`. Raw comments and parsed
keyword/value pairs are retained in the GeoCSV metadata, including unknown
keywords; supported declarations also control parsing.

Quoted cells such as `"#Label"` and `"#dataset: hello"` are header or data values,
including in one-column datasets. A line starting with `#` inside a multiline
quoted cell remains part of that cell. Since 0.3.0, legacy preambles with entire
comments wrapped in CSV quotes are unsupported; those comments must be written
with literal leading `#`. Blank and whitespace-only lines are still skipped
(audit issue 2).

Declared `string`, `float`, `integer`, and `datetime` fields become nullable
pandas `string`, `Float64`, `Int64`, and UTC datetime columns, respectively.
Nonmissing datetimes require an explicit timezone. Input `nan` (case-insensitive)
becomes `pd.NA` in strings, floats, and integers, and `pd.NaT` in datetimes.
A nonempty per-column `field_missing` declaration also identifies a missing
value. Other strings, including `NA`, remain literal.

Malformed records or declarations, invalid typed values, and additional
datasets raise `geocsv.GeoCSVError` (a `ValueError`). The reader preserves row
order and duplicate timestamps. It does not derive scientific quantities,
interpolate locations, or choose between same-time records.
