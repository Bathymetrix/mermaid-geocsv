# Data fixture roles

- [Published tutorial replay inputs](schema-1.0.0/hosted/README.md): unchanged
  prefixes of the public schema 1.0.0 histories for offline fetch/EarthScope tests.
- [Schema 1.0.0](schema-1.0.0/README.md): active typed-reader, association,
  download and tutorial inputs, converted from historical source evidence.
  The manifest records source hashes, row mappings and conversion assumptions.
  These are not regenerated producer output or full histories.
- [Association](association/README.md): unchanged original MiniSEED/SAC pairs,
  frozen pre-migration GeoCSV subsets, original manifests and historical audits.
  Tests parse the separate schema subsets and use the original waveforms here.
- [P0006](P0006/README.md) and [P0045](P0045/README.md): complete historical
  pre-migration GeoCSV snapshots retained for provenance, not active parsing.
  [P0006 waveforms](P0006/waveforms/README.md) also retain original pairs and
  saved EarthScope responses for current offline tutorial replay.

Original manifests describe original bytes and remain unchanged. Current
association record indices refer to the schema file actually read; use the
schema manifest to recover historical source indices. Subsets cannot establish
uniqueness across omitted full-history rows. Tests never regenerate fixtures.

General [GeoCSV specification examples](../../docs/references/geocsv-v2.0.4-examples/README.md)
are reference documents outside the fixture tree. They are unsupported inputs.
