# ObsPy Stream and waveform merging

Source review, 2026-10-16. This describes `/Users/jdsimon/programs/obspy/`
at commit `50033e1daf95233cd4f30e95a49c37fd50be2ccd`, not a promise about
all ObsPy versions. The checkout was clean. Runtime examples use this
repository's separately installed ObsPy 1.5.1; its executable implementations
of `Stream.merge`, `_cleanup`, `_merge_checks`, and `Trace.__add__` match the
checkout when docstrings are excluded.

Primary sources at that revision:

- [Stream implementation](https://github.com/obspy/obspy/blob/50033e1daf95233cd4f30e95a49c37fd50be2ccd/obspy/core/stream.py):
  `Stream`, `merge`, `_merge_checks`, `_cleanup`, `get_gaps`, `split`.
- [Trace implementation](https://github.com/obspy/obspy/blob/50033e1daf95233cd4f30e95a49c37fd50be2ccd/obspy/core/trace.py):
  `Stats`, `Trace.__add__`, `Trace.__setattr__`.
- [Stream tests](https://github.com/obspy/obspy/blob/50033e1daf95233cd4f30e95a49c37fd50be2ccd/obspy/core/tests/test_stream.py):
  merge gaps, overlaps, incompatible headers, cleanup, and misalignment cases.

Companions: [Stats](OBSPY_STATS.md), [association design](OBSPY_ASSOCIATION.md),
and [our first-segment location policy](OBSPY_MERGED_TRACES.md).

## Container semantics

A `Stream` is a list-like collection of `Trace` objects, not necessarily one
continuous waveform or even one channel. Several traces can share an ID
while differing in time, rate, or metadata. A trace's `id` is
`network.station.location.channel`; it contains no MiniSEED quality flag.
The codes are often called SNCL; ObsPy's string order is NSLC.

Constructing a Stream from traces, appending/extending it, adding Streams,
and selecting traces retain references to those traces. `stream_a + stream_b`
collects traces; it does not merge their samples. `Stream.copy()` deep-copies
the traces and data. `select()` returns a new container sharing traces;
`slice()` returns new traces whose sample arrays can share data;
`trim()` changes the supplied Stream in place.

## `merge` signature and result

```python
Stream.merge(self, method=0, fill_value=None, interpolation_samples=0, **kwargs)
```

`merge()` mutates the Stream **and returns `self`**. The inspected docstring's
statement that it returns nothing disagrees with its implementation. Work on
`stream.copy()` when the original must remain available. The operation is
not transactional: cleanup can change ordering, remove empty traces, merge
data, or shift a referenced input trace before later work fails.

Merge groups by exact trace ID. For methods `0` and `1`, nonempty traces of
each ID must have exactly equal sampling rates, NumPy data types, and
calibration factors. No rate tolerance or resampling is provided. MiniSEED
Q/D/M, coordinates, and source-row attachments are not grouping criteria.
Different IDs remain separate.

Every call first invokes `_cleanup(**kwargs)`, including methods `0` and `1`.
At this revision its sole argument is `misalignment_threshold=0.01`.
It can be passed through the public method as
`stream.merge(misalignment_threshold=0.01)`; the actual name is neither
`misalign_tolerance` nor `time_tolerance`.

## Three merge methods

| Method | Effect |
| --- | --- |
| `-1` | Cleanup only. Join exactly adjacent traces and consistent overlapping/contained traces, subject to the grid checks below. Leave real gaps and conflicting overlap values in separate traces. No filling or overlap interpolation. |
| `0` (default) | After cleanup, combine traces of each ID. Equal overlaps are retained once; conflicting overlap samples become gaps, represented by masks or `fill_value`. A conflicting contained trace creates a gap over its extent. |
| `1` | After cleanup, combine traces of each ID. For a partial conflicting overlap, prefer the later-starting trace, optionally interpolating the transition. A conflicting fully contained trace is discarded; it does not replace the containing trace's valid data. |

Masked missing samples can be supplied by valid samples in another trace;
the overlap descriptions above concern conflicting valid values. The source
uses ID/start/end sorting; equal starts are consequently ordered by end time,
and equal timing does not provide an independent scientific precedence rule.

With methods `0` and `1`, real gaps use:

| `fill_value` | Representation |
| --- | --- |
| `None` | Masked missing samples. |
| A number | Samples filled with that value. |
| `"latest"` | Last sample value before the gap. |
| `"interpolate"` | Linear interpolation between gap boundaries. |

`interpolation_samples` is a different control: it smooths the overlap
transition only for method `1`. Zero means no smoothing; a positive integer
uses that many overlap samples, capped at overlap length; `-1` uses the whole
overlap. Gap and overlap interpolation preserve the input dtype, so integer
waveforms do not acquire fractional-valued storage.

## Sampling-grid alignment and timing

For a positive sampling rate `f`, `delta = 1 / f`. The left trace's last
sample is `endtime = starttime + (npts - 1) * delta`; the expected next
sample is `endtime + delta`.

Cleanup's `misalignment_threshold` is a **dimensionless fraction of delta**,
documented from 0 to 0.5. Its default `0.01` corresponds to:

| Sampling rate | Interval | Default alignment threshold in seconds |
| --- | --- | --- |
| 20 Hz | 0.05 s | 0.0005 s (0.5 ms) |
| 40 Hz | 0.025 s | 0.00025 s (0.25 ms) |
| 100 Hz | 0.01 s | 0.0001 s (0.1 ms) |

Cleanup computes the right trace's start relative to the expected next sample
and examines the residual modulo `delta`. For a sufficiently small residual
near either end of a sample interval, it moves the right trace's start onto
the left trace's grid. It changes timestamp interpretation without
interpolating/resampling the sample values. For a positive gap larger than
`misalignment_threshold * delta`, this correction is skipped. Consistent
overlaps are then joined only if the grid and data checks pass.

This is not an absolute bound on the difference between trace start times:
two traces can start seconds apart yet share a grid. Nor is it the only
timing rule used by a full merge. `Trace.__add__` converts the separation into
samples with `round_away` rounding, then classifies overlap, adjacency, or gap.
Thus `misalignment_threshold=0` disables cleanup snapping but does **not**
make methods `0` and `1` strict timestamp-preserving operations.

Two implementation details matter when interpreting the threshold:

- Cleanup uses inclusive comparisons for snapping but a strict `<` for its
  overlap grid check. At threshold zero, even identical overlapping traces
  remain separate in cleanup-only mode at this revision. Exactly adjacent
  traces can still join through a separate branch. Zero is not a universal
  "merge all and only exactly aligned traces" mode.
- Cleanup mixes UTCDateTime arithmetic and floating-point timestamp/modulo
  operations. It does not implement our associator's integer-nanosecond
  comparison. Decimal boundary behavior should be tested for the rate and
  timestamps of interest rather than inferred from a single formula.

## Minimal executable example

```python
import numpy as np
from obspy import Stream, Trace, UTCDateTime

start = UTCDateTime("2020-01-01T00:00:00Z")
header = dict(network="MH", station="TEST", location="00", channel="BDH",
              starttime=start, sampling_rate=20.0)
left = Trace(np.array([1, 2, 3, 4], dtype=np.int32), header)
right = Trace(np.array([5, 6, 7, 8], dtype=np.int32),
              dict(header, starttime=start + 0.2004))
original = Stream([left, right])

merged = original.copy()
assert merged.merge(method=-1, misalignment_threshold=0.01) is merged
assert len(merged) == 1
assert merged[0].data.tolist() == [1, 2, 3, 4, 5, 6, 7, 8]
assert merged[0].stats.npts == 8
assert merged[0].stats.endtime == start + 0.35
assert original[1].stats.starttime == start + 0.2004

# Conflicting overlap: method 0 masks it; method 1 uses the later trace.
overlap = Trace(np.array([9, 10, 11, 12], dtype=np.int32),
                dict(header, starttime=start + 0.1))
conflict = Stream([left.copy(), overlap])
masked = conflict.copy().merge(method=0)
replaced = conflict.copy().merge(method=1)
assert masked[0].data.tolist() == [1, 2, None, None, 11, 12]
assert replaced[0].data.tolist() == [1, 2, 9, 10, 11, 12]
```

The 0.4 ms displacement is within 0.5 ms at 20 Hz. Cleanup adopts the left
grid; its merged samples span 0 through 0.35 seconds. This is a waveform
timing decision, not merely permission to attach metadata.

## Metadata and scientific provenance

The pairwise merge starts a new Trace with a deep copy of the earlier
trace's Stats. Data assignment updates `npts` and derived `endtime`; there
is no generic combination of nested headers from the two traces. In
particular:

- An earlier `stats.geocsv`, `stats.coordinates`, `stats.sac`, or
  `stats.mseed` can survive while describing only the earlier input.
- Q and D traces of the same ID can merge. `merge()` does not derive M
  quality or reconstruct contributing acquisitions from their flags.
- Earlier processing history is inherited, rather than combining both
  histories. Neither `merge` nor `Trace.__add__` adds a processing entry.
- A filled gap becomes ordinary sample values. An unmasked result is not
  evidence that no gap filling or overlap replacement occurred upstream.

Use `get_gaps()` to inspect gaps/overlaps and `split()` to obtain contiguous
unmasked traces from a masked result. Neither reconstructs discarded
samples, hidden fills, source metadata, or original acquisition identity.
These limitations are central to the association comparison; merging an
already associated trace does not revalidate its association label.

## Comparison with GeoCSV association

This section consolidates the 2026-10-16 comparison, updated for the
0.18.0 `allow_first_segment` name. It uses the same pinned ObsPy checkout
and separately installed 1.5.1 described above.

ObsPy merge combines waveform samples on a shared grid. GeoCSV association
identifies one source row and attaches metadata while preserving samples and
native headers. Their timing controls compare different quantities:

| Concern | ObsPy merge/cleanup | `geocsv.associate` |
| --- | --- | --- |
| Timing control | `misalignment_threshold=0.01`, a fraction of sample interval. | `time_tolerance=0.0001`, inclusive absolute seconds between waveform and source starts. |
| Timing effect | Cleanup can shift starts; full merge rounds separation to sample counts. | Neither waveform nor source times change; comparison uses UTC integer nanoseconds. |
| Rates | Exactly equal per trace ID. | Source rate within inclusive 0.01 Hz endpoint bounds, provisionally. |
| Counts and overlaps | Produces new coverage under `method`/`fill_value` choices. | Exact original count by default; explicit fallback validates coverage without combining samples. |
| Metadata | Earlier headers can survive without reconciliation. | Fresh source-row and coordinate containers; existing destinations raise. |
| Result | Mutates Stream/traces, returns `self`, and is not transactional. | Validates the full batch before attachment, returns `None`. |

For a seconds tolerance `t` at rate `f`, `t * f` gives the same numeric
fraction of a sample interval, **not an equivalent test**. At 20 Hz, 1 ms
corresponds to 0.02 of an interval. Starts seconds apart may share a sampling
grid; strict association compares each waveform's first sample to its source
start. The opt-in containing-anchor policy instead requires that sample to lie
within one unique source interval and validates clipped source-grid coverage.
The two appearances of 0.01 in cleanup's fraction and association's
Hz bound are dimensionally unrelated. Neither threshold measures clock accuracy.
The queried `misalign_tolerance` is not an option in the inspected merge code.

`stats.geocsv.association.waveform_start_offset_seconds` records waveform minus source
start at initial association. It is a diagnostic, not an applied alignment
shift. Raw source names such as `StartTime` remain intentional provenance,
not alternate spellings to replace with core Stats names.

Ordering has consequences:

1. **Associate, then merge:** ObsPy may inherit only the earlier source row
   and coordinates while increasing count/duration. A retained `single_segment`
   label is not revalidated or converted to `anchor_segment`; contributing rows
   are not collected.
2. **Merge, then associate:** strict matching normally rejects the changed
   count. `allow_first_segment=True` can adopt a unique anchor's location only
   with the exact source-grid coverage checks in the
   [fallback policy](OBSPY_MERGED_TRACES.md). It cannot recover discarded
   overlaps, hidden fills, or acquisition identities. Masked gaps raise.

Quality is not part of either grouping/matching identity. Calling association
again on retained destinations raises; there is no implicit clearing or
reconciliation workflow. SAC export is a separate operation for associated
waveforms with either association label, not a merge option. Associate the
final clipped/combined window first. Use the
[association guide](tutorials/ASSOCIATE.md) for the complete public contract.

## Verification limits

This review inspected the checkout's implementation and nearby tests, then
ran synthetic checks in the repository `.venv` for the example, return value,
overlap methods, masks/filling, timing shifts, zero-threshold behavior,
header inheritance, and exact rate/calibration/dtype requirements. It did
not build the ObsPy checkout or run its full test suite. No ObsPy source or
association behavior was changed.


### MiniSEED record assembly and half-sample association coverage

Rechecked 2026-10-21 at ObsPy source commit
`50033e1daf95233cd4f30e95a49c37fd50be2ccd`, separately from installed 1.5.1:
`obspy/io/mseed/src/obspy-readbuffer.c` sets its record-join tolerance to half
an interval. This reader behavior is separate from `Stream.merge` cleanup's
`misalignment_threshold`. A single parsed Trace does not prove all input record
timestamps lay on that Trace's ideal grid.

The preserved P0006 response demonstrates this distinction. The first record
in its retained REQ portion starts at 09:52:01.434792000 UTC; its corresponding
sample on the parsed Trace grid is 09:52:01.455932718, a -21.140718 ms offset.
The local original DET/REQ starts already have a 21.040431 ms phase difference
at identical rates. Thus the association offset cannot be assigned wholly to
an EarthScope timestamp change. Archive overlap selection and reader assembly
are separate stages; the legacy LOG/MER correction's contribution is not
established by this comparison.

Since 0.21.0, association uses unique nearest-sample placement within half a
waveform interval for source coverage, not `time_tolerance`, with strict
`abs(offset) < 0.5 / waveform_sampling_rate` and exact midpoint rejection. This resembles
reader joining but compares source ranges to the assembled Trace's grid, not
successive record joins. Source counts fix the placed ranges; excessive retained
endpoint drift, midpoint ambiguity and uncovered waveform samples still raise.
Native times and samples remain unchanged, and measured boundary offsets are
recorded. This policy does not modify strict start matching, anchor containment,
source rate agreement, or quality handling. See the [coverage policy](OBSPY_MERGED_TRACES.md).

The half-sample scale comes from `obspy-readbuffer.c`'s `0.5 * hpdelta`
record-join rule. Association's rejection of exact midpoint ties is stricter
than the reader's inclusive join comparison.
