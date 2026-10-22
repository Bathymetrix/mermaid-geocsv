# Clipped and combined MiniSEED windows: containing anchors and source coverage

Current opt-in policy, revised 2026-10-21 in version 0.21.0 following the user's
MERMAID scientific clarification. The [association tutorial](tutorials/ASSOCIATE.md)
and [SAC tutorial](tutorials/WRITE_SAC.md) give runnable real-data examples.

## Scope and geographic meaning

A download may start or end inside an original acquisition, or combine several
source segments. The strict default remains original-segment matching.
`allow_first_segment=True` permits one same-SNCL source segment containing the
waveform's first sample to supply its anchor metadata, provided GeoCSV sample
ranges cover the complete downloaded waveform grid. Merely choosing the
nearest preceding source row is not sufficient.

The user's MERMAID construction currently produces windows for which receiver
geographic drift is negligible. Under that explicit application convention,
the anchor's latitude, longitude, approximate pressure-derived depth, and
sea-level reference apply to the whole window, including SAC STLA/STLO/STDP/STEL.
The source position still describes the source segment's original first sample;
no interpolation to the clipped start, averaging, or reconstructed trajectory
is performed. This is not a general moving-sensor or arbitrarily long-window
claim. Missing REQ anchor pressure remains undefined, never borrowed from a
later record. The existing declared-unit and missing-DET-pressure rules remain.

Waveform samples, identity, native timing, rate, calibration and quality are
unchanged. Quality M neither proves a particular merge nor selects an anchor.
No merging, gap filling, sample-value comparison or acquisition-lineage
reconstruction is performed by association.

## Matching and labels

| stats.geocsv.association.type | Initial association performed |
| --- | --- |
| `single_segment` | One row passes strict complete SNCL, start-time, source-count and rate checks. |
| `anchor_segment` | One containing anchor supplies metadata; clipped source sample ranges cover the downloaded grid without gaps after overlaps are counted once. |

With opt-in enabled, require a unique containing anchor even if one candidate
would also pass strict matching. Two containing rows are ambiguous; do not
prefer the nearer start, identical count, quality, or a row with more metadata.
If the anchor is unique and strict matching passes, retain `single_segment`.
Otherwise use `anchor_segment` only after coverage validation. Multiple traces
may independently use the same unique source row.

Source preflight still rejects invalid identities and duplicate complete
SNCL/UTC-start/count/rate keys across the supplied datasets. Different counts
may disambiguate strict default matching, but do not resolve containment
ambiguity when opt-in is enabled.

## Containment and complete coverage

For `allow_first_segment=True`:

1. Use complete exact SNCL, including known empty Location, as in strict mode.
   Require zoned source timestamps and positive integer source SampleCount,
   with finite positive source SampleRate declared in hertz to establish a
   source interval. Its inclusive last sample is
   `StartTime + (SampleCount - 1) / SampleRate`, rounded to UTC nanoseconds.
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

See [reader and merge distinctions](STREAM.md#comparison-with-geocsv-association).

## Ambiguity diagnostics and provenance

Errors identify the affected trace indices, SNCL, start/end times, source
path or download URL (or `<memory>` for bare bytes), dataset indices,
zero-based source record indices, and one-based physical starting line numbers.
For multiline CSV records, the line is the start of the record, not an assumed
header offset. The reader retains this immutable mapping as
`metadata.record_line_numbers`, including for in-memory downloads. Artificial
rows added after parsing have no source line and are identified as unknown.

Containing-anchor ambiguity is reported for every affected trace in the batch.
The error leaves the choice to the caller: resolve the source ambiguity or
manually fill headers outside the package. No automatic row selection, header
filling or partial association occurs. Exact duplicate matching keys still
fail source preflight and identify the affected traces and both source rows.

Every attachment retains unchanged raw anchor fields and dataset provenance.
`association.waveform_start_offset_seconds` is waveform minus anchor start; an interior
start can legitimately produce a difference of seconds or minutes.
`association.waveform.sample_count` records the waveform's count at association, separately
from the anchor's original SampleCount. Later processing does not refresh
these values or the geographic projection. The nested report records full
source segments, clipped coverage ranges, physical line references and measured
grid/rate differences; see the [report schema](OBSPY_ASSOCIATION.md#association-report).
These are coverage evidence, not a reconstruction of concatenation history.

## SAC export

`write_sac` accepts both association labels. It constructs fresh geographic
headers from the anchor and declared units, preserving missing REQ depth.
Identity, association-time start/count/rate, source rate agreement and SAC storage
validity are checked before file creation. No GeoCSV file is reopened.
Associate the final downloaded/clipped/combined window before export; later
length/start/rate changes require a fresh association on an unassociated waveform.
Neither matching nor export proves an unmodified sample history.

## Real-data evidence and limits

A tracked [raw P0006 EarthScope response](../tests/fixtures/association/P0006_20180713_earthscope/README.md)
now complements the constructed example below. Its request starts inside the
2018-07-13 DET segment and ends inside the overlapping REQ segment. Reading the
unmodified response produces one 9,403-sample trace. Strict association rejects;
the fallback now succeeds without a timing override, with a
measured 21.813578 ms maximum retained boundary-grid offset. Its coverage ranges
`[0, 4630)` and `[438, 9403)` overlap by 4,192 samples. Offline tests verify
coverage, the association report, unchanged waveform data and anchor SAC export.
This is one preserved service response, not a general archive reconstruction
or overlap-precedence policy. Absolute start and rate thresholds are unchanged.

The tracked P0045 tutorial merges two original REQ segments and then clips a
second example at both ends. The anchor is source record 101433; record 101434
covers the later portion. Source ranges overlap by 13 samples. The automatic
half-sample allowance accommodates the documented approximately 24.8 ms placement
of the second segment without an absolute timing override. The cropped example proves
containment and complete clipped coverage without rewriting anchor fields.
The SAC tutorial exports that clipped window with undefined REQ depth.

A separate historical July 13 P0006 archive response has 10,176 samples and
quality M, with source counts 4,768 and 9,600. The previously recorded 25 ms
check gave 10,176 unique covered samples after removing 4,192 overlapping
samples. That dated observation does not establish which layer combined them
or which source supplied overlapping values. It is not a portable service
response fixture or a new default. See the
[retrieval observations](OBSPY_RETRIEVAL_OBSERVATIONS.md).

Exact range coverage cannot detect already filled waveform gaps, select source
sample values in overlaps, or reconstruct Q/D lineage. These remain separate
[scientific questions](OPEN_QUESTIONS.md#association-scientific-questions).
