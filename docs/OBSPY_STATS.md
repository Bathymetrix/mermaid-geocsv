# ObsPy trace metadata: links, mappings, and operation boundaries

Source survey, 2026-10-08, using current official ObsPy documentation and
implementation. Companion to the [association discussion](OBSPY_ASSOCIATION.md).
This records observed behavior; it does not settle our attachment API.

`Stats` is an extensible dictionary-like container. There is no closed list
of all possible entries: waveform readers and user code add their own.
This survey covers the standard core links and common metadata namespaces,
with representative additional readers. It is not an audit of every optional
format or third-party plugin.

The important distinction is between **live relationships**, **mapping at a
read/write boundary**, and **metadata consumed or updated by an operation**.
Calling all three automatic projection obscures their different guarantees.

## Live relationships in ordinary `Trace` and `Stats`

| Fields | Trigger and behavior | Scope |
| --- | --- | --- |
| `stats.sampling_rate` and `stats.delta` | Assigning either recalculates the reciprocal. | Live core relationship. |
| `stats.starttime`, `stats.npts`, `stats.delta`/`sampling_rate` → `stats.endtime` | Assigning the inputs recalculates the last-sample time; `endtime` is read-only. | Live derived field. |
| `Trace.data` → `stats.npts` | Assigning a data array updates the count, which updates `endtime`. | Assignment through `Trace`; not a general observer of arbitrary array mutations. |
| `stats.channel` and `stats.component` | Reading `component` returns the channel's last character; assigning it replaces that character. | A view/setter, not a second stored component value. |
| Core network/station/location/channel and `Trace.id` | Reading the ID assembles those codes; assigning a valid ID splits them into core fields. | A view/setter on `Trace`. |
| `Trace.meta` and `Trace.stats` | `meta` accesses the same stats object and can replace it. | An alias, not a copied representation. |

