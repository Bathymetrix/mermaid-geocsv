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

The reader uses the [MERMAID GeoCSV 1.0.0-rc2 schema](docs/format-spec.md).
It returns typed pandas tables with 18 columns, separate measured and derived
values, and source order and provenance. Two literal location spaces represent
a known blank code. GPS fixes and signed gauge pressure readings are preserved.
Waveform rows supply estimated position and measured pressure where available.
Coordinate elevation is absent and SAC `stel` is undefined.

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

from pathlib import Path

path = Path("data/fixtures/schema-1.0.0-rc2/P0006.geocsv")
records, = geocsv.read(path)
print(records.head())
```

For waveform association, install the ObsPy extra and use the included
original MiniSEED example with the P0006 table:

```python
from obspy import read as read_waveforms

mseed = Path("data/fixtures/P0006/waveforms/20180629T170731.06_5B3F1904.MER.DET.WLT5.mseed")
trace, = read_waveforms(str(mseed))
geocsv.associate(trace, [records], create_sac_header=True)
project_metadata = {
    "metadata_path": str(path),
    "source_index": trace.stats.geocsv.source_index,
    "source_line": trace.stats.geocsv.source_line,
    "mseed_filename": mseed.name,
}
# Use your own unused output filename; ObsPy writes the projected SAC headers.
# trace.write("my-output.sac", format="SAC")
```

Retain `project_metadata`, the source GeoCSV and original MiniSEED with the
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

The public testing workflow uses immutable, manifest-pinned snapshots.
The fetch tutorial applies after a testing snapshot is activated. Unit tests
serve rc2 fixtures over local HTTP and replay saved EarthScope responses.
See [hosting](docs/hosting.md) and [fetch](docs/fetch.md).

Detailed matching rules, association reports, SAC precision and provenance
limits, format rules, and fixture references are in the
[documentation index](docs/README.md).

Developed and maintained by [Bathymetrix®](https://bathymetrix.com).

Measurement rows supply observations. Derived times and estimated positions
come from automaid. The `producer` comment identifies the software version.

GeoCSV references use `source_index` for zero-based data rows and `source_line`
for one-based physical starting lines, as in a text editor. Metadata
`line_numbers[index]` maps between them. Association accepts the parsed
DataFrame list as `tables`.
