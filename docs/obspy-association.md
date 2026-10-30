# Waveform association

`geocsv.associate` attaches source metadata and receiver coordinates to
MiniSEED-derived ObsPy traces. The [association tutorial](../tutorials/associate.md)
provides introductory executable examples. This reference defines the public API and
collects the scientific rationale and validation rules; waveform processing
remains downstream.

## Scope and authority

Association describes MERMAID receiver (station) locations. Optional SAC
projections supply only `stla`, `stlo`, `stel`, and `stdp`; the pressure-derived
`stdp` is approximate station depth. Earthquake-source metadata and `ev*`
projections are outside this package's scope.

Waveform identity, timing, measured sampling rate, loaded sample count,
calibration, and samples remain authoritative. Association validates them
against GeoCSV; it never repairs a mismatch by rewriting either source.
Paired SAC files are independent comparison references, never association
inputs or sources of missing metadata.

Eligible source rows have `MethodIdentifier` beginning with `Derivation:Recording:`.
These are detected and requested waveform acquisitions, independent of producer
version. The subject `Recording` identifies an original contiguous waveform segment.
Position, pressure and crossing rows are not waveform candidates.

In the MERMAID construction, each original contiguous segment has one
event row. Multiple traces may independently match that row, including
identical waveforms requested in different MER files. One trace must resolve
to exactly one row; ambiguity never permits combining source metadata.

Position is the interpolated receiver position at the **source segment's first sample time**,
independent of duration or repeat-request date. It is not averaged over the
waveform.

## Matching original traces

The signature is `associate(waveforms, records, *, time_tolerance=0.001,
allow_first_segment=False, create_sac_header=False)`. It modifies a Trace or Stream in place and
returns `None`; records are tables from `geocsv.read`, retaining their
source indices and immutable GeoCSV metadata.

A standard match requires:

1. Exact, complete Network, Station, Channel, and Location. Only Location may
   be the known blank code of exactly two ASCII spaces, matching only waveform
   location `""`. Both source spaces remain in the table and raw attachment.
   Empty decoded source Location and other whitespace-only codes are invalid; codes are not trimmed,
   relabeled, or treated as wildcards. This validates presence, not the
   complete SEED character set or code lengths.
2. Timezone-aware source starts within the inclusive absolute
   `time_tolerance` of the waveform start. Comparisons use full UTC integer
   nanoseconds. The default is 1 millisecond; an override must be finite
   nonnegative seconds, and zero requires exact equality. `None` is invalid.
   Source lexical resolution does not enlarge the tolerance.
3. GeoCSV `SampleCount == stats.npts == len(data) > 0` exactly, with loaded,
   unmasked samples. There is no sample-count tolerance.
4. Finite positive rates satisfying the inclusive floating-point endpoint
   check `waveform_rate - 0.00001 <= source_rate <= waveform_rate + 0.00001`, in Hz.
   The 0.00001 Hz threshold is an agreement criterion, not an instrument
   accuracy bound or proof that whole-trace sampling grids agree.

DataQuality is retained independently from MiniSEED quality and does not
filter or disambiguate matches. See the [data-quality reference](mermaid-data-quality.md)
for DET Q, REQ D, raw-buffer R, and legacy archive M distinctions.

Before matching, source preflight rejects invalid identities on every event
row, even unrelated ones, and duplicate complete SNCL/UTC-start/count/rate
keys across supplied datasets. Different counts can disambiguate the same
SNCL/start. Missing or timezone-naive starts are ineligible candidates;
diagnostics identify skipped rows when no unique match can be made.

Event lookup groups complete SNCL and sorts UTC starts once per call. Every
trace must then resolve to one eligible row under the actual tolerance,
count, and rate rules. Zero or multiple matches raise `ValueError` with
source/candidate context. All matches and fallback coverage checks finish
before projections are built; all projections validate before any trace is
modified. Unsupported waveform argument types raise `TypeError`.

## Fresh attachments and coordinates

