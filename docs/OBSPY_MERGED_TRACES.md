# Merged EarthScope traces: first-segment location association

Implemented in the sandbox, 2026-10-15; not exposed as a public package API.
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
See the [inspection evidence](../sandbox/obspy_association/OBSERVATIONS.md).

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
| `first_segment` | One unique SNCL/start-time row anchors a longer trace and supplies the location adopted for the whole trace. |

With opt-in enabled, use `one_segment` whenever the standard checks pass.
Use `first_segment` only when the fallback is needed and its conditions pass.
These labels describe the matching performed, not proof of waveform provenance
or sample integrity. They are not recomputed after later ObsPy manipulation.
`association` is a reserved attachment key, alongside `source_record_index`,
`dataset_index`, and `metadata`; a colliding GeoCSV column raises.

Do not reject or choose a policy solely because quality is M. Default failure
diagnostics include the Stream index, SNCL, start/end times, waveform count
and rate, GeoCSV source paths and candidate row indices, and concrete reasons
such as 10176 versus 4768 samples. A bare Trace need not retain its filename.
All validation finishes before any batch mutation.

## Fallback requirements

When no standard match exists and `allow_merge=True`:

1. Require exactly one algorithm:event row matching complete SNCL and the
   trace's start time under the existing time tolerance. Do not select a
   nearest, arbitrary earlier, or later overlapping row. Multiple start-time
   anchors remain ambiguous even if their counts or rates differ.
2. Require finite positive rates differing by at most the provisional 0.01 Hz.
3. Require a positive integer anchor SampleCount and strictly more samples in
   the trace. Require trace duration `(npts - 1) / sampling_rate` to cover at
   least the anchor's corresponding duration. This compares elapsed durations
   after the start-time check; it does not impose exact source timestamp equality.
4. Reject masked gaps. Separate traces across gaps are associated independently;
   this function does not join them. A uniform Trace cannot reveal upstream
   gap filling or every obscured acquisition boundary.
5. Require a complete valid latitude/longitude pair and absent destination
   containers, as in strict mode.

Assign latitude/longitude from the anchor to the whole trace, with the
existing sea-level elevation convention. Preserve waveform identity, samples,
start/end times, sampling rate, npts, calibration, and MiniSEED quality.
Retain the independent GeoCSV quality value as source metadata.

These checks make the fallback narrower than accepting every count mismatch.
They do not prove that additional samples form a legitimate merge or identify
which original acquisitions contributed. The caller explicitly chooses the
representative-location convention for supplied coverage. Shortened traces
and arbitrary start-time shifts receive no special accommodation.

## Source metadata remains anchor metadata

In the July 13 example:

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
package exposure and SAC projection implementation remain separate unfinished
work.

## Verification

Tracked synthetic tests exercise both labels, opt-in enforcement, ambiguous
anchors, rate/time/SNCL mismatches, insufficient coverage, masked gaps, missing
coordinates/count, preservation of native metadata, and batch atomicity.
The saved July 13 EarthScope trace was also checked against the full rebuilt
P0006 history: strict mode rejects 10176 versus 4768 samples; opt-in associates
row 237 as `first_segment`, preserves M and the waveform count, and projects
latitude -14.387563, longitude -179.504105, elevation 0. This local download is
not required by the tracked test suite.
