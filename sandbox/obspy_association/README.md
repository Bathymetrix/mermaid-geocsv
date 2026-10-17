# ObsPy association sandbox

Retrieval examples and an experimental association prototype. The reader
package API remains unchanged; the prototype contract is described below.
Run from the repository root with an environment containing this package and
ObsPy. Downloaded responses go under ignored `downloads/`.

Install the sandbox dependency in the repository environment:

```bash
.venv/bin/python -m pip install -e '.[obspy]'
```

## Short acquisition examples

```bash
.venv/bin/python sandbox/obspy_association/retrieve_event_examples.py --raw
```

Add `--plot` for the seismograms. The examples use two `Algorithm(event)` rows
from the bundled P0006 GeoCSV fixture:

| Source record index | Acquisition | Start time (UTC) | Rate | Count | Source quality |
| --- | --- | --- | --- | --- | --- |
| 98 | Detected | 2018-06-29 17:07:31.205 | 20 Hz | 4832 | Q |
| 100 | Requested | 2018-07-06 01:49:28.590 | 20 Hz | 4800 | D |

Requests use complete SNCL `MH.P0006.00.BDH`, with a one-second margin around
the source's first and last sample. This is a retrieval margin, not our
future matching tolerance. Quality is not filtered, so we can inspect the
service's default behavior. The scripts do not explicitly trim, merge,
calibrate, or attach metadata.

