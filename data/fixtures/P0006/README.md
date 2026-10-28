# P0006 GeoCSV fixture

This is the single shared, complete P0006 GeoCSV snapshot used by parser,
fetch, plotting, and EarthScope-response tests and examples. It was copied
verbatim on 2026-10-21 from the read-only source
`$MERMAID/processed/452.020-P-06/geo_DET_REQ.csv`; only the filename differs.
The original header identifies automaid v4.5.14 and creation time
`2026-10-21T22:48:33.277Z`. No header or data records were edited.

- Size: 3,001,072 bytes.
- SHA-256: `93e8807306731191545845d58bb410480ed219b6e8129d381b22fcdcf9379080`.
- Records: 20,345, including 828 `Algorithm(event)` records.

All 828 event records have latitude/longitude; all lack elevation, and 32 lack
water pressure. Complete SNCL/start time is unique among these event records;
this is snapshot evidence, not a general association uniqueness guarantee.
Measured sample rates are preserved as emitted by the current GeoCSV writer.

The [P0045 snapshot](../P0045/README.md) supplies the second instrument for
fetch selection and merged-window examples. Download tests and the fetch
tutorial construct manifests dynamically and serve these exact repository
bytes over loopback HTTP. They do not depend on a website checkout, public
hosting, or equality with an older website test release. These fixtures are
scientific metadata examples, not a published scientific data release.

The [waveform fixtures](waveforms/README.md) contain three original
MiniSEED/SAC pairs and their saved EarthScope responses for the complete
[EarthScope tutorial](../../../tutorials/EARTHSCOPE.md). Their separate
manifest records request parameters, source paths, and hashes.

The separately tracked P0006 association subset is a verbatim selection from
this same processed export, with its record mapping and full-source hash in
[the association manifest](../association/manifest.json). It exists to keep
ordinary multi-instrument association tests small, not to preserve an older
version. Complete optional histories remain Git-ignored.

Do not regenerate or modify fixtures during tests. Future replacement requires
an explicit source/provenance update; see the
[maintenance notes](../../../scripts/fixtures/README.md#current-fixture-snapshots).
