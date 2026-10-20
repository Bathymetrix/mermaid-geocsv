"""Write a single associated waveform using ObsPy's SAC implementation."""

from collections.abc import Mapping
from math import isfinite
from pathlib import Path

import numpy as np
from obspy import Trace
from obspy.io.sac import SACTrace
import pandas as pd

from .read import GeoCSVMetadata


def write_sac(trace, path):
    """Validate an associated original segment and write fresh SAC headers."""
    if not isinstance(trace, Trace):
        raise TypeError("write_sac requires one ObsPy Trace")
    source = trace.stats.get("geocsv")
    if not isinstance(source, Mapping):
        raise ValueError("write_sac requires stats.geocsv from geocsv.associate")
    if source.get("association") != "one_segment":
        raise ValueError("write_sac requires a one_segment association; "
                         "first_segment anchor metadata cannot describe a longer trace")
    metadata = source.get("metadata")
    if not isinstance(metadata, GeoCSVMetadata):
        raise ValueError("write_sac requires attached GeoCSV dataset metadata")

    # Check the original segment relationship without reopening its source file.
    for field, key in (("Network", "network"), ("Station", "station"),
                       ("Location", "location"), ("Channel", "channel")):
        code = source.get(field)
        if not isinstance(code, str) or code != trace.stats[key]:
            raise ValueError(f"{trace.id}: waveform {key} differs from its association")
    count = source.get("SampleCount")
    if (not len(trace.data) or np.ma.is_masked(trace.data)
            or len(trace.data) != trace.stats.npts
            or count is None or pd.isna(count) or count != trace.stats.npts):
        raise ValueError(f"{trace.id}: requires the original loaded sample count "
                         "without masked gaps")
    source_start = pd.Timestamp(source.get("StartTime"))
    difference = source.get("starttime_difference_seconds")
    if (pd.isna(source_start) or source_start.tzinfo is None
            or difference is None or pd.isna(difference) or not isfinite(float(difference))
            or trace.stats.starttime.ns != source_start.value + round(difference * 1e9)):
        raise ValueError(f"{trace.id}: waveform start differs from its association")
    rate = source.get("SampleRate")
    if (metadata.field_units.get("SampleRate") != "hertz"
            or rate is None or pd.isna(rate) or not isfinite(float(rate))
            or not isfinite(trace.stats.sampling_rate) or trace.stats.sampling_rate <= 0
            or not trace.stats.sampling_rate - 0.01 <= rate <= trace.stats.sampling_rate + 0.01):
        raise ValueError(f"{trace.id}: waveform rate disagrees with its association")

    headers = {"stel": 0.0}
    for field, key, unit, lower, upper in (
        ("Latitude", "stla", "degrees_north", -90, 90),
        ("Longitude", "stlo", "degrees_east", -180, 180),
    ):
        value = source.get(field)
        if metadata.field_units.get(field) != unit:
            raise ValueError(f"{trace.id}: {field} requires declared units {unit}")
        if (value is None or pd.isna(value) or not isfinite(float(value))
                or not lower <= value <= upper):
            raise ValueError(f"{trace.id}: requires valid {field}")
        headers[key] = float(value)

    pressure = source.get("WaterPressure")
    if pressure is None or pd.isna(pressure):
        quality = source.get("DataQuality")
        if not isinstance(quality, str) or quality != "D":
            raise ValueError(f"{trace.id}: missing WaterPressure; "
                             "only REQ source records (DataQuality D) may omit depth")
        headers["stdp"] = None  # SAC undefined; never infer another record's depth.
    else:
        if metadata.field_units.get("WaterPressure") != "mbar":
            raise ValueError(f"{trace.id}: WaterPressure requires declared units mbar")
        if not isfinite(float(pressure)) or pressure < 0:
            raise ValueError(f"{trace.id}: requires finite nonnegative WaterPressure")
        # Automaid convention: 100 mbar = 1 dbar, treated as approximately 1 m.
        headers["stdp"] = float(pressure) / 100

    sac = SACTrace.from_obspy_trace(trace, keep_sac_header=False)
    for key, value in headers.items():
        setattr(sac, key, value)
    # Exclusive creation also protects against collisions between loop iterations.
    with Path(path).open("xb") as handle:
        sac.write(handle, byteorder="little")
