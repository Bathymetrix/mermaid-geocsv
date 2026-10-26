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

See [installation and notebook setup](../INSTALLATION.md) if needed. Run the
Python examples in order from the repository root, `docs/`, or `docs/tutorials/`.
These examples use included fixtures and run offline.

## 1. Read MiniSEED and create SAC headers

```python
from pathlib import Path
from tempfile import TemporaryDirectory
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
trace = read_waveforms(str(waveform_path))[0]
tables = geocsv.read(example_dir / "association_subset.geocsv")
geocsv.associate(trace, tables, create_sac_header=True)
print(trace.stats.sac)
```

`create_sac_header=True` requires an absent `stats.sac`. It creates ObsPy's
standard headers and adds four station location fields:

| Header | Value |
| --- | --- |
| `stla` | Source latitude in degrees north |
| `stlo` | Source longitude in degrees east |
| `stel` | Adopted sea-level reference, 0 metres |
| `stdp` | Source pressure in mbar divided by 100, an approximate depth in metres |

The pressure conversion follows the MERMAID convention rather than a physical
pressure-to-depth model. Missing REQ pressure stays undefined; missing DET
pressure raises. Waveform samples remain raw counts.

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
For a Stream, use `stream.write(..., format="SAC")`; ObsPy writes one file per trace.

Associate the final waveform after clipping or merging. Later edits do not
refresh the headers. See the [association tutorial](ASSOCIATE.md) and the
[detailed SAC reference](../development/WRITE_SAC.md) for missing-value rules,
precision, independent SAC comparisons, and export checks.
