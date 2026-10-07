# Reader findings against the GeoCSV examples

Reviewed 2026-10-06 with `mermaid-geocsv` 0.7.2 against the five examples on
pages 5–6 of the repository's [GeoCSV v2.0.4 PDF](docs/references/GeoCSV_v2.0.4.pdf).
The [fixtures](data/fixtures/GeoCSV_v2.0.4_examples/) remove display wrapping,
use ASCII hyphens, and retain the agreed space before `TAJIKISTAN`. They preserve
the printed metadata inconsistencies rather than repairing them. This checks
these examples, not full specification conformance.

| Fixture | Reader outcome |
| --- | --- |
| `unavco.geocsv` | One 5-row, 7-column DataFrame: two string, three nullable float, and two timezone-naive datetime columns. Units and raw comments, including coordinate-system metadata, are preserved. |
| `iris.geocsv` | `GeoCSVError`: `line 3: field_unit has 7 fields; header has 8`. |
| `minimal_iris.geocsv` | One 2-row, 8-column DataFrame. All columns remain strings because no types are declared; dates and coordinates are not inferred. |
| `event.geocsv` | One 2-row, 13-column DataFrame. All columns remain strings, preserving contributor-ID leading zeros and text whitespace. |
| `r2r.geocsv` | `GeoCSVError`: `line 4: field_type has 8 fields; header has 9`. |

Successful reads retain exact header spellings, source record order, a zero-based
`source_record_index`, and immutable GeoCSV metadata with the resolved source
path. All five current fixtures end with LF. The width requirements are enforced
by this reader; pandas itself does not validate GeoCSV comment declarations.

The IRIS units and R2R types mismatches are present in the PDF. Section 7 describes
these as values for each column, and section 11 allows unknown values to be empty,
but an explicit list-width mandate is absent. Accidental omissions are a reasonable
inference; the document alone does not establish the authors' intent.

R2R also has a second issue hidden by its first error: the unquoted comma in
`latitude_at_device,(layback)` produces ten `field_long_name` entries for nine
columns under this reader's list rules. This observation comes from inspecting
the declaration, not from a successful R2R read.

## Suggested specification clarifications

- Require every present column-attribute list (`field_*`) to have exactly one
  entry per header field, in header order. Unknown values require explicit empty
  entries; the entire declaration may be omitted. Correct the IRIS and R2R
  examples to illustrate that rule.
- Specify the delimiter and quoting rules for metadata lists explicitly,
  including values containing the delimiter. If the R2R latitude description is
  one value, quote `"latitude_at_device,(layback)"` in the comma-delimited list.
- Clarify the meaning of `UTC` in `field_unit` when timestamps lack timezone
  designators, as in UNAVCO. This reader preserves the declaration and leaves
  those timestamps naive. An explicit ISO 8601 timezone designator would make
  their intended interpretation unambiguous.

Verification: `.venv/bin/pytest -q tests/test_spec_examples.py` covers all five
unmodified fixtures: three successful reads and two expected rejections.
Result: **5 passed**. Reader behavior and package version are unchanged.
