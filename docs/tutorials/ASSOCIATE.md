# Associate GeoCSV metadata with a waveform

`geocsv.associate` attaches the matching GeoCSV event record and receiver
coordinates to an ObsPy Trace or Stream. These examples use included MiniSEED
and GeoCSV fixtures and run offline.

Companions: [Markdown](ASSOCIATE.md) · [Notebook](ASSOCIATE.ipynb).

## Setup

From the cloned repository, activate your environment and install ObsPy support:

```bash
source .venv/bin/activate
python -m pip install '.[obspy]'
```

See [installation and notebook setup](../INSTALLATION.md) if needed. Run the
Python examples in order from the repository root, `docs/`, or `docs/tutorials/`.

## 1. Read and associate one MiniSEED trace

```python
from pathlib import Path
from obspy import read as read_waveforms
from mermaid import geocsv

root = Path.cwd()
if root.name == "tutorials":
    root = root.parent.parent
elif root.name == "docs":
    root = root.parent

example_dir = root / "data/fixtures/association/452.020-P-0030"
waveform_path = (
    example_dir / "0009_20210528-04h30m10s"
    / "20210528T053250.0030_60B08BB3.MER.DET.WLT2.mseed"
)
tables = geocsv.read(example_dir / "association_subset.geocsv")
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
[fixture provenance](../../data/fixtures/association/README.md).

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

For optional `create_sac_header=True` and writing with ObsPy, see the
[SAC tutorial](WRITE_SAC.md). Detailed tolerances, report fields, and projection
rules are in the [association reference](../OBSPY_ASSOCIATION.md); extended
batch, failure, and merged-window examples are in the
[development notes](../development/ASSOCIATE.md).
