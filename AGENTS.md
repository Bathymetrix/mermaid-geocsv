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

`docs/format-spec.md` defines the implemented payload schema. Keep public
references, tests and tutorials synchronized with verified behavior.

## Repository Scope

### No source-value defaults

Never substitute a default value for missing, unknown, invalid, or unavailable
source metadata anywhere in this repository. This applies to parsing,
association, coordinate and SAC projections, and provenance. Optional values
remain missing or absent as specified by the schema; missing required values
raise. Never silently repair invalid values, fill from another row or trace,
or invent zero, an empty identity, a timestamp, or another assumed value.

Preserve explicit source values, including zero and literal two-space Location.
CSV decoding, declared typing and documented projections from complete source
values are permitted; they do not authorize inference or default filling.
The zero Recording Elevation must come from the writer's explicit
numeric cell `0`, with type `float` and unit `meters`. Never append a unit to
the numeric cell. An adopted convention does not permit supplying an absent value. Ordinary
function/configuration defaults are separate from this source-data rule.

Finite signed Pressure-Absolute sensor readings preserve reported gauge error.
Recording pressure and crossing proxies remain nonnegative. Never clamp,
replace, offset-correct or discard a reported gauge value during parsing or projection.

This repository does not handle earthquake parameters. Do not add earthquake-source
parameter inference, calculations, projections, or header mappings, including
earthquake origin, hypocentre, depth, or magnitude. Geographic metadata describe
MERMAID receiver (station) locations. The approximation 100 mbar per metre
supplies station depth in SAC `stdp`. Optional SAC projections populate only
`stla`, `stlo`, `stel`, and `stdp`; never populate earthquake-source `ev*` headers.
GeoCSV `Derivation:Recording:<source>` rows describe original waveform segments,
not earthquake-source metadata. Unsupported method identifiers raise.

Repository ethos: **simple rules, clear projections, and no surprise side effects**.
Before changing association or describing ObsPy's main Stats attributes, consult
`docs/obspy-stats-reference.md`, which records the relevant supplied source.
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
Use small association GeoCSV subsets for
portable tests. Preserve original header and selected record bytes, retain
nearby candidates and measurement context, and record the mapping from subset
indices to original source-record indices. Subsets do not establish uniqueness
across an entire source history. Keep complete local histories unchanged for
separate corpus checks; ordinary tests must not depend on their availability.
Original byte-preserving subsets remain source evidence, not an active legacy
reader requirement. Create separate new-schema fixtures with documented source
mapping and provenance; do not overwrite protected originals or archived bytes.

`$MERMAID/waveforms/mseed/` and `$MERMAID/waveforms/sac/` are additional
authorized read-only references for the waveforms described by these GeoCSV
files. Entries may be symlinks into the protected processed tree. Consult
them for context without modifying either the entries or their targets.

### Association Cardinality and Location Meaning

Complete SNCL and time are always required. In the user's MERMAID construction,
each original contiguous waveform segment has one Recording record.
Multiple input traces may associate with the same GeoCSV row, including
identical traces requested again in different MER files. Never consume or
reserve a matched row exclusively for one trace. Conversely, one trace must
not receive multiple source-row associations; multiple eligible rows are an
error, not permission to combine their metadata.

Known blank Location is exactly two literal ASCII spaces in the source and
matches only waveform location `""`. Preserve those spaces in the DataFrame
and raw source attachment; identity comparison never rewrites the source or
waveform. An empty decoded Location cell is unknown, not a known blank code.
Network, Station, and Channel must be nonempty; complete association identity
cannot be missing. Only empty decoded CSV cells are missing. Nonempty strings
such as `nan` and `NaT` are literal; invalid nonempty numeric/datetime values
raise. Do not retain declared alternate missing markers. Whitespace-only cells
are invalid except the two-space Location code. Source preflight rejects invalid Recording
identities and duplicate complete SNCL/UTC-time/count/rate matching keys before
trace matching. Different counts may disambiguate the same SNCL/time. Resolve
every trace match before building projections; validate all projections before
mutating traces. DataQuality remains independent source evidence, not a filter.

The source position is the interpolated receiver position at the source
segment's first sample, irrespective of when a repeat request was made.
Do not average position over the waveform. Strict association requires original
start/count agreement. With explicit `allow_first_segment=True`, a unique
same-SNCL source interval must contain the downloaded waveform's first sample;
never assume the nearest earlier row contains it. This supports starts and ends
inside source segments and longer combined windows. Source `SampleCount` remains
necessary to establish intervals, but need not equal downloaded `npts`.
Retain complete, gap-free source sample coverage after clipping ranges to the
waveform bounds and counting overlaps once. Retained boundary samples must
have unique nearest-sample placement within half a waveform interval, independent
of the absolute start/containment tolerance. Exact half-sample ties and drift
beyond the placement allowance raise; counts have no tolerance. Multiple
containing anchors raise, even when one would pass strict matching, with clear
source record/physical line numbers and affected traces. Do not choose an
anchor or fill headers automatically. Label standard matches
`stats.geocsv.association.type = "single_segment"`
and fallback types `"anchor_segment"`; never change raw anchor row values.
Association is a nested AttribDict report with a fresh waveform snapshot,
chronological source coverage descriptions/ranges, signed waveform-start offset,
and maximum measured grid/rate differences. Follow the schema in
`docs/obspy-association.md`; do not store input tolerances or a segment ordinal.
Association provenance is guaranteed only in the in-memory attachment at initial
association. Users may write sidecars in any format; package-managed sidecar
writing, schemas and persistence guarantees are outside the v1 scope.

