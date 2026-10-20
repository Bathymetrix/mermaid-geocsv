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

Repository ethos: **simple rules, clear projections, and no surprise side effects**.
Before changing association or describing ObsPy's main Stats attributes, consult
`docs/OBSPY_STATS_REFERENCE.md`, which records the relevant supplied source.
Keep the ten core defaults distinct from optional namespaces and processing
history; `_add_processing_info` is a decorator, not a core Stats field.

### ObsPy Source and Style Reference

Use `/Users/jdsimon/programs/obspy/` as the local read-only source reference
for ObsPy behavior and conventions. Reinspect relevant modules, nearby tests,
`CONTRIBUTING.md`, and `misc/docs/source/coding_style.rst` occasionally,
especially before substantial association/API work or after the checkout
changes. Record the inspected commit in source-based reports, and distinguish
checkout behavior from the ObsPy version installed in this repository's `.venv`.

Keep this repository broadly consistent with ObsPy's naming, documentation,
testing, and implementation style where appropriate: `geocsv` may eventually
be proposed for inclusion there. Favor semantic consistency over mechanical
renaming or unrelated style rewrites; possible upstream inclusion does not
authorize API changes. Inspection is authorized; do not modify the ObsPy
checkout unless separately and explicitly requested.

### Processed Data Reference

`$MERMAID/processed/` is a canonical source of test examples. Its recursive
float directories contain paired SAC/MiniSEED waveforms and GeoCSV metadata
(including `geo_DET_REQ.csv`). Reading and copying examples into this
repository is authorized. Never write, rename, delete, regenerate, or otherwise
modify anything in that source tree without the user's express instruction.
Document fixture provenance. Copy both waveform formats for each selected
basename. Complete association GeoCSV histories are local, Git-ignored copies;
retain their provenance/hashes in the tracked manifest. Do not stage them.
As authorized on 2026-10-16, publish small association GeoCSV subsets for
portable tests. Preserve original header and selected record bytes, retain
nearby candidates and measurement context, and record the mapping from subset
indices to original source-record indices. Subsets do not establish uniqueness
across an entire source history. Keep complete local histories unchanged for
separate corpus checks; ordinary tests must not depend on their availability.

`$MERMAID/waveforms/mseed/` and `$MERMAID/waveforms/sac/` are additional
authorized read-only references for the waveforms described by these GeoCSV
files. Entries may be symlinks into the protected processed tree. Consult
them for context without modifying either the entries or their targets.

### Association Cardinality and Location Meaning

Complete SNCL and time are always required. In the user's MERMAID construction,
each original contiguous waveform segment has one algorithm:event record.
Multiple input traces may associate with the same GeoCSV row, including
identical traces requested again in different MER files. Never consume or
reserve a matched row exclusively for one trace. Conversely, one trace must
not receive multiple source-row associations; multiple eligible rows are an
error, not permission to combine their metadata.

Known empty Location is valid and matches only waveform location `""`.
Network, Station, and Channel must be nonempty; no identity field may be missing.
The reader preserves empty cells specifically in string-valued `Location`;
`nan` and nonempty declared missing markers still mean unknown. Other columns
retain their existing missingness. Source preflight rejects invalid event
identities and duplicate complete SNCL/UTC-time/count/rate matching keys before
trace matching. Different counts may disambiguate the same SNCL/time. Resolve
every trace match before building projections; validate all projections before
mutating traces. DataQuality remains independent source evidence, not a filter.

The assigned position is the interpolated receiver position at the first
sample time, irrespective of waveform length or when a repeat request was
made. Do not average position over the waveform. This position convention
does not relax sample-count validation: GeoCSV `SampleCount` already represents
NPTS and remains an additional check against the original waveform. The
explicit `allow_merge=True` option is the documented exception: a unique
SNCL/start-time anchor may supply location for a longer trace only when source
sample ranges cover the waveform grid exactly and without gaps after overlaps
are counted once. Source start and last-sample alignment use the explicit
tolerance; sample counts have no tolerance. Label standard matches
`stats.geocsv.association = "one_segment"`
and fallback matches `"first_segment"`; never change raw anchor row values.

Retain DET Q and REQ D as useful lineage/validation evidence, independent of
rate. Loss of these distinctions in EarthScope M data, overlaps, contiguity,
and reconstruction of transformed/merged coverage remain open design questions.
The first-segment option adopts a location without claiming that reconstruction;
do not infer original segment identity from M or silently change matching rules.

### Association Inputs and SAC Comparison References

Until further instruction, develop association for original MiniSEED-derived
traces/streams and the explicit first-segment location fallback only.
Paired `.sac` fixtures are independent comparison
references, not association inputs. Their inherited `stats.sac` headers must
never supply defaults, matching hints, or missing values to the associator.

The intended verification sequence is: read MiniSEED, associate its trace with
GeoCSV records, optionally project approved fields into fresh `stats.sac`
headers, then compare those fields key-by-key with `stats.sac` on the paired
SAC trace read separately by ObsPy. Define field coverage, units, missing-value
conventions, and numeric precision for the comparisons. Do not promise whole
SAC-header equivalence for fields without a GeoCSV source or agreed mapping.
Supporting association of SAC-derived input traces is outside current scope;
creating SAC headers on associated MiniSEED traces is deferred planned work.
The unused `project_sac` option was removed on 2026-10-16 before package
exposure. Keep the mapping and comparison plan in `docs/FUTURE.md`; do not
reserve an unimplemented argument in the current associator.

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
pre-existing trace metadata to fill missing source values. Requested destination
containers (`stats.geocsv` and `stats.coordinates`) must be absent, even if
empty or apparently equivalent; otherwise raise. Future `stats.sac`
projections must follow the same rule. Never
merge, overwrite, or delete existing destinations. Required groups, including
latitude/longitude pairs, must be complete or raise; do not introduce per-field
missing-data policy switches. Apply this rule to all association-owned fields,
including future SAC projections, not only coordinates.

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
`geocsv.associate(waveforms, records, *, time_tolerance=0.0001,
allow_merge=False)` attaches uniquely matched event metadata to an ObsPy Trace
or Stream in place and returns `None`. ObsPy remains an optional dependency,
loaded only when association is called. Keep the matching implementation
private and preserve the scientific contract above.
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

Every public function or method must have a dedicated, standalone tutorial
pair under `docs/tutorials/`, named for that operation (for example, `READ.md`
and `READ.ipynb`, `FETCH.md` and `FETCH.ipynb`, or `ASSOCIATE.md` and
`ASSOCIATE.ipynb`). Each tutorial must include its own setup, imports, and
examples runnable from top to bottom without another tutorial's state.
Start each tutorial with the simplest working example, then build toward
increasing input and option complexity. Explain additional options when they
are first introduced.
Downstream analysis examples may have additional standalone pairs, such as
`PLOTTING.md` and `PLOTTING.ipynb`.

Link both companions from each tutorial and list every pair in the README.
Any change to explanations, examples, scientific assumptions, or setup
instructions in either file must be reflected in its companion in the same
change. Markdown Python blocks become executable notebook cells; shell
commands remain Markdown instructions. Cell boundaries may differ for readable
interactive output, but preserve the same prose and Python source in the same
order. Keep committed notebook outputs empty and execution counts unset.
Extend `tests/test_tutorials.py` whenever a public operation or tutorial pair
is added; verify content parity and run each tutorial's Python examples in
order after changing them. Verify that each example actually exercises its
stated behavior (for example, `allow_merge=True` must reach `first_segment`
in its fallback example). Report missing fixture coverage explicitly, and
distinguish real-data examples from synthetic demonstrations so suitable
fixtures can be added.

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
