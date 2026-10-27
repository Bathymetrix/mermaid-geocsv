# Documentation

Start with the [project README](../README.md) for installation and a quick
example, or the [installation guide](INSTALLATION.md) for environment and
notebook setup.

## Tutorials

Each short walkthrough contains the same prose and Python examples as its
notebook and runs independently. Read, associate, SAC, and plotting use included
fixtures; fetch uses the public Bathymetrix testing collection. EarthScope
downloads three P0006 detections and combines hosted metadata, waveform
retrieval, association, and independent SAC comparisons.

| Workflow | Guide | Notebook |
| --- | --- | --- |
| Read GeoCSV and use pandas | [Read](tutorials/READ.md) | [READ.ipynb](tutorials/READ.ipynb) |
| Fetch releases | [Fetch](tutorials/FETCH.md) | [FETCH.ipynb](tutorials/FETCH.ipynb) |
| Associate waveforms | [Associate](tutorials/ASSOCIATE.md) | [ASSOCIATE.ipynb](tutorials/ASSOCIATE.ipynb) |
| Create SAC station headers and write with ObsPy | [Write SAC](tutorials/WRITE_SAC.md) | [WRITE_SAC.ipynb](tutorials/WRITE_SAC.ipynb) |
| Download EarthScope waveforms and verify SAC export | [EarthScope](tutorials/EARTHSCOPE.md) | [EARTHSCOPE.ipynb](tutorials/EARTHSCOPE.ipynb) |
| Plot and analyze records | [Plotting](tutorials/PLOTTING.md) | [PLOTTING.ipynb](tutorials/PLOTTING.ipynb) |

## API and scientific conventions

- [Reader specification](READER_SPEC.md): input types, DataFrame dtypes and
  indices, immutable metadata, timestamp precision, and missing-value rules,
  including known empty SEED location codes.
- [Fetch reference](development/FETCH.md#the-fetch-interface): release discovery, checksums, storage,
  memory use, provenance, failure behavior, and the test collection layout.
  Production hosting is not deployed; callers supply `base_url`.
- [Hosting workflow and build checklist](HOSTING.md): testing publication at
  `bathymetrix.com/geocsv/`, the cross-repository Mermaid diagram,
  timestamp-based snapshots, publisher-owned creation, full-archive validation,
  evidence and transfer using this package's public APIs, and separate website hosting.
- [Association reference](OBSPY_ASSOCIATION.md): matching tolerances, source-row
  attachments, coordinate projections, validation, and processing limitations.
- [Merged-trace policy](OBSPY_MERGED_TRACES.md): explicit first-segment location
  fallback for clipped/combined windows, sample-grid coverage, overlaps, and
  limits on reconstruction claims.
- [SAC header and ObsPy writing reference](development/WRITE_SAC.md): supported segments, geographic
  header mappings, pressure/depth conventions, missing pressure, float32
  precision, and independent automaid comparisons.

## Scientific context and design references

- [MERMAID data quality](MERMAID_DATA_QUALITY.md) and
  [dated retrieval observations](OBSPY_RETRIEVAL_OBSERVATIONS.md).
- ObsPy [Stats survey](OBSPY_STATS.md), [Stats source reference](OBSPY_STATS_REFERENCE.md),
  and [Stream and merge behavior](STREAM.md).
- [Association design and scientific conventions](OBSPY_ASSOCIATION.md).
- [Historical audits](../audits/README.md): dated findings and remediation evidence.
- [Open questions](OPEN_QUESTIONS.md) and [future workflows](FUTURE.md).

## Fixtures and maintenance

- [Development examples and checks](development/README.md): extended pandas
  and plotting examples, a local HTTP collection, detailed association
  diagnostics, and independent SAC comparisons moved out of the tutorials.
- [P0006 reader fixture](../data/fixtures/P0006/README.md).
- [Association fixture inventory](../data/fixtures/association/README.md):
  paired MiniSEED/SAC files and tracked GeoCSV subsets. Ordinary tests use
  tracked files; complete histories are optional local references.
- [Fixture maintenance](../scripts/fixtures/README.md): complete-history
  restoration, corpus checks, and collection provenance.
- [Current fixture snapshots](../scripts/fixtures/README.md#current-fixture-snapshots).
