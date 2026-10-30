# Download P0006 waveforms and verify SAC export

Fetch P0006 GeoCSV metadata, download three known detections from EarthScope
with ObsPy, associate each waveform, and save and compare its SAC export with
independent MiniSEED/SAC fixtures. Start with one detection, then repeat the
workflow for two more.

Companions: [Markdown](05_earthscope.md) · [Notebook](05_earthscope.ipynb).

## Setup

From the cloned repository, activate your environment and install ObsPy support:

```bash
source .venv/bin/activate
python -m pip install '.[obspy]'
```

See [installation and notebook setup](../docs/installation.md) if needed. Run the
Python examples in order from the repository root, `docs/`, or `tutorials/`.
Internet access is required for the hosted GeoCSV metadata and EarthScope
waveform downloads. Tests replay saved metadata subsets and responses offline. Paired
reference files are included in the repository; see their
[provenance manifest](../data/fixtures/P0006/waveforms/manifest.json) and
[fixture notes](../data/fixtures/P0006/waveforms/README.md).

The examples use three isolated DET segments with complete pressure metadata:

| Source record index | Source start UTC | Samples | Recorded download minus original start (µs) |
| ---: | --- | ---: | ---: |
| 98 | 2018-06-29T17:07:31.205624Z | 4,832 | −6 |
| 169 | 2018-07-12T06:51:58.293418Z | 4,448 | 0 |
| 239 | 2018-07-15T22:48:15.969095Z | 5,440 | −1 |