Both `stats.geocsv` and `stats.coordinates` must be absent, even if empty or
apparently equivalent. Every trace gets new containers populated only from
its matched record, dataset provenance, and documented projection rules.
Nothing is merged, overwritten, deleted, or filled from existing trace
metadata. A failed batch leaves all supplied traces unchanged.

`stats.geocsv` contains a mutable snapshot of the complete parsed row, with
original field names, values, and missingness, plus:

| Key | Meaning |
| --- | --- |
| `source_record_index` | Original file-wide data-record index, not a physical line number. |
| `dataset_index` | Position of the matched table in the supplied records list. |
| `metadata` | That table's immutable `GeoCSVMetadata`, including units and source/download provenance. |
| `association` | Nested association report described below. |

These keys and ObsPy `AttribDict` attribute/method names are reserved against
source-column collisions. A collision raises before mutation; fields are
never silently renamed or discarded.

Coordinates require a complete finite latitude/longitude pair, within
[-90, 90] and [-180, 180], declared in `degrees_north` and `degrees_east`.
Missing either component raises; there are no per-field missing-data switches.
The ten core Stats defaults, optional namespaces, and processing history are
distinguished in the [source-based Stats reference](obspy-stats-reference.md).

### Association report

`stats.geocsv.association` is a fresh nested ObsPy `AttribDict` for each trace.
All nested mappings, including entries in the `coverage_segments` tuple, support
both key and attribute access. It contains outputs only, not input tolerances.

| Field | Meaning |
| --- | --- |
| `type` | `single_segment` for strict original-segment matching; `anchor_segment` for the explicit containing-anchor fallback. A clipped window within one source segment can have type `anchor_segment`. |
| `waveform` | Association-time snapshot: `network`, `station`, `location`, `channel`, `starttime`, `endtime`, `sampling_rate_hz`, and `sample_count`. Times are fresh ObsPy `UTCDateTime` values preserving nanoseconds. |
| `coverage_segments` | Chronological tuple of contributing source-segment descriptions. For a strict match, contains only the matched source segment. |
| `waveform_start_offset_seconds` | Signed waveform start minus anchor start, computed using integer nanoseconds. An interior window can have a large positive offset; this is not its sample-grid error, a clock correction, or an uncertainty. |
| `max_sample_grid_offset` | `seconds`, `dataset_index`, `source_record_index`, `source_line_number`, and `waveform_sample_index` identifying the largest absolute timing difference among retained first/last sample pairs of contributing source ranges. |
| `max_sample_rate_difference` | `hz`, `dataset_index`, `source_record_index`, and `source_line_number` identifying the largest absolute source/waveform rate difference. |

Each `coverage_segments` entry contains:

| Fields | Meaning |
| --- | --- |
| `network`, `station`, `location`, `channel` | Complete source identity, including the literal two-space known blank Location. |
| `starttime`, `endtime` | Full original source segment bounds as UTCDateTime values. End is the last sample, computed as `Time + (SampleCount - 1) / SampleRate`, rounded to integer nanoseconds. |
| `sampling_rate_hz`, `sample_count` | Original source rate/count, not a clipped count. |
| `dataset_index` | Zero-based position of the dataset in the supplied DataFrame list. |
| `source_record_index` | Zero-based file-wide data-record index, excluding headers and comments; it does not restart for each dataset. |
| `source_line_number` | One-based physical starting line in that source file, counting headers, comments and blank lines; `None` if the row has no recorded physical line. |
| `waveform_sample_start`, `waveform_sample_stop` | Clipped contributing waveform range, zero-based, start inclusive and stop exclusive. Overlaps may appear in different entries and are counted once for coverage. |

`len(association.coverage_segments)` gives the source segment count. Source
record and line numbers refer to the file actually parsed, including a fixture
subset; they are not indices into an unparsed full history. Dataset indices
refer to the supplied list, which can combine files.

The geographic anchor is identified by `stats.geocsv.dataset_index` and
`stats.geocsv.source_record_index`. It need not be the first chronological
coverage entry: an earlier segment ending just before the waveform start can
contribute a retained boundary sample under the half-sample placement rule.

