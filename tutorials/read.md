# Read GeoCSV into pandas tables

`geocsv.read` returns one pandas DataFrame per GeoCSV dataset, preserving
source columns, timestamps, units, and metadata. This example uses the
included P0006 file.

Companions: [Markdown](read.md) · [Notebook](read.ipynb).

## Setup

From the cloned repository, activate your environment and install the package:

```bash
source .venv/bin/activate
python -m pip install .
```

See [installation and notebook setup](../docs/installation.md) if needed. Run the
Python examples in order from the repository root, `docs/`, or `tutorials/`.

## 1. Read a file

The small path setup below locates the included data from either a Python
prompt or this notebook.

```python
from pathlib import Path
from mermaid import geocsv

root = Path.cwd()
if root.name in {"docs", "tutorials"}:
    root = root.parent

path = root / "data/fixtures/schema-1.0.0/P0006/P0006.geocsv"
tables = geocsv.read(path)
records = tables[0]  # A list is returned even for a single dataset.
records.head()
```

Inspect the columns and their pandas dtypes:

```python
print(records.shape)
print(records.dtypes)
```

## 2. Select records with pandas

Select GPS measurements and display their positions:

```python
gps = records.loc[records["MethodIdentifier"].str.startswith("Measurement:Position")]
gps[["Time", "Latitude", "Longitude"]].head()
```

The index, `source_record_index`, identifies each row's original position
among the file's data records. Filtering keeps those labels. `Time`
remains a column.

## 3. Inspect source metadata

```python
metadata = records.attrs["geocsv"]
print(metadata.field_units["WaterPressure"])
print(metadata.source_path)
```

Keep `metadata` separately if needed later; arbitrary pandas transformations
and exports may lose `attrs`.

`read` also accepts UTF-8 bytes and results from [fetch](fetch.md). The optional
`datetime_timezone` argument converts zoned timestamps to a requested timezone:

```python
converted = geocsv.read(path, datetime_timezone="America/Los_Angeles")
converted[0]["Time"].head()
```

This changes the displayed timezone while preserving the instant.
See the [reader specification](../docs/reader-spec.md) for format and timestamp
rules, or [plotting](plotting.md) for a quick visualization.
