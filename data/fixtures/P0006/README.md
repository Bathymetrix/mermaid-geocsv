# P0006 GeoCSV fixture

This complete pre-migration snapshot is retained as historical source evidence.
It is unsupported by the current reader. Active tests and tutorials parse the
separate [schema 1.0.0 fixture](../schema-1.0.0/P0006/P0006.geocsv);
its [manifest](../schema-1.0.0/manifest.json) records the mapping and original
hash. The original bytes and provenance below remain unchanged.

It was copied
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
Measured sample rates are preserved as emitted by the historical writer.

The [P0045 snapshot](../P0045/README.md) supplies historical context for the
merged-window example. Current download tests and tutorials serve the separate
schema fixtures over loopback HTTP; they do not parse these historical bytes
or depend on public hosting. Fixtures are not a scientific data release.

The [waveform fixtures](waveforms/README.md) contain three original
MiniSEED/SAC pairs and their saved EarthScope responses for the complete
[EarthScope tutorial](../../../tutorials/05_earthscope.md). Their separate
manifest records request parameters, source paths, and hashes.

The separately tracked P0006 association subset is a verbatim selection from
this same processed export, with its record mapping and full-source hash in
[the association manifest](../association/manifest.json). It exists to keep
ordinary multi-instrument association tests small, not to preserve an older
version. Complete optional histories remain Git-ignored.

Do not regenerate or modify fixtures during tests. Future replacement requires
an explicit source/provenance update; see the
[maintenance notes](../../../scripts/fixtures/README.md#current-fixture-snapshots).
