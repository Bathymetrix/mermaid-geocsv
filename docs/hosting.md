# Hosting and workflow ownership

| Component | Responsibility |
| --- | --- |
| Automaid | Original waveforms and GeoCSV source generation |
| mermaid-geocsv | Payload schema, fetch, read, association and optional SAC headers |
| mermaid-publisher | Verbatim snapshots, exhaustive validation, acceptance gate, transfer, latest activation and archive recording |
| bathymetrix-site | Read-only Worker, browser listings, landing page and hosting infrastructure |

The [publication/download contract](../../mermaid-publisher/docs/geocsv/contract.md)
defines manifests, paths and immutable bytes. The publisher's
[workflow](../../mermaid-publisher/docs/geocsv/workflow.md),
[validation reference](../../mermaid-publisher/docs/geocsv/validation.md) and
[SAC verification](../../mermaid-publisher/docs/geocsv/sac-verification.md)
define maintainer operations. The website's
[runbook](../../bathymetrix-site/docs/geocsv-hosting.md) owns deployment status.
The [fetch reference](fetch.md) defines client behavior; browser listings are
not a discovery API for fetch.

## Testing service

The public testing collection is `https://bathymetrix.com/geocsv/testing/`.
Testing latest selects P0006/P0045 snapshot `2026-10-30T18:08:32.316000Z`,
using schema 1.0.0 and consumer >= 0.27.0. Production latest is absent.
The [publication record](../../mermaid-publisher/docs/geocsv/schema1-testing-publication.md)
binds its manifest, report, receipt and source revision. Older retained
snapshots can use unsupported schemas; downloading bytes does not establish
reader compatibility.

Keep matching `testing_only: true` flags and isolated testing paths/pointers.
Testing publication and scientific acceptance do not authorize production
activation. Further uploads, deployment and retirement require explicit
authorization. Never reuse an identity for different bytes or apply a report
to changed inputs. Original source products and mirrors remain read-only.

## Scientific client workflow

Fetch selects a manifest-pinned snapshot and verifies sizes/SHA-256. Read
validates the payload and preserves provenance. Associate attaches one uniquely
matched source row, coordinates and an association-time report to each native
MiniSEED-derived trace. Optional `create_sac_header=True` creates fresh station
headers; ObsPy owns serialization. The publisher verifies scratch exports and
independently read paired SAC references. SAC never supplies association hints
or missing source values. See [association](obspy-association.md) and [SAC](sac.md).

The [fixture checker](../scripts/fixtures/README.md) verifies sampled package
inputs; it is not the exhaustive publication gate. Artifact-bound results are
listed in the publisher's [evidence index](../../mermaid-publisher/docs/geocsv/evidence.md).
