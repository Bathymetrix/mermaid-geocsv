# GeoCSV download fixture

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
is documented in [`docs/FETCH.md`](../../../docs/FETCH.md).
`tests/test_fetch.py` constructs the release manifest and latest pointer in a
temporary server directory from this fixture, preserving its bytes and hash.
A second, invented instrument entry combines `typed.geocsv` and
`multiline.geocsv` for batch and multiple-dataset tests; it is not a real float.
