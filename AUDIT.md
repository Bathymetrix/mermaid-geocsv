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

All reconciliation checkboxes start unchecked. Checking a box means the stated
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

- [ ] Restrict legacy quoted-comment recognition to the preamble.
- [ ] After the header, recognize comments only by their literal leading `#`.
- [ ] Add regression examples for both quoted values and verify that the records
  and their `source_record_index` values are retained.
- [ ] Verify that the canonical MERMAID file's legacy quoted preamble and the
  existing multiline/two-column quoted-data examples still parse correctly.

## 2. Whitespace-only data records disappear

**Classification:** Definite bug.

**Specification:** Section 3c says lines without a leading `#` are delimited
data.

**Code:** [Blank-line handling](/Users/jdsimon/programs/mermaid-geocsv/src/mermaid/geocsv/read.py:127)
skips every whitespace-only line.

**Reproduced:** A one-column string record containing three spaces disappears,
changing both the number of records and subsequent `source_record_index`
values. Entirely empty lines are also skipped.

**Reconciliation:**

- [ ] Parse whitespace-only records instead of discarding them.
- [ ] Define how an entirely empty line represents an empty one-column cell.
- [ ] Reject incompatible record widths explicitly rather than silently skipping
  the record.
- [ ] Verify record counts and source-record indices for whitespace-only and
  empty records.

