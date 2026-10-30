> **AI-written documentation — non-authoritative.** Verify scientific and format details against the linked sources before relying on them.

# GeoCSV migration decisions

Paired design note: [automaid](../../automaid/docs/geocsv-method-identifiers.md). Keep both notes synchronized. Execution plan: [four-repository migration](../../automaid/docs/geocsv-migration-plan.md).

Status: schema 1.0.0 implemented locally on 2026-10-29 by automaid v4.6.0
and mermaid-geocsv 0.27.0. Current producer source is v4.6.2; v4.6.1 added
MiniSEED correction rounding and v4.6.2 added per-record read-back validation.
Software release and compatible hosted data remain separate. Legacy MERMAID GeoCSV versions are unsupported: no legacy
reader/writer path, aliases or automatic fallback. The reader supports this
controlled MERMAID profile, not arbitrary GeoCSV dialects or schemas.

The complete [schema 1.0.0 contract](format-spec.md) specifies the header,
field dictionary, domains, row matrix and complete synthetic example. It is
the payload specification to review before implementation; this note records
the decisions and their source evidence.

The required first header line is exactly:

```text
# MERMAID GeoCSV schema: 1.0.0
```

Emit it once, without a trailing period, alongside the existing GeoCSV metadata.
The reader requires the supported schema declaration and rejects missing or
unsupported revisions clearly. Preserve it in parsed and association provenance.
Schema versioning is independent of producer/package versions and release IDs;
this does not authorize a software 1.0.0 release or require legacy support.

## File structure

Each file contains one MERMAID instrument and one CSV table. Use UTF-8 encoding,
a comma delimiter, LF writer line endings and standard double-quote CSV
escaping. The table has exactly these 16 columns in this fixed order:

```csv
MethodIdentifier,Time,Network,Station,Location,Channel,DataQuality,Latitude,Longitude,Elevation,WaterPressure,InstrumentDescription,SampleRate,SampleCount,ClockOffset,TimeCorrectionApplied
```

Require schema, dataset, created, delimiter, lineterminator, field_type and
field_unit declarations exactly once before the column header. Description and
attribution are optional descriptive text. Preserve other descriptive comments;
reject repeated required declarations and field_missing. The complete contract
defines the remaining syntax. There is no generic GeoCSV or multiple-table support.

## Agreed names

`MethodIdentifier` has exactly three nonempty colon-separated components:
`Method:Subject:Source`.

```text
Measurement:Position:<GPS-sensor>
Measurement:Pressure-Absolute:<pressure-sensor>
Derivation:Recording:automaid-<version>
Interpolation:Crossing-Descent:automaid-<version>
Interpolation:Crossing-Ascent:automaid-<version>
```

The source identifies the actual sensor or producer version. Parse colons first;
hyphens within source names remain part of that source. Both crossing subjects
may be grouped as `Crossing`. No direction column is added.

Rename `StartTime` to `Time`. `Recording` describes an original waveform segment,
including its corrected first-sample epoch, station position, sample rate and
count. `Position` is geographic station position; `Location` remains the SEED
location code. Rename `TimeDelay` to `ClockOffset` and `TimeCorrection` to
`TimeCorrectionApplied`, with their existing values, signs and second units
unchanged. Other column names and units remain unchanged unless separately
specified. Absolute-pressure labeling does not introduce atmospheric correction.

`InstrumentDescription` uses `MERMAID_<model>`, for example
`MERMAID_452.020`, replacing `MERMAIDHydrophone(452.020)`.
Preserve the actual source model code; do not hard-code 452.020 for other
models or supply a default when the model is absent. This describes the
MERMAID instrument model; the MethodIdentifier source identifies the specific
GPS sensor, pressure sensor or processing software.

In the writer, **Recording rows only** emit the literal Elevation cell `0`, with
`float` in field_type and `meters` in field_unit, explicitly
representing the adopted sea-level reference rather than the submerged sensor's
physical elevation. Other row kinds keep Elevation absent. The reader preserves
both the explicit zero and absence; it never supplies a default. Association's
approved elevation projections use the Recording source value instead of
inventing zero. Remove the existing hard-coded zero for SAC `stel` and coordinate
elevation; missing required source Elevation raises. This replaces the current
missing Recording Elevation, not the writer's scientific depth calculation.

Repository-wide rule: never substitute defaults for missing, unknown, invalid
or unavailable source metadata in parsing, association, projections or
provenance. Optional values remain missing; required values raise. Preserve
explicit source values without silent repair or filling from another record.

## Row requirements

