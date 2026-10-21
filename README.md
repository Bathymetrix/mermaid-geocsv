# mermaid-geocsv

[![Tests](https://github.com/Bathymetrix/mermaid-geocsv/actions/workflows/tests.yml/badge.svg?branch=main&event=push)](https://github.com/Bathymetrix/mermaid-geocsv/actions/workflows/tests.yml)

Fetch and read MERMAID GeoCSV metadata, associate it with ObsPy waveforms,
and export associated waveforms to SAC with geographic headers.

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
| [`geocsv.write_sac(trace, path)`](docs/tutorials/WRITE_SAC.md) | Export one associated MiniSEED-derived waveform to a new SAC file; returns `None` and leaves the trace unchanged. |

Fetching and reading do not require ObsPy. Association defaults to original
segments. With `allow_first_segment=True`, clipped or combined windows may use
one same-SNCL source segment containing the waveform start, provided GeoCSV
sample ranges cover every downloaded sample after clipping and counting overlaps
once. Coverage uses unique nearest-sample placement strictly below half a waveform
interval. This follows the half-sample scale of ObsPy's MiniSEED reader;
absolute start/containment tolerance is separate. Measured offsets
remain in the association report; waveform samples and times are unchanged.
Zero or multiple containing anchors raise; no nearest-prior row is assumed.
Errors identify affected traces, source records, and physical starting lines.

`trace.stats.geocsv.association` is a nested ObsPy `AttribDict` with
`.type` (`single_segment` or `anchor_segment`), a waveform snapshot, source
coverage segments with record/line references and clipped sample ranges, and
measured timing/rate differences. It records association-time evidence, not
waveform construction history; see the [report schema](docs/OBSPY_ASSOCIATION.md#association-report).

Both association types can be exported to SAC. For `anchor_segment`, the anchor's
STLA/STLO/STDP/STEL apply to the entire waveform under the supplied MERMAID
negligible-drift convention. Missing REQ pressure remains undefined. This does
not reconstruct acquisition lineage. Production GeoCSV hosting is still pending.

Associate the final downloaded/clipped/combined window before export. Avoid
changing its samples, start, count, or sampling rate after association. SAC
output has float32 precision and no
serialized GeoCSV provenance; nonfinite or unrepresentable values and identity
codes that cannot survive SAC storage are rejected. No response correction or
counts-to-pressure calibration is supplied.

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
