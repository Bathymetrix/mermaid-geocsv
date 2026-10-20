# Documentation

Start with the [project README](../README.md) for installation and a quick
example, or the [installation guide](INSTALLATION.md) for environment and
notebook setup.

## Tutorials

Each pair contains the same prose and Python examples and runs independently.

| Workflow | Guide | Notebook |
| --- | --- | --- |
| Read GeoCSV and use pandas | [Read](tutorials/READ.md) | [READ.ipynb](tutorials/READ.ipynb) |
| Fetch releases | [Fetch](tutorials/FETCH.md) | [FETCH.ipynb](tutorials/FETCH.ipynb) |
| Associate waveforms | [Associate](tutorials/ASSOCIATE.md) | [ASSOCIATE.ipynb](tutorials/ASSOCIATE.ipynb) |
| Write SAC files | [Write SAC](tutorials/WRITE_SAC.md) | [WRITE_SAC.ipynb](tutorials/WRITE_SAC.ipynb) |
| Plot and analyze records | [Plotting](tutorials/PLOTTING.md) | [PLOTTING.ipynb](tutorials/PLOTTING.ipynb) |

## API and scientific conventions

- [Reader specification](READER_SPEC.md): input types, DataFrame dtypes and
  indices, immutable metadata, timestamp precision, and missing-value rules,
  including known empty SEED location codes.
- [Fetch guide](tutorials/FETCH.md): release discovery, checksums, storage,
  memory use, provenance, failure behavior, and the test collection layout.
  The production collection URL is undecided; callers supply `base_url`.
- [Association guide](tutorials/ASSOCIATE.md): matching tolerances, source-row
  attachments, coordinate projections, validation, and processing limitations.
- [Merged-trace policy](OBSPY_MERGED_TRACES.md): explicit first-segment location
  fallback, sample-grid coverage, overlaps, and limits on reconstruction claims.
- [SAC writing guide](tutorials/WRITE_SAC.md): supported segments, geographic
  header mappings, pressure/depth conventions, missing pressure, float32
  precision, and independent automaid comparisons.

## Scientific context and design references

- [MERMAID data quality](MERMAID_DATA_QUALITY.md) and
  [dated retrieval observations](OBSPY_RETRIEVAL_OBSERVATIONS.md).
- ObsPy [Stats survey](OBSPY_STATS.md), [Stats source reference](OBSPY_STATS_REFERENCE.md),
  and [Stream and merge behavior](STREAM.md).
- [Association architecture and history](OBSPY_ASSOCIATION.md),
  [comparison with ObsPy association patterns](OBSPY_ASSOCIATION_COMPARISON.md),
  and [association audit](OBSPY_ASSOCIATION_AUDIT.md).
- [Open questions](OPEN_QUESTIONS.md) and [future workflows](FUTURE.md).

## Fixtures and maintenance

- [P0006 reader fixture](../data/fixtures/P0006/README.md).
- [Association fixture inventory](../data/fixtures/association/README.md):
  paired MiniSEED/SAC files and tracked GeoCSV subsets. Ordinary tests use
  tracked files; complete histories are optional local references.
- [Fixture maintenance](../scripts/fixtures/README.md): complete-history
  restoration, corpus checks, and collection provenance.
- [TODO](../TODO.md): fixture maintenance tasks.
