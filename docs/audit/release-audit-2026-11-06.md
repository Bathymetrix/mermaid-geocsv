# Consumer release audit — 2026-11-06

No consumer implementation blocker was found in fetch, read or initial ObsPy
association for the latest published original-waveform corpus. The linked
[publisher audit](../../../mermaid-publisher/docs/geocsv/release-audit-2026-11-06.md)
identifies two high-priority workflow conditions and two moderate evidence
defects. Those findings affect confidence in the supplied metadata, even when
the consumer faithfully reads and attaches it.

Consumer **0.29.0**, publisher **0.8.0**, schema **1.0.0-rc1** and the
**testing-only** collection are the inspected baseline, not release blockers.
Scope ends at successful initial association and optional creation of the four
approved SAC station headers. Later operations on associated objects are
outside scope.

## Linked checklist, highest severity first

P1/P2 and statuses match the publisher checklist. P1 requires resolving a
workflow policy or validation gap before scientific release sign-off. P2 is a
bounded evidence defect; RA-05 is an accepted external-input limitation.
An acknowledgement below does not close the publisher's open implementation work.

| ID | Severity | Shared status | Consumer responsibility | Fix owner |
| --- | --- | --- | --- | --- |
| RA-01 | P1 | Open | Preserve changed source values; acknowledge comparison coverage | Publisher |
| RA-02 | P1 | Open | Preserve correction metadata and never apply it again | Publisher |
| RA-03 | P2 | Open | Retain many-originals-to-one-row association | Publisher |
| RA-04 | P2 | Open | Retain existing rate-matching semantics | Publisher |
| RA-05 | P2 | Accepted limitation | Reject the demonstrated unmatched/ambiguous response | External provenance; current consumer behavior is correct |

### RA-01: schema approval does not establish unchanged scientific rows

The publisher's schema-mismatch path returns a placeholder rather than a row
comparison. **Example:** changing current P0006 from schema `1.0.0-rc1` to
supported `1.0.0-rc2` and its first Position latitude from **−14.453383° to
−13.453383°**, approximately **111 km**, produces `schema_changed=True` but
`metadata_changed=False`. This policy gap is reproduced; it is not an observed
error in the published P0006 data. The real predecessor's **20,345 P0006 rows**
and **124,016 P0045 rows** were independently confirmed unchanged apart from
producer revision labels.

- [x] Acknowledge that supported schema spelling and manifest hashes do not
  establish scientific equivalence to a predecessor. The reader preserves
  each supplied latitude and exact schema revision; it must not substitute an
  older value.
- [ ] Acknowledge the publisher's revised comparison/approval policy here when
  RA-01 closes. No new consumer migration API or legacy-format support is required.

### RA-02: correction metadata can be wrong while association succeeds

The publisher does not currently verify serialized correction provenance.
**Example:** a synthetic **20 Hz, 4-sample** original with **0 correction ticks**
still passes all **12 publisher checks and acceptance** when GeoCSV claims
**+2 seconds** already applied, an error of **40 sample intervals**. Initial
association matches the unchanged start/count/rate and preserves the source claim.

The actual corpus's **240,242 MiniSEED records / 43,333 files** have the applied
bit set and corrections consistent with independent serialization precision.
For real N0001 index **1050**, line **1064**, **−0.466050 s** in GeoCSV and
**−4661 ticks = −0.4661 s** in MiniSEED differ by **50 µs**. Such a difference
does not establish incorrect timing: independently rounding a source value to
1 µs and 100 µs permits **50.5 µs** disagreement. Exact re-rounding of printed
cells would flag **1,158 records in 214 files** without establishing a defect.

- [x] Preserve `TimeCorrectionApplied` as signed source metadata and retain the
  native waveform start. Never apply it again or replace it with a header value.
- [ ] Acknowledge the publisher's eventual per-record provenance check and
  precision rule here and in affected references. Keep producer validation out
  of the public reader/associator.

### RA-03: “verified” producer evidence can be structurally incomplete

The publisher verifies clash binding/references but can omit required evidence
fields. **Example:** P0006 index **100**, line **114**, has **3 files / 2 raw
variants**, with reported header rates **20.007053 / 20.007053 / 20.007048 Hz**.
A temporary sidecar without `variant_count`, `header_differences` and
`payload_bytes_identical` in all **3 P0006 clash entries** is still labelled
`verified`. The archived sidecar is complete and unchanged.

- [x] Keep producer assertions distinct from consumer matching. Multiple
  originals may use one unique row: **43,333 original pairs / 43,316 Recording
  rows** is expected, not an instruction to consume rows exclusively or deduplicate
  waveforms. Repetition alone does not demonstrate distinct raw variants.
- [ ] Acknowledge structural validation and its limited meaning when the
  publisher closes RA-03. No consumer clash parser is needed.

### RA-04: gate diagnostics need the same rate semantics as matching

The publisher's independent gate omits the rate-error bound. **Example:** a
temporary report with **0.1 Hz** rate error and recomputed maxima passes the
gate, despite the **0.00001 Hz** matching allowance: a **10,000-fold** excess.
The actual accepted corpus maximum is **0.0000034332129956737845 Hz**;
the consumer's normal matching rule already rejects large differences.

