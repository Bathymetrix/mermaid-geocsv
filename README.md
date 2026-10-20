# mermaid-geocsv

[![Tests](https://github.com/Bathymetrix/mermaid-geocsv/actions/workflows/tests.yml/badge.svg?branch=main&event=push)](https://github.com/Bathymetrix/mermaid-geocsv/actions/workflows/tests.yml)

Fetch and read MERMAID GeoCSV metadata, associate it with ObsPy waveforms,
and export associated original segments to SAC with geographic headers.

The reader returns typed pandas DataFrames while preserving source column
names, record order, timestamps, units, comments, and provenance. Scientific
analysis stays in pandas and other downstream tools.

## Install

Requires Python 3.12 or newer. From the cloned repository (macOS/Linux):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

If `.venv` already exists, activate it and skip the creation step. The base
installation includes pandas 2.2 or newer. For waveform association and SAC
export, add ObsPy 1.5.1 or newer:

```bash
python -m pip install '.[obspy]'
```

See the [installation guide](docs/INSTALLATION.md) for notebook setup.

## Quick start

```python
from mermaid import geocsv

tables = geocsv.read("data/fixtures/P0006/P0006.geocsv")
records = tables[0]  # One DataFrame per dataset, even for a single dataset.
print(records.head())
metadata = records.attrs["geocsv"]
```

## Public API

| Function | Purpose |
| --- | --- |
| [`geocsv.fetch(...)`](docs/tutorials/FETCH.md) | Retrieve verified release files to disk or memory; returns a list of fetch results. Requires an explicit `base_url`. |
| [`geocsv.read(...)`](docs/READER_SPEC.md#python-api) | Parse a local path, bytes, or fetch results; returns a list of dataset tables. |
| [`geocsv.associate(...)`](docs/tutorials/ASSOCIATE.md) | Attach uniquely matched event metadata and coordinates to an ObsPy Trace or Stream in place; returns `None`. |
| [`geocsv.write_sac(trace, path)`](docs/tutorials/WRITE_SAC.md) | Export one associated original MiniSEED segment to a new SAC file; returns `None` and leaves the trace unchanged. |

Fetching and reading do not require ObsPy. Association defaults to original
segments; longer traces require the explicit `allow_first_segment=True`
option. SAC export requires an original segment. See the linked guides for
signatures, matching rules, units, provenance, and limitations.

## Learn more

Each tutorial is standalone, with matching Markdown and notebook versions.

| Tutorial | Guide | Notebook |
| --- | --- | --- |
| Read GeoCSV and use pandas | [Read](docs/tutorials/READ.md) | [READ.ipynb](docs/tutorials/READ.ipynb) |
| Fetch releases | [Fetch](docs/tutorials/FETCH.md) | [FETCH.ipynb](docs/tutorials/FETCH.ipynb) |
| Associate waveforms | [Associate](docs/tutorials/ASSOCIATE.md) | [ASSOCIATE.ipynb](docs/tutorials/ASSOCIATE.ipynb) |
| Write SAC files | [Write SAC](docs/tutorials/WRITE_SAC.md) | [WRITE_SAC.ipynb](docs/tutorials/WRITE_SAC.ipynb) |
| Plot and analyze records | [Plotting](docs/tutorials/PLOTTING.md) | [PLOTTING.ipynb](docs/tutorials/PLOTTING.ipynb) |

For format rules, scientific context, fixture provenance, and design notes,
see the [documentation index](docs/README.md).

Developed and maintained by [Bathymetrix®](https://bathymetrix.com).
