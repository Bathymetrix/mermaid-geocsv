# Documentation

Start with the [project README](../README.md) for installation, a quick example,
and the complete [tutorial and notebook list](../README.md#api-and-tutorials).
Runnable walkthroughs live in top-level `tutorials/`; this directory contains
maintained references.

## Package references

- [Installation](INSTALLATION.md): Python/dependency support, certificate setup, notebooks, and clean-install checks.
- [Reader specification](READER_SPEC.md): inputs, dtypes, record order, metadata, timestamps, and format conventions.
- [Fetch](FETCH.md): selection, release protocol, storage, integrity, provenance, and failures.
- [Association](OBSPY_ASSOCIATION.md): matching, clipped/combined coverage, coordinates, reports, and lifetime limits.
- [SAC](SAC.md): geographic mappings, missing pressure, precision, writing, and independent comparisons.
- [ObsPy Stats](OBSPY_STATS_REFERENCE.md): source-based core defaults, optional namespaces, and processing history.
- [MERMAID product identity](MERMAID_DATA_QUALITY.md): DET/REQ, nominal configurations, and independent quality indicators.
- [Open questions](OPEN_QUESTIONS.md): unresolved format/scientific questions and deferred workflows/mappings.
- [Hosting](HOSTING.md): ownership, testing-only status, and links to canonical publisher/site contracts.

## Fixtures and sources

- [GeoCSV v2.0.4](references/GeoCSV_v2.0.4.pdf) and [preserved examples](../data/fixtures/GeoCSV_v2.0.4_examples/README.md).
- [P0006 metadata](../data/fixtures/P0006/README.md) and [EarthScope responses](../data/fixtures/P0006/waveforms/README.md).
- [P0045 metadata](../data/fixtures/P0045/README.md) and [combined-window waveforms](../tests/fixtures/association/P0045_20220115/README.md).
- [Association inventory](../data/fixtures/association/README.md): paired waveforms, subsets, record maps, and measurement evidence.
- [Fixture maintenance](../scripts/fixtures/README.md): optional full-history restoration and checks.
