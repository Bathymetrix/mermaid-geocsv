# Create station location headers and write SAC with ObsPy

`geocsv.associate(..., create_sac_header=True)` creates fresh `stats.sac`
headers using ObsPy's default conversion, then adds station latitude (`stla`),
longitude (`stlo`), adopted sea-level elevation (`stel`), and approximate depth
(`stdp`) from the documented GeoCSV mapping. `stats.sac` must be absent.
The default False leaves existing SAC headers untouched. Write the associated
Trace or Stream using ObsPy's `write(..., format="SAC")` method.

The companion files [`WRITE_SAC.md`](WRITE_SAC.md) and
[`WRITE_SAC.ipynb`](WRITE_SAC.ipynb) contain the same prose and Python examples
in the same order. This tutorial is standalone; it uses tracked real-data
fixtures and runs offline. ObsPy owns file writing and storage behavior;
`mermaid-geocsv` does not provide a writer.

From the repository root, activate your existing environment and install
ObsPy support:

```bash
source .venv/bin/activate
python -m pip install '.[obspy]'
```

See the [installation guide](../INSTALLATION.md) if you need an environment.
ObsPy 1.5.1 or newer is required to call `associate`; importing
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
geocsv.associate(trace, tables, create_sac_header=True)
assert trace.stats.geocsv.association.type == "single_segment"

workspace = TemporaryDirectory(prefix="geocsv-sac-")
output_dir = Path(workspace.name)
output = output_dir / "associated.sac"
before = trace.copy()
assert trace.write(str(output), format="SAC") is None
assert output.is_file()
assert trace.stats == before.stats
np.testing.assert_array_equal(trace.data, before.data)
assert "sac" in trace.stats
print(output)
```

This P0030 waveform starts 349 microseconds later than its millisecond-rendered
GeoCSV time, within the default 1 ms association tolerance; see the [association tutorial](ASSOCIATE.md).
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

All geographic values and declared units come from the matched GeoCSV row
and its immutable dataset metadata. Association builds every requested
projection before changing any trace. It never inherits an existing SAC header,
uses another trace's location, or reads an independent SAC comparison file.
Missing required coordinates or invalid pressure/units fail the entire batch.

ObsPy's fresh-header conversion supplies ordinary identity, sampling, timing,
and defaults. Only the four station location fields receive additional GeoCSV
mappings. Native waveform Stats, calibration metadata, samples and processing
history remain unchanged. Creating `stats.sac` does not calibrate samples or
remove an instrument response. GeoCSV provides no counts-to-pressure factor.
ObsPy calls one header slot `scale` and maps `stats.calib` into it; the linked
SAC manual marks that slot UNUSED. That mapping is ObsPy behavior, not an
additional GeoCSV calibration promise.

ObsPy's default `keep_sac_header=True` preserves the projected headers when
writing. Passing `keep_sac_header=False` discards them. Binary SAC uses float32
samples and floating headers; large integers can lose precision and timing
need not preserve UTC nanoseconds. ObsPy defaults to little-endian binary SAC
and accepts its own writer options. The package does not validate a later
write, promise lossless conversion, or serialize GeoCSV row provenance.
Retain the associated trace or source records for provenance. Additional
export-time consistency and storage checks belong to the publisher's
[verification tooling](../../../mermaid-publisher/docs/geocsv/SAC_VERIFICATION.md).

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
calibration and trigger information that these four geographic mappings do not
reconstruct. In particular, the native MiniSEED calibration metadata may differ
from automaid's SAC `scale`.

## 4. Write a Stream, including REQ with missing pressure

A SAC file contains one trace. ObsPy's `Stream.write` creates one file per
trace and appends numbers when the Stream contains multiple traces. For this
two-trace example, `segment.sac` becomes `segment01.sac` and `segment02.sac`.
The package supplies no file naming or batch-writing behavior.

```python
request_example = next(item for item in manifest["examples"]
                       if item["group"].startswith("REQ."))
