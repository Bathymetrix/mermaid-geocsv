# Read GeoCSV into pandas tables

`geocsv.read` accepts only MERMAID GeoCSV schema 1.0.0 and returns one pandas
DataFrame per file, preserving source columns, timestamps, units, and metadata.
Generic GeoCSV and legacy MERMAID files are unsupported. This example uses a
[schema-converted P0006 subset](../data/fixtures/schema-1.0.0/README.md),
not newly generated producer output. Its provenance records representation
changes and the mapping to historical source records.

Companions: [Markdown](02_read.md) · [Notebook](02_read.ipynb).

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

`read` also accepts UTF-8 bytes and results from [fetch](01_fetch.md). The optional
`datetime_timezone` argument converts zoned timestamps to a requested timezone:

```python
converted = geocsv.read(path, datetime_timezone="America/Los_Angeles")
converted[0]["Time"].head()
```

This changes the displayed timezone while preserving the instant.

## 4. Inspect CSV cells without schema typing

For a downstream CSV-only inspection, pandas can retain every decoded cell as
text. Disable automatic missing markers and numeric inference so leading-zero
codes, literal `nan` and two-space Location values survive. This bypasses
MERMAID schema validation and does not create association provenance; use
`geocsv.read` for association inputs.

```python
import pandas as pd

raw_cells = pd.read_csv(path, comment="#", dtype="string",
                        keep_default_na=False, skipinitialspace=False)
print(raw_cells[["Station", "Location"]].head())
```

This example reads the included single-line-record fixture. The `comment="#"`
shortcut is not a general GeoCSV parser for arbitrary multiline content.
Empty cells remain empty strings in this inspection, rather than the typed
reader's missing values.
See the [reader specification](../docs/reader-spec.md) for format and timestamp
rules, or [plotting](06_plotting.md) for a quick visualization.
