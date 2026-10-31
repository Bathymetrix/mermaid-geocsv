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

## Schema and producer

- [MERMAID GeoCSV schema 1.0.0](format-spec.md): exact fields/header, row requirements and worked example.
- [Producer source rules](../../automaid/docs/geocsv.md) and [clock matrix](../../automaid/docs/clock-timing-matrix.md).

## Fixtures and sources

- [Fixture roles and provenance](../data/fixtures/README.md).
- [Fixture maintenance](../scripts/fixtures/README.md).
- [GeoCSV v2.0.4](references/GeoCSV_v2.0.4.pdf) and [preserved specification examples](references/geocsv-v2.0.4-examples/README.md).
- [Artifact-bound publication and validation records](../../mermaid-publisher/docs/geocsv/evidence.md).

[Source verification records](audit/README.md) retain commit-specific audits;
they do not replace current reference requirements.
