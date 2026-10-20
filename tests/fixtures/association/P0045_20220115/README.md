# P0045 real merged waveform example, 2022-01-15

Two original WLT5 request segments are copied byte-for-byte from the authorized
read-only `$MERMAID/waveforms/mseed/` references. Their paired SAC files are
copied from `$MERMAID/waveforms/sac/` as independent comparison references;
they are not association inputs. The symlinks resolve into
`$MERMAID/processed/452.020-P-0045/0210_20220112-22h43m00s/`.
No source files or symlinks were modified. No merged waveform is stored.

`manifest.json` records source and resolved paths, byte counts, SHA-256 hashes,
original waveform headers, and the expected merge. Its day inventory contains
all nine P0045 MiniSEED files whose filenames begin `20220115` in the local
waveform reference. The selected files are:

- `20220115T043358.0045_6238169F.MER.REQ.WLT5.mseed` (9,696 samples).
- `20220115T044202.0045_62A7D1AC.MER.REQ.WLT5.mseed` (36,000 samples).

Both have SNCL `MH.P0045.00.BDH` and measured sample rate
20.006973266601562 Hz. Of the same-SNCL/same-rate continuous spans starting
that UTC day, their union is the longest. They overlap; the next request at
05:12:02.912869 UTC has approximately 0.624 seconds missing after the expected
next sample of the second selected segment. Later overlapping request/detection
segments span only about 31 minutes 53 seconds. Earlier RAW data has location
`10` and a different sample rate. Do not bridge gaps, relabel locations, or
resample simply to obtain a longer example.

The association source is the single shared
[`P0045.geocsv`](../../geocsv/P0045.geocsv) fixture. Rows 101433 and 101434 are
zero-based **data-record indices in that full file**, not subset indices.
Its source timestamp, rate, count, and position values are never edited.

The [association tutorial](../../../../docs/tutorials/ASSOCIATE.md) merges the
loaded originals with ObsPy `method=1`, `interpolation_samples=0`, and
`misalignment_threshold=0`. The later trace supplies overlap values. Its start
falls about 24.8 ms off the first trace's grid and is placed at integer sample
9683. The resulting 45,683 samples contain no masked gap and run from
04:33:58.910159 to approximately 05:12:02.214055 UTC (38 minutes 3.304 seconds
between first and last samples). This timing placement is explicit and is not
a statement that the original grids were identical.

Association fails with the earlier tutorial's 1 ms tolerance, including with
`allow_first_segment=True`. It succeeds with explicit `time_tolerance=0.025` and
`allow_first_segment=True`, uniquely placing the source ranges `[0, 9696)` and
`[9683, 45683)`. It attaches row 101433 and the `first_segment` label without
changing the source row or merged samples. The 25 ms tolerance is an example
policy close to half a sample; it does not establish clock accuracy. No
acquisition lineage is inferred from the overlap.

ObsPy behavior and merge tests were inspected read-only at checkout commit
`50033e1daf95233cd4f30e95a49c37fd50be2ccd`, including Stream merging, overlap
tests, contribution instructions, and coding style. The repository `.venv`
separately runs installed ObsPy 1.5.1. The manifest records that distinction.
