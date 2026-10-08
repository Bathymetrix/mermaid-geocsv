# Retrieval observations

Execution evidence will be recorded here, including failures. Do not infer
EarthScope merging behavior from source inspection alone.

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

The fixture also has record 101 at `2018-07-06T01:49:28.613Z`, quality Q,
4736 samples. The second returned trace starts near that row's time but has
record 100's count. This is an ambiguity to investigate, not a demonstrated
association to either source row.

Exact sample-rate and quality equality are therefore not valid general
matching requirements for these downloaded examples. The 23.021 ms start
difference cannot be explained by simple truncation to milliseconds alone.
Do not infer a cause or select a matching tolerance from these two examples.

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
