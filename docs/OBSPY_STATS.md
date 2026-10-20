# ObsPy trace metadata: links, mappings, and operation boundaries

Source survey, 2026-10-08; verified against the local ObsPy checkout on
2026-10-16. Companion to the [association discussion](OBSPY_ASSOCIATION.md).
This records observed behavior. Consult the
[focused core Stats reference](OBSPY_STATS_REFERENCE.md) before changing the
associator; it incorporates the source supplied by the user on 2026-10-14.

`Stats` is an extensible dictionary-like container. There is no closed list
of all possible entries: waveform readers and user code add their own.
This survey covers the standard core links and common metadata namespaces,
with representative additional readers. It is not an audit of every optional
format or third-party plugin.

## Verification source and result

The reference checkout is `/Users/jdsimon/programs/obspy/`, clean at commit
`50033e1daf95233cd4f30e95a49c37fd50be2ccd` during this review. Sources below
are relative to that checkout; the linked web documentation remains useful
but can describe a different revision. The repository environment contains
ObsPy 1.5.1, installed separately from this checkout.

The survey's core relationships and namespace boundaries agree with the
checkout. The review added explicit defaults, timing edge cases, SAC sampling
interval handling, coordinate-unit requirements, and merge consequences.
The [focused reference](OBSPY_STATS_REFERENCE.md) retains the provenance of
the previously supplied source excerpts.

| Claims checked | Checkout source |
| --- | --- |
| Defaults, derived fields, component, ID/meta aliases, data assignment, history | `obspy/core/trace.py`: `Stats`, `Trace.__setattr__`, `get_id`/`_set_id`, `_internal_add_processing_info`, `_add_processing_info`. |
| SAC conversion and managed headers | `obspy/io/sac/util.py`: `sac_to_obspy_header`, `obspy_to_sac_header`; `obspy/io/sac/sactrace.py`: header descriptors and `reftime`. |
| MiniSEED, SEG-Y/SU, GSE2, Seismic Handler metadata | `obspy/io/mseed/core.py`, `obspy/io/segy/core.py` and `segy.py`, `obspy/io/gse2/libgse2.py`, `obspy/io/sh/core.py`. |
| Coordinates and distance consumers | `obspy/imaging/waveform.py`: section plotting; `obspy/signal/array_analysis.py`: `get_geometry`. |
| Rotation, calibration, response lookup, simulation | `obspy/core/stream.py`: `read`, `rotate`; `obspy/core/trace.py`: `simulate`, `_get_response`, `remove_response`. |

The seven inspected implementations of `Stats.__setitem__`,
`Trace.__setattr__`, `Trace.__add__`, `Trace._internal_add_processing_info`,
`Stream.merge`, `Stream._cleanup`, and `Stream._merge_checks` match installed
1.5.1 when compared as Python syntax trees with docstrings removed. Focused
runtime checks also verified the core links, lack of nested SAC coupling,
and merge metadata inheritance. This is not an exhaustive format round-trip
or consumer audit.

The important distinction is between **live relationships**, **mapping at a
read/write boundary**, and **metadata consumed or updated by an operation**.
Calling all three automatic projection obscures their different guarantees.

## Live relationships in ordinary `Trace` and `Stats`

`Stats.defaults` contains exactly ten entries: `sampling_rate=1.0`,
`delta=1.0`, `starttime=UTCDateTime(0)`, `endtime=UTCDateTime(0)`, `npts=0`,
`calib=1.0`, and empty strings for `network`, `station`, `location`, and
`channel`. `processing`, format namespaces, and coordinates are optional.

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

For positive rates and nonempty traces, the last-sample time is
`starttime + (npts - 1) * delta`; this is not the next segment's expected
start, which is `endtime + delta`. For `npts=0`, `endtime=starttime`.
The implementation also permits zero rate/delta, setting the reciprocal to
zero; our associator requires a finite positive rate. Assigning `stats.npts`
does not resize `Trace.data`. A zero `calib` warns rather than being rejected.

## Format-specific namespaces

### `stats.sac`

The SAC adapter maps identity, timing, sampling, count, and calibration into
core fields when reading. For example, `knetwk`, `kstnm`, `khole`, and `kcmpnm`
become the core codes; reference time plus `b` becomes `starttime`; `scale`
becomes `calib`. The source SAC header is retained separately.

By default, `sac_to_obspy_header` rounds the stored sample interval to
microseconds before deriving the rate, warning when it differs from the
conventional float32 conversion. This is a read-boundary rule, not a general
Stats rounding rule; `round_sampling_interval=False` selects the conventional
conversion. SAC's undefined `scale` becomes core `calib=1.0`.

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

Units belong to the consuming operation's contract. In particular,
`array_analysis.get_geometry(coordsys="lonlat")` expects latitude/longitude
in degrees and elevation in **kilometres**; its Cartesian inputs also use
kilometres. Record-section distance uses metres by default, or coordinates
and an event position for angular distances. A generic `stats.coordinates`
mapping supplies no automatic unit conversion. Our adopted elevation zero
has the same numeric value in metres and kilometres; that does not establish
a unit convention for a future nonzero elevation projection.

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

## GeoCSV mapping boundary

GeoCSV follows the format-adapter precedent: retain the complete source row
and immutable provenance under `stats.geocsv`, create explicit coordinates
at association, and construct fresh SAC headers only during `write_sac`.
There is no perpetual synchronization between these containers. The
[association reference](OBSPY_ASSOCIATION.md) specifies authority and lifetime.

An Inventory or specialized managed metadata object would need an actual
consumer and explicit epoch/synchronization rules; it is not required by the
current in-memory contract.

## Stream merging does not reconcile nested metadata

`Trace.__add__` initializes a merged trace from a deep copy of the earlier
trace's Stats, then assigns the combined data, updating `npts` and `endtime`.
It does not reconcile coordinates, SAC headers, MiniSEED quality, GeoCSV rows,
or processing histories from both inputs. `Stream.merge` and `Trace.__add__`
are not decorated with `_add_processing_info`; merging itself adds no history
entry. Thus a retained attachment can describe an original segment while
core Stats now describe a longer waveform. See [Stream and merge](STREAM.md#comparison-with-geocsv-association).
