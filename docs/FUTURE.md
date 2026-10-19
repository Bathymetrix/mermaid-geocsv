# Future workflows

This document records possible package extensions and their motivating use
cases. These are planning notes, not commitments to public APIs. Names and
behavior should be decided when an extension is taken up.

## Read local or fetched GeoCSV

`geocsv.read(path)` already reads a local file and returns one DataFrame per
dataset. Keep it as the parsing step in future workflows. Decide whether it
should also accept downloaded text or a file-like object, or whether `fetch`
should save the response and pass its path to `read`.

## Write MERMAID GeoCSV

Add a writer for MERMAID GeoCSV files, informed by the legacy implementation
in `automaid/scripts/geocsv.py`. The writer should be designed around this
package's data model and documented GeoCSV behavior rather than copying
incidental structure from the legacy script.

## Fetch the latest GeoCSV

Initially, keep fetching simple: retrieve GeoCSV metadata for an instrument
from the author's website, [bathymetrix.com](https://bathymetrix.com), at a
location TBD. A possible interface is `geocsv.fetch(instrument_id)`, using an
identifier such as `P0006`. Decide whether it returns downloaded
content, a local path, parsed tables, or supports more than one of these; also
decide whether fetching and parsing can be combined with `geocsv.read`.

## Associate GeoCSV metadata with ObsPy traces

Implemented in version 0.15.0 as `geocsv.associate(waveforms, records, *,
time_tolerance=0.0001, allow_merge=False)`, with optional ObsPy support. It
attaches uniquely matched event metadata and coordinates in place and returns
`None`. See the [association tutorial](ASSOCIATION_TUTORIAL.md) for the public
contract and executable examples; the [original discussion](OBSPY_ASSOCIATION.md)
retains architectural evidence and unresolved archive-lineage questions.

Fetching may later connect to reading and association, while each step remains
usable independently. SAC projection and archive reconstruction remain future
work; package exposure does not add either.

## Associate transformed archive waveforms

Before extending association to trimmed, split, resampled, or archive-combined
waveforms, establish how original acquisitions and overlapping sample values
can be identified. The current `allow_merge=True` option validates exact
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

SAC projection remains planned work. The unused `project_sac` keyword and its
`NotImplementedError` placeholder were removed from the sandbox associator on
2026-10-16 before package exposure; no SAC option is currently accepted.

Retain the intended sequence: read MiniSEED, associate GeoCSV, project approved
fields into fresh `stats.sac`, then compare those keys with the paired SAC file
read independently. The planned geographic mapping is `stla`/`stlo` from
receiver coordinates, `stel=0` for the adopted sea-level reference, and
approximate `stdp=WaterPressure[mbar]/100`. Confirm field coverage, missing
pressure handling, units, comparison precision, and first-segment scope before
implementing it. SAC references must never supply matching inputs or fill
missing source metadata. See the [SAC projection notes](OBSPY_ASSOCIATION.md#optional-sac-projection)
and [merged-trace qualifications](OBSPY_MERGED_TRACES.md#source-metadata-remains-anchor-metadata).
