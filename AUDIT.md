# Audit against EarthScope's GeoCSV specification v2.0.4

Audit date: 2026-10-06. Package version reviewed: 0.2.0.

The specific baseline for this audit is
[EarthScope's GeoCSV specification v2.0.4 (2015-07-21)](docs/references/GeoCSV_v2.0.4.pdf),
also published in the [EarthScope GeoCSV GitHub repository](https://github.com/EarthScope/GeoCSV)
as [`GeoCSV-specification-2.0.4.pdf`](https://github.com/EarthScope/GeoCSV/blob/main/GeoCSV-specification-2.0.4.pdf).
Throughout this document, "the specification" and numbered section references
refer to that exact document. CSVW guidance is supporting material referenced
by that specification; supplementary CSVW recommendations are identified as
such. MERMAID conventions and proposed format amendments are evaluated
separately from the requirements of EarthScope's GeoCSV specification v2.0.4.

The audit covers the parser, metadata model, documentation, existing tests,
and adversarial examples run using the repository's virtual environment.
The audit made no implementation changes.

The reader implements a documented MERMAID subset. Several restrictions come
from the implementation rather than the specification. Two confirmed cases
silently discard data records. Findings below distinguish bugs, specification
mismatches, validation gaps, deliberate policies, and scope limits.

All reconciliation checkboxes started unchecked. Checking a box means the stated
step has been completed and verified. Where alternatives are given, record the
chosen resolution; documenting an intentional limitation can resolve a scope
decision without implementing broader support. This checklist does not
authorize functional changes or expand the previously agreed project scope.

Code line references describe the version audited and may move during fixes.

## 1. Valid quoted data can disappear

**Classification:** Definite bug.

**Specification:** Sections 3 and 5 identify comments by a leading `#`. A
record beginning with `"` is CSV data.

**Code:** [Quoted-comment detection](/Users/jdsimon/programs/mermaid-geocsv/src/mermaid/geocsv/read.py:54)
treats a single quoted cell beginning with `#` as a comment.

**Reproduced:** In a one-column dataset, `"#hello"` disappears.
`"#dataset: hello"` instead causes a false "multiple datasets" error.

**Reconciliation:**

- [x] Remove legacy quoted-comment recognition, including in the preamble.
- [x] At record boundaries, recognize comments and keyword declarations only
  by their literal leading `#`.
- [x] Add regression examples for both quoted values and verify that the records
  and their `source_record_index` values are retained.
- [x] Verify that the canonical MERMAID file's corrected unquoted preamble and the
  existing multiline/two-column quoted-data examples still parse correctly.
- [x] Verify quoted hash-prefixed headers, padded keyword declarations, unknown
  comments, and rejection of a legacy quoted dataset declaration.

**Resolution:** The initial 0.2.1 fix retained legacy quoted preamble support.
Version 0.3.0 removes that exception: quoted hash-prefixed cells are header or
data values, never comments. Raw leading-`#` comments and their keyword/value
pairs remain in metadata. P0006's user-edited preamble removes the outer quotes
from the description and delimiter and adds an edit note to the attribution;
the dataset identifier, header, and data bytes are unchanged. Full known-keyword handling stays
tracked in issue 6; blank-record handling stays tracked in issue 2.
Verification: 8 focused tests passed, including canonical P0006 content,
metadata, and source integrity; the full suite passed with 34 tests.

## 2. Whitespace-only data records disappear

**Classification:** Definite bug.

**Specification:** Section 3c says lines without a leading `#` are delimited
data.

**Code:** [Blank-line handling](/Users/jdsimon/programs/mermaid-geocsv/src/mermaid/geocsv/read.py:127)
skipped every whitespace-only line at audit time. After implementing issue 14,
empty/whitespace-only lines after the header now reach record-width or field
conversion checks; empty lines before the header are still skipped.

**Reproduced at audit time:** A one-column string record containing three
spaces disappeared, changing both the number of records and subsequent
`source_record_index` values. Entirely empty lines were also skipped.

**Reconciliation:**

- [x] Send post-header whitespace-only records through field conversion and
  reject them with a located error, as agreed in finding 14.
- [x] Treat an entirely empty post-header line as a zero-cell record and reject
  it against any nonempty header width; do not infer/pad empty cells.
- [x] Reject incompatible record widths explicitly rather than silently
  skipping the record.
- [x] Verify a blank record fails width validation and a whitespace-only field
  fails conversion without shifting subsequent records.

**Resolution:** Implemented alongside finding 14. An empty line after the
header has zero cells and fails width validation; it is never expanded to the
header width. Whitespace-only values in a correctly sized row fail conversion.
Explicitly empty cells in correctly sized records map to typed missing values.

CSVW's non-normative parsing algorithm defaults `skip blank rows` to false and
parses a zero-character row as one empty cell. This reader applies GeoCSV's
fixed-width record policy and rejects that one-cell row when its width does
not match the header:
[CSVW parsing guidance](https://www.w3.org/TR/tabular-data-model/#parsing).

## 3. Valid timezone-free datetimes and dates are rejected

**Classification:** Direct specification mismatch.

**Specification:** Section 14 explicitly permits optional time portions and
optional timezone designations. The specification's UNAVCO and IRIS examples
include timezone-free timestamps.

**Code at audit time:** the datetime converter required a timezone and a time
portion, then converted accepted values with `utc=True`.

**Reproduced at audit time:** Both `2011-08-18T00:00:00` and `2011-08-18` failed.

**Reconciliation:**

- [x] Preserve timezone-free timestamps as naive datetimes; do not assume UTC.
- [x] Accept timezone-free timestamps and date-only values.
- [x] Preserve explicit timezone offsets rather than converting source values
  to UTC. Mixed naive/aware or differently offset columns use object dtype so
  each timestamp retains its original timezone.
- [x] Revise the public API documentation for homogeneous and mixed datetime
  columns.
- [x] Test timezone-free timestamps, date-only values, explicit UTC, numeric
  offsets, and mixed representations.

**Resolution:** Implemented in 0.4.0. A date-only value is represented at
midnight with no timezone. Homogeneous timezone columns retain pandas datetime
dtypes; mixed representations retain individual `Timestamp` values in an
object column rather than converting timestamps or discarding timezone data.
Tests cover the timezone-free UNAVCO example form, a date-only value, explicit
UTC, a numeric offset, mixed naive/aware values, invalid calendar dates, and
the canonical P0006 timestamps. The full suite passes with 52 tests.

## 4. Optional or unknown field attributes are treated as mandatory

**Classification:** Direct specification mismatch.

**Specification:** Section 11 permits empty field-attribute values. The minimal
IRIS example also omits `field_type` and `field_unit` entirely.

**Code:** [Required declarations](/Users/jdsimon/programs/mermaid-geocsv/src/mermaid/geocsv/read.py:144)
requires both declarations to have nonempty values;
[type validation](/Users/jdsimon/programs/mermaid-geocsv/src/mermaid/geocsv/read.py:158)
rejects empty type entries.

**Reproduced:** Missing declarations, an unknown type for one column, and a
blank unit for a one-column dataset all fail.

**Reconciliation:**

- [x] Accept absent or empty `field_type` and `field_unit` declarations and
  entries.
- [x] Represent undeclared/empty field types as strings without guessing; keep
  empty source declarations in metadata so their absence remains visible.
- [x] Keep absent/empty units empty; do not invent units.
- [x] Reject unknown nonempty type names as unsupported while accepting empty
  entries within otherwise populated lists.
- [x] Test omitted declarations, empty one-column declarations, and partially
  undeclared field attributes.
- [x] Document the supported behavior and distinguish it from unknown type
  names.

**Resolution:** Implemented in 0.5.0. Only `dataset` is required before the
header. Missing or empty field types are represented as strings and recorded
as empty in `metadata.field_types`; missing or empty units remain empty in
`metadata.field_units`. Unknown nonempty type names still raise an error.

## 5. Dataset identity and placement are not checked

**Classification:** Validation gap; first-line placement is a recommendation.

**Specification:** Section 8 says the dataset marker should be first and
identify `GeoCSV 2.0`.

**Code at audit time:** [Dataset handling](/Users/jdsimon/programs/mermaid-geocsv/src/mermaid/geocsv/read.py:139)
accepts any nonempty value, anywhere before the header.

**Reproduced:** `#dataset: NOT_GEOCSV 93.7` is accepted, as is metadata preceding
the marker.

**Reconciliation:**

- [x] Require the dataset value to contain `GeoCSV`, case-insensitively.
- [ ] Recognize and validate supported GeoCSV versions; version validation is
  intentionally deferred while the dataset identity policy remains in flux.
- [x] Continue accepting unversioned `GeoCSV` for current MERMAID compatibility.
- [ ] Decide whether first-line placement is enforced or accepted permissively;
  the specification uses "should" here.
- [x] Test canonical/unversioned names, case-insensitive names, arbitrary
  version text, unsupported identifiers, and a marker preceded by metadata.

**Interim decision (open):** Accept any nonempty dataset value containing
`GeoCSV` in any letter case. Do not validate its version or require the marker
to be first. This keeps current MERMAID files readable while the package's
container/version policy remains in flux; revisit before declaring this finding
resolved or claiming full v2.0.4 compliance.

## 6. Changed metadata can bypass the required dataset boundary

**Classification:** Direct specification mismatch.

**Specification:** Section 3a distinguishes ordinary comments from recognized
GeoWS keyword declarations; section 5 defines declaration syntax, and section 7
lists the known keywords. Section 8 requires a new dataset marker when keyword
values change.

**Code at audit time:** schema tracking covered only delimiter, field type,
field unit, and field missing. Other known declarations became passive comments.

**Reproduced:** `#title: Before` followed by `#title: After`, or changed
`field_long_name` declarations, is accepted within one dataset.

**Reconciliation:**

- [x] Include an explicit lookup of known keywords in the pre-CSV comment and
  declaration parser, using section 7 of the pinned
  [GeoCSV v2.0.4 specification](docs/references/GeoCSV_v2.0.4.pdf) as the
  authority: `dataset`, `field_unit`, `field_type`, `field_long_name`,
  `field_standard_name`, `field_missing`, `delimiter`, `attribution`,
  `standard_name_cv`, `title`, `history`, `institution`, `source`, `comment`,
  and `references`. Keep this lookup local and versioned; a live URL lookup
  must not determine parsing behavior.
- [x] At record boundaries, classify literal leading-`#` lines as recognized
  declarations or ordinary comments before CSV parsing. Accept section 5's
  optional whitespace in forms such as `# known_keyword : value`; preserve
  unknown keyword/value comments and free-text comments without inferring
  scientific semantics. Lines inside multiline quoted CSV cells remain cell
  content.
- [x] Track the known declarations from section 7 and detect conflicting values.
- [x] Start a separate table at each `#dataset` marker so changed values apply
  only to the following dataset.
- [x] Preserve raw comments for diagnostics and traceability on each table.
- [x] Verify conflicting descriptive and field-attribute declarations, separately
  from identical repetitions and ordinary free-text comments.
- [x] Test padded known-keyword declarations, unknown keyword/value comments,
  and free-text comments before the header and between data records; verify
  raw metadata preservation and exclusion from source-record numbering.

**Resolution:** Multiple datasets are returned as separate DataFrames. Known
metadata changes are accepted only after a new dataset marker; identical
repetitions are accepted within a dataset.

## 7. Identical repeated declarations are rejected unnecessarily

**Classification:** Extra restriction.

**Specification:** Section 3b permits comments throughout the stream; section 8
requires a boundary for a change, not an identical repetition.

**Code:** [Declaration rejection](/Users/jdsimon/programs/mermaid-geocsv/src/mermaid/geocsv/read.py:135)
rejects repeated schema declarations regardless of whether their values agree.

**Reproduced:** Repeating `#field_type: string` fails. Repeating an unchanged
`field_unit` between records also fails.

**Reconciliation:**

- [x] Distinguish identical repetitions from conflicting declarations.
- [x] Accept identical repetitions and retain both source comments.
- [x] Accept identical known declarations before the header and between data
  records; changed values require a dataset boundary (finding 6).
- [x] Test identical declarations before the header and between data records,
  while retaining rejection of unmarked conflicting changes.

## 8. Whitespace normalization is incomplete for recognized metadata lists

**Classification:** Incomplete specification implementation.

**Specification:** Section 6 requires trimming each individual keyword value,
including list elements.

**Code at audit time:** [Comment parsing](/Users/jdsimon/programs/mermaid-geocsv/src/mermaid/geocsv/read.py:71)
trims the entire value; only the three explicitly parsed field declarations
receive per-element trimming.

**Reproduced:** `#field_long_name: first  ,  second` remains the parsed string
`"first  ,  second"`.

**Reconciliation:**

- [x] Keep `raw` unchanged.
- [x] Parse and trim individual values for recognized list-valued attributes
  such as `field_long_name` and `field_standard_name`.
- [x] Define how those parsed values are exposed without conflating the raw
  declaration with its list semantics.
- [x] Verify equivalent padded declarations produce equivalent parsed values
  while preserving their different raw source text.

**Resolution:** Immutable `metadata.field_long_names` and
`metadata.field_standard_names` map source column names to individually trimmed
values. `metadata.comments` still contains each raw declaration. Repeated
declarations compare their parsed values, so padding differences do not create
a false metadata change.

## 9. `nan` is reserved universally without that rule existing in this specification

**Classification:** Deliberate MERMAID policy.

**Specification:** Section 7f provides `field_missing` declarations. It does not
reserve every spelling of `nan`, particularly in string columns.

**Code:** [Missing-value conversion](/Users/jdsimon/programs/mermaid-geocsv/src/mermaid/geocsv/read.py:216)
overrides the source value and any declared sentinel.

**Reproduced:** A string `nan` becomes missing even when the declared missing
value is `ABSENT`.

**Reconciliation:**

- [x] Retain the universal MERMAID policy: case-insensitive `nan` is missing in
  every type, including strings, whether or not another sentinel is declared.
- [x] Honor each explicitly declared `field_missing` sentinel for its column.
- [x] Document this policy and its precedence over `field_missing` in the README.
- [x] Identify the proposed specification amendment in `TODO.md` as a proposal,
  not part of the existing standard.
- [x] Verify literal-string and explicit-sentinel behavior under the chosen
  policy, including case variants of `nan`.

**Resolution:** An empty cell, case-insensitive `nan`, or that column's
declared `field_missing` value is missing. Numeric and datetime cells are
trimmed before this check; string cells retain whitespace, so `" nan "` is
literal text. A nonempty whitespace-only cell remains an error in every type.

## 10. Empty and duplicate column names are rejected without a specification requirement

**Classification:** Extra restriction.

**Specification:** Section 4 recommends field names but does not require
nonempty, unique names. The referenced CSVW guidance places no constraints on
header titles:
[CSVW headers](https://www.w3.org/TR/2015/CR-tabular-data-model-20150716/#headers).

**Code:** [Header validation](/Users/jdsimon/programs/mermaid-geocsv/src/mermaid/geocsv/read.py:150)
imposes both requirements.

**Reconciliation:**

- [x] Retain and document nonempty, unique names as restrictions of this reader.
- [x] Preserve accepted source header spellings rather than inventing renamed
  columns.
- [x] Test empty and duplicate names under the chosen contract.

**Resolution:** Nonempty, unique names keep column data and field metadata
unambiguous under the documented name-keyed API. The specification does not
require this restriction.

## 11. "Strict" CSV parsing still accepts nonconforming quoting

**Classification:** Validation gap; accepting malformed input is distinct from
failing to read valid input.

**Specification:** Section 16 requires quoting values containing double quotes
and doubling quotes within quoted cells.

**Code at audit time:** [CSV parsing](/Users/jdsimon/programs/mermaid-geocsv/src/mermaid/geocsv/read.py:80)
relies on `csv.reader(strict=True)`.

**Reproduced:** `he"llo` is accepted unquoted. A space before `"hello"` is
accepted as literal data. Lone-CR record endings are also accepted although
section 3 specifies LF or CRLF.

**Reconciliation:**

- [x] Reject malformed CSV rather than repairing it.
- [x] Validate unquoted quotes and padding
  outside quoted cells while preserving multiline quoted cells.
- [x] Reject lone-CR line endings; accept LF and CRLF.
- [x] Verify malformed quotations alongside valid doubled quotes, embedded
  delimiters, and embedded LF/CRLF within quoted cells.

**Resolution:** A streaming quote check rejects malformed header/data cells
with a source line number. The parser also rejects lone-CR line endings on
comments, headers, and data. It does not alter the source to repair errors.

**Open edge case:** A final record without a line ending is still accepted.
Section 3 describes lines ending in LF or CRLF; decide whether an EOF-terminated
final record should also be rejected.

The quotation rule also appears in
[CSVW section 7.4](https://www.w3.org/TR/2015/CR-tabular-data-model-20150716/#lines).

## 12. Latitude/longitude recognition remains unsupported

**Classification:** Documented scope limit and recommendation gap.

**Specification:** Sections 8-9 support multiple self-contained datasets,
which the reader now returns as separate DataFrames. Section 15 recommends
recognizing the stated latitude/longitude naming patterns.

**Code:** [Dataset handling](/Users/jdsimon/programs/mermaid-geocsv/src/mermaid/geocsv/read.py)
parses each dataset in one file pass and preserves file-wide record indexes.
There is no coordinate-name recognition.

**Reconciliation:**

- [x] Return one DataFrame per dataset, each with its own metadata, while
  preserving file-wide data-record numbering.
- [x] Document that `geocsv.read` always returns a list, including for a
  single-dataset file.
- [x] Document latitude/longitude recognition as intentionally unimplemented.
- [x] Preserve source column spellings, coordinate values, and declared units
  without adding inferred coordinate roles or conversions.

**Resolution:** The reader leaves coordinate interpretation to code using the
DataFrame. This does not affect faithful parsing of source columns or metadata.

## 13. Typed conversion introduces additional scientific limitations

**Classification:** Data-integrity risks and representation limits beyond
explicit format rules.

**Code at audit time:** [Numeric conversion](/Users/jdsimon/programs/mermaid-geocsv/src/mermaid/geocsv/read.py:220)
and [datetime conversion](/Users/jdsimon/programs/mermaid-geocsv/src/mermaid/geocsv/read.py:186).

**Reproduced:**

- A finite `1e309` becomes infinity.
- A timestamp ending in `.123456789123Z` silently becomes `.123456789Z`.
- Padded integer ` 17 ` fails although padded floats succeed.
- Integers outside signed 64-bit range fail; that bound is the reader's dtype
  choice rather than an explicit GeoCSV integer bound.

**Reconciliation:**

- [x] Reject finite-value overflow explicitly instead of silently returning
  infinity.
- [x] Reject timestamp fractions longer than nine digits rather than silently
  truncating them.
- [x] Document numeric ranges and timestamp precision supported by the chosen
  pandas types.
- [x] Trim numeric and datetime cells before conversion; preserve whitespace
  in string cells, and reject whitespace-only cells in every type.
- [x] Verify overflow, supported/unsupported timestamp precision, integer range
  boundaries, and padded numeric values.

**Resolution:** Finite float overflow and nonzero values that underflow to zero
raise located errors; explicit infinity remains representable. Integers use
nullable signed Int64. Timestamps support at most nine fractional digits.
Broader numeric ranges and timestamp precision remain outside scope.
Pandas also accepts a space between date and time; the precision check covers
that spelling, but whether to accept it as GeoCSV ISO 8601 remains open.

## 14. Empty fields do not become typed missing values

**Classification:** Implementation gap against the agreed MERMAID missing-data
policy, identified after the original audit; not an explicit GeoCSV requirement.

**Observed:** Public-API probes with valid two-column records show that an empty
field, either unquoted or written as `""`, remains `""` in a string column and
raises `GeoCSVError` in integer, float, and datetime columns. Case-insensitive
`nan` already becomes a typed missing value.

**Agreed policy:** Enforce record width before converting fields. An explicitly
empty field and `nan` represent missing data in every declared type. A blank
line must not be expanded to match the header: a 16-column missing-data record
requires 16 cells (for example, 15 commas). Whitespace-only values such as
`" "` are errors for every declared type, including `string`; an empty field
encodes missing data. Whitespace-only `field_missing` sentinels are not
supported. This is distinct from the blank-record issue in finding 2 and padded
numeric conversion in finding 13.

**Reconciliation:**

- [x] Convert empty CSV fields, including quoted empty cells, to `pd.NA` for
  nullable string, integer, and float columns and `pd.NaT` for datetime columns.
- [x] Retain universal case-insensitive `nan` handling and explicit
  `field_missing` sentinel handling.
- [x] Enforce width before missing-value conversion; do not pad blank or short
  records with inferred cells.
- [x] Reject whitespace-only values in every type with errors identifying
  source field, line, and path.
- [x] Verify empty and quoted-empty fields across all four declared types,
  including a correctly sized all-empty record. Existing tests cover `nan` and
  declared sentinels; verify row count, dtypes, and source-record indices.
- [x] Document the empty-field policy and distinguish it from whitespace-only
  content; bump the package version.

**Resolution:** Implemented in 0.3.1. Empty and quoted-empty fields produce
`pd.NA` in nullable string, integer, and float columns and `pd.NaT` in datetime
columns. Nonempty whitespace-only fields raise a located error for every type.

## Verification and completion

At audit time, `.venv/bin/pytest -q` reported **29 passed**. Adversarial probes
used temporary files outside the repository and reproduced the observations
above. The existing tests establish current behavior; several explicitly
assert restrictions identified in this audit, so passing them does not
establish full specification compliance.

- [x] Record an explicit resolution for every finding: fix, accepted documented
  limitation, retained MERMAID policy, or deferred feature.
- [x] Replace existing test expectations where the chosen resolution changes the
  intended behavior.
- [x] Add focused specification examples and regression tests, prioritizing the
  two record-loss cases.
- [x] Run the relevant focused tests, then the full suite for implemented
  behavioral changes.
- [x] Verify the canonical P0006 data, dtypes, row alignment, source-record
  indices, and provenance after applicable changes.
- [x] Update README, tutorial, docstrings, and project instructions wherever
  public contracts or supported semantics change.
- [x] Bump the package to an appropriate pre-1.0 version for public behavior
  changes. This audit document alone does not require a version bump.
- [x] Keep version 1.0.0, tags, commits, pushes, and publication subject to the
  user's explicit instructions.

Current verification: version 0.7.0, 79 tests passed, including the canonical
P0006 checks. Finding 5's version and first-line placement decisions remain
explicitly open by prior agreement. The newly identified final-line and
space-separated datetime questions are recorded above.
