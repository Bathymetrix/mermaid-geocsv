# Future workflows

This document records possible package extensions and their motivating use
cases. These are planning notes, not commitments to public APIs. Names and
behavior should be decided when an extension is taken up.

## Read local or fetched GeoCSV

Implemented in version 0.16.0. `geocsv.read(source)` accepts a local path,
bytes, one fetch result, or a list/tuple of results and returns a flat list of
dataset DataFrames. Fetch-result provenance is retained on fresh frames;
in-memory sources have no local source path. See [Fetching GeoCSV](tutorials/FETCH.md).

## Write MERMAID GeoCSV

Add a writer for MERMAID GeoCSV files, informed by the legacy implementation
in `automaid/scripts/geocsv.py`. The writer should be designed around this
package's data model and documented GeoCSV behavior rather than copying
incidental structure from the legacy script.

## Fetch the latest GeoCSV

Implemented in version 0.16.0 as `geocsv.fetch(instrument_ids=None, *, base_url,
output_dir=".", release=None, timeout=30)`. Manifest-based selection supports
one float, selected floats, or a complete release. The default saves verified
files and their manifest under a local release directory; `output_dir=None`
retains bytes in memory. Parsing remains a separate `read` step. Production
hosting and a default collection URL remain undecided. See the
[fetch guide](tutorials/FETCH.md) for the API and provisional hosting agreement.

## Associate GeoCSV metadata with ObsPy traces

Implemented in version 0.15.0 with optional ObsPy support. The current signature
is `geocsv.associate(waveforms, records, *, time_tolerance=0.0001,
allow_first_segment=False)`; version 0.18.0 renames the first-segment option. It
attaches uniquely matched event metadata and coordinates in place and returns
`None`. See the [association tutorial](tutorials/ASSOCIATE.md) for the public
contract and executable examples; the [original discussion](OBSPY_ASSOCIATION.md)
retains architectural evidence and unresolved archive-lineage questions.

Fetching, reading, and association connect through their results while each
step remains usable independently. SAC export is implemented separately in
version 0.17.0; archive reconstruction remains future work.

## Associate transformed archive waveforms

Before extending association to trimmed, split, resampled, or archive-combined
waveforms, establish how original acquisitions and overlapping sample values
can be identified. The current `allow_first_segment=True` option validates exact
source-grid coverage and adopts a unique first segment's location; it does
not reconstruct contributions or acquisition lineage. Keep its existing
contract while investigating stronger evidence.

Use the [open association questions](OPEN_QUESTIONS.md#association-scientific-questions)
to guide further retrieval comparisons. Decide the supported transformations,
required provenance, and failure behavior before adding APIs or changing
matching rules. Quality M alone cannot identify a particular merge. The
[retrieval sandbox](../sandbox/obspy_association/README.md) remains exploratory,
separate from the public association implementation.

## Project associated metadata into SAC headers

Implemented in version 0.17.0 as `geocsv.write_sac(trace, path)`. The unused
`project_sac` keyword was removed on 2026-10-16; association still has no SAC
option and does not mutate `stats.sac`. Export constructs a fresh ObsPy
`SACTrace` from an associated original MiniSEED segment and writes a new file.

The mapping is `stla`/`stlo` from attached receiver coordinates in declared
degrees, `stel=0` metres for the adopted sea-level reference, and approximate
`stdp=WaterPressure[mbar]/100` metres, reproducing automaid's dbar-as-metres
convention. Missing REQ pressure (source DataQuality D) leaves stdp undefined;
missing DET pressure fails. SAC references never supply source values.
`first_segment` associations are rejected because anchor metadata does not
represent a longer waveform's trajectory. No averaging or trajectory
reconstruction is attempted. Supporting merged or processed exports remains
undecided. See the [SAC writing tutorial](tutorials/WRITE_SAC.md) and
[notebook](tutorials/WRITE_SAC.ipynb) for the implemented contract and
key-by-key comparison precision.
