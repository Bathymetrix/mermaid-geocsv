# Adversarial read-only audit of mermaid-geocsv

Reviewed 2026-10-06, package **0.7.2**, commit
`890fb0bf02e62d35ea57b01ca31559a5817c2a2c`.

## Assessment

**Five confirmed findings: one P1, three P2, and one P3.** The strongest
finding is silent timestamp truncation despite an explicit promise to reject
excess precision. Successful parsing is also too permissive about datetime
syntax and undocumented missing tokens. Optional metadata entries do not
compose reliably with supported whitespace delimiters.

The existing suite passes on the repository's pandas 3.0.6 environment, but
has one failure on supported pandas 2.2.3. Ordinary CSV framing, source-record
ordering, immutable metadata, and canonical MERMAID data passed the checks
described below. These results do not establish complete format conformance.

P1 means a high-priority scientific-integrity defect; P2 means a correctness
or public-contract defect; P3 means a lower-priority verification or
documentation defect. No P0 defect was established.

## Method and independence

I read the applicable AGENTS instructions, parser, metadata implementation,
public documentation, tests, fixtures, and bundled specification before
opening either previous report. I used the local automaid writer and legacy
MATLAB reader as behavioral references, without executing or changing them.

I recorded all five independent conclusions in a temporary checkpoint before
reading `AUDIT.md` or `FINDINGS.md`. The comparison below came afterward.
Additional confirmation probes and packaging checks did not change the list
of findings.

All Python commands used this repository's `.venv/bin/python`. Bytecode and
pytest cache writes were disabled; test files and build work went under
`/private/tmp`. For dependency comparison, pandas 2.2.3 and its required pytz
package were extracted from downloaded wheels into a temporary import
overlay. The repository's virtual environment was not modified. Build tools
were similarly extracted into a temporary overlay, and packaging used a
temporary copy of the source. The **only repository addition is this report**;
existing code, tests, fixtures, documentation, and Git history were unchanged.

## Findings

### F1 — [P1] Single-digit time components bypass the precision guard

