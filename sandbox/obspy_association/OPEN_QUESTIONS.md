# Open questions / TBD

Keep observations separate from decisions. Scope remains original downloaded
traces; our guarantee ends at initial association.

1. **EarthScope aggregation and merging:** what does a month/year request
   return when original acquisitions share SNCL? Are acquisition boundaries
   retained, combined, or obscured? Distinguish archive/server behavior from
   MiniSEED record assembly and ObsPy's own client-side trimming.
2. **One row versus multiple traces:** can a single original acquisition be
   returned as several traces because of gaps, quality, or sampling changes?
   Can one returned trace contain samples from several GeoCSV waveform rows?
3. **Quality indicators:** preserve the GeoCSV and MiniSEED indicators
   separately; they can differ after archive processing. The user-supplied
   stream mapping says quality labels DET/REQ/raw-buffer lineage, while
   nominal frequency is described by the rate/channel/location configuration.
   Keep the indicator available, but do not make equality a hard association
   filter. EarthScope's default “best” service may still use quality when
   selecting overlapping records; distinguish service selection from our
   association behavior. Legacy EarthScope archives may mark submitted records
   M after facility processing; see the observations and mapping note.
4. **Timing:** establish an acquisition-matching rule without treating stored
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
7. **Initial attachment:** settle source-record schema, mutability, existing
   header conflicts, and whether association appends a processing entry.
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
   MER files (trustworthiness and exact encoding unverified) but writes
   single-decimal rates to GeoCSV. Compare raw MER, writer input/output,
   MiniSEED headers, and ObsPy reading to check whether ObsPy changes the value
   slightly. Preserve all evidence and tighten the criterion when justified.
   See the [reader follow-up](../../docs/OPEN_QUESTIONS.md#mermaid-sampling-rate-follow-up).

The first probes already expose overlapping source rows, differing quality
indicators, rate differences, and a one-sample returned trace. See
[OBSERVATIONS.md](OBSERVATIONS.md) and the user-supplied
[quality mapping](MERMAID_DATA_QUALITY.md). The 0.01 Hz rate check is a
provisional design decision, not implemented code; count/coverage matching
remains open.

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
