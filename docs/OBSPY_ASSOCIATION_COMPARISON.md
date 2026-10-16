# ObsPy merging versus the association prototype

Report, 2026-10-16. This is a comparison and API design discussion, not an
implemented rename or policy change. The association interface remains in
[`sandbox/obspy_association/associate.py`](../sandbox/obspy_association/associate.py),
outside the public reader API. ObsPy evidence comes from the local checkout
at `50033e1daf95233cd4f30e95a49c37fd50be2ccd`; see
[Stream and merge](STREAM.md) and the verified [Stats survey](OBSPY_STATS.md).

## Main finding

ObsPy compatibility is a useful design goal, but matching names is useful
only when their scientific meaning agrees. Our `time_tolerance` and ObsPy's
`misalignment_threshold` both accommodate small timing discrepancies, but
compare different quantities, use different units/defaults, and have different
side effects. Renaming ours to theirs without a semantic change would make
the interface less clear. The queried name `misalign_tolerance` is not the
option in the inspected `Stream.merge`/`_cleanup` implementation.

ObsPy merges waveform samples onto a shared sampling grid. We identify a
unique source row and attach its metadata while preserving the waveform.
Neither operation substitutes for the other.

## Behavior and parameter comparison

| Concern | ObsPy `Stream.merge` | Current `associate` prototype |
| --- | --- | --- |
| Inputs | Traces already in `self`. | `waveforms`: a Trace or Stream; `records`: frames from `geocsv.read`. |
| Identity | Groups by `Trace.id` (network.station.location.channel). | Exact equality of all four identity columns; no missing-code wildcards. |
| Time control | `misalignment_threshold=0.01`, passed through `**kwargs` to `_cleanup`. | `time_tolerance=None`, or explicit finite nonnegative seconds. |
| Quantity compared | Sampling-grid phase residual, with adjacency/gap conditions. | Absolute difference between waveform and GeoCSV row start times. |
| Default timing scale | Fraction of waveform sample interval. | Each source timestamp's lexical resolution from immutable GeoCSV metadata. |
| Time side effect | Cleanup can shift right-hand trace start times; full merge rounds separation to sample counts. | Preserves source and waveform times; compares UTC integer nanoseconds. |
| Rate | Exact equality between traces of an ID. | Absolute waveform/source difference <= `SAMPLE_RATE_TOLERANCE_HZ = 0.01` Hz, a provisional internal constant. |
| Count | Produces new sample coverage and count. | Requires source `SampleCount == stats.npts == len(data)` by default. |
| Calibration/dtype | Must agree for full merge. | Neither is matched to a source replacement; native waveform calibration and data remain unchanged. |
| Overlaps | `method=-1`, `0`, or `1` controls cleanup/conflict handling. | Does not join, compare, discard, or interpolate overlapping waveform samples. |
| Gaps | Masked by default; `fill_value` can supply values. | Rejects masked missing samples; cannot detect every previous fill. |
| Longer coverage | Constructed through merging, including overlap/gap policy. | `allow_merge=True` only permits a unique first-segment location anchor for an already longer trace. |
| Metadata | Generally inherits earlier trace headers; does not reconcile arbitrary namespaces. | Creates fresh `stats.geocsv` and complete `stats.coordinates`; existing destinations raise. |
| Ambiguity/cardinality | Reduces compatible same-ID traces; it has no source-row matching contract. | Exactly one eligible row per trace; several traces may independently use that row. |
| Quality | MiniSEED Q/D/M is not in the grouping ID. | Retains source `DataQuality` separately from waveform quality; neither is a match filter. |
| Mutation/result | Changes Stream/traces; returns `self`; no transaction guarantee. | Validates the full batch before attaching metadata; returns `None`. |
| History | Merge itself appends no `stats.processing` entry. | Preserves existing processing history; records initial association provenance separately. |
| SAC | Existing headers can be inherited without general reconciliation. | `project_sac=False`; `True` is reserved and raises before mutation. SAC inputs remain outside development scope. |

The source row's names (`StartTime`, `SampleRate`, `SampleCount`, etc.) remain
raw GeoCSV column names under `stats.geocsv`. Differences from core Stats
names are intentional provenance, not candidates for spelling alignment.
The reader's `MethodIdentifier` is also unrelated to merge's integer `method`.

## Timing: similar motivation, different semantics

For our default, a row written as `...03.139` has a resolution of 0.001 s.
Association accepts an absolute start-time difference **up to and including**
0.001 s, subject to identity, rate, count, and uniqueness checks. A row written
as `...03.139000` instead has a 0.000001 s default tolerance despite the same
timestamp value. This follows the current implementation; it does not imply
a measured uncertainty, a half-bin rounding model, or an accuracy estimate.
The MERMAID 0.01 s physical-resolution convention is not this default.

For cleanup, let `delta = 1 / sampling_rate` and let `p` be
`misalignment_threshold`. Its nominal timing scale is `p * delta` seconds.
At 20 Hz, `p=0.01` gives 0.0005 s. At 100 Hz it gives 0.0001 s. The scale
changes with waveform rate, not the number of timestamp digits.

Converting a seconds tolerance `t` to the same numeric scale would require
`p = t / delta = t * sampling_rate`. For `t=0.001 s` at 20 Hz, `p=0.02`,
not `0.001`. This is a **unit conversion only**, not an equivalence of tests:

