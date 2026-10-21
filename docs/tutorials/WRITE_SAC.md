# Write associated waveforms to SAC

`geocsv.write_sac(trace, path)` writes one already-associated MiniSEED-derived
waveform to a new binary SAC file and returns `None`. It fills receiver
latitude, longitude, approximate depth when available, and the adopted
sea-level elevation. The input trace is unchanged. The companion files
[`WRITE_SAC.md`](WRITE_SAC.md) and [`WRITE_SAC.ipynb`](WRITE_SAC.ipynb) contain
the same prose and Python examples in the same order. This tutorial is
standalone; it uses tracked real-data fixtures and runs offline.

From the repository root, activate your existing environment and install
ObsPy support:

```bash
source .venv/bin/activate
python -m pip install '.[obspy]'
```

See the [installation guide](../INSTALLATION.md) if you need an environment.
ObsPy 1.5.1 or newer is required to call `associate` or `write_sac`; importing
the package and fetching or reading GeoCSV do not require it. For notebooks:

```bash
python -m pip install jupyterlab ipykernel
python -m jupyterlab docs/tutorials/WRITE_SAC.ipynb
```

Select this repository's `.venv` kernel and run top to bottom. Python blocks
also run in order from a Python prompt. Start in the repository root, `docs/`,
or `docs/tutorials/`. Examples write into a temporary directory, removed at
the end; replace those output paths with your own existing directory to keep
research outputs.

## 1. Associate one original segment and write it

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import json

import numpy as np
import pandas as pd
from obspy import Stream, read as read_waveforms
from obspy.io.sac import SACTrace
from mermaid import geocsv

root = Path.cwd()
if root.name == "tutorials":
    root = root.parent.parent
elif root.name == "docs":
    root = root.parent
fixtures = root / "data" / "fixtures" / "association"
manifest = json.loads((fixtures / "manifest.json").read_text())
example = manifest["examples"][0]  # A real DET.WLT2 segment from P0030.
subset_paths = {item["path"]: item["subset"]["path"]
                for item in manifest["geocsv"]}
trace, = read_waveforms(str(fixtures / example["mseed"]))
tables = geocsv.read(fixtures / subset_paths[example["geocsv"]])
geocsv.associate(trace, tables, time_tolerance=0.001)
assert trace.stats.geocsv.association.type == "single_segment"

workspace = TemporaryDirectory(prefix="geocsv-sac-")
output_dir = Path(workspace.name)
output = output_dir / "associated.sac"
before = trace.copy()
assert geocsv.write_sac(trace, output) is None
assert output.is_file()
assert trace.stats == before.stats
np.testing.assert_array_equal(trace.data, before.data)
assert "sac" not in trace.stats
print(output)
```

This P0030 waveform starts 349 microseconds later than its millisecond-rendered
GeoCSV time, so association explicitly allows 1 ms. The default association
tolerance remains 100 microseconds; see the [association tutorial](ASSOCIATE.md).
Writing uses the native waveform timing, not the rounded GeoCSV time.

Use complete source histories for research. These tracked subsets preserve
original header and selected record bytes, nearby candidates, and measurement
context, but cannot establish uniqueness across omitted history records.
The [fixture provenance](../../data/fixtures/association/README.md) records
hashes and mappings to complete-history record indices.

## 2. Inspect the geographic headers and their meaning

```python
written = SACTrace.read(str(output))
source = trace.stats.geocsv
assert written.stla == np.float32(source.Latitude)
assert written.stlo == np.float32(source.Longitude)
assert written.stel == 0.0
assert written.stdp == np.float32(source.WaterPressure / 100)
for key in ("stla", "stlo", "stdp", "stel"):
    print(key, getattr(written, key))
