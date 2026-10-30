# SAC station headers and ObsPy writing

Use `associate(..., create_sac_header=True)` on the final MiniSEED-derived
waveform, then ObsPy `Trace.write` or `Stream.write`. The [SAC tutorial](../tutorials/write-sac.md)
provides runnable examples. Matching, fresh destinations, and the in-memory
report are defined in the [association reference](obspy-association.md).

## Geographic mapping

Association constructs ObsPy's fresh SAC baseline and adds only these four
GeoCSV projections. `stats.sac` must be absent, including an empty container.
All requested projections validate before any trace is modified.

| SAC header | Source and units |
| --- | --- |
| `stla` | Matched `Latitude` in declared `degrees_north`, within [-90, 90]. |
| `stlo` | Matched `Longitude` in declared `degrees_east`, within [-180, 180]. |
| `stel` | Explicit matched Recording `Elevation` in `meters`, required to be zero; missing raises. |
| `stdp` | Nonnegative `WaterPressure` in declared `mbar`, divided by 100; approximate MERMAID station depth in metres, positive down. |

The pressure conversion follows automaid's approximation: 100 mbar = 1 dbar
corresponds to approximately one metre of MERMAID receiver (station) depth.
Thus `stdp = WaterPressure / 100` describes the submerged station, in metres
positive downward. It uses no density model, latitude correction, or additional
atmospheric-pressure correction, and does not reconstruct a depth trajectory.
This package does not supply earthquake-source metadata or populate `evla`,
`evlo`, `evel`, or `evdp`. The [coordinate convention](obspy-association.md#adopted-sea-level-reference)
defines the vertical-reference limits.

Missing pressure is accepted only for source `DataQuality="D"` (REQ).
`stdp` is then SAC undefined: -12345 in the stored numeric header, `None`
through `SACTrace`, and absent from `stats.sac` when read as an ObsPy Trace.
Missing DET pressure raises. Present pressure must have valid mbar units even
for REQ. Downloaded MiniSEED quality never supplies this exception or a depth.
Other rows and independent SAC files never fill missing values.

For `anchor_segment`, the anchor's four geographic values apply to the entire
window under the MERMAID negligible-drift convention. Source fields retain
their original meanings. Subsequent trimming, merging, or resampling does not
refresh the headers or revalidate association.

## Writing and precision

Keep ObsPy's default `keep_sac_header=True`; False discards these projections.
ObsPy supplies native identity, timing, sampling, and default SAC headers.
Conversion preserves native Stats, calibration, samples, and processing history.
It does not remove response or convert raw counts to pressure. ObsPy's mapping
of `stats.calib` to `scale` is not a GeoCSV calibration promise.

Binary SAC stores samples and floating headers as float32. Large integer
samples can lose precision, and UTC nanoseconds need not survive. The inspected
ObsPy writer emits SAC version 6; version 7's double-precision footer does not
make that write path lossless. Ordinary strings occupy eight-byte slots
(event name uses two); arbitrary dictionary keys do not become file headers.
Full GeoCSV rows and provenance are not serialized into SAC.

A SAC file contains one trace. ObsPy writes separate numbered files for a
multi-trace Stream and overwrites existing filenames. An exclusively opened
binary file (`open(..., "xb")`) can enforce overwrite refusal. An I/O failure
can leave partial files; batch writing is not transactional. The package
performs no export-time validation. The publisher owns
[final waveform and SAC verification](../../mermaid-publisher/docs/geocsv/sac-verification.md).

## Independent comparison references

Paired automaid SAC fixtures are read separately after association. They never
supply matching hints, defaults, or pressure. The portable tests compare:

- `stla` and `stlo`: half a six-decimal GeoCSV unit plus one float32 spacing
  at the reference coordinate.
- `stel` and `stdp`: the mapped values at float32 storage precision, preserving
  undefined REQ depth.
- Samples: equality with the native samples converted to float32; independent
  original-pair comparisons also check reference samples.
- Native identity, count, interval, and absolute first-sample time. The
  original-pair tests use a 1 microsecond start-time comparison allowance;
  this is fixture evidence, not a universal SAC accuracy guarantee.

These checks do not promise whole-header or byte-for-byte equivalence. SAC
references can contain instrument, orientation, trigger, or calibration fields
without a GeoCSV mapping. Compare absolute sample times rather than requiring
the same split between reference-time fields and `b`.

See [fixture provenance](../data/fixtures/association/README.md) for sampled
product coverage and [open questions](open-questions.md#deferred-workflows-and-mappings)
for deferred mappings. The read-only source reference is ObsPy commit
`50033e1daf95233cd4f30e95a49c37fd50be2ccd`, especially
[conversion](https://github.com/obspy/obspy/blob/50033e1daf95233cd4f30e95a49c37fd50be2ccd/obspy/io/sac/util.py)
and [header definitions](https://github.com/obspy/obspy/blob/50033e1daf95233cd4f30e95a49c37fd50be2ccd/obspy/io/sac/header.py).
This is distinct from the installed ObsPy version used for each test run.
