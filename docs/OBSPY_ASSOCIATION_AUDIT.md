# Adversarial association audit and API readiness

Audit performed 2026-10-14 against the sandbox `associate.py`. This records
findings before remediation and their dispositions; the function remains an
experimental sandbox interface, not an exposed package API.

## SAC placeholder removal, 2026-10-16

Version 0.14.1 removes the unused `project_sac` argument and its
`NotImplementedError` placeholder from the sandbox associator. The historical
sections below describe the former option. SAC projection remains deferred
work, recorded in [future workflows](FUTURE.md#project-associated-metadata-into-sac-headers);
the mapping and independent comparison plan are retained. No package API is
exposed by this removal.

## Portable real-data verification update, 2026-10-16

The [current repository audit](../audits/05.md) supersedes the historical
verification counts below. Tracked GeoCSV subsets now supply every real-data
association test: all 296 tests pass with ObsPy installed, including from a
copy containing only files eligible for Git. Full histories remain ignored
and unchanged. A separate full-history check verifies subset extraction and
unique matches for the 18 sampled waveforms; see the
[fixture provenance](../data/fixtures/association/README.md).

## Empty-location and preflight update, 2026-10-16

Version 0.14.0 preserves known empty strings in string-valued `Location`, while
explicit missing markers remain missing. Only Location may be empty in a valid
association identity. Source preflight rejects invalid event identities and
duplicate complete SNCL/UTC-time/count/rate keys across datasets. All supplied
trace matches validate before projections. Same SNCL/time with different counts
can still be uniquely matched. These replace the former universal empty-cell
missingness for Location; other columns keep their prior policy. See the
[current reader rules](READER_SPEC.md#field-types-and-missing-values) and
[association rules](OBSPY_ASSOCIATION.md#matching-original-traces).

## Timing and coverage policy update, 2026-10-16

Version 0.13.0 replaces the source-resolution default below with a fixed
100-microsecond absolute tolerance (`time_tolerance=0.0001`). `None` is no
longer accepted; source lexical resolution remains reader metadata, not a
matching requirement. Current millisecond-rendered histories require an
explicit tolerance when their offsets exceed the default. Rate checks use
inclusive floating-point endpoints around the unchanged 0.01 Hz threshold.
The first-segment fallback now requires exact gap-free source sample coverage
on the waveform grid, with overlapping samples counted once. Start and
last-sample alignment must satisfy the chosen time tolerance. The historical
remediation details and test counts below describe earlier implementations.
See [current matching rules](OBSPY_ASSOCIATION.md#matching-original-traces) and
[merged coverage](OBSPY_MERGED_TRACES.md) for the active contract.

## Input scope clarification

Original MiniSEED-derived traces are the association inputs. Paired SAC files
are read separately only as reference outputs: after MiniSEED -> GeoCSV
association -> optional SAC header projection, compare the agreed projected
keys with the reference trace's inherited `stats.sac`. SAC-input association
is outside scope until further instruction. SAC reference values must never
be used to construct, match, or fill the associated MiniSEED metadata.

This narrows the interpretation of finding 1. Its adversarial trace had
manually pre-populated `stats.coordinates`; it was not a freshly read MiniSEED
fixture and was not a SAC-input test. No cross-trace/loop leakage was found.
There was no inherited coordinate contamination observed in the intended
MiniSEED workflow. The original P1 rating describes a conditional scientific
failure for pre-populated inputs, not an observed in-scope MiniSEED defect or
a separate blocker requiring SAC-input support. The fresh-state and complete
coordinate-pair rules remain useful and have been implemented. Findings
about CI coverage, timestamp comparison, invalid-row handling, and batch
performance still apply to MiniSEED input.

## Original findings

1. **P1: coordinate projection can mix sources.** The helper copied existing
   `stats.coordinates` before projecting each available GeoCSV component.
   A missing source latitude, old latitude -80 degrees, and new longitude
   7.319633 degrees produced a successful but unverified coordinate pair.
   ObsPy initializes no default geographic coordinates: inheritance happened
   in our code. Complete GeoCSV coordinates are not enough evidence that this
   behavior is safe when a future row is incomplete.

2. **P1 for API readiness: CI exercises no association behavior.** All tests
   calling the function depended on ignored histories. The existing local
   suite passed 191 tests, but a fresh tracked-files checkout passed 157 and
   skipped 34. Header checks ran, while matching, ambiguity, batch failures,
   coordinate validation, and preservation checks skipped.

3. **P2: time bins do not exactly reproduce writer rendering.** A bin was a
   half-open 0.001-second interval used only during comparison. A UTCDateTime
   at .000999600 prints as .001000 with default precision. The actual writer
   expression `str(time)[:23] + 'Z'` consequently produced .001Z, while the
   nanosecond-floor bin comparison rejected that row. This was an adversarial
   Trace counterexample, not an observed sampled MiniSEED failure. Separately,
   .000100 and .000900 source/waveform times were accepted within one bin even
   when source precision distinguished them. Input values themselves were
   not rewritten. The reader already retained nine-digit timestamps.

4. **P2: unrelated incomplete events can prevent a unique match. Resolved in
   the sandbox.** A valid matching event plus a same-SNCL event with missing
   StartTime previously caused a fatal error on the incomplete row.
   Count/rate missingness instead eliminated candidates, so invalid-row policy
   was inconsistent.

5. **P2 performance concern: batch matching repeats event scans. Resolved in
   the sandbox.** The same SNCL's rows were selected by rescanning every event
   for each trace. A synthetic benchmark excluding parsing took 0.158 s at 100
   traces/rows and 2.008 s at 400. One sampled float history contains 1,830
   events.

## Remediation of findings 4 and 5

Rows with missing or timezone-naive `StartTime`, or without source timestamp
resolution metadata, are now ineligible candidates rather than call-wide
errors. A valid unique match can proceed. When a trace has no unique match,
the error lists skipped incomplete rows with source, dataset, record index,
and reason. Missing count/rate values remain candidate mismatch reasons once
the row's time is eligible. This policy cannot establish whether a row lacking
time would otherwise have matched; its omission remains visible in failure
diagnostics.

At dataset preparation, event rows are grouped by complete SNCL and sorted by
UTC start time. Binary search selects a broad window using the maximum relevant
source resolution (or the explicit tolerance); the existing per-row tolerance,
count, rate, and ambiguity checks then run unchanged. This avoids inspecting
every same-SNCL event for every trace. The index is local to one `associate`
call and adds no persistent index or public interface.

A microbenchmark on the complete 1,830-event P0048 history, with lookup/parsing
separated and 400 repeated traces, took 8.922 s for full SNCL/time scans and
0.024 s to build the sorted index and perform binary-search lookups (377x in
this workload). The traces intentionally repeated one valid event to model
repeated requests; this isolates lookup cost and is not an end-to-end waveform
throughput estimate.

## Remediation of the first three findings

### Complete coordinate pairs

The final rule is strict: the projection starts empty and both Latitude and
Longitude are required. Each requested destination container must be absent,
even if empty or apparently equivalent. Existing values cannot supply a missing
component. No container is merged, overwritten, or deleted. All checks complete
before any trace is mutated. A complete pair gets source latitude/longitude
and the explicit sea-level elevation=0 convention.

An intermediate remedy offered `missing_coordinates="warn"`; this was removed
at the user's request in favor of simple rules, clear projections, and no
surprise side effects. Processing history is not a projection or one of the
ten core Stats defaults; its existing list is left untouched. See the
[source-based reference](OBSPY_STATS_REFERENCE.md).

### Reproducible unit coverage without cutting real histories

`tests/fixtures/association/synthetic.geocsv` is entirely invented. No lines
were chosen from real histories. Tests construct trace time/identity/rate/count
headers independently and search the entire synthetic dataset, including a
GPS row sharing an event's time/identity, multiple stations, incomplete pairs,
and timestamps of different precision. These tracked unit cases exercise the
function on CI. Complete real histories remain local integration fixtures.

### Full precision with a source-resolution default

The reader never imposed millisecond truncation. Version 0.11.0 adds immutable
`GeoCSVMetadata.datetime_resolution_ns[column][source_record_index]`, derived
from the source spelling before pandas conversion. Nine fractional digits
have a 1 ns resolution; .120 has 1 ms resolution and .120000 has 1 microsecond
resolution despite equal timestamp values. Missing timestamps have no entry.
Whole seconds, minutes-only times, and dates have nominal source resolutions
of a second, minute, and day. Timestamp values and timezones remain intact.

Association no longer uses bins. It compares absolute differences of full UTC
nanosecond values. `time_tolerance=None` defaults **per candidate** to one unit
of source resolution, inclusively; an explicit finite nonnegative tolerance
is in seconds, and zero requires exact equality. Both input timestamps remain
unchanged. Multiple eligible candidates still raise, rather than choosing a
nearest event. This default accommodates a writer that truncates fractions;
it is not an assertion of clock accuracy or an estimated uncertainty interval.

As of this audit, the user's current MERMAID convention is that resolution
finer than 0.01 s has no physical significance. Preserve those digits anyway:
this is a general GeoCSV reader, and the convention is not a global limit or
a 0.01 s matching tolerance. The [FDSN miniSEED 3 specification](https://docs.fdsn.org/projects/miniseed3/en/latest/background.html)
defines nanosecond start-time resolution. Support for decoding that binary
format belongs to the waveform reader, not this GeoCSV parser.

Related metadata dependencies (position pairs, timing, orientation, response,
pressure/depth, clock corrections, and provenance) are listed in the
[architecture notes](OBSPY_ASSOCIATION.md#timestamp-precision-and-metadata-dependencies).

## Readiness boundary

The 2026-10-15 source clarification establishes the user's construction:
multiple traces may share one row, but one trace must not be associated with
multiple rows for the core metadata considered here. Repeated identical REQ
files were inspected and successfully mapped to the same rebuilt GeoCSV row.
Position is interpolated at the first sample time, regardless of request date
or sample length. `SampleCount` already supplies the proposed NPTS check.
See the [original-file evidence](../sandbox/obspy_association/OBSERVATIONS.md#original-july-13-waveforms-2026-10-15).

These clarifications do not finish this audit or resolve findings 4 and 5.
In particular, legacy EarthScope M responses may lose DET Q / REQ D evidence
and combine overlapping coverage. Contiguity and quality-based validation of
such transformed inputs remain open. A subsequent explicit `allow_merge=True`
fallback now adopts a first-segment location without resolving those provenance
questions; see the [merged-trace policy](OBSPY_MERGED_TRACES.md). Strict
count matching remains the default; both outcomes carry an association label.

Preserve the sound parts: waveform metadata is authoritative; quality remains
independent; sample count and rate checks are explicit; zero/multiple matches
fail; batch validation precedes mutation; source values and provenance remain
attached. The initial-association guarantee ends before subsequent ObsPy
manipulation. The agreed provisional 0.01 Hz sampling-rate tolerance is a
separate quantity from timestamp precision and remains unchanged.

Package ownership/exposure, public schema/exception contracts, and optional
SAC projection remain later work. These fixes do not expose
`geocsv.associate`. Optional SAC projection remains NotImplementedError.

## Verification after strict-rule simplification

- Full local suite: **219 passed**, including complete-history integration.
- Fresh files without ignored histories: **185 passed, 34 skipped**. The
  tracked synthetic association tests execute; only full-history cases skip.
- Focused synthetic/full-history association suite: **80 passed**.
- Source timestamp values, timezone equivalence, per-record resolution and
  trailing zeros, mixed dataset record indices, immutable resolution metadata,
  coordinate-pair failure, strict destination conflicts, batch atomicity, and the writer
  rounding boundary are covered. Repository diff whitespace checks pass.
- Synthetic matching also covers ignored incomplete same-SNCL rows, their
  failure diagnostics, and the sorted SNCL/time lookup.

No processed source histories or Automaid files were modified. No commits or
pushes were performed for this remediation.

## Verification after findings 4 and 5

- Full suite: **236 passed**.
- Focused association suite: **97 passed**.
- The P0048 lookup microbenchmark used a complete local history and did not
  modify the fixture or its processed source.
- `git diff --check` passes.
