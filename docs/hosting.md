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
For a human-readable link that follows new publications, use
`https://bathymetrix.com/geocsv/testing/latest/`. It temporarily redirects to
the release directory selected by the testing latest pointer without caching.
Testing latest selects P0006/P0045 snapshot `2026-11-03T22:29:17.981000Z`,
using the previous header readable by consumer 0.28.0. Production latest is
absent. Consumer >= 0.29.0 requires the new dataset-first header; no rc1
snapshot is published.
The [publication record](../../mermaid-publisher/docs/geocsv/testing-publication-20261103.md)
binds its manifest, report, receipt and source revision. Older retained
snapshots can use unsupported schemas; downloading bytes does not establish
reader compatibility.

Keep matching `testing_only: true` flags and isolated testing paths/pointers.
Testing publication and scientific acceptance do not authorize production
activation. Further uploads, deployment and retirement require explicit
authorization. Never reuse an identity for different bytes or apply a report
to changed inputs. Original source products and mirrors remain read-only.

## Browser bundles

Publisher 0.5.0 adds `MERMAID.geocsv.tar.gz`, containing exactly the snapshot's
manifested instrument files. It is outside `manifest.files` and scientific
reports; member integrity uses the existing manifest hashes. Fetch continues
to select and verify individual manifest entries. The site implements plain
clickable directory trees and `releases/<component>/` pages, with bundle links
only when objects exist. This Worker support was deployed on 2026-11-03.
Live release-directory GET/HEAD and pinned downloads passed. The separately
authorized v4.9.2 snapshot publication then verified bundle/report bytes and
selected the new testing latest. The Worker deployment itself did not upload
data or change testing latest. Further deployments
and bundle uploads remain separately authorized operations.

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

Publisher 0.6.0 adds mandatory Recording coverage, bound producer clash reports,
and hosted mapping/diff evidence. See the publisher
[report contract](../../mermaid-publisher/docs/geocsv/publication-reports.md).
This source update does not establish deployment or new corpus acceptance.

Automaid v4.9.2 collects Position and Pressure-Absolute measurements from all
cycles, including Init and IcCycle, while omitting their Recording and crossing
rows. Normal producer output is bounded by its configured deployment window
and retained GPS span; excluded rows remain in local `outside_filterDate_gps.geocsv`.
Publisher validation independently checks GPS bracketing and excludes Init/IcCycle
waveform files. The consumer continues to
parse supplied payloads faithfully and performs no IcCycle/Init inference or filtering.
Fresh source generation and acceptance are required before a new publication.

The publisher's metadata-change gate exempts automaid MethodIdentifier revision
updates alone when the rest of each row is identical. Exact published diffs
retain those provenance changes; other edits and deletions require review.

## PPHC header and testing schema

The writer emits dataset-first GeoCSV 2.0 with `schema: MERMAID GeoCSV
v1.0.0-rc1`, padded comment keywords, unquoted comma/LF declarations and
producer/publisher/hoster/consumer project descriptions. `references` is reserved
for the describing paper and omitted until its DOI exists. Final schema 1.0.0
is reserved for paper publication. Testing accepts the 1.0.0 version family,
retains the exact revision and applies all scientific requirements.

This header requires consumer >= 0.29.0 and publisher >= 0.8.0. Existing hosted
snapshots retain their original old header; fetch can retrieve their exact bytes,
but the dataset-first reader rejects them. No upload, activation or retirement
is implied by local candidate validation. Canonical sources remain read-only.
