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
Only the MERMAID rc2 schema is used by this workflow. A fresh testing snapshot
requires a complete rebuilt source and candidate-bound validation.

Keep matching `testing_only: true` flags and isolated testing paths/pointers.
Testing publication and scientific acceptance do not authorize production
activation. Further uploads, deployment and retirement require explicit
authorization. Never reuse an identity for different bytes or apply a report
to changed inputs. Original source products and mirrors remain read-only.

## Browser bundles

`MERMAID.geocsv.tar.gz` contains exactly the snapshot's manifested instrument
files. It is outside `manifest.files` and scientific reports; member integrity
uses the existing manifest hashes. Fetch selects and verifies individual entries.
The read-only Worker provides clickable directory trees and release pages,
with bundle links only when objects exist. Publication verifies exact public
bundle bytes and member hashes before activating testing latest. Further
uploads, deployments and retirement require explicit authorization.

## Scientific client workflow

Fetch selects a manifest-pinned snapshot and verifies sizes/SHA-256. Read
validates the payload and preserves provenance. Associate attaches one uniquely
matched source row, coordinates and an association-time report to each native
MiniSEED-derived trace. Optional `create_sac_header=True` creates fresh station
headers; ObsPy owns serialization. The publisher verifies scratch exports and
independently read paired SAC references. SAC never supplies association hints
or missing source values. See [association](obspy-association.md) and [SAC](sac.md).

Publication requires complete waveform coverage, bound producer clash reports,
and hosted mapping/diff evidence. See the publisher
[report contract](../../mermaid-publisher/docs/geocsv/publication-reports.md).

Automaid collects GPS and pressure measurements from all
cycles, including Init and IcCycle, while omitting their waveform and crossing
rows. Normal producer output is bounded by its configured deployment window
and retained GPS span; excluded rows remain in local `outside_filterDate_gps.geocsv`.
Publisher validation independently checks GPS bracketing and excludes Init/IcCycle
waveform files. The consumer continues to
parse supplied payloads faithfully and performs no IcCycle/Init inference or filtering.
Fresh source generation and acceptance are required before a new publication.
