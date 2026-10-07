# mermaid-geocsv

`mermaid-geocsv` reads MERMAID GeoCSV files into typed pandas DataFrames,
returning one table per dataset through `geocsv.read(...)`:

```python
from mermaid import geocsv
```

It preserves source column names, record order, timestamps and their timezones,
and GeoCSV metadata, including units, comments, and the source file path.
Empty fields and type-appropriate missing markers are represented as pandas
missing values.
For whitespace-delimited metadata lists, quote empty edge entries with ASCII
double quotes (`""`).

By default, timestamps retain their source timezones, including mixed offsets.
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
and the [pandas tutorial](TUTORIAL.md) for examples.

Developed and maintained by [Bathymetrix®](https://bathymetrix.com).
