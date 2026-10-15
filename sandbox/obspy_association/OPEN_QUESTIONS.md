# Open questions / TBD

Keep observations separate from decisions. Strict matching targets original
acquisitions; our guarantee ends at initial association.

The [merged-trace policy](../../docs/OBSPY_MERGED_TRACES.md) documents the
implemented `allow_merge=False` default and opt-in first-segment location
fallback. `stats.geocsv.association` distinguishes `one_segment` from
`first_segment`. Stronger coverage/provenance checks and the questions below
remain open.

1. **EarthScope aggregation and merging:** what does a month/year request
   return when original acquisitions share SNCL? Are acquisition boundaries
   retained, combined, or obscured? Distinguish archive/server behavior from
   MiniSEED record assembly and ObsPy's own client-side trimming.
2. **Source cardinality versus archive segmentation:** the user's construction
   has one algorithm:event row per original contiguous segment. Multiple input
   traces may legitimately use one row, including repeat requests of the same
   waveform in different MER files. A trace must not acquire metadata from
   multiple rows; multiple eligible rows remain an error. Still open: can a
   service split an original acquisition or combine coverage from several rows,
   and how should those transformed inputs be detected and handled?
3. **Quality indicators:** preserve the GeoCSV and MiniSEED indicators
   separately; they can differ after archive processing. The user-supplied
   stream mapping says quality labels DET/REQ/raw-buffer lineage, while
   nominal frequency is described by the rate/channel/location configuration.
   Keep the indicator available, but do not make equality a hard association
   filter. EarthScope's default “best” service may still use quality when
   selecting overlapping records; distinguish service selection from our
   association behavior. Legacy EarthScope archives may mark submitted records
   M after facility processing; see the observations and mapping note.
   DET Q versus REQ D can distinguish original overlapping streams, but
   EarthScope may expose both as M and may combine their coverage. Quality-based
   validation/disambiguation then loses that distinction. M alone proves no
   particular merge. Resolve this later; current association preserves quality
   separately and does not use equality as a hard match filter.
4. **Timing:** the prototype compares full UTC nanosecond values using each
   source timestamp's resolution by default, with a `time_tolerance` override
   in seconds. The previous bins have been removed. Revisit other producers without treating stored
   fractional digits as MERMAID clock accuracy. The user clarifies that the
   current waveform clock does not have millisecond timing precision;
   sub-millisecond GeoCSV fidelity is not a scientific requirement. Preserve
   downloaded timing and rate as authoritative. The scripts' one-second
   request margin is not a proposed matching tolerance.
5. **Coverage and boundaries:** do request bounds omit edge samples or include
   neighboring acquisitions? How do long requests compare with separate short
   requests? Does changing window partitioning change returned traces?
6. **Matching and ambiguity:** after complete SNCL/time checks, when do rate,
   count, and quality distinguish candidates? How should zero/multiple matches
   and partial acquisitions be reported without silently guessing?
7. **Initial attachment:** the sandbox uses a mutable row snapshot under
   `stats.geocsv`, plus immutable dataset metadata, source record index, and
   dataset index. It requires every requested destination container to be absent;
   it preserves processing history without adding an entry. Package promotion
   and the reserved SAC projection remain open.
8. **Verify the rebuilt processed dataset:** a newly added DET.WLT2 fixture
   reads as 2.5 Hz, location 10, quality Q, so DET is not limited to WLT5 / 20
   Hz. Automaid's quality assignment is stream-based: DET Q, REQ D, independent
   of rate. Inspect the fixture's source MER header, then verify representative
   regenerated outputs against the source classification, current SNCL mapping,
   and quality rule. A separate older v4.5.1 DET.WLT2 product has location 01;
   preserve such actual headers rather than rewriting them. Keep `.REQ.RAW`
   event products (D, about 40 Hz) distinct from physically recovered
   continuous raw-buffer streams (R, location 20). See
   [MERMAID_DATA_QUALITY.md](MERMAID_DATA_QUALITY.md).
