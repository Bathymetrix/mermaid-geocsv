# mermaid-geocsv

[![Tests](https://github.com/Bathymetrix/mermaid-geocsv/actions/workflows/tests.yml/badge.svg?branch=main&event=push)](https://github.com/Bathymetrix/mermaid-geocsv/actions/workflows/tests.yml)

Fetch and read MERMAID GeoCSV metadata, associate it with [ObsPy](https://docs.obspy.org/) waveforms,
and optionally create SAC station location headers for writing with ObsPy.

The reader returns typed pandas DataFrames while preserving source column
names, record order, timestamps, units, comments, and provenance. It follows
[MERMAID reader conventions](docs/READER_SPEC.md); general GeoCSV conformance
is not promised. Scientific analysis stays in downstream tools.

## Install

Supports Python 3.11–3.14. From the cloned repository (macOS/Linux):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

If `.venv` already exists, activate it and skip the creation step. The base
installation includes pandas 2.2 or newer. For waveform association and optional SAC
header creation, add ObsPy 1.5.1 or newer:

```bash
python -m pip install '.[obspy]'
```

See the [installation guide](docs/INSTALLATION.md) for dependency support,
CI coverage, and notebook setup.

## Quick start

```python
from mermaid import geocsv

tables = geocsv.read("data/fixtures/P0006/P0006.geocsv")
records = tables[0]  # One DataFrame per dataset, even for a single dataset.
print(records.head())
metadata = records.attrs["geocsv"]
```

## API and tutorials

Each tutorial is standalone, with matching Markdown and notebook versions.

| Operation | Purpose | Guide | Notebook |
| --- | --- | --- | --- |
| `geocsv.fetch(...)` | Retrieve verified GeoCSV files to disk or memory. | [Fetch](docs/tutorials/FETCH.md) | [FETCH.ipynb](docs/tutorials/FETCH.ipynb) |
| `geocsv.read(...)` | Parse local paths, bytes, or fetch results into dataset tables. | [Read](docs/tutorials/READ.md) | [READ.ipynb](docs/tutorials/READ.ipynb) |
| `geocsv.associate(...)` | Attach uniquely matched metadata and coordinates to ObsPy waveforms in place. | [Associate](docs/tutorials/ASSOCIATE.md) | [ASSOCIATE.ipynb](docs/tutorials/ASSOCIATE.ipynb) |
| SAC headers and ObsPy writing | Use `associate(..., create_sac_header=True)`, then ObsPy `Trace.write` or `Stream.write`. | [Write SAC](docs/tutorials/WRITE_SAC.md) | [WRITE_SAC.ipynb](docs/tutorials/WRITE_SAC.ipynb) |
| Plot and analyze records | Use pandas and Matplotlib downstream. | [Plotting](docs/tutorials/PLOTTING.md) | [PLOTTING.ipynb](docs/tutorials/PLOTTING.ipynb) |

Hosted GeoCSV collections remain testing only; `fetch` requires an explicit
`base_url`. See the [hosting workflow](docs/HOSTING.md) for publication status.

Detailed matching rules, association reports, SAC precision and provenance
limits, format rules, and fixture references are in the
[documentation index](docs/README.md).

Developed and maintained by [Bathymetrix®](https://bathymetrix.com).
