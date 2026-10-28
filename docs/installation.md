# Installation and notebook setup

Requires Python 3.11 or newer. Python 3.14 is the latest tested and supported
version; newer Python versions are not yet validated. After cloning the
repository, run these commands in your terminal from the repository root
(macOS/Linux):

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
```

If `.venv` already exists, just activate it. Choose the installation command
below that fits your workflow. Each installs the core package; running the
minimal command first is unnecessary. In these commands, `python` uses the
activated environment, and `-m` runs the named module using that interpreter.

On macOS, python.org installers for Python 3.11–3.14 include
`Install Certificates.command` in `/Applications/Python 3.x/` (use the
installed version's folder). Run it once to complete HTTPS certificate setup.
If `fetch` reports `CERTIFICATE_VERIFY_FAILED`, run it and restart Python. See
[Python's macOS installation instructions](https://docs.python.org/3/using/mac.html#installation-steps).

On Linux, distribution-provided Python normally uses the system CA bundle.
Ensure the distribution's `ca-certificates` package is installed and current.

## Supported Python versions

The supported Python range is 3.11–3.14. CI checks a fresh full installation
and runs the full suite, including association, SAC export, and tutorial
examples, on every supported minor version:

| Python | pandas | ObsPy | NumPy |
| --- | --- | --- | --- |
| 3.11 | 2.3.3 (minimum) and latest compatible | 1.5.1 (minimum) and latest compatible | Latest compatible |
| 3.12 | 2.3.3 (minimum) and latest compatible | 1.5.1 (minimum) and latest compatible | Latest compatible |
| 3.13 | 2.3.3 (minimum) and latest compatible | 1.5.1 (minimum) and latest compatible | Latest compatible |
| 3.14 | 2.3.3 (minimum) and latest compatible | 1.5.1 (minimum) and latest compatible | Latest compatible |

The package metadata lists supported Python minor versions using standard
classifiers. `Requires-Python >=3.11` sets the installation minimum; it does not
certify untested future Python versions. Supporting 3.11 also means package
code must use syntax and standard-library APIs available in that version.

Pandas 2.3.3 is the common minimum across Python 3.11–3.14. Its
[release metadata lists all four Python versions](https://pypi.org/project/pandas/2.3.3/),
and its [release notes introduce Python 3.14 support](https://pandas.pydata.org/docs/whatsnew/v2.3.3.html).
Pandas 2.2 does not support Python 3.14. The package requires `pandas>=2.3.3`
so fresh installs and existing environments use the same supported minimum.

[`scripts/check_installation.py`](../scripts/check_installation.py) creates a
temporary virtual environment for each interpreter and runs the documented
full install (`python -m pip install '.[obspy]'`) without installing dependencies
in advance. Packaging inputs are copied to a temporary source directory,
excluding existing build output, to reproduce installation from a fresh
download. Pip builds and installs the package wheel. The check records the
resolved versions, runs `pip check`, and runs
[`scripts/check_wheel.py`](../scripts/check_wheel.py) outside the checkout in
Python's isolated mode. The smoke check verifies the installed import location and
version, lazy ObsPy loading, and a real-data `read → associate(create_sac_header=True) → Trace.write`
round trip with sample, timing, identity and coordinate checks. Fixtures remain
external test inputs; they are not needed in the installed package. The check
does not contact EarthScope or require production GeoCSV hosting.

After the smoke check, the runner installs pytest and runs the full suite
against the installed distribution, with the checkout's `src` path disabled.
Each interpreter also runs a separate fresh installation with minimum pandas
and ObsPy versions. Environments are removed after each case. Existing project
environments are unchanged. Reproduce the matrix locally with:

```bash
.venv/bin/python scripts/check_installation.py python3.11 python3.12 python3.13 python3.14
```

Pass absolute interpreter paths if the executables are not on `PATH`. The
runner needs network access to download dependencies. It tests each listed
dependency combination, rather than every historical dependency release.

## Minimal parser installation

Install the parser and its required dependency, pandas 2.3.3 or newer:

```bash
python -m pip install .
```

Use it from Python with `from mermaid import geocsv`.

## Notebook installation and demos

Install the parser together with JupyterLab, a Python notebook kernel, and the
NumPy and Matplotlib packages used by the plotting tutorial:

```bash
python -m pip install . jupyterlab ipykernel numpy matplotlib
```

Launch the tutorial from the repository root:

```bash
python -m jupyterlab tutorials/read.ipynb
```

JupyterLab opens in your browser. Select **Python 3 (ipykernel)** if prompted,
then run the cells from top to bottom with **Shift+Enter**. Keep the terminal
running while you work. To stop JupyterLab, press **Ctrl+C** in the terminal
and confirm shutdown if prompted.

On subsequent visits, activate the environment and launch the notebook:

```bash
source .venv/bin/activate
python -m jupyterlab tutorials/read.ipynb
```

## Optional ObsPy support

The optional ObsPy dependency enables `geocsv.associate` for MiniSEED-derived
traces and streams, including optional `create_sac_header=True`. Use ObsPy's
`Trace.write` or `Stream.write` to serialize the located waveform:

```bash
python -m pip install '.[obspy]'
```

This adds ObsPy 1.5.1 or newer. Reader import and use remain independent of
ObsPy. To run the association notebook, also install the notebook tools above:

```bash
python -m jupyterlab tutorials/associate.ipynb
```

The [SAC writing tutorial](../tutorials/write-sac.md) and
[notebook](../tutorials/write-sac.ipynb) demonstrate header creation and ObsPy export.
Comparison rules for independent automaid SAC references are defined in the
[SAC reference](sac.md).

Each tutorial is standalone and has a synchronized Markdown companion.
Start with the [read tutorial](../tutorials/read.md), then explore
[fetching](../tutorials/fetch.md), [plotting](../tutorials/plotting.md), or the
[association tutorial](../tutorials/associate.md), and the
[reader specification](reader-spec.md) for API and format details.

## Development tests

The `dev` extra installs pytest. Combine it with `obspy` to run the full test
suite, including waveform association, SAC export, and tutorial examples:

```bash
python -m pip install '.[dev,obspy]'
python -B -m pytest -q -p no:cacheprovider
```

The minimal and `obspy` installations do not include pytest. Building or
reinstalling the package includes development dependencies only when the
`dev` extra is explicitly selected.
