# GeoCSV hosting responsibilities and status

`mermaid-geocsv` owns public fetch/read/associate/write_sac APIs and their
scientific behavior. `mermaid-publisher` owns snapshot creation, full-archive
scientific validation, the report schema and publication gate, transfer, latest
activation and local archive recording. `bathymetrix-site` owns its read-only
R2 Worker, landing page, DNS/TLS and hosting runbook. Automaid generates source
GeoCSV and original waveforms. No publication scripts or report implementation
are part of this package.

The canonical [publication/download contract](../../mermaid-publisher/docs/geocsv/CONTRACT.md),
[publisher workflow](../../mermaid-publisher/docs/geocsv/WORKFLOW.md),
[scientific validation rules](../../mermaid-publisher/docs/geocsv/VALIDATION.md),
and [historical archive findings](../../mermaid-publisher/docs/geocsv/ARCHIVE_FINDINGS.md)
are maintained by the publisher. The [website runbook](../../bathymetrix-site/docs/GEOCSV_HOSTING.md)
records deployment and infrastructure status. Keep a single canonical contract;
package and host implementations must preserve supported consumer compatibility.
A publisher change does not implicitly authorize a corresponding fetch change.

## Current phase: testing only

All hosted data remain testing only, including complete-corpus tests. Publisher
0.1.0 requires `testing_only: true`, explicit testing destinations and complete
schema-3 scientific evidence. The local website Worker isolates
`/geocsv/testing/` and `geocsv/testing/` keys from future production activation.
The read-only Worker was deployed on 2026-10-23. The explicitly authorized
P0006/P0045 testing snapshot `2026-10-21T22:48:33.277Z` was published on
2026-10-26; testing latest selects it and production latest remains absent.
The landing page identifies the scope, cites the MH network (10.7914/SN/MH),
and describes retirement of initial workflow-testing artifacts. Further uploads,
production promotion and first formal releases remain separately unauthorized.

