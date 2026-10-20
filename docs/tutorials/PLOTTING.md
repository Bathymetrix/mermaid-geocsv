# Plot and explore GeoCSV measurements

These downstream pandas, NumPy, and Matplotlib examples explore the real
P0006 fixture. All calculations are explicit analysis after parsing.
The companion files [PLOTTING.md](PLOTTING.md) and
[PLOTTING.ipynb](PLOTTING.ipynb) contain the same prose and Python examples;
update both together whenever either changes.

This tutorial runs independently using tracked fixtures from a fresh checkout.
From the repository root, activate the existing environment and install the
required packages:

```bash
source .venv/bin/activate
python -m pip install . numpy matplotlib
```

See the [installation guide](../INSTALLATION.md) to create an environment.
For a notebook, also install JupyterLab and a Python kernel:

```bash
python -m pip install jupyterlab ipykernel
python -m jupyterlab docs/tutorials/PLOTTING.ipynb
```

Select this repository's `.venv` kernel and run cells from top to bottom.
Alternatively, run the Python blocks in order at a Python prompt. Start from
the repository root, `docs/`, or `docs/tutorials/`.

Interactive windows depend on the Matplotlib backend; use the commented
`fig.savefig` calls to save plots if a window does not appear. This tutorial
requires no variables or notebook state from the [read tutorial](READ.md).

## 1. Read and select the plotting data

```python
from pathlib import Path
from mermaid import geocsv
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

repository_root = Path.cwd()
if repository_root.name == "tutorials":
    repository_root = repository_root.parent.parent
elif repository_root.name == "docs":
    repository_root = repository_root.parent
records = geocsv.read(repository_root / "data/fixtures/P0006/P0006.geocsv")[0]
gps_mask = records["MethodIdentifier"].str.startswith("Measurement:GPS")
gps = records.loc[gps_mask].dropna(subset=["Latitude", "Longitude"])
gps = gps.sort_values("StartTime")
start = pd.Timestamp("2019-01-01", tz="UTC")
end = pd.Timestamp("2020-01-01", tz="UTC")
gps_2019 = gps.loc[gps["StartTime"].ge(start) & gps["StartTime"].lt(end)]
assert len(gps_2019) >= 2
```

The source units are retained in `records.attrs["geocsv"].field_units`.
Original `source_record_index` labels stay attached after filtering and sorting.

## 2. Plot a dive's pressure history

Pressure measurements provide a much denser view of vertical motion. This
example selects the first two weeks of the file and overlays positioned
algorithm records. The pressure is plotted in its **source unit, mbar**.

```python
window_start = pd.Timestamp("2018-06-27", tz="UTC")
window_end = pd.Timestamp("2018-07-11", tz="UTC")
window = records.loc[
    records["StartTime"].ge(window_start) & records["StartTime"].lt(window_end)
]
pressure = window.loc[
    window["MethodIdentifier"].str.startswith("Measurement:Pressure")
].dropna(subset=["WaterPressure"]).sort_values("StartTime")
events = window.loc[
    window["MethodIdentifier"].str.startswith("Algorithm(event)")
].dropna(subset=["WaterPressure"])

assert not pressure.empty
assert not events.empty

fig, ax = plt.subplots(figsize=(11, 4))
ax.plot(pressure["StartTime"], pressure["WaterPressure"],
        lw=1, label="Pressure measurement")
ax.scatter(events["StartTime"], events["WaterPressure"],
           color="tab:red", s=25, label="Event algorithm record")
ax.set(xlabel="Time (UTC)", ylabel="WaterPressure (mbar)",
       title="P0006 pressure history, first two weeks")
ax.legend()
ax.grid(alpha=0.3)
fig.autofmt_xdate()
fig.tight_layout()
# fig.savefig("p0006_pressure.png", dpi=180)
plt.show()
```

This plot lets you inspect dive cycles and when event records occur within
them. A plotted event is an algorithm record, not an independent pressure
measurement. Use `window["MethodIdentifier"].value_counts()` to see which
record types are present in a different time window.

## 3. Plot a two-dimensional surface trajectory

The 2019 GPS fixes are actual surface positions. Longitude wraps from +180°
to −180° at the international date line. Unwrap it for this plot so lines do
not jump across the entire horizontal axis. The displayed longitudes may then
extend beyond ±180°, but still represent the same locations.

```python
track = gps_2019.copy()
track["LongitudeUnwrapped"] = np.rad2deg(
    np.unwrap(np.deg2rad(track["Longitude"].to_numpy(dtype=float)))
)

fig, ax = plt.subplots(figsize=(9, 6))
ax.plot(track["LongitudeUnwrapped"], track["Latitude"], "-", lw=0.8, alpha=0.7)
points = ax.scatter(
    track["LongitudeUnwrapped"], track["Latitude"],
    c=track["StartTime"].dt.dayofyear, cmap="viridis", s=10,
)
ax.scatter(track["LongitudeUnwrapped"].iloc[0], track["Latitude"].iloc[0],
           marker="o", s=80, facecolors="none", edgecolors="black", label="First fix")
ax.scatter(track["LongitudeUnwrapped"].iloc[-1], track["Latitude"].iloc[-1],
           marker="x", s=80, color="black", label="Last fix")
fig.colorbar(points, ax=ax, label="Day of 2019 (UTC)")
ax.set(xlabel="Unwrapped longitude (degrees east)",
       ylabel="Latitude (degrees north)", title="P0006 GPS fixes in 2019")
ax.legend()
ax.grid(alpha=0.3)
fig.tight_layout()
# fig.savefig("p0006_surface_2019.png", dpi=180)
plt.show()
```

