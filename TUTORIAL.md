# Explore GeoCSV with pandas

This tutorial uses the real P0006 fixture to introduce pandas while exploring
MERMAID positions and pressure measurements. From the repository root, activate
the local environment at the shell prompt:

```bash
source .venv/bin/activate
```

The plots use NumPy and Matplotlib. If either is missing, install them from
the shell while `.venv` is activated:

```bash
python -m pip install numpy matplotlib
```

Then start Python:

```bash
python
```

Run the Python blocks below in order at the `>>>` prompt, without typing the
prompt characters. The parser needs Python 3.12 or newer and pandas. Interactive
Matplotlib windows depend on the local display backend; use `plt.savefig` as
shown below if a window does not appear.

## 1. Read the file and inspect the table

```python
from mermaid import geocsv
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

tables = geocsv.read("data/fixtures/P0006/P0006.geocsv")
records = tables[0]  # The P0006 file contains one dataset.
type(records)
records.shape
records.head()
records.tail(3)
records.columns.tolist()
records.dtypes
records.info()
```

`shape` gives `(rows, columns)`. A DataFrame also has an **index**: the labels
displayed to the left of its rows. This reader creates an index named
`source_record_index`. The first data record in the file gets label `0`, the
second gets `1`, and so on. These labels identify each record's original
position among the data records; they are not physical file line numbers,
which also count headers and comments. The index is separate from the data
columns.

```python
records.index.name                 # 'source_record_index'
records.index[:5].tolist()          # [0, 1, 2, 3, 4]
```

When you filter or sort rows, their existing index labels stay attached.
A filtered table might therefore have labels such as `0, 1, 7, 12`, and a
sorted table can show labels out of numerical order. Pandas does not
automatically renumber them. Below, `loc` uses these labels, while `iloc`
uses a row's current position in the table.

`StartTime` is a data column, rather than the index. Multiple records can
have the same timestamp and still have distinct `source_record_index` labels.
In this P0006 file, every timestamp has an explicit UTC timezone, so the column
has dtype `datetime64[us, UTC]`. Microsecond storage resolution does not
establish microsecond measurement accuracy. In other GeoCSV files, timezone-free
values remain naive; mixed naive and zoned values are preserved as `Timestamp`
objects in an `object` column.

One column name gives a one-dimensional pandas `Series`; a list of names gives
another two-dimensional `DataFrame`:

```python
latitude = records["Latitude"]
coordinates = records[["Latitude", "Longitude"]]
type(latitude)
type(coordinates)
coordinates.head()
records.loc[0, ["StartTime", "MethodIdentifier", "Latitude"]]
records.iloc[:5, :4]
```

`.loc[row, column]` selects by row index label and column name; `.iloc` uses
integer positions. In slices, `.loc` includes the stop label, while `.iloc`
excludes the stop position. These expressions leave `records` unchanged. A
`Series` retains an index and a dtype, and arithmetic acts on its values
rather than repeating a Python list.

After selecting rows by position, their original labels stay with them:

```python
subset = records.iloc[1:3]
subset.index.tolist()  # [1, 2]
subset.loc[2]          # row labeled 2
subset.iloc[0]         # first row in subset, labeled 1
```

The file contains different record types. Check their counts and which
measurements are present:

```python
records["MethodIdentifier"].value_counts()
records[["Latitude", "Longitude", "WaterPressure"]].isna().sum()
records["StartTime"].min(), records["StartTime"].max()
records["WaterPressure"].describe()
```

`isna()` marks missing values, `sum()` counts them, and `describe()` summarizes
nonmissing numeric values. The original units and declarations are retained:

```python
metadata = records.attrs["geocsv"]
metadata.field_units["WaterPressure"]
metadata.field_units["Latitude"]
metadata.field_types["StartTime"]
metadata.comments[:5]
metadata.source_path
```

`source_path` is the full, resolved path of the file opened by the reader. It
records where the data came from; it is not a field declared in the GeoCSV.
Optional `metadata.field_long_names` and `metadata.field_standard_names` map
source column names to individually trimmed descriptions; P0006 does not
declare them, so their values are empty. The reader preserves coordinate
columns as written and does not infer latitude or longitude roles.
The fresh parsed DataFrame has this metadata. If you need it later, keep
`metadata` separately: pandas does not guarantee `attrs` through arbitrary
transformations or exports. In particular, concatenating tables from
different source files drops their differing `attrs`.

## 2. Select, filter, and summarize records

The boolean expression below has one value per row. `loc[mask]` keeps rows
where it is true. A GPS record has coordinates, but most pressure-only
records do not.

```python
gps_mask = records["MethodIdentifier"].str.startswith("Measurement:GPS")
gps = records.loc[gps_mask].dropna(subset=["Latitude", "Longitude"])
gps = gps.sort_values("StartTime")
gps[["StartTime", "Latitude", "Longitude"]].head()
len(gps)
```

`dropna(subset=...)` discards rows missing either coordinate; it does not
change `records`. The source row number remains the index even after sorting.
For the first five rows by their new time order, use `gps.head()`, not
`gps.loc[:4]`.

Filter a UTC date interval with explicit bounds. The upper bound is excluded,
so this selects all of calendar year 2019:

```python
start = pd.Timestamp("2019-01-01", tz="UTC")
end = pd.Timestamp("2020-01-01", tz="UTC")
gps_2019 = gps.loc[gps["StartTime"].ge(start) & gps["StartTime"].lt(end)]
gps_2019[["StartTime", "Latitude", "Longitude"]].head()
len(gps_2019)
```

Use parentheses around comparisons when combining them with `&` (AND) or
`|` (OR). For example:

```python
has_position = records["Latitude"].notna() & records["Longitude"].notna()
has_pressure = records["WaterPressure"].notna()
records.loc[has_position & has_pressure, ["StartTime", "Latitude", "Longitude", "WaterPressure"]].head()
```

Some useful aggregations:

```python
gps.groupby(gps["StartTime"].dt.year).size()
gps.groupby(gps["StartTime"].dt.year)[["Latitude", "Longitude"]].median()
records.groupby("MethodIdentifier")["WaterPressure"].agg(["count", "min", "median", "max"])
```

`groupby` forms groups and `agg` computes summaries for each. The yearly
coordinate medians are descriptive only; a median longitude near the date
line can be misleading because longitude wraps at ±180°.

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

## 6. Plot a dive's pressure history

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

The parser only reads and preserves GeoCSV information. All filtering,
distance estimates, depth approximations, and plots above are analyses you
perform after parsing; none is inferred by `geocsv.read`.
