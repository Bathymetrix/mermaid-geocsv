# mermaid-geocsv: First-Pass Implementation Handoff

## Goal

Build a clean, lightweight Python reader for MERMAID GeoCSV files. This
package is intended to be a trustworthy, citeable implementation reference for
work on MERMAID metadata formats.

The initial product is a useful typed pandas `DataFrame`, not merely a sequence
of parsed text rows and not a recreation of the legacy MATLAB workflow.

## Authority and References

Treat these as reference material, in this order:

1. The current canonical MERMAID example:
   `/Users/jdsimon/Desktop/P0006.geocsv`
2. The GeoCSV format specification:
   `/Users/jdsimon/programs/GeoCSV/docs/GeoCSV_v2.0.4.pdf`
3. MERMAID-specific format notes:
   `/Users/jdsimon/programs/GeoCSV/docs/geocsv_description_automaid-v4.txt`
4. The private legacy writer:
   `/Users/jdsimon/programs/automaid/scripts/geocsv.py`
5. The legacy MATLAB reader and historical example:
   `/Users/jdsimon/programs/GeoCSV/readGeoCSV.m`
   `/Users/jdsimon/programs/GeoCSV/P0006_geo.csv`

The private writer and MATLAB reader describe existing behavior but are not
implementation templates. Do not copy their workflow, assumptions, or manual
CSV splitting.

## Canonical Example Observations

The current `P0006.geocsv` file contains one dataset with:

- comment metadata followed by one header row and 20,345 data rows;
- 16 columns, consistently present in every observed data row;
- `#field_unit` and `#field_type` declarations matching the header width;
- four observed MERMAID method families: GPS, pressure, thermocline, and
  event;
- literal `nan` cells, including in the declared `integer` `SampleCount`
  field.

The 2025 historical example has 14 columns. In particular, it lacks
`DataQuality` and `SampleCount`. Therefore, do not hard-code the current
16-column MERMAID schema.

## First-Pass Scope

Support one self-contained GeoCSV dataset per file:

1. Read the comment preamble, header, and data table.
2. Use the standard-library `csv` module so quoted cells and the declared
   delimiter are handled correctly.
3. Build columns dynamically from the file header.
4. Convert values using the aligned `#field_type` declaration:
   `string`, `datetime`, `float`, and `integer`.
5. Retain comments, field types, field units, and original column names.
6. Preserve row alignment across all typed columns.

Do not add scientific interpretation or transformation. In particular, do not
derive depth from pressure, interpolate positions, reclassify method IDs,
filter event types, or write output files.

Do not expose a CLI in the first pass. The immediate public value is the Python
reader and its usable returned object. Add a CLI only once there is a concrete
command-level workflow such as validation, inspection, or conversion.

## Missing Values

Define and document one explicit conversion policy:

- declared `float` values written as `nan` become `pandas.NA` in a nullable
  `Float64` column;
- declared `integer` values written as `nan` become `pandas.NA` in a nullable
  `Int64` column;
- declared `string` values written as `nan` become `pandas.NA` in a nullable
  pandas `string` column;
- declared `datetime` values written as `nan` become `pandas.NaT`; nonmissing
  datetimes with explicit offsets are converted to UTC.

Match `nan` case-insensitively across all declared types. Preserve other
strings unless a source `field_missing` declaration marks them as missing.

Do not silently substitute zero, empty strings, or inferred values.

## Intended Python Interface

Canonical names:

- distribution and future CLI: `mermaid-geocsv`
- import: `from mermaid import geocsv`
- format name in prose: `GeoCSV`

Use `src/mermaid/geocsv/` as the package layout.

`geocsv.read(...)` should return the typed pandas `DataFrame` directly.
Preserve GeoCSV comments and field metadata under the single key
`frame.attrs["geocsv"]`. This is a deliberate use of pandas' experimental
global-metadata facility: guarantee the metadata on the freshly parsed frame,
but do not guarantee that arbitrary pandas transformations or file exports
retain it.

Store metadata in one immutable, documented `GeoCSVMetadata` value rather than
scattering package keys through `DataFrame.attrs`. It preserves the resolved
absolute source path as reader provenance, ordered raw comments (including
repeated or unknown keys), field types, field units, the delimiter, and any
other parsing-relevant source declarations.

The intended experience is:

```python
from mermaid import geocsv

frame = geocsv.read("P0006.geocsv")

frame.iloc[17]
frame.loc[frame["StartTime"].eq(date)]
frame.loc[frame["StartTime"].eq(date), "Latitude"]
metadata = frame.attrs["geocsv"]
metadata.source_path
metadata.field_types["SampleCount"]
metadata.field_units["Latitude"]
```

Keep the exact GeoCSV header spelling as the `DataFrame` column labels. Do not
make normalized attribute aliases such as `.latitude` part of the public API.
They would be fragile for arbitrary GeoCSV headers and duplicate pandas'
existing access mechanisms.

Use a zero-based, file-wide data-record-order `RangeIndex` named
`source_record_index`; it excludes comments and headers. Keep `StartTime` as a
timezone-aware datetime column, not as the index. Start times need not be
unique: the canonical file has both a pressure and thermocline record at
`2019-04-23T19:31:14.000Z`. Keeping time as a column preserves every source
row and makes time selections return all
matching, provenance-bearing rows.

Use pandas' nullable `Int64`, `Float64`, and `string` dtypes for declared
integer, float, and string columns. Use timezone-aware pandas datetimes for
declared datetime columns. Follow the native missing-value policy above.

## Deferred: Multiple Datasets per File

The GeoCSV standard allows one physical file to contain multiple independent
datasets. Each begins with a new `#dataset:` record and has its own comments,
header, and data rows; it is not merely a concatenation based on station name.

This is intentionally out of scope for the first pass. If a second `#dataset:`
record is encountered after the initial dataset starts, fail clearly that
multi-dataset GeoCSV files are not yet supported.

Future support should be a thin framing layer that separates the stream at
dataset boundaries and invokes the mature single-dataset parser for each
section. Do not build that infrastructure prematurely.

## Verification Expectations

- Add focused tests using small, non-sensitive fixtures based on the canonical
  file's structure.
- Test dynamic header handling, each declared field type, quoted comments or
  cells, the missing-value policy, and rejection of a second dataset.
- Test the public import, returned metadata, DataFrame dtypes, row index, and
  time-selection access pattern.
- Use the repository `.venv` when it exists.
- Keep the README concise, format-oriented, and aligned with the documented
  public Python API.