```

| SAC header | Meaning and source |
| --- | --- |
| `stla` | Attached `Latitude`, declared in `degrees_north`; finite and within [-90, 90]. |
| `stlo` | Attached `Longitude`, declared in `degrees_east`; finite and within [-180, 180]. |
| `stdp` | Attached `WaterPressure` in `mbar`, divided by 100; nonnegative approximate depth in metres. |
| `stel` | Zero metres, the adopted sea-level reference; no geoid model. |

The pressure conversion reproduces automaid's convention: 100 mbar = 1 dbar,
treated as approximately 1 metre of depth, positive downward. It is not a
physical pressure-to-depth calculation. No latitude-dependent correction,
density model, or additional pressure correction is applied. Latitude and
longitude describe the interpolated receiver position at the first sample;
they are not averages over the waveform. Pressure is the matched event's
source value, not a reconstructed depth trajectory.

All geographic values and declared units come from `stats.geocsv` and its
immutable dataset metadata. The writer never reopens GeoCSV, reads
`stats.coordinates`, or inherits values from an existing `stats.sac`. It
constructs a fresh `SACTrace` with `keep_sac_header=False`. Existing containers
on the input trace remain untouched.

ObsPy supplies ordinary waveform identity, sampling, timing, calibration
metadata, and default SAC headers. Samples are not scaled or calibrated.
Output is little-endian binary SAC, with float32 samples and floating headers.
Integer samples outside the exactly representable float32 range can lose
precision. Export requires finite real samples. Overflow and nonzero values
that would become zero in float32 storage raise `ValueError` before file
creation; the same storage checks apply to depth, sample interval, and
calibration. Identity codes must fit eight ASCII bytes, have no surrounding
whitespace, and not equal the SAC undefined token `-12345`.
SAC timing also has finite precision and does not guarantee
preservation of UTC nanoseconds. GeoCSV row provenance is not serialized into
SAC; retain the associated trace or source records when you need it.

## 3. Compare with an independently read automaid SAC file

Only now open the paired SAC reference. It never supplies input values or
matching hints to association or writing.

```python
reference = SACTrace.read(str(fixtures / example["sac"]))
for key in ("stla", "stlo"):
    expected = getattr(reference, key)
    tolerance = 0.5e-6 + abs(float(np.spacing(np.float32(expected))))
    assert abs(getattr(written, key) - expected) <= tolerance
assert written.stel == reference.stel
assert written.stdp == reference.stdp
np.testing.assert_array_equal(written.data, trace.data.astype(np.float32))
np.testing.assert_array_equal(written.data, reference.data)
assert written.npts == trace.stats.npts == reference.npts
assert written.delta == np.float32(trace.stats.delta)

reopened = written.to_obspy_trace(round_sampling_interval=False)
original_sac = reference.to_obspy_trace(round_sampling_interval=False)
assert reopened.id == trace.id == original_sac.id
assert abs(reopened.stats.starttime.ns - trace.stats.starttime.ns) <= 1000
assert abs(reopened.stats.starttime.ns - original_sac.stats.starttime.ns) <= 1000
```

GeoCSV coordinates have six decimal places; comparison allows half a decimal
unit plus one float32 spacing at the reference coordinate. Depth agrees at
float32 precision for the tracked DET examples. The 1 microsecond timing
allowance above is a fixture comparison tolerance, not a general SAC accuracy
guarantee. Compare absolute first-sample times: equivalent SAC files can split
time differently between reference-time fields and the relative `b` header.

This is a comparison of the four geographic headers and waveform content,
identity, count, interval and start time. It does not assert whole-header or
byte-for-byte equivalence. Automaid also writes instrument, orientation,
calibration and trigger information that this geographic exporter does not
reconstruct. In particular, the native MiniSEED calibration metadata may differ
from automaid's SAC `scale`.

## 4. Export several traces, including REQ with missing pressure

Each call takes one Trace and one explicit path. Loop over an associated
Stream and choose distinct filenames; there is no implicit naming scheme or
batch transaction. Earlier files remain if a later export fails.

```python
request_example = next(item for item in manifest["examples"]
                       if item["group"].startswith("REQ."))
request, = read_waveforms(str(fixtures / request_example["mseed"]))
request_tables = geocsv.read(fixtures / subset_paths[request_example["geocsv"]])
geocsv.associate(request, request_tables, time_tolerance=0.001)
assert request.stats.geocsv.DataQuality == "D"
assert pd.isna(request.stats.geocsv.WaterPressure)

batch = Stream([trace, request])
for index, item in enumerate(batch):
    geocsv.write_sac(item, output_dir / f"segment-{index}.sac")
request_sac = SACTrace.read(str(output_dir / "segment-1.sac"))
assert request_sac.stla is not None and request_sac.stlo is not None
assert request_sac.stdp is None
request_reference = SACTrace.read(str(fixtures / request_example["sac"]))
assert request_reference.stdp is None
```

REQ events lack acquisition pressure in the current MERMAID construction.
Missing pressure is accepted for source `DataQuality="D"`, the REQ convention;
`stdp` remains SAC's undefined value (-12345 on disk, `None` through SACTrace,
and an absent `stats.sac.stdp` when read as an ObsPy Trace). Latitude and
longitude are still required and `stel` is still zero. Missing DET pressure
raises `ValueError`. Source quality identifies this exception; native MiniSEED
quality does not override it and is not used to infer depth. When pressure is
present, its declared units must be mbar even for REQ records.

## 5. Handle existing files and export a clipped combined window

Output paths must not exist; parent directories must already exist. All input
validation and SAC construction finish before exclusive file creation.
Invalid inputs create no output. Filesystem errors propagate; an I/O failure
after creation can leave a partial file.

```python
saved_bytes = output.read_bytes()
try:
    geocsv.write_sac(trace, output)
except FileExistsError as error:
    print(error)
