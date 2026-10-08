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
4. **Timing:** compare nanosecond waveform starts with GeoCSV millisecond
   timestamps. Choose matching tolerance only after inspecting discrepancies;
   the scripts' one-second request margin is not a proposed tolerance.
5. **Coverage and boundaries:** do request bounds omit edge samples or include
   neighboring acquisitions? How do long requests compare with separate short
   requests? Does changing window partitioning change returned traces?
6. **Matching and ambiguity:** after complete SNCL/time checks, when do rate,
   count, and quality distinguish candidates? How should zero/multiple matches
   and partial acquisitions be reported without silently guessing?
7. **Initial attachment:** settle source-record schema, mutability, existing
   header conflicts, and whether association appends a processing entry.
8. **Nominal versus returned sampling:** why is GeoCSV 20 Hz returned as
   approximately 20.007 Hz? Establish how rates should be used in matching
   without overwriting scientifically meaningful waveform timing.

The first probes already expose overlapping source rows, changed quality,
rate differences, and a one-sample returned trace. See
[OBSERVATIONS.md](OBSERVATIONS.md); strict rate/count/quality matching remains
provisional rather than an implemented rule.

Settled: preserve the source row/provenance in `stats.geocsv`; validate core
waveform fields; populate coordinates with sea-level reference elevation 0;
offer optional SAC stla/stlo/stel and approximate stdp = mbar / 100. No geoid
model or later synchronization/persistence guarantee is introduced.
