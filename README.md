# mermaid-geocsv

`mermaid-geocsv` reads MERMAID GeoCSV files into typed pandas DataFrames,
returning one table per dataset through `geocsv.read(...)`:

```python
from mermaid import geocsv
```

It preserves source column names, record order, timestamps and their timezones,
and GeoCSV metadata, including units, comments, and the source file path.

## Install

Requires Python 3.12 or newer. From the repository root:

```bash
python -m pip install .
```

The installation includes pandas 2.2 or newer.

See the [reader specification](docs/READER_SPEC.md) for API and format details,
and the [pandas tutorial](TUTORIAL.md) for examples.

Developed and maintained by [Bathymetrix®](https://bathymetrix.com).
