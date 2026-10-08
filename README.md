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
**`nan` is always missing**, case-insensitively, for every field type,
including strings, regardless of `#field_missing`. A string field cannot
represent literal `nan`; quoted `"nan"` is missing too. Empty fields,
including quoted empty strings, are also missing. String whitespace is
preserved, so ` nan ` remains literal text.
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

Requires Python 3.12 or newer. After cloning the repository, run these commands
in your terminal from the repository root (macOS/Linux):

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
```

If `.venv` already exists, just activate it. Choose one of the two installation
workflows below. In both, `python` uses the activated environment, and `-m`
runs the named module using that interpreter.

### Minimal parser installation

Install the parser and its required dependency, pandas 2.2 or newer:

```bash
python -m pip install .
```

Use it from Python with `from mermaid import geocsv`.

### Notebook installation and demos

Install the parser together with JupyterLab, a Python notebook kernel, and the
NumPy and Matplotlib packages used by the tutorial:

```bash
python -m pip install . jupyterlab ipykernel numpy matplotlib
```

Launch the tutorial from the repository root:

```bash
python -m jupyterlab docs/TUTORIAL.ipynb
```

JupyterLab opens in your browser. Select **Python 3 (ipykernel)** if prompted,
then run the cells from top to bottom with **Shift+Enter**. Keep the terminal
running while you work. To stop JupyterLab, press **Ctrl+C** in the terminal
and confirm shutdown if prompted.

On subsequent visits, activate the environment and launch the notebook:

```bash
source .venv/bin/activate
python -m jupyterlab docs/TUTORIAL.ipynb
```

### Optional ObsPy support

The optional ObsPy dependency supports the experimental
[waveform-association sandbox](sandbox/obspy_association/README.md):

```bash
python -m pip install '.[obspy]'
```

This adds ObsPy 1.5.1 or newer; it does not introduce an association API.

See the [reader specification](docs/READER_SPEC.md) for API and format details,
the pandas tutorial ([Markdown](docs/TUTORIAL.md) or
[Jupyter notebook](docs/TUTORIAL.ipynb)) for examples, and
[open GeoCSV questions](docs/OPEN_QUESTIONS.md) for unresolved format details.

Developed and maintained by [Bathymetrix®](https://bathymetrix.com).