The normal `get_waveforms` path parses MiniSEED and trims to request bounds
inside ObsPy. With `--raw`, a second request saves the service response before
that client-side parsing/trimming. Reading that file still assembles MiniSEED
records into traces. Neither result alone identifies original acquisitions.
See the [client implementation](https://docs.obspy.org/_modules/obspy/clients/fdsn/client.html)
and [retrieval parameters](https://docs.obspy.org/packages/autogen/obspy.clients.fdsn.client.Client.get_waveforms.html).

The explicit HTTPS EarthScope endpoint serves the role of `Client("IRIS")`
in the supplied example, without depending on alias behavior across versions.
Fixture timestamps are already corrected; do not apply `TimeCorrection` again.

## Inspect a MiniSEED file

Use ObsPy's MiniSEED reader and built-in stream plotter to inspect a local file
and print each trace's MiniSEED data-quality flag:

```bash
.venv/bin/python sandbox/obspy_association/view_mseed.py \
    data/fixtures/association/452.020-P-0030/0002_20210527-14h28m09s/20210527T154441.0030_60AFC696.MER.DET.WLT2.mseed
```

## Longer window

```bash
.venv/bin/python sandbox/obspy_association/retrieve_long_window.py
```

The default request spans 30 days. A one-year probe is explicit:

```bash
.venv/bin/python sandbox/obspy_association/retrieve_long_window.py \
    --start 2018-06-29T00:00:00Z --end 2019-06-29T00:00:00Z
```

Inspect trace count, gaps/overlaps, rates, timing, and quality. A successful
request does not establish completeness; compare with eligible GeoCSV rows
before concluding that all expected acquisitions were returned.

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) for the running design questions
and [OBSERVATIONS.md](OBSERVATIONS.md) for execution evidence. The supplied
[MERMAID data-quality note](MERMAID_DATA_QUALITY.md) records DET/REQ/raw-buffer
meaning and the nominal channel/location/rate table.
## Original processed waveform association

Develop association for MiniSEED-derived traces only until further instruction.
Paired SAC files are read separately as output references for later key-by-key
checks of `stats.sac` projected onto associated MiniSEED traces. Their inherited
headers never supply association inputs or defaults. SAC-input association
is outside scope; SAC output projection remains deferred.

The sandbox now implements `associate` for an original processed `Trace` or
`Stream`. The public reader API is unchanged. `$MERMAID/processed/` is the
canonical read-only source: never modify it without express instruction.
Its float directories supply paired waveforms and complete GeoCSV histories.
Tracked subsets make real-data tests independent of those full histories.
See the [fixture inventory and audit](../../data/fixtures/association/README.md).

From this sandbox directory (with the repository environment installed):

```python
from obspy import read
from mermaid import geocsv
from associate import associate

st = read("/path/to/original.MER.DET.WLT5.mseed")
records = geocsv.read("/path/to/geo_DET_REQ.csv")
associate(st, records, allow_merge=False, time_tolerance=0.001)
tr = st[0]
print(tr.stats.geocsv.Latitude)
print(tr.stats.geocsv.source_record_index)
print(tr.stats.geocsv.metadata.source_path)
print(tr.stats.coordinates)
```

The example explicitly allows 1 ms for Automaid's millisecond-rendered history.
Network, Station, and Channel require nonempty strings. A string-valued source
`Location` cell written empty or quoted-empty is the known code `""`, matching
only waveform `location=""`. `nan`, declared missing markers, and absent identity
columns do not supply an empty code. Missing DataQuality remains separate from
waveform quality and is not a match filter.
Source preflight rejects invalid event identities and duplicate complete
SNCL/UTC-time/count/rate keys across datasets, including unrelated rows. It
reports source paths and dataset/record indices. Distinct counts can
disambiguate same-SNCL/time rows. All supplied traces must then match uniquely
under the actual tolerance/count/rate rules before projections are built.
The function mutates in place and returns `None`. It requires exactly one
event-row match per trace: full SNCL, UTC time differences within 100 microseconds by default, exact original
sample count/data length, and measured rates within 0.01 Hz. Waveform core
headers and processing history are preserved. Source quality is attached
separately from MiniSEED quality. Latitude/longitude use their declared units;
elevation is the explicit sea-level constant 0, with no geoid model.

All matches and projections are validated before any batch mutation. Existing
GeoCSV or coordinate containers raise `ValueError`, even if empty or equivalent. The mutable
attachment keeps original columns plus dataset index, source record index,
immutable dataset metadata, `association`, and `starttime_difference_seconds`.
These attachment keys are reserved; colliding source columns raise.
`stats.geocsv` is an ObsPy `AttribDict`: its attributes and methods, including
inherited names, are also reserved against source-column collisions. Such a
collision raises `ValueError` with the source, dataset, and conflicting names
before any trace is modified. Source columns are never silently renamed or dropped.
`starttime_difference_seconds` is waveform start time minus matched GeoCSV
`StartTime`, computed from integer UTC nanoseconds before conversion to
seconds. Positive values mean the waveform starts later; negative values mean
it starts earlier. It records the initial match, is not a clock correction or
uncertainty estimate, and is not recomputed after waveform changes.
Standard matches are labeled
`one_segment`. With `allow_merge=True`, a longer trace may instead receive
`first_segment`: one unique SNCL/start-time anchor must have a compatible rate,
a positive integer count, and exact gap-free source sample coverage after overlap
removal on the waveform grid. Masked gaps
raise. The anchor location applies to the whole trace; other source fields
still describe the anchor only. This neither merges waveforms nor reconstructs
contributing acquisitions, and does not require MiniSEED quality M. See the
[merged-trace policy](../../docs/OBSPY_MERGED_TRACES.md).
For `first_segment`, the start-time difference is relative to the anchor row.
Guarantees end at initial association; arbitrary trimming/resampling and
upstream gap filling remain outside this matching contract.

Batch matching builds a lookup once per call, grouping event rows by complete
SNCL and sorting them by UTC start time. Binary search narrows each trace's
candidate window; each candidate still undergoes its own time-tolerance,
count, and rate checks. Multiple eligible rows remain an error, while multiple
traces may independently match the same row. Every trace receives fresh
attachment and coordinate containers after the entire batch validates.

SAC projection is deferred; no SAC keyword or placeholder is accepted.
The [future-work reminder](../../docs/FUTURE.md#project-associated-metadata-into-sac-headers)
retains the planned geographic mapping and independent SAC comparison workflow.

`collect_processed_examples.py` is the reproducible sampling script; it writes
only a new repository fixture directory and refuses to overwrite one. It
copies both waveform formats and complete GeoCSV files verbatim.
Full association histories are ignored local files. On a fresh checkout,
`restore_geocsv_histories.py` copies the manifest-listed complete histories
from `$MERMAID/processed/` after checking their hashes. See the fixture README
for instructions. Tests instead require the tracked `association_subset.geocsv`
files. `check_full_histories.py` separately verifies their verbatim extraction
and all 18 sampled matches against complete local histories.

Coordinate projection requires a complete source latitude/longitude pair.
Missing either raises. `stats.geocsv` and `stats.coordinates` must be absent.
Existing `stats.sac` headers are left untouched. No merge,
overwrite, deletion, or per-field missing-data options are provided. Reference
elevation 0 is supplied only with a valid source pair. Native waveform fields
are validated and preserved, never filled or relabeled from GeoCSV.
See the [source-based Stats reference](../../docs/OBSPY_STATS_REFERENCE.md):
processing history is decorator-maintained optional metadata, not a mainline
Stats default or an association projection.

`time_tolerance=0.0001` defaults to a fixed 100 microseconds;
pass a finite nonnegative number of seconds to override it, or zero for exact
matching. Both source and waveform timestamps retain full nanosecond precision.
`None` is not accepted. Source lexical resolution is preserved but does not
control matching. Current Automaid millisecond-rendered histories may require
an explicit `time_tolerance=0.001`; real-fixture integration tests use that value.
The current MERMAID 0.01 s physical-resolution convention does not truncate
generic GeoCSV input and does not define matching tolerance.

Tracked synthetic examples in `tests/fixtures/association/` exercise the
adapter's matching rules on CI. Small tracked real-data subsets also run on
CI; full local histories remain optional corpus references. See the
[current audit and Monday next steps](../../audits/05.md) and the
[historical adversarial audit](../../docs/OBSPY_ASSOCIATION_AUDIT.md).
