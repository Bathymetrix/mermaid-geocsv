# ObsPy Stats reference for association

Consult this reference before changing association or describing core Stats.
The read-only source checkout is ObsPy commit
`50033e1daf95233cd4f30e95a49c37fd50be2ccd`, including `core/trace.py`,
`core/stream.py`, `core/util/attribdict.py`, nearby tests, contribution guidance,
and coding style. The checked installed release is separately ObsPy 1.5.1.
Relevant executable Stats methods agreed with that release, ignoring docstrings.

The supplied `core/trace.py` attachment received 2026-10-14 has SHA-256
`c365cdc6f1515c3cee87853be344905a93f2bee2619c23566f20d3d5dcd487ca`.
This records source provenance, not an additional runtime dependency. ObsPy
source is copyright the ObsPy Development Team, LGPLv3.

## Ten default attributes

| Field | ObsPy default | Association responsibility |
| --- | --- | --- |
| `network` | `""` | Match complete identity; never fill or relabel. |
| `station` | `""` | Match complete identity; never fill or relabel. |
| `location` | `""` | Match exactly, including a known empty location. |
| `channel` | `""` | Match complete identity; never fill or relabel. |
| `starttime` | `UTCDateTime(0)` | Validate with full nanoseconds; preserve native time. |
| `sampling_rate` | `1.0` | Validate against source; preserve native rate. |
| `delta` | `1.0` | ObsPy maintains the reciprocal rate; do not assign separately. |
| `npts` | `0` | Validate loaded data and source count/coverage; preserve native count. |
| `endtime` | `UTCDateTime(0)` | Read-only derived last-sample time. |
| `calib` | `1.0` | Preserve; GeoCSV supplies no replacement. |

For a nonempty positive-rate trace, endtime is
`starttime + (npts - 1) * delta`, rounded to integer nanoseconds; for an empty
trace it equals starttime. Changing delta, sampling_rate, starttime, or npts
refreshes derived values. Assigning Trace.data updates npts; assigning npts
does not resize data. Stats permits zero rate/delta with reciprocal zero;
association requires positive rates. A zero calib warns rather than raising.
`component` is a channel view and `Trace.id` combines identity codes; neither
is another stored core default.

## Optional namespaces and processing history

`stats.mseed` is format metadata inherited from MiniSEED. Its dataquality is
independent of source GeoCSV quality and is not part of Trace.id.
`stats.sac`, `stats.coordinates`, `stats.geocsv`, `response`, and other
application or format entries are not core defaults. Association creates only
its documented [destinations](OBSPY_ASSOCIATION.md#fresh-attachments-and-coordinates),
including optional [SAC headers](SAC.md). It does not infer a Response from an
instrument report URL, perform calibration, or populate orientation metadata.

`_add_processing_info` is a decorator, not a Stats field. After an operation
succeeds it calls `_internal_add_processing_info`, which creates/appends the
optional `stats.processing` list subject to its size limit. Association neither
adds to nor clears this history.

AttribDict converts nested mappings on assignment but does not recursively
convert mappings inside tuples. The association implementation explicitly
allocates AttribDict entries in coverage tuples and fresh UTCDateTime snapshots.
Mutable attachments are fresh per trace; only the matched dataset's immutable
provenance may be shared.

## Metadata lifetime

Core Stats update with supported ObsPy operations; arbitrary attached
namespaces do not track those changes. In particular, trimming, resampling,
and merging do not refresh GeoCSV reports or projected SAC geography. Merge
can retain earlier metadata while changing samples and waveform extent.
Associate the final waveform, and retain provenance separately if needed for
exports. ObsPy's ordinary MiniSEED/SAC writers do not serialize arbitrary
GeoCSV attachments or revalidate their scientific meaning.
