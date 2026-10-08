# Associating GeoCSV records with ObsPy traces

Discussion draft, 2026-10-08. This proposes an architecture; it does not define
an implemented or committed public API.

## Starting point

Treat `geocsv.read` as complete for the current MERMAID parsing scope. The
reader preserves the information needed here: typed columns, source record
indices, units, comments, and immutable dataset metadata with source paths.
The current 136 tests pass. The [open format questions](OPEN_QUESTIONS.md)
remain qualifications on general GeoCSV interoperability, rather than reasons
to mix waveform interpretation into the reader.

The user-selected first target is **original downloaded MERMAID traces**.
The motivating workflow is to attach record-specific station location and
other metadata to an existing ObsPy `Trace` or `Stream`. The first downstream
consumer has not yet been selected.

The current workflow is in memory: the waveforms are not SAC files and SAC
reading/writing is not a requirement. Existing SAC headers were examined as
one possible attachment mechanism, not as a requirement to use SAC for the
whole payload. Complete SNCL is required; matching tolerance is deferred.

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
| `stats.sac.stla`, `.stlo`, `.stel`, `.stdp` | SAC geographic headers | Available alternative; unnecessary for the current in-memory workflow. |
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
- An original MiniSEED trace can retain finer precision than the GeoCSV row.
  Exact equality of the stored nanoseconds is not necessarily a valid match
  requirement.
- Treat the writer's millisecond rendering as producer-specific evidence,
  rather than imposing millisecond resolution on every GeoCSV producer.

The local automaid note `notes/geocsv_event_deduplication.md` also documents
events sharing a time but differing in sample count. A timestamp alone cannot
identify a waveform record.

