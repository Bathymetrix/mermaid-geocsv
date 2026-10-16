# Associating GeoCSV records with ObsPy traces

Architecture notes, updated 2026-10-15. A sandbox prototype now implements
the initial association contract below; it is not a committed package API.

## Starting point

Treat `geocsv.read` as complete for the current MERMAID parsing scope. The
reader preserves the information needed here: typed columns, source record
indices, units, comments, and immutable dataset metadata with source paths.
The reader test suite passes. The [open format questions](OPEN_QUESTIONS.md)
remain qualifications on general GeoCSV interoperability, rather than reasons
to mix waveform interpretation into the reader.

The first implementation target is **original rebuilt processed MERMAID
traces**, before EarthScope archive handling. `$MERMAID/processed/` supplies
waveforms and complete GeoCSV histories; treat this tree as read-only.
EarthScope retrievals below remain evidence for later service handling.
The motivating workflow is to attach record-specific station location and
other metadata to an existing ObsPy `Trace` or `Stream`. The first downstream
consumer has not yet been selected.

The [retrieval sandbox](../sandbox/obspy_association/README.md) now contains
live examples and a running TBD list. Its
[observations](../sandbox/obspy_association/OBSERVATIONS.md) show that service
downloaded traces and GeoCSV rows can differ in segmentation, reported
sampling rates, and quality flags. This does not establish which layer caused
each difference. The user identifies integer-valued GeoCSV rates in place of
intended measured rates as an upstream writer issue, outside this project.
Preserve both representations; do not round or snap rates to hide discrepancies.
The matching proposal below remains provisional pending corrected source data
and investigation of the other differences.

The user-provided automaid writer diff assigns submitted MiniSEED quality `D`
to requested waveforms and `Q` to detected waveforms. Our current EarthScope
retrievals return `M` for both. EarthScope documents that its legacy archive
rewrote every submitted record's quality to `M` to indicate possible facility
modification; legacy `M` records will retain that code. This appears consistent
with archive handling even when MERMAID submitted separate files, and does not
prove any particular trace combined multiple files. After MERMAID data are
reingested/updated, verify whether submitted Q/D labels are now returned before
using quality in association. EarthScope's current [dataselect help](https://service.earthscope.org/fdsnws/dataselect/docs/1/help/)
says the default “best” selection merges qualities and removes overlaps in
quality-preference order; the `quality` selection parameter has been retired.
Automaid assigns DET=`Q` and REQ=`D` based on stream type, independent of
sampling frequency. A local DET.WLT2 MiniSEED confirms a detected product at
2.5 Hz with quality `Q`. The quality code describes timing/stream lineage;
rate, channel, and location identify the sampling configuration.

The association workflow is in memory, with MiniSEED as waveform ground
truth. Paired SAC fixtures are retained for later header comparisons. Existing SAC headers were examined as
one possible attachment mechanism, not as a requirement to use SAC for the
whole payload. Complete SNCL is required; the initial prototype compares UTC
full UTC timestamps using the source GeoCSV resolution as the default
absolute matching tolerance, with an optional seconds-valued override.

## What ObsPy provides

The [broader trace-metadata survey](OBSPY_STATS.md) distinguishes ObsPy's live
core relationships, format-adapter mappings, and operation-time metadata use.
It broadens the evidence beyond geographic coordinates; the preferred
direction below remains a proposal while those patterns are discussed.