`MethodIdentifier`, `Time`, `Network`, `Station` and `InstrumentDescription`
are required on every row. R means required, O optional, and a dash means the
cell must be empty. Required missing values and populated inapplicable fields
raise; nothing is defaulted.

| Field | Position | Pressure-Absolute | Recording | Crossing (both directions) |
| --- | --- | --- | --- | --- |
| `Latitude`, `Longitude` | R | — | R | R |
| `Location`, `Channel`, `DataQuality` | — | — | R | — |
| `Elevation` | — | — | R: zero metres | — |
| `WaterPressure` | — | R | R for Q; O for D | R |
| `SampleRate`, `SampleCount` | — | — | R | — |
| `ClockOffset` | O | — | — | — |
| `TimeCorrectionApplied` | — | — | R | — |

Location is required **only on Recording rows** and must be empty on all other
row kinds. Two literal ASCII spaces are a present, known blank code; an empty
cell is unknown and does not satisfy the Recording requirement. The pressure
exception uses the source row's Q/DET or D/REQ quality and preserves the
existing rule; never borrow a missing pressure from another row.

Pressure-Absolute sensor measurements accept finite signed readings, including
negative gauge error, without clamping, replacement or offset correction.
Present numbers are finite; latitude is within [-90, 90], longitude within
[-180, 180], Recording/crossing pressure nonnegative, sample rate positive and sample count a
positive integer. Recording quality is Q or D. Preserve identity strings
without new alphabet/length restrictions or rate-derived codes. Network,
Station and InstrumentDescription each agree across all rows of a file.

## Clock definitions and source mappings

Reserve clock "drift" for the manual's DRIFT/GPSACK definition:

```text
drift = gps_time - mermaid_time
ClockOffset = mermaid_time - gps_time = -drift
```

`ClockOffset` is the observed-minus-reference time difference at a GPS fix,
in seconds: positive means the instrument clock is ahead. Its current source
is `gps.mseed_time_delay`, which is already `-gps.clockdrift`. The proposed
`ClockDrift` column is withdrawn; no GPS-column sign reversal is selected.

`TimeCorrectionApplied` is `event.mseed_time_correction`, the clock correction
already added to the uncorrected original recording start, in seconds. It is a
signed numeric amount, not the MiniSEED boolean applied flag:

```text
Time = uncorrected_starttime + TimeCorrectionApplied
TimeCorrectionApplied = -estimated_ClockOffset_at_recording_time
```

Timing-field requirements:

- Position rows: `ClockOffset` is optional. Unknown offset stays absent;
  `TimeCorrectionApplied` is not applicable and remains absent.
- Recording rows: `TimeCorrectionApplied` is required. Missing correction raises;
  `ClockOffset` is not applicable and remains absent.
- Pressure and crossing rows: both timing-correction fields remain absent.

Do not move the GPS-fix offset into a Recording row, infer a recording correction
from another row, or substitute zero for an absent value.

Positive correction moves the recording timestamp later; negative moves it
earlier. The correction uses the drift sign, opposite to the offset evaluated
at that same epoch. GPS-fix offsets and recording corrections refer to different
epochs and need not have equal magnitudes. Never apply the correction again.

The current source computes `clockdrift_correction = ascent.clockdrift * pct`,
then sets `mseed_time_correction = clockdrift_correction` and adds it to the
uncorrected start. These are definitions of existing behavior, not changes to
clock processing. The source mapping was checked at automaid commit
`3d183c1636f92c7fe8619b02adc5892500dbd208`: 24 extracted-source sign/interpolation
assertions passed, and all 3,266 P0006 GPS GeoCSV rows matched the negative of
the raw GPS export's `gps_time-mer_time` value at printed precision.

The GeoCSV migration retained MiniSEED fixed-header truncation toward zero.
A separately authorized follow-up in automaid v4.6.1 rounds the decimal spelling
of the supplied correction to the nearest 0.0001-second tick, with exact ties
to even. Non-finite values and rounded ticks outside the signed 32-bit range
raise before any file bytes change. In the normal write path, timestamps are
already corrected and the applied bit prevents reapplication. The stored field
is correction history; its quantization does not round waveform timestamps or
the GeoCSV value. The follow-up did not rewrite existing processed waveforms or migration
candidates; their original correction fields retained the earlier serialization.
The canonical tree was subsequently regenerated with v4.6.2 on 2026-10-30;
historical candidates remain unchanged.

Automaid v4.6.2 independently reads back every record after writing and requires
the applied bit and expected rounded tick count, including zero. A mismatch
raises with record and byte-offset context; writes are not rolled back. This
adds verification without changing the clock model, waveform timestamps or
GeoCSV values. The big-endian and uniform-record limitations remain; see the
[clock matrix](../../automaid/docs/clock-timing-matrix.md).

