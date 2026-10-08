# mermaid-geocsv

`mermaid-geocsv` reads MERMAID GeoCSV files into typed pandas DataFrames,
returning one table per dataset through `geocsv.read(...)`:

```python
from mermaid import geocsv
```

It preserves source column names, record order, timestamps and their timezones,
and GeoCSV metadata, including units, comments, and the source file path.
If an unknown `#key: value` line repeats with a changed value after the
header, the reader requires a new `#dataset` section and header. Free-text
comments remain usable between records. The scope of custom keys is an
[open format question](docs/OPEN_QUESTIONS.md#1-do-custom-keyword-lines-define-dataset-wide-metadata).
Empty fields and type-appropriate missing markers are represented as pandas
missing values.
For whitespace-delimited metadata lists, quote empty edge entries with ASCII
double quotes (`""`).

By default, timestamps retain their source timezones, including mixed offsets.
Declared datetime columns with no non-missing timestamps remain timezone-naive,
including when a conversion timezone is requested.
Pass `datetime_timezone="UTC"` (or another timezone accepted by pandas) to
convert timezone-aware datetime columns. In that mode every non-missing value
must include a timezone; naive timestamps raise an error.

Datetime values use extended ISO calendar dates (`YYYY-MM-DD`), optionally
with a time, up to nine fractional-second digits, and `Z` or a numeric UTC
offset. The reader rejects other spellings instead of relying on pandas to
normalize them.

## Install

Requires Python 3.12 or newer. From the repository root:

```bash
python -m pip install .
```

The installation includes pandas 2.2 or newer.

See the [reader specification](docs/READER_SPEC.md) for API and format details,
the [pandas tutorial](docs/TUTORIAL.md) for examples, and
[open GeoCSV questions](docs/OPEN_QUESTIONS.md) for unresolved format details.

Developed and maintained by [Bathymetrix®](https://bathymetrix.com).