Grid diagnostics use the retained boundary pairs evaluated by the coverage
check, with the same integer-nanosecond arithmetic. The per-segment grids have
constant rates; these endpoints characterize their accumulated linear drift,
subject to nanosecond rounding. This is not a comparison of waveform sample
values. Strict matching still validates start/count/rate only: its reported
last-sample disagreement does not introduce a new endpoint acceptance check.
For equal maxima, select the first segment in chronological order (ties by
dataset then record index), and its first boundary sample before its last.

The report is a mutable association-time snapshot. Later changes to waveform
Stats, source tables, or other traces do not refresh it. Association never
moves or interpolates samples. Coverage rows are evidence that the supplied
waveform grid is supported, not proof that these rows were actually concatenated
or supplied particular values in an overlap. Arbitrary GeoCSV reports are not
serialized into SAC or MiniSEED headers.

Association provenance is guaranteed only in this in-memory attachment at
initial association. Users may persist it in sidecars in any format they
choose. Sidecar creation, format, fidelity and later restoration are the user's
responsibility; the package provides no sidecar writer or round-trip guarantee.

### Adopted sea-level reference

`stats.coordinates.elevation` and SAC `stel` use the explicit matched Recording
`Elevation`, declared `float` with unit `meters` and required to be zero. Missing,
invalid or nonzero source elevation raises before mutation. No zero default is
supplied. The source denotes the adopted sea-level reference, not the submerged
sensor's physical elevation. No geoid, ellipsoid or tidal correction is inferred.

Zero has the same numeric value in metres and kilometres; ObsPy array processing
expects kilometres while SAC `stel` uses metres. This profile defines no nonzero
coordinate-elevation conversion. Raw source Elevation remains attached unchanged.

## Clipped and combined windows

For `allow_first_segment=True`:

1. Use complete exact SNCL, including known empty Location, as in strict mode.
   Require zoned source timestamps and positive integer source SampleCount,
   with finite positive source SampleRate declared in hertz to establish a
   source interval. Its inclusive last sample is
   `Time + (SampleCount - 1) / SampleRate`, rounded to UTC nanoseconds.
2. Require exactly one source interval containing the waveform's first sample,
   allowing the explicit `time_tolerance` at interval boundaries. A preceding
   interval that ended earlier is not an anchor. Zero or multiple anchors raise.
3. For a nonstandard match, collect same-SNCL source intervals intersecting the
   waveform window expanded by half a waveform interval at each edge, including
   intervals beginning before the waveform. Required
   counts/rates must be valid. Rates retain the inclusive 0.00001 Hz
   agreement check around the waveform rate.
4. Place each source's integer sample range on the waveform grid. Clip it to
   `[0, npts)`; source samples outside the downloaded window are permitted.
   Round the source-start displacement to its nearest waveform sample index;
   the original source count fixes the range length. Retained first and last
   source samples must each remain within half a waveform interval of their
   assigned indices. Exact half-sample ties raise rather than using a rounding
   convention to choose a side. Accumulated drift beyond half an interval raises;
   do not independently round the last boundary to create additional coverage.
   Comparison is in sample units before rounding waveform times to nanoseconds;
   the report retains the existing nanosecond-rounded boundary measurements.
5. Require the union of those clipped integer ranges to cover every waveform
   sample without gaps, counting overlaps once. Source SampleCount is not
   rewritten and need not equal waveform `npts`. Full source metadata coverage
   is still required; trimming the window does not waive it.
6. Reject empty or masked waveform data, incomplete coordinates, existing
   destination containers, and other invalid inputs as before. Waveform
   `npts == len(data)` remains required. All matches and projections validate
   before any trace is modified.

If the unique containing anchor also passes the standard match, the label
remains `single_segment`; coverage validation applies to the fallback.
Multiple containing anchors raise even when one passes standard matching.
Errors include affected trace indices, source paths or download URLs, dataset
and record indices, and one-based physical starting lines. No anchor is chosen
automatically and no partial attachment is made.

### Separate absolute matching from grid placement