This is a longitude/latitude trajectory, not a projected or distance-scaled
map. The connecting line joins successive observations; it does not establish
the exact route between fixes, particularly while the instrument is submerged.
The color encodes time. For another year, change the `start` and `end` dates,
recreate the filtered `track`, and update the plot labels.

## 4. Estimate distance traveled between two dates

The calculation below sums great-circle distances between successive **GPS
surface fixes** in the selected interval. It uses the haversine formula and
an Earth radius of 6,371 km. Longitudes are converted to radians and wrapped
by the trigonometric formula, so crossing the date line is handled correctly.

```python
start = pd.Timestamp("2019-01-01", tz="UTC")
end = pd.Timestamp("2020-01-01", tz="UTC")
route = gps.loc[gps["StartTime"].ge(start) & gps["StartTime"].lt(end)]
route = route.sort_values("StartTime")

lat = np.deg2rad(route["Latitude"].to_numpy(dtype=float))
lon = np.deg2rad(route["Longitude"].to_numpy(dtype=float))
dlat = np.diff(lat)
dlon = np.diff(lon)
a = np.sin(dlat / 2) ** 2 + np.cos(lat[:-1]) * np.cos(lat[1:]) * np.sin(dlon / 2) ** 2
segment_km = 2 * 6371.0 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))

print(f"GPS fixes: {len(route)}")
print(f"Sum of straight segments: {segment_km.sum():.1f} km")
print(f"Largest gap: {route['StartTime'].diff().max()}")
```

Change `start` and `end` to answer a different interval. These bounds select
fixes *inside* the interval; the calculation does not include travel between
the boundary and the first or last fix. It is a polyline estimate from sampled
surface positions, **not** a measured underwater distance. Sparse fixes,
unseen turns, and GPS noise affect the sum. Inspect the largest time gap before
interpreting the result as continuous travel. Summing more noisy fixes can
even increase the estimate without real movement.

For a separate question, compute the straight-line displacement between the
first and last fixes:

```python
first_to_last_km = 2 * 6371.0 * np.arcsin(np.sqrt(np.clip(
    np.sin((lat[-1] - lat[0]) / 2) ** 2
    + np.cos(lat[0]) * np.cos(lat[-1]) * np.sin((lon[-1] - lon[0]) / 2) ** 2,
    0, 1,
)))
print(f"First-to-last displacement: {first_to_last_km:.1f} km")
```

This second quantity only needs two fixes and generally differs from the
sum of successive segments. Both examples require at least two fixes.

## 5. Plot a three-dimensional track with pressure-derived depth

Rows with both coordinates and pressure are algorithm records, rather than
GPS fixes. Select them explicitly. The source comment says **100 mbar is
approximately 1 m of water**. Applying that rule gives a rough vertical
coordinate; it does not correct for atmospheric pressure, water density, or
sensor calibration. `Elevation` is missing throughout this fixture and is
not used here.

```python
profile = records.dropna(subset=["Latitude", "Longitude", "WaterPressure"])
profile = profile.loc[
    profile["StartTime"].ge(start) & profile["StartTime"].lt(end)
].sort_values("StartTime").copy()
assert not profile.empty
profile["DepthApproxM"] = profile["WaterPressure"] / 100.0
profile["LongitudeUnwrapped"] = np.rad2deg(
    np.unwrap(np.deg2rad(profile["Longitude"].to_numpy(dtype=float)))
)
profile["DaysSinceStart"] = (
    profile["StartTime"] - profile["StartTime"].min()
).dt.total_seconds() / 86400
profile["MethodIdentifier"].value_counts()

fig = plt.figure(figsize=(10, 7))
ax = fig.add_subplot(projection="3d")
ax.plot(profile["LongitudeUnwrapped"], profile["Latitude"],
        -profile["DepthApproxM"], color="0.7", lw=0.7)
points = ax.scatter(
    profile["LongitudeUnwrapped"], profile["Latitude"],
    -profile["DepthApproxM"], c=profile["DaysSinceStart"],
    cmap="plasma", s=14,
)
fig.colorbar(points, ax=ax, shrink=0.6, label="Days since first selected record")
ax.set(xlabel="Unwrapped longitude (degrees east)",
       ylabel="Latitude (degrees north)",
       zlabel="Approximate depth (m, plotted negative)",
       title="P0006 positioned pressure records in 2019")
# fig.savefig("p0006_depth_2019.png", dpi=180)
plt.show()
```

The line orders sparse records by time; it does not reconstruct the actual
three-dimensional path. The axes also mix angular coordinates and meters, so
the visual slope and aspect are not physically scaled. To inspect a specific
record behind a point, look at `profile[["StartTime", "MethodIdentifier",
"Latitude", "Longitude", "WaterPressure"]]`.


The parser only reads and preserves GeoCSV information. All filtering,
distance estimates, depth approximations, and plots above are analyses you
perform after parsing; none is inferred by `geocsv.read`.
