# Association design and scientific conventions

`geocsv.associate` attaches source metadata and receiver coordinates to
MiniSEED-derived ObsPy traces. The [association tutorial](tutorials/ASSOCIATE.md)
defines the public API and provides executable examples. This reference
collects the scientific rationale and validation rules; waveform processing
remains downstream.

## Scope and authority

Waveform identity, timing, measured sampling rate, loaded sample count,
calibration, and samples remain authoritative. Association validates them
against GeoCSV; it never repairs a mismatch by rewriting either source.
Paired SAC files are independent comparison references, never association
inputs or sources of missing metadata.

Eligible source rows have `MethodIdentifier` beginning with `Algorithm(event)`.
This includes detected and requested acquisitions, not just confirmed
seismic events, and is independent of producer version. GPS, pressure, and
thermocline observations are not waveform candidates.

In the user's MERMAID construction, each original contiguous segment has one
event row. Multiple traces may independently match that row, including
identical waveforms requested in different MER files. One trace must resolve
to exactly one row; ambiguity never permits combining source metadata.

Position is the interpolated receiver position at the **first sample time**,
independent of duration or repeat-request date. It is not averaged over the
waveform. [Original July 13 waveform inspection](OBSPY_RETRIEVAL_OBSERVATIONS.md#original-july-13-waveforms-2026-10-15)
provides evidence for the repeated-request case.

## Matching original traces

The signature is `associate(waveforms, records, *, time_tolerance=0.0001,
allow_first_segment=False)`. It modifies a Trace or Stream in place and
returns `None`; records are tables from `geocsv.read`, retaining their
source indices and immutable GeoCSV metadata.

A standard match requires:

1. Exact, complete Network, Station, Channel, and Location. Only Location may
   be the known empty string `""`, matching only waveform location `""`.
   Missing or whitespace-only codes are invalid; codes are not trimmed,
   relabeled, or treated as wildcards. This validates presence, not the
   complete SEED character set or code lengths.
2. Timezone-aware source starts within the inclusive absolute
   `time_tolerance` of the waveform start. Comparisons use full UTC integer
   nanoseconds. The default is 100 microseconds; an override must be finite
   nonnegative seconds, and zero requires exact equality. `None` is invalid.
   Source lexical resolution does not enlarge the tolerance.
3. GeoCSV `SampleCount == stats.npts == len(data)` exactly, with loaded,
   unmasked samples. There is no sample-count tolerance.
4. Finite positive rates satisfying the inclusive floating-point endpoint
   check `waveform_rate - 0.01 <= source_rate <= waveform_rate + 0.01`, in Hz.
   The 0.01 Hz threshold is provisional scientific policy, not an instrument
   accuracy bound or proof that whole-trace sampling grids agree.

DataQuality is retained independently from MiniSEED quality and does not
filter or disambiguate matches. See the [data-quality reference](MERMAID_DATA_QUALITY.md)
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
| `association` | `one_segment` for a standard match, or `first_segment` for the explicit fallback. |
| `starttime_difference_seconds` | Waveform start minus matched source start, computed from integer UTC nanoseconds. Positive means the waveform starts later. |

These keys and ObsPy `AttribDict` attribute/method names are reserved against
source-column collisions. A collision raises before mutation; fields are
never silently renamed or discarded. The signed start difference describes
the initial match, not a correction or an uncertainty estimate.

Coordinates require a complete finite latitude/longitude pair, within
[-90, 90] and [-180, 180], declared in `degrees_north` and `degrees_east`.
Missing either component raises; there are no per-field missing-data switches.
The ten core Stats defaults, optional namespaces, and processing history are
distinguished in the [source-based Stats reference](OBSPY_STATS_REFERENCE.md).

### Adopted sea-level reference

`stats.coordinates.elevation = 0.0` is an explicit marine MERMAID convention
consistent with automaid. It refers to sea level, not the submerged sensor's
physical elevation, and is not inferred from missing GeoCSV `Elevation`.
No geoid, ellipsoid, tidal correction, or other vertical-datum model is
assumed. Lake-level handling is deferred.

Zero has the same numeric value in metres and kilometres; ObsPy array
processing expects kilometres while SAC `stel` uses metres. This does not
establish a future nonzero elevation unit convention or suitability for every
analysis of a submerged receiver. Parsed `Elevation`, including missingness,
remains unchanged in the source attachment.

## Timing evidence and precision

The inspected automaid writer uses `str(starttime)[:23] + 'Z'`, retaining
milliseconds from an already corrected waveform start. Association must not
apply `TimeCorrection` again. Some histories need an explicit
`time_tolerance=0.001` because their waveform/source offsets exceed the
100-microsecond default. The [reader specification](READER_SPEC.md#geocsv-metadata)
explains preserved lexical resolution and timestamp precision.

The user's current MERMAID clock does not establish millisecond physical
accuracy; the 2026-10-14 clarification says finer than 0.01 s has no physical
significance for these instruments. Neither this convention nor the number
of stored digits defines a matching tolerance. Preserve all received digits.
MiniSEED encoding resolution likewise does not establish clock accuracy.

Precise rate and sample interval remain meaningful even with coarser absolute
clock accuracy. For an independently measured first-to-last sample duration,
rate is `(npts - 1) / duration`; a duration covering `npts` full intervals uses
`npts / duration`. Recovering rate from ObsPy's rate-derived `endtime` would
be circular, not independent evidence. Raw-MER/writer/MiniSEED precision and
the provisional rate threshold remain an [open investigation](OPEN_QUESTIONS.md#mermaid-sampling-rate-follow-up).

## Longer traces and subsequent processing

The explicit `allow_first_segment=True` fallback adopts one unique anchor's
position only when source sample ranges cover the longer waveform grid
exactly without gaps after overlaps are counted once. It preserves raw anchor
fields and labels the initial attachment `first_segment`. It performs no
waveform merge and does not reconstruct acquisition contributions. The
[merged-trace policy](OBSPY_MERGED_TRACES.md) specifies all coverage checks,
observed examples, and limits.

Association guarantees end at initial attachment. Later trimming, resampling,
merging, or manual edits do not refresh the row or projections. In particular,
ObsPy can inherit an earlier row while changing `npts` and `endtime`; a
retained `one_segment` label is not revalidated. See [Stream merging and
association](STREAM.md#comparison-with-geocsv-association).

Association does not create SAC headers. Separate
[`geocsv.write_sac`](tutorials/WRITE_SAC.md) exports an associated original
segment to a new file, constructing fresh headers from the attached GeoCSV
values and units. It rejects `first_segment` attachments. Arbitrary GeoCSV
provenance is not serialized by MiniSEED or SAC export.

## Timestamp precision and metadata dependencies

Scientific fields need context before projection or interpretation:

| Group | Required context |
| --- | --- |
| Receiver position | Latitude and longitude, angular units, coordinate convention, and vertical reference. |
| Waveform identity | Complete SNCL; missing codes are not wildcards. |
| Timing and coverage | Start, count, rate/interval, and endpoint convention; endtime is derived. |
| Orientation | Azimuth and dip/inclination, units, and SEED versus SAC convention. No orientation projection is implemented. |
| Pressure-derived depth | Pressure, units, and the adopted approximation/vertical reference; see the SAC writing guide. |
| Calibration/response | Scaling, input/output units, and response definition; a report URL is not an ObsPy Response. |
| Clock correction | Value, seconds units, and whether already applied. Association never applies it again. |
| Provenance | Source/download identity, dataset metadata, and record index together. |

These are interpretation requirements, not a general validation framework.

## Migration and related references

Version 0.18.0 renamed `allow_merge` to `allow_first_segment` without changing
association behavior. Update existing keyword calls. The unused
`project_sac` and `missing_coordinates` options were removed before public
association exposure; neither is part of the API.

- [Stats and metadata mapping boundaries](OBSPY_STATS.md).
- [Historical association audit](../audits/ASSOCIATION.md) and
  [repository audits](../audits/README.md).
- [Fixture inventory and provenance](../data/fixtures/association/README.md).
- [Open scientific questions](OPEN_QUESTIONS.md#association-scientific-questions)
  and [future workflows](FUTURE.md).
