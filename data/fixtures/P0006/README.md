# P0006 GeoCSV fixture

`P0006.geocsv` is the canonical representative MERMAID GeoCSV fixture for
this repository. It is a real, single-dataset file produced by automaid v4.5.9
on 2026-08-12.

Use this fixture for end-to-end parser compatibility and provenance tests. It
is intentionally distinct from small, synthetic test fixtures, which belong
under `tests/fixtures/` and should isolate individual parser behaviors.

Do not modify, subset, normalize, or regenerate this file during tests. If a
replacement is required, document the source and reason for the change here.
