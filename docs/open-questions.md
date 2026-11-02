# Open scientific questions and deferred scope

The [reader specification](reader-spec.md), [association reference](obspy-association.md),
and [SAC mapping](sac.md) define current behavior. The questions here remain
unresolved; they do not authorize silently changing scientific values or
matching rules. The [GeoCSV v2.0.4 specification](references/GeoCSV_v2.0.4.pdf)
does not settle every MERMAID convention or interoperability question.

Scientific estimation methods, assumptions and validation belong to the automaid
version in the GeoCSV attribution header and scientific publication. Measurement
rows provide observations; derived times/locations are best estimates that users
may reinterpolate.

## Association scientific questions

### Archive segmentation and overlap lineage

Determine which acquisition boundaries and samples survive long requests,
partitioned requests, client trimming, MiniSEED record assembly, and archive
overlap selection. Exact source-grid coverage does not identify which source
supplied overlap values or detect gaps already filled upstream. The current
anchor association copies one source geography without reconstructing acquisition
lineage. Quality M alone supplies neither provenance nor a merge history.

A preserved month request for P0006, 2018-06-29 through 2018-07-29, produced
11 traces, all M, versus 14 source event records. It included a one-sample
trace followed by a 3,584-sample trace approximately 0.024992 s after the next
expected sample. This bounded observation establishes no general service
completeness or segmentation policy. The response and request logs remain
optional local evidence under ignored `data/local/obspy_retrievals/`; ordinary
tests do not require them.

Inspection of three original July 13 P0006 repeated REQ waveforms found equal
starts, rates, counts, and sample arrays, all corresponding to source index
238. That supports repeated traces independently using one row, without
establishing archive transformation rules. The portable
[clipped-response fixture](../tests/fixtures/association/P0006_20180713_earthscope/README.md)
records the separately tested overlap case.

### P0006 July 6 REQ response: DET start with REQ count

An unresolved upstream discrepancy was rechecked on 2026-10-27. All entries
have SNCL `MH.P0006.00.BDH` on 2018-07-06:

| Source | Start UTC | Samples | Quality |
| --- | --- | ---: | --- |
| Complete GeoCSV source index 100, REQ | 01:49:28.590000 | 4,800 | D |
| Complete GeoCSV source index 101, DET | 01:49:28.613000 | 4,736 | Q |
| Saved EarthScope response | 01:49:28.613021 | 4,800 | M |

Indices refer to the shared [P0006 snapshot](../data/fixtures/P0006/README.md).
Local original MiniSEED starts are 01:49:28.590640 for REQ and
01:49:28.613021 for DET. The response sample array equals neither original;
the rechecked response bytes equal the earlier saved response. Its original
request and raw bytes are preserved as `P0006_record_100.mseed` and
`event_retrieval.log` under the optional local evidence directory above.

Strict association rejects: the REQ start differs by 23.021 ms and the DET
count by 64 samples. Opt-in containment is ambiguous because both source
intervals contain the first sample. Do not widen tolerances, discard competing
rows, or rewrite fixtures to hide this discrepancy.

Compare original MER timing/counts, automaid exports, historically submitted
MiniSEED bytes, returned record starts and sample arrays. Current processed
originals alone do not establish the submitted bytes. Saving a raw FDSN
response bypasses client trimming, but reading still assembles records into
traces. The cause and responsible upstream component remain unresolved.

## Deferred workflows and mappings

These are scope decisions requiring concrete consumers and scientific rules,
not promised APIs: GeoCSV authoring, resampled/transformed acquisition
reconstruction, StationXML/Inventory conversion and position epochs, live
metadata synchronization, and package-managed association persistence.
Production promotion remains a separate [hosting decision](hosting.md).

Only four geographic SAC mappings are implemented; see [SAC](sac.md).
Additional mappings require explicit agreement:

| Concern | Constraint |
| --- | --- |
| `TimeCorrectionApplied` | Automaid uses `user3` in seconds; retain as metadata, never apply twice. |
| `ClockOffset` | Needs an agreed slot and units; not `b`, `o`, or a pick header. |
| `InstrumentDescription` | `kinst` fits a short designation, not the full description. |
| `MethodIdentifier` | No faithful dedicated SAC field; extracting a version loses source content. |
| `DataQuality` | SAC `iqual` has different categories; no direct Q/D/M mapping. |
| Orientation | Needs a source and agreed SEED/SAC conventions; hydrophone zeros would be an explicit choice. |
| Calibration | Outside package scope; GeoCSV supplies no counts-to-Pa factor. |

Automaid reserves `user0`–`user2` for SNR, criterion, and trigger index,
`user3` for clock correction, and its own `kuser0`–`kuser2` meanings. Do not
allocate those slots incidentally or reconstruct absent processing parameters.