These are zero-based data-record indices in the complete published P0006
history, pinned below. The migrated producer supplies six-digit source epochs;
display width does not establish clock accuracy. All three associate as
`single_segment`. The [association tutorial](03_associate.md#3-associate-a-clipped-window)
demonstrates `anchor_segment` and a
[combined window](03_associate.md#4-associate-a-combined-window).

## 1. Download the matching GeoCSV snapshot

Download the published schema 1.0.0 snapshot directly. Pinning keeps the record
indices and source values reproducible even if testing latest changes.
`output_dir=None` downloads into memory. Passing fetch results directly to
`read` preserves download provenance.

```python
from mermaid import geocsv

base_url = "https://bathymetrix.com/geocsv/testing/"
release = "2026-10-30T18:08:32.316000Z"
downloads = geocsv.fetch("P0006", base_url=base_url, release=release,
                         output_dir=None)
tables = geocsv.read(downloads)
records = tables[0]
print(downloads[0].provenance.release_id)
print(records.loc[[98, 169, 239], ["Time", "SampleCount"]])
```

## 2. Download and associate the first detection

Use EarthScope's HTTPS service directly. The one-second margin around the
source segment requests its complete first and last samples despite the
GeoCSV timestamp/rate precision. It is a retrieval margin, not an association
tolerance. `Time` is already corrected; do not apply `TimeCorrectionApplied`
again. Leave quality selection unspecified.

`filename` saves the raw service response before ObsPy's client parsing and
trimming. Read those bytes separately. MiniSEED reading can assemble records
into traces even without an explicit merge. For these requests, the returned
trace has exactly the original segment's sample count and start within 1 ms.
No clipping, filling, merging, or resampling is needed.

```python
from pathlib import Path
from tempfile import mkdtemp

from obspy import UTCDateTime, read as read_waveforms
from obspy.clients.fdsn import Client
from obspy.io.sac import SACTrace

output_dir = Path(mkdtemp(prefix="mermaid-earthscope-"))
print(f"Downloads and SAC exports: {output_dir}")
client = Client("https://service.earthscope.org", timeout=30)

row = records.loc[98]
start = UTCDateTime(row["Time"].isoformat())
last_sample = start + (int(row["SampleCount"]) - 1) / float(row["SampleRate"])
raw_path = output_dir / "P0006_record_98.mseed"
client.get_waveforms(
    network=row["Network"], station=row["Station"],
    location=row["Location"], channel=row["Channel"],
    starttime=start - 1, endtime=last_sample + 1,
    filename=str(raw_path),
)
trace, = read_waveforms(str(raw_path), format="MSEED")
print(trace)

geocsv.associate(trace, tables, create_sac_header=True)
assert trace.stats.geocsv.source_record_index == 98
assert trace.stats.geocsv.association.type == "single_segment"
print(trace.stats.geocsv.association.type)
```

The single-trace unpacking and association checks intentionally fail if a
future service response no longer represents this original segment. The
source history includes nearby candidates; no rows are discarded to force a
match. The [July 6 REQ discrepancy](../docs/open-questions.md#p0006-july-6-req-response-det-start-with-req-count)
is excluded because its returned start does not match its original row and the
containing-anchor candidates are ambiguous against this history.

Association uses MiniSEED identity, timing, rate, and count plus the fetched
GeoCSV records. SAC references supply no matching hints or missing values.
`create_sac_header=True` creates fresh SAC headers with four GeoCSV station
fields; the waveform samples remain uncalibrated counts.

## 3. Save and reopen SAC

Use ObsPy's writer with its default `keep_sac_header=True` to preserve the
projected station fields. `SACTrace` exposes the stored sample interval without
the default ObsPy Trace reader's interval rounding.

```python
sac_path = output_dir / "P0006_record_98.sac"
trace.write(str(sac_path), format="SAC")
written = SACTrace.read(str(sac_path))
print(sac_path)
```

SAC stores waveform samples and floating headers at float32 precision. The
station fields are `stla`/`stlo` in degrees north/east, `stel = 0` metres at the
adopted sea-level reference, and `stdp = WaterPressure / 100` in approximate
metres positive downward for the MERMAID receiver (station). Pressure is in
mbar; 100 mbar corresponds to approximately 1 m of station depth under the
MERMAID convention. Earthquake-source metadata and `ev*` projections are
outside package scope. All three DET examples have pressure. Missing REQ pressure would remain undefined (`SACTrace.stdp is None`,
with the SAC undefined sentinel stored on disk); it must not be borrowed from
another record.

## 4. Compare against the original MiniSEED and SAC pair

Read the reference files only after association and export. The function below
checks identity, count, absolute first-sample time, interval, waveform samples,
and the four supported station fields. It is reused for the next two detections.

The recorded download-minus-original start offsets above are checked exactly
in integer nanoseconds. Their cause is not established. They are observations
for these fixtures, not timing corrections: the downloaded times and the
GeoCSV values remain unchanged. The independent SAC references retain the
original starts.

MiniSEED samples must equal the independent original exactly. Exported samples
must equal both the downloaded samples converted to float32 and the independent
SAC samples. Latitude/longitude must equal the GeoCSV values rounded to float32;
the independent SAC comparison allows one float32 representable step (one ULP)
because the calculations can round differently. Depth/elevation must agree
exactly. The exported SAC start must agree with the downloaded start within
1 microsecond and retain the recorded offset from the reference SAC start
within 1 microsecond. This is a storage allowance for these fixture comparisons,
not a general SAC timing guarantee. Compare absolute start times,
since equivalent SAC files may split time differently between their reference
time and relative `b` header.

```python
import numpy as np

root = Path.cwd()
if root.name in {"docs", "tutorials"}:
    root = root.parent
fixtures = root / "data/fixtures/P0006/waveforms"


def compare_with_fixtures(waveform, exported, basename, start_offset_ns):
    original, = read_waveforms(str(fixtures / f"{basename}.mseed"))
    reference = SACTrace.read(str(fixtures / f"{basename}.sac"))
    reopened = exported.to_obspy_trace(round_sampling_interval=False)
    reference_trace = reference.to_obspy_trace(round_sampling_interval=False)

    assert waveform.id == original.id == reopened.id == reference_trace.id
    assert waveform.stats.npts == original.stats.npts == exported.npts == reference.npts
    assert waveform.stats.starttime.ns - original.stats.starttime.ns == start_offset_ns
    assert waveform.stats.sampling_rate == original.stats.sampling_rate
    assert abs(reopened.stats.starttime.ns - waveform.stats.starttime.ns) <= 1000
    reference_offset = reopened.stats.starttime.ns - reference_trace.stats.starttime.ns
    assert abs(reference_offset - start_offset_ns) <= 1000
    assert exported.delta == np.float32(waveform.stats.delta) == reference.delta
    np.testing.assert_array_equal(waveform.data, original.data)
    np.testing.assert_array_equal(exported.data, waveform.data.astype(np.float32))
    np.testing.assert_array_equal(exported.data, reference.data)

    for key, field in (("stla", "Latitude"), ("stlo", "Longitude")):
        assert getattr(exported, key) == np.float32(waveform.stats.geocsv[field])
        np.testing.assert_array_max_ulp(
            np.float32(getattr(exported, key)),
            np.float32(getattr(reference, key)), maxulp=1,
        )
    assert exported.stel == reference.stel == 0.0
    assert exported.stdp == np.float32(waveform.stats.geocsv.WaterPressure / 100)
    assert exported.stdp == reference.stdp


compare_with_fixtures(
    trace, written, "20180629T170731.06_5B3F1904.MER.DET.WLT5", start_offset_ns=-6000,
)
print("Record 98: fixture comparisons passed")
```

These comparisons do not imply whole-header or byte equality. Instrument,
orientation, calibration, and trigger fields in the original SAC file are
outside the four GeoCSV mappings. EarthScope quality flags are independent
evidence: the saved responses have M while original DET MiniSEED and GeoCSV
have Q. Neither flag is used to select an association, and M does not establish
original acquisition lineage.

## 5. Repeat for two more known P0006 detections

Use a fresh MiniSEED trace for every association. This loop repeats the same
download, association, export, and independent comparisons for July 12 and
July 15. Association uses the complete downloaded P0006 history.

```python
additional_examples = [
    (169, "20180712T065158.06_5B4748AE.MER.DET.WLT5", 0),
    (239, "20180715T224815.06_5B4C1D4F.MER.DET.WLT5", -1000),
]
for record_index, basename, start_offset_ns in additional_examples:
    row = records.loc[record_index]
    start = UTCDateTime(row["Time"].isoformat())
    last_sample = start + (int(row["SampleCount"]) - 1) / float(row["SampleRate"])
    raw_path = output_dir / f"P0006_record_{record_index}.mseed"
    client.get_waveforms(
        network=row["Network"], station=row["Station"],
        location=row["Location"], channel=row["Channel"],
        starttime=start - 1, endtime=last_sample + 1,
        filename=str(raw_path),
    )
    waveform, = read_waveforms(str(raw_path), format="MSEED")
    geocsv.associate(waveform, tables, create_sac_header=True)
    assert waveform.stats.geocsv.source_record_index == record_index
    assert waveform.stats.geocsv.association.type == "single_segment"
    sac_path = output_dir / f"P0006_record_{record_index}.sac"
    waveform.write(str(sac_path), format="SAC")
    exported = SACTrace.read(str(sac_path))
    compare_with_fixtures(waveform, exported, basename, start_offset_ns)
    print(f"Record {record_index}: fixture comparisons passed; {sac_path}")
```

The new output directory retains all three raw downloads and SAC exports.
Rerunning the tutorial creates another directory; rerunning a write cell
overwrites that cell's output file. SAC does not preserve the complete GeoCSV
attachment. Keep the associated traces and fetched records in memory for
association provenance, and retain raw responses to document the download.

Live services can change availability, record selection, timing, or
segmentation. A failed assertion needs investigation; do not replace the
reference fixtures, adjust timing, or relax comparisons merely to obtain a
pass. Ordinary tutorial tests replay the recorded responses and serve the
metadata locally. They establish example correctness without depending on
current network availability; live execution is a separate check.

Service behavior: [EarthScope dataselect help](https://service.earthscope.org/fdsnws/dataselect/docs/1/help/)
and [ObsPy `get_waveforms`](https://docs.obspy.org/packages/autogen/obspy.clients.fdsn.client.Client.get_waveforms.html).
The client filename/read boundary and nearby tests were inspected in the
read-only ObsPy checkout at `50033e1daf95233cd4f30e95a49c37fd50be2ccd`.
Live downloads and comparisons were checked on 2026-10-30 with the repository's
separately installed ObsPy 1.5.1.
