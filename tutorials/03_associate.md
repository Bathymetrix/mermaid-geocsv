# Associate GeoCSV metadata with a waveform

`geocsv.associate` attaches the matching GeoCSV waveform-acquisition record
and MERMAID receiver (station) coordinates to an ObsPy Trace or Stream.
The source subject `Recording` identifies an original contiguous waveform segment. These examples use included MiniSEED and GeoCSV fixtures and run offline.

Companions: [Markdown](03_associate.md) · [Notebook](03_associate.ipynb).

## Setup

From the cloned repository, activate your environment and install ObsPy support:

```bash
source .venv/bin/activate
python -m pip install '.[obspy]'
```

See [installation and notebook setup](../docs/installation.md) if needed. Run the
Python examples in order from the repository root, `docs/`, or `tutorials/`.

## 1. Read and associate one MiniSEED trace

```python
from pathlib import Path
from obspy import read as read_waveforms
from mermaid import geocsv

root = Path.cwd()
if root.name in {"docs", "tutorials"}:
    root = root.parent

example_dir = root / "data/fixtures/association/452.020-P-0030"
waveform_path = (
    example_dir / "0009_20210528-04h30m10s"
    / "20210528T053250.0030_60B08BB3.MER.DET.WLT2.mseed"
)
tables = geocsv.read(root / "data/fixtures/schema-1.0.0/association/452.020-P-0030/association_subset.geocsv")
trace = read_waveforms(str(waveform_path))[0]
geocsv.associate(trace, tables)
```

Association modifies the supplied waveform in place and returns `None`.
It preserves the waveform samples and native headers. Inspect the attached
source record and coordinates:

```python
print(trace.stats.geocsv.MethodIdentifier)
print(trace.stats.coordinates)
print(trace.stats.geocsv.association.type)  # single_segment
```

The default match requires the same network, station, location, channel,
sample count, and agreeing sample rate, with starts within 1 ms. A missing
or ambiguous match raises an error. For another attempt, reread the MiniSEED:
association requires fresh `stats.geocsv` and `stats.coordinates` destinations.

These small GeoCSV subsets are demonstration fixtures. Use complete histories
for research; omitted records could affect uniqueness. See the
[schema conversion and source mapping](../data/fixtures/schema-1.0.0/README.md)
and [original waveform provenance](../data/fixtures/association/README.md).

## 2. Associate a Stream

ObsPy can read the three included MiniSEED files for this float using a wildcard.
The same call associates every trace in the Stream:

```python
stream = read_waveforms(str(example_dir / "*/*.mseed"))
geocsv.associate(stream, tables)
for item in stream:
    print(item.id, item.stats.geocsv.source_record_index)
```

If any match or required projection fails, the whole Stream is left unchanged.

## 3. Associate a clipped window

By default, a clipped trace fails the original start/count match. Opt in to
`allow_first_segment=True` to use the source segment containing its first sample:

```python
window = read_waveforms(str(waveform_path))[0]
window.trim(starttime=window.stats.starttime + 1,
            endtime=window.stats.endtime - 1)
geocsv.associate(window, tables, allow_first_segment=True)
print(window.stats.geocsv.association.type)  # anchor_segment
```

The source must cover every retained waveform sample. The attached position
remains the source segment's first-sample position, adopted for the window
under the MERMAID negligible-drift convention. Clip or combine waveforms before
association; later waveform edits do not refresh the attachment.

## 4. Associate a combined window

This real P0045 example explicitly merges two overlapping original segments
with ObsPy, taking the later trace's values in the overlap. This is a processing
choice, not a reconstruction of archive lineage. The
[fixture notes](../tests/fixtures/association/P0045_20220115/README.md) record
the sample placement and source provenance.

```python
combined_dir = root / "tests/fixtures/association/P0045_20220115"
combined = read_waveforms(str(combined_dir / "*.mseed"))
combined.merge(method=1, interpolation_samples=0, misalignment_threshold=0)
combined_tables = geocsv.read(root / "data/fixtures/schema-1.0.0/P0045/P0045.geocsv")
geocsv.associate(combined, combined_tables, allow_first_segment=True)
print(combined[0].stats.geocsv.association.type)  # anchor_segment
print(combined[0].stats.geocsv.association.coverage_segments)
```

The final window must have a unique containing anchor and complete source-grid
coverage. Overlapping ranges count once. Association performs no merge itself.

For optional `create_sac_header=True` and writing with ObsPy, see the
[SAC tutorial](04_write-sac.md). Detailed tolerances, report fields, and projection
rules are in the [association reference](../docs/obspy-association.md).
