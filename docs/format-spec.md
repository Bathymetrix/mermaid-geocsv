# MERMAID GeoCSV schema

## 1.0.0-rc2 payload

Automaid v4.11.2 writes the rc2 layout below. The reader selects this layout
from the exact `# schema: MERMAID GeoCSV v1.0.0-rc2` declaration.

The payload uses the GeoCSV 2.0 container, six fractional UTC digits,
literal source strings, and producer provenance. Each file contains one
table with one `network` and `station`. The field declarations and header below
specify the exact column order, units and types. Optional field description
declarations each take 18 entries in that order.

```text
# field_unit: unitless,iso8601,iso8601,unitless,unitless,unitless,unitless,unitless,degrees_north,degrees_east,degrees_north,degrees_east,mbar,mbar,hertz,unitless,seconds,seconds
# field_type: string,datetime,datetime,string,string,string,string,string,float,float,float,float,float,float,float,integer,float,float
type,measured_time,derived_time,network,station,location,channel,data_quality,measured_latitude,measured_longitude,estimated_latitude,estimated_longitude,measured_pressure,estimated_pressure,sample_rate,sample_count,clock_offset,time_correction_applied
```

Every row requires `type`, `network`, and `station`. This table lists the
additional applicable fields. Empty cells represent missing or inapplicable
values. Width includes trailing empty cells.

| `type` | Required | Optional |
| --- | --- | --- |
| `gps` | `measured_time`, measured latitude and longitude | `clock_offset` |
| `pressure` | `measured_time`, `measured_pressure` | Estimated latitude and longitude as a pair |
| `downcrossing`, `upcrossing` | `derived_time`, estimated latitude and longitude, `estimated_pressure` | |
| `waveform` | `derived_time`, estimated latitude and longitude, `location`, `channel`, `data_quality`, `sample_rate`, `sample_count`, `time_correction_applied`, and `measured_pressure` for DET | `measured_pressure` for REQ |

Latitudes are within ±90° and longitudes within ±180°. Rates and counts are
positive. Pressure measurements in `pressure` rows retain signed gauge
readings. Waveform pressures and the configured pressure proxy at crossings
are nonnegative. No depth or elevation column is present. Waveform
`data_quality` is `Q` for DET and `D` for REQ. Identity strings preserve
leading zeros. Known blank waveform location is two ASCII spaces.

GPS fixes and pressure observations retain their measured times. Crossings
use a derived time and no clock correction field. A waveform's derived time
is its corrected first-sample time. Its original time can be recovered by
subtracting `time_correction_applied` at the precision of the stored values.
A `gps` row's `clock_offset` is instrument time minus GPS time at that fix.
The [producer rules](../../automaid/docs/geocsv.md) describe modeled pressure
positions and retained crossing anchor epochs.

The reader keeps both time columns, including their missing values and
source-index provenance. Association matches only waveform rows using their
derived time, SNCL, rate and count. It attaches original rc2 field names,
uses estimated coordinates, and projects approximate depth from measured
waveform pressure when supplied. SAC elevation is undefined.

See the [producer rc2 fixtures](../data/fixtures/schema-1.0.0-rc2/README.md)
for examples and source-record mappings.

## File and header

Files are UTF-8 CSV with comma delimiters. The writer emits LF line endings.
The reader accepts LF and CRLF and requires a terminated final line.
CSV uses double quotes, with doubled interior quotes and support for quoted
multiline cells. An empty decoded cell denotes missing data. No padding is
allowed outside quotes and nonempty data values retain their literal spelling.

The first physical line must declare `# dataset: GeoCSV 2.0`. Before the
column header, declare `schema`, `created`, `delimiter`, `lineterminator`,
`field_unit`, and `field_type` exactly once. `created` is a UTC timestamp
with six fractional digits. `delimiter` is a literal comma and
`lineterminator` is a literal backslash followed by `n`. Header keywords
are case-sensitive. Syntactic padding around keywords, values, and field
list entries is ignored and raw comments are retained. Optional
`field_long_name` and `field_standard_name` each describe all columns in
order. Other `field_*` declarations are unsupported. The writer's
`producer` comment identifies the automaid version. All comments precede
the column header.

Every populated timestamp uses `YYYY-MM-DDTHH:MM:SS.ffffffZ`. Numeric values
must parse as finite binary64 floats or signed 64-bit base-ten integers as
declared. Whitespace-only cells are invalid except for the two-space waveform
location. Record order and repeated timestamps are preserved. The publisher
requires each row's populated time to lie within the measured GPS span.

## Complete synthetic example

```csv
# dataset: GeoCSV 2.0
# schema: MERMAID GeoCSV v1.0.0-rc2
# created: 2026-10-29T00:00:00.123456Z
# description: Synthetic schema example; not an observed instrument history
# producer: Synthetic test data
# lineterminator: \n
# delimiter: ,
# field_unit: unitless,iso8601,iso8601,unitless,unitless,unitless,unitless,unitless,degrees_north,degrees_east,degrees_north,degrees_east,mbar,mbar,hertz,unitless,seconds,seconds
# field_type: string,datetime,datetime,string,string,string,string,string,float,float,float,float,float,float,float,integer,float,float
type,measured_time,derived_time,network,station,location,channel,data_quality,measured_latitude,measured_longitude,estimated_latitude,estimated_longitude,measured_pressure,estimated_pressure,sample_rate,sample_count,clock_offset,time_correction_applied
gps,2026-01-01T12:00:00.000000Z,,MH,PTEST,,,,-20.123456,-150.654321,,,,,,,2.000000,
pressure,2026-01-01T12:00:01.000000Z,,MH,PTEST,,,,,,,,1013,,,,,
downcrossing,,2026-01-01T12:10:00.000000Z,MH,PTEST,,,,,,-20.123500,-150.654400,,5000,,,,
waveform,,2026-01-01T12:20:00.250000Z,MH,PTEST,  ,BDH,Q,,,-20.123600,-150.654500,123400,,20.000000,2000,,-0.750000
upcrossing,,2026-01-01T13:00:00.000000Z,MH,PTEST,,,,,,-20.124000,-150.655000,,5000,,,,
gps,2026-01-01T13:10:00.000000Z,,MH,PTEST,,,,-20.124100,-150.655100,,,,,,,,
gps,2026-01-01T14:00:00.000000Z,,MH,PTEST,,,,-20.124200,-150.655200,,,,,,,-1.000000,
waveform,,2026-01-01T14:20:01.500000Z,MH,PTEST,01,BDH,D,,,-20.124300,-150.655300,,,20.000000,2400,,1.500000
```
