# ObsPy Stats reference for association

Consult this file before changing association or discussing core Stats fields.
Repository ethos: **simple rules, clear projections, and no surprise side effects**.

## Source

Relevant excerpts from the user's supplied ObsPy `core/trace.py` source,
received 2026-10-14 (attachment `Pasted text.txt`). SHA-256:
`c365cdc6f1515c3cee87853be344905a93f2bee2619c23566f20d3d5dcd487ca`.
The installed ObsPy 1.5.1 defaults were checked against this list.
Excerpts are ObsPy source, copyright the ObsPy Development Team, LGPLv3.
The broader [metadata survey](OBSPY_STATS.md) covers other namespaces and consumers.

Reverified 2026-10-16 against `/Users/jdsimon/programs/obspy/` at commit
`50033e1daf95233cd4f30e95a49c37fd50be2ccd`: the ten defaults, refresh keys,
read-only endtime, and processing-history distinction still agree. The
relevant executable methods also match the separately installed ObsPy 1.5.1
(ignoring docstrings). This checkout check supplements, rather than replaces,
the supplied attachment provenance above. See [Stream merging](STREAM.md)
for behavior that can leave attached metadata describing an earlier segment.

Rechecked 2026-10-19 for public association exposure against the same checkout
commit `50033e1daf95233cd4f30e95a49c37fd50be2ccd`, including Stats/AttribDict,
nearby Stats tests, contribution instructions, and coding style. The
repository `.venv` separately uses ObsPy 1.5.1. Promotion retains the existing
matching and projection behavior; it does not add native Stats fields.

## The ten default Stats attributes

```python
    # set of read only attrs
    readonly = {'endtime'}
    # default values
    defaults = {
        'sampling_rate': 1.0,
        'delta': 1.0,
        'starttime': UTCDateTime(0),
        'endtime': UTCDateTime(0),
        'npts': 0,
        'calib': 1.0,
        'network': '',
        'station': '',
        'location': '',
        'channel': '',
    }
    # keys which need to refresh derived values
    _refresh_keys = {'delta', 'sampling_rate', 'starttime', 'npts'}
```

| Fields | Association responsibility |
| --- | --- |
| network, station, location, channel | Match the complete MiniSEED identity; never fill or relabel it from GeoCSV. |
| starttime | Validate against GeoCSV under the explicit tolerance; preserve the original UTCDateTime and its nanoseconds. |
| sampling_rate | Check the source rate; preserve the waveform rate. |
| npts | Check source SampleCount and loaded data length by default; preserve the waveform count. The explicit first-segment fallback permits a longer trace. |
| delta | ObsPy maintains its reciprocal relationship with sampling_rate; do not assign separately. |
| endtime | Read-only last-sample time derived by ObsPy from starttime, npts, and sampling_rate. |
| calib | Preserve the calibration factor; current GeoCSV supplies no replacement. |

These ten defaults are the mainline fields. `component` is a convenience view
of channel, and `Trace.id` is assembled from identity codes, not extra stored
core attributes. Assigning Trace.data updates npts; assigning stats.npts does
not resize the sample array.

For a nonempty positive-rate trace, `endtime` is
`starttime + (npts - 1) * delta`, rounded to integer nanoseconds by Stats.
For an empty trace it equals `starttime`. Zero sampling rate/delta is allowed
by Stats with reciprocal zero; association rejects nonpositive rates. A zero
calibration factor emits a warning, not a validation error.

## Processing history is not a core field or projection

The supplied source defines the decorator:

```python
@decorator
def _add_processing_info(func, *args, **kwargs):
    # Build an operation-description string, then:
    result = func(*args, **kwargs)
    self = args[0]
    self._internal_add_processing_info(info)
    return result
```

This is an abbreviated illustration of the decorator's execution order.
Its history helper contains:

```python
proc = self.stats.setdefault('processing', [])
# Subject to the processing-history size limit:
proc.append(info)
```

`_add_processing_info` is the decorator; `stats.processing`, when present, is
the list it populates. It is absent from Stats.defaults. Association does not
create, reconstruct, append to, or clear it. Existing history remains unchanged.

## Explicit non-core destinations

The current adapter adds only `stats.geocsv` (source row, provenance, and association label) and
`stats.coordinates` (complete source latitude/longitude plus the adopted
sea-level reference elevation). The separate `geocsv.write_sac` operation
writes geographic SAC headers on a fresh SACTrace for comparison against independently read SAC fixtures. No SAC
option is accepted by association, and existing `stats.sac` is left untouched
by both operations. See the [SAC writing tutorial](tutorials/WRITE_SAC.md).
`stats.mseed` is inherited MiniSEED format metadata and remains untouched.
Response, paz, distance, rotation metadata, and other sensor-specific entries
are not implicitly inferred or projected.

Each requested destination container must be absent, even if an existing one
is empty or looks equivalent. Build fresh complete projections, validate the
whole batch, then attach. No merge, overwrite, deletion, fallback, or per-field
missing-data policy switches. Missing required inputs raise. Source fields
that have no agreed projection remain faithfully available under stats.geocsv.

`stats.geocsv.association` records `one_segment` or `first_segment` at initial
association. The latter requires explicit `allow_first_segment=True`; see the
[merged-trace policy](OBSPY_MERGED_TRACES.md). It adopts an anchor location
without rewriting native waveform fields or source-row values.
