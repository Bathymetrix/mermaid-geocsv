# Open GeoCSV questions

Reviewed 2026-10-07 with reader version 0.10.2. All questions below are open.

This document collects format questions raised while implementing the reader.
The [reader specification](READER_SPEC.md) describes what this package does
today; the behavior below is provisional where the
[GeoCSV v2.0.4 specification](references/GeoCSV_v2.0.4.pdf) is silent or does
not settle interoperability. An open question here is not a claim that the
current reader is correct for every GeoCSV producer.

Keep format questions separate from Python API choices. When a clarification
becomes authoritative, record its source and version here, then reconcile the
reader specification, tests, and behavior as needed. The audits provide the
evidence and history; this page tracks the questions in one place.

## Questions for the GeoCSV specification

### 1. Do custom keyword lines define dataset-wide metadata?

**Question:** Sections 3, 5, 7, and 8 distinguish comments from known keywords
and require a new `#dataset` marker when a keyword value changes. Does that
boundary rule also apply to custom `#key: value` lines such as
`#GeodeticDatum: WGS84`? How should ordinary free-text comments be
distinguished from custom declarations?

**Row-varying alternative:** Should GeoCSV allow a custom key's value to change
between records within one dataset? If so, does each value apply to following
records until the next change, and how are records before the first value
interpreted? pandas [`DataFrame.attrs`](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.attrs.html)
holds metadata for the whole table, so the current reader cannot express that
association there. A future reader could create an explicit per-record column,
but that would change the public table schema and needs a specified rule for
which custom keys have row-level meaning.

**Current reader behavior:** It preserves every leading-`#` comment with its
line number. Known declarations cannot be added or changed after the header.
For any unknown `#key: value` line, the first occurrence may appear before or
after the header, but a changed repetition after the header requires a new
`#dataset` marker. Repetitions with different values before the header are
retained; the last value becomes the comparison baseline. Free-text comments
remain unrestricted. See
[Audit 04, finding 1](../audits/04.md#1-changed-custom-scientific-metadata-can-span-one-table).

**Clarification needed:** State which custom declarations have dataset scope
and how their names and changes are recognized. Decide whether any custom
declarations may instead vary by record, and define their inheritance rule if
so. The changed-value rule is a provisional reader policy, not a general rule
supplied by v2.0.4.

### 2. What is the exact grammar of `field_*` lists?

**Question:** Must every present `field_*` declaration contain exactly one
entry per header field, including explicit empty entries? Does `#delimiter`
also delimit metadata lists? How are embedded delimiters, quotes, and empty
first or last entries represented when the delimiter is a space or tab?

**Current reader behavior:** It requires exactly one entry per header field,
uses the declared data delimiter for these lists, accepts double-quoted list
values, and requires `""` for an empty edge entry with a whitespace delimiter.
It rejects the printed IRIS and R2R examples because their `field_unit` and
`field_type` lists, respectively, are shorter than the headers. The R2R
`field_long_name` example also contains an unquoted comma. See
[Audit 03](../audits/03.md) and
[Audit 02, finding F3](../audits/02.md#f3--p2-trimming-a-declaration-destroys-edge-entries-with-whitespace-delimiters).

**Clarification needed:** Specify list width, separator, quoting, and empty
entry rules, and correct or explain the inconsistent printed examples.

### 3. Which source values mean missing data?

**Question:** Section 7 defines `field_missing` but does not say whether empty
fields, quoted empty strings, `nan`, or `NaT` have default missing meanings.
How can a string field represent a literal `nan` or empty string when those
tokens also denote missing data?

**Current reader behavior:** Empty fields, including `""`, and case-insensitive
`nan` are **always missing**, including for string fields and even with a
different declared `field_missing` value; a declared `field_missing` value is
also missing. Literal `nan`, quoted `"nan"`, and quoted empty strings cannot be
represented as string values. Datetime fields additionally treat
case-insensitive `NaT` as missing. Universal `nan` handling is an explicit
MERMAID policy, not a v2.0.4 requirement. See
[Audit 04, finding 3](../audits/04.md#3-universal-nan-handling-can-erase-literal-string-data)
and [the reader's missing-value rules](READER_SPEC.md#supported-geocsv-semantics).

**Clarification needed:** Define default missing tokens, the precedence of
`field_missing`, and a source representation for literal string values if
tokens are reserved.

### 4. Does a datetime unit establish its timezone?

**Question:** The specification permits timestamps without timezone
designators, while its UNAVCO example declares `UTC` in `field_unit` for two
such columns. Does that unit determine the timestamps' timezone, or is it
descriptive metadata only?

**Current reader behavior:** It preserves the `UTC` unit declaration and
leaves those source timestamps timezone-naive; it does not infer a timezone
from metadata. See [Audit 03](../audits/03.md).

**Clarification needed:** State whether a datetime unit can supply timezone
semantics and which declaration takes precedence when a timestamp has an
explicit offset.

### 5. Which ISO 8601 datetime forms must readers support?

**Question:** Section 14 requires ISO 8601, recommends one extended calendar
form, and makes the time and timezone optional. It does not enumerate required
date forms, offset spellings, fractional precision, or representable range.

**Current reader behavior:** It accepts the documented extended calendar-date
subset with optional time and timezone, up to nine fractional-second digits.
It rejects other ISO 8601 forms rather than silently normalizing them. See
[the reader's datetime rules](READER_SPEC.md#supported-geocsv-semantics) and
[Audit 02, finding F4](../audits/02.md#f4--p2-formatiso8601-does-not-enforce-the-advertised-datetime-syntax).

**Clarification needed:** Publish an interoperable datetime profile and state
what a reader should do with valid ISO 8601 forms outside that profile.

### 6. How should container versions be recognized?

**Question:** Section 8 says the `#dataset` value should identify the
container type and version and gives `GeoCSV 2.0`. What version syntax and
forward-compatibility rule should readers use for later versions? How should
existing unversioned MERMAID declarations be identified?

**Current reader behavior:** It accepts any nonempty dataset value containing
`GeoCSV` without validating a version, and allows preceding comments for
MERMAID compatibility. The latter is a documented exception to section 8's
first-line recommendation, not an unresolved point in that text. See
[Audit 04, finding 5](../audits/04.md#5-future-geocsv-versions-may-be-parsed-under-current-rules)
and [Audit 01, finding 5](../audits/01.md#5-dataset-identity-and-placement-are-not-checked).

**Clarification needed:** Define version syntax and forward-compatibility
rules. The reader still needs a separate compatibility decision for existing
unversioned MERMAID files. Version validation remains open; the reader
continues to accept unrecognized future-looking GeoCSV version strings.
