# P0006 GeoCSV fixture

`P0006.geocsv` is the canonical representative MERMAID GeoCSV fixture for
this repository. It is a real, single-dataset file produced by automaid v4.5.9
on 2026-08-12.

Use this fixture for end-to-end parser compatibility and provenance tests. It
is intentionally distinct from small, synthetic test fixtures, which belong
under `tests/fixtures/` and should isolate individual parser behaviors.

Do not modify, subset, normalize, or regenerate this file during tests. If a
replacement is required, document the source and reason for the change here.

The file contains 20,345 records, including 828 `Algorithm(event)` waveform
records alongside GPS, pressure, and thermocline observations. All 828 events
have latitude/longitude; all lack elevation, and 32 lack water pressure.
Complete SNCL/start time happens to be unique among these event records;
this is fixture evidence, not a general association uniqueness guarantee.
These counts were moved from the association design notes and rechecked with
`geocsv.read` during the documentation cleanup.

General-fixture consolidation remains [deferred maintenance](../../../scripts/fixtures/README.md#deferred-general-fixture-consolidation);
this cleanup does not replace or modify the source fixture.
