# MERMAID waveform data quality and stream types

Working association note, transcribed from material supplied by the user on
2026-10-13. This is planning documentation, not an independently verified
instrument specification or publication-ready text. Resolve the marked
citations and instrument-generation details before external use.

## Why the streams have different flags

Acoustic MERMAID instruments produce two principal waveform streams:

- **DET**: data automatically detected by the onboard algorithm. The
  submitted MiniSEED data-quality indicator is `Q`.
- **REQ**: data manually requested from the onboard circular buffer. The
  submitted indicator is `D`.

The user's supplied rationale is that DET has more accurate timing, while
REQ can have greater timing and location uncertainty. Both streams receive
per-dive clock-drift corrections. Apart from artifacts from wavelet
decompression, overlapping DET and REQ waveforms should otherwise agree.

For older-generation instruments, including P0006-25 and possibly others,
some REQ data were reportedly time-shifted because waveform reconstruction
used a sampling rate from request time rather than acquisition time. The user
notes that this problem is fixed in the current generation, but verification
is pending. Do not generalize this behavior to every instrument generation.

A third stream, **raw buffer** data, is rarely recovered after physical
retrieval of the instrument and its circular-buffer SD card. The supplied
material says raw-buffer data receive no time correction and use quality
indicator `R`. To date, the user identifies P0006 and P0023 as providing this
stream.

## Nominal availability by waveform identity

The user-supplied table gives this nominal sampling/channel/location mapping:

| Nominal sample rate (Hz) | Channel | Location | Submitted qualities |
| ---: | --- | --- | --- |
| 20 | BDH | 00 | Q, D |
| 40 | BDH | 10 | D |
| 10 | BDH | 20 | D |
| 5 | MDH | 00 | D |
| 2.5 | MDH | 10 | D |
| 1.25 | MDH | 20 | D |
| 40* | BDH | 20 | R |

`*` The supplied note reports raw-buffer data averaging an unresolved `XX`
Hz for P0006 and 40.01406 Hz for P0023, citing Pipatprathanporn & Simon
(2022). The P0006 rate and the cited source still need verification.

The table's channel, location, and nominal rate describe the acquisition
configuration. The quality indicator labels the stream class (DET, REQ, or
raw buffer) and its associated timing/lineage. Preserve the quality indicator
as useful metadata, but do not treat it as the source of the sample rate or
make it a hard association filter when GeoCSV and downloaded data can carry
different indicators.

## Association handling

An association should retain both indicators independently:

- GeoCSV source value, for example `trace.stats.geocsv.DataQuality`.
- Downloaded MiniSEED header, for example `trace.stats.mseed.dataquality`.

Do not rewrite either value to make them agree. A mismatch is worth recording
and interpreting in context, but is not by itself a failed waveform
association. Use complete identity, time, sample rate, sample count, and
coverage evidence according to the separate matching policy. Quality may
explain stream lineage or overlap precedence, so keep it available to callers.

The user's automaid writer diff sets requested traces to `D` and detected
traces to `Q`. Our current P0006 EarthScope retrievals expose `M` for both.
EarthScope documents that its legacy archive process changed submitted
quality indicators to `M` when records may have been modified by facility
processing; old `M` records remain M. `M` does not prove a specific trace
was combined from multiple source files. See
[EarthScope archive changes](https://www.earthscope.org/news/miniseed-archiving-and-distribution-changes/)
and the [sandbox retrieval observations](OBSERVATIONS.md).

## Items to verify before treating this as a formal specification

- Confirm which MERMAID hardware generations have the REQ sampling-rate/time
  shift issue and whether it is fixed in the current generation.
- Confirm whether “more accurate timing” and “higher timing/location
  uncertainty” are the intended definitions for Q versus D; they appear
  directionally consistent but cite separate passages in the supplied text.
- Resolve the P0006 raw-buffer average sampling rate (`XX`) and verify the
  P0023 measured rate and source citation.
- Identify “(Ivy)” and complete/verify the Nolet et al. (2024) and
  Pipatprathanporn & Simon (2022) references.
- Confirm whether a raw-buffer rate varies by device or acquisition and how
  nominal rates are represented in the source data.