- Two traces starting many seconds apart can share the same sampling grid.
  Cleanup compares their grid phase; association compares each waveform's
  first sample with a source start and would not accept an offset of seconds
  under a millisecond tolerance.
- Cleanup may move sample timestamps; association never does.
- Cleanup's documented threshold range is 0 through 0.5; association accepts
  any finite nonnegative seconds override. Neither implies a scientifically
  justified tolerance merely because a value is accepted.
- Zero means exact integer-nanosecond equality in association. In ObsPy,
  zero disables cleanup snapping but has overlap-branch subtleties and does
  not disable full merge's sample-count rounding; see [Stream](STREAM.md).

`stats.geocsv.starttime_difference_seconds` is signed waveform-minus-source
start time, recorded at association. It is a diagnostic, not a shift that
was applied. It is not analogous to a cleanup alignment correction.

The two occurrences of `0.01` in association rate checking (Hz) and ObsPy
cleanup (fraction of a sample interval) are dimensionally unrelated. A small
rate difference also accumulates timing drift with duration; acceptance by
our provisional rate check does not imply merge compatibility or agreement
of whole-trace sampling grids.

## `allow_merge` is the clearest naming question

Our flag does not perform a merge. With no standard match, it permits one
unique SNCL/start-time anchor with compatible rate and positive integer
count, strictly fewer samples than the trace, and an anchor duration no
greater than the trace duration. Masked gaps still raise. It adopts the
anchor's receiver position at the first sample for the entire trace and
labels the result `first_segment`; all raw anchor fields stay unchanged.
It does not verify contributing acquisitions or prefer rows by M/Q/D quality.
See the [complete fallback policy](OBSPY_MERGED_TRACES.md).

**Recommendation for a future design discussion:** consider a name such as
`allow_first_segment` rather than borrowing ObsPy's `method`, `fill_value`,
or `interpolation_samples`. That would communicate the implemented metadata
policy more directly. This report does not choose or introduce a replacement.

## Ordering association and merge

1. **Associate original traces, then merge:** initial associations are valid
   for their original inputs. ObsPy can then inherit only the earlier row
   and coordinates while increasing core `npts`/`endtime`. A retained
   `one_segment` label is not revalidated and does not become `first_segment`.
   Merge does not collect contributing rows or create association provenance.
2. **Merge, then associate:** strict mode normally rejects the changed count.
   The explicit fallback can accept an eligible first-segment anchor, but
   cannot recover discarded overlaps, hidden fills, or acquisition identity.
   Masked gaps are rejected. Cleanup may also have changed timings used for
   matching, so association inspects the resulting waveform as supplied.

Calling association again on a retained attachment raises because destination
containers already exist. There is no automatic clearing/reconciliation
workflow. For current development, use original MiniSEED traces for strict
association, or explicitly choose the documented location fallback on an
eligible longer trace. Treat ObsPy waveform transformations as boundaries
after which association guarantees need reassessment.

## Style alignment and possible future upstream work

The checkout's `misc/docs/source/coding_style.rst` and `CONTRIBUTING.md`
favor meaningful snake_case names, familiar NumPy aliases, grouped imports,
focused examples/tests, and reStructuredText API parameter documentation.
Its reference semantics and method return values must be inspected per
operation; even `merge`'s prose disagrees with its return statement.

| Candidate | Recommendation; no change made |
| --- | --- |
| `time_tolerance` | Keep the seconds meaning explicit. `starttime_tolerance` could make its scope clearer if later renamed; do not borrow `misalignment_threshold` for the present semantics. |
| `allow_merge` | Discuss a name reflecting permission to use the first segment's metadata, rather than waveform manipulation. |
| `SAMPLE_RATE_TOLERANCE_HZ` | Its unit is explicit. There is no matching merge parameter to imitate; the provisional scientific criterion needs review before any public exposure. |
| `waveforms`, `records` | Reasonable descriptive standalone-function names. Moving into a method or ObsPy package is a separate ownership/API decision. |
| `project_sac` | An explicit projection boundary, with no equivalent merge option. Keep its reserved status visible. |
| Return `None` versus `self` | ObsPy merge supports chaining. Changing our return contract could be considered separately; a name cleanup does not justify it automatically. |
| Raw source names versus Stats names | Preserve raw columns and deliberate projections; never mechanically rename source metadata to resemble Stats. |

There is no need to introduce a policy registry, generalized tolerance
system, or merge wrapper for this comparison. Possible inclusion in ObsPy
should motivate compatible terminology and a focused adapter, while package
placement, supported GeoCSV scope, dependencies, licensing, and contribution
acceptance remain separate questions. No upstream suitability or acceptance
is established by this review.

## Verification and scope

The review read the current sandbox implementation, relevant tests and
policies, and pinned ObsPy source and nearby tests. Runtime probes checked
the distinctions described in [Stream](STREAM.md). Running
`.venv/bin/pytest tests/test_associate_synthetic.py -q` passed all 47 existing
synthetic association tests; the Stream example and relative documentation
links also passed checks. No parameters, variable names, matching rules,
package version, or waveform data were changed. Remaining recommendations
are design options for a later decision.
