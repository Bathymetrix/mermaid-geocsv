# mermaid-geocsv

[![Tests](https://github.com/Bathymetrix/mermaid-geocsv/actions/workflows/tests.yml/badge.svg?branch=main&event=push)](https://github.com/Bathymetrix/mermaid-geocsv/actions/workflows/tests.yml)

`mermaid-geocsv` reads MERMAID GeoCSV files into typed pandas DataFrames,
returning one table per dataset. It preserves source column names, record
order, timestamps and their timezones, and GeoCSV metadata, including units,
comments, and the source file path.

Empty and quoted-empty cells in string-valued `Location` preserve the known
empty SEED location code `""`; `nan` and declared missing markers remain missing.
Other columns retain their existing missing-value rules.

An experimental [ObsPy association sandbox](sandbox/obspy_association/README.md)
attaches parsed event metadata to original processed traces. Its paired
waveform fixtures and full GeoCSV histories are documented in the
[rebuilt-source audit](data/fixtures/association/README.md); the adapter is
not yet part of the package's public API. Strict association is the default;
`allow_merge=True` permits adopting the first segment's location for a longer
trace. `stats.geocsv.association` records `one_segment` or `first_segment`.
`stats.geocsv.starttime_difference_seconds` records waveform minus matched
GeoCSV start time in seconds. Batch lookup groups events by SNCL and sorts
them by UTC start time.
The default absolute time tolerance is 100 microseconds; use an explicit
`time_tolerance=0.001` for millisecond-rendered Automaid histories when needed.
Merged inputs require exact gap-free source sample coverage on the waveform
grid after overlapping samples are counted once.
The source-row attachment uses ObsPy's `AttribDict`; source columns colliding
with its attributes or methods, or with association-owned keys, raise before
any trace is modified.
Source preflight rejects invalid event identities and duplicate full matching
keys. Only Location may be empty; no SNCL field may be missing. All trace
matches validate before projections or mutation.
See the [merged-trace policy](docs/OBSPY_MERGED_TRACES.md) for checks and limits.

Reader version 0.11.0 also preserves source datetime resolution in immutable
`frame.attrs["geocsv"].datetime_resolution_ns[column][source_record_index]`
(integer nanoseconds per non-missing timestamp). Timestamp values retain up to
nine fractional digits, including timezone information; no MERMAID clock
resolution is imposed on this general reader.

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
- ObsPy references: [Stats](docs/OBSPY_STATS.md), [Stream and merge](docs/STREAM.md),
  and [comparison with association](docs/OBSPY_ASSOCIATION_COMPARISON.md).

Developed and maintained by [Bathymetrix®](https://bathymetrix.com).
