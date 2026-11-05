# MERMAID GeoCSV schema 1.0.0-rc1

This is a controlled MERMAID GeoCSV profile, not a generic GeoCSV specification.
Only the controlled 1.0.0 schema family is supported. The writer emits
`1.0.0-rc1`; the testing workflow accepts `1.0.0`, prerelease identifiers such
as `1.0.0-rc2`, and optional build metadata. Other base versions, including
`1.0.01` and `1.0.1`, raise. The exact declared revision remains in provenance.
Final schema `1.0.0` is reserved for publication of the describing paper;
accepting that spelling during tests does not declare the schema released.
Schema versions are independent of software package and validation-report versions.

Automaid owns writing. `mermaid-geocsv` owns parsing, typed tables and station
association. The publisher's [publication/download contract](../../mermaid-publisher/docs/geocsv/contract.md)
owns manifests, release identities, immutable paths and publication gates.
The site serves exact bytes. See [producer source rules](../../automaid/docs/geocsv.md).

## File and CSV structure

Each file contains one MERMAID instrument and one table with the fixed 16
columns below. Network, Station and InstrumentDescription must each be constant
across its data rows. Do not infer these values from a filename. A table may be
recordless for local processing; the publisher excludes recordless sources.

Writers emit UTF-8 without a byte-order mark, comma delimiters and LF line
endings, including the final record terminator. Readers accept LF and CRLF
record terminators and require a terminated final record. The declared LF is
the canonical writer convention; parsing never rewrites the delivered bytes.
Blank records are invalid. There is no second dataset or second column header.

