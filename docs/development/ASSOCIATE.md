# Detailed association examples and fixture checks

Supporting reference for development and detailed investigation. The [short
tutorial](../tutorials/ASSOCIATE.md) and
[notebook](../tutorials/ASSOCIATE.ipynb) provide the introductory workflow.

The extended examples below preserve the scientific explanations, diagnostic
checks, and fixture coverage from the longer walkthrough. Run their Python
blocks in order from the repository root, `docs/`, or `docs/development/`,
using the [installation guide](../INSTALLATION.md). These reference pages are
independent of the tutorial notebook pairs.

## 1. Read a waveform and its GeoCSV records

Use an original processed MiniSEED waveform, with samples loaded, and the
matching float's GeoCSV history. Paired SAC fixtures are independent comparison
references; their headers do not supply association inputs or defaults.

```python
from pathlib import Path
import json

import numpy as np
from obspy import Stream, read as read_waveforms
from mermaid import geocsv

root = Path.cwd()
if root.name in {"tutorials", "development"}:
    root = root.parent.parent
elif root.name == "docs":
    root = root.parent
fixtures = root / "data" / "fixtures" / "association"
example_dir = fixtures / "452.020-P-0030"
waveform_path = (
    example_dir / "0009_20210528-04h30m10s"
    / "20210528T053250.0030_60B08BB3.MER.DET.WLT2.mseed"
)
geocsv_path = example_dir / "association_subset.geocsv"

stream = read_waveforms(str(waveform_path))
trace, = stream
tables = geocsv.read(geocsv_path)
records = tables[0]
print(stream)
print(records[["StartTime", "MethodIdentifier", "SampleCount", "SampleRate"]])
```

`geocsv.read` returns a list of DataFrames, even for one dataset. Pass that
list directly to `associate`. You can combine lists from several files with
`tables_a + tables_b`; keep the frames' original indices and GeoCSV provenance.
Concatenating frames can lose their differing pandas `attrs`.

The tracked subset retains original header and selected record bytes, nearby
candidates, and measurement context. It is sufficient for this example, but
cannot establish uniqueness across omitted history records. Use your complete
GeoCSV histories for research association. The [fixture manifest and provenance
notes](../../data/fixtures/association/README.md) describe the subset extraction.

## 2. Associate in place with the default tolerances

The public call is:

```python
help(geocsv.associate)
```

Begin with one trace and the parsed tables. The default 1 ms start tolerance
accepts this fixture; no optional input is needed.
Its signature is `associate(waveforms, records, *, time_tolerance=0.001,
allow_first_segment=False, create_sac_header=False)`. The fallback flag must be a Python bool; strings
such as `"False"` are rejected. Each trace must match exactly one `Algorithm(event):` row
under these rules:

- Network, Station, Location, and Channel (SNCL) match exactly. Only Location
  may be the known empty string `""`; no identity field may be missing.
- Zoned source start times and waveform UTC times differ by no more than the
  inclusive tolerance, in seconds. The default is 1 millisecond. Zero
  requires exact equality; `None`, negative, and nonfinite values are invalid.
- `SampleCount` equals both waveform `npts` and the number of loaded samples.
  Counts have no tolerance. Empty waveforms and masked sample gaps are rejected.
- Source `SampleRate`, declared in hertz, differs from the waveform rate by at
  most 0.00001 Hz. This is rate agreement, not physical clock accuracy.

Source timestamp spelling does not enlarge the tolerance or establish clock
accuracy. This real P0030 waveform begins **349 microseconds later** than its
millisecond-rendered GeoCSV start. The default 1 ms tolerance accepts it:

```python
original = trace.copy()
result = geocsv.associate(trace, tables)
assert result is None
assert np.array_equal(trace.data, original.data)
assert all(trace.stats[key] == value for key, value in original.stats.items())
print(trace.stats.geocsv.association.type)  # single_segment
print(trace.stats.geocsv.association.waveform_start_offset_seconds)  # 0.000349
```

The function modifies the supplied Trace or the traces inside the supplied
Stream and returns `None`. Do not assign its return value back to `stream`.
To preserve an untouched waveform, make a copy before association, as above.
Matching validates the native identity, timing, rate, and sample count; it
does not relabel the waveform, apply `TimeCorrection` again, calibrate samples,
or change processing history. Source `DataQuality` remains separate from
MiniSEED quality and is not a matching filter.

Source preflight rejects invalid event identities and duplicate complete
SNCL/UTC-time/count/rate keys across all supplied datasets, even if a waveform
would not select those rows. Distinct counts can disambiguate otherwise equal
identity/time rows. Multiple eligible rows under the actual tolerance rules
raise; multiple traces may independently match the same row.