9. **Upstream sampling-rate representation:** the user identifies integer-valued
   GeoCSV rates in place of intended measured rates as a writer issue, to be
   fixed outside this project. Preserve the parsed value and the downloaded
   rate; do not compensate by rounding or snapping either to a nominal rate.
   The agreed provisional minimum check is
   `abs(obspy_sps - geocsv_sps) <= 0.01` Hz, potentially grossly relaxed.
   Revisit it: the user reports microsecond-precision sampling timing in raw
   MER files (trustworthiness and exact encoding unverified); earlier GeoCSV
   outputs used single-decimal rates. Compare raw MER, writer input/output,
   MiniSEED headers, and ObsPy reading to check whether ObsPy changes the value
   slightly. Preserve all evidence and tighten the criterion when justified.
   See the [reader follow-up](../../docs/OPEN_QUESTIONS.md#mermaid-sampling-rate-follow-up).

The first probes already expose overlapping source rows, differing quality
indicators, rate differences, and a one-sample returned trace. See
[OBSERVATIONS.md](OBSERVATIONS.md) and the user-supplied
[quality mapping](MERMAID_DATA_QUALITY.md). The 0.01 Hz rate check is a
implemented provisional check for original processed traces. Exact original
count matching is implemented; transformed coverage matching remains open.

Settled: preserve the source row/provenance in `stats.geocsv`; validate core
waveform fields; populate coordinates with sea-level reference elevation 0;
offer optional SAC stla/stlo/stel and approximate stdp = mbar / 100. No geoid
model or later synchronization/persistence guarantee is introduced.
Downloaded waveform headers are presumed correct for this workflow; GeoCSV
does not override them. Rate estimates from count/duration would need
independent timing evidence, not ObsPy's rate-derived `endtime`.

Quality-code note: the provided automaid diff sets MiniSEED data quality to
`D` for requested waveforms and `Q` for detected waveforms, so those are the
expected submitted headers under that writer logic. The retrieved P0006 streams
report `M` for both source rows (GeoCSV Q and D, respectively). EarthScope
documents that its legacy archive rewrote every submitted record to `M` to
mark that facility processing may have modified it; existing `M` data remain
M after its archiving transition. Thus the observed `M` is consistent with
legacy archive handling, even when MERMAID submitted individual files. It
doesn't establish that the particular trace was combined with another file.
If MERMAID data are reingested under the newer archive process, contributor
Q/D codes should be served unchanged; verify the result then before making
quality-based association or precedence rules. See [EarthScope's archive
transition note](https://www.earthscope.org/news/miniseed-archiving-and-distribution-changes/).

Rebuilt-source follow-up: full combined GeoCSV histories now accompany the
sampled waveforms. The sampled measured rates are rendered to six decimal
places, replacing the earlier rate-format concern for these particular
outputs. Differences from MiniSEED remain below 0.000002 Hz in the sample;
the broader raw-MER/writer/ObsPy precision investigation is still open.
See [the fixture audit](../../data/fixtures/association/README.md).

## Clarifications and original-file inspection, 2026-10-15

`$MERMAID/waveforms/mseed/` and `sac/` are authorized read-only context sources;
they may contain symlinks into `$MERMAID/processed/`. SAC remains a comparison
reference, never a metadata input for MiniSEED association.

The July 13 DET file and three repeated REQ files named by the user were
inspected directly. DET is Q/4768 samples; all REQs are D/9600 samples with
equal start times, sampling rates, and sample arrays. In the rebuilt P0006
GeoCSV, all three REQs have the same matching row (238); DET matches row 237.
See the [inspection evidence](OBSERVATIONS.md#original-july-13-waveforms-2026-10-15).

GeoCSV already carries NPTS as `SampleCount` (typed Int64), and the associator
checks it against `stats.npts` and data length. No additional NPTS column is
needed for the current schema. Count is additional evidence, not a substitute
for SNCL/time or proof of identical samples/lineage.

Receiver position is interpolated at the first sample time, regardless of
waveform length or subsequent request dates. There is no duration-averaged
position. Repeated identical requests can therefore share a source row and
location. A case with different counts still needs the existing count checks;
the position convention alone does not authorize ignoring a count mismatch.
Only explicit `allow_merge=True` permits the documented longer-trace fallback.

Contiguity is necessary to establish a segment; an individual MiniSEED record
always has a start time. Distinguish discontinuity from the expected next
sample from merely encountering another record header. The legacy month
response also contains overlapping DET/REQ coverage without a clean original
acquisition boundary, so gap inspection alone does not recover its provenance.
The opt-in first-segment location policy does not settle reconstruction of
merged coverage, quality-based selection, invalid-event-row handling (audit
finding 4), performance (finding 5), or public API promotion. The audit and
other discussion remain open.