Retain DET Q and REQ D as useful lineage/validation evidence, independent of
rate. Loss of these distinctions in EarthScope M data, overlaps, contiguity,
and reconstruction of transformed/merged coverage remain open design questions.
The first-segment option adopts anchor geography without claiming that
reconstruction. Under the user's MERMAID negligible-drift convention, anchor
STLA/STLO/STDP/STEL projection to the entire window is valid, including SAC
export. Missing REQ pressure remains undefined; never borrow another row's
pressure. Do not infer original segment identity from M.

### Association Inputs and SAC Comparison References

Until further instruction, develop association for original MiniSEED-derived
traces/streams and the explicit containing-anchor fallback for clipped or
combined MiniSEED windows only.
Paired `.sac` fixtures are independent comparison
references, not association inputs. Their inherited `stats.sac` headers must
never supply defaults, matching hints, or missing values to the associator.

The intended verification sequence is: read MiniSEED, associate its trace with
GeoCSV records, optionally project approved fields into fresh `stats.sac`
headers, then compare those fields key-by-key with `stats.sac` on the paired
SAC trace read separately by ObsPy. Define field coverage, units, missing-value
conventions, and numeric precision for the comparisons. Do not promise whole
SAC-header equivalence for fields without a GeoCSV source or agreed mapping.
Supporting association of SAC-derived input traces is outside current scope.
The optional `create_sac_header=True` association argument creates fresh
`stats.sac` headers with ObsPy's default conversion plus only stla/stlo/stel/stdp
for either association label. The destination must be absent. ObsPy's
Trace/Stream writer owns serialization; publisher-only tooling retains final
waveform/export verification. Do not restore a public package writer. SAC waveform samples remain raw counts, subject
to SAC storage precision. Expect uncalibrated input; instrument correction,
response removal and counts-to-pressure calibration are outside repository scope.
Preserve association-time waveform sample count
separately from raw source SampleCount so publisher verification can detect later length changes.
Keep deferred mappings in `docs/open-questions.md`; do not
reserve an unimplemented argument in the current associator.

### Automaid Source Reference

When MERMAID waveform-processing behavior needs verification, use
`/Users/jdsimon/programs/automaid/` as the definitive source checkout to
inspect. Inspection is authorized; do not modify files in that repository
unless the user separately and explicitly requests those changes.

### Hosting workflow and related repositories

Read `docs/hosting.md` and the publisher's `docs/geocsv/contract.md` for the
canonical ownership and download agreement. Inspect adjacent implementations
before cross-repository changes. The consumer owns scientific APIs; the
publisher owns exhaustive validation, report schema, gating, transfer, latest
activation and local archive recording. The site owns only read-only serving,
listings, landing pages and infrastructure. Do not duplicate association or
publication logic across these boundaries.

Sources and original fixture bytes remain read-only. Artifact-bound reports,
manifests, receipts and source mappings remain immutable evidence. Reports
never accept changed bytes or software. The external publication archive is
`$MERMAID/publisher`; testing artifacts use `geocsv/testing/`. Never copy original
waveform archives there. A source in Git requires a clean entire worktree and
full revision; fingerprints also account for ignored files. Publication includes
a scoped local archive commit only when that publication is authorized; no
push or software-repository commit is implicit. Retiring testing artifacts
requires separate explicit authorization; production retention is indefinite.

### Current hosted-data phase

All hosted GeoCSV data are testing only until production publication is explicitly
authorized, including full-corpus upload/download tests. Keep public descriptions,
manifests and latest pointers consistent with `testing_only: true`, and keep test
activation isolated from future production. Publisher and website testing isolation must be verified before uploads;
local support does not establish deployed behavior.

Timestamped immutable snapshots support reproducible tests without constituting a
first scientific release. Passing scientific acceptance or deploying infrastructure
does not authorize production promotion, a first data/software release tag or
production-availability claims. Preserve the website's scientific and publication
gates; do not relabel frozen manifests or reuse reports bound to different bytes.

### Fresh Association State for Every Trace

Every trace association must start with empty, newly allocated association
state for every association-owned key/value and projection. This applies to
each trace, each loop iteration, and each invocation. Never reuse a mutable
attachment/container from another trace or iteration, and never copy an
existing attachment wholesale as the starting state.

