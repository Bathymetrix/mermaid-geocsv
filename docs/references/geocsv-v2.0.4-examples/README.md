# GeoCSV v2.0.4 specification examples

These five reference files transcribe pages 5–6 of the
[GeoCSV v2.0.4 PDF](../GeoCSV_v2.0.4.pdf). Display wrapping was removed,
hyphens use ASCII, and the space before `TAJIKISTAN` is retained. Printed
metadata inconsistencies are preserved. All five files end with LF.

These are specification reference material, not supported MERMAID inputs or
examples of current reader output. `geocsv.read` rejects every file because
it lacks the required MERMAID schema declaration. The reader supports only
[MERMAID schema 1.0.0](../../format-spec.md); general GeoCSV support belongs
outside this package's current scope. The files were moved from
`data/fixtures/GeoCSV_v2.0.4_examples/` without changing their bytes.

## Preserved specification observations

| File | Content or printed inconsistency |
| --- | --- |
| `unavco.geocsv` | Seven columns with coordinate-system metadata and declared types. |
| `iris.geocsv` | Seven `field_unit` entries for eight columns. |
| `minimal_iris.geocsv` | Eight columns without declared types. |
| `event.geocsv` | Thirteen columns, including contributor identifiers with leading zeros and text whitespace. |
| `r2r.geocsv` | Eight `field_type` entries for nine columns; an unquoted comma in `latitude_at_device,(layback)` also yields ten `field_long_name` entries under CSV list parsing. |

Section 7 describes values for each column, and section 11 allows unknown
values to be empty, but an explicit list-width mandate is absent. Accidental
omissions are a reasonable inference; the document alone does not establish
the authors' intent. These observations do not define current parser behavior
or a general GeoCSV conformance test suite.

[`tests/test_spec_examples.py`](../../../tests/test_spec_examples.py) checks
the supported-format boundary by requiring schema rejection for these files.
The complete MERMAID specification example is tested separately as valid input.
