# Open GeoCSV and association questions

Format questions reviewed 2026-10-07 with reader version 0.10.2. Association
questions consolidated from the sandbox notes on 2026-10-19. The questions
remain open; descriptions of settled behavior provide context.

This document collects format questions raised while implementing the reader
and separate scientific questions about waveform association.
The [reader specification](READER_SPEC.md) describes what this package does
today; the format behavior below is provisional where the
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

**Current reader behavior:** Empty fields, including `""`, are missing except
in a string-valued column named exactly `Location`, where they represent the
known empty SEED location code. Case-insensitive `nan` is **always missing**,
including for string fields and even with a
different declared `field_missing` value; a declared `field_missing` value is
also missing. Literal `nan` and quoted `"nan"` cannot be represented as string
values; empty strings can be represented only in string-valued `Location`.
Datetime fields additionally treat
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

## MERMAID sampling-rate follow-up

Added 2026-10-08 during ObsPy association planning. This is a scientific-data
follow-up, separate from the GeoCSV specification questions above.

The user reports that raw MER files quote sampling timing at microsecond
precision, but its trustworthiness is uncertain. At the start of association
planning, the supplied GeoCSV output used single-decimal sampling rates,
including integer-valued rates where measured rates were intended. Establish
the precise raw quantity, units, and encoding before treating that precision
as reliable.

The rebuilt processed snapshot later supplied measured rates to six decimal
places; differences from MiniSEED are below 0.000002 Hz in the 18 sampled
waveforms. This addresses the formatting concern for those outputs, not the
broader raw-MER/writer/ObsPy precision question. See the
[fixture audit](../data/fixtures/association/README.md).

Compare raw MER sampling information, the writer's input and serialized
GeoCSV output, encoded MiniSEED rates, and ObsPy reader output. In particular,
verify whether ObsPy changes the rate slightly or simply exposes an already
different encoded rate. Separate upstream formatting loss from reader
conversion and from nominal-versus-measured sampling.

Since 0.22.0 the public associator requires source rates within inclusive
floating-point endpoint bounds of `waveform_rate +/- 0.00001` Hz. This replaces
the former provisional 0.01 Hz check after successful fresh-source verification
of 22 originals and three windows across 15 full histories. The largest observed
original-segment rate difference was approximately 0.000001296 Hz. This is a
bounded compatibility criterion, not instrument accuracy or proof that sampling
grids coincide. Raw-MER/encoding investigations beyond that checked sample
remain separate scientific work. See [audit 06](../audits/06.md).