Populate association metadata only from that trace's uniquely matched source
record, its dataset provenance, and explicitly documented projections of
complete source values. Never use an earlier match or
pre-existing trace metadata to fill missing source values. Requested destination
containers (`stats.geocsv` and `stats.coordinates`) must be absent, even if
empty or apparently equivalent; otherwise raise. Requested `stats.sac`
projections follow the same rule. Never
merge, overwrite, or delete existing destinations. Required groups, including
latitude/longitude pairs, must be complete or raise; do not introduce per-field
missing-data policy switches. Apply this rule to all association-owned fields,
including optional SAC projections, not only coordinates.

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
- geospatial analysis, coordinate transformation, or conversions beyond the
  explicitly approved association projections;
- inferred scientific metadata;
- downstream catalog, timeline, or waveform interpretation.

Parse the file format as emitted. Do not silently infer, normalize, discard,
or reinterpret scientific metadata unless the documented GeoCSV format
explicitly requires it.

The writer implementation and representative MERMAID GeoCSV files are behavioral
references. Historical files and the MATLAB parser are scientific references,
not compatibility targets. Do not reproduce their incidental limitations.

## Naming and Public Interface

`docs/format-spec.md` is the payload authority. Producer source precedence and
clock behavior are documented in `../automaid/docs/geocsv.md` and its clock
matrix. Keep all four repositories synchronized before suggesting commit messages.
Only the controlled MERMAID schema is supported. Preserve literal two-space
Location and project explicit Recording Elevation; missing required source
values raise without defaults.

Documentation and tutorial filenames use lowercase kebab-case. Retain
the conventional `README.md`, `LICENSE`, and `AGENTS.md` names.

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

Implementation modules use a leading underscore (`_read.py`, `_fetch.py` and
`_associate.py`). Expose public operations and types through
`src/mermaid/geocsv/__init__.py`; implementation module paths are private.

Preserve `mermaid` as a native namespace package: do not add
`src/mermaid/__init__.py`, and keep namespace package discovery enabled in the
build configuration. Retain `src/mermaid/geocsv/__init__.py` for this component's
public API and package metadata. This distribution owns `mermaid.geocsv`, not
the entire `mermaid` namespace; do not package unrelated sibling components.

A hypothetical future ecosystem may provide `from mermaid import foo` from a
separate `mermaid-foo` repository with its own `src/mermaid/foo/` package,
dependencies, version and releases. Such components need not live in this
repository and must preserve the same native namespace convention without
overlapping package ownership. An optional umbrella metapackage could depend
on compatible component versions to provide one installation command; the
component distributions would still be installed separately in the same Python
environment. This is a possible future direction, not a committed roadmap or
authorization to add sibling packages, shared infrastructure or a metapackage.

The intended public Python API is deliberately small and must be documented.
`geocsv.associate(waveforms, records, *, time_tolerance=0.001,
allow_first_segment=False, create_sac_header=False)` attaches uniquely matched station metadata to an ObsPy Trace
or Stream in place and returns `None`. ObsPy remains an optional dependency,
loaded only when association is called. Keep the matching implementation
private and preserve the scientific contract above.
`geocsv.read(...)` returns a list of typed pandas `DataFrame` objects, one per
supported MERMAID dataset, including for a single-dataset file. This return
shape does not promise arbitrary GeoCSV schema support. Preserve GeoCSV-specific
metadata under the single key `frame.attrs["geocsv"]` on each table as one
immutable, documented metadata value, including the resolved absolute path
opened by the reader as source provenance. This deliberately uses pandas'
experimental `attrs` facility: guarantee this metadata on freshly parsed
frames, but not after arbitrary pandas transformations or file exports.

Keep original GeoCSV header spellings as the DataFrame column labels. Preserve
file-wide data-record order with a zero-based `RangeIndex` named
`source_record_index`, excluding headers and comments, and keep
timestamps as a `Time` column rather than an index because source timestamps
need not be unique. Require the schema's UTC `Z` timestamp spelling with six
fractional digits; never infer a timezone for invalid or incomplete input.
The digit count defines display format, not clock accuracy or measurement
precision. Preserve the required `# MERMAID GeoCSV schema: 1.0.0` declaration
in metadata and provenance; missing or unsupported schemas raise.

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

## Documentation Voice

Write documentation in a direct, factual, statement-based voice. State the
configuration, decisions and requirements without conversational attribution
such as "the user reports", "you said" or "we agreed". Mark planned behavior,
unverified information and uncertainty explicitly rather than presenting them
as established facts. Omit personal account and billing details unless
explicitly requested for the document.

## Development and Verification

Every public function or method must have a dedicated, standalone tutorial
pair under `tutorials/`, prefixed with two digits and an underscore in the
recommended execution order, then named for that operation (for example, `02_read.md`
and `02_read.ipynb`, `01_fetch.md` and `01_fetch.ipynb`, or `03_associate.md` and
`03_associate.ipynb`). Each tutorial must include its own setup, imports, and
examples runnable from top to bottom without another tutorial's state.
Start each tutorial with the simplest working example, then build toward
increasing input and option complexity. Explain additional options when they
are first introduced.
Downstream analysis examples may have additional standalone pairs, such as
`06_plotting.md` and `06_plotting.ipynb`.

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
stated behavior (for example, `allow_first_segment=True` must reach `anchor_segment`
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
