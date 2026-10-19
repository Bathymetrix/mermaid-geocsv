# MERMAID waveform data quality and stream types

Working association note, transcribed from material supplied by the user on
2026-10-13. This is planning documentation, not an independently verified
instrument specification or publication-ready text. Resolve the marked
citations and instrument-generation details before external use.

## Why the streams have different flags

Acoustic MERMAID instruments produce two principal waveform streams:

- **DET**: data detected by the onboard algorithm. Automaid assigns quality
  `Q` to DET regardless of sampling frequency; the local fixtures include a
  DET.WLT2 product at about 2.5 Hz.
- **REQ**: data manually requested from the onboard circular buffer. These
  requests may use the listed sampling frequencies and Automaid assigns them
  quality `D`.

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

## Nominal waveform identity and quality assignment

The user-supplied table gives this nominal sampling/channel/location mapping.
Quality is assigned by stream type, not sampling frequency: DET is `Q` and REQ
is `D` at any frequency where that stream occurs. The quality column below
states the assignment rule for a stream at that configuration; it does not
assert that every stream/configuration combination is present in the dataset.

| Nominal sample rate (Hz) | Channel | Location | Processed event qualities |
| ---: | --- | --- | --- |
| 20 | BDH | 00 | DET `Q`; REQ `D` |
| 40 | BDH | 10 | DET `Q`; REQ `D` for RAW event products |
| 10 | BDH | 20 | DET `Q`; REQ `D` |
| 5 | MDH | 00 | DET `Q`; REQ `D` |
| 2.5 | MDH | 10 | DET `Q`; REQ `D` |
| 1.25 | MDH | 20 | DET `Q`; REQ `D` |
| 40* | BDH | 20 | R |

`*` The supplied note reports raw-buffer data averaging an unresolved `XX`
Hz for P0006 and 40.01406 Hz for P0023, citing Pipatprathanporn & Simon
(2022). The P0006 rate and the cited source still need verification.

## Automaid waveform filenames and sampling SNCL

Automaid's current `events.py:set_processed_file_name()` constructs the
waveform filename suffix as:

```text
.MER.[DET|REQ].[WLT1|WLT2|WLT3|WLT4|WLT5|RAW].mseed
```

Here `DET` versus `REQ` is the first slot; `WLT1` through `WLT5` or `RAW` is
the second. For example:

```text
20210528T053250.0030_60B08BB3.MER.DET.WLT2.sac
20250513T225306.0119_6926C549.MER.REQ.RAW.mseed
```

The first example has `.sac` rather than `.mseed`, showing that the same
product stem can be written in either waveform format. `STD` is a separate
Stanford-event product branch, outside the DET/REQ mapping below.

For the acoustic DET/REQ branch, the filename code has these combinations:

| Stream slot | Processing slot(s) | Output file ending |
| --- | --- | --- |
| `DET` | `WLT1`–`WLT5` (code-permitted; rebuilt inventory contains WLT2 and WLT5) | `.mseed` or `.sac` |
| `REQ` (manually requested) | `WLT1`, `WLT2`, `WLT3`, `WLT4`, `WLT5` | `.mseed` or `.sac` |
| `DET` or `REQ` | `RAW` (code-generated; DET.RAW not locally observed) | `.mseed` or `.sac` |

The code selects DET versus REQ from the event trigger classification and
selects RAW versus WLT from the scale field. It does not restrict DET to a
particular WLT scale. The rebuilt processed inventory contains DET.WLT2 and
DET.WLT5. DET.WLT1, DET.WLT3, DET.WLT4, and DET.RAW are code-permitted but
absent from that inventory. REQ.WLT3, REQ.WLT4, REQ.WLT5, and REQ.RAW are
present; REQ.WLT1 and REQ.WLT2 are absent. See the
[rebuilt fixture audit](../data/fixtures/association/README.md). The local
`.REQ.RAW` examples are requested event products, not the continuous
raw-buffer stream. Preliminary-position products may insert `.prelim` before
`.mseed` or `.sac`.

Automaid's `find_measured_sampling_frequency()` and `utils.location()` map
the transmitted WLT scale count to nominal rate, channel, and location as
follows. The measured source rate can make the resulting ObsPy rate slightly
different from the nominal rate.

| Second filename slot | Nominal sample rate (Hz) | Channel | Location | Writer quality assignment |
| --- | ---: | --- | --- | --- |
| `WLT1` | 1.25 | MDH | 20 | DET `Q`; REQ `D` |
| `WLT2` | 2.5 | MDH | 10 in current helper; 01 in older example | DET `Q`; REQ `D`; DET confirmed locally |
| `WLT3` | 5 | MDH | 00 | DET `Q`; REQ `D` |
| `WLT4` | 10 | BDH | 20 | DET `Q`; REQ `D` |
| `WLT5` | 20 | BDH | 00 | DET `Q`; REQ `D` |
| `RAW` event product (`STAGES=-1`) | about 40 | BDH | 10 in current helper; older/local event files also show 00 or 01 | DET `Q`; REQ `D` |
| physically recovered continuous buffer | about 40 | BDH | 20 | R in supplied table and local P0023 files |

The newly added fixture `20210527T154441.0030_60AFC696.MER.DET.WLT2.mseed`
reads as `MH.P0030.10.MDH`, 2.5009128631 Hz, 584 samples, with MiniSEED quality
`Q`; its paired SAC file has `kuser1=DET.WLT2`. This confirms a non-20-Hz DET
product using the current helper's WLT2 location `10`. Before the rebuild, a separate older
v4.5.1 product, `20210528T053250.0030_60B08BB3.MER.DET.WLT2.mseed`, has
location `01`, showing a historical location-code difference, not a reason
to limit DET to WLT5. The rebuilt v4.5.11 copy of this same basename now
uses location `10` and is included in the new paired fixtures. The source MER header for the newly identified DET.WLT2
record should be checked to confirm its event classification and scale. Keep
the quality rule independent of rate: detected products are Q; requested
products are D. Association preserves the actual downloaded SNCL.

The apparent raw-buffer location conflict is a terminology collision. The
`.REQ.RAW` filename suffix denotes a requested event whose `STAGES=-1` data
were kept at the instrument's roughly 40 Hz rate; it does not denote the
separately recovered continuous buffer stream. Current `utils.location()` maps
that event product to location `10`, although local historical `.REQ.RAW`
MiniSEED also includes `00` and `01` locations. The continuous recovered buffer
is the table's `R` stream at location `20`: local P0023 files under
`buffers/P0023/mseed/` read as `MH.P0023.20.BDH`, 40.01405975 Hz, quality `R`.
These are distinct products and should retain distinct identity/lineage.
Do not use the filename token `RAW` alone to infer quality `R` or location 20.

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
and the [dated retrieval observations](OBSPY_RETRIEVAL_OBSERVATIONS.md).

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
