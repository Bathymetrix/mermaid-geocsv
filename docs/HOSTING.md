# GeoCSV hosting workflow and build checklist

Design agreed 2026-10-22. This is an implementation plan, not an operational
hosting service. The public collection base is planned as
`https://bathymetrix.com/geocsv/`. The main website remains independently
maintained; large GeoCSV payloads live in object storage rather than Git.
Cloudflare R2 and a Worker route for `/geocsv/*` were selected on 2026-10-22.
Keep the existing website on GitHub Pages and domain registration at Squarespace.

The snapshot creator, full-archive validator, publisher and Worker paths below
are **planned**. They have not been implemented. `geocsv.fetch` supports the
timestamp release/path contract below as of package version 0.24.0. The website
must implement that contract, and full-archive validation remains to be built.
Nothing in this document authorizes
modification of protected processed inputs, publication, or a package release.

## Current website and DNS

The user reports a Squarespace domain registration costing $20/year, with no
website hosting subscription identified. The live website is served by GitHub
Pages; public A records match GitHub Pages and the HTTP response identifies
GitHub. The user reports a custom CNAME target of `bathymetrix.github.io` and an
inactive Squarespace preset. Public authoritative nameservers currently use
`ns-cloud-c1.googledomains.com` through `ns-cloud-c4.googledomains.com`, consistent
with the current Squarespace domain/DNS management. These observations were
checked on 2026-10-22; recheck before deployment.