`time_tolerance` uses its 1 millisecond default for strict original-start
matching and containing-anchor boundaries. It never controls coverage-grid
placement; even zero does not require coincident grids in the anchor fallback.
The rule is strictly `abs(grid offset) < 0.5 / waveform_sampling_rate`.
It is fixed, rate-dependent, and has no separate public knob:
approximately 12.5 ms at 40 Hz, 25 ms at 20 Hz, and 200 ms at 2.5 Hz.

This explicitly accepts different grid phases and sub-sample timing
discontinuities. It establishes compatible sample coverage, not exact timing
agreement, absence of physical gaps, an unmodified acquisition, or reconstruction
of original overlap values. No waveform sample or timestamp is moved or
interpolated. Exact SNCL (including Location), unique anchor, source rate
agreement, source counts and complete union coverage remain required. Strict
`single_segment` acceptance does not gain a new endpoint check.

The half-interval scale is chosen to mirror ObsPy's MiniSEED reader in
`obspy/io/mseed/src/obspy-readbuffer.c`: it sets
`hptimetol = (hptime_t) (0.5 * segmentCurrent->hpdelta)` and accepts record
joins within that limit. Association uses a strict inequality because an exact
midpoint has two equally near sample indices. Thus we mirror the reader's
half-sample scale, not its inclusive endpoint or complete joining algorithm:
association compares whole source ranges to an already assembled Trace.
Several record-join errors may accumulate, so a Trace accepted by the reader
can still fail coverage. The inspected checkout is
`50033e1daf95233cd4f30e95a49c37fd50be2ccd`; installed ObsPy is separately 1.5.1.

ObsPy Stream merging is a separate operation; its default cleanup threshold
is 0.01 sample intervals, not the MiniSEED reader's half-sample join scale.
Choose merge behavior explicitly before association.

## Geographic meaning and later processing

Under the MERMAID negligible-drift convention, the containing anchor's
geographic metadata applies to the whole clipped or combined window. The
source position still describes the source segment's original first sample;
it is not interpolated to the clipped start or averaged over the window.
This convention does not establish suitability for arbitrary moving sensors
or long windows. Missing pressure is never filled from another row.

Associate the final waveform after any clipping or merging. Later changes to
Stats, samples, or source tables do not refresh attachments or projections.
ObsPy merging can retain an earlier trace's metadata while changing its count
and extent; a retained association label is not revalidated. No original
sample-contribution history is reconstructed.

Optional `create_sac_header=True` adds fresh SAC station headers for either
association label. The flag must be a Python bool; the default False leaves
existing SAC headers untouched. The [SAC reference](sac.md) owns the mapping,
missing-pressure rules, and storage limits. ObsPy owns writing, and the
publisher owns final export verification.

## Timing evidence

The inspected automaid writer renders corrected waveform starts as
`str(starttime)[:23] + 'Z'`, retaining milliseconds. Association must not apply
`TimeCorrectionApplied` again. The default start tolerance accommodates the checked
histories' sub-millisecond serialization differences. The
[fixture evidence](../data/fixtures/association/README.md#tolerance-evidence)
records the bounded sample behind that choice; it is not a clock-accuracy
specification. The MERMAID timing convention gives stored digits finer than
0.01 s no physical accuracy claim. Preserve those digits anyway.

Precise sampling intervals remain meaningful with coarser absolute clock
accuracy. Rate from an independently measured first-to-last duration is
`(npts - 1) / duration`; a duration spanning `npts` whole intervals uses
`npts / duration`. Deriving rate from ObsPy's rate-derived endtime is circular.
Raw-MER and encoding precision remain an
[open investigation](open-questions.md#mermaid-sampling-rate-follow-up).

The [P0045 fixture](../tests/fixtures/association/P0045_20220115/README.md)
and [preserved P0006 service response](../tests/fixtures/association/P0006_20180713_earthscope/README.md)
exercise differing source-grid phases and overlapping ranges. Their provenance,
counts, and measured offsets are maintained with the fixtures. Coverage cannot
identify which source supplied overlap values or detect gaps filled upstream;
see [open scientific questions](open-questions.md#association-scientific-questions).
