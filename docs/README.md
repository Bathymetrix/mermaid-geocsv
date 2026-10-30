# Documentation

Start with the [project README](../README.md) for installation, a quick example,
and the complete [tutorial and notebook list](../README.md#api-and-tutorials).
Runnable walkthroughs live in top-level `tutorials/`; this directory contains
maintained references.

## Package references

- [Installation](installation.md): Python/dependency support, certificate setup, notebooks, and clean-install checks.
- [Reader specification](reader-spec.md): inputs, dtypes, record order, metadata, timestamps, and format conventions.
- [Fetch](fetch.md): selection, release protocol, storage, integrity, provenance, and failures.
- [Association](obspy-association.md): matching, clipped/combined coverage, coordinates, reports, and lifetime limits.
- [SAC](sac.md): geographic mappings, missing pressure, precision, writing, and independent comparisons.
- [ObsPy Stats](obspy-stats-reference.md): source-based core defaults, optional namespaces, and processing history.
- [MERMAID product identity](mermaid-data-quality.md): DET/REQ, nominal configurations, and independent quality indicators.
- [Open questions](open-questions.md): unresolved format/scientific questions and deferred workflows/mappings.
- [Hosting](hosting.md): ownership, testing-only status, and links to canonical publisher/site contracts.

## Format design notes

- [MERMAID GeoCSV schema 1.0.0](format-spec.md): locally implemented contract, exact fields/header, complete synthetic example and acceptance cases.
- [GeoCSV migration decisions](geocsv-method-identifiers.md): agreed names, timestamps, missing values and scientific constraints; maintained with automaid.
- [Four-repository migration plan](../../automaid/docs/geocsv-migration-plan.md): coordinated implementation, verification, instruction precedence and automaid code boundaries.

## Fixtures and sources

- [GeoCSV v2.0.4](references/GeoCSV_v2.0.4.pdf) and [preserved examples](references/geocsv-v2.0.4-examples/README.md).
- [Schema 1.0.0 fixtures](../data/fixtures/schema-1.0.0/README.md): active parser, association and tutorial inputs with source mappings.
- Historical [P0006 metadata](../data/fixtures/P0006/README.md) and [EarthScope responses](../data/fixtures/P0006/waveforms/README.md).
- Historical [P0045 metadata](../data/fixtures/P0045/README.md) and [combined-window waveforms](../tests/fixtures/association/P0045_20220115/README.md).
- [Association inventory](../data/fixtures/association/README.md): paired waveforms, subsets, record maps, and measurement evidence.
- [Fixture maintenance](../scripts/fixtures/README.md): optional full-history restoration and checks.

## Audit records

- [Post-migration review, 2026-10-30](audit/2026-10-30.md): reference relocation, fixture roles, tutorial verification and cross-repository synchronization.

- [Development readiness audit, 2026-10-28](audit/2026-10-28.md): I/O and ObsPy findings, test evidence, and open release/hosting verification.
