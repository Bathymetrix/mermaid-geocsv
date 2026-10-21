# Read GeoCSV into pandas tables

`geocsv.read` parses GeoCSV into typed pandas DataFrames while preserving
source metadata. This tutorial explores the real P0006 fixture.
The companion files [READ.md](READ.md) and
[READ.ipynb](READ.ipynb) contain the same prose and Python examples;
update both together whenever either changes.

This tutorial runs independently using tracked fixtures from a fresh checkout.
From the repository root, activate the existing environment and install the
required packages:

```bash
source .venv/bin/activate
python -m pip install .
```

See the [installation guide](../INSTALLATION.md) to create an environment.
For a notebook, also install JupyterLab and a Python kernel:

```bash
python -m pip install jupyterlab ipykernel
python -m jupyterlab docs/tutorials/READ.ipynb
```

Select this repository's `.venv` kernel and run cells from top to bottom.
Alternatively, run the Python blocks in order at a Python prompt. Start from
the repository root, `docs/`, or `docs/tutorials/`.

## 1. Read one local file

```python
from pathlib import Path
from mermaid import geocsv
import pandas as pd

repository_root = Path.cwd()
if repository_root.name == "tutorials":
    repository_root = repository_root.parent.parent
elif repository_root.name == "docs":
    repository_root = repository_root.parent
fixture_path = repository_root / "data/fixtures/P0006/P0006.geocsv"
tables = geocsv.read(fixture_path)
records = tables[0]  # The P0006 file contains one dataset.
records.head()
```

The simplest call is `geocsv.read(fixture_path)`: no optional arguments are
needed. It returns a list, even for this one-dataset file. Now inspect its
first table with ordinary pandas operations:

```python
type(records)
records.shape
records.head()
records.tail(3)
records.columns.tolist()
records.dtypes
records.info()
```

`shape` gives `(rows, columns)`. A DataFrame also has an **index**: the labels
displayed to the left of its rows. This reader creates an index named
`source_record_index`. The first data record in the file gets label `0`, the
second gets `1`, and so on. These labels identify each record's original
position among the data records; they are not physical file line numbers,
which also count headers and comments. The index is separate from the data
columns.

```python
records.index.name                 # 'source_record_index'
records.index[:5].tolist()          # [0, 1, 2, 3, 4]
```

When you filter or sort rows, their existing index labels stay attached.
A filtered table might therefore have labels such as `0, 1, 7, 12`, and a
sorted table can show labels out of numerical order. Pandas does not
automatically renumber them. Below, `loc` uses these labels, while `iloc`
uses a row's current position in the table.

`StartTime` is a data column, rather than the index. Multiple records can
have the same timestamp and still have distinct `source_record_index` labels.
In this P0006 file, every timestamp has an explicit UTC timezone, so the column
has a timezone-aware datetime dtype. Its storage resolution depends on the
pandas version and parsed values; it does not establish measurement accuracy.
In other GeoCSV files, timezone-free values remain naive; mixed naive and zoned
values are preserved as `Timestamp`
objects in an `object` column.

One column name gives a one-dimensional pandas `Series`; a list of names gives
another two-dimensional `DataFrame`:

```python
latitude = records["Latitude"]
coordinates = records[["Latitude", "Longitude"]]
type(latitude)
type(coordinates)
coordinates.head()
records.loc[0, ["StartTime", "MethodIdentifier", "Latitude"]]
records.iloc[:5, :4]
```

`.loc[row, column]` selects by row index label and column name; `.iloc` uses
integer positions. In slices, `.loc` includes the stop label, while `.iloc`
excludes the stop position. These expressions leave `records` unchanged. A
`Series` retains an index and a dtype, and arithmetic acts on its values
rather than repeating a Python list.

After selecting rows by position, their original labels stay with them:

```python
subset = records.iloc[1:3]
subset.index.tolist()  # [1, 2]
subset.loc[2]          # row labeled 2
subset.iloc[0]         # first row in subset, labeled 1
```

The file contains different record types. Check their counts and which
measurements are present:

```python
records["MethodIdentifier"].value_counts()
records[["Latitude", "Longitude", "WaterPressure"]].isna().sum()
records["StartTime"].min(), records["StartTime"].max()
records["WaterPressure"].describe()
```

`isna()` marks missing values, `sum()` counts them, and `describe()` summarizes
nonmissing numeric values. The original units and declarations are retained:

```python
metadata = records.attrs["geocsv"]
metadata.field_units["WaterPressure"]
metadata.field_units["Latitude"]
metadata.field_types["StartTime"]
metadata.comments[:5]
metadata.source_path
metadata.record_line_numbers[0]  # Physical starting line of source record 0.
```