## 3. Inspect the attachment and coordinate projection

`stats.geocsv` is a fresh ObsPy `AttribDict` containing the matched row's
original column names and values, including missing source values. Access
columns as attributes or dictionary keys:

```python
attached = trace.stats.geocsv
print(attached.MethodIdentifier)
print(attached["StartTime"])
print(attached.SampleCount, attached.SampleRate, attached.DataQuality)
print(trace.stats.mseed.dataquality)  # Separate waveform evidence.
print(trace.stats.coordinates)
```

The coordinate projection requires a complete finite latitude/longitude pair,
within [-90, 90] and [-180, 180], declared as `degrees_north` and `degrees_east`.
It copies those source values into `stats.coordinates.latitude` and
`.longitude` and adopts `.elevation = 0.0` as a sea-level reference, with no
geoid model. Zero is the same in metres and kilometres; this does not define
units for a future nonzero elevation projection. This is the interpolated
receiver position at the first sample time, rather than an average position
over the waveform. Elevation does not
represent receiver depth or infer a pressure conversion. Missing either
coordinate fails the association. By default, association leaves `stats.sac`
untouched. Set `create_sac_header=True` to create ObsPy's fresh SAC baseline
plus station latitude (`stla`), longitude (`stlo`), adopted sea-level elevation
(`stel`) and approximate depth (`stdp`). The flag must be a Python bool and
`stats.sac` must be absent. Pressure in declared mbar is divided by 100 as an
approximate depth in metres; missing REQ pressure stays SAC undefined, while
missing DET pressure raises. No additional GeoCSV-to-SAC mappings are promised.

```python
sac_trace, = read_waveforms(str(waveform_path))
geocsv.associate(sac_trace, tables, create_sac_header=True)
assert sac_trace.stats.sac.stla == sac_trace.stats.geocsv.Latitude
assert sac_trace.stats.sac.stlo == sac_trace.stats.geocsv.Longitude
assert sac_trace.stats.sac.stel == 0.0
assert sac_trace.stats.sac.stdp == sac_trace.stats.geocsv.WaterPressure / 100
```

Write with ObsPy's `sac_trace.write(path, format="SAC")`, preserving its default
`keep_sac_header=True`. Setting it to False discards the projection. The
[SAC tutorial](WRITE_SAC.md) shows `Trace.write`, `Stream.write`, precision,
and independent reference comparisons. All requested projections validate
before any trace is modified; native waveform headers and samples stay intact.

The attachment also has four association-owned keys:

| Key | Meaning |
| --- | --- |
| `dataset_index` | Zero-based position in the supplied list of DataFrames. |
| `source_record_index` | Zero-based file-wide data-record index, excluding headers/comments; does not restart for each dataset. |
| `metadata` | Immutable GeoCSV dataset metadata, including source path, units, and comments. |
| `association` | Nested ObsPy AttribDict report of the association-time waveform, coverage and alignment evidence. |

Inspect the report using either attribute or dictionary access:

```python
report = attached.association
assert report.type == "single_segment"
assert report["type"] == report.type
print(report.waveform)
segment, = report.coverage_segments
print(segment)
assert segment.sample_count == report.waveform.sample_count == trace.stats.npts
assert segment.waveform_sample_start == 0
assert segment.waveform_sample_stop == trace.stats.npts
assert report.waveform.starttime.ns == trace.stats.starttime.ns
assert report.waveform.endtime.ns == trace.stats.endtime.ns
print(report.max_sample_grid_offset)
print(report.max_sample_rate_difference)
```

`waveform` snapshots SNCL, `starttime`, `endtime`, `sampling_rate_hz` and
`sample_count`. Each coverage entry describes the full original source segment
using those same fields, plus `dataset_index`, `source_record_index`,
`source_line_number`, `waveform_sample_start` and `waveform_sample_stop`.
Source line numbers are one-based physical starting lines, counting headers,
comments and blank lines, or `None` if unavailable. Sample ranges are zero-based,
start inclusive and stop exclusive. They describe the clipped portion supporting
the waveform, while source times/count remain those of the complete segment.
All end times mean the last sample, not an exclusive window boundary.

