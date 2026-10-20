# Installation and notebook setup

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

## Minimal parser installation

Install the parser and its required dependency, pandas 2.2 or newer:

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
python -m jupyterlab docs/tutorials/READ.ipynb
```

JupyterLab opens in your browser. Select **Python 3 (ipykernel)** if prompted,
then run the cells from top to bottom with **Shift+Enter**. Keep the terminal
running while you work. To stop JupyterLab, press **Ctrl+C** in the terminal
and confirm shutdown if prompted.

On subsequent visits, activate the environment and launch the notebook:

```bash
source .venv/bin/activate
python -m jupyterlab docs/tutorials/READ.ipynb
```

## Optional ObsPy support

The optional ObsPy dependency enables `geocsv.associate` for MiniSEED-derived
traces and streams:

```bash
python -m pip install '.[obspy]'
```

This adds ObsPy 1.5.1 or newer. Reader import and use remain independent of
ObsPy. To run the association notebook, also install the notebook tools above:

```bash
python -m jupyterlab docs/tutorials/ASSOCIATE.ipynb
```

Each tutorial is standalone and has a synchronized Markdown companion.
Start with the [read tutorial](tutorials/READ.md), then explore
[fetching](tutorials/FETCH.md), [plotting](tutorials/PLOTTING.md), or the
[association tutorial](tutorials/ASSOCIATE.md), and the
[reader specification](READER_SPEC.md) for API and format details.