These relationships are explicitly implemented in
[Trace and Stats](https://docs.obspy.org/_modules/obspy/core/trace.html).
They do not provide a generic facility for registering relationships between
nested metadata containers.

## Format-specific namespaces

### `stats.sac`

The SAC adapter maps identity, timing, sampling, count, and calibration into
core fields when reading. For example, `knetwk`, `kstnm`, `khole`, and `kcmpnm`
become the core codes; reference time plus `b` becomes `starttime`; `scale`
becomes `calib`. The source SAC header is retained separately.

Writing reconciles selected values again. Current core `npts` and `delta`
take precedence; identity codes and `b`/`e` are reconciled. With retained
headers, arbitrary SAC fields are carried forward. These are conversion-time
rules, not live coupling. See
[SAC conversion](https://docs.obspy.org/_modules/obspy/io/sac/util.html).

In particular, changing `stats.sampling_rate` refreshes core `delta` and
`endtime` without refreshing a retained `stats.sac.delta`. Changing
`stats.sac.stla` does not populate `stats.coordinates.latitude`.

`SACTrace` is a different, managed object. Within that object, assigning
reference time shifts relative time headers, and geographic setters can
recalculate distance/azimuth fields when `lcalda` is enabled and coordinates
are available. A plain `Trace.stats.sac` mapping does not have those
descriptors. See [SACTrace](https://docs.obspy.org/packages/autogen/obspy.io.sac.sactrace.SACTrace.html).

### `stats.mseed`

The reader puts identity, start time, sampling rate, and sample count into
core stats. Additional information such as data quality, encoding, byte order,
record length, record count, and optional blockette details is retained under
`mseed`. The writer consumes selected nested fields, with explicit writer
arguments taking precedence for supported options.

Record counts are not continuously recalculated when a trace is trimmed.
Nested timing quality is not a second waveform clock, and changing it does
not shift `starttime`. This is reader/writer metadata, not live projection.
See [MiniSEED adapter](https://docs.obspy.org/_modules/obspy/io/mseed/core.html).

### `stats.segy.trace_header` and `stats.su.trace_header`

Readers derive core sampling and start time from trace-header fields.
Writers use current core fields for selected output timing/sampling values
and retain other recognized format fields. Geographic header values do not
automatically become `stats.coordinates`.

The nested header may be a `LazyTraceHeaderAttribDict`: accessing a field
unpacks and caches its bytes. That is an example of a specialized nested
metadata object, but it is lazy decoding rather than cross-container
synchronization. See [SEG-Y/SU adapter](https://docs.obspy.org/_modules/obspy/io/segy/core.html).

### `stats.gse2` and `stats.sh`

These follow the same division between common waveform fields and format
extras. GSE2 retains items such as auxiliary ID, instrument type, calibration
period, and orientation. Seismic Handler retains extra headers under `sh`,
while station, channel, start time, interval, and calibration use core fields.
Writers assemble output from those representations when invoked; assigning a
nested value is not a general trigger to update another container. See
[GSE2 adapter](https://github.com/obspy/obspy/blob/master/obspy/io/gse2/libgse2.py)
and [Seismic Handler adapter](https://docs.obspy.org/_modules/obspy/io/sh/core.html).

## Metadata used by analysis and processing

| Entry | What ObsPy does with it | What it does not imply |
| --- | --- | --- |
| `stats.coordinates` | Geographic plotting and array routines read its fields. | Automatic import from SAC, GeoCSV, or an Inventory. |
| `stats.distance` | Record-section plotting can consume distance in metres. | Automatic calculation from geographic headers; SAC `dist` uses kilometres. |
| `stats.back_azimuth`, `stats.inclination` | Rotation methods can read them when arguments are omitted and record the values used. | Live coupling to SAC `baz`/`cmpinc` or an event location. Ray inclination and component inclination are different quantities. |
| `stats.response` | Response-removal methods can use the attached response; alternatively they look up an Inventory at operation time. | Automatic refresh when trace identity/time changes, or synchronization with `calib`/`paz`. |
| `stats.paz` | `simulate(paz_remove="self")` consumes the attached poles/zeros representation. | A synchronized alternate representation of `stats.response`. |
| `stats.calib` | Explicit calibration application can multiply samples by this factor. | Merely assigning the factor changes samples or derives it from a response sensitivity. |
| `stats.processing` | Decorated processing methods append operation descriptions. | A complete audit of manual data/header changes or nested metadata edits. |
| `stats._format` | The reader records the detected format. | Adding a metadata namespace changes the source-format label or synchronizes containers. |

Sources: [record-section plotting](https://docs.obspy.org/packages/autogen/obspy.core.stream.Stream.plot.html),
[array analysis](https://docs.obspy.org/packages/autogen/obspy.signal.array_analysis.array_processing.html),
[rotation](https://docs.obspy.org/packages/autogen/obspy.core.stream.Stream.rotate.html),
[response removal](https://docs.obspy.org/packages/autogen/obspy.core.trace.Trace.remove_response.html),
[simulation](https://docs.obspy.org/packages/autogen/obspy.core.trace.Trace.simulate.html),
[waveform reading and calibration](https://docs.obspy.org/_modules/obspy/core/stream.html),
and [processing metadata](https://docs.obspy.org/_modules/obspy/core/trace.html).

An Inventory lookup is another useful pattern: an operation obtains the
metadata it needs from a supplied source using trace identity and time.
It need not attach a duplicate first. This is explicit operation-time lookup,
not a permanent link between the trace and the inventory.

## Architectural evidence, without choosing our API yet

ObsPy's common nested metadata model does not promise that every duplicate
header agrees indefinitely. Its adapters define when values are mapped and
which representation wins at that boundary. Its consumers define the fields
they require. Stronger relationships are implemented selectively through
properties or specialized classes.

This leaves several legitimate precedents for GeoCSV:

- Preserve source metadata in a namespace and map when requested, following
  format-adapter behavior.
- Pass source metadata to the consuming operation and look it up then,
  following Inventory-based processing.
- Use a specialized nested object for managed views if a demonstrated need
  justifies it, while recognizing that ordinary `Stats` will not provide that
  behavior automatically.

The question to settle is the intended mapping boundary and authoritative
representation for each overlapping field. A requirement for perpetual
synchronization should be stated explicitly rather than inferred from
ObsPy's support for nested metadata.

Verification was by source/documentation inspection. ObsPy is not installed
in this repository's `.venv`, and these relationships were not exercised in
a local runtime during this survey.
