# mermaid-geocsv

`mermaid-geocsv` reads MERMAID GeoCSV files into typed pandas DataFrames.

Developed and maintained by [Bathymetrix®](https://bathymetrix.com).

The package scaffold is in place; the reader implementation is forthcoming.
The examples below define its planned public API.

GeoCSV is self-describing: it carries its field names, declared field types,
units, delimiter, and descriptive comments with the tabular data. This package
preserves that information while providing a standard Python analysis surface.

## Use

```python
from mermaid import geocsv
import pandas as pd

frame = geocsv.read("P0006.geocsv")
```

`frame` is the only return value: a typed pandas `DataFrame`. Its columns use
the exact field names from the GeoCSV header. Its zero-based `row_index`
preserves source data order, and `StartTime` is a timezone-aware UTC column.

```python
# Select position-bearing records for a trajectory map.
trajectory = frame.loc[
    frame["Latitude"].notna() & frame["Longitude"].notna()
].sort_values("StartTime")

# Find every record at an exact timestamp. Timestamps need not be unique.
time = pd.Timestamp("2019-04-23T19:31:14Z")
matches = frame.loc[
    frame["StartTime"].eq(time),
    ["MethodIdentifier", "DataQuality", "Latitude"],
]
```

## GeoCSV metadata

GeoCSV metadata is available on the returned frame:

```python
metadata = frame.attrs["geocsv"]

metadata.field_types["SampleCount"]
metadata.field_units["Latitude"]
metadata.comments
```

As of writing, pandas documents `DataFrame.attrs` as experimental. We use it
deliberately because GeoCSV is self-describing: its format metadata belongs
with its parsed table. Metadata is guaranteed on the freshly parsed frame, but
may not survive arbitrary pandas transformations or file exports.

## Scope

The initial reader supports one GeoCSV dataset per file. It parses and types
the declared table; it does not derive scientific quantities, interpolate
locations, or choose between same-time records.
