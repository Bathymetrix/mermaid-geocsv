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

Add a way to retrieve the latest GeoCSV metadata for an instrument from the
EarthScope MDA using its instrument identifier, such as `P0006`. A possible
interface is `geocsv.fetch(instrument_id)`. Decide whether it returns downloaded
content, a local path, parsed tables, or supports more than one of these; also
decide whether fetching and parsing can be combined with `geocsv.read`.

## Associate GeoCSV metadata with ObsPy traces

See the [ObsPy association discussion](OBSPY_ASSOCIATION.md) for the initial
architecture proposal, ObsPy conventions, MERMAID matching evidence, and open
decisions. Its first target is original downloaded traces.

Support users who have downloaded MERMAID waveform data as in-memory ObsPy
`Trace` or `Stream` objects, but whose traces lack station locations. They
could fetch the instrument's GeoCSV metadata, parse it with `geocsv.read`, and
associate the relevant metadata with their traces so downstream tools can use
location and other station fields.

The association operation might be named `associate`, `tag`, or `map`; settle
the name and public interface when designing the feature. Important choices
include how to match traces to metadata, how to handle multiple metadata rows
or time ranges, and whether to store results in `trace.stats` or return a
separate mapping or dict-like object. Preserve the source metadata and make
ambiguous matches visible rather than silently choosing a row.

The intended workflow may connect fetching, reading, and association, but each
step should remain usable on its own. These notes do not change the current
`geocsv.read` interface or behavior.
