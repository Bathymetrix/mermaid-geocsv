# P0045 GeoCSV fixture

This complete pre-migration snapshot is retained as historical source evidence.
It is unsupported by the current reader. Active tests and tutorials parse the
separate [schema 1.0.0 fixture](../schema-1.0.0/P0045/P0045.geocsv);
its [manifest](../schema-1.0.0/manifest.json) records the mapping and original
hash. The original bytes and provenance below remain unchanged.

It was copied verbatim on
2026-10-21 from the read-only source
`$MERMAID/processed/452.020-P-0045/geo_DET_REQ.csv`; only the filename differs.
The original header identifies automaid v4.5.14 and creation time
`2026-10-21T22:48:33.277Z`. No header or data records were edited.

- Size: 18,031,322 bytes.
- SHA-256: `6a1e92c09aa3c6b7f55e194b487487b57f3e583de735817857fb0558996acdc9`.
- Records: 124,022, including 2,459 `Algorithm(event)` records.

All event records have latitude/longitude, all lack elevation, and seven lack
water pressure. Rows 101433 and 101434 (zero-based complete-file record indices)
match the two original request segments used by the
[2022-01-15 merged-window example](../../../tests/fixtures/association/P0045_20220115/README.md).
Current merged-window tests read the separate schema subset. Original full-file
rows 101433 and 101434 map to schema-subset rows 13 and 14. Subset matches do
not establish uniqueness across omitted records. The historical [P0006
snapshot](../P0006/README.md) supplies source context for the preserved
EarthScope responses; active examples use separate schema fixtures.

Do not regenerate or modify fixtures during tests. Future replacement requires
an explicit source/provenance update; see the
[maintenance notes](../../../scripts/fixtures/README.md#current-fixture-snapshots).