The separate record-offset regression was fixed in automaid commit `c16bf70`
by restoring advancement to the next record. Verification of the current helper
with two synthetic seven-record files confirmed both correction signs on every
record, with applied bits set and samples/start/end unchanged (12 assertions).
This issue is resolved; it is not pending migration work.

## Time and scientific meaning

All timestamp strings emitted by the GeoCSV writer, including `Time` and
`#created`, use UTC with exactly six fractional digits and `Z`. Time offsets and
corrections retain six decimal places in seconds. Source epochs with more than
six fractional digits round to the nearest microsecond, with exact ties to
even and normal carry. This changes serialization only, not clock processing
or MiniSEED header handling. Displayed digits make no
claim about clock accuracy, measurement precision, or uncertainty.

Recording times retain the existing clock-drift correction. GPS, pressure and
crossing times do not acquire that recording correction. Preserve the existing
crossing fallback: the GPS helper can retain an anchor position and its epoch
instead of estimating unstable velocity from closely spaced fixes. This
intentional stability behavior is accepted and documented; it is not a
migration defect to fix.

The mixed layer is the upper approximately 50 m in this model. Descent exits
its base; ascent enters it. The boundary is configured, not measured from a
temperature profile. Faster horizontal drift there is empirical, approximately
an order of magnitude, with no imposed velocity ratio. Legacy code's deeper
"mixed layer" means the deep layer; correction outside the allowed writer is
deferred. See [Nolet et al. (2024), pp. 2369, 2372](https://doi.org/10.1785/0220230377).

Geographic metadata describe the station, not earthquake parameters. Retain the
approximate `WaterPressure / 100` station-depth mapping, existing tolerances,
and optional SAC `stla/stlo/stel/stdp` projections; never add `ev*` projections.
Crossing WaterPressure retains configured mixed-layer depth multiplied by 100;
it is a boundary proxy, distinct from an absolute-pressure sensor measurement.

## Missing values

Fields that do not apply to the row kind must be empty CSV cells. Unexpected
populated inapplicable fields raise; do not ignore or silently discard them.
This is distinct from optional applicable fields, which may be absent.

- An empty decoded CSV field is absent; required/applicable fields follow the
  row schema. Missing required values raise. Emit absence as an unquoted empty
  field; quoted empty fields also decode as absent.
- Nonempty strings such as `nan`, `NA`, `NULL` and `NaT` are literal values.
  Nonempty invalid numbers or timestamps raise; numeric values must be finite.
- Whitespace-only values are invalid except exactly two ASCII spaces in
  `Location`: `6,"  ",9` means a known blank SEED location code; `6,,9` is absent.
  The DataFrame and raw association source retain both literal spaces. Never
  trim, normalize, or default this source value. Association can compare that
  defined blank code with ObsPy's `""` without rewriting either identity or the
  source cell; absent Location remains unknown and never becomes a blank code.

References: [CSV field syntax](https://www.rfc-editor.org/rfc/rfc4180.html),
[blank SEED identifiers](https://www.fdsn.org/media/message_attachments/2015/07/20/FDSN-WS-Specifications-1.1.pdf).
Blank Location does not universally mean "primary instrument".

## Scope and remaining decisions

The names, file/header contract, field domains, row requirements, six-digit
rounding, missingness, literal Recording Elevation `0` and intentional fallback
are selected. The complete specification and worked example are now recorded
for final review in the linked contract. No naming, sign or row-applicability
decision remains open; the separately requested local implementation follows that contract. No direction column or generic compatibility layer is added.

The separately authorized local implementation is limited in automaid to
`scripts/geocsv.py` plus the version returned by `scripts/setup.py`. Other
producer algorithms, callers, utilities and configuration remain unchanged.
The existing writer pressure sanity assertion now uses exact numeric equality
rather than object identity, allowing saved cycles to be verified without
recomputing their scientific values. No tolerance is added.

Historical source data, published bytes, release identities and evidence remain
unchanged. Six-digit formatting applies to new output; fetch must preserve any
existing literal release ID and all its fractional digits. Protected source archives and historical evidence remain read-only. No uploads,
pointer changes, deployment, commits, tags or releases are authorized.

Source references: [writer](../../automaid/scripts/geocsv.py),
[position helper](../../automaid/scripts/gps.py),
[cycle calculation](../../automaid/scripts/cycles.py).
Timing and fallback behavior were inspected at automaid revisions
`678ea8f06e445d3da1864236f29a2ebee87ee659` and
`f0c97e98629967de8161f744e9fbbc4474030b9b`; inspect current source before implementation.
