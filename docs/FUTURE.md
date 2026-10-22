# Future workflows and deferred mappings

These are open extensions and decisions, not commitments to public APIs.
Implemented fetching, reading, association, and SAC export are documented in
the [tutorials](README.md#tutorials). Scientific uncertainties belong in
[open questions](OPEN_QUESTIONS.md).

## Write MERMAID GeoCSV

A possible writer would be informed by `automaid/scripts/geocsv.py`, but use
this package's data model and documented GeoCSV semantics rather than copy
incidental legacy structure. The current package does not author or rewrite
GeoCSV. Take up this scope/API decision only for a concrete workflow.

## Production collection hosting

Fetching is implemented, but production hosting and a default collection URL
remain undecided. Callers supply `base_url`; the
[fetch guide](tutorials/FETCH.md) records the provisional manifest protocol
and a standalone local test collection. Publication belongs to the collection
host, separate from the client package.

## Associate transformed archive waveforms

The current `allow_first_segment=True` option supports clipped and combined
MiniSEED windows using a unique source segment containing the waveform start
and complete source-grid coverage clipped to the window. Anchor geographic SAC
projection is supported under the user's MERMAID negligible-drift convention.
This does not reconstruct contributions or acquisition lineage. Resampled
waveforms and reconstruction of overlapping sample choices remain separate
scientific questions.

Decide supported transformations, required provenance, and failure behavior
before adding APIs or changing matching rules. Quality M alone cannot identify
a particular merge. Use the [scientific questions](OPEN_QUESTIONS.md#association-scientific-questions),
[dated retrieval evidence](OBSPY_RETRIEVAL_OBSERVATIONS.md), and
[exploratory sandbox](../sandbox/obspy_association/README.md) to guide that work.

## Project associated metadata into SAC headers

Geographic SAC export is implemented separately as `geocsv.write_sac(trace,
path)` for associated MiniSEED-derived waveforms with either label. Association has no SAC
option and does not mutate `stats.sac`; the unused `project_sac` placeholder
was removed on 2026-10-16. The [SAC writing guide](tutorials/WRITE_SAC.md) and
[notebook](tutorials/WRITE_SAC.ipynb) define current coverage, units, missing
pressure handling, and key-by-key comparison precision against independent
paired SAC references. Whole-header equivalence is not promised.

The implemented mapping is `stla`/`stlo` from attached receiver coordinates
in declared degrees, `stel=0` metres at the adopted sea-level reference, and
approximate `stdp=WaterPressure[mbar]/100` metres. Missing REQ pressure
(DataQuality D) leaves stdp undefined; missing DET pressure fails. SAC
references never supply source values. `anchor_segment` exports adopt all four
anchor geographic headers for the window; missing anchor pressure is not filled
from later rows. Further processed-waveform semantics remain undecided.

The pressure conversion follows automaid's 100 mbar per metre approximation,
not an exact oceanographic depth calculation. The user's cited MERMAID manual
(Réf: 452.000.852, Version 00) states 101 mbar per metre; that comparison was
supplied by the user and has not been independently verified. No additional
atmospheric-pressure or latitude-dependent correction is applied. GeoCSV mbar
must be divided by 100, whereas automaid event depth in LOG/MER is in dbar.
Depth is positive downward in `stdp`, not earthquake-source depth `evdp`.

Additional mappings remain deferred:

| Source or concern | Candidate and constraint |
| --- | --- |
| `TimeCorrection` | Automaid uses `user3` in seconds; retain as metadata only, never apply twice. |
| `TimeDelay` | Would require an agreed `userN` slot and units; not `b`, `o`, or a pick header. |
| `InstrumentDescription` | `kinst` can hold a short designation such as `452.020`, not the full description. |
| `MethodIdentifier` | No faithful dedicated SAC field; extracting a version loses part of the source value. |
| `DataQuality` | SAC `iqual` has different categories; no direct Q/D/M equivalent. |
| Orientation | No GeoCSV source or agreed projection; scalar-hydrophone zeros would be an explicit convention. North azimuth is 0, east 90; vertical has no meaningful horizontal projection. |
| Calibration | Outside repository scope: SAC waveform samples remain raw counts. GeoCSV supplies no counts-to-Pa factor; do not infer `scale` or change native `calib`. |

Automaid reserves `user0`–`user2` for SNR, criterion, and trigger index,
`user3` for clock correction, and its own `kuser0`–`kuser2` meanings. SNR,
criterion, trigger index, transform settings, and scale cannot be reconstructed
from current GeoCSV columns. Do not allocate their slots incidentally.

SAC float headers use float32 storage and ordinary strings have eight-byte
slots (event name uses two). Arbitrary dictionary keys are not new file
headers. Numeric and string nulls differ; preserve source missingness rather
than inserting numeric -12345 into string fields. The inspected ObsPy write
path emits version 6; the SAC version-7 double-precision footer does not make
that path lossless. Full descriptions, units, comments, and source/download
provenance remain in `stats.geocsv`. See the [SAC format](https://ds.iris.edu/files/sac-manual/manual/file_format.html)
and the inspected ObsPy [conversion](https://github.com/obspy/obspy/blob/50033e1daf95233cd4f30e95a49c37fd50be2ccd/obspy/io/sac/util.py)
and [header definitions](https://github.com/obspy/obspy/blob/50033e1daf95233cd4f30e95a49c37fd50be2ccd/obspy/io/sac/header.py),
at the revision recorded in the [Stats survey](OBSPY_STATS.md).

StationXML/Inventory conversion, station position epochs, live metadata
synchronization, and external association tables also need demonstrated
consumers and explicit authority/lifetime rules before becoming public APIs.