ObsPy stores UTC time as integer nanoseconds but defaults to six fractional
digits for comparisons and display. Matching should use an explicit source
precision rule, not an incidental `UTCDateTime` comparison or a floating-point
POSIX timestamp. Require timezone-aware GeoCSV values for this workflow;
compare UTC instants without changing the preserved source timestamps. See
[UTCDateTime](https://docs.obspy.org/packages/autogen/obspy.core.utcdatetime.UTCDateTime.html).

## Agreed boundary: initial association

The agreed design boundary is: **our guarantee ends at initial association;
subsequent behavior is governed by ObsPy**. This is a design decision, not an
implemented public API.

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
alone is not the matched row. The exact attachment schema and mutability
remain to be designed; no scientific inference or conversion belongs in the
source attachment.

Initial association is limited to the following existing waveform attributes
and coordinate convention. It does not fill SAC, response, rotation, or
other format/analysis headers.

| Attribute | Initial association responsibility |
| --- | --- |
| `network`, `station`, `location`, `channel` | Validate against the matched complete SNCL. Existing waveform codes are authoritative; do not silently relabel an input to make it match. |
| `starttime` | Validate the acquisition time under the matching rule still to be chosen; retain the waveform's `UTCDateTime` and finer precision. Do not reapply `TimeCorrection`. |
| `sampling_rate` | Validate against `SampleRate`; preserve the original waveform rate. |
| `npts` | Validate `SampleCount` against the waveform count and data length; do not use a header assignment to repair a mismatched array. |
| `delta`, `endtime` | Leave calculation to ObsPy from the current core fields; do not assign independently. |
| `calib` | Preserve the existing value, including ObsPy's default of 1.0. Current GeoCSV rows supply no calibration factor. |
| `coordinates` | Populate available valid geographic values from the matched row, subject to the units/missingness policy below. Report conflicts rather than silently overwrite. |
| `processing` | Preserve existing history. GeoCSV method/version is source provenance, not a reconstructed ObsPy processing history. Whether to record association itself remains open. |

The ten default attributes of `Stats` are the four channel codes,
`starttime`, `endtime`, `sampling_rate`, `delta`, `npts`, and `calib`.
`coordinates` and `processing` are additional conventions, not initialized
core defaults. `component` is a convenience view of the last channel
character, not another independent field to populate. See
[Stats](https://docs.obspy.org/packages/autogen/obspy.core.trace.Stats.html).

“Populate” means establish or verify a scientifically correct initial state;
it does not mean overwrite every listed field from GeoCSV. For existing
original traces, much of this is validation rather than assignment.

## Coordinates at initial association

The decision to include coordinates in initial association replaces the
previous proposal for optional, separately requested coordinate projection.
Latitude and longitude can be copied when present, finite, and expressed in
compatible declared units. Preserve missing values in the source attachment;
do not invent missing operational coordinates.

Elevation still requires an explicit destination-unit policy. The source
fixture declares metres, while ObsPy array processing expects
`stats.coordinates.elevation` in kilometres. `coordinates` is a consumer
convention, not a universally enforced schema. All 828 waveform rows in the
fixture lack elevation, so this first fixture cannot supply that value.
Water pressure is not elevation; neither zero nor pressure-derived depth
should be substituted. A latitude/longitude attachment need not satisfy the
requirements of a consumer that also requires elevation. See
[array processing](https://docs.obspy.org/packages/autogen/obspy.signal.array_analysis.array_processing.html)
and [record-section plotting](https://docs.obspy.org/packages/autogen/obspy.core.stream.Stream.plot.html).

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

### Possible SAC mappings, if a SAC workflow is later wanted

These are candidate destinations, not an approved slot allocation. Core
waveform fields are checked during association, rather than overwritten.
This table is reference material; it does not prescribe default attachment
destinations for the current in-memory workflow.

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
| `Elevation` | `stats.sac.stel` | Direct only for compatible elevation datum and metres; preserve missingness. |
| `WaterPressure` | No dedicated pressure field; possibly a free `userN` | Preserve mbar. `stdp` requires depth in metres. |
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
when callers keep the original tables. Neither attachment schema is settled.

### Reviewing the automaid example

The example demonstrates a useful approach: core waveform headers, recognized
geographic SAC headers, and explicit application use of user slots. It also
identifies decisions we should not copy automatically:

- **Pressure and depth:** `stdp = self.depth` uses the stated dbar-to-metres
  approximation. That is a derived depth, not a direct mapping of GeoCSV's
  mbar pressure. If offered, document the approximation and preserve pressure.
- **Vertical reference:** `stel = 0` expresses automaid's surface-reference
  convention alongside subsurface depth. It does not establish that a missing
  GeoCSV `Elevation` value means zero. Decide explicitly whether to adopt that
  convention and how it relates to sensor elevation used by other consumers.
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
3. Use start time to identify the acquisition. Precision and matching
   tolerance are deferred, as requested; retain the producer evidence above
   for that later discussion.
4. Require matching sample rate and sample count for original traces. Use
   `stats.mseed.dataquality` as an additional discriminator when present;
   absence on a different input format must not be mistaken for a mismatch.
   ObsPy reads the MiniSEED quality flag into that format-specific field;
   see [MiniSEED source](https://docs.obspy.org/_modules/obspy/io/mseed/core.html).
5. Attach only when one candidate remains. Zero matches and multiple matches
   need distinct, informative outcomes, including candidate record indices.
   Do not silently choose the nearest, first, or last record.

Inspect all supplied datasets without losing their provenance. Do not require
a one-to-one relationship: repeated copies of the same waveform may each
legitimately associate with the same metadata record. Duplicate candidate
rows remain an ambiguity until a deliberate equivalence rule is chosen.

The recommended first behavior for a batch is to resolve matches before
mutation and raise on an unresolved trace, avoiding a partly tagged stream.
This is a modest implementation choice, not a reason to build a reporting
framework. A diagnostic table can be added if real batch use needs it.

## Mutation and subsequent processing

ObsPy commonly operates in place. An attachment function that mutates and
returns the supplied `Trace` or `Stream` is a natural starting proposal.
Callers who want independence can first use `.copy()`, which copies waveform
data too. The function name and return contract are still open. See
[Trace.copy](https://docs.obspy.org/packages/autogen/obspy.core.trace.Trace.copy.html).

Keep existing waveform identity, timing, sample rate, count, calibration,
and existing defined format headers authoritative. Association checks them;
it does not repair or replace them. Do not create SAC headers by default.
Report conflicting custom attachments or initial coordinate
projections rather than silently overwrite them. An explicit future SAC
projection should extend its existing header rather than replace it. We still
need to decide whether an identical repeated attachment is a no-op.

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
separate when their positions matter. Designing associations for already
merged, trimmed, resampled, or clock-shifted inputs is outside the first scope.
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

The next discussion should settle, in order:

1. Coordinate missingness and elevation units for the initial attachment;
   identify the first consumer before promising its requirements are met.
2. Adapter ownership and public name. `associate` emphasizes matching;
   `attach_metadata` emphasizes mutation. Neither spelling is committed.
3. Source-record attachment schema and whether its snapshot is immutable.
4. Whether association itself should append a `processing` entry; preserve
   existing history and do not reconstruct it from GeoCSV.
5. Existing-header conflict handling. SAC slot allocation and pressure/depth
   conversion are outside the current in-memory requirement.

Complete SNCL is established. The exact time-matching rule and tolerance are
deferred until the metadata representation is settled.

Before implementation, validate the proposed rule on a real original trace,
including its quality flag, full-precision start time, rate, and count. Then
use focused examples for multiple candidates, missing pressure/elevation,
equivalent timezones, and metadata copying through trimming. ObsPy is not
installed in this repository's `.venv`; this draft is based on official
documentation/source inspection and local GeoCSV/writer inspection, not an
executed ObsPy prototype.
