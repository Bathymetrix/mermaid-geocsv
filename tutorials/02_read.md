# Read GeoCSV into pandas tables

`geocsv.read` returns one typed pandas DataFrame per MERMAID GeoCSV file.
This example uses a [P0006 rc2 subset](../data/fixtures/schema-1.0.0-rc2/README.md)
generated with automaid v4.11.2.

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

path = root / "data/fixtures/schema-1.0.0-rc2/P0006.geocsv"
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
gps = records.loc[records["type"].eq("gps")]
gps[["measured_time", "measured_latitude", "measured_longitude"]].head()
```

The index, `source_index`, identifies each row's original position
among the file's data records. Filtering keeps those labels. The `measured_time` and `derived_time` columns retain their distinct meanings.

## 3. Inspect source metadata

```python
metadata = records.attrs["geocsv"]
print(metadata.field_units["measured_pressure"])
print(metadata.source_path)
```

Keep `metadata` separately if needed later; arbitrary pandas transformations
and exports may lose `attrs`.

`read` also accepts UTF-8 bytes and results from [fetch](01_fetch.md). The optional
`datetime_timezone` argument converts zoned timestamps to a requested timezone:

```python
converted = geocsv.read(path, datetime_timezone="America/Los_Angeles")
converted[0]["measured_time"].head()
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
print(raw_cells[["station", "location"]].head())
```

This example reads the included single-line-record fixture. The `comment="#"`
shortcut is not a general GeoCSV parser for arbitrary multiline content.
Empty cells remain empty strings in this inspection, rather than the typed
reader's missing values.
See the [reader specification](../docs/reader-spec.md) for format and timestamp
rules, or [plotting](06_plotting.md) for a quick visualization.