The chosen same-host `/geocsv/*` Worker route requires a Cloudflare zone and a
proxied DNS record for the hostname; a DNS CNAME cannot route a URL subpath.
Plan Cloudflare authoritative DNS onboarding while retaining Squarespace as
registrar and GitHub Pages as the website origin. Inventory and preserve the
working website and email records, and account for DNSSEC during that migration.
Prepare the complete migration/deployment steps before any live changes.
Selecting R2 does not itself activate a DNS migration or publish the data.
See Cloudflare's [Worker routing requirements](https://developers.cloudflare.com/workers/best-practices/workers-best-practices/#set-up-custom-domains-or-routes-correctly)
and [primary DNS setup](https://developers.cloudflare.com/dns/zone-setups/full-setup/setup/).

## Release identity and unchanged historical data

The exact value of the GeoCSV `#created` comment is the release ID. It identifies
the upstream automaid run, not observation coverage or the later publication
time. Require exactly one valid UTC `#created` declaration per file and the
same declaration value across every GeoCSV in the snapshot. Missing, repeated,
or inconsistent values raise; do not silently infer or repair them. Preserve
fractional digits. Record validation/publication times separately.

A dead float may produce identical historical data records indefinitely.
Those records do not have to change between releases. Updated comments,
including a new shared `#created`, are valid under a new release ID, even when
all non-comment records are unchanged. The publisher copies the complete
upstream file verbatim and hashes all bytes, including comments. There is no
requirement for a changed data row, and no deduplication across releases.

Published files and manifests remain immutable under an existing release ID.
An identical retry reuses the existing release; different bytes or a different
inventory under that same ID raise, including comment-only changes. Corrections
therefore need a new upstream run timestamp. Do not regenerate or overwrite an
existing release manifest simply to change its publication metadata.

## Release path contract

Keep the literal timestamp as `release_id` in JSON, fetch arguments and returned
provenance. Production timestamps use `YYYY-MM-DDTHH:MM:SS[.digits]Z`, with a
valid calendar date, hours 00–23 and seconds 00–59. Preserve every fractional
digit; do not parse and reformat the identity. The client also retains support
for plain ASCII token IDs such as `test-001` for illustrative test collections.
It verifies the manifest protocol, sizes and hashes, without interpreting each
GeoCSV's `#created`; snapshot-wide timestamp validation belongs to the publisher.

Define `release_component = urllib.parse.quote(release_id, safe="")`. In the
accepted timestamp grammar this changes only `:` to uppercase `%3A`. A client
must receive the literal ID, not an already encoded value. This representation
is lossless: decoding once recovers the identical ID, including fractional
digits. Equivalent instants with different fractional spellings are different
IDs; the publisher must require exact source spelling agreement.

For `release_id = "2026-10-21T22:48:33.277Z"`:

| Context | Representation |
| --- | --- |
| JSON `release_id`, fetch `release`, returned provenance | `2026-10-21T22:48:33.277Z` |
| URL component and downloaded local directory name | `2026-10-21T22%3A48%3A33.277Z` |
| Object key or server-side release directory | `2026-10-21T22:48:33.277Z` |

URLs contain the encoded component; storage keys contain the literal ID. Decode
the URL path **exactly once** when resolving the object key. Do not store `%3A`
in object keys or encode `%` again as `%25`. Local download directories retain
the encoded spelling so they contain no Windows-invalid colons. The publisher's
external staging/report workspace uses that same encoded directory spelling.
The storage provider may change without changing this public contract.

The latest pointer must use the exact encoded relative manifest path:

```json
{
  "release_id": "2026-10-21T22:48:33.277Z",
  "testing_only": false,
  "manifest": "releases/2026-10-21T22%3A48%3A33.277Z/manifest.json"
}
```

The immutable manifest contains the same literal `release_id`, boolean
`testing_only`, and a `files` array. Each entry requires a unique nonempty
`instrument_id`, unique `filename`, nonnegative integer `size_bytes`, lowercase
64-hex-digit `sha256`, and a `provenance` object. For production, each filename is
`{instrument_id}.geocsv`. Filenames start with an ASCII letter or digit and use
only ASCII letters, digits, `.`, `_`, and `-`; `manifest.json` is reserved.
Checksums and sizes describe complete uncompressed GeoCSV bytes. Descriptive
fields are retained verbatim without becoming filesystem instructions. No new
`release_component` JSON field is needed; it is derived from `release_id`.

The client pins latest once or bypasses it for an explicit ID, requires exact
manifest identity and test-flag agreement, and never falls back to another
release. These rules apply to any chosen host. The existing website test-token
collection remains compatible; its documentation needs the production addition.

## Workflow diagram

Repository paths are relative to the `mermaid-geocsv/` root. A subgraph names
its repository root; paths inside it are relative to that root. `$MERMAID`
identifies the external read-only data tree. `{work}` is a chosen local
publication workspace outside all Git checkouts and the protected source tree;
it contains staged payloads, reports and temporary comparison outputs.

```mermaid
flowchart TB
    subgraph upstream["../automaid/ — existing upstream writers"]
        run["scripts/main.py<br/>one creation_datestr per archive run"]
        csv["scripts/geocsv.py<br/>write the shared #created comment"]
        events["scripts/events.py<br/>write original MiniSEED and SAC"]
        run --> csv
        run --> events
    end

    source["$MERMAID/processed/{instrument_serial}/<br/>geo_DET_REQ.csv"]
    waveforms["$MERMAID/processed/{instrument_serial}/{cycle}/<br/>original .mseed and paired .sac"]
    csv --> source
    events --> waveforms

    subgraph website["../bathymetrix-site/ — planned publication tools"]
        create["scripts/geocsv/create_snapshot.py<br/>copy verbatim and inventory all instruments"]
        consistent{"One common #created<br/>and valid, unique instrument IDs?"}
        publish["scripts/geocsv/publish_snapshot.py<br/>require passing report and recheck hashes"]
        accepted{"Report covers these exact bytes<br/>and release ID can be published?"}
        create --> consistent
        publish --> accepted
    end

    candidate["{work}/snapshots/{release_component}/<br/>{instrument_id}.geocsv + manifest.json"]
    report["{work}/validation/{release_component}/validation.json<br/>snapshot hashes, waveform inventory and results"]
    stop["Stop and report failures<br/>existing latest remains unchanged"]
    source -->|read-only| create
    consistent -->|yes| candidate
    consistent -->|no| stop

    subgraph package["./ — mermaid-geocsv; planned full-archive validator"]
        validate["scripts/validate_snapshot.py<br/>read → associate → write_sac<br/>compare every pair using approved precision rules"]
    end
    candidate --> validate
    waveforms -->|read-only| validate
    validate --> report
    report --> publish
    candidate --> publish
    accepted -->|no| stop

    stored["R2 object keys: geocsv/releases/{literal release_id}/<br/>GeoCSV files, then manifest.json and validation.json"]
    verify["Verify public HTTPS bytes and hashes<br/>run geocsv.fetch with the explicit release ID"]
    healthy{"Remote checks pass?"}
    activate["Replace geocsv/latest.json last"]
    accepted -->|yes or identical retry| stored
    stored --> verify
    verify --> healthy
    healthy -->|no| stop
    healthy -->|yes| activate

    subgraph public["bathymetrix.com — planned public Worker route"]
        worker["../bathymetrix-site/workers/geocsv/src/index.js<br/>planned: decode URL once to literal object key; stream payloads"]
        latest["/geocsv/latest/{instrument_id}.geocsv<br/>temporary redirect to the selected immutable release"]
        client["geocsv.fetch reads /geocsv/latest.json once<br/>then one immutable manifest and its selected files"]
        worker --> latest
        worker --> client
    end
    stored -. serve immutable objects .-> worker
    activate -. select the current release .-> worker
```

An identical retry verifies and reuses an existing immutable release; the
publisher must not overwrite its objects. A failed full-archive report blocks
publication. Upload failures or failed public checks block activation. The
previous latest release remains usable throughout these operations.

The Worker streams R2 payloads, serves `latest.json`, and redirects convenient
`/latest/` file URLs. The fetch client downloads through the immutable release
paths so a latest update cannot mix snapshots within one operation. HTTPS,
pointer cache bypass and immutable-object caching are hosting responsibilities.

## Ownership and scientific acceptance

| Owner | Script or responsibility | Status |
| --- | --- | --- |
| `../automaid/` | `scripts/main.py`, `scripts/geocsv.py`, `scripts/events.py`: create scientific outputs and their run timestamp | Existing |
| `../bathymetrix-site/` | `scripts/geocsv/create_snapshot.py`: stage unchanged GeoCSV bytes, resolve IDs, enforce one timestamp and generate the complete manifest | Planned |
| `./` | `scripts/validate_snapshot.py`: validate staged GeoCSV against every local original MiniSEED/SAC pair | Planned |
| `../bathymetrix-site/` | `scripts/geocsv/publish_snapshot.py`: enforce acceptance, upload, verify and activate | Planned |
| `../bathymetrix-site/` | `workers/geocsv/src/index.js`: public routing, streaming and latest redirects | Planned |

The validator runs against the frozen candidate, not a separate live GeoCSV
copy. It inventories every original MiniSEED and paired SAC for all included
instruments; missing pairs, unsupported products and unexamined files are
reported rather than silently skipped. Process one instrument at a time with
bounded waveform batches and temporary SAC exports. Read/copy the protected
source only; never rewrite it or borrow SAC headers for association.

Associate originals with the standard strict contract and its documented
tolerances, without the containing-anchor fallback. Multiple waveform files
may use the same source row. Compare every paired file using the approved
SNCL, sample-count, sample-value, timing, interval and STLA/STLO/STDP/STEL rules.
Preserve raw counts subject to SAC float32 storage. Geographic comparisons
must account for documented source decimal precision and SAC float32 rounding;
an unexpected mismatch is reported, not grounds for automatic tolerance
widening. This covers every pair, not every producer-specific SAC header.

The machine-readable report records the release ID, exact candidate manifest
SHA-256, all staged file hashes, the source waveform inventory/fingerprints,
package/code/dependency versions, checks and limits, counts, measured maxima,
and individual failures. Missing coverage or any failed check blocks acceptance.
The publisher rechecks the complete candidate inventory and hashes before
uploading. A pass from different input bytes cannot authorize publication.

`validation.json` may accompany the immutable release as evidence outside the
manifest's GeoCSV `files` list. It binds the already-frozen manifest; avoid a
circular hash dependency by keeping its own hash out of that manifest.
Use source-relative identifiers in public reports, retaining local diagnostics
in the publication workspace.

The existing [full-history fixture checker](../scripts/fixtures/check_full_histories.py)
checks 18 sampled waveform associations. It is not the proposed complete-corpus
validator and cannot satisfy the publication gate by itself.

Website staging and hosting implementation can start against the documented
0.24.0 fetch contract without another client API change. Work still owned here
before publication is the full-archive validator, its concrete report format,
and a complete archive run. The website publisher must consume that report
without a temporary acceptance bypass. Real HTTPS integration checks follow
once a host is available. Keeping `base_url` explicit is supported; choosing a
production default is optional and does not block the website.

## Implementation checklist

These boxes track implementation, not approval of the design. No production
hosting component below is implemented by this documentation change.

### 1. Coordinate the contract

- [x] **This repository:** specify and test literal timestamp identity, encoded
  URLs/local directories, and literal server/object keys, including fractional
  digits and rejection of invalid or already encoded IDs (0.24.0).
- [ ] **Website:** adopt the release path contract above in staging, manifests,
  URL routing and object-key lookup; verify exactly one URL decoding step.
- [ ] **Website:** update `data/geocsv/testing/CONTRACT.md` to distinguish the
  existing test protocol from the agreed production layout and ownership.
- [ ] **Both repositories:** fix manifest/report fields and meanings, including
  complete inventory, exact-byte SHA-256/size, relative provenance, timestamp
  identity, idempotent retries and immutable retention of old releases.
- [ ] **Website:** define instrument-ID extraction/validation and how unexpected
  missing previously published instruments are reported before acceptance.
- [ ] **Website:** settle the collection's data-license and citation text.

### 2. Stage a reproducible candidate

- [ ] **Website:** implement `scripts/geocsv/create_snapshot.py` with an explicit
  source root and external publication workspace; run after processing finishes.
- [ ] Enforce exactly one valid `#created` per file and exact snapshot-wide
  agreement; raise on missing/repeated/mixed timestamps or ambiguous IDs.
- [ ] Copy each `geo_DET_REQ.csv` verbatim as `{instrument_id}.geocsv`, freeze
  the sorted complete manifest, and record full-file hashes and byte counts.
- [ ] Verify a retired float with identical historical rows and updated comments
  under a new shared timestamp passes; no new data row is required.
- [ ] Verify differing bytes under an existing release ID raise, while an
  identical retry preserves the existing manifest and objects.

### 3. Establish full-archive scientific acceptance

- [ ] **This repository:** implement `scripts/validate_snapshot.py` using the
  public APIs, complete waveform inventories and independent paired SAC reads.
- [ ] Fix comparison fields, units, missing-value rules and precision limits
  using the documented scientific contract; avoid whole-SAC equivalence claims.
- [ ] Produce the candidate-bound validation report, complete accounting and
  useful failure diagnostics; leave sources unchanged and remove scratch SAC.
- [ ] Exercise the gate with real inputs and intentional missing-pair,
  association, sample and coordinate mismatches; failures must block publishing.
- [ ] Run the complete local archive and resolve every failure or unsupported
  input before accepting the first candidate. Record actual checked counts.

### 4. Prepare hosting and safe publication

- [ ] **Website:** prepare Cloudflare DNS onboarding with existing website/email
  records preserved, Squarespace registration retained, and the GitHub Pages
  origin working through the proxy; review migration steps before activation.
- [ ] **Website:** configure R2 and Cloudflare routing/TLS for
  `bathymetrix.com/geocsv/`, including the landing page at `/geocsv/`.
- [ ] Implement `workers/geocsv/src/index.js` for streamed immutable downloads,
  manifest/pointer delivery, correct missing-file responses and temporary latest
  redirects. Keep the main website's other routes working.
- [ ] Bypass caches for `latest.json` and latest redirects; cache successful
  immutable release responses deliberately and prevent stale publication 404s.
- [ ] Serve plain GeoCSV with appropriate content metadata; honor
  `Accept-Encoding: identity` and verify the exact delivered bytes.
- [ ] Implement `scripts/geocsv/publish_snapshot.py`: require a passing report,
  recheck candidate hashes, upload files before the manifest, verify remote
  content, and update the single latest pointer last. Serialize publications.
- [ ] Test interrupted uploads, a changed candidate after validation, conflicting
  release IDs and rollback to a retained release. Failures leave latest intact.

### 5. Complete client integration and launch checks

- [x] **This repository:** implement timestamp-ID/path handling in `fetch`, with
  focused tests, version 0.24.0 and synchronized fetch tutorials.
- [ ] Verify explicit release pinning and default latest selection against the
  real HTTPS endpoint, including one/all instruments and disk/memory downloads.
- [ ] Verify checksums, manifests and provenance survive `fetch → read`, and a
  public real-data example completes `associate → write_sac` as documented.
- [ ] Run both supported Python/dependency-bound CI jobs and their wheel checks
  after client changes; retain offline tests independent of hosting.
- [ ] Update package/website installation and download examples, decide whether
  to make the production base URL the fetch default, and link the release's
  manifest and acceptance report from the website.
- [ ] Mark components implemented only after verification, update this diagram
  and checklist, and record the actual first publication separately from any
  software v1 release. Neither publication is implicit authorization for the other.

## Keeping the plan current

Read the relevant instructions and current source in all three repositories
before implementation or revision. Changes to automaid timestamp generation,
output names, formatting or waveform processing can affect snapshot validation.
Changes to website staging, routes, manifests or publishing can affect fetch.
Update the diagram, paths, script names, status and checklist together as those
implementations evolve; coordinate contract changes across owners. Do not copy
scientific matching logic into the website or silently change numerical limits.

Read-only references inspected for this plan on 2026-10-22:

- `../automaid/` at `e841a1a0e2607582f10631c4f5989286d42d346b`:
  `scripts/main.py` creates one run timestamp and passes it to the GeoCSV writer;
  `scripts/geocsv.py` emits it as `#created`.
- `../bathymetrix-site/` at `f861d6182e3632e32bfc142294e24118b977830e`:
  the provisional contract is `data/geocsv/testing/CONTRACT.md`; the planned
  snapshot/publication scripts and Worker directory do not yet exist.

These references are dated evidence, not permission to change those checkouts.