Live exact-byte HTTPS, cache hits and controls, conditional-write rejection,
latest/pinned fetch, one/all instruments, memory/disk, local reuse and download
provenance checks passed. A complete read/associate/write_sac rerun using hosted
downloads passed all 3,292 original waveform pairs. See the publisher's
[publication findings](../../mermaid-publisher/docs/geocsv/SCHEMA3_FINDINGS.md#initial-hosted-testing-publication--2026-10-26).

The external archive is `$MERMAID/publisher`, a separate local Git repository.
Testing GeoCSV artifacts use
`geocsv/testing/{snapshots,staging,validation,publications}`, selected from the
manifest’s `testing_only: true` flag. Initial workflow-testing artifacts may be
retired through separately authorized cleanup after verification; they are not
permanent scientific releases. Retain immutable bytes until retirement and never
reuse retired testing identities for different bytes. Production retention
remains indefinite. Original waveform archives are not copied. Git-tracked source
inputs require a clean tree and full commit hash in immutable local snapshot
provenance; ordinary source directories remain valid.
Successful publication includes a scoped local archive commit, never an automatic
push. Source-provenance and receipt changes do not alter the fetch manifest.

The pre-migration schema-2 run passed 43,365 original waveform pairs, staging 103
GeoCSV files and recording nine recordless exclusions. Those findings remain
historical; new code/candidates require fresh validation. Scientific comparisons
retain the existing documented rules, including exact native float32 interval
preservation and a one-ULP allowance against independent SAC intervals. No
comparison tolerance is changed by migration.

Instrument selection is frozen at creation with `--instruments P0006 P0045`.
Validation and publication use that same scope; publishing cannot filter a
snapshot. Full-corpus validation may use a separate ordinary temporary workspace
without Git, archival or publication intent. Fresh schema-3 runs passed all
43,365 full-corpus waveform pairs and all 3,292 pairs for the separate archived
P0006/P0045 candidate, including current acceptance gates after the local layout
change. See the publisher’s [fresh findings](../../mermaid-publisher/docs/geocsv/SCHEMA3_FINDINGS.md).
These reports are distinct from the historical schema-2 acceptance.

## Release path contract

The complete agreement is maintained in the publisher contract linked above.
The existing fetch contract is unchanged: preserve the literal UTC `#created`
timestamp as `release_id`; URL and downloaded directory components percent-encode
colons, while server object keys contain literal colons. For example:

| Context | Example |
| --- | --- |
| Literal identity | `2026-10-21T22:48:33.277Z` |
| URL/local component | `2026-10-21T22%3A48%3A33.277Z` |

Fetch accepts an explicit `base_url`, resolves latest once or bypasses it for an
explicit release, validates manifest identity/testing flags, and checks sizes and
SHA-256 of exact uncompressed bytes. Relative paths remain `latest.json` and
`releases/{encoded ID}/manifest.json` with payloads alongside the manifest.
The independent publisher pins consumer baseline 0.24.0 at package commit
`33ed5ff477b6c44447d472fc8e828b5ae930e0db`. The
[2026-10-26 baseline review](../../mermaid-publisher/docs/geocsv/CONSUMER_BASELINE_REVIEW.md)
covers the identical `read.py` to `_read.py` rename and three import updates.
Historical download fixtures and the original `c1eb805` fingerprints remain
retained. Published reports preserve their original software evidence; another
publication requires fresh validation matching the active installed consumer.
Changes to manifests, identities, paths or checksum semantics require explicit
compatibility review, separate from publisher/report version changes.

## Cross-repository workflow

```mermaid
flowchart TB
    upstream["automaid: GeoCSV and original MiniSEED/SAC"] --> source["$MERMAID/processed — read only"]
    source --> create["mermaid-publisher/scripts/geocsv/create_snapshot.py"]
    inspect["inspect_snapshot.py: internal integrity checks"] -.-> create
    create --> candidate["$MERMAID/publisher/geocsv/testing/snapshots/{ID}"]
    candidate --> validate["validate_snapshot.py: complete scientific comparisons"]
    source --> validate
    api["mermaid-geocsv: read → associate → write_sac"] -.-> validate
    validate --> report["testing/validation/{ID}: schema-3 evidence"]
    report --> gate["gate_snapshot.py: current evidence"]
    candidate --> gate
    gate --> publish["publish_snapshot.py: conditional transfer"]
    publish --> remote["Isolated testing objects: payloads, manifest, report"]
    remote --> checks["Exact HTTPS bytes and pinned fetch"]
    checks --> latest["Confirm latest activation last"]
    latest --> record["testing/publications/: receipt and local Git commit"]
    remote -.-> website["bathymetrix-site: read-only Worker and landing page"]
    website --> fetch["mermaid-geocsv.fetch"]
```

## Implementation and remaining checks

- [x] Separate publisher tools/tests/contracts from package APIs and website hosting.
- [x] Rename internal modules to inspect_snapshot and gate_snapshot.
- [x] Implement local testing-only creation, transfer isolation and serving support.
- [x] Implement clean-source Git provenance, dedicated Git archives and publication receipts.
- [x] Preserve download semantics and freeze an independently installed consumer baseline.
- [x] Freeze instrument selection and isolate local testing artifacts.
- [x] Run fresh full-corpus and separate P0006/P0045 schema-3 validation and acceptance.
- [x] Limit approved hosted testing to P0006/P0045 and prepare the MH network citation.
- [x] Publish the testing scope, citation and retirement notice before data uploads (2026-10-26).
- [x] Deploy approved R2/Worker configuration and verify read-only SDK/HTTPS access.
- [x] Publish the accepted two-instrument testing snapshot and record its local receipt.
- [x] Verify live conditional-write rejection, successful-object labels, cache hits and exact bytes.
- [x] Verify pinned/latest, one/all instruments, disk/memory, local reuse and all 3,292 scientific pairs.
- [ ] Restore DNSSEC after hosting verification.

As recorded on 2026-10-22, Cloudflare authority, proxy/TLS, email and scoped
Python-client edge access passed. DNSSEC remains disabled. Current hosting status
and recovery procedures belong in the website runbook. The sampled full-history
fixture checker remains package development tooling, not the publication gate.
