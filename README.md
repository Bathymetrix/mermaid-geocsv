# mermaid-geocsv

[![Tests](https://github.com/Bathymetrix/mermaid-geocsv/actions/workflows/tests.yml/badge.svg?branch=main&event=push)](https://github.com/Bathymetrix/mermaid-geocsv/actions/workflows/tests.yml)

`mermaid-geocsv` fetches MERMAID GeoCSV files, reads them into typed pandas
DataFrames, associates event metadata with ObsPy waveforms, and exports
associated original segments to SAC with geographic headers. The reader returns
one table per dataset and preserves source column names, record order, timestamps and
their timezones, and GeoCSV metadata, including units, comments, and the source
file path or download provenance.

Empty and quoted-empty cells in string-valued `Location` preserve the known
empty SEED location code `""`; `nan` and declared missing markers remain missing.
Other columns retain their existing missing-value rules.

`geocsv.associate` attaches parsed event metadata to original MiniSEED-derived
ObsPy traces in place and returns `None`. Paired waveform fixtures and tracked
GeoCSV subsets are documented in the
[fixture inventory](data/fixtures/association/README.md). Strict association is
the default;
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
`geocsv.write_sac(trace, path)` separately exports one associated original
segment to a new SAC file; association itself does not create SAC headers.
See the [merged-trace policy](docs/OBSPY_MERGED_TRACES.md) for checks and limits.
Real-data association tests run from tracked files without restoring full
histories. Association requires complete source latitude/longitude in declared
degrees_north/degrees_east and creates fresh `stats.geocsv` and
`stats.coordinates` containers, including the adopted sea-level elevation zero.
Both destinations must be absent. Waveform samples and native headers remain
unchanged.

Association validates the supplied waveform and attaches metadata describing its matched source record at that moment. Subsequent waveform modifications do not update or revalidate the attachment. Users are responsible for interpreting and maintaining metadata after processing.

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

For association or SAC writing, install the optional ObsPy 1.5.1 or newer dependency:

```bash
python -m pip install '.[obspy]'
```

Reader import and use do not load or require ObsPy.

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

Retrieve one float, selected floats, or a complete release:

```python
# Local preview of the website's test collection; production URL is undecided.
collection_url = "http://localhost:8000/data/geocsv/testing/"

downloads = geocsv.fetch("P0006", base_url=collection_url)  # Save under ./<release_id>/.
downloads = geocsv.fetch(["P0006"], base_url=collection_url, output_dir="data")
downloads = geocsv.fetch(base_url=collection_url, output_dir=None)  # All floats, in memory.
tables = geocsv.read(downloads)
provenance = tables[0].attrs["geocsv"].download
```

`fetch(instrument_ids=None, *, base_url, output_dir=".", release=None,
timeout=30)` discovers files from a release manifest and always returns a list
of `GeoCSVFetchResult` values. Omit identifiers to fetch the complete release;
`release=None` resolves latest once for the batch. An explicit release bypasses
latest. Every file must match its declared byte count and SHA-256. Local output
includes the original manifest; existing identical files are verified and
reused, while differing files raise instead of being overwritten. There is no
implicit persistent cache. Fetching uses the Python standard library.

`read` accepts local paths, bytes, one fetch result, or its result list. It
returns a flat list of dataset tables without combining files. Each table
retains immutable GeoCSV metadata and, for fetch results, release/URL/checksum
provenance. `source_path` is None for memory-only input. Metadata is guaranteed
on freshly returned frames; persistence through pandas transformations or
exports is not guaranteed. See the [fetch guide](docs/tutorials/FETCH.md) for storage,
memory use, failure behavior, and the test collection layout.

Associate an original MiniSEED Trace or Stream with its GeoCSV tables:

```python
from obspy import read as read_waveforms
from mermaid import geocsv

stream = read_waveforms("/path/to/original.mseed")
tables = geocsv.read("/path/to/geo_DET_REQ.csv")
geocsv.associate(stream, tables, time_tolerance=0.001)
print(stream[0].stats.coordinates)
print(stream[0].stats.geocsv.metadata.source_path)
```

The public signature is `associate(waveforms, records, *,
time_tolerance=0.0001, allow_merge=False)`. The example explicitly allows 1 ms
for millisecond-rendered Automaid histories; the default remains 100
microseconds. Exact SNCL, original sample count, and rates within 0.01 Hz are
required for a standard match. That rate threshold remains provisional
scientific policy. No unique match or an invalid projection raises
`ValueError` before any trace in the batch is modified. Unsupported waveform
argument types raise `TypeError`; missing ObsPy raises an actionable
`ImportError`. See the association tutorial for provenance and fallback details.

Write an associated original segment to an explicit, unused path:

```python
geocsv.write_sac(stream[0], "/path/to/associated.sac")
```

`write_sac(trace, path)` returns `None` and leaves the input trace unchanged.
It uses the attached `stats.geocsv` source row and unit metadata, without
reopening GeoCSV or reading `stats.coordinates` or existing `stats.sac` values.
ObsPy supplies waveform headers; geographic headers are `stla`/`stlo` from
Latitude/Longitude, `stel=0` metres at sea level, and
`stdp=WaterPressure[mbar]/100` metres. The latter reproduces automaid's
approximate 1 dbar ≈ 1 metre convention, not a physical depth calculation.
Missing REQ pressure (source DataQuality D) leaves `stdp` undefined; missing DET
pressure raises. `first_segment` associations are rejected. Export original
segments before processing: consistency checks cannot establish an unchanged
sample history. Output is little-endian binary SAC with float32 samples and
floating headers; samples are not calibrated. Other automaid-specific headers
and GeoCSV provenance are not reconstructed. Existing files are never
overwritten, and parent directories must exist. Loop over a Stream with
explicit distinct paths for several files; exports are independent calls.
See the [SAC writing tutorial](docs/tutorials/WRITE_SAC.md) for round-trip
verification and comparison precision.

## Documentation

- [Reader specification](docs/READER_SPEC.md): Python API, metadata, and
  detailed parsing rules.
- Fetch tutorial: [Markdown](docs/tutorials/FETCH.md) or
  [Jupyter notebook](docs/tutorials/FETCH.ipynb).
- Read tutorial and pandas basics: [Markdown](docs/tutorials/READ.md) or
  [Jupyter notebook](docs/tutorials/READ.ipynb).
- Association tutorial and API contract: [Markdown](docs/tutorials/ASSOCIATE.md)
  or [Jupyter notebook](docs/tutorials/ASSOCIATE.ipynb), including a real P0045
  merge from 2022-01-15 with explicit overlap and alignment choices.
- SAC writing and independent automaid comparisons: [Markdown](docs/tutorials/WRITE_SAC.md)
  or [Jupyter notebook](docs/tutorials/WRITE_SAC.ipynb).
- Plotting and downstream analysis: [Markdown](docs/tutorials/PLOTTING.md) or
  [Jupyter notebook](docs/tutorials/PLOTTING.ipynb).
- [Installation guide](docs/INSTALLATION.md): environment and notebook setup.
- [TODO](TODO.md): fixture maintenance tasks.
- [Open questions](docs/OPEN_QUESTIONS.md): unresolved format and association
  details; [future workflows](docs/FUTURE.md) tracks planned functionality.
- [Fixture maintenance](scripts/fixtures/README.md): optional complete-history
  restoration/checks and initial collection provenance.
- Scientific context: [MERMAID data quality](docs/MERMAID_DATA_QUALITY.md) and
  [dated retrieval observations](docs/OBSPY_RETRIEVAL_OBSERVATIONS.md).
- ObsPy references: [Stats](docs/OBSPY_STATS.md), [Stream and merge](docs/STREAM.md),
  and [comparison with association](docs/OBSPY_ASSOCIATION_COMPARISON.md).

Developed and maintained by [Bathymetrix®](https://bathymetrix.com).