else:
    raise AssertionError("Expected overwrite refusal")
assert output.read_bytes() == saved_bytes
```

An `anchor_segment` association retains one source anchor for a clipped or
combined window. Under the user's MERMAID negligible-drift convention, its
STLA/STLO/STDP/STEL are valid for the entire window. Missing REQ pressure stays
undefined; later rows never fill it. Both association types can be exported.
The source row retains its original start/count/rate and does not become an account
of every contributing acquisition.

The following real P0045 example merges two original request segments on the
first segment's sample grid, takes later values in their overlap, and allows
25 ms source-grid alignment. These are explicit demonstration choices, not a
reconstruction of acquisition lineage. The [association tutorial](ASSOCIATE.md)
explains the source ranges, 13-sample overlap, and approximately 24.8 ms grid
shift. No gap filling is used.

```python
merge_dir = root / "tests" / "fixtures" / "association" / "P0045_20220115"
segments = Stream()
for path in sorted(merge_dir.glob("*.mseed")):
    segments += read_waveforms(str(path))
segments.merge(method=1, interpolation_samples=0, misalignment_threshold=0)
merged, = segments
# Clip before association; retain a first sample inside the first source segment.
merged.trim(starttime=merged.stats.starttime + 1,
            endtime=merged.stats.endtime - 1)
merged_tables = geocsv.read(root / "tests" / "fixtures" / "geocsv" / "P0045.geocsv")
geocsv.associate(merged, merged_tables, time_tolerance=0.025, allow_first_segment=True)
assert merged.stats.geocsv.association.type == "anchor_segment"
assert merged.stats.npts < 45683
assert merged.stats.geocsv.SampleCount == 9696
assert merged.stats.geocsv.association.waveform.sample_count == merged.stats.npts
assert merged.stats.geocsv.association.waveform_start_offset_seconds > 0.9
merged_path = output_dir / "merged.sac"
geocsv.write_sac(merged, merged_path)
merged_sac = SACTrace.read(str(merged_path))
assert merged_sac.stla == np.float32(merged.stats.geocsv.Latitude)
assert merged_sac.stlo == np.float32(merged.stats.geocsv.Longitude)
assert merged_sac.stel == 0
assert merged_sac.stdp is None  # The REQ anchor has no pressure.
np.testing.assert_array_equal(merged_sac.data, merged.data.astype(np.float32))
workspace.cleanup()
```

Associate the final downloaded/clipped/combined window before export. The writer
checks identity, initial start-time offset, association-time waveform sample
count, and source rate agreement under association's 0.01 Hz threshold. Original
source SampleCount must equal waveform count only for `single_segment`. Source
coverage was checked at association; the writer does not reopen source files.
Later count/start changes require a fresh association on an unassociated trace.
It also rejects empty data and masked gaps. These checks cannot detect all
sample transformations, including filtering or changes within the rate
threshold; they do not prove an unchanged processing history. A `single_segment`
label is not refreshed by later waveform processing.

## Verification and fixture coverage

The test suite exports all 18 manifest-listed paired waveforms, spanning
DET.WLT2, DET.WLT5, REQ.WLT3, REQ.WLT4, REQ.WLT5 and REQ.RAW. It compares
geographic headers against independent SAC references and verifies waveform
round trips and no input mutation. Other product groups have no paired
examples in this collection; see the manifest's population counts. The P0045
window above exercises actual `anchor_segment` export after clipping both ends. Synthetic tests cover
invalid units, missing DET pressure, source-quality independence, destination
conflicts, and source-field validation; these are distinct from the real-data
comparisons.

Implementation references: ObsPy's documented
[SACTrace conversion](https://docs.obspy.org/packages/autogen/obspy.io.sac.sactrace.SACTrace.from_obspy_trace.html)
and [writer](https://docs.obspy.org/packages/autogen/obspy.io.sac.sactrace.SACTrace.write.html).
Source inspection used `/Users/jdsimon/programs/obspy/` commit
`50033e1daf95233cd4f30e95a49c37fd50be2ccd`, including SAC conversion, headers,
array writing and nearby tests; the repository environment separately uses
ObsPy 1.5.1. The pressure convention follows automaid's
`scripts/events.py` and `scripts/geocsv.py`.

## Association report compatibility

Version 0.20.0 requires the nested `stats.geocsv.association` report created by
current association. Its `.type` is `single_segment` or `anchor_segment`;
`.waveform` records identity, start/end time, rate and count. SAC export checks
identity/start/count/rate against this snapshot and retains the source rate and
unit checks. A later rate change is rejected even when it remains within the
source-rate tolerance. Reassociate the final waveform on an unassociated copy.
The report's coverage segments and alignment diagnostics stay in memory and
are not serialized into SAC. See the
[report schema](../OBSPY_ASSOCIATION.md#association-report).
