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

### Processed Data Reference

`$MERMAID/processed/` is a canonical source of test examples. Its recursive
float directories contain paired SAC/MiniSEED waveforms and GeoCSV metadata
(including `geo_DET_REQ.csv`). Reading and copying examples into this
repository is authorized. Never write, rename, delete, regenerate, or otherwise
modify anything in that source tree without the user's express instruction.
Document fixture provenance. Copy both waveform formats for each selected
basename and copy the complete GeoCSV history for each sampled float, verbatim;
do not subset those histories to the selected waveform rows.
The complete association GeoCSV histories are local, Git-ignored copies;
retain their provenance/hashes in the tracked manifest. Do not stage them.

### Association Inputs and SAC Comparison References

Until further instruction, develop association for original MiniSEED-derived
traces/streams only. Paired `.sac` fixtures are independent comparison
references, not association inputs. Their inherited `stats.sac` headers must
never supply defaults, matching hints, or missing values to the associator.

The intended verification sequence is: read MiniSEED, associate its trace with
GeoCSV records, optionally project approved fields into fresh `stats.sac`
headers, then compare those fields key-by-key with `stats.sac` on the paired
SAC trace read separately by ObsPy. Define field coverage, units, missing-value
conventions, and numeric precision for the comparisons. Do not promise whole
SAC-header equivalence for fields without a GeoCSV source or agreed mapping.
Supporting association of SAC-derived input traces is outside current scope;
creating SAC headers on associated MiniSEED traces is in scope.

### Automaid Source Reference

When MERMAID waveform-processing behavior needs verification, use
`/Users/jdsimon/programs/automaid/` as the definitive source checkout to
inspect. Inspection is authorized; do not modify files in that repository
unless the user separately and explicitly requests those changes.

### Fresh Association State for Every Trace

Every trace association must start with empty, newly allocated association
state for every association-owned key/value and projection. This applies to
each trace, each loop iteration, and each invocation. Never reuse a mutable
attachment/container from another trace or iteration, and never copy an
existing attachment wholesale as the starting state.

Populate association metadata only from that trace's uniquely matched source
record, its dataset provenance, and explicitly documented projection rules
(such as the adopted sea-level reference). Never use an earlier match or
pre-existing trace metadata to fill missing source values. Existing values
may be inspected for conflicts, but are not fallback data. Required groups,
including latitude/longitude pairs, must be complete or follow an explicit
error/skip-with-warning policy; skipping must not retain stale projected
values. Apply this rule to all association-owned fields, including future SAC
projections, not only coordinates.

This rule concerns newly associated metadata, not clearing the waveform's
native Stats or data: existing waveform identity, timing, sampling, and
calibration remain authoritative. Immutable dataset provenance may be shared
only when explicitly obtained from the currently matched dataset. Validation
must finish before mutating the supplied traces; a failure must not clear or
partially replace their existing metadata.

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
`geocsv.read(...)` returns a list of typed pandas `DataFrame` objects, one per
dataset, including for a single-dataset file. Preserve GeoCSV-specific
metadata under the single key `frame.attrs["geocsv"]` on each table as one
immutable, documented metadata value, including the resolved absolute path
opened by the reader as source provenance. This deliberately uses pandas'
experimental `attrs` facility: guarantee this metadata on freshly parsed
frames, but not after arbitrary pandas transformations or file exports.

Keep original GeoCSV header spellings as the DataFrame column labels. Preserve
file-wide data-record order with a zero-based `RangeIndex` named
`source_record_index`, excluding headers and comments, and keep
timestamps as a `StartTime` column rather than an index because source
timestamps need not be unique. Preserve their source timezone when present.

Do not expose parser internals, implementation modules, or convenience
wrappers as stable interfaces merely because tests use them. Do not create
custom column or timestamp-query APIs that duplicate pandas indexing.

Treat the documented Python API and parsed-data model as long-term public
contracts. Preserve raw source content where necessary for provenance and
traceability. Do not add a CLI until a concrete command-level workflow is
identified.

Before the 1.0.0 release, revise public interfaces when doing so makes the
package cleaner, simpler, or more useful. Identify and document meaningful
changes rather than preserving a weak design solely for compatibility.

## Versioning and Release

Start suggested commit summaries with lowercase after the colon: use
`docs: specify known-keyword recognition in audit`, not
`docs: Specify known-keyword recognition in audit`.
When suggesting a commit message, put it in a fenced `text` block so it can be
copied with one click.

Bump the package version when a change affects public behavior, the Python
API, supported GeoCSV semantics, or dependencies. Choose a pre-1.0.0 version
that reflects the scope of the change; documentation-only edits do not need a
version bump. Keep the version in `src/mermaid/geocsv/__init__.py` and update
checks that assert it.

Do not set the package version to 1.0.0, tag it, publish it, or otherwise
release v1.0.0 until the user explicitly instructs you to do so. Version bumps
do not authorize commits, tags, pushes, or publication.

## Development and Verification

Keep `docs/TUTORIAL.md` and `docs/TUTORIAL.ipynb` synchronized. Any change to
explanations, examples, scientific assumptions, or setup instructions in either
file must be reflected in the other in the same change. Markdown Python blocks
become executable notebook cells; shell commands remain Markdown instructions.
Cell boundaries may differ for readable interactive output, but preserve the
same prose and Python source in the same order. Keep the committed notebook's
outputs empty and execution counts unset. Verify content parity and run the
Python examples in order after changing them.

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