CSV uses ASCII double quotes. Quote a field containing a comma, double quote
or line break; represent a literal double quote inside it as `""`. Quoted
multiline fields remain one logical record. A quoted field starts with its
opening quote and ends at its closing quote; no padding is allowed outside
those quotes. A literal `#` inside a quoted field is data, including at the
start of a physical continuation line. These escaping rules follow
[RFC 4180, section 2](https://www.rfc-editor.org/rfc/rfc4180.html#section-2);
this profile separately specifies UTF-8, comment headers and writer LF endings.

Decoded string values retain their exact characters. Numeric and timestamp
cells must not contain surrounding whitespace. Never trim or normalize a
source value to repair it. A trailing empty sixteenth field requires its
preceding comma; a seventeenth field, even empty, is invalid.

The writer retains its existing chronological sorting and scientific
deduplication rules. The reader preserves all source rows in their original
order, including equal timestamps; it never sorts, merges or deduplicates them.
Association independently rejects ambiguous complete matching keys.

## Header contract

The first physical line declares the GeoCSV container, followed by the MERMAID
application schema. Canonical writer spelling is:

```text
# dataset: GeoCSV 2.0
# schema: MERMAID GeoCSV v1.0.0-rc1
```

A comment begins with `#` as its first character. Readers accept zero or more
whitespace characters after `#`, before the colon, and around header values,
including individual values in metadata lists, following GeoCSV v2.0.4 rules
5–6. Keyword names remain case-sensitive. Raw comment spelling is preserved
alongside normalized keys/values. No such trimming applies to data cells.

Exactly one dataset declaration is required on the first physical line.
Exactly one schema declaration is required before the column header; its base
version must be 1.0.0 with an optional hyphenated prerelease and/or `+` build
metadata composed of dot-separated ASCII letters, digits and hyphens. Unknown
base versions and missing/repeated declarations raise. Schema matching does
not waive the field, scientific or CSV requirements below. Old magic-line
headers are unsupported; there are no aliases or format fallback.

All comments precede the column header. Comments after it are invalid except
for `#` inside a quoted multiline CSV cell. One file contains one dataset.
The remaining required declarations can occur in any order:

| Declaration | Required value |
| --- | --- |
| `dataset` | `GeoCSV 2.0` |
| `schema` | `MERMAID GeoCSV v` followed by a supported 1.0.0-family revision |
| `created` | Six-digit UTC timestamp |
| `delimiter` | A single comma, unquoted |
| `lineterminator` | Literal backslash and letter n, unquoted: `\n` |
| `field_unit` | Exactly 16 schema units, in column order |
| `field_type` | Exactly 16 schema types, in column order |

`field_type` and `field_unit` values are comma-separated lists; surrounding
padding on each metadata value is discarded, while raw declarations remain
source evidence. Types and units must match exactly after padding removal.
They have no source-data defaults. Optional `field_long_name` and
`field_standard_name` each occur once and contain 16 descriptive entries.
Other `field_*` declarations, including `field_missing`, raise.

The writer emits `description`, `producer`, `publisher`, `hoster` and `consumer`
comments. PPHC means Producer–Publisher–Hoster–Consumer. These comments identify
project roles and links, not a claim that a local file was published or accepted.
`producer` records the actual automaid software version and software DOI.
`references` identifies the paper describing MERMAID GeoCSV and its utility;
it is omitted until a real paper DOI exists. No placeholder is emitted.
These and other descriptive comments are optional to the reader and retained
in order; they cannot change typing, units, missingness or row requirements.
`lineterminator` is a MERMAID descriptive extension, not a GeoCSV-defined keyword.

Canonical writer comments (example creation identity and software version):

```text
# dataset: GeoCSV 2.0
# schema: MERMAID GeoCSV v1.0.0-rc1
# created: 2026-11-05T17:40:39.379513Z
# description: metadata for drifting Mobile Earthquake Recording in Marine Areas by Independent Divers (MERMAID) hydrophones (http://earthscopeoceans.org)
# producer: automaid v4.10.0 (https://github.com/earthscopeoceans/automaid, doi: 10.5281/zenodo.5057096) processes raw MERMAID data to generate miniSEED and GeoCSV files
# publisher: mermaid-publisher (https://github.com/bathymetrix/mermaid-publisher) validates and publishes immutable metadata snapshots
# hoster: bathymetrix (https://bathymetrix.com) provides read-only snapshot hosting
# consumer: mermaid-geocsv (https://github.com/bathymetrix/mermaid-geocsv) fetches and parses metadata, associates it with waveforms, and optionally creates SAC station headers
# lineterminator: \n
# delimiter: ,
# field_unit: unitless,iso8601,unitless,unitless,unitless,unitless,unitless,degrees_north,degrees_east,meters,mbar,unitless,hertz,unitless,seconds,seconds
# field_type: string,datetime,string,string,string,string,string,float,float,float,float,string,float,integer,float,float
```

`#created` describes file creation, not a scientific observation. A snapshot
uses one shared literal value across its files. Preserve that spelling in
provenance; do not replace it with a normalized or rounded release ID.

## Columns, types and units

```csv
MethodIdentifier,Time,Network,Station,Location,Channel,DataQuality,Latitude,Longitude,Elevation,WaterPressure,InstrumentDescription,SampleRate,SampleCount,ClockOffset,TimeCorrectionApplied
```

Column spelling, case and order are exact. No extra or duplicate column is
permitted. Units describe values; they are never appended to numeric cells.
Recording Elevation is emitted as the literal numeric cell `0`, not `0 m`.
Its declared type is `float` and its declared unit is `meters`.

| Column | Type | Unit | Meaning and domain when present |
| --- | --- | --- | --- |
| MethodIdentifier | string | unitless | One of the five method/subject combinations below, with its actual source |
| Time | datetime | iso8601 | Row epoch, UTC, exactly six fractional digits and `Z` |
| Network | string | unitless | Actual nonempty source network code |
| Station | string | unitless | Actual nonempty source station code |
| Location | string | unitless | Actual nonempty recording location code, or exactly two ASCII spaces for known blank |
| Channel | string | unitless | Actual nonempty recording channel code |
| DataQuality | string | unitless | `Q` for DET or `D` for REQ original recordings |
| Latitude | float | degrees_north | GPS-derived station latitude, within [-90, 90] |
| Longitude | float | degrees_east | GPS-derived station longitude, within [-180, 180] |
| Elevation | float | meters | Recording's explicit adopted sea-level reference; numeric value zero |
| WaterPressure | float | mbar | Finite signed sensor reading on Pressure-Absolute rows; nonnegative Recording pressure or crossing proxy |
| InstrumentDescription | string | unitless | `MERMAID_<model>`, preserving the actual nonempty source model code |
| SampleRate | float | hertz | Actual recording sample rate, strictly positive |
| SampleCount | integer | unitless | Original recording sample count, from 1 through 2^63 - 1 |
| ClockOffset | float | seconds | GPS-fix instrument time minus GPS time, signed |
| TimeCorrectionApplied | float | seconds | Signed amount already added to the recording's original start |

Every nonempty number must be finite. Float cells use base-ten decimal syntax
with an optional sign, decimal point and exponent; do not accept infinity or
NaN tokens. Conversion uses binary64 with ordinary floating-point rounding.
Reject overflow and nonzero values that underflow to zero. Integer cells use
base-ten integer syntax, not decimal-point or exponent notation. Do not round
a noninteger count or coerce an invalid cell to missing.

Identity strings preserve case, leading zeros and all source characters.
This profile adds no alphabet or length restrictions to Network, Station,
Location or Channel. Required strings cannot be empty or whitespace-only,
except the defined two-space Location. Do not derive identity or quality from
sample rate, equate DET with 20 Hz, replace historical source codes with current
helper values, or hard-code a model such as 452.020. An actual supplied model
452.020 is emitted as `MERMAID_452.020`.

Latitude and longitude preserve source values. Scientific estimation methods
and assumptions belong to the automaid version in the `producer` header.
Measurement rows supply observations; derived times and locations are the
producer's best estimates, provided in the hope that they are useful. Users may
reinterpolate the measurements for their own scientific purposes. Parsing and
publication checks do not independently validate producer estimation methods.

The producer's GeoCSV writing policy selects rows inside its deployment window
and retained GPS span, and records excluded rows in a local audit sidecar.
The publisher independently checks GPS time bracketing for normal payloads.
These selection policies do not add a reader constraint: the consumer parses
supplied measurements and derived rows without inferring deployment bounds.
See the [producer rules](../../automaid/docs/geocsv.md#measurement-retention-and-derived-row-exclusion).

## Method identifiers and row requirements

MethodIdentifier has exactly three nonempty colon-delimited components,
`Method:Subject:Source`. The supported combinations are:

| Identifier template | Meaning |
| --- | --- |
| `Measurement:Position:<GPS-sensor>` | Source GPS position measurement |
| `Measurement:Pressure-Absolute:<pressure-sensor>` | Reported absolute-pressure sensor reading at its source epoch |
| `Derivation:Recording:automaid-<version>` | Original waveform segment and producer-estimated time/location |
| `Interpolation:Crossing-Descent:automaid-<version>` | Producer descent-crossing estimate |
| `Interpolation:Crossing-Ascent:automaid-<version>` | Producer ascent-crossing estimate |

Use the actual sensor or software identifier. Preserve the producer version's
existing `v` where present, for example `automaid-v4.5.14`; do not invent or
default a version. Sensor-name spaces become underscores, as in the existing
writer. A source cannot contain another colon or whitespace. Split on colons,
not on all hyphens. Both crossing subjects can be grouped as Crossing without
adding a direction column. Unknown method/subject combinations raise.

MethodIdentifier, Time, Network, Station and InstrumentDescription are required
on every row. For other fields, R means required, O optional, and a dash means
the cell must be empty. Missing required or populated inapplicable fields raise.

| Field | Position | Pressure-Absolute | Recording | Both crossings |
| --- | --- | --- | --- | --- |
| Latitude, Longitude | R | — | R | R |
| Location, Channel, DataQuality | — | — | R | — |
| Elevation | — | — | R: zero | — |
| WaterPressure | — | R | R for Q; O for D | R |
| SampleRate, SampleCount | — | — | R | — |
| ClockOffset | O | — | — | — |
| TimeCorrectionApplied | — | — | R | — |

The pressure exception depends only on the source Recording row's Q or D,
not the downloaded waveform's quality. There is no R/buffer or M/archive row
kind in this original-recording profile. Missing optional values stay absent.
No reader, association, projection or provenance path supplies source defaults
or borrows another row's values.

## Missingness and known blank Location

Only a decoded empty CSV cell is missing: both bare empty and `""` decode to
absence. Writers use bare empty cells. An absent Recording Location is invalid;
it does not mean a known blank SEED location.

Exactly two literal ASCII spaces in Location are a present, known blank code.
The canonical visible spelling is `"  "`. Retain both spaces in the DataFrame
and raw source attachment. Association may compare this defined blank code
with waveform Location `""` without rewriting either source or waveform.
This does not universally mean the primary instrument.

All other whitespace-only cells are invalid. Nonempty `nan`, `NA`, `NULL` and
`NaT` are literal strings, never missing markers. Their validity still depends
on the column domain: Station `nan` is a literal supplied string; WaterPressure
`nan` is invalid numeric input. Quoting a numeric `nan` does not make it missing.
Preserve leading-zero codes such as `01` as strings.

## Time and clock signs

Time and #created have the exact shape `YYYY-MM-DDTHH:MM:SS.ffffffZ`, with a
valid Gregorian calendar date, hours 00–23, minutes 00–59 and seconds 00–59.
Timezone-free, date-only, offset-zone and leap-second spellings are outside
this profile. Do not infer a timezone or normalize invalid input.

When a source epoch has more than six fractional digits, the writer rounds to
the nearest microsecond, with exact ties to even and normal carry into the next
second or date. This is serialization only; do not change source objects or
clock algorithms. This formatting precedes assignment of a new #created release
identity; it never reformats an existing release ID. Values already at
microsecond resolution retain their epoch.
ClockOffset and TimeCorrectionApplied are emitted with six decimal places in
seconds using the existing numeric formatter. Printed digits establish neither
clock accuracy nor measurement precision. Readers retain typed UTC values and
record the six-digit source notation in metadata; they do not round input with
an unsupported timestamp width into compliance.

For t_mer = instrument time and t_gps = GPS reference time at the same epoch:

```text
manual drift = t_gps - t_mer = gps.clockdrift
ClockOffset = t_mer - t_gps = gps.mseed_time_delay = -gps.clockdrift
Time = uncorrected_recording_start + TimeCorrectionApplied
TimeCorrectionApplied = event.mseed_time_correction
                      = event.clockdrift_correction
                      = -estimated_ClockOffset_at_recording_epoch
```

Positive ClockOffset means the instrument is ahead. Positive correction moves
the recorded start later; negative correction moves it earlier. GPS-fix offsets
and recording corrections refer to different epochs; do not assume equal
magnitudes or opposite signs for arbitrary pairs of rows. The correction has
already been applied to Time and must never be added again. It is a signed
numeric amount, not a MiniSEED boolean applied flag. The clock columns preserve these source values and signs.

Position ClockOffset is optional because a GPS position can exist without a
clock-offset observation. Recording TimeCorrectionApplied is required. GPS,
pressure and crossing times do not acquire the recording clock correction.
The [clock matrix](../../automaid/docs/clock-timing-matrix.md) records source
and MiniSEED evidence. MiniSEED correction fields use decimal ties-to-even 0.0001-second ticks;
the helper verifies the stored correction and applied bit in every record.
This does not change waveform timestamps or the clock model.

## Pressure, elevation and crossings

Pressure-Absolute rows preserve the reported absolute-pressure sensor value,
including finite negative readings caused by gauge error. A negative reported
reading does not assert negative physical absolute pressure. Do not clamp,
replace, offset-correct or discard it. Recording pressure and crossing proxies
remain nonnegative because they support different projections.
Recording WaterPressure retains the source recording pressure; REQ pressure
may be absent. Crossing values retain producer estimates. Consult the automaid
version in `producer` for their meaning and source estimation assumptions.

Only Recording rows contain Elevation, with literal writer value `0` and unit
`meters`. This is the adopted sea-level reference, not the submerged sensor's
physical elevation. The reader never supplies it. Association projects the
explicit source value into its documented coordinate and SAC destinations;
missing required Elevation raises. There is no implicit vertical-datum or
geoid correction.

The approved SAC station-depth approximation remains
`stdp = WaterPressure / 100` in metres positive down, with no density, latitude
or additional atmospheric correction. Missing REQ pressure remains undefined;
SAC's undefined marker represents absence, not a filled scientific value.
Optional geographic SAC mappings remain only stla, stlo, stel and stdp. This
package handles station metadata, never earthquake-source parameters or ev*
projections. Association algorithms and comparison tolerances do not change.

## Complete synthetic example

The following is a complete file, including its final LF. It demonstrates the
schema, not an observed instrument history. Version labels are illustrative. Independent timing examples do not
establish a relationship between the displayed GPS fixes.

```csv
# dataset: GeoCSV 2.0
# schema: MERMAID GeoCSV v1.0.0-rc1
# created: 2026-10-29T00:00:00.123456Z
# description: Synthetic schema example; not an observed instrument history
# producer: Illustrative automaid-v4.5.14 source labels; not migrated writer output
# lineterminator: \n
# delimiter: ,
# field_unit: unitless,iso8601,unitless,unitless,unitless,unitless,unitless,degrees_north,degrees_east,meters,mbar,unitless,hertz,unitless,seconds,seconds
# field_type: string,datetime,string,string,string,string,string,float,float,float,float,string,float,integer,float,float
MethodIdentifier,Time,Network,Station,Location,Channel,DataQuality,Latitude,Longitude,Elevation,WaterPressure,InstrumentDescription,SampleRate,SampleCount,ClockOffset,TimeCorrectionApplied
Measurement:Position:u-blox_NEO-M8N,2026-01-01T12:00:00.000000Z,MH,PTEST,,,,-20.123456,-150.654321,,,MERMAID_452.020,,,2.000000,
Measurement:Pressure-Absolute:KELLER_Series_6,2026-01-01T12:00:01.000000Z,MH,PTEST,,,,,,,1013,MERMAID_452.020,,,,
Interpolation:Crossing-Descent:automaid-v4.5.14,2026-01-01T12:10:00.000000Z,MH,PTEST,,,,-20.123500,-150.654400,,5000,MERMAID_452.020,,,,
Derivation:Recording:automaid-v4.5.14,2026-01-01T12:20:00.250000Z,MH,PTEST,"  ",BDH,Q,-20.123600,-150.654500,0,123400,MERMAID_452.020,20.000000,2000,,-0.750000
Interpolation:Crossing-Ascent:automaid-v4.5.14,2026-01-01T13:00:00.000000Z,MH,PTEST,,,,-20.124000,-150.655000,,5000,MERMAID_452.020,,,,
Measurement:Position:u-blox_NEO-M8N,2026-01-01T13:10:00.000000Z,MH,PTEST,,,,-20.124100,-150.655100,,,MERMAID_452.020,,,,
Measurement:Position:u-blox_NEO-M8N,2026-01-01T14:00:00.000000Z,MH,PTEST,,,,-20.124200,-150.655200,,,MERMAID_452.020,,,-1.000000,
Derivation:Recording:automaid-v4.5.14,2026-01-01T14:20:01.500000Z,MH,PTEST,01,BDH,D,-20.124300,-150.655300,0,,MERMAID_452.020,20.000000,2400,,1.500000
```

The Q Recording has known blank Location, literal zero Elevation and a
-0.750000 s correction already included in Time. An uncorrected start of
12:20:01.000000 becomes 12:20:00.250000. The D Recording retains Location `01`
and missing pressure; its +1.500000 s correction turns an uncorrected
14:20:00.000000 into 14:20:01.500000. One Position has missing ClockOffset;
the other two demonstrate positive and negative offsets.

## Acceptance and rejection cases

These cases define the executable format verification requirements. The complete example must parse to one
eight-row table with unchanged source order and all five method identifiers.

| Case | Required result |
| --- | --- |
| Complete example | Accept; 16 columns with the declared types/units |
| Finite negative Pressure-Absolute gauge reading | Accept unchanged; no station-depth projection from this row |
| Position ClockOffset empty | Accept as missing; never fill zero |
| D Recording pressure empty | Accept as missing; never borrow pressure |
| All Station cells changed to `nan`, `NA`, `NULL` or `NaT` | Accept each as a literal consistent identity string |
| Location `"  "` versus `01` | Preserve two spaces and leading zero respectively |
| Quoted empty optional cell | Missing, equivalent to bare empty |
| A quoted comma, doubled quote, or multiline value in an otherwise valid string field | Decode and preserve; a continuation `#` remains data |
| Equal timestamps | Preserve all rows; no uniqueness inference from Time alone |
| Optional descriptive project comments omitted | Accept; no replacement text is invented |
| Unknown descriptive header comment | Preserve as opaque text; no semantic effect |
| Missing/unsupported/duplicate schema or required declaration | Reject, including identical repetitions |
| `field_missing`, wrong type/unit, changed/extra/reordered column or second dataset | Reject |
| Short/long row, blank record, malformed quote, or comment after the column header | Reject |
| Required Location empty or a one-space Location | Reject; unknown is not known blank |
| Missing Elevation, `0 m`, or nonzero Recording Elevation | Reject |
| Populated field marked inapplicable in the row matrix | Reject, even if its value is zero |
| Missing required field, invalid/nonfinite number, negative Recording/crossing pressure, nonpositive rate/count, or out-of-range coordinate | Reject; no repair or default |
| Mixed Network, Station or InstrumentDescription within a file | Reject |
| Unknown method/subject, missing source, or old two-clock-column names | Reject; no legacy aliases |
| Timestamp with wrong fractional width, invalid date or missing/alternate timezone | Reject; do not reformat into validity |
| Source epoch 12:00:00.123456500 / .123457500 / .999999500 | Serialize as .123456 / .123458 / 12:00:01.000000 respectively |

Verification also requires producer/reader agreement on both clock signs,
exact new output bytes, schema/literal-release provenance, association,
source-derived elevation/SAC projections and unchanged scientific tolerances.
Use representative real inputs alongside this explicitly synthetic example.

## Snapshot identity and ownership

Changed output bytes require a new shared #created and immutable snapshot
identity. Never rewrite published bytes or literal release identities.
Payload #created strings use six digits; transport preserves
every fractional digit of existing literal release IDs. URL/storage/download
components replace only the two timestamp time-separator colons with hyphens.
Illustrative token IDs remain unchanged. No encoded aliases or fallback return.

Fetch can retrieve exact bytes independently of whether read supports that
payload schema. Transport success does not establish reader compatibility.
Use supported-schema snapshots with the matching consumer. Testing-only
status, production inactivity and publication authorization gates apply.

The producer owns writing, this package owns parsing and station association,
the publisher owns validation/publication, and the site serves exact bytes.
See [hosting responsibilities](hosting.md) for current service status.
