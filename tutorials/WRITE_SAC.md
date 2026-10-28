# Write an associated waveform as SAC

Create station location headers with `geocsv.associate`, then write the
waveform with ObsPy.

Companions: [Markdown](WRITE_SAC.md) · [Notebook](WRITE_SAC.ipynb).

## Setup

From the cloned repository, activate your environment and install ObsPy support:

```bash
source .venv/bin/activate
python -m pip install '.[obspy]'
```

See [installation and notebook setup](../docs/INSTALLATION.md) if needed. Run the
Python examples in order from the repository root, `docs/`, or `tutorials/`.
These examples use included fixtures and run offline.

## 1. Read MiniSEED and create SAC headers

```python
from pathlib import Path
from tempfile import TemporaryDirectory
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
trace = read_waveforms(str(waveform_path))[0]
tables = geocsv.read(example_dir / "association_subset.geocsv")
geocsv.associate(trace, tables, create_sac_header=True)
print(trace.stats.sac)
```

`create_sac_header=True` requires an absent `stats.sac`. It creates ObsPy's
standard headers and adds station latitude, longitude, the adopted sea-level
reference, and approximate pressure-derived depth. The [SAC mapping](../docs/SAC.md#geographic-mapping)
defines units and the missing-REQ-pressure exception. Samples remain raw counts.

## 2. Write and reopen a SAC file

This example uses a temporary directory that is removed when the block ends.
Use your own output path to keep the file.

```python
with TemporaryDirectory() as directory:
    output = Path(directory) / "example.sac"
    trace.write(str(output), format="SAC")
    reopened = read_waveforms(str(output))[0]
    print(reopened)
    print(reopened.stats.sac.stla, reopened.stats.sac.stlo)
```

Keep ObsPy's default `keep_sac_header=True` to preserve the projected headers.
SAC stores samples and floating headers at float32 precision; it does not
preserve the full GeoCSV attachment. ObsPy overwrites existing output filenames.

## 3. Write a Stream

Read the three original MiniSEED examples for this float into a fresh Stream,
then create headers for the whole batch. ObsPy writes one numbered SAC file
per trace when given a single output filename:

```python
stream = read_waveforms(str(example_dir / "*/*.mseed"))
geocsv.associate(stream, tables, create_sac_header=True)
with TemporaryDirectory() as directory:
    stream.write(str(Path(directory) / "segment.sac"), format="SAC")
    written_names = sorted(path.name for path in Path(directory).glob("*.sac"))
    print(written_names)  # segment01.sac, segment02.sac, segment03.sac
```

Associate the final waveform after clipping or merging. Later edits do not
refresh the headers. See the [association tutorial](ASSOCIATE.md) and the
[SAC reference](../docs/SAC.md) for missing-value rules,
precision, independent SAC comparisons, and export checks.
