# Retrieval observations

This document preserves dated execution evidence, including failures,
originally recorded under `sandbox/obspy_association/OBSERVATIONS.md`. Counts,
versions, timing rules, and references below describe their recorded runs;
they are not a statement of today's service behavior or package defaults.
Do not infer EarthScope merging behavior from source inspection alone.

For current behavior, see the [association tutorial](tutorials/ASSOCIATE.md),
[open scientific questions](OPEN_QUESTIONS.md#association-scientific-questions),
and implemented [SAC export](tutorials/WRITE_SAC.md). Association uses a fixed
explicit time tolerance; historical bins and SAC placeholders below were
superseded. Geographic SAC comparisons are now implemented, with coverage
and precision defined in the writing tutorial.
The [retrieval scripts](../sandbox/obspy_association/README.md) remain in the
sandbox; their saved responses and logs remain under its ignored `downloads/`.

## Fixture verification

`geocsv.read` confirms source record 98 has quality Q, 4832 samples at 20 Hz;
record 100 has quality D, 4800 samples at 20 Hz. Both describe
`MH.P0006.00.BDH` and use `Algorithm(event):automaid:v4.5.9`.

## Service execution, 2026-10-08

Executed with ObsPy 1.5.1 against `https://service.earthscope.org`, without
credentials. An initial sandboxed attempt failed DNS/service discovery;
the retry with network access enabled succeeded. No plot was opened.
Raw MiniSEED responses are saved locally under ignored `downloads/`.

### Short requests

Both the standard `get_waveforms` result and the separately saved raw response
read with ObsPy returned one trace per short request, with these headers:

| Source record | Source count | Returned count | Source rate (Hz) | Returned rate (Hz) | Start difference (returned − GeoCSV) | Source / returned quality |
| --- | --- | --- | --- | --- | --- | --- |
| 98 | 4832 | 4832 | 20.0 | 20.007062146892654 | +0.000618 s | Q / M |
| 100 | 4800 | 4800 | 20.0 | 20.007062146892654 | +0.023021 s | D / M |

Returned starts are `2018-06-29T17:07:31.205618Z` and
`2018-07-06T01:49:28.613021Z`. Raw file sizes were 20,480 and 24,576 bytes.
They contain STEIM2, big-endian, 4096-byte records. The normal client path
adds a `trim` processing entry even though these examples retained the count.

The user supplied the relevant automaid writer change: requested waveforms set
MiniSEED data quality `D`, and detected waveforms set `Q`. Those are the
submitted qualities expected from that writer, consistent with their GeoCSV
rows. EarthScope's [archive transition note](https://www.earthscope.org/news/miniseed-archiving-and-distribution-changes/)
explains that its legacy archive changed all submitted quality codes to `M`
to mark records as potentially modified during facility processing. Existing
legacy `M` records will retain that code; new submissions after the transition
retain contributor quality codes. The retrieved `M` headers therefore appear
consistent with legacy archive handling, not necessarily an incorrect MERMAID
file header. EarthScope notes that `M` indicates potential modification; it
does not prove a particular trace combines multiple submitted files.
Recheck after MERMAID data are reingested/updated before making a quality-based
association or precedence rule. The current FDSN dataselect documentation also
says default “best” selection merges available qualities and removes overlaps
by quality preference, while its `quality` request parameter is now retired:
[service help](https://service.earthscope.org/fdsnws/dataselect/docs/1/help/).

The fixture also has record 101 at `2018-07-06T01:49:28.613Z`, quality Q,
4736 samples. The second returned trace starts near that row's time but has
record 100's count. This is an ambiguity to investigate, not a demonstrated
association to either source row.

Exact sample-rate and quality equality do not hold for these downloaded
examples. This does not establish that rate mismatches should be accepted in
the eventual association API. The 23.021 ms start
difference cannot be explained by simple truncation to milliseconds alone.
Do not infer a cause or select a matching tolerance from these two examples.

### Sampling-rate clarification from the user

MERMAID currently has a finite set of nominal acquisition rates. The supplied
table lists 20, 40, 10, 5, 2.5, and 1.25 Hz, with channel/location/quality
distinctions. It also lists nominal 40 Hz raw-buffer data separately and
reports a measured 40.01406 Hz for P0023. The P0006 raw-buffer rate is shown
as an unresolved `XX` in the screenshot, not an established value.

The user states that integer-valued GeoCSV rates in place of intended measured
rates require an upstream writer fix, outside this project's scope. The fixture
literally contains `20.0`: it is an integer-valued floating-point rate, not
evidence that the parser cast or rounded a more precise source value.
The finite nominal set is context, not authorization to round waveform
headers, rewrite GeoCSV, or introduce nearest-nominal matching. Preserve both
reported rates and revisit comparison using corrected source data.

The user further establishes downloaded waveform attributes as the operational
authority and clarifies that the current waveform clock does not have
millisecond timing precision. The sub-millisecond digits above record header
representations, not demonstrated clock accuracy. This does not make precise
waveform sample intervals meaningless, and it does not authorize overwriting
downloaded timing from GeoCSV. No hardware-precision verification was performed.

### Filename, quality, and raw-buffer distinction

Inspected the newly added fixture
`20210527T154441.0030_60AFC696.MER.DET.WLT2.mseed` with ObsPy 1.5.1. It reads
as `MH.P0030.10.MDH`, 2.5009128631 Hz, 584 samples, and MiniSEED quality Q.
Its paired SAC file has `kuser1=DET.WLT2`. This confirms a DET.WLT2 product at
2.5 Hz with quality Q and the current helper's location 10. It contradicts
the earlier interpretation that DET was restricted to WLT5 / 20 Hz. The
source MER header still needs inspection to verify how this product was
classified and encoded before processing. Preserve the quality rule
independently of rate: DET is Q and REQ is D.

A separate older v4.5.1 DET.WLT2 example,
`20210528T053250.0030_60B08BB3.MER.DET.WLT2.mseed`, reads as
`MH.P0030.01.MDH`, 2.5009138679 Hz, 3000 samples, and quality Q. Its location
01 differs from the current helper's location 10, which remains a historical
location-code difference. Preserve the downloaded trace's actual SNCL.

Separately inspected local `.REQ.RAW.mseed` event products and continuous P0023
buffer files. The `.REQ.RAW` products have MiniSEED quality D and use several
location codes across historical products; a recent example is location 10.
They are requested event files with un-wavelet-transformed data, not the
physically recovered continuous raw-buffer stream. The latter is represented
locally by files such as `buffers/P0023/mseed/MH.P0023.20.BDH...mseed`, which
ObsPy reads at 40.01405975 Hz with quality R. This resolves the apparent
location discrepancy: current `STAGES=-1` event mapping to location 10 and the
table's physical-buffer location 20 describe different data products. Do not
infer the R quality code or location 20 from the filename token `RAW`.

### Month request

Requested `MH.P0006.00.BDH` from 2018-06-29 00:00:00Z through
2018-07-29 00:00:00Z. The raw response was 237,568 bytes. Parsing produced
11 traces, all quality M, at four slightly different rates around 20.007 Hz.
The fixture contains 14 `Algorithm(event)` rows with this complete SNCL and
start times inside the request window.

Most gaps separate sparse acquisitions; there were 10 reported gaps and no
reported overlaps in the parsed result. Three cases merit closer inspection:

- Records 100 and 101 describe overlapping requested/detected waveforms;
  the result has one 4800-sample trace starting at 01:49:28.613021Z.
- Records 237 and 238 have 4768 and 9600 samples at starts
  2018-07-13T09:48:03.139Z and 09:48:31.908Z. The result has a single
  10,176-sample trace starting at 09:48:03.139965Z. This is consistent with
  combined coverage, but does not establish which layer combined it or how
  overlapping samples were selected.
- Records 445–447 each have 3584 samples and nearby starts on July 28.
  The result has one trace of **one sample** at 22:56:19.555182Z, then a
  3584-sample trace at 22:56:19.630156Z, with a reported 0.024992-second gap.

These findings rule out assuming one GeoCSV row per returned trace in this
window. They do not establish missing data, archive precedence, or a general
service merging policy. A year-long request has not been executed.

## Verification

Both scripts compiled, and both live retrieval examples completed. The
package's 136 tests passed after adding the optional ObsPy dependency.
Editable installation metadata confirms version 0.10.3 and the `obspy` extra.

## Rebuilt processed fixtures, 2026-10-13

`$MERMAID/processed/` is the canonical read-only source. The inventory contains
43,337 acoustic event MiniSEED files across six naming combinations. We copied
three random paired SAC/MiniSEED examples for each present combination (18
pairs), plus verbatim full combined GeoCSV histories for their 14 floats.
The [fixture inventory](../data/fixtures/association/README.md) and manifest
record the seed, missing combinations, original source paths, and file hashes.

A read-only audit of all 43,337 source MiniSEED files found no SNCL or
DET Q / REQ D inconsistencies relative to the documented current mapping.
The selected SAC files agree on SNCL and `kuser1` labels. Each selected waveform
has one association in its full GeoCSV history, with the expected quality.
The GeoCSV histories render measured rates to six decimal places; all sampled
MiniSEED/GeoCSV rate differences are below 0.000002 Hz. Geographic/depth SAC
header comparisons are deferred. Some SAC reads emit ObsPy's documented
sample-spacing rounding warning; MiniSEED remains the timing/rate ground truth.

The sandbox prototype now supports a Trace or Stream, including records from
multiple floats. It validates all matches and projected coordinates before
mutation, retains a row/provenance snapshot under `stats.geocsv`, and preserves
waveform core fields. Its time criterion is equal UTC millisecond bins, its
original sample count criterion is exact, and the provisional rate criterion
is 0.01 Hz. Quality is retained separately rather than used to select matches.
At that stage, optional SAC projection was an explicit `NotImplementedError`
placeholder. The unused keyword and placeholder were removed on 2026-10-16;
projection remains in the [future-work plan](FUTURE.md#project-associated-metadata-into-sac-headers).

## Original July 13 waveforms, 2026-10-15

Inspected the four user-named files under `$MERMAID/waveforms/mseed/`, whose
entries are symlinks to processed originals. All read as one trace each with
SNCL `MH.P0006.00.BDH`; no source files or symlinks were modified.

| Filename | Quality | Start UTC | NPTS | Rebuilt GeoCSV row |
| --- | --- | --- | ---: | ---: |
| `20180713T094803.06_5B4C1D4F.MER.DET.WLT5.mseed` | Q | 2018-07-13T09:48:03.139974Z | 4768 | 237 |
| `20180713T094831.06_5B6DEF16.MER.REQ.WLT5.mseed` | D | 2018-07-13T09:48:31.908782Z | 9600 | 238 |
| `20180713T094831.06_5B73E987.MER.REQ.WLT5.mseed` | D | 2018-07-13T09:48:31.908782Z | 9600 | 238 |
| `20180713T094831.06_5B773AE6.MER.REQ.WLT5.mseed` | D | 2018-07-13T09:48:31.908782Z | 9600 | 238 |

All four rates are 20.007052186177717 Hz. The three REQ traces have exactly
equal sample arrays, starts, rates, and counts. This establishes equality of
the inspected waveform data/core headers, not a claim about every file byte
or every item of request provenance. The files' different MER identifiers
do not require different GeoCSV metadata rows. The current prototype was
called on all four fresh traces in one Stream using the full rebuilt P0006
GeoCSV history: DET associated with row 237 and all REQs with row 238.

GeoCSV `SampleCount` is already present (4768 / 9600), equivalent to NPTS,
and is checked by the prototype. Rebuilt GeoCSV rates here are 20.007051 Hz;
the waveform rate is preserved. Position is taken from the matched row at
the first sample time, independently of request date and waveform duration.

This supports the user's many-traces-to-one-row rule. It does not establish
an association policy for the legacy EarthScope response's one 10176-sample
M trace spanning these overlapping source windows. The response's loss of
Q/D distinctions, possible coverage combination, and quality-based validation
remain open. No functional code or matching policy changed for this inspection.


## Preserved clipped P0006 EarthScope response, 2026-10-21

A live HTTPS dataselect request for `MH.P0006.00.BDH` from
2018-07-13T09:48:10Z through 09:56:00Z returned HTTP 200 and 45,056 bytes.
Unlike the older ignored probes, its exact response is now a tracked portable
[fixture with request provenance and original comparison pairs](../tests/fixtures/association/P0006_20180713_earthscope/README.md).
The request clips the start of original DET row 237 and the end of overlapping
REQ row 238. The existing full P0006 fixture supplies unedited source metadata.

ObsPy 1.5.1 reads one unmasked quality-M trace with 9,403 samples at
20.007052186177717 Hz, from 09:48:10.037533 to 09:55:59.971830 UTC.
No client trim, explicit merge, filling or resampling is needed. Independent
sample comparison finds DET samples `[138, 4768)` followed by REQ samples
`[4192, 8965)` in this response. This observation does not establish a general
archive precedence policy or identify which service/archive layer assembled it.

Strict association rejects the changed start/count. The containing-anchor
fallback rejects at 1 ms but succeeds with explicit 25 ms tolerance: its
clipped ranges `[0, 4630)` and `[438, 9403)` have a 4,192-sample overlap and
cover the complete returned grid. The association report measures a maximum
21.813578 ms boundary-grid difference at sample 438/source row 238 and a
maximum rate difference of approximately 0.00000118618 Hz. These observations
do not change package defaults or establish clock accuracy.

The offline test also exports SAC with DET anchor geography and verifies
returned samples plus STLA/STLO/STDP/STEL against the original DET reference.
It checks unchanged waveform state on rejection, association and export.
Version 0.20.0's public behavior is unchanged by this fixture/test addition.


### Half-sample coverage policy adopted, 2026-10-21 (0.21.0)

The prior 0.20.0 rejection/25 ms probes above retain their dated meaning.
The same captured response now associates with `allow_first_segment=True`
and no absolute timing override. Its unchanged 21.813578 ms maximum grid offset
fits half the waveform interval, approximately 24.991188 ms. Start/containment
and rate thresholds are unchanged. The report still records the measured
coverage ranges and differences, and SAC export remains checked against the
association-time waveform snapshot.

A record-by-record read also shows that not all timing disagreement originates
in EarthScope timestamp changes: local original DET and REQ grids already differ
by 21.040431 ms in phase. The first retained REQ response record starts
21.140718 ms before its corresponding sample on the assembled Trace grid.
ObsPy joins those records within half an interval. Archive overlap selection
and reader assembly are distinct; the legacy LOG/MER correction's contribution
has not been isolated. See the [source-based comparison](STREAM.md#miniseed-record-assembly-and-half-sample-association-coverage).
