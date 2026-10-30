# mermaid-geocsv

[![Tests](https://github.com/Bathymetrix/mermaid-geocsv/actions/workflows/tests.yml/badge.svg?branch=main&event=push)](https://github.com/Bathymetrix/mermaid-geocsv/actions/workflows/tests.yml)
[![Python 3.11–3.14](https://img.shields.io/badge/Python-3.11%E2%80%933.14-blue)](docs/installation.md#supported-python-versions)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

Fetch and read MERMAID GeoCSV metadata, associate it with [ObsPy](https://docs.obspy.org/) waveforms,
and optionally create SAC station location headers for writing with ObsPy.

Geographic metadata describe the MERMAID receiver (station), including its
approximate depth from water pressure. Optional SAC projections populate only
`stla`, `stlo`, `stel`, and `stdp`. Earthquake-source metadata and `ev*` header
projections are outside this package's scope.

The reader supports only the controlled [MERMAID GeoCSV schema 1.0.0](docs/format-spec.md),
with its required first-line declaration, fixed 16 columns and five method identifiers.
It returns typed pandas tables preserving source order, literal identities,
comments, units and schema/creation provenance. Only empty decoded cells are
missing; two literal Location spaces denote known blank. Finite signed gauge
measurements remain unchanged. Recording Elevation must explicitly supply zero
metres; coordinate elevation and SAC `stel` use that source value.
Legacy MERMAID and generic GeoCSV formats are unsupported. General GeoCSV
[specification examples](docs/references/geocsv-v2.0.4-examples/README.md) are
preserved as reference material. The [fixture inventory](data/fixtures/README.md)
distinguishes active schema inputs from frozen historical evidence. Scientific
analysis stays downstream.

## Install

Supports Python 3.11–3.14. From the cloned repository (macOS/Linux):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

If `.venv` already exists, activate it and skip the creation step. The minimal
installation above includes pandas 2.3.3 or newer and supports `fetch` and
`read`. For `associate` and optional SAC header creation, use `python -m pip
install '.[obspy]'` instead of the minimal install command; the `obspy` extra
includes the core dependencies and adds ObsPy 1.5.1 or newer.

See the [installation guide](docs/installation.md) for dependency support,
CI coverage, and notebook setup.

## Quick start

```python
from mermaid import geocsv

tables = geocsv.read("data/fixtures/schema-1.0.0/P0006/P0006.geocsv")
records = tables[0]  # One DataFrame per file, including single-file input.
print(records.head())
metadata = records.attrs["geocsv"]
```

## API and tutorials

Each tutorial is a short, standalone walkthrough with matching Markdown and
notebook versions. Local examples use included fixtures; fetch demonstrates
a temporary local testing collection. EarthScope downloads three P0006 detections,
associates their metadata, and compares SAC exports with independent fixtures.

| Operation | Purpose | Guide | Notebook |
| --- | --- | --- | --- |
| `geocsv.fetch(...)` | Retrieve verified GeoCSV files to disk or memory. | [fetch.md](tutorials/fetch.md) | [fetch.ipynb](tutorials/fetch.ipynb) |
| `geocsv.read(...)` | Parse local paths, bytes, or fetch results into dataset tables. | [read.md](tutorials/read.md) | [read.ipynb](tutorials/read.ipynb) |
| `geocsv.associate(...)` | Attach uniquely matched metadata and coordinates to ObsPy waveforms in place. | [associate.md](tutorials/associate.md) | [associate.ipynb](tutorials/associate.ipynb) |
| SAC headers and ObsPy writing | Use `associate(..., create_sac_header=True)`, then ObsPy `Trace.write` or `Stream.write`. | [write-sac.md](tutorials/write-sac.md) | [write-sac.ipynb](tutorials/write-sac.ipynb) |
| EarthScope workflow | Download P0006 waveforms, associate metadata, and verify SAC exports. | [earthscope.md](tutorials/earthscope.md) | [earthscope.ipynb](tutorials/earthscope.ipynb) |
| Plot and analyze records | Use pandas and Matplotlib downstream. | [plotting.md](tutorials/plotting.md) | [plotting.ipynb](tutorials/plotting.ipynb) |

Hosted GeoCSV collections remain testing only and contain old-format payloads.
Consumer 0.27.0 requires new schema 1.0.0 data; it cannot parse those hosted files.
The [fetch tutorial](tutorials/fetch.md) serves separate new-schema fixtures locally.
Transport still preserves exact bytes, token release IDs and all fractional digits;
only the two timestamp time-separator colons become hyphens in paths. Local source
implementation does not establish a software release or compatible hosted data.
See the [hosting workflow](docs/hosting.md) and [fetch reference](docs/fetch.md).

Detailed matching rules, association reports, SAC precision and provenance
limits, format rules, and fixture references are in the
[documentation index](docs/README.md).

Developed and maintained by [Bathymetrix®](https://bathymetrix.com).
