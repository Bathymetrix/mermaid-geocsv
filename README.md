# mermaid-geocsv

[![Tests](https://github.com/Bathymetrix/mermaid-geocsv/actions/workflows/tests.yml/badge.svg?branch=main&event=push)](https://github.com/Bathymetrix/mermaid-geocsv/actions/workflows/tests.yml)
[![Python 3.11–3.14](https://img.shields.io/badge/Python-3.11%E2%80%933.14-blue)](docs/INSTALLATION.md#supported-python-versions)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

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

If `.venv` already exists, activate it and skip the creation step. The minimal
installation above includes pandas 2.2 or newer and supports `fetch` and
`read`. For `associate` and optional SAC header creation, use `python -m pip
install '.[obspy]'` instead of the minimal install command; the `obspy` extra
includes the core dependencies and adds ObsPy 1.5.1 or newer.

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

Each tutorial is a short, standalone walkthrough with matching Markdown and
notebook versions. Local examples use included fixtures; fetch demonstrates
the hosted testing collection.

| Operation | Purpose | Guide | Notebook |
| --- | --- | --- | --- |
| `geocsv.fetch(...)` | Retrieve verified GeoCSV files to disk or memory. | [Fetch](docs/tutorials/FETCH.md) | [FETCH.ipynb](docs/tutorials/FETCH.ipynb) |
| `geocsv.read(...)` | Parse local paths, bytes, or fetch results into dataset tables. | [Read](docs/tutorials/READ.md) | [READ.ipynb](docs/tutorials/READ.ipynb) |
| `geocsv.associate(...)` | Attach uniquely matched metadata and coordinates to ObsPy waveforms in place. | [Associate](docs/tutorials/ASSOCIATE.md) | [ASSOCIATE.ipynb](docs/tutorials/ASSOCIATE.ipynb) |
| SAC headers and ObsPy writing | Use `associate(..., create_sac_header=True)`, then ObsPy `Trace.write` or `Stream.write`. | [Write SAC](docs/tutorials/WRITE_SAC.md) | [WRITE_SAC.ipynb](docs/tutorials/WRITE_SAC.ipynb) |
| Plot and analyze records | Use pandas and Matplotlib downstream. | [Plotting](docs/tutorials/PLOTTING.md) | [PLOTTING.ipynb](docs/tutorials/PLOTTING.ipynb) |

Hosted GeoCSV collections remain testing only; `fetch` requires an explicit
`base_url`. The [fetch tutorial](docs/tutorials/FETCH.md) downloads P0006 and
P0045 from `https://bathymetrix.com/geocsv/testing/`. See the
[hosting workflow](docs/HOSTING.md) for publication status.

Detailed matching rules, association reports, SAC precision and provenance
limits, format rules, and fixture references are in the
[documentation index](docs/README.md).
Extended examples and development checks are retained in the
[development notes](docs/development/README.md).

Developed and maintained by [Bathymetrix®](https://bathymetrix.com).
