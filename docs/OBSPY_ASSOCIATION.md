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
and coordinate convention. An optional SAC projection may also populate
the geographic headers specified below. It does not fill response, rotation,
or other format/analysis headers.

| Attribute | Initial association responsibility |
| --- | --- |
| `network`, `station`, `location`, `channel` | Validate against the matched complete SNCL. Existing waveform codes are authoritative; do not silently relabel an input to make it match. |
| `starttime` | Validate the acquisition time under the matching rule still to be chosen; retain the waveform's `UTCDateTime` as received, without claiming hardware precision from its displayed digits. Do not reapply `TimeCorrection`. |
| `sampling_rate` | Require an absolute difference from GeoCSV `SampleRate` of at most 0.01 Hz under the provisional check below; preserve the downloaded waveform rate. |
| `npts` | Validate `SampleCount` against the waveform count and data length; do not use a header assignment to repair a mismatched array. |
| `delta`, `endtime` | Leave calculation to ObsPy from the current core fields; do not assign independently. |
| `calib` | Preserve the existing value, including ObsPy's default of 1.0. Current GeoCSV rows supply no calibration factor. |
| `coordinates` | Populate available valid latitude/longitude from the matched row and elevation 0.0 under the sea-level-reference convention below. Report conflicts rather than silently overwrite. |
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

When requested, populate `stla` and `stlo` from receiver latitude/longitude,
`stel = 0.0` from the adopted sea-level convention, and `stdp` from the
approximation above when pressure is available. Do not populate `evla` or
`evlo`: the waveform row does not locate a seismic source. Extend existing
SAC metadata rather than replace it, and report conflicting values rather
than silently overwrite them. Custom user-header slot allocation remains
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
when callers keep the original tables. Neither attachment schema is settled.

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
3. Use start time to identify the acquisition. Precision and matching
   tolerance are deferred, as requested; retain the producer evidence above
   for that later discussion.
4. Require present, finite, positive rates satisfying the provisional minimum
   check `abs(obspy_sps - geocsv_sps) <= 0.01`, in Hz (samples per second).
   A difference greater than 0.01 Hz fails this check; do not round either
   value or overwrite waveform headers to force agreement. This is a necessary
   consistency check, not proof of a unique match. Count and quality still
   require a rule for combined/split coverage and quality M versus source Q/D.
   ObsPy reads the returned MiniSEED quality flag into
   `stats.mseed.dataquality`; see
   [MiniSEED source](https://docs.obspy.org/_modules/obspy/io/mseed/core.html).
5. Attach only when one candidate remains. Zero matches and multiple matches
   need distinct, informative outcomes, including candidate record indices.
   Do not silently choose the nearest, first, or last record.

**Revisit the sampling-rate threshold:** 0.01 Hz is explicitly provisional
and potentially grossly relaxed. The user reports that raw MER files quote
sampling timing at microsecond precision, with uncertain trustworthiness,
whereas the current GeoCSV writer emits single-decimal sampling rates. Verify
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

ObsPy commonly operates in place. An attachment function that mutates and
returns the supplied `Trace` or `Stream` is a natural starting proposal.
Callers who want independence can first use `.copy()`, which copies waveform
data too. The function name and return contract are still open. See
[Trace.copy](https://docs.obspy.org/packages/autogen/obspy.core.trace.Trace.copy.html).

Keep existing waveform identity, timing, sample rate, count, calibration,
and existing defined format headers authoritative. Association checks them;
it does not repair or replace them. Do not create SAC headers by default.
Report conflicting custom attachments or initial coordinate
projections rather than silently overwrite them. The optional SAC
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

1. Latitude/longitude missingness and the first consumer, before promising
   its analysis requirements are met. Sea-level zero and the approximate
   pressure-to-depth convention are now established.
2. Adapter ownership and public name. `associate` emphasizes matching;
   `attach_metadata` emphasizes mutation. Neither spelling is committed.
3. Source-record attachment schema and whether its snapshot is immutable.
4. Whether association itself should append a `processing` entry; preserve
   existing history and do not reconstruct it from GeoCSV.
5. Existing-header conflict handling. Custom SAC slot allocation remains
   outside the first projection; geographic headers and the approximate
   pressure-to-depth mapping are established above.

Complete SNCL is established. The exact time-matching rule and tolerance are
deferred until the metadata representation is settled.

Before implementation, validate the proposed rule on a real original trace,
including its quality flag, full-precision start time, rate, and count. Then
use focused examples for multiple candidates, missing pressure/elevation,
equivalent timezones, and metadata copying through trimming. ObsPy is now
available in this repository's `.venv` after the sandbox work. The initial
design used documentation/source and local writer inspection; live retrieval
evidence is now recorded in the sandbox. An association prototype has not
been implemented.
