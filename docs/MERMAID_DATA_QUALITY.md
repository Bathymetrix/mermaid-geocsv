# MERMAID product identity and data quality

Automaid assigns MiniSEED quality `Q` to detected (DET) event products and `D`
to requested (REQ) event products, independently of sampling rate. A detected
waveform need not be at 20 Hz. The [fixture inventory](../data/fixtures/association/README.md)
records observed product groups, exact headers, and the sampled source audit.
This document describes producer behavior and preserved examples, not a
complete instrument-generation specification.

## Product names and nominal configurations

Automaid's `scripts/events.py:set_processed_file_name()` uses the acoustic
product suffix `.MER.[DET|REQ].[WLT1|WLT2|WLT3|WLT4|WLT5|RAW]`, followed by
`.mseed` or `.sac`. DET/REQ comes from trigger classification; WLT/RAW comes
from the scale field. `STD` is a separate Stanford-event branch. Preliminary
products may add `.prelim` before the waveform extension.

The inspected producer helpers `find_measured_sampling_frequency()` and
`utils.location()` define these nominal configurations. Source reference:
automaid commit `678ea8f06e445d3da1864236f29a2ebee87ee659`. Actual measured
rates and historical identity codes must be preserved rather than replaced
by this table.

| Processing slot | Nominal rate (Hz) | Channel | Current helper location | Event quality |
| --- | ---: | --- | --- | --- |
| WLT1 | 1.25 | MDH | 20 | DET Q / REQ D |
| WLT2 | 2.5 | MDH | 10 | DET Q / REQ D |
| WLT3 | 5 | MDH | 00 | DET Q / REQ D |
| WLT4 | 10 | BDH | 20 | DET Q / REQ D |
| WLT5 | 20 | BDH | 00 | DET Q / REQ D |
| RAW event (`STAGES=-1`) | about 40 | BDH | 10 | DET Q / REQ D |

Not every code-permitted combination occurs in the sampled inventory. Older
WLT2 products include location `01`; the current paired DET.WLT2 fixtures use
`10`. Historical requested RAW event files also include locations `00` and
`01`. These are source identities, not aliases to normalize.

A `.REQ.RAW` event is distinct from the separately recovered continuous
circular-buffer stream. The supplied buffer mapping uses quality R and
location 20; local P0023 buffer examples read as `MH.P0023.20.BDH`,
40.01405975 Hz, R. The filename token RAW alone establishes neither quality R
nor location 20. No continuous-buffer products are included in the paired
association fixture inventory.

## Association and archive quality

Keep `trace.stats.geocsv.DataQuality` and
`trace.stats.mseed.dataquality` as independent evidence. Association neither
rewrites them nor requires equality. Complete SNCL, time, count, rate, and
coverage follow the [association reference](OBSPY_ASSOCIATION.md).

Preserved [EarthScope responses](../data/fixtures/P0006/waveforms/README.md)
have quality M while their original DET files have Q. M alone does not prove
that a waveform combines acquisitions or identify overlap precedence.
Requested products can also return M. Any proposed quality-based matching or
lineage reconstruction needs independent source and archive evidence.
Instrument-generation timing claims, raw-buffer rates, and incomplete
citations remain [open questions](OPEN_QUESTIONS.md#instrument-and-product-evidence).
