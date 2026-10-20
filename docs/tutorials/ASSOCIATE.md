# Associate GeoCSV metadata with ObsPy waveforms

`geocsv.associate` attaches a uniquely matched event row and receiver position
to an ObsPy `Trace` or `Stream`. This tutorial uses tracked MiniSEED and GeoCSV
fixtures, so it runs offline from a fresh checkout. The companion files
[`ASSOCIATE.md`](ASSOCIATE.md) and
[`ASSOCIATE.ipynb`](ASSOCIATE.ipynb) must keep the same
explanations and Python examples in the same order when either is edited.
For pandas basics, start with the [reader tutorial](READ.md).

From the repository root, activate the existing environment and install the
package with its optional ObsPy dependency (ObsPy 1.5.1 or newer):

```bash
source .venv/bin/activate
python -m pip install '.[obspy]'
```

See the [installation guide](../INSTALLATION.md) if you have not created an
environment yet. For a notebook, also install JupyterLab and its Python kernel:

```bash
python -m pip install jupyterlab ipykernel
python -m jupyterlab docs/tutorials/ASSOCIATE.ipynb
```

Select a kernel using this repository's `.venv` and run the cells from top to
bottom. Alternatively, start `python` and run the Python blocks in order at
the shell's Python prompt. Start with the working directory set to the
repository root, `docs/`, or `docs/tutorials/`. The reader itself requires only pandas; ObsPy is
loaded when association is called.

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
if root.name == "tutorials":
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

## 2. Associate in place with an explicit time tolerance

The public call is:

```python
help(geocsv.associate)
```

Begin with one trace and the parsed tables. This fixture needs the explicit
1 ms tolerance explained below; no other optional input is needed.
Its signature is `associate(waveforms, records, *, time_tolerance=0.0001,
allow_merge=False)`. Each trace must match exactly one `Algorithm(event):` row
under these rules:

- Network, Station, Location, and Channel (SNCL) match exactly. Only Location
  may be the known empty string `""`; no identity field may be missing.
- Zoned source start times and waveform UTC times differ by no more than the
  inclusive tolerance, in seconds. The default is 100 microseconds. Zero
  requires exact equality; `None`, negative, and nonfinite values are invalid.
- `SampleCount` equals both waveform `npts` and the number of loaded samples.
  Counts have no tolerance. Masked sample gaps are rejected.
- Source `SampleRate`, declared in hertz, differs from the waveform rate by at
  most 0.01 Hz. This threshold remains provisional scientific policy.

Source timestamp spelling does not enlarge the tolerance or establish clock
accuracy. This real P0030 waveform begins **349 microseconds later** than its
millisecond-rendered GeoCSV start. The default rejects it; explicitly allow
1 ms for this Automaid history:

```python
original = trace.copy()
result = geocsv.associate(trace, tables, time_tolerance=0.001)
assert result is None
assert np.array_equal(trace.data, original.data)
assert all(trace.stats[key] == value for key, value in original.stats.items())
print(trace.stats.geocsv.association)  # one_segment
print(trace.stats.geocsv.starttime_difference_seconds)  # 0.000349
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
coordinate fails the association. SAC header projection remains future work.

The attachment also has five association-owned keys:

| Key | Meaning |
| --- | --- |
| `dataset_index` | Zero-based position in the supplied list of DataFrames. |
| `source_record_index` | Original DataFrame row label, counting data records rather than physical file lines. |
| `metadata` | Immutable GeoCSV dataset metadata, including source path, units, and comments. |
| `association` | `one_segment` for standard matching, or `first_segment` for the explicit fallback below. |
| `starttime_difference_seconds` | Waveform start minus matched source start, calculated from integer UTC nanoseconds before conversion to seconds. |

Positive start differences mean the waveform begins later. This records the
initial match; it is neither a clock correction nor an uncertainty estimate.
Source columns colliding with these keys or with `AttribDict` attributes and
methods raise before mutation; they are never silently renamed or discarded.

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
geocsv.associate(batch, tables, time_tolerance=0.001)
assert batch[0].stats.geocsv.source_record_index == batch[1].stats.geocsv.source_record_index
assert batch[0].stats.geocsv is not batch[1].stats.geocsv
assert batch[0].stats.coordinates is not batch[1].stats.coordinates
```

All trace matches resolve before coordinate projections are built, and all
projections validate before any trace is modified. A failure leaves the
entire supplied batch unchanged. These two unassociated copies demonstrate
the too-small default tolerance:

```python
unmatched = Stream([original.copy(), original.copy()])
try:
    geocsv.associate(unmatched, tables)
except ValueError as error:
    print(error)
else:
    raise AssertionError("Expected the default tolerance to reject this fixture")
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

## 6. Opt in to a first-segment location for a longer trace

Strict matching is the default. When a longer waveform combines several
source segments, the explicit `allow_merge=True` option may attach a unique
first segment's metadata and adopt its location for the whole trace. It
requires exact gap-free coverage of the waveform sample grid by source sample
ranges, counting overlaps once. Both starts and last samples must align within
the chosen time tolerance, without ambiguous sample placement. A shorter
trace, ambiguous anchor, masked gap, missing coordinate pair, incompatible
rate, or any coverage gap or excess still raises.

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
p0045_tables = geocsv.read(root / "tests/fixtures/geocsv/P0045.geocsv")
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

Strict association rejects its enlarged sample count. Even with
`allow_merge=True`, the 1 ms tolerance used earlier is too small for this
sample-grid placement. Demonstrate both failures before increasing the option:

```python
for options in (
    {"time_tolerance": 0.001},
    {"time_tolerance": 0.001, "allow_merge": True},
):
    try:
        geocsv.associate(merged_trace, p0045_tables, **options)
    except ValueError as error:
        print(error)
    else:
        raise AssertionError("Expected strict count or 1 ms grid validation to fail")
assert "geocsv" not in merged_trace.stats
assert "coordinates" not in merged_trace.stats
```

For this example only, explicitly allow 25 ms for source start and last-sample
alignment. This is close to half a sample at the measured rate; the associator
still requires exactly one eligible sample index for every source start.
The millisecond-rendered GeoCSV starts and rounded rates pass that uniqueness
check at 25 ms. This tolerance is a declared example policy, not a claim about
clock accuracy or a new default. Do not increase tolerance blindly for other
waveforms.

```python
before_merge_association = merged_trace.copy()
geocsv.associate(merged_trace, p0045_tables,
                  time_tolerance=0.025, allow_merge=True)
assert merged_trace.stats.geocsv.association == "first_segment"
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
A standard match remains `one_segment` even when `allow_merge=True`.
MiniSEED quality M neither enables nor prevents the fallback. Coverage cannot
detect gaps already filled upstream or determine which overlapping samples
survived a prior merge. See the [merged-trace policy](../OBSPY_MERGED_TRACES.md).

Association describes the waveform at the time of attachment. Subsequent
trimming, resampling, or merging does not refresh its source row, position,
label, or start difference. Preserve original waveforms and associate before
downstream transformations when you need the original segment relationship.

## Fixture coverage

The real P0030 fixture exercises `one_segment`, the explicit time tolerance,
repeated-row batch association, and rejection of existing destinations.
The real P0045 example merges two original MiniSEED request segments and
explicitly asserts `first_segment`, unchanged anchor fields and waveform data,
and failure at the earlier 1 ms tolerance. The largest continuous span is
limited by the following real gap; no gap filling, resampling, or mixing of
location codes is used. Synthetic coverage tests remain in the test suite,
separate from this real-data tutorial.