`geocsv.read` continues to parse the supplied value faithfully. Upstream
writer corrections are outside this project; neither rounding downloaded
rates nor silently normalizing parsed rates is authorized. See the
[association discussion](OBSPY_ASSOCIATION.md#matching-original-traces) and
[association questions below](#association-scientific-questions).

## Association scientific questions

These questions replace the former `sandbox/obspy_association/OPEN_QUESTIONS.md`
TBD list. Preserve the distinction between dated evidence, current matching
rules, and unresolved interpretation. The public API and initial attachment
rules are settled in the [association tutorial](tutorials/ASSOCIATE.md);
Geographic SAC export is implemented separately in
[`write_sac`](tutorials/WRITE_SAC.md); broader transformed-waveform support
remains [planned work](FUTURE.md#associate-transformed-archive-waveforms).

### Archive segmentation and request boundaries

When original acquisitions share SNCL, which boundaries survive a month/year
request? Can a service split an acquisition, combine several, omit edge
samples, or include neighboring acquisitions? Does partitioning a long window
into short requests change the returned samples or trace boundaries?

Distinguish archive/server operations, MiniSEED record assembly, and ObsPy's
client-side trimming. An individual MiniSEED record's start time does not by
itself define a contiguous acquisition. The dated month probe includes a
one-sample trace and apparently combined coverage; it does not establish a
general service policy or completeness. The year-long probe has not been
executed in the recorded observations. See the
[retrieval evidence](OBSPY_RETRIEVAL_OBSERVATIONS.md#month-request) and the
[exploratory scripts](../sandbox/obspy_association/README.md).

### Overlapping sample values and acquisition lineage

Which source samples survive overlapping acquisitions, and can original
contributions be recovered after archive transformations? Exact source-grid
coverage does not identify the source of each sample value or detect gaps
already filled upstream. The implemented first-segment fallback adopts one
location anchor without claiming that reconstruction. See the
[merged-trace policy](OBSPY_MERGED_TRACES.md).

DET Q and REQ D are useful lineage evidence independent of sampling rate.
The recorded P0006 service responses expose M for both; M alone does not
prove that a trace combines acquisitions. The dated
[quality/archive discussion](OBSPY_RETRIEVAL_OBSERVATIONS.md#short-requests)
records the then-consulted service documentation. Recheck returned indicators
and overlap selection if MERMAID data are reingested or service behavior
changes, before proposing quality-based validation or precedence rules.
The current associator retains GeoCSV and waveform quality independently
and does not filter matches by equality.

### Timing across producers and instrument generations

How do raw timing, serialized GeoCSV starts, waveform headers, and physical
clock accuracy relate across producers and instrument generations? The user
clarifies that the current waveform clock does not have millisecond timing
precision; stored fractional digits do not establish physical accuracy.
Preserve the downloaded timing and measured rate. A rate calculated from
ObsPy's rate-derived endtime would not provide independent timing evidence.

The public absolute start/containment default is a fixed 1 ms tolerance, with
an explicit seconds override; source lexical resolution never enlarges it.
The checked fresh histories fit this default. Half-sample coverage placement
is independent of that absolute tolerance. The retrieval
scripts' one-second margin is unrelated to this matching tolerance. Revisit
other producers using independent evidence, including the separate
[sampling-rate investigation](#mermaid-sampling-rate-follow-up), rather than
rounding, snapping, or overriding scientific metadata.

### Original product classification and raw-buffer distinctions

The rebuilt processed inventory and 18 paired fixtures establish DET Q / REQ D
consistency with the documented SNCL mapping. The remaining source-MER check
is to verify the DET.WLT2 event classification and scale before processing;
the inventory audit did not independently inspect every raw MER header.
Historical location codes, including an older WLT2 location 01 versus current
helper location 10, must remain source evidence rather than be relabeled.

Keep `.REQ.RAW` event products (quality D, roughly 40 Hz) distinct from the
physically recovered continuous buffer stream (quality R, location 20 in the
supplied mapping). The filename token RAW alone establishes neither R nor
location 20. Instrument-generation timing claims, raw-buffer rates, and
citations still need the verification listed in the
[data-quality reference](MERMAID_DATA_QUALITY.md#items-to-verify-before-treating-this-as-a-formal-specification).

### Partial and transformed acquisitions

How should trimmed, split, or resampled inputs be recognized and related to
their original acquisitions without guessing? The current public associator
targets original MiniSEED-derived segments plus the explicit containing-anchor
fallback for clipped/combined windows. The fallback still requires full source
sample coverage after clipping. Geographic SAC export of either label is
supported under the user's negligible-drift convention; resampling and original
sample-contribution reconstruction remain outside this decision. It rejects zero/multiple eligible matches; it does not use quality
to select a candidate or combine competing metadata rows.

The [original July 13 inspection](OBSPY_RETRIEVAL_OBSERVATIONS.md#original-july-13-waveforms-2026-10-15)
established that three repeated REQ waveforms have equal sample arrays,
starts, rates, and counts and share one source row. This supports multiple
traces independently using one row; it does not establish a transformed-input
or archive-reconstruction policy. GeoCSV SampleCount already represents NPTS;
no extra source count column is required. The nested report field
`association.waveform.sample_count` records the downloaded window's count for export checks.
Position remains the interpolated receiver position at the source segment's
first sample time, adopted for a clipped/combined window under the MERMAID
negligible-drift convention, independent of duration or request date.

Package promotion, fresh destinations, source preflight, batch validation,
and per-call SNCL/time indexing are implemented rather than pending research
questions. No future reconstruction policy should silently change those
rules. Planned functionality belongs in [future workflows](FUTURE.md).