`waveform_start_offset_seconds` is signed waveform start minus the first
coverage segment's start. A positive offset can be large for an interior
window; it is not the sample-grid error, a clock correction or an uncertainty.
`max_sample_grid_offset` records the largest absolute retained boundary-sample
time difference in `seconds`, its source dataset/record/line, and the
`waveform_sample_index`. `max_sample_rate_difference` records the largest
absolute rate difference in `hz` and its source dataset/record/line. Ties select
the first chronological segment (dataset then record index break time ties),
then its first boundary sample before its last. No input tolerances are stored.
See the [complete report definitions](../OBSPY_ASSOCIATION.md#association-report).

Coverage segments are chronological, with the geographic anchor first.
`len(report.coverage_segments)` gives their count; overlaps count once toward
coverage but may appear in multiple entries. A clipped window within one source
segment still has type `anchor_segment`. These are coverage evidence, not proof
of how a waveform was concatenated. The report is an independent snapshot;
later processing does not refresh it. Strict matching still checks only
start/count/rate, without adding an endpoint acceptance check.

Source columns colliding with the four attachment keys or with `AttribDict`
attributes and methods raise before mutation; they are never silently renamed
or discarded. Version 0.20.0 replaces the former string association labels and
moves the former top-level count/start-difference fields into this report; no
compatibility aliases are retained.

## 4. Follow provenance back to the source record

```python
metadata = attached.metadata
source_row = tables[attached.dataset_index].loc[attached.source_record_index]
assert attached.Latitude == source_row["Latitude"]
assert attached.Longitude == source_row["Longitude"]
assert metadata is records.attrs["geocsv"]
print(metadata.source_path)
print(attached.dataset_index, attached.source_record_index)  # 0, 18
print(metadata.field_units["Latitude"], metadata.field_units["SampleRate"])
```

For this fixture, record 18 refers to the **subset file** actually opened.
The tracked manifest maps it to record 689 in the complete export:

```python
manifest = json.loads((fixtures / "manifest.json").read_text())
subset_info = next(
    item["subset"] for item in manifest["geocsv"]
    if item["subset"]["path"] == geocsv_path.relative_to(fixtures).as_posix()
)
original_index = subset_info["source_record_indices"][attached.source_record_index]
assert original_index == 689
print(f"Subset record {attached.source_record_index}: original record {original_index}")
```

Association copies the row values into a new mutable attachment. Editing the
DataFrame afterward does not refresh it. Immutable dataset provenance may be
shared with its parsed frame; mutable attachments and coordinate containers
are newly allocated for each trace and each invocation.

## 5. Associate a batch and handle failures

One source row may describe more than one input trace, including repeated
requests for the same original segment. Rows are never consumed or reserved:

```python
batch = Stream([original.copy(), original.copy()])
geocsv.associate(batch, tables)
assert batch[0].stats.geocsv.source_record_index == batch[1].stats.geocsv.source_record_index
assert batch[0].stats.geocsv is not batch[1].stats.geocsv
assert batch[0].stats.coordinates is not batch[1].stats.coordinates
```

All trace matches resolve before coordinate projections are built, and all
projections validate before any trace is modified. A failure leaves the
entire supplied batch unchanged. These two unassociated copies demonstrate
an explicitly tighter 100 microsecond tolerance:

```python
unmatched = Stream([original.copy(), original.copy()])
try:
    geocsv.associate(unmatched, tables, time_tolerance=0.0001)
except ValueError as error:
    print(error)
else:
    raise AssertionError("Expected the explicit 100 microsecond tolerance to reject this fixture")
assert all("geocsv" not in item.stats for item in unmatched)
assert all("coordinates" not in item.stats for item in unmatched)
```

Diagnostics include waveform identity, timing, counts, rates, and candidate
source paths and indices. Unsupported waveform argument types raise
`TypeError`; missing ObsPy raises an actionable `ImportError`.

Both destination containers, `stats.geocsv` and `stats.coordinates`, must be
absent, even if existing containers are empty or appear equivalent. Calling
association again on the already associated trace therefore fails:

```python
try:
    geocsv.associate(trace, tables, time_tolerance=0.001)
except ValueError as error:
    print(error)  # stats.geocsv already exists
else:
    raise AssertionError("Expected association to reject an existing destination")
```

For another association experiment, use an untouched copy or reread the
MiniSEED file. Existing source or trace metadata never fills missing matched
values, and association never merges, overwrites, or deletes destinations.

## 6. Opt in to a containing anchor for clipped or combined windows

Strict matching is the default. With `allow_first_segment=True`, exactly one
same-SNCL source segment must contain the waveform's first sample. Its inclusive
last-sample time is `StartTime + (SampleCount - 1) / SampleRate`; the explicit
time tolerance applies at the interval boundaries. A nearest-prior row is not
enough. Multiple containing anchors raise even if one is an exact start/count
match. Errors identify affected traces, source records and one-based physical
starting lines. Resolve the source ambiguity or fill headers manually outside
this package; the associator does not choose an anchor or modify any trace on
failure.

The fallback retains exact gap-free source sample coverage over the downloaded
window, counting overlaps once. Source ranges are clipped to that window,
allowing either edge to fall inside a source segment. Retained first/last
samples must have unique nearest-sample placement within half a waveform
interval, independently of the absolute start/containment tolerance. Missing source coverage, masked waveform gaps, incompatible rates,
or incomplete coordinates still raise. Raw anchor fields remain unchanged;
`association.waveform.sample_count` records the downloaded count separately.
Under the user's
MERMAID negligible-drift convention, the anchor's position and approximate depth
may also supply the whole window's geographic SAC headers.

Use the two real P0045 WLT5 request segments selected from 2022-01-15, the
date of the Hunga Tonga eruption. We inspected all nine P0045 MiniSEED files
whose starts fall on that UTC day. These two overlapping segments form the
longest continuous span with the same SNCL and sample rate. The complete
inventory, source paths, hashes, and independent SAC comparison references
are documented in the [fixture notes](../../tests/fixtures/association/P0045_20220115/README.md).
The full P0045 GeoCSV fixture is shared with the fetch tests; no second copy
or subset is needed for this example.

First load the original segments and inspect their overlap:

```python
merge_directory = root / "tests/fixtures/association/P0045_20220115"
merge_manifest = json.loads((merge_directory / "manifest.json").read_text())
p0045_tables = geocsv.read(root / "data/fixtures/P0045/P0045.geocsv")
p0045_records = p0045_tables[0]
segments = Stream()
for item in merge_manifest["selected"]:
    segments += read_waveforms(str(merge_directory / item["mseed"]["path"]))
segments.sort()
assert len(segments) == 2
assert all(item.id == "MH.P0045.00.BDH" for item in segments)
assert [item.stats.npts for item in segments] == [9696, 36000]
print(segments)
print(segments.get_gaps())  # Negative duration/count indicates an overlap.
```

ObsPy reports an overlap of approximately 0.625 seconds, counting the interval
to the next expected sample. The later segment starts about 24.8 ms off the
earlier segment's sample grid. There is a separate **0.624-second gap** before
the following request segment at 05:12:02.912869 UTC. We stop before that gap;
filling it would not demonstrate continuous source coverage. The RAW segment
earlier that day has location `10` and twice the sample rate, so it cannot be
combined directly with location `00` WLT5 samples.

Now merge the two loaded segments with ObsPy, before attaching metadata:

```python
merged_stream = segments.copy()
merged_stream.merge(method=1, interpolation_samples=0, misalignment_threshold=0)
merged_trace, = merged_stream
assert np.ma.count_masked(merged_trace.data) == 0
assert merged_trace.stats.npts == 45683
assert np.array_equal(merged_trace.data,
                      np.concatenate([segments[0].data[:9683], segments[1].data]))
print(merged_stream)
```

`method=1` uses the later trace's values in the overlap, without interpolating
sample amplitudes. `misalignment_threshold=0` disables cleanup's preliminary
subsample adjustment; the merge still places segments at the nearest integer
sample index on the first trace's grid. This shifts the later segment's grid
by about 24.8 ms. The result runs from 04:33:58.910159 through approximately
05:12:02.214055 UTC: **38 minutes 3.304 seconds** between first and last samples,
at the measured rate of 20.006973266601562 Hz. Original input traces and
GeoCSV rows remain unchanged. This is an explicit overlap-handling choice,
not a reconstruction of which original acquisition supplied each sample.

Strict association rejects its enlarged sample count:

```python
try:
    geocsv.associate(merged_trace, p0045_tables, time_tolerance=0.001)
except ValueError as error:
    print(error)
else:
    raise AssertionError("Expected strict count validation to fail")
assert "geocsv" not in merged_trace.stats
assert "coordinates" not in merged_trace.stats
```

With `allow_first_segment=True`, source ranges are placed on the waveform grid
to their unique nearest samples. The offset must be strictly less than half
the waveform sample interval, approximately 24.991 ms here. Its approximately 24.8 ms grid offset
therefore succeeds without increasing `time_tolerance`.

This separates two checks: `time_tolerance` controls absolute strict-start
matching and containing-anchor boundaries; the half-sample rule controls source
coverage placement. Even `time_tolerance=0` leaves the half-sample coverage rule
in place. Exact half-sample ties raise, as does accumulated rate drift beyond
half an interval at a retained boundary. Source counts fix each placed range's
length; boundaries are not independently rounded to invent extra coverage.
The rule accepts different grid phases and small timing discontinuities;
it does not establish exact time agreement or physical clock accuracy.

The half-sample scale mirrors ObsPy's own MiniSEED reader,
`obspy/io/mseed/src/obspy-readbuffer.c`. Our strict inequality rejects midpoint
ties; the reader uses an inclusive join limit. See the [policy and source rationale](../OBSPY_MERGED_TRACES.md#separate-absolute-matching-from-grid-placement).

```python
before_merge_association = merged_trace.copy()
geocsv.associate(merged_trace, p0045_tables, allow_first_segment=True)
assert merged_trace.stats.geocsv.association.type == "anchor_segment"
merged_report = merged_trace.stats.geocsv.association
assert len(merged_report.coverage_segments) == 2
assert [segment.source_record_index for segment in merged_report.coverage_segments] == [101433, 101434]
assert merged_report.max_sample_grid_offset.seconds > 0.001
assert merged_report.max_sample_grid_offset.seconds < merged_trace.stats.delta / 2
print(merged_report.coverage_segments)
print(merged_report.max_sample_grid_offset)
assert merged_trace.stats.geocsv.source_record_index == 101433
assert merged_trace.stats.geocsv.SampleCount == 9696
assert merged_trace.stats.npts == 45683
assert np.array_equal(merged_trace.data, before_merge_association.data)
assert all(merged_trace.stats[key] == value
           for key, value in before_merge_association.stats.items())
anchor = p0045_records.loc[101433]
assert merged_trace.stats.coordinates.latitude == anchor.Latitude
assert merged_trace.stats.coordinates.longitude == anchor.Longitude
assert p0045_records.loc[101434, "SampleCount"] == 36000
print(merged_trace.stats.coordinates)
```

The source ranges occupy `[0, 9696)` and `[9683, 45683)` on the merged grid;
their 13-sample overlap is counted once, giving exactly 45,683 samples with no
gap. The attached position remains the first segment's position at its first
sample; it does not average drift over the merged waveform.

The function performs no waveform merge and reconstructs no acquisition
lineage. All attached raw fields still describe the anchor row only; its
count, quality, pressure, and rate do not become whole-trace measurements.
A standard match remains `single_segment` with `allow_first_segment=True` only
when its containing anchor is also unique.
MiniSEED quality M neither enables nor prevents the fallback. Coverage cannot
detect gaps already filled upstream or determine which overlapping samples
survived a prior merge. See the [merged-trace policy](../OBSPY_MERGED_TRACES.md).

Association describes the waveform at the time of attachment. Subsequent
trimming, resampling, or merging does not refresh its source row, position,
label, or start difference. Preserve original waveforms and associate before
downstream transformations when you need the original segment relationship.

## 7. Associate a window starting and ending inside source segments

Clip the unassociated originals after merging, then associate that final window.
This real example starts inside the first REQ segment and ends inside the second.
Both source ranges extend outside the window; their clipped union must still
cover every downloaded sample. Half-sample placement also applies after
clipping; neither source counts nor native waveform times are rewritten.

```python
window, = segments.copy().merge(method=1, interpolation_samples=0,
                                misalignment_threshold=0)
window.trim(starttime=window.stats.starttime + 1,
            endtime=window.stats.endtime - 1)
window_before = window.copy()
geocsv.associate(window, p0045_tables, allow_first_segment=True)
assert window.stats.geocsv.association.type == "anchor_segment"
assert window.stats.geocsv.source_record_index == 101433
assert window.stats.geocsv.association.waveform.sample_count == window.stats.npts
assert window.stats.geocsv.SampleCount == 9696
assert window.stats.geocsv.association.waveform_start_offset_seconds > 0.9
np.testing.assert_array_equal(window.data, window_before.data)
assert window.stats.coordinates.latitude == anchor.Latitude
print(window.stats.coordinates)
```

The anchor's GeoCSV position still describes its original first sample. Its
geographic projection onto this window follows the supplied MERMAID convention;
no new interpolation or average position is computed. Associate after clipping
or combining traces, before optional SAC header creation and writing.
Later waveform edits do not refresh association or its projections; ObsPy
writing does not revalidate them. Source SampleCount is never rewritten.

## Fixture coverage

The real P0030 fixture exercises `single_segment`, default and explicit time tolerances,
repeated-row batch association, and rejection of existing destinations.
The real P0045 example merges two original MiniSEED request segments and
explicitly asserts `anchor_segment`, unchanged anchor fields and waveform data,
and automatic half-sample coverage placement. The largest continuous span is
limited by the following real gap; no gap filling, resampling, or mixing of
location codes is used. The additional real window clips both ends and checks
containment, unchanged anchor values and preserved samples. Synthetic coverage
tests remain in the test suite,
separate from this real-data tutorial.
