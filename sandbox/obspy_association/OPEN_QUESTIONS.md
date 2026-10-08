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
3. **Overlaps and quality:** how does default service selection handle Q/D
   overlaps? Does explicit quality selection change sample coverage? GeoCSV
   quality should remain evidence, not an assumed server precedence rule.
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
8. **Upstream sampling-rate representation:** the user identifies integer-valued
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

The first probes already expose overlapping source rows, changed quality,
rate differences, and a one-sample returned trace. See
[OBSERVATIONS.md](OBSERVATIONS.md). The 0.01 Hz rate check is a provisional
design decision, not implemented code; count and quality matching remain open.

Settled: preserve the source row/provenance in `stats.geocsv`; validate core
waveform fields; populate coordinates with sea-level reference elevation 0;
offer optional SAC stla/stlo/stel and approximate stdp = mbar / 100. No geoid
model or later synchronization/persistence guarantee is introduced.
Downloaded waveform headers are presumed correct for this workflow; GeoCSV
does not override them. Rate estimates from count/duration would need
independent timing evidence, not ObsPy's rate-derived `endtime`.
