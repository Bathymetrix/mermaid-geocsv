# mermaid-geocsv

These instructions supplement, in increasing order of precedence:

- the global Codex AGENTS (`~/.codex/AGENTS.md`)
- the workspace AGENTS (`~/programs/AGENTS.md`)
- the shared MERMAID AGENTS (`$MERMAID/AGENTS.md`)

This repository `AGENTS.md` has highest precedence. The shared MERMAID AGENTS
sets ecosystem architecture and scientific-data ethos; this file defines
repository-specific implementation and public-interface decisions.

Read and follow the shared MERMAID AGENTS before changing this repository. If
they cannot be located or read, stop and notify the user before making
changes. If instructions conflict, this file takes precedence.

## Repository Scope

`mermaid-geocsv` provides lightweight, faithful parsing of MERMAID GeoCSV
files. It owns structural parsing, typed pandas tabular output, and
preservation of source metadata.

It does not own:

- authoring or rewriting GeoCSV files;
- geospatial analysis, coordinate transformation, or unit conversion;
- inferred scientific metadata;
- downstream catalog, timeline, or waveform interpretation.

Parse the file format as emitted. Do not silently infer, normalize, discard,
or reinterpret scientific metadata unless the documented GeoCSV format
explicitly requires it.

The writer implementation, representative GeoCSV files, and legacy MATLAB
parser are behavioral references. Do not reproduce their structure or
incidental limitations without an explicit reason.

## Naming and Public Interface

Use the following canonical names:

- repository and distribution: `mermaid-geocsv`
- reserved future console command: `mermaid-geocsv`
- Python import: `from mermaid import geocsv`
- format name in prose: `GeoCSV`

Python import names are lowercase by convention. `geocsv` is the stable,
user-facing Python spelling; `GeoCSV` is the format's proper name.

Use a `src/mermaid/geocsv/` package layout because the requested public import
is `from mermaid import geocsv`. This is a package-local implementation of an
immediate public interface, not premature shared cross-repository namespace
infrastructure.

The intended public Python API is deliberately small and must be documented.
`geocsv.read(...)` returns a typed pandas `DataFrame` directly. Preserve
GeoCSV-specific metadata under the single key `frame.attrs["geocsv"]` as one
immutable, documented metadata value. This deliberately uses pandas'
experimental `attrs` facility: guarantee this metadata on the freshly parsed
frame, but not after arbitrary pandas transformations or file exports.

Keep original GeoCSV header spellings as the DataFrame column labels. Preserve
source data order with a zero-based `RangeIndex` named `row_index`, and keep
timestamps as a timezone-aware `StartTime` column rather than an index because
source timestamps need not be unique.

Do not expose parser internals, implementation modules, or convenience
wrappers as stable interfaces merely because tests use them. Do not create
custom column or timestamp-query APIs that duplicate pandas indexing.

Treat the documented Python API and parsed-data model as long-term public
contracts. Preserve raw source content where necessary for provenance and
traceability. Do not add a CLI until a concrete command-level workflow is
identified.

## Development and Verification

When present, use this repository's `.venv` for Python commands, tests, and
the installed console command.

For behavior changes, add focused tests based on representative GeoCSV files
and verify the Python API, DataFrame dtypes, row index, and GeoCSV metadata.
Verify a CLI only when one exists. Keep fixtures small and representative; do
not include sensitive or unnecessary source data.

Update the README whenever changes affect the CLI, public API, supported file
semantics, dependencies, or installation workflow. Keep the README concise,
format-oriented, and suitable as an implementation reference for the planned
metadata-format paper.