request, = read_waveforms(str(fixtures / request_example["mseed"]))
request_tables = geocsv.read(fixtures / subset_paths[request_example["geocsv"]])
geocsv.associate(request, request_tables, create_sac_header=True)
assert request.stats.geocsv.DataQuality == "D"
assert pd.isna(request.stats.geocsv.WaterPressure)

batch = Stream([trace, request])
batch.write(str(output_dir / "segment.sac"), format="SAC")
request_sac = SACTrace.read(str(output_dir / "segment02.sac"))
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

## 5. Control overwriting and write a clipped combined window

ObsPy overwrites an existing output filename by default. Use an exclusively
opened binary file if overwrite refusal is required; this is standard Python
file handling, not a package-managed writer. An I/O failure can leave a partial
file, and writing multiple files is not a transaction.

```python
saved_bytes = output.read_bytes()
try:
    with output.open("xb") as handle:
        trace.write(handle, format="SAC")
except FileExistsError as error:
    print(error)
else:
    raise AssertionError("Expected exclusive-open refusal")
assert output.read_bytes() == saved_bytes
```

An `anchor_segment` association retains one source anchor for a clipped or
combined window. Under the user's MERMAID negligible-drift convention, its
STLA/STLO/STDP/STEL are valid for the entire window. Missing REQ pressure stays
undefined; later rows never fill it. Both association types can be exported.
The source row retains its original start/count/rate and does not become an account
of every contributing acquisition.

The following real P0045 example merges two original request segments on the
first segment's sample grid and takes later values in their overlap. Association
uses unique half-sample source-grid placement, independently of the absolute
start/containment tolerance. The merge is a demonstration choice, not a
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
merged_tables = geocsv.read(root / "data" / "fixtures" / "P0045" / "P0045.geocsv")
geocsv.associate(merged, merged_tables, allow_first_segment=True,
                 create_sac_header=True)
assert merged.stats.geocsv.association.type == "anchor_segment"
assert merged.stats.npts < 45683
assert merged.stats.geocsv.SampleCount == 9696
assert merged.stats.geocsv.association.waveform.sample_count == merged.stats.npts
assert merged.stats.geocsv.association.waveform_start_offset_seconds > 0.9
merged_path = output_dir / "merged.sac"
merged.write(str(merged_path), format="SAC")
merged_sac = SACTrace.read(str(merged_path))
assert merged_sac.stla == np.float32(merged.stats.geocsv.Latitude)
assert merged_sac.stlo == np.float32(merged.stats.geocsv.Longitude)
assert merged_sac.stel == 0
assert merged_sac.stdp is None  # The REQ anchor has no pressure.
np.testing.assert_array_equal(merged_sac.data, merged.data.astype(np.float32))
workspace.cleanup()
```

Associate the final downloaded/clipped/combined window before writing.
Association checks its identity, start, rate, count and source coverage at that
time. Later trimming, resampling, merging or manual edits do not refresh
`stats.geocsv`, `stats.coordinates` or the station location projection.
ObsPy's writer does not revalidate GeoCSV association. A retained association
label does not establish current coverage or an unchanged processing history.
The publisher retains separate checks on the final waveform and its SAC export.

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
and [Trace writer](https://docs.obspy.org/packages/autogen/obspy.core.trace.Trace.write.html)
and [Stream writer](https://docs.obspy.org/packages/autogen/obspy.core.stream.Stream.write.html).
Source inspection used `/Users/jdsimon/programs/obspy/` commit
`50033e1daf95233cd4f30e95a49c37fd50be2ccd`, including SAC conversion, headers,
array writing and nearby tests; the repository environment separately uses
ObsPy 1.5.1. The pressure convention follows automaid's
`scripts/events.py` and `scripts/geocsv.py`.

## Migration from the former package writer

Version 0.25.0 removes `geocsv.write_sac`. Request `create_sac_header=True` on
an unassociated final waveform, then use `Trace.write` or `Stream.write`.
Creating the header is part of transactional association; file writing remains
an ObsPy operation. Existing destination containers raise even when empty.
The package's former output-path protection, export-time association checks,
storage guards and stable summary calculation are retained in publisher-only
verification, rather than becoming consumer API promises. This tutorial's
four-field and waveform comparisons remain unchanged.
