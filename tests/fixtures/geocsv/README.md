# GeoCSV download fixtures

`P0006.geocsv` is the first fixture for developing GeoCSV download tests.
It contains scientific metadata but is not a published scientific data release.

- Size: 3,001,102 bytes.
- SHA-256: `07dfbbe639bacde403bb2b9d15eaf5d3ea8840ad17f11e3dde36d52ccbd17fa3`.
- Byte-identical website fixture: `bathymetrix-site/data/geocsv/testing/releases/test-001/P0006.geocsv`.

Source provenance: `$MERMAID/processed/452.020-P-06/geo_DET_REQ.csv`, renamed to
`P0006.geocsv` with three comment lines removed. The attribution comment records
this edit; data records are retained.

Serve this local fixture with a local HTTP server for routine automated download
tests; do not depend on the public endpoint or the website repository. The test
endpoint layout and provisional manifest are documented in the website's
`data/geocsv/testing/README.md` and `CONTRACT.md`. The package's fetch behavior
is documented in [`docs/tutorials/FETCH.md`](../../../docs/tutorials/FETCH.md).
`tests/test_fetch.py` constructs the release manifest and latest pointer in a
temporary server directory from this fixture, preserving its bytes and hash.
The temporary test release also includes real P0045 for instrument selection
and ordering. A separate invented `P_TEST` entry combines `typed.geocsv` and
`multiline.geocsv` for multiple-dataset parsing; it is not a real float.

## P0045

`P0045.geocsv` was supplied by the user on 2026-10-20. Its unchanged header
identifies automaid v4.5.11 and creation time 2026-10-13T20:48:01.378Z.
No earlier source path or byte identity is inferred from that header.

- Size: 18,031,573 bytes; 124,022 data records.
- SHA-256: `ce8df12383ae128798d84d154a1926f96f488a2282a666c4fb2575e7a0f8fb3a`.

This single file supplies both fetch-selection examples and the real merged
waveform association example. Its source-record indices 101433 and 101434
match the selected 2022-01-15 segments. See the
[paired waveform fixture notes](../association/P0045_20220115/README.md).
Do not create another GeoCSV copy for the association tutorial.
