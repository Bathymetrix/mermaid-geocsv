# P0006 EarthScope tutorial fixtures

Three original DET MiniSEED/SAC pairs were copied verbatim on 2026-10-27
from the authorized read-only `$MERMAID/waveforms/mseed/` and
`$MERMAID/waveforms/sac/` references. Their symlinks resolve into the protected
`$MERMAID/processed/452.020-P-06/` tree. No source files or symlinks were modified.

| Complete GeoCSV record index | Original basename | Samples |
| ---: | --- | ---: |
| 98 | `20180629T170731.06_5B3F1904.MER.DET.WLT5` | 4,832 |
| 169 | `20180712T065158.06_5B4748AE.MER.DET.WLT5` | 4,448 |
| 239 | `20180715T224815.06_5B4C1D4F.MER.DET.WLT5` | 5,440 |

The first detection is the short DET example in the
[retrieval sandbox](../../../../sandbox/obspy_association/README.md). The other
two are isolated detections in the same complete history. The sandbox's REQ
record 100 is excluded: its live response start differs from that source row,
and rows 100 and 101 are ambiguous containing anchors in the current history.

`earthscope/record_*.mseed` stores the unmodified public service responses
saved by ObsPy `Client.get_waveforms(filename=...)`. Each request uses complete
SNCL `MH.P0006.00.BDH`, one-second margins, and no quality filter. The manifest
records request URLs/parameters, retrieval times based on file modification
times immediately after saving, response hashes, and parsed waveform headers.
The request time bounds use the millisecond GeoCSV start and declared rate;
no correction is reapplied, and no response is trimmed or rewritten.

Responses are not byte-identical to original MiniSEED files: saved responses
carry quality M and originals carry Q. Their identity, rate, count, and samples
agree exactly. Download-minus-original start differences are −6 µs, 0 µs, and
−1 µs for records 98, 169, and 239 respectively. The manifest records them in
integer nanoseconds, and the tutorial checks them explicitly without changing
any timing. Their cause is not established. All three associate uniquely as
`single_segment` using the complete shared [P0006 GeoCSV](../README.md). The manifest retains that
file's path/hash and the pinned testing snapshot used by the tutorial; it does
not duplicate the complete history or create a subset.

SAC files are independent output comparison references, never association
inputs. Their samples agree with the downloaded counts at SAC float32
precision. The [EarthScope tutorial](../../../../docs/tutorials/EARTHSCOPE.md)
compares identity, absolute start, count, interval, samples, and stla/stlo/stel/stdp
after export. It documents units, precision, and the limited header coverage.
Tests replay these raw responses offline; later live downloads need not have
identical bytes. Do not regenerate these files during tests.

[`manifest.json`](manifest.json) records source/resolved paths, byte counts,
SHA-256 hashes, complete-history indices and physical lines, and ObsPy versions.
The inspected source checkout and installed runtime are recorded separately.
