# Plot GeoCSV measurements

Read the included P0006 data and make two plots with pandas and Matplotlib.
These examples run offline and perform analysis after parsing. The
[schema-converted subset](../data/fixtures/schema-1.0.0/README.md) retains
selected historical records, including 12 GPS fixes for 2019; these plots do
not represent a complete instrument history.

Companions: [Markdown](plotting.md) · [Notebook](plotting.ipynb).

## Setup

From the cloned repository, activate your environment and install the packages:

```bash
source .venv/bin/activate
python -m pip install . matplotlib
```

See [installation and notebook setup](../docs/installation.md) if needed. Run the
Python examples in order from the repository root, `docs/`, or `tutorials/`.

## 1. Read the data

```python
from pathlib import Path
import matplotlib.pyplot as plt
from mermaid import geocsv

root = Path.cwd()
if root.name in {"docs", "tutorials"}:
    root = root.parent

records = geocsv.read(root / "data/fixtures/schema-1.0.0/P0006/P0006.geocsv")[0]
```

## 2. Plot pressure measurements

Select pressure measurements from the first two weeks. Plot the source values
in mbar, without converting them to depth:

```python
pressure = records.loc[
    records["MethodIdentifier"].str.startswith("Measurement:Pressure-Absolute")
    & records["Time"].ge("2018-06-27")
    & records["Time"].lt("2018-07-11")
].dropna(subset=["WaterPressure"]).sort_values("Time")

fig, ax = plt.subplots(figsize=(9, 3))
ax.plot(pressure["Time"], pressure["WaterPressure"])
ax.set(xlabel="Time (UTC)", ylabel="WaterPressure (mbar)",
       title="P0006 pressure measurements")
fig.autofmt_xdate()
fig.tight_layout()
plt.show()
```

## 3. Plot GPS latitude over time

GPS records describe surface fixes. This plot selects the fixes from 2019:

```python
gps = records.loc[
    records["MethodIdentifier"].str.startswith("Measurement:Position")
    & records["Time"].ge("2019-01-01")
    & records["Time"].lt("2020-01-01")
].dropna(subset=["Latitude"]).sort_values("Time")

fig, ax = plt.subplots(figsize=(9, 3))
ax.scatter(gps["Time"], gps["Latitude"], s=10)
ax.set(xlabel="Time (UTC)", ylabel="Latitude (degrees north)",
       title="P0006 GPS fixes in 2019")
fig.autofmt_xdate()
fig.tight_layout()
plt.show()
```

Use `fig.savefig("p0006_gps.png", dpi=180)` to save the current figure.
Further analysis is downstream of parsing; choose coordinate systems and any
receiver (station) pressure-to-depth model explicitly for the scientific
question. The optional SAC projection uses the documented approximation
100 mbar per metre of MERMAID station depth in `stdp`.
