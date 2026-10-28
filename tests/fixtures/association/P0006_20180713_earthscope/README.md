# P0006 clipped EarthScope response, 2018-07-13

This fixture preserves an **unmodified live EarthScope MiniSEED response**,
retrieved on 2026-10-21, plus two original acquisition MiniSEED/SAC pairs for
independent comparison. Ordinary tests read these files offline and do not
contact EarthScope. No locally merged or client-trimmed waveform is stored.

## Request and source context

The HTTPS FDSN dataselect request selects `MH.P0006.00.BDH` from
**2018-07-13T09:48:10Z through 2018-07-13T09:56:00Z**, with no quality filter.
The exact URL, parameters, retrieval time, HTTP status and selected response
headers are in `manifest.json`. `earthscope.mseed` is the exact response body:
45,056 bytes, SHA-256
`6124b6e4014c87a3ac6e600334480cf74244a9372fd6247a9c8e9d9debacdef4`.
The manifest is sufficient to repeat the request as a separate live experiment;
a later service response need not have identical bytes or segmentation.

The source metadata is the existing tracked full
[`P0006.geocsv`](../../../../data/fixtures/P0006/P0006.geocsv), refreshed
verbatim from the current processed automaid v4.5.14 export on 2026-10-21,
with its source path and hash retained in the manifest. No subset is created.
Rows 237 and 238 (zero-based
file-wide records, physical starting lines 247 and 248) describe overlapping
DET and REQ segments. Row 236 is nearby pressure context; row 239 is the next
event. Full-history matching, including competing rows, runs in the test.
The same current snapshot supplies the parser and download examples; no older
GeoCSV export is required for this response test.

| Original | Start UTC | Last sample UTC | Samples | Quality |
| --- | --- | --- | ---: | --- |
| DET, `20180713T094803.06_5B4C1D4F.MER.DET.WLT5` | 09:48:03.139974 | 09:52:01.405959 | 4,768 | Q |
| REQ, `20180713T094831.06_5B6DEF16.MER.REQ.WLT5` | 09:48:31.908782 | 09:56:31.689607 | 9,600 | D |

The request begins inside the DET segment, before the REQ begins. It ends
inside the REQ segment, after the DET ends. Both original rates are
20.007052186177717 Hz. Both `.mseed` and `.sac` originals were copied verbatim
from authorized `$MERMAID/waveforms/` references; the manifest records source
paths, resolved protected processed paths, byte counts, hashes and waveform
headers. No originals or symlinks were modified. SAC files are comparison
references, not association inputs. The repeated REQ deliveries documented in
the historical observations are not copied again.

## Observed response and expected behavior

Reading the raw response with ObsPy 1.5.1 returns **one unmasked trace**, quality
M, 9,403 samples at 20.007052186177717 Hz, from
09:48:10.037533 to 09:55:59.971830 UTC. It already lies inside the request;
no client trim, explicit merge, interpolation, filling or resampling is needed.
The request times need not themselves lie on a sample grid.

- Strict association rejects the changed start/count.
- `allow_first_segment=True` succeeds without a timing override.
  The REQ range's approximately 21.8 ms offset fits the automatic half-sample
  allowance of approximately 24.991 ms. Strict start/containment tolerance is
  separate from source-grid placement. Exact midpoint ties,
  excessive endpoint drift and incomplete coverage still raise.
- The geographic anchor is DET row 237. Clipped source ranges are `[0, 4630)`
  and `[438, 9403)`. Their 4,192-sample overlap is counted once, leaving exactly
  9,403 covered samples. Source counts remain 4,768 and 9,600.
- The association report records a 6.898533 s waveform-minus-anchor start
  offset, a maximum boundary-grid difference of 0.021813578 s at waveform
  sample 438 / source row 238, and a maximum rate difference of approximately
  0.000000186178 Hz against the refreshed GeoCSV. These are different quantities.
- SAC export preserves the returned samples at SAC float32 precision and uses
  the DET anchor's STLA/STLO/STDP/STEL, compared with its independently read
  paired SAC reference. Latitude/longitude must exactly equal the current
  GeoCSV values rounded to SAC float32, and may differ from the independent
  reference by at most one float32 representable step (one ULP). This allows
  the current float64 calculation to round differently without a general
  relative-error allowance. Depth and elevation still require exact equality.
  It does not reconstruct other original SAC headers.

For this specific response, the first 4,630 samples equal DET samples
`[138, 4768)`; the remaining 4,773 equal REQ samples `[4192, 8965)`. This is
observed sample equality, **not a general EarthScope overlap precedence rule**
or evidence of which archive layer selected the values. The test preserves
this evidence without inferring acquisition lineage from quality M.

See [`tests/test_earthscope_response.py`](../../../test_earthscope_response.py),
[open archive questions](../../../../docs/OPEN_QUESTIONS.md#association-scientific-questions), and
[current coverage policy](../../../../docs/OBSPY_ASSOCIATION.md#clipped-and-combined-windows).
ObsPy source was inspected read-only at
`50033e1daf95233cd4f30e95a49c37fd50be2ccd`, separately from installed 1.5.1,
including the FDSN client's parse/trim boundary. The fixture test reads the
response directly and never calls the live client.

Record-level checks distinguish archive selection from reader assembly. The
first retained REQ record header starts at 09:52:01.434792000 UTC while the
corresponding assembled Trace sample is at 09:52:01.455932718. The local
original REQ start is already 21.040431 ms off the nearest original DET sample.
These are separate from the report's 21.813578 ms GeoCSV-to-Trace maximum.
ObsPy's reader joins records within half an interval; an assembled regular grid
does not prove identical raw record timing. The legacy LOG/MER correction's
contribution is not established by these comparisons.
