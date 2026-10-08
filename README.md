# mermaid-geocsv

[![Tests](https://github.com/Bathymetrix/mermaid-geocsv/actions/workflows/tests.yml/badge.svg?branch=main&event=push)](https://github.com/Bathymetrix/mermaid-geocsv/actions/workflows/tests.yml)

`mermaid-geocsv` reads MERMAID GeoCSV files into typed pandas DataFrames,
returning one table per dataset. It preserves source column names, record
order, timestamps and their timezones, and GeoCSV metadata, including units,
comments, and the source file path.

## Install

Requires Python 3.12 or newer and pandas 2.2 or newer. After cloning the
repository, run these commands from its root (macOS/Linux):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

If `.venv` already exists, activate it and skip the creation step. See the
[installation guide](docs/INSTALLATION.md) for notebook setup and optional
ObsPy support.

## Use

```python
from mermaid import geocsv

tables = geocsv.read("data/fixtures/P0006/P0006.geocsv")
records = tables[0]  # One DataFrame per dataset, even for a single-dataset file.
records.head()
metadata = records.attrs["geocsv"]
```

The reader parses and preserves GeoCSV information; downstream scientific
analysis remains in pandas or other tools.

## Documentation

- [Reader specification](docs/READER_SPEC.md): Python API, metadata, and
  detailed parsing rules.
- Pandas tutorial: [Markdown](docs/TUTORIAL.md) or
  [Jupyter notebook](docs/TUTORIAL.ipynb).
- [Installation guide](docs/INSTALLATION.md): environment and notebook setup.
- [Open GeoCSV questions](docs/OPEN_QUESTIONS.md): unresolved format details.

Developed and maintained by [Bathymetrix®](https://bathymetrix.com).
