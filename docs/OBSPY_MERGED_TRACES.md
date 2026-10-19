# Merged EarthScope traces: first-segment location and sample-coverage validation

Implemented in the sandbox, 2026-10-15; exposed as `geocsv.associate` in 0.15.0.
The other open questions and audit findings remain open.

## Motivation and observed example

An end user may request all available data without distinguishing DET Q from
REQ D. An EarthScope response may expose M quality and waveform coverage whose
original Q/D contributions cannot be reconstructed. M alone does not prove a
particular merge; an unchanged single acquisition may also carry M.

The saved P0006 month response contains one 10176-sample trace beginning
2018-07-13T09:48:03.139965Z. Original GeoCSV row 237 describes the first DET
acquisition (4768 samples, start 09:48:03.139Z); row 238 describes the overlapping
REQ acquisition (9600 samples, start 09:48:31.908Z). The original files retain
Q/D distinctions, but the served trace has M. These observations do not prove
how every served sample was selected or which layer combined the coverage.
See the [inspection evidence](OBSPY_RETRIEVAL_OBSERVATIONS.md).

The user supplies this practical MERMAID convention: drift over the merged
waveform is sufficiently small that a new start/end-based position
interpolation is unnecessary. Adopt the interpolated receiver location of the
first segment for the entire contiguous merged trace. This is an application
convention, not a general claim for all sensors, floats, or arbitrary durations.

## Opt-in call and labels

```python
associate(st, records, allow_merge=False)  # Strict default.
associate(st, records, allow_merge=True)   # Permit first-segment location fallback.
```

The flag does not merge, split, resample, fill gaps, move samples, or
re-interpolate coordinates. Other arguments and no-mixing rules are unchanged.

| stats.geocsv.association | Initial association performed |
| --- | --- |
| `one_segment` | Exactly one row passes the standard SNCL, start-time, sample-count, and sampling-rate checks. |
| `first_segment` | One unique SNCL/start-time row supplies location; source sample ranges cover the longer trace exactly after overlap removal. |

With opt-in enabled, use `one_segment` whenever the standard checks pass.
Use `first_segment` only when the fallback is needed and its conditions pass.
These labels describe the matching performed, not proof of waveform provenance
or sample integrity. They are not recomputed after later ObsPy manipulation.
`association` is a reserved attachment key, alongside `source_record_index`,
`dataset_index`, `metadata`, and `starttime_difference_seconds`; a colliding
GeoCSV column raises. The signed difference is waveform start time minus the
matched row's start time, in seconds, computed from integer UTC nanoseconds.
For `first_segment`, it compares against the anchor row. Positive means the
waveform starts later. This initial-match diagnostic is not a clock correction
and is not recomputed after later waveform changes.

Do not reject or choose a policy solely because quality is M. Default failure
diagnostics include the Stream index, SNCL, start/end times, waveform count
and rate, GeoCSV source paths and candidate row indices, and concrete reasons
such as 10176 versus 4768 samples. A bare Trace need not retain its filename.
All validation finishes before any batch mutation.

## Fallback requirements

When no standard match exists and `allow_merge=True`:

1. Require exactly one algorithm:event anchor matching complete SNCL and the
   trace start within `time_tolerance` (100 microseconds by default). Multiple
   anchors remain ambiguous even when their rates or counts differ.
2. Require a positive integer anchor count smaller than waveform `npts`.
3. Collect same-SNCL event rows whose start times fall between the waveform's
   first and last samples, allowing `time_tolerance` at either boundary.
   Missing or timezone-naive times are ineligible. Each collected row must
   have a positive integer count and a finite positive rate within the
   provisional 0.01 Hz endpoint bounds around the waveform rate.
4. Require exactly one waveform sample index within `time_tolerance` of each
   start time; zero or multiple possible indices raise. Place its exact `SampleCount`
   samples on that grid. No source timestamp, rate, count, or waveform is changed.
   The source's last-sample time, calculated using its declared rate, must also
   lie within `time_tolerance` of the assigned last waveform sample.
   Sample times are rounded to integer nanoseconds for these comparisons.
5. Require every source sample range to lie inside `[0, npts)`. Sort the integer
   ranges and count their union, counting overlapping samples once. Require
   gap-free coverage of exactly `[0, npts)`. There is no sample-count tolerance.
   Gaps, excess coverage, and a missing tail all raise before batch mutation.
6. Reject masked waveform gaps, incomplete coordinates, and existing destination
   containers, as in strict mode.

This validates source-count consistency on the authoritative waveform grid.
It does not compare sample values or identify which source supplied an
individual overlapping sample. It does not infer cropped contributions from
rows starting before the waveform, interpolate samples, fill gaps, or choose a
subset of source rows to force agreement. The finite rate tolerance remains a
compatibility check, not proof of identical acquisition clocks.

The anchor location is adopted for the whole trace under the MERMAID drift
convention. Native waveform fields, samples, and quality remain unchanged.

## Source metadata remains anchor metadata

In the July 13 example with explicit `time_tolerance=0.025`:

| Quantity | Meaning after association |
| --- | --- |
| stats.npts = 10176 | Actual served waveform count; unchanged. |
| stats.geocsv.SampleCount = 4768 | Count of original row 237; unchanged. |
| stats.mseed.dataquality = M | Served waveform quality; unchanged. |
| stats.geocsv.DataQuality = Q | Quality recorded for the anchor acquisition only. |
| stats.geocsv.association = first_segment | Location comes from the first segment. |
| stats.coordinates | Row 237 position adopted for the whole trace, elevation 0. |

Keep all raw row/provenance values unchanged. Pressure, clock correction,
and other attached fields describe the anchor acquisition; they are not
thereby validated as whole-trace metadata.

The location convention covers geographic position and the adopted reference
elevation. It does not independently justify projecting anchor pressure/depth,
clock correction, or all SAC fields onto the merged waveform. SAC stla/stlo
would follow the adopted position; other projections need explicit decisions.
SAC projection remains unimplemented. SAC reference files remain comparison
references, never association inputs.

## Questions deliberately left open

- Can original Q/D contributions and boundaries be recovered reliably later?
- How can coverage be validated more strongly when overlaps were replaced,
  clock grids shifted, gaps filled, or acquisition boundaries obscured?
- Which metadata beyond location can meaningfully describe the entire merge?

The original many-traces-to-one-row rule remains. The opt-in still chooses
one location anchor, not several competing source rows. Incomplete-event
handling and per-call SNCL/time indexing address audit findings 4 and 5;
Version 0.15.0 exposes the same matching behavior through `geocsv.associate`;
see the [association tutorial](ASSOCIATION_TUTORIAL.md). SAC projection remains
unfinished work.

## Verification

Tracked synthetic cases verify contiguous segments, overlapping ranges counted
once, exact integer counts, one-sample shortages/excesses, gaps, off-grid
starts, inclusive timing boundaries, incomplete metadata, and batch atomicity.
The saved July 13 EarthScope trace was checked separately against the complete
rebuilt history. Source row 238 maps to output sample index 576, with a start
residual of -21,813,431 ns. A 1 ms tolerance rejects that alignment. An explicit
25 ms tolerance passes the start/last-sample checks and gives exact coverage:
4768 + 9600 - 4192 overlapping samples = 10176 unique samples. The anchor is
row 237; waveform count and M quality remain unchanged. The 25 ms value is an
explicit override for this check, not the default or an inferred uncertainty.
The local download is not required by tracked tests.