- [x] Retain the existing floating-point endpoint rule, counts without tolerance,
  and the **1 ms** default start tolerance. Do not widen any of them to close a
  publisher reporting defect.
- [ ] Acknowledge the publisher's rejection test and consistent rate evidence
  when RA-04 closes.

### RA-05: one external response fails initial association correctly

The saved EarthScope `P0006_record_100.mseed` was rechecked against current
archived P0006 metadata; no live EarthScope request was made for this audit.
All entries below have SNCL `MH.P0006.00.BDH` on **2018-07-06**:

| Input | Start UTC | Samples | Difference from response |
| --- | --- | ---: | --- |
| Current REQ index 100, line 114 | 01:49:28.590640 | 4,800 | 22.381 ms earlier |
| Current DET index 101, line 115 | 01:49:28.613021 | 4,736 | 64 fewer samples |
| Saved external response | 01:49:28.613021 | 4,800 | — |

The response rate is **20.007062146892654 Hz**; both rows declare
**20.007062 Hz**. Strict association rejects the unmatched combination.
`allow_first_segment=True` rejects **2 containing anchors**. Current-source
numbers differ from the older GeoCSV's millisecond-quantized example retained
in [open questions](../open-questions.md); the source generation must stay explicit.

- [x] Record correct failure behavior and keep this an accepted limitation for
  the scoped release. The response's original segmentation/provenance remains
  unresolved; no automatic repair, nearest-row choice or broader reconstruction
  project is required.

Optional local response: `data/local/obspy_retrievals/P0006_record_100.mseed`,
SHA-256 `b4f04278c62edd72bd2129b7ce6c5cee191be6660ef731f939c03e7ac18af96a`.
This ignored evidence is not an ordinary test dependency. The archived native
waveforms passed their separate original-corpus checks.

## Baseline and completed verification

Live latest and its exact **28,636-byte manifest** were checked on 2026-11-06:
snapshot **2026-11-05T23:41:47.235000Z**, **103 instruments**, **4,104,855 rows**,
**43,316 Recording rows**, **43,333 passing original pairs**. Source accounting
is **112 instruments including 9 recordless exclusions**. The
[publication record](../../../mermaid-publisher/docs/geocsv/full-corpus-rc1-publication.md)
locates the immutable report, receipt and earlier public client verification.

Manifest SHA-256:
`7d75dbc537bfc39769b7feff496ca7f2d1834f67ff5b9e42502095161c9d5e16`.
Accepted report SHA-256:
`e310db4253c336233f95ebf8fd023b1091afc53ef16ac73d9cb5d74640367074`.

- [x] Fresh consumer suite: **425 passed, 9 expected warnings**, including
  **27 tutorial parity/execution checks**. Python **3.14.3**, pandas **3.1.0**,
  NumPy **2.5.4**, ObsPy **1.5.1**. Existing installed-wheel smoke and `pip check`
  passed; package source hashes match the publisher's accepted consumer.
- [x] Fresh publisher suite: **115 passed** in its separate Python **3.12.4**
  environment. All **103 local payload hashes** and **103 bundle members**
  match the manifest. The audit freshly read public latest/manifest and retained
  earlier full-public-download evidence; it did not repeat every remote download
  or every independent SAC comparison.
- [x] Fresh full-corpus acceptance gate passed against the canonical source,
  including **86,872 input fingerprints**, unchanged software, parsed payloads
  and Recording coverage. The accepted report still accounts for **43,333
  passing pairs** with **0 failed/missing/unsupported/unexamined**.
- [x] Reader/association tests cover declared types/units, literal two-space
  Location, missing required values, independent per-trace attachments, absent
  destinations and validation before mutation. Strict and containing-anchor
  examples actually reach their advertised paths. No source-default or
  earthquake-header mapping was introduced.

Inspected consumer commit: `2ca333de4fd53c770eda25c6ef4c4645150f34c3`;
publisher: `26862f0d30c6f42a5eb470ec8a5da9d88e2baf09`.
ObsPy read-only source: `50033e1daf95233cd4f30e95a49c37fd50be2ccd`, distinct
from the installed **1.5.1** used for runtime checks. Relevant MiniSEED correction
decoding, SAC conversion and contribution/style references were inspected.
The [publisher audit](../../../mermaid-publisher/docs/geocsv/release-audit-2026-11-06.md)
records producer/source identities and detailed reproductions. Localhost tests
initially hit sandbox restrictions and passed after access was enabled; this
was not a product failure. No dependency installation or environment change occurred.

## Maintenance and scientific boundary

Update both audit documents by **RA ID** when severity, status, numerical
evidence or resolution changes; explicitly acknowledge the counterpart in the
same change. Links provide manual coordination, not automatic synchronization.
Publisher validation changes require fresh acceptance evidence. Preserve all
frozen reports, source bytes and historical results.

Correct attachment proves which source metadata matched, not the independent
accuracy of the producer's model. For example, a shared producer error changing
**151,800 mbar to 1,518 mbar** and agreeing in its SAC output would yield
**15.18 m rather than 1,518 m** under the approved depth projection. Such
scientific producer validation stays with versioned automaid and publication;
it does not justify inference or default filling in this small consumer.
Neither a producer testing overhaul nor post-association object management is
part of these release conditions.