ObsPy separates waveform data from station metadata. A `Trace` contains a
sample array and `stats`; a `Stream` contains traces. Station metadata lives
in an `Inventory` with `Network`, `Station`, and `Channel` objects. These are
complementary representations, not competing replacements for the waveform.
See [ObsPy core](https://docs.obspy.org/packages/obspy.core.html) and
[Inventory](https://docs.obspy.org/packages/obspy.core.inventory.html).

`Stats` is a dictionary-like header container, supporting both item and
attribute access. Its core fields describe the waveform: network, station,
location code, channel, start time, sample rate, and sample count. `location`
is a SEED location **code**, not geographic position. Changing timing or
sample fields recalculates related fields, including the read-only `endtime`.
See [Stats](https://docs.obspy.org/packages/autogen/obspy.core.trace.Stats.html).

Additional metadata can live in a dedicated nested entry, following the
pattern of format-specific `stats.mseed` and `stats.sac`. A dictionary assigned
to `Stats` is converted to ObsPy's `AttribDict`, allowing convenient attribute
access. `stats.geocsv` would be our convention, not a built-in ObsPy schema.
See [Stats source](https://docs.obspy.org/_modules/obspy/core/trace.html) and
[AttribDict](https://docs.obspy.org/packages/autogen/obspy.core.util.attribdict.AttribDict.html).

Geographic metadata has consumer-specific conventions:

| Representation | Intended use | Relevant semantics |
| --- | --- | --- |
| `Inventory` channel coordinates | Standard station metadata, StationXML, response workflows | Coordinates belong to channel epochs; elevation and depth use metres. |
| `stats.coordinates.latitude` and `.longitude` | Some waveform analysis and plotting functions | Record-section plotting can use these two fields alone. |
| `stats.coordinates.elevation` | ObsPy array analysis | Array processing expects kilometres. |
| `stats.sac.stla`, `.stlo`, `.stel`, `.stdp` | SAC geographic headers | Optional projection at association, using the conventions below. |
| Proposed `stats.geocsv` | Source record and provenance | Preserve GeoCSV names, declared units, method, and source identity. |

Sources: [Channel](https://docs.obspy.org/packages/autogen/obspy.core.inventory.channel.Channel.html),
[Distance units](https://docs.obspy.org/_modules/obspy/core/inventory/util.html),
[record-section plotting](https://docs.obspy.org/packages/autogen/obspy.core.stream.Stream.plot.html),
[array processing](https://docs.obspy.org/packages/autogen/obspy.signal.array_analysis.array_processing.html),
and [SAC headers](https://docs.obspy.org/packages/autogen/obspy.io.sac.sactrace.SACTrace.to_obspy_trace.html).

An `Inventory` is the standard choice for station/channel metadata and
instrument responses. It is not automatically the best representation of
every GeoCSV row. Generating position epochs from observations would require
a policy about when each position is valid. The GeoCSV record itself does not
establish that interval. Inventory also supports custom StationXML tags via
`.extra`, but this entails an XML representation and is unnecessary for the
initial in-memory association. See
[custom StationXML tags](https://docs.obspy.org/tutorial/code_snippets/stationxml_custom_tags.html).

Response handling is separate. A response-report URL in a GeoCSV comment is
not an ObsPy `Response`. Current documentation deprecates `attach_response`
and recommends passing an inventory to response-removal methods. Our
association should not claim to supply instrument-response correction. See
[Trace.attach_response](https://docs.obspy.org/packages/autogen/obspy.core.trace.Trace.attach_response.html).

## MERMAID evidence that constrains the design

The bundled [P0006 fixture](../data/fixtures/P0006/P0006.geocsv) has 20,345
records: 828 `Algorithm(event)` waveform records alongside GPS, pressure, and
thermocline records. All 828 waveform records have latitude and longitude;
all lack elevation, and 32 lack water pressure. Full channel identity and
start time happen to be unique among these waveform records. That is evidence
for this fixture, not a uniqueness guarantee for all files.

The local automaid reference writer, `scripts/geocsv.py`, supplies waveform
rows from `event.obspy_trace_stats`, including channel codes, sample rate,
sample count, and MiniSEED data quality. Its start-time expression is
`str(event.obspy_trace_stats["starttime"])[:23] + 'Z'`: it retains milliseconds
and drops the later displayed fractional digits. The local
`scripts/events.py` assigns `corrected_starttime` to those stats. Consequently:

- Match against the corrected waveform time; do not apply `TimeCorrection`
  again during association.
- Timestamp representations can differ without establishing a difference in
  physical clock accuracy. Extra digits are not evidence of clock resolution.
- Treat the writer's millisecond rendering as producer-specific evidence,
  rather than imposing millisecond resolution on every GeoCSV producer.

The local automaid note `notes/geocsv_event_deduplication.md` also documents
events sharing a time but differing in sample count. A timestamp alone cannot
identify a waveform record.

### Authority and timing meaning

For this association workflow, presume the downloaded waveform attributes
are correct and use them as the operational authority. GeoCSV can have passed
through multiple formatting/conversion steps before this reader receives it.
The reader supplies typed values faithfully; it cannot restore information
lost upstream. GeoCSV discrepancies are matching evidence, not instructions
to repair the waveform's identity, start time, sampling rate, or sample count.

The user clarifies that the current MERMAID waveform clock does not have
millisecond timing precision. Do not make sub-millisecond GeoCSV timestamp
fidelity a scientific requirement or mistake ObsPy's nanosecond storage for
hardware accuracy. Preserve the values as received and keep the time-matching
rule explicit and separate from physical clock accuracy. Require timezone-aware
GeoCSV timestamps and compare UTC instants without changing source values.

Precise `delta` and `sampling_rate` remain meaningful for waveform timing even
when absolute clock accuracy is coarser. A rate can be estimated from count
and independently established duration only with the endpoint convention
specified: for first-to-last sample duration, rate is `(npts - 1) / duration`;
for a duration covering `npts` full sampling intervals, rate is `npts / duration`.
ObsPy's `stats.endtime` is derived from its rate, count, and start time, so
calculating the rate back from `stats.endtime - stats.starttime` is circular,
not an independent check. This association does not recalculate sampling rates.

## Agreed boundary: initial association

The agreed design boundary is: **our guarantee ends at initial association;
subsequent behavior is governed by ObsPy**. This is implemented in the sandbox, without establishing a public package API.

An associated original downloaded trace receives `stats.geocsv` from the
matched row returned by `geocsv.read`. The initial eligible category is
`MethodIdentifier` beginning with `Algorithm(event)`, such as
`Algorithm(event):automaid:v4.5.9`. This category describes the waveform
acquisition, including both detections and requested waveforms; it does not
mean a confirmed earthquake or only an onboard detection. GPS, pressure,
and thermocline observations describe different records and are outside this
first association scope. Do not hard-code one producer version.

The attachment retains the parsed row's source names, values, and missingness.
It also needs the row's `source_record_index` and dataset metadata from
`frame.attrs["geocsv"]`, including units and source path. Dataset metadata
alone is not the matched row. The sandbox stores the row's original columns directly under an ObsPy
`AttribDict` at `stats.geocsv`, with `source_record_index`, `dataset_index`
(the index in the supplied records list), and `metadata` (the original
immutable `GeoCSVMetadata`), plus `association` (`one_segment` or
`first_segment`) and `starttime_difference_seconds`. These five names are
reserved against source-column collisions. All attribute and method names of
the installed ObsPy `AttribDict`, including inherited names, are also reserved
because `stats.geocsv` uses that container. A collision raises `ValueError`
identifying the source, dataset, and conflicting container names before any
trace is modified; columns are never silently renamed or dropped.
The row attachment is a mutable snapshot,
independent of the DataFrame. No scientific conversion belongs in it.

`starttime_difference_seconds` records waveform start time minus matched
GeoCSV `StartTime`, subtracting integer UTC nanoseconds before conversion to
seconds. Positive values mean the waveform starts later; negative values mean
it starts earlier. For `first_segment`, the source time is the anchor row's
time. This derived diagnostic records the initial match; it is neither a clock
correction nor an uncertainty estimate and is not recomputed after later
waveform changes. Both original timestamps remain unchanged.

Initial association is limited to the following existing waveform attributes
and coordinate convention. The reserved optional SAC projection will populate the geographic headers
specified below; the prototype currently raises `NotImplementedError` when
`project_sac=True`. It does not fill response, rotation,
or other format/analysis headers.

| Attribute | Initial association responsibility |
| --- | --- |
| `network`, `station`, `location`, `channel` | Validate against the matched complete SNCL. Existing waveform codes are authoritative; do not silently relabel an input to make it match. |
| `starttime` | Validate the acquisition time within source resolution or explicit `time_tolerance`; retain the waveform's `UTCDateTime` as received, without claiming hardware precision from its displayed digits. Do not reapply `TimeCorrection`. |
| `sampling_rate` | Require an absolute difference from GeoCSV `SampleRate` of at most 0.01 Hz under the provisional check below; preserve the downloaded waveform rate. |
| `npts` | By default validate `SampleCount` against the waveform count and data length; do not use a header assignment to repair a mismatched array. |
| `delta`, `endtime` | Leave calculation to ObsPy from the current core fields; do not assign independently. |
| `calib` | Preserve the existing value, including ObsPy's default of 1.0. Current GeoCSV rows supply no calibration factor. |
| `coordinates` | Require both valid source latitude and longitude, then project elevation 0.0 into a fresh container. Missing either component or an existing destination raises. |

The [source-based Stats reference](OBSPY_STATS_REFERENCE.md) is the canonical
reference for these distinctions. The ten default attributes of `Stats` are the four channel codes,
`starttime`, `endtime`, `sampling_rate`, `delta`, `npts`, and `calib`.
`coordinates` and `processing` are additional conventions, not initialized
core defaults. Processing history is an optional list maintained by ObsPy
processing decorators; association does not project or alter it. `component` is a convenience view of the last channel
character, not another independent field to populate. See
[Stats](https://docs.obspy.org/packages/autogen/obspy.core.trace.Stats.html).

“Populate” means establish or verify a scientifically correct initial state;
it does not mean overwrite every listed field from GeoCSV. For existing
original traces, much of this is validation rather than assignment.

## Coordinates at initial association

The decision to include coordinates in initial association replaces the
previous proposal for optional, separately requested coordinate projection.
Latitude and longitude form one position and must both be present, finite,
and expressed in compatible declared units. Missing either raises. No partial
or elevation-only operational container is created. Source missingness in
other fields remains faithfully attached under `stats.geocsv`.

Every requested destination container must be absent: `stats.geocsv` and
`stats.coordinates`, plus `stats.sac` when SAC projection is requested. Even
an empty or apparently equivalent container raises. Nothing is merged,
overwritten, or deleted. All requested projections start fresh and use only
the matched record, provenance, and documented conventions. There are no
per-field missing-data options; the former `missing_coordinates` argument has
been removed from this experimental sandbox interface.

This strict destination rule is separate from validation of native waveform
fields. Existing MiniSEED SNCL, timing, rate, count, and calibration remain
intact and authoritative. Matching validates their agreement; it never assigns
GeoCSV values to repair a mismatch. All checks finish before any batch mutation.

### Adopted vertical reference and approximate depth

For the initial marine MERMAID workflow, use a constant sea-level reference:
`stats.coordinates.elevation = 0.0` and, when SAC projection is requested,
`stats.sac.stel = 0.0`. This is an explicit application convention consistent
with automaid, not an elevation observation or an inference from a missing
GeoCSV `Elevation`. It refers to the sea surface, not the submerged sensor's
physical elevation. No geoid model, ellipsoid transformation, tidal correction,
or other vertical-datum model is assumed. Lake-level handling is deferred
until required.

The projected zero is numerically identical in metres and kilometres. SAC
`stel` uses metres, while ObsPy array processing expects
`coordinates.elevation` in kilometres. Any future nonzero convention must
make the destination units explicit. Supplying zero does not establish that
surface geometry is suitable for every analysis of a submerged receiver.
The parsed `Elevation` value, including missingness, remains unchanged in
`stats.geocsv`; a future nonzero source elevation must not silently redefine
this reference convention. See
[array processing](https://docs.obspy.org/packages/autogen/obspy.signal.array_analysis.array_processing.html)
and [record-section plotting](https://docs.obspy.org/packages/autogen/obspy.core.stream.Stream.plot.html).

For optional SAC `stdp` projection, adopt the user's automaid approximation:

```text
1 dbar = 100 mbar ≈ 1 m of water depth
stdp [m] = WaterPressure [mbar] / 100
```

The pressure-unit conversion is exact; the pressure-to-depth relationship is
an intentionally approximate scientific convention. Event depth in automaid
`.LOG` and `.MER` is reported in dbar, whereas the parsed GeoCSV
`WaterPressure` is declared in mbar. Thus a source event depth expressed in
dbar is numerically equal to the approximate depth in metres, but GeoCSV
pressure must first be divided by 100. For example, 151800 mbar maps to
`stdp = 1518.0` metres, positive downward from the sea-level reference.

This convention deliberately follows automaid's 100 mbar per metre rather
than the 101 mbar per metre stated in the user's cited MERMAID manual
(Réf: 452.000.852, Version 00). That manual comparison is supplied by the
user, not independently verified here. Do not apply a latitude-dependent
pressure-to-depth formula or an additional atmospheric-pressure correction.
This is not an exact oceanographic depth calculation.

Project `stdp` only when pressure is present, finite, and declared in the
expected mbar units. Missing pressure means no new `stdp` value; do not
substitute zero. Preserve original pressure and units in `stats.geocsv`.
Receiver depth belongs in `stdp`, not seismic-source depth `evdp`.

### Optional SAC projection

Until further instruction, MiniSEED-derived traces are the only development
target for association. The paired SAC files are independent output references,
not association inputs. The intended promoted workflow is:

```python
records = geocsv.read(geocsv_path)
tr = obspy.read(mseed_path)[0]
geocsv.associate(tr, records, project_sac=True)  # Planned package API.
reference = obspy.read(sac_path)[0]
# Compare agreed projected keys: tr.stats.sac[key] vs reference.stats.sac[key].
```

The current sandbox still reserves `project_sac=True` with NotImplementedError;
this clarification does not implement it or expose the package API. Reference
SAC headers are consulted only after association/projection and never used
as fallback source metadata or matching hints. Define the comparison's field
coverage, units, missingness, and float32/formatting precision. GeoCSV does not
describe every inherited SAC header, so key-by-key comparison covers approved
mappings rather than an unconditional whole-header equivalence promise.

When requested, populate `stla` and `stlo` from receiver latitude/longitude,
`stel = 0.0` from the adopted sea-level convention, and `stdp` from the
approximation above when pressure is available. Do not populate `evla` or
`evlo`: the waveform row does not locate a seismic source. Require the output `stats.sac` container to be absent and build it fresh;
never merge with or overwrite inherited headers. Custom user-header slot allocation remains
outside this first projection.

This projection carries the same initial-association guarantee as the core
and coordinate attachment. It adds no later synchronization or persistence
guarantee.

## Subsequent behavior belongs to ObsPy

The adapter introduces no observers, subclasses, or synchronization machinery.
ObsPy maintains its existing core relationships: assigning `sampling_rate`
updates `delta` and `endtime`; assigning `npts` updates `endtime`; assigning
`Trace.data` updates `npts`. Assigning `stats.npts` alone does not resize the
sample array. See
[Trace/Stats implementation](https://docs.obspy.org/_modules/obspy/core/trace.html).

The adapter makes no additional promise that later trimming, resampling,
merging, copying, manual edits, or export preserves or recomputes the source
attachment or its projections. ObsPy's actual behavior applies; it does not
provide a live GeoCSV mapping. For example, trimming can change core
`starttime` and `npts` while the attached source `StartTime` and `SampleCount`
still describe the original waveform. Geographic metadata is not automatically
recomputed from that source.

This boundary does not require us to guarantee subsequent ObsPy behavior.
The source attachment's meaning at association and the correctness of initial
validation/projection remain our responsibility.

## What `stats.sac` is and what it can preserve

`trace.stats.sac` is an attribute containing a dict-like `AttribDict`, not a
method or a `SACTrace`. It is created when reading SAC and can also be added
to a trace read from another format. Setting a SAC header does not transform
the waveform into SAC, apply a calibration, or synchronize all other metadata
containers. See [ObsPy SAC support](https://docs.obspy.org/packages/obspy.io.sac.html).

Three different levels matter:

- **Defined SAC fields** have established scientific meanings, such as
  station latitude and longitude.
- **SAC user fields** have standard storage but custom meanings. `user3`
  can hold a clock correction, but SAC does not define it that way.
- **Arbitrary dictionary entries** can exist in `stats.sac` in memory, but
  are not additional SAC file headers. ObsPy warns and ignores unrecognized
  names when building the header arrays.

The current writer uses float32 numeric header storage and eight-byte string
slots, with a special two-slot event name. Float32 conversion happens when
building a `SACTrace`; manually attached values in `stats.sac` need not already
be float32. A Python `float` returned by a `SACTrace` property has nevertheless
already passed through that storage. Longer strings can be truncated, and
arbitrary provenance cannot be serialized as new keys. See
[SAC array conversion](https://docs.obspy.org/_modules/obspy/io/sac/arrayio.html)
and [SACTrace properties](https://docs.obspy.org/_modules/obspy/io/sac/sactrace.html).

The current ObsPy conversion explicitly emits SAC header version 6. The SAC
specification also defines a version-7 double-precision footer; its existence
does not make the inspected ObsPy write path lossless. See
[ObsPy conversion](https://docs.obspy.org/_modules/obspy/io/sac/util.html)
and [SAC format](https://ds.iris.edu/files/sac-manual/manual/file_format.html).

### SAC mapping reference

The geographic projection above is agreed; remaining entries are candidate
destinations, not an approved slot allocation. Core waveform fields are
checked during association, rather than overwritten. SAC projection is
optional, not a default attachment destination.

| GeoCSV field | Existing destination | Fit and qualification |
| --- | --- | --- |
| `Network` | `stats.network`; SAC `knetwk` on export | Direct identity match. |
| `Station` | `stats.station`; SAC `kstnm` | Direct identity match. |
| `Location` | `stats.location`; SAC `khole` | Location code, not position. |
| `Channel` | `stats.channel`; SAC `kcmpnm` | Direct identity match. |
| `StartTime` | `stats.starttime`; SAC reference time plus `b` | Existing waveform time is authoritative. |
| `SampleRate` | `stats.sampling_rate`; SAC `delta` | Sampling interval is its reciprocal. |
| `SampleCount` | `stats.npts`; SAC `npts` | Verify against original waveform. |
| `DataQuality` | `stats.mseed.dataquality` | SAC `iqual` has different categories; no direct equivalent. |
| `Latitude` | `stats.sac.stla` | Direct degrees-north mapping. |
| `Longitude` | `stats.sac.stlo` | Direct degrees-east mapping. |
| Sea-level reference convention | `stats.sac.stel` | Constant 0.0 metres; preserve parsed `Elevation` separately. |
| `WaterPressure` | `stats.sac.stdp` in optional projection | Approximate depth in metres = pressure in mbar / 100; preserve source pressure. |
| `TimeCorrection` | Candidate `stats.sac.user3` | Matches automaid's established slot; seconds, metadata only. |
| `TimeDelay` | Possibly a free `userN` | Separate quantity; do not put it into `b`, `o`, or a pick header. |
| `InstrumentDescription` | `stats.sac.kinst` for a short designation only | `452.020` fits; the full `MERMAIDHydrophone(452.020)` string does not. |
| `MethodIdentifier` | No faithful dedicated field | A short version in `kuser0` preserves only part of the identifier. |

Field definitions: [ObsPy SAC headers](https://docs.obspy.org/packages/autogen/obspy.io.sac.header.html).
Core/SAC translation: [ObsPy conversion source](https://docs.obspy.org/_modules/obspy/io/sac/util.html).
MiniSEED quality storage: [MiniSEED source](https://docs.obspy.org/_modules/obspy/io/mseed/core.html).

### What SAC cannot represent faithfully

A custom entry is warranted for full method and instrument descriptions,
source path and record index, units, dataset comments/declarations, and
quantities that have no agreed SAC slot. It can reuse the existing immutable
`GeoCSVMetadata` for dataset-level provenance. A path plus record index
identifies a row in that source file, not an immutable identity across rewrites.

Pressure, delay, and correction could be projected into user fields for SAC
interoperability, but their names and units still need our documented contract.
Putting them in `userN` does not remove the custom semantics. Decide whether
to retain their exact parsed values as well, especially if SAC round-trip
precision matters. Retaining the complete matched record is the simplest
self-contained option; retaining only residual fields is the smaller option
when callers keep the original tables. The sandbox retains the complete matched record as described above.

### Reviewing the automaid example

The example demonstrates a useful approach: core waveform headers, recognized
geographic SAC headers, and explicit application use of user slots. It also
identifies decisions we should not copy automatically:

- **Pressure and depth:** the user explicitly adopted automaid's approximate
  dbar-to-metres conversion for optional `stdp` projection. Convert GeoCSV
  mbar to dbar by dividing by 100, and preserve the original pressure.
- **Vertical reference:** the user explicitly adopted `stel = 0` and
  `coordinates.elevation = 0` as a sea-level-reference convention, without
  assuming a geoid model. This does not change parsed GeoCSV elevation or
  represent the physical elevation of the submerged sensor.
- **User slots:** leave `user0`–`user2` for SNR, criterion, and trigger index,
  and `user3` for clock correction if preserving automaid compatibility.
  Do not commandeer its `kuser0`–`kuser2` meanings for new labels. No pressure
  or delay slot number is selected yet.
- **Unavailable information:** SNR, criterion, trigger index, transform
  settings, and scale are not current GeoCSV columns. The association cannot
  reconstruct them. Method version and short instrument designation would
  require deliberate extraction from longer strings.
- **Calibration:** `scale` is a real SAC field, but GeoCSV provides no counts
  to Pa factor. ObsPy reads SAC `scale` into core `stats.calib`; avoid changing
  either merely by copying the example. Existing waveform amplitude units
  must be understood before introducing calibration metadata.
- **Orientation:** the stated `cmpinc` convention agrees with SAC. The
  azimuth comment has a typo: a north horizontal component has azimuth 0,
  an east component 90, and a vertical component has no meaningful horizontal
  projection. For a scalar hydrophone, zeros should be identified as a chosen
  convention, not orientation inferred from GeoCSV.
- **Nulls:** the numeric `-12345.0` default belongs to numeric fields, not
  `kinst` or `kuserN` strings. Several strings are subsequently assigned, but
  initialization should respect field types. For newly attached missing
  values, omitting the key lets ObsPy supply the format's appropriate null
  during conversion; preserve existing defined values.

The orientation, depth, and string-storage distinctions are supported by the
[SAC format specification](https://ds.iris.edu/files/sac-manual/manual/file_format.html).
The numeric/string null constants are in
[ObsPy's header definitions](https://github.com/obspy/obspy/blob/master/obspy/io/sac/header.py).

### Tradeoffs of using SAC headers

Advantages are familiar names, a working SAC export path, and fewer new
interfaces for fields SAC already describes. Latitude and longitude can
remain ordinary Python values in the in-memory header until conversion.
It also maintains continuity with automaid's existing scientific workflow.

Limitations are restricted strings, export precision, occupied user slots,
and application-specific meanings for those slots. SAC headers do not make
MiniSEED preserve the same metadata. They also do not populate
`stats.coordinates` or an `Inventory` automatically. If a plotting or array
consumer needs those representations, add a small explicit projection with
its required units rather than assume it reads `stats.sac`.

For the current in-memory workflow, SAC does not solve interoperability with
`stats.coordinates`, nor does it establish a consistency relationship. Prefer
the explicit source-attachment/projection proposal above. Retain this SAC
analysis for a future consumer that actually uses those fields.

An external table of associations is also reasonable for inspection before
attachment. It avoids mutation, but callers then carry a second object and
must keep it aligned with traces. An `Inventory` conversion becomes useful
when an actual station-epoch or StationXML workflow requires it. Neither
alternative needs to become part of the first public interface.

## Matching original traces

Proposed first matching policy:

1. Search waveform metadata rows, distinguishing `Algorithm(event)` records
   from GPS, pressure, and thermocline observations. Do not select by time
   alone or hard-code one automaid version string.
2. Require complete, matching station, network, channel, and location codes
   (SNCL). Missing values are not wildcards and do not silently become empty
   codes. A valid explicitly empty location code is distinct from missing.
3. Compare full UTC nanosecond timestamps using absolute differences; neither
   input is truncated. `time_tolerance=None` uses one unit of each candidate's
   source timestamp resolution from reader metadata. For `.123Z` that is
   0.001 seconds, for `.123456Z` it is 0.000001 seconds, and for nine fractional
   digits it is one nanosecond. Trailing zeros count: `.120Z` and `.120000Z`
   express different source resolutions despite representing the same instant.
   Bounds are inclusive. An explicit finite, nonnegative `time_tolerance` in
   seconds overrides this default; zero requires exact equality. Symmetric
   tolerance accommodates the current writer's truncation and printing-rounding
   boundary without inferring that the waveform's physical clock is that exact.
   Require the full original sample count and loaded data length to agree
   exactly with GeoCSV `SampleCount` by default. The explicit `allow_merge=True`
   fallback below is the sole exception to original-count equality.
4. Require present, finite, positive rates satisfying the provisional minimum
   check `abs(obspy_sps - geocsv_sps) <= 0.01`, in Hz (samples per second).
   A difference greater than 0.01 Hz fails this check; do not round either
   value or overwrite waveform headers to force agreement. This is a necessary
   consistency check, not proof of a unique match. Count and coverage still
   require a rule for combined/split acquisitions. Keep GeoCSV and MiniSEED
   quality indicators separately as stream/archive metadata; they may differ
   and are not a hard association filter. See the sandbox's
   [user-supplied data-quality mapping](../sandbox/obspy_association/MERMAID_DATA_QUALITY.md).
   ObsPy reads the returned MiniSEED quality flag into
   `stats.mseed.dataquality`; see
   [MiniSEED source](https://docs.obspy.org/_modules/obspy/io/mseed/core.html).
5. Attach only when one candidate remains. Zero matches and multiple matches
   need distinct, informative outcomes, including candidate record indices.
   Do not silently choose the nearest, first, or last record.

**Revisit the sampling-rate threshold:** 0.01 Hz is explicitly provisional
and potentially grossly relaxed. The user reports that raw MER files quote
sampling timing at microsecond precision, with uncertain trustworthiness,
whereas the earlier GeoCSV outputs used single-decimal sampling rates. The
rebuilt sampled files now render rates to six decimal places; verify all
producer versions before generalizing this change. Verify
the raw quantity, its units/encoding, and its reliability; compare raw MER,
writer input/output, MiniSEED rate representation, and ObsPy reader output.
Determine whether ObsPy changes the value slightly rather than assuming it
does. GeoCSV rounding alone can obscure differences; the present threshold
is not a general guarantee that all single-decimal representations will pass.
Track this in the [reader follow-up](OPEN_QUESTIONS.md#mermaid-sampling-rate-follow-up)
and the sandbox TBD list. No reader or writer normalization is authorized.

Inspect all supplied datasets without losing their provenance. Do not require
a one-to-one relationship: repeated copies of the same waveform may each
legitimately associate with the same metadata record. Duplicate candidate
rows remain an ambiguity until a deliberate equivalence rule is chosen.

The recommended first behavior for a batch is to resolve matches before
mutation and raise on an unresolved trace, avoiding a partly tagged stream.
This is a modest implementation choice, not a reason to build a reporting
framework. A diagnostic table can be added if real batch use needs it.

## Mutation and subsequent processing

The agreed function mutates the supplied `Trace` or `Stream` in place and
returns `None`.
Callers who want independence can first use `.copy()`, which copies waveform
data too. See
[Trace.copy](https://docs.obspy.org/packages/autogen/obspy.core.trace.Trace.copy.html).

Keep existing waveform identity, timing, sample rate, count, calibration,
and existing defined format headers authoritative. Association checks them;
it does not repair or replace them. Do not create SAC headers by default.
Require association-owned destination containers to be absent. Do not merge,
overwrite, or delete them; identical repeated attachments also raise. Optional
SAC output projection will build fresh headers, never extend an inherited one.

Attachment describes the original source waveform. After trimming, its
original `StartTime` and `SampleCount` remain provenance, not assertions about
the current trace. ObsPy's `slice` copies stats while sharing sample data;
ordinary metadata copying does not recalculate geographic meaning. See
[Trace.slice](https://docs.obspy.org/packages/autogen/obspy.core.trace.Trace.slice.html)
and [trace source](https://docs.obspy.org/_modules/obspy/core/trace.html).

Merging is more consequential: trace addition constructs the result from
one input's stats, rather than combining arbitrary metadata from both. A
retained `stats.geocsv` entry cannot be assumed to describe all merged
samples. Prefer attaching before trimming, and keep distinct source waveforms
separate when their positions matter. Already merged inputs have the explicit
first-segment location option below. Arbitrarily trimmed, resampled, or
clock-shifted inputs remain outside the matching contract.
See [trace addition source](https://docs.obspy.org/_modules/obspy/core/trace.html).

This is initially an in-memory contract. MiniSEED's writer uses specific
header fields and does not serialize an arbitrary `stats.geocsv` entry.
Recognized SAC fields can be exported, subject to the storage limits above;
the custom supplement does not survive that export automatically. See
[MiniSEED writer](https://docs.obspy.org/_modules/obspy/io/mseed/core.html).

## Ownership and decisions still open

This work moves from parsing into waveform association: an architecture and
public-interface discussion. The current repository guidance excludes
downstream waveform interpretation. A thin optional ObsPy adapter is a
plausible, limited scope extension here; richer waveform processing belongs
downstream. Decide ownership before implementation and revise the repository
scope explicitly if this package takes on association. A new repository is
not justified solely by this small operation.

Keep ObsPy optional if the adapter lives here, so GeoCSV parsing remains
lightweight. Do not add a dependency or change `read` during planning.

## Implemented sandbox API

### Source identity, repeated requests, and location

Under the user's MERMAID construction, each original contiguous segment has
one algorithm:event row. Multiple traces may map to the same row; repeated
requests in different MER files do not by themselves imply different waveform
metadata. Each trace must still have exactly one eligible row. Multiple rows
cannot be combined into one trace association for the core metadata considered
here; duplicates/ambiguity must be reported.

Position means the interpolated receiver position at the first sample time,
irrespective of waveform length or request date. It is not averaged over
duration. GeoCSV `SampleCount` already supplies NPTS and is checked against the
waveform by default; this extra validation does not replace mandatory SNCL and
time. The opt-in first-segment policy relaxes count equality as specified below.

DET Q / REQ D may help distinguish original overlapping streams. That evidence
can be lost in legacy EarthScope M responses, including when coverage has been
combined. Quality-based validation and recovery of original contributions
remain open. The opt-in below adopts a location without resolving that provenance. See the
[open questions](../sandbox/obspy_association/OPEN_QUESTIONS.md).

### Call contract

```python
from associate import associate  # sandbox/obspy_association on the import path

records = geocsv.read("geo_DET_REQ.csv")
associate(tr, records, project_sac=False, allow_merge=False)
associate(st, records, allow_merge=True)  # Optional first-segment location fallback.
```

`associate` accepts one `Trace` or a `Stream`, mutates supplied traces in place,
and returns `None`. Iterate over traces using one matching routine; recursion
is unnecessary. Records can span multiple floats and multiple datasets. Each
trace must have exactly one match, but independent traces may match the same
row. Zero and multiple matches raise informative `ValueError`s including
source paths and candidate row indices. All matches and destination checks
are validated before modifying any trace in the batch.

`allow_merge=False` requires a standard match and labels it
`stats.geocsv.association = "one_segment"`. With `allow_merge=True`, standard
matches retain that label. Only if no standard match exists may a trace use
`"first_segment"`: require exactly one complete SNCL/start-time anchor under the
same time tolerance, a compatible rate, positive integer anchor SampleCount,
a strictly larger trace count, and trace duration `(npts - 1) / sampling_rate`
at least as long as the anchor duration. Masked gaps raise in both modes.
Ambiguous anchors, shorter traces, incompatible rates, missing coordinates,
and destination conflicts still fail before batch mutation.

The fallback adopts the anchor's location for the whole trace under the
MERMAID drift convention; all attached row fields retain their anchor values,
including SampleCount and DataQuality. It does not validate the provenance of
the additional samples, recover contributors, or detect gaps already filled
upstream. Quality M neither enables nor prevents either association. The flag
performs no waveform merge. These labels describe the initial association;
they are not recomputed after subsequent ObsPy operations. See the
[merged-trace policy](OBSPY_MERGED_TRACES.md) for evidence and limitations.

The prototype preserves the ten native core Stats fields, MiniSEED format
metadata, waveform samples, and any existing processing history. It adds no
processing entry. It requires absent destination containers and complete source
coordinates, with no warning/skip/overwrite switches. Optional SAC projection
is reserved and explicitly unimplemented. See the
[Stats reference](OBSPY_STATS_REFERENCE.md) for core defaults versus extras.

The [rebuilt fixture audit](../data/fixtures/association/README.md) covers 18
paired examples from the six observed naming combinations and their 14 full
GeoCSV histories. Tests exercise multi-float streams, ambiguity, atomic batch
failure, count/rate mismatches, timezone equivalence, missing coordinates,
unit validation, and quality preservation.

Remaining decisions: promote this sandbox interface into the package or keep
it downstream; implement the optional SAC projection; revisit timing and rate
criteria against more source data; establish policies for trimmed, split,
or resampled traces and stronger validation of merged coverage. The opt-in
first-segment policy does not establish full merge provenance.

## Timestamp precision and metadata dependencies

A former millisecond “bin” meant a half-open 0.001-second interval: times
`.123000` through `.123999999` were treated alike, but `.124000` belonged to
another interval. Only comparisons used those bins; input values were never
rewritten. That rule has now been replaced by the explicit tolerance above.

`geocsv.read` already preserved timestamp values to nine fractional digits.
Version 0.11.0 additionally retains their lexical resolution in immutable
`frame.attrs["geocsv"].datetime_resolution_ns[column][source_record_index]`.
This records the precision written in the file rather than guessing from
pandas storage units or trailing zero values. Missing timestamps have no
resolution entry. The reader does not restore digits discarded by a writer.

As of 2026-10-14, the user's MERMAID convention is that temporal resolution
finer than 0.01 s has no physical significance for the current instruments.
This is not a general GeoCSV rule, an accuracy bound, or an automatic 0.01 s
matching tolerance. Preserve all source precision for this general reader.
[miniSEED 3](https://docs.fdsn.org/projects/miniseed3/en/latest/background.html)
defines nanosecond start-time resolution; its binary decoding support is a
separate ObsPy concern and is not implemented by this GeoCSV reader.

Related metadata must be interpreted together:

| Metadata group | Required context before meaningful projection/use |
| --- | --- |
| Receiver position | Latitude **and** longitude, angular units, and coordinate convention; elevation also needs its vertical reference. |
| Waveform identity | Network, station, location, channel; missing codes are not wildcards. |
| Sample timing/coverage | Start time, sample count, sample rate (or delta), and endpoint convention; endtime is derived. |
| Orientation | Azimuth plus dip/incidence, units, and SEED versus SAC angle convention. No orientation projection is implemented. |
| Pressure-derived depth | Pressure, pressure units, and adopted pressure/depth and vertical-reference conventions; optional SAC projection remains reserved. |
| Calibration/response | Scaling or response values plus input/output units and the relevant response definition; a URL alone supplies no ObsPy Response. |
| Clock correction | Correction value, seconds units, and whether it was already applied; association never applies it again. |
| Provenance | Source path, record index, and dataset metadata together; an index alone does not identify a source row. |

These are interpretation dependencies, not a new general validation framework.
The remaining audit findings are tracked in [the audit](OBSPY_ASSOCIATION_AUDIT.md).