**Location:** [`read.py:45`](src/mermaid/geocsv/read.py#L45),
[`read.py:440–443`](src/mermaid/geocsv/read.py#L440), and datetime assembly at
[`read.py:240`](src/mermaid/geocsv/read.py#L240).

**Reproducer:** Read this complete LF-terminated file:

```text
#dataset: GeoCSV
#field_type: datetime
Time
2025-01-01T1:00:00.123456789012
```

**Observed on pandas 3.0.6 and 2.2.3:** The read succeeds and returns
`Timestamp('2025-01-01 01:00:00.123456789')`. The source fraction has twelve
digits; the result keeps nine. Single-digit minutes or seconds also bypass
the guard, for example `2025-01-01T12:1:00.123456789012` and
`2025-01-01T12:00:1.123456789012`.

**Cause:** `_TIME_FRACTION` assumes two-digit time components. Pandas accepts
the nonpadded forms anyway, so an unmatched fraction reaches pandas without
the length check. `errors="raise"` does not prevent fractional truncation.

**Expected:** Reject the malformed timestamp, or at minimum reject its
unsupported precision. README lines 145–150 explicitly promise rejection
rather than silent change. The non-ISO spelling does not exempt it from that
promise: it should fail validation, not produce an apparently valid time.

**Impact:** Scientific timing changes silently, and distinct source values
can collapse to the same timestamp. The returned table does not retain raw
data-cell text from which to recover the lost digits.

**Recommended correction:** Validate supported datetime syntax and fractional
precision before pandas conversion. The precision check must cover every
form that is allowed to reach pandas. Add a small regression covering
nonpadded components and excess precision alongside the existing valid
nine-digit case. Merely extending the current regex does not resolve F4.

### F2 — [P2] Undeclared `NaT` tokens silently become missing timestamps

**Location:** [`read.py:418–419`](src/mermaid/geocsv/read.py#L418) and
[`read.py:234–247`](src/mermaid/geocsv/read.py#L234).

**Reproducer:**

```text
#dataset: GeoCSV
#field_type: datetime
#field_missing: ABSENT
Time
NaT
```

**Observed on both tested pandas versions:** The value becomes `pd.NaT`.
`nat` and `NAT` also become missing without a declaration. String columns
retain these tokens, while integer and float columns reject them.

**Expected:** `GeoCSVError`, because this token is neither a datetime nor one
of the documented missing markers. If `field_missing` explicitly declares
`NaT`, accepting it as missing is appropriate.

**Cause:** The reader's own missing check recognizes empty values, `nan`, and
the declared sentinel, then passes other datetime strings through to pandas.
Pandas independently recognizes `NaT`, even with `errors="raise"`.

**Impact:** Malformed source data is silently replaced by missing data under a
type-specific policy absent from the README and previous reconciliation.
The source token is not retained in the parsed table.

**Recommended correction:** Prevent undeclared datetime strings from becoming
missing during conversion; preserve the explicit-sentinel path. Test undeclared
and explicitly declared `NaT` separately. Do not broaden the universal missing
policy accidentally through pandas behavior.

### F3 — [P2] Trimming a declaration destroys edge entries with whitespace delimiters

**Location:** [`read.py:94–99`](src/mermaid/geocsv/read.py#L94), before
[`read.py:153–198`](src/mermaid/geocsv/read.py#L153) splits field attributes.

**Reproducer:** In the following Python string, the `\t` inside the delimiter
declaration is literal backslash-plus-`t`; the other tabs are actual separators:

```python
text = (
    "#dataset: GeoCSV\n"
    "#delimiter: \\t\n"
    "#field_type:\tinteger\n"
    "A\tB\n"
    "x\t1\n"
)
```

**Observed on both tested versions:**
`GeoCSVError: line 3: field_type has 1 fields; header has 2`.
Trailing empty entries (`string\t`), two empty entries (`\t`), and analogous
space-delimited declarations fail as well. Interior empty entries, such as
`string\t\tinteger`, survive.

**Cause:** `_comment` strips all surrounding whitespace from the complete
declaration value before its delimiter is interpreted. This erases tabs or
spaces that encode empty edge entries. The same operation affects units,
missing sentinels, and other supported field-attribute lists. The raw comment
is preserved, but the operational declaration is already altered.

**Expected under the reader's list contract:** Retain explicit empty entries
and enforce the actual column alignment. README lines 107–110 require one
entry per column; lines 125–128 accept empty types and units. Whitespace
delimiters are supported and have no documented exception to this contract.

**Qualification:** The specification requires whitespace padding to be trimmed
but does not fully define metadata-list quoting or how padding is distinguished
from a whitespace separator. This is an implementation/public-contract gap,
not proof that the specification resolves every ambiguous spelling. For
example, `#field_unit:\tmeters\tseconds` is accepted for a two-column header
after the leading tab is removed; whether that tab was padding or an empty
first entry is lost during operational parsing.

**Impact:** Some empty per-column declarations cannot be represented using the
same unquoted separator convention that works for commas. Ambiguous edge
whitespace can also conceal intended metadata alignment.

**Recommended correction:** Define a delimiter-aware policy for padding and
empty entries, preserve separators until the list is parsed, and document
any necessary restriction for whitespace delimiters. Quoting an empty entry
as `""` currently works and is a practical workaround. Focus tests on leading
and trailing empty entries with tab and space delimiters.

### F4 — [P2] `format="ISO8601"` does not enforce the advertised datetime syntax

**Location:** [`read.py:440–443`](src/mermaid/geocsv/read.py#L440) and
[`read.py:240–247`](src/mermaid/geocsv/read.py#L240).

**Reproducer:** Use the same three-line preamble/header as F1, with any of the
following data values:

| Source value | Observed result on both tested versions |
| --- | --- |
| `2025/01/01` | `2025-01-01 00:00:00` |
| `2025.01.01` | `2025-01-01 00:00:00` |
| `2025-1-1` | `2025-01-01 00:00:00` |
| `2025-01-01T12:00:00+1` | `2025-01-01 12:00:00+01:00` |
| `2025-01-01T12:00:00+013` | `2025-01-01 12:00:00+01:03` |

**Expected:** Reject these non-ISO representations with a located
`GeoCSVError`. GeoCSV section 14 and README lines 145–148 require ISO 8601,
with a documented exception for a space between date and time. The
[W3C ISO 8601 profile](https://www.w3.org/TR/NOTE-datetime) provides supporting
examples of fixed-width calendar and time-offset syntax; it is a profile,
not the complete ISO standard.

**Cause:** Apart from the fraction-length guard, datetime lexical validation
is delegated to pandas. Its format label does not establish strict input
conformance in the observed implementation.

**Impact:** Invalid dates and offset spellings are normalized into credible
timestamps. A malformed offset can be assigned a meaning the source did not
express unambiguously. This is a validation defect distinct from F1's actual
precision loss.

**Recommended correction:** State and validate the supported ISO 8601 forms
explicitly, retaining the documented space exception. Do not infer strict
conformance from the pandas argument name. Keep rejection tests narrow and
ensure valid date-only, basic/extended forms selected for support, offsets,
and nine-digit fractions retain their intended behavior.

### F5 — [P3] A test and tutorial assume pandas 3's datetime storage resolution

**Location:** [`tests/test_read.py:422`](tests/test_read.py#L422),
[`TUTORIAL.md:69–71`](TUTORIAL.md#L69), and the declared dependency
[`pyproject.toml:25`](pyproject.toml#L25).

**Reproducer:** Run the existing 94-test suite with pandas 2.2.3, which satisfies
`pandas>=2.2`.

**Observed:** **93 passed, 1 failed, 5 FutureWarnings.** The failure is
`test_optional_field_type_and_unit_declarations`: the parsed dtype is
`datetime64[ns]`, but the assertion requires `datetime64[us]`.
The tutorial also describes P0006's timezone-aware dtype as specifically
`datetime64[us, UTC]`; pandas 2.2.3 uses nanosecond storage.

**Expected:** Verify datetime dtype, timezone, and scientific values without
requiring a storage unit absent from the public contract. The package does not
promise one fixed datetime storage resolution.

**Impact:** The test suite falsely reports a failure on a supported dependency,
and documentation misdescribes the dtype in that environment. This is not
evidence that the corresponding timestamp values are incorrect.

**Recommended correction:** Use a datetime-type assertion and retain exact
value/timezone checks; describe storage resolution as dependency-dependent.
The mixed-timezone FutureWarnings are consistent with the
[pandas 2.2 documentation](https://pandas.pydata.org/pandas-docs/version/2.2/reference/api/pandas.to_datetime.html).
The mixed-zone values checked in this audit retained their nanoseconds and
offsets; the warnings alone are not an additional correctness finding.

## Comparison with the existing reports

| Existing claim | Independent assessment |
| --- | --- |
| `AUDIT.md` 1–2: quoted hash-prefixed data and whitespace records no longer disappear | Supported by current tests and the framing probes. No continuing silent record-loss case was established here. |
| `AUDIT.md` 3: date-only, naive, UTC, numeric-offset, and mixed-zone timestamps are preserved | Supported for the tested normal forms on both pandas versions. This does not establish strict syntax or missing-token validation; see F1, F2, F4. |
| `AUDIT.md` 4 and 8: optional entries and per-column metadata parsing are resolved | Supported for comma-separated and tested interior-empty lists. The whitespace-delimiter edge case in F3 remains unresolved. |
| `AUDIT.md` 5: dataset-version validation is deferred and preceding comments are allowed | Matches implementation and README. Deliberate scope decisions, not fresh findings. The final audit paragraph calls placement open despite the earlier placement decision marked resolved; this is minor historical-document inconsistency. |
| `AUDIT.md` 6–7: known metadata changes require boundaries; identical repetitions are retained | Supported by implementation review and current tests. Unknown comments remain passive metadata as intended. |
| `AUDIT.md` 9 and 14: missing policy is empty / case-insensitive `nan` / declared sentinel | Incomplete for datetimes because pandas additionally accepts undeclared `NaT`; F2. |
| `AUDIT.md` 10–12: unique headers, strict CSV/newlines, no inferred coordinate roles | Matches current implementation and documented scope. The quoted-record probes found no new framing defect. |
| `AUDIT.md` 13: excess timestamp precision is rejected | **Incomplete:** its conventional two-digit examples are rejected, but F1 bypasses the guard and silently truncates. Numeric overflow/underflow and Int64 boundaries passed the existing checks. |
| `FINDINGS.md`: three specification examples succeed and two fail for declaration width | Reproduced exactly by the five specification-example tests. R2R's additional unquoted-comma description issue is supported by inspection. |
| `FINDINGS.md`: exact list-width requirements and metadata-list syntax need specification clarification | Agree. The PDF does not supply an explicit list-width mandate; strict widths are this reader's documented policy. This distinction also qualifies F3. |
| `FINDINGS.md`: UNAVCO's `UTC` unit does not cause naive timestamps to be localized | Agree; no timezone inference from units was observed. |

`AUDIT.md` is a historical audit with later reconciliation notes; its initial
0.2.0 observations and old source line references are not all claims about
the current parser. Its concluding 89-test count predates the present 94-test
suite. `FINDINGS.md` deliberately checks only the five printed examples and
does not claim full conformance.

## Verification and limits

| Check | Result |
| --- | --- |
| Repository suite, Python 3.12.4 / pandas 3.0.6 | **94 passed** |
| Same suite, temporary pandas 2.2.3 overlay | **93 passed, 1 failed**, as F5 describes |
| Adversarial F1–F4 public-API probes | Reproduced on both versions |
| 600 generated two-cell quoted CSV records across comma, pipe, tab, space, backslash, semicolon | Expected values preserved, including Unicode, embedded delimiters, doubled quotes, hash-prefixed cells, and LF/CRLF within cells; empty cells followed documented missing policy |
| Mixed naive/aware and mixed-offset datetime probes | Individual offsets and tested nine-digit fractions preserved on both versions |
| P0006 fixture and five specification examples | Current expected outcomes pass; P0006 is 20,345 rows by 16 columns |
| Wheel built from temporary source copy and imported from unpacked wheel outside checkout | Build and P0006 smoke read succeeded; metadata reports 0.7.2, Python >=3.12, pandas >=2.2; LICENSE included |
| Repository integrity | No existing tracked-file changes; this report is the sole repository addition |

Baseline command:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest \
  -p no:cacheprovider --basetemp=/private/tmp/mermaid-geocsv-audit-pytest
```

Dependency comparison used the same command with the extracted pandas/pytz
directory and `src` placed on `PYTHONPATH`, and a separate temporary pytest
directory. Build tooling was absent from the repository environment; an initial
non-isolated build could not import setuptools. Downloading/extracting the
declared build tools into a temporary overlay resolved that prerequisite,
and the subsequent wheel build succeeded. No dependency was installed or
upgraded in `.venv`.

A compact public-API reproducer for F1–F4, run from the repository root:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from mermaid import geocsv

cases = {
    "precision": "#dataset: GeoCSV\n#field_type: datetime\nTime\n"
                 "2025-01-01T1:00:00.123456789012\n",
    "undeclared_missing": "#dataset: GeoCSV\n#field_type: datetime\n"
                          "#field_missing: ABSENT\nTime\nNaT\n",
    "empty_tab_attribute": "#dataset: GeoCSV\n#delimiter: \\t\n"
                           "#field_type:\tinteger\nA\tB\nx\t1\n",
    "non_iso": "#dataset: GeoCSV\n#field_type: datetime\nTime\n"
               "2025/01/01\n",
}
with TemporaryDirectory() as directory:
    for name, text in cases.items():
        path = Path(directory) / f"{name}.geocsv"
        path.write_text(text, encoding="utf-8")
        try:
            print(name, geocsv.read(path)[0].to_dict("list"))
        except geocsv.GeoCSVError as error:
            print(name, error)
```

The authoritative format reference was the bundled
[GeoCSV v2.0.4 PDF](docs/references/GeoCSV_v2.0.4.pdf), especially sections
6–7, 11, 13–14, and 16. Behavioral references were
`/Users/jdsimon/programs/automaid/scripts/geocsv.py` and
`/Users/jdsimon/programs/GeoCSV/readGeoCSV.m`.

This audit sampled two supported pandas versions, not every version allowed
by the open-ended dependency. It did not execute the upstream writer, run
MATLAB, or certify all ISO 8601 representations. Valid ISO week dates, ordinal
dates, and comma-fraction forms were also rejected in exploratory probes;
the supported ISO subset should be made explicit, but these were not promoted
to separate findings without an agreed requirement to support those forms.
The existing tested UTC dtype for empty/all-missing datetime columns was
treated as a representation policy, not evidence that nonmissing source times
were reinterpreted.

No fixes were made during the read-only audit. Follow-up implementation status
is recorded below.

## Follow-up — 2026-10-07

F1, F2, F3, and F5 have since been addressed. F4 is closed in package 0.9.0:
the reader now validates the documented extended-calendar datetime subset
before calling pandas, and tests reject all five reproduced nonconforming
spellings. The README and reader specification document the supported forms.
Timezone parsing and conversion remain delegated to pandas. Verification after
the F4 change: `.venv/bin/pytest -q` reports **125 passed** on pandas 3.0.6.
