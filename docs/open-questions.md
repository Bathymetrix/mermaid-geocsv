# Open scientific questions and deferred scope

The [reader specification](reader-spec.md), [association reference](obspy-association.md),
and [SAC mapping](sac.md) define current behavior. The questions here remain
unresolved; they do not authorize silently changing scientific values or
matching rules. The [GeoCSV v2.0.4 specification](references/GeoCSV_v2.0.4.pdf)
does not settle every MERMAID convention or interoperability question.

## Questions for the GeoCSV specification

### 1. Do custom keyword lines define dataset-wide metadata?

Clarify whether custom declarations such as `#GeodeticDatum: WGS84` have
dataset scope, and how they differ from free-text comments. If declarations
can vary by row, define inheritance and the meaning of records preceding a
declaration. Dataset-wide pandas attrs cannot represent row-varying values.
The reader's [changed-declaration policy](reader-spec.md#comments-and-metadata-declarations)
is provisional for unknown keys, rather than a requirement established by v2.0.4.

### 2. What is the exact grammar of `field_*` lists?

Specify width, separator, quoting, and empty-entry rules, including whitespace
delimiters. Correct or explain the short IRIS units and R2R types lists and
the unquoted comma in R2R's long name. The
[preserved specification examples](../data/fixtures/GeoCSV_v2.0.4_examples/README.md)
record these inconsistencies without repairing them. The reader requires
one list entry per header field; the specification does not explicitly state
that width rule.

### 3. Which source values mean missing data?

Define default missing tokens, `field_missing` precedence, and a representation
for literal reserved strings. The reader's universal case-insensitive `nan`
handling and special empty string-valued `Location` are MERMAID conventions,
not v2.0.4 requirements. Current [missing-value rules](reader-spec.md#field-types-and-missing-values)
are maintained in the reader reference.

### 4. Does a datetime unit establish its timezone?

UNAVCO declares UTC units for timezone-free timestamps. Clarify whether units
establish timezone semantics and how they interact with explicit offsets.
The reader preserves units without inferring a timezone.

### 5. Which ISO 8601 datetime forms must readers support?

Publish an interoperable profile covering date forms, offsets, fractional
precision, range, and handling of otherwise valid forms outside that profile.
The reader accepts its documented [extended-calendar subset](reader-spec.md#numeric-limits-and-datetime-syntax);
it does not claim support for all ISO 8601 forms.

### 6. How should container versions be recognized?

Define version syntax, forward compatibility, and treatment of existing
unversioned MERMAID declarations. The reader currently recognizes GeoCSV
without validating a version, including future-looking version strings.
Its allowance for comments before `#dataset` is an explicit compatibility
choice, separate from the specification's first-line recommendation.

## MERMAID sampling-rate follow-up

Compare raw MER timing quantities and units, writer inputs and serialized
rates, encoded MiniSEED rates, and ObsPy output. Establish whether differences
arise from upstream formatting, waveform encoding, or reader conversion.
Stored microseconds and six-decimal rates do not independently establish
measurement accuracy. Rate computed from ObsPy's rate-derived endtime is
not independent evidence.

The [fixture evidence](../data/fixtures/association/README.md#tolerance-evidence)
supports the current agreement criterion for the checked sample. It does not
settle raw-MER precision across producers and instrument generations. Reading
preserves supplied rates; upstream corrections belong in the producer.

## Association scientific questions

### Archive segmentation and overlap lineage

Determine which acquisition boundaries and samples survive long requests,
partitioned requests, client trimming, MiniSEED record assembly, and archive
overlap selection. Exact source-grid coverage does not identify which source
supplied overlap values or detect gaps already filled upstream. The current
fallback adopts one geographic anchor without reconstructing acquisition
lineage. Quality M alone supplies neither provenance nor a merge history.

A preserved month request for P0006, 2018-06-29 through 2018-07-29, produced
11 traces, all M, versus 14 source event records. It included a one-sample
trace followed by a 3,584-sample trace approximately 0.024992 s after the next
expected sample. This bounded observation establishes no general service
completeness or segmentation policy. The response and request logs remain
optional local evidence under ignored `data/local/obspy_retrievals/`; ordinary
tests do not require them.

Inspection of three original July 13 P0006 repeated REQ waveforms found equal
starts, rates, counts, and sample arrays, all corresponding to source record
238. That supports repeated traces independently using one row, without
establishing archive transformation rules. The portable
[clipped-response fixture](../tests/fixtures/association/P0006_20180713_earthscope/README.md)
records the separately tested overlap case.

### P0006 July 6 REQ response: DET start with REQ count

An unresolved upstream discrepancy was rechecked on 2026-10-27. All entries
have SNCL `MH.P0006.00.BDH` on 2018-07-06:

| Source | Start UTC | Samples | Quality |
| --- | --- | ---: | --- |
| Complete GeoCSV record 100, REQ | 01:49:28.590000 | 4,800 | D |
| Complete GeoCSV record 101, DET | 01:49:28.613000 | 4,736 | Q |
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

### Instrument and product evidence

Verify the hardware generations affected by reported REQ sampling-rate/time
shifts and whether reconstruction uses acquisition-time or request-time rate.
Claims that DET timing is more accurate, REQ location is less certain, and
current hardware fixes earlier behavior require instrument-specific evidence.
Do not generalize those claims across the archive.

Check source MER classification and scale for the non-20-Hz DET.WLT2 example;
the processed-header audit did not independently inspect every raw MER header.
Preserve historical location codes as source evidence. The
[product reference](mermaid-data-quality.md) distinguishes requested RAW events
from recovered continuous-buffer data.

Resolve the missing P0006 buffer average rate and verify the P0023 value and
the proposed Pipatprathanporn & Simon (2022) citation. Identify the incomplete
“Ivy” reference and verify Nolet et al. (2024). The supplied MERMAID manual
reference 452.000.852, Version 00, reportedly uses 101 mbar per metre;
independent verification is pending. Current SAC mapping follows automaid's
100 mbar per metre approximation.

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
| `TimeCorrection` | Automaid uses `user3` in seconds; retain as metadata, never apply twice. |
| `TimeDelay` | Needs an agreed slot and units; not `b`, `o`, or a pick header. |
| `InstrumentDescription` | `kinst` fits a short designation, not the full description. |
| `MethodIdentifier` | No faithful dedicated SAC field; extracting a version loses source content. |
| `DataQuality` | SAC `iqual` has different categories; no direct Q/D/M mapping. |
| Orientation | Needs a source and agreed SEED/SAC conventions; hydrophone zeros would be an explicit choice. |
| Calibration | Outside package scope; GeoCSV supplies no counts-to-Pa factor. |

Automaid reserves `user0`–`user2` for SNR, criterion, and trigger index,
`user3` for clock correction, and its own `kuser0`–`kuser2` meanings. Do not
allocate those slots incidentally or reconstruct absent processing parameters.
