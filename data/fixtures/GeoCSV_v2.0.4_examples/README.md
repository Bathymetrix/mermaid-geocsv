# GeoCSV v2.0.4 specification examples

These five fixtures transcribe pages 5–6 of the
[GeoCSV v2.0.4 PDF](../../../docs/references/GeoCSV_v2.0.4.pdf). Display wrapping
was removed, hyphens use ASCII, and the space before `TAJIKISTAN` is retained.
Printed metadata inconsistencies are preserved. These examples test selected
reader behavior, not complete specification conformance.

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

`tests/test_spec_examples.py` verifies three successful reads and two
expected rejections. Unresolved specification questions are maintained in
[open questions](../../../docs/open-questions.md#questions-for-the-geocsv-specification).
