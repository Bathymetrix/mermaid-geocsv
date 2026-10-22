# P0045 GeoCSV fixture

This is the single shared, complete P0045 GeoCSV snapshot used by fetch,
association, and SAC-export tests and examples. It was copied verbatim on
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
Full-history association checks include other candidate rows; no source field
is changed to make a trace match.

The [P0006 snapshot](../P0006/README.md) supplies parser, plotting, and the
preserved EarthScope-response examples. Download tests and the fetch tutorial
serve both shared snapshots over loopback HTTP with dynamically built
manifests. No additional GeoCSV copy is kept for a separate tutorial.

Do not regenerate or modify fixtures during tests. Future replacement requires
an explicit source/provenance update; see the
[maintenance notes](../../../scripts/fixtures/README.md#current-fixture-snapshots).
