# Adversarial association audit and API readiness

Audit performed 2026-10-14 against the sandbox `associate.py`. This records
findings before remediation and their dispositions; the function remains an
experimental sandbox interface, not an exposed package API.

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

4. **P2: unrelated incomplete events can prevent a unique match.** A valid
   matching event plus a same-SNCL event with missing StartTime caused a fatal
   error on the incomplete row. Count/rate missingness instead eliminated
   candidates, so invalid-row policy was inconsistent. Decide validation scope
   and diagnostic behavior before API exposure. Deferred by the user.

5. **P2 performance concern: batch matching repeats event scans.** The same
   SNCL's rows are inspected for every trace. A synthetic benchmark excluding
   parsing took 0.158 s at 100 traces/rows and 2.008 s at 400. One sampled
   float history contains 1,830 events. A simple lookup built once is a possible
   improvement; realistic whole-float measurements should drive the change.
   Deferred by the user.

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

Preserve the sound parts: waveform metadata is authoritative; quality remains
independent; sample count and rate checks are explicit; zero/multiple matches
fail; batch validation precedes mutation; source values and provenance remain
attached. The initial-association guarantee ends before subsequent ObsPy
manipulation. The agreed provisional 0.01 Hz sampling-rate tolerance is a
separate quantity from timestamp precision and remains unchanged.

Findings 4 and 5, package ownership/exposure, public schema/exception contracts,
and optional SAC projection remain later work. These fixes do not expose
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

No processed source histories or Automaid files were modified. No commits or
pushes were performed for this remediation.
