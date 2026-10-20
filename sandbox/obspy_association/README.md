# EarthScope waveform retrieval and inspection sandbox

This directory holds exploratory ObsPy scripts for investigating returned
waveform timing, quality, segmentation, and coverage. The association
implementation is part of the package; use the public
[association tutorial](../../docs/tutorials/ASSOCIATE.md) or its
[notebook](../../docs/tutorials/ASSOCIATE.ipynb) for `geocsv.associate`.

Run from the repository root with the package and optional ObsPy dependency:

```bash
.venv/bin/python -m pip install -e '.[obspy]'
```

## Short requests

```bash
.venv/bin/python sandbox/obspy_association/retrieve_event_examples.py --raw
```

This queries EarthScope for P0006 source records 98 (DET Q, 4832 samples) and
100 (REQ D, 4800 samples) from the bundled GeoCSV fixture. It requests complete
SNCL `MH.P0006.00.BDH` with a one-second margin around the first and last
sample. This is a retrieval margin, not an association tolerance. Add `--plot`
for seismograms; `--raw` makes a second request saved before client-side
parsing/trimming. Quality is not filtered, and no association is performed.
The fixture start times are already corrected; do not apply TimeCorrection
again.

## Longer requests

```bash
.venv/bin/python sandbox/obspy_association/retrieve_long_window.py
```

The default spans 30 days. For an explicit one-year probe:

```bash
.venv/bin/python sandbox/obspy_association/retrieve_long_window.py \
    --start 2018-06-29T00:00:00Z --end 2019-06-29T00:00:00Z
```

Both retrieval scripts contact the network. Saved responses go under ignored
`downloads/`. Preserve responses and logs used as experimental evidence;
they are local artifacts, not portable test fixtures. ObsPy's normal client
path trims to request bounds, and reading MiniSEED assembles records into
traces even without an explicit merge. Returned traces alone do not establish
original acquisition boundaries or retrieval completeness.

## Inspect a local MiniSEED file

```bash
.venv/bin/python sandbox/obspy_association/view_mseed.py \
    data/fixtures/association/452.020-P-0030/0002_20210527-14h28m09s/20210527T154441.0030_60AFC696.MER.DET.WLT2.mseed
```

This prints trace headers and quality flags and opens ObsPy's waveform plot.

## Evidence and maintained tools

- [Dated retrieval observations](../../docs/OBSPY_RETRIEVAL_OBSERVATIONS.md).
- [MERMAID data-quality reference](../../docs/MERMAID_DATA_QUALITY.md).
- [Open association questions](../../docs/OPEN_QUESTIONS.md#association-scientific-questions)
  and the [merged-trace policy](../../docs/OBSPY_MERGED_TRACES.md).
- [Fixture maintenance scripts](../../scripts/fixtures/README.md), now under
  `scripts/fixtures/`, and the
  [fixture inventory](../../data/fixtures/association/README.md).

Generated `__pycache__/` content is disposable and remains ignored.