`source_path` is the full, resolved path of the file opened by the reader. It
records where the data came from; it is not a field declared in the GeoCSV.
`record_line_numbers` is a read-only map from record indices to one-based
physical starting lines, including for records with multiline quoted cells.
For in-memory input, `source_path` is None. When reading a fetch result,
`metadata.download` retains the selected release, requested URLs, verified
checksum and byte count, test-collection flag, and original manifest bytes;
for a bare path or bytes it is None. See [Fetching GeoCSV](FETCH.md) for local
and memory-only retrieval. Metadata is guaranteed on freshly parsed frames,
including after a fetch, with no guarantee of persistence through later
pandas operations or exports.
Optional `metadata.field_long_names` and `metadata.field_standard_names` map
source column names to individually trimmed descriptions; P0006 does not
declare them, so their values are empty. The reader preserves coordinate
columns as written and does not infer latitude or longitude roles.
The fresh parsed DataFrame has this metadata. If you need it later, keep
`metadata` separately: pandas does not guarantee `attrs` through arbitrary
transformations or exports. In particular, concatenating tables from
different source files drops their differing `attrs`.

## 2. Select, filter, and summarize records

The boolean expression below has one value per row. `loc[mask]` keeps rows
where it is true. A GPS record has coordinates, but most pressure-only
records do not.

```python
gps_mask = records["MethodIdentifier"].str.startswith("Measurement:GPS")
gps = records.loc[gps_mask].dropna(subset=["Latitude", "Longitude"])
gps = gps.sort_values("StartTime")
gps[["StartTime", "Latitude", "Longitude"]].head()
len(gps)
```

`dropna(subset=...)` discards rows missing either coordinate; it does not
change `records`. The source row number remains the index even after sorting.
For the first five rows by their new time order, use `gps.head()`, not
`gps.loc[:4]`.

Filter a UTC date interval with explicit bounds. The upper bound is excluded,
so this selects all of calendar year 2019:

```python
start = pd.Timestamp("2019-01-01", tz="UTC")
end = pd.Timestamp("2020-01-01", tz="UTC")
gps_2019 = gps.loc[gps["StartTime"].ge(start) & gps["StartTime"].lt(end)]
gps_2019[["StartTime", "Latitude", "Longitude"]].head()
len(gps_2019)
```

Use parentheses around comparisons when combining them with `&` (AND) or
`|` (OR). For example:

```python
has_position = records["Latitude"].notna() & records["Longitude"].notna()
has_pressure = records["WaterPressure"].notna()
records.loc[has_position & has_pressure, ["StartTime", "Latitude", "Longitude", "WaterPressure"]].head()
```

Some useful aggregations:

```python
gps.groupby(gps["StartTime"].dt.year).size()
gps.groupby(gps["StartTime"].dt.year)[["Latitude", "Longitude"]].median()
records.groupby("MethodIdentifier")["WaterPressure"].agg(["count", "min", "median", "max"])
```

`groupby` forms groups and `agg` computes summaries for each. The yearly
coordinate medians are descriptive only; a median longitude near the date
line can be misleading because longitude wraps at ±180°.

## 3. Read bytes instead of a path

Local paths and raw UTF-8 bytes can be read independently of `fetch`:

```python
byte_tables = geocsv.read(fixture_path.read_bytes())
assert byte_tables[0].attrs["geocsv"].source_path is None
pd.testing.assert_frame_equal(records, byte_tables[0])
```

## 4. Explicitly convert timestamp timezone

The default preserves source timezone notation. For zoned timestamps, request
a common output timezone explicitly:

```python
converted = geocsv.read(fixture_path, datetime_timezone="America/Los_Angeles")
print(converted[0]["StartTime"].head())
assert converted[0]["StartTime"].iloc[0] == records["StartTime"].iloc[0]
help(geocsv.read)
```

This changes the timezone representation of an instant, not the observation
time. The option requires timezone-aware source values; it does not infer a
timezone for naive timestamps.

The full reader signature and timestamp policies are documented in the
[reader specification](../READER_SPEC.md). Each file returns a list with one
DataFrame per dataset, even for a single dataset. Original column spellings,
source record labels, units, and missing values remain available. Reading
performs no plotting, coordinate conversion, or scientific inference.

For analysis examples, continue with the standalone [plotting tutorial](PLOTTING.md).
For verified disk or memory retrieval, use the [fetch tutorial](FETCH.md).
For waveform metadata attachment, use the [association tutorial](ASSOCIATE.md).