CSVW's parsing guidance also defaults to retaining blank rows:
[CSVW parsing guidance](https://www.w3.org/TR/2015/CR-tabular-data-model-20150716/#parsing).

## 3. Valid timezone-free datetimes and dates are rejected

**Classification:** Direct specification mismatch.

**Specification:** Section 14 explicitly permits optional time portions and
optional timezone designations. The specification's UNAVCO and IRIS examples
include timezone-free timestamps.

**Code:** [Timezone check](/Users/jdsimon/programs/mermaid-geocsv/src/mermaid/geocsv/read.py:229)
requires a timezone and a time portion.

**Reproduced:** Both `2011-08-18T00:00:00` and `2011-08-18` fail.

**Reconciliation:**

- [ ] Decide explicitly how unspecified timezones are represented: preserve naive
  datetimes unless source metadata establishes UTC, or choose another faithful,
  documented representation.
- [ ] Accept timezone-free timestamps and date-only values.
- [ ] Review the subsequent `utc=True` conversion. Merely deleting the timezone
  check would silently assume UTC for values whose timezone is unspecified.
- [ ] Revise the current "all datetimes are UTC" public contract and explain the
  behavior for columns containing different source representations.
- [ ] Test timezone-free timestamps, date-only values, explicit UTC, and numeric
  offsets, including examples from the specification.

## 4. Optional or unknown field attributes are treated as mandatory

**Classification:** Direct specification mismatch, or an intentional narrower
profile if retained and identified as such.

**Specification:** Section 11 permits empty field-attribute values. The minimal
IRIS example also omits `field_type` and `field_unit` entirely.

**Code:** [Required declarations](/Users/jdsimon/programs/mermaid-geocsv/src/mermaid/geocsv/read.py:144)
requires both declarations to have nonempty values;
[type validation](/Users/jdsimon/programs/mermaid-geocsv/src/mermaid/geocsv/read.py:158)
rejects empty type entries.

**Reproduced:** Missing declarations, an unknown type for one column, and a
blank unit for a one-column dataset all fail.

**Reconciliation:**

- [ ] Decide whether to support these permitted forms or retain mandatory
  declarations as a documented MERMAID profile requirement.
- [ ] If supporting them, preserve undeclared types as strings rather than
  guessing scientific types.
- [ ] Accept absent or empty units without inventing units.
- [ ] Distinguish unknown declarations from malformed declarations, including
  empty entries within otherwise populated lists.
- [ ] Test omitted declarations, empty single-column declarations, and partially
  unknown attribute lists.
- [ ] Ensure the documentation attributes any retained requirement to the
  MERMAID profile, not to GeoCSV itself.

## 5. Dataset identity and placement are not checked

**Classification:** Validation gap; first-line placement is a recommendation.

**Specification:** Section 8 says the dataset marker should be first and
identify `GeoCSV 2.0`.

**Code:** [Dataset handling](/Users/jdsimon/programs/mermaid-geocsv/src/mermaid/geocsv/read.py:139)
accepts any nonempty value, anywhere before the header.

**Reproduced:** `#dataset: NOT_GEOCSV 93.7` is accepted, as is metadata preceding
the marker.

**Reconciliation:**

- [ ] Recognize `GeoCSV 2.0` explicitly.
- [ ] Retain the existing unversioned `GeoCSV` spelling only as a documented
  legacy MERMAID exception, if that compatibility is desired.
- [ ] Reject unsupported container identities and versions with a clear error.
- [ ] Decide whether first-line placement is enforced or accepted permissively;
  the specification uses "should" here.
- [ ] Test canonical, legacy, unsupported, and misplaced dataset markers.

## 6. Changed metadata can bypass the required dataset boundary

**Classification:** Direct specification mismatch.

**Specification:** Section 8 requires a new dataset marker when keyword values
change.

**Code:** [Schema tracking](/Users/jdsimon/programs/mermaid-geocsv/src/mermaid/geocsv/read.py:21)
covers only four keys. Other known declarations become passive comments.

**Reproduced:** `#title: Before` followed by `#title: After`, or changed
`field_long_name` declarations, is accepted within one dataset.

**Reconciliation:**

- [ ] Track the known declarations from section 7 and detect conflicting values.
- [ ] Until multiple datasets are supported, reject such changes with an
  explanation that a dataset boundary is required.
- [ ] Preserve raw comments for diagnostics and traceability.
- [ ] Verify conflicting descriptive and field-attribute declarations, separately
  from identical repetitions and ordinary free-text comments.

## 7. Identical repeated declarations are rejected unnecessarily

**Classification:** Extra restriction.

**Specification:** Section 3b permits comments throughout the stream; section 8
requires a boundary for a change, not an identical repetition.

**Code:** [Declaration rejection](/Users/jdsimon/programs/mermaid-geocsv/src/mermaid/geocsv/read.py:135)
rejects repeated schema declarations regardless of whether their values agree.

**Reproduced:** Repeating `#field_type: string` fails. Repeating an unchanged
`field_unit` between records also fails.

**Reconciliation:**

- [ ] Distinguish identical repetitions from conflicting declarations.
- [ ] Accept identical repetitions and retain both source comments.
- [ ] Separately document or remove the restriction that declarations must
  precede the header.
- [ ] Test identical declarations before the header and between data records,
  while retaining rejection of unmarked conflicting changes.

## 8. Whitespace normalization is incomplete for recognized metadata lists

**Classification:** Incomplete specification implementation.

**Specification:** Section 6 requires trimming each individual keyword value,
including list elements.

**Code:** [Comment parsing](/Users/jdsimon/programs/mermaid-geocsv/src/mermaid/geocsv/read.py:71)
trims the entire value; only the three explicitly parsed field declarations
receive per-element trimming.

**Reproduced:** `#field_long_name: first  ,  second` remains the parsed string
`"first  ,  second"`.

**Reconciliation:**

- [ ] Keep `raw` unchanged.
- [ ] Parse and trim individual values for recognized list-valued attributes
  such as `field_long_name` and `field_standard_name`.
- [ ] Define how those parsed values are exposed without conflating the raw
  declaration with its list semantics.
- [ ] Verify equivalent padded declarations produce equivalent parsed values
  while preserving their different raw source text.

Raw preservation alone does not implement list-value semantics.

## 9. `nan` is reserved universally without that rule existing in this specification

**Classification:** Deliberate MERMAID policy.

**Specification:** Section 7f provides `field_missing` declarations. It does not
reserve every spelling of `nan`, particularly in string columns.

**Code:** [Missing-value conversion](/Users/jdsimon/programs/mermaid-geocsv/src/mermaid/geocsv/read.py:216)
overrides the source value and any declared sentinel.

**Reproduced:** A string `nan` becomes missing even when the declared missing
value is `ABSENT`.

**Reconciliation:**

- [ ] Record the choice between general GeoCSV sentinel behavior and the already
  approved universal MERMAID policy.
- [ ] For general GeoCSV behavior, honor declared sentinels and preserve other
  strings; the writer can explicitly declare `nan` as a missing value.
- [ ] If retaining the universal policy, document it as a MERMAID convention and
  explain its precedence over `field_missing`.
- [ ] Identify the proposed specification amendment in `TODO.md` as a proposal,
  not part of the existing standard.
- [ ] Verify literal-string and explicit-sentinel behavior under the chosen
  policy, including case variants of `nan`.

## 10. Empty and duplicate column names are rejected without a specification requirement

**Classification:** Extra restriction.

**Specification:** Section 4 recommends field names but does not require
nonempty, unique names. The referenced CSVW guidance places no constraints on
header titles:
[CSVW headers](https://www.w3.org/TR/2015/CR-tabular-data-model-20150716/#headers).

**Code:** [Header validation](/Users/jdsimon/programs/mermaid-geocsv/src/mermaid/geocsv/read.py:150)
imposes both requirements.

**Reconciliation:**

- [ ] Decide whether to document nonempty, unique names as restrictions of this
  reader or support those columns positionally.
- [ ] If supporting duplicate names, replace name-keyed column storage and
  resolve metadata alignment by position before removing the guard.
- [ ] Preserve source header spellings rather than inventing renamed columns.
- [ ] Test empty and duplicate names under the chosen contract.

Removing the check alone would collapse duplicate columns in the current
dictionaries and make metadata mappings ambiguous.

## 11. "Strict" CSV parsing still accepts nonconforming quoting

**Classification:** Validation gap; accepting malformed input is distinct from
failing to read valid input.

**Specification:** Section 16 requires quoting values containing double quotes
and doubling quotes within quoted cells.

**Code:** [CSV parsing](/Users/jdsimon/programs/mermaid-geocsv/src/mermaid/geocsv/read.py:80)
relies on `csv.reader(strict=True)`.

**Reproduced:** `he"llo` is accepted unquoted. A space before `"hello"` is
accepted as literal data. Lone-CR record endings are also accepted although
section 3 specifies LF or CRLF.

**Reconciliation:**

- [ ] Decide whether the reader promises strict validation or intentionally
  accepts additional syntax.
- [ ] If strict validation is intended, validate unquoted quotes and padding
  outside quoted cells while preserving multiline quoted cells.
- [ ] Explicitly enforce or document acceptance of lone-CR record endings.
- [ ] If permissive parsing is retained, document the accepted syntax and narrow
  the claim that malformed input raises an error.
- [ ] Verify malformed quotations alongside valid doubled quotes, embedded
  delimiters, and embedded LF/CRLF within quoted cells.

The quotation rule also appears in
[CSVW section 7.4](https://www.w3.org/TR/2015/CR-tabular-data-model-20150716/#lines).

## 12. Multiple datasets and latitude/longitude recognition remain unsupported

**Classification:** Documented scope limit and recommendation gap.

**Specification:** Sections 8-9 support multiple self-contained datasets.
Section 15 recommends recognizing the stated latitude/longitude naming
patterns.

**Code:** [Dataset handling](/Users/jdsimon/programs/mermaid-geocsv/src/mermaid/geocsv/read.py:133)
rejects additional sections; there is no coordinate-name recognition.

**Reconciliation:**

- [ ] Keep the deliberate single-dataset scope clearly identified as a subset
  of GeoCSV support, with explicit rejection of additional sections.
- [ ] Record multiple-dataset support as deferred, consistent with the agreed
  scope; this audit does not require implementing it now.
- [ ] Before future support, decide the public return structure for separate
  tables and metadata, preserving the agreed file-wide record numbering.
- [ ] Document latitude/longitude recognition as an unimplemented recommendation
  if it remains downstream.
- [ ] If recognition is implemented later, preserve column spellings and avoid
  coordinate transformations or inferred scientific units.

Neither issue requires renaming columns or transforming coordinates.

## 13. Typed conversion introduces additional scientific limitations

**Classification:** Data-integrity risks and representation limits beyond
explicit format rules.

**Code:** [Numeric conversion](/Users/jdsimon/programs/mermaid-geocsv/src/mermaid/geocsv/read.py:220)
and [datetime conversion](/Users/jdsimon/programs/mermaid-geocsv/src/mermaid/geocsv/read.py:186).

**Reproduced:**

- A finite `1e309` becomes infinity.
- A timestamp ending in `.123456789123Z` silently becomes `.123456789Z`.
- Padded integer ` 17 ` fails although padded floats succeed.
- Integers outside signed 64-bit range fail; that bound is the reader's dtype
  choice rather than an explicit GeoCSV integer bound.

**Reconciliation:**

- [ ] Reject finite-value overflow explicitly instead of silently returning
  infinity.
- [ ] Reject unsupported timestamp precision explicitly instead of silently
  truncating it, or adopt a representation that faithfully retains it.
- [ ] Document numeric ranges and timestamp precision supported by the chosen
  pandas types.
- [ ] Apply a deliberate, consistent whitespace policy before numeric conversion.
- [ ] Verify overflow, supported/unsupported timestamp precision, integer range
  boundaries, and padded numeric values.

Full support for broader ranges can remain outside scope, provided errors and
limits are clear.

## Verification and completion

At audit time, `.venv/bin/pytest -q` reported **29 passed**. Adversarial probes
used temporary files outside the repository and reproduced the observations
above. The existing tests establish current behavior; several explicitly
assert restrictions identified in this audit, so passing them does not
establish full specification compliance.

- [ ] Record an explicit resolution for every finding: fix, accepted documented
  limitation, retained MERMAID policy, or deferred feature.
- [ ] Replace existing test expectations where the chosen resolution changes the
  intended behavior.
- [ ] Add focused specification examples and regression tests, prioritizing the
  two record-loss cases.
- [ ] Run the relevant focused tests, then the full suite for implemented
  behavioral changes.
- [ ] Verify the canonical P0006 data, dtypes, row alignment, source-record
  indices, and provenance after applicable changes.
- [ ] Update README, tutorial, docstrings, and project instructions wherever
  public contracts or supported semantics change.
- [ ] Bump the package to an appropriate pre-1.0 version for public behavior
  changes. This audit document alone does not require a version bump.
- [ ] Keep version 1.0.0, tags, commits, pushes, and publication subject to the
  user's explicit instructions.
