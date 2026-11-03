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

downloads = geocsv.fetch("P0006", base_url="https://bathymetrix.com/geocsv/testing/",
                         output_dir=None)
release = downloads[0].provenance.release_id
records = geocsv.read(downloads)[0]
print(release, records.head())
```

For the full waveform workflow, install the ObsPy extra and use the included
original MiniSEED example with the fetched P0006 table:

```python
from pathlib import Path
import hashlib
from obspy import read as read_waveforms

mseed = Path("data/fixtures/P0006/waveforms/20180629T170731.06_5B3F1904.MER.DET.WLT5.mseed")
trace, = read_waveforms(str(mseed))
geocsv.associate(trace, [records], create_sac_header=True)
project_metadata = {
    "release_id": release,
    "manifest_sha256": hashlib.sha256(downloads[0].provenance.manifest).hexdigest(),
    "source_index": trace.stats.geocsv.source_index,
    "source_line": trace.stats.geocsv.source_line,
    "mseed_filename": mseed.name,
}
# Use your own unused output filename; ObsPy writes the projected SAC headers.
# trace.write("my-output.sac", format="SAC")
```

Retain `project_metadata`, the fetched manifest and original MiniSEED with the
research project. SAC does not preserve the complete GeoCSV attachment. This is
an example of project metadata, not a package-managed sidecar contract.

## API and tutorials

The numeric prefixes give the recommended execution order. Each tutorial is a
short, standalone walkthrough with matching Markdown and notebook versions;
no tutorial depends on another tutorial's state. Local examples use included
fixtures; fetch downloads from the public testing collection. EarthScope downloads three P0006 detections,
associates their metadata, and compares SAC exports with independent fixtures.

| Operation | Purpose | Guide | Notebook |
| --- | --- | --- | --- |
| `geocsv.fetch(...)` | Retrieve verified GeoCSV files to disk or memory. | [01_fetch.md](tutorials/01_fetch.md) | [01_fetch.ipynb](tutorials/01_fetch.ipynb) |
| `geocsv.read(...)` | Parse local paths, bytes, or fetch results into dataset tables. | [02_read.md](tutorials/02_read.md) | [02_read.ipynb](tutorials/02_read.ipynb) |
| `geocsv.associate(...)` | Attach uniquely matched metadata and coordinates to ObsPy waveforms in place. | [03_associate.md](tutorials/03_associate.md) | [03_associate.ipynb](tutorials/03_associate.ipynb) |
| SAC headers and ObsPy writing | Use `associate(..., create_sac_header=True)`, then ObsPy `Trace.write` or `Stream.write`. | [04_write-sac.md](tutorials/04_write-sac.md) | [04_write-sac.ipynb](tutorials/04_write-sac.ipynb) |
| EarthScope workflow | Download P0006 waveforms, associate metadata, and verify SAC exports. | [05_earthscope.md](tutorials/05_earthscope.md) | [05_earthscope.ipynb](tutorials/05_earthscope.ipynb) |
| Plot and analyze records | Use pandas and Matplotlib downstream. | [06_plotting.md](tutorials/06_plotting.md) | [06_plotting.ipynb](tutorials/06_plotting.ipynb) |

Hosted GeoCSV collections remain testing only. Testing latest serves the
P0006/P0045 schema 1.0.0 snapshot `2026-11-03T22:29:17.981000Z`, compatible
with consumer 0.28.0. Other retained snapshots may use unsupported schemas.
The [fetch tutorial](tutorials/01_fetch.md) downloads from the public testing collection.
Transport still preserves exact bytes, token release IDs and all fractional digits;
only the two timestamp time-separator colons become hyphens in paths. Package source and hosted snapshot identities are separate.
See the [hosting workflow](docs/hosting.md) and [fetch reference](docs/fetch.md).

Detailed matching rules, association reports, SAC precision and provenance
limits, format rules, and fixture references are in the
[documentation index](docs/README.md).

Developed and maintained by [Bathymetrix®](https://bathymetrix.com).

The example resolves testing latest once and retains its identity. Pin any further
fetches with `release=release`. A canonical first-v1 example is deferred until that
snapshot is published. Measurement rows supply observations; derived times and
locations are producer estimates. Users may reinterpolate measurements. Consult
the automaid version in `#attribution` for estimation methods and assumptions.

Consumer 0.28.0 names GeoCSV references `source_index` (zero-based data rows)
and `source_line` (one-based physical starting lines, as in a text editor).
Metadata `line_numbers[index]` maps between them. This replaces
`source_record_index`, `source_line_number`, and `record_line_numbers`; association's
DataFrame-list argument is now `tables`. No compatibility aliases are supplied.
