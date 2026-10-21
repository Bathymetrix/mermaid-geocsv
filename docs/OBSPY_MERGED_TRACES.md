# Clipped and combined MiniSEED windows: containing anchors and source coverage

Current opt-in policy, revised 2026-10-21 in version 0.19.0 following the user's
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

| stats.geocsv.association | Initial association performed |
| --- | --- |
| `one_segment` | One row passes strict complete SNCL, start-time, source-count and rate checks. |
| `first_segment` | One containing anchor supplies metadata; clipped source sample ranges cover the downloaded grid without gaps after overlaps are counted once. |

With opt-in enabled, require a unique containing anchor even if one candidate
would also pass strict matching. Two containing rows are ambiguous; do not
prefer the nearer start, identical count, quality, or a row with more metadata.
If the anchor is unique and strict matching passes, retain `one_segment`.
Otherwise use `first_segment` only after coverage validation. Multiple traces
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
   waveform window, including intervals beginning before the waveform. Required
   counts/rates must be valid. Rates retain the provisional inclusive 0.01 Hz
   agreement check around the waveform rate.
4. Place each source's integer sample range on the waveform grid. Clip it to
   `[0, npts)`; source samples outside the downloaded window are permitted.
   Retained first and last source samples must align within `time_tolerance`
   with exactly one waveform sample index. Off-grid or ambiguous placement raises.
5. Require the union of those clipped integer ranges to cover every waveform
   sample without gaps, counting overlaps once. Source SampleCount is not
   rewritten and need not equal waveform `npts`. Full source metadata coverage
   is still required; trimming the window does not waive it.
6. Reject empty or masked waveform data, incomplete coordinates, existing
   destination containers, and other invalid inputs as before. Waveform
   `npts == len(data)` remains required. All matches and projections validate
   before any trace is modified.

The default timing tolerance remains 100 microseconds. Source lexical
resolution does not enlarge it. A window can fail containment or sample-grid
checks even with superficially nearby metadata; do not increase tolerance
blindly. Resampling and reconstruction of altered sampling grids remain
outside this change.

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
`starttime_difference_seconds` is waveform minus source start; an interior
start can legitimately produce a difference of seconds or minutes.
`waveform_sample_count` records the waveform's count at association, separately
from the anchor's original SampleCount. Later processing does not refresh
these values or the geographic projection.

## SAC export

`write_sac` accepts both association labels. It constructs fresh geographic
headers from the anchor and declared units, preserving missing REQ depth.
Identity, association-time start/count, source rate agreement and SAC storage
validity are checked before file creation. No GeoCSV file is reopened.
Associate the final downloaded/clipped/combined window before export; later
length/start changes require a fresh association on an unassociated waveform.
Neither matching nor export proves an unmodified sample history.

## Real-data evidence and limits

The tracked P0045 tutorial merges two original REQ segments and then clips a
second example at both ends. The anchor is source record 101433; record 101434
covers the later portion. Source ranges overlap by 13 samples. The explicit
25 ms grid tolerance accommodates the documented approximately 24.8 ms placement
of the second segment; 1 ms still rejects the grid. The cropped example proves
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
