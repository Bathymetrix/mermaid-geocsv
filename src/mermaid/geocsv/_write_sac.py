"""Write a single associated waveform using ObsPy's SAC implementation."""

from collections.abc import Mapping
from math import isfinite
from pathlib import Path

import numpy as np
from obspy import Trace, UTCDateTime
from obspy.io.sac import SACTrace
import pandas as pd

from ._associate import SAMPLE_RATE_TOLERANCE_HZ
from .read import GeoCSVMetadata


def _float32_value(value, label):
    """Reject overflow and loss to zero at the SAC storage boundary."""
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        stored = np.float32(value)
    if not np.isfinite(stored) or (value != 0 and stored == 0):
        raise ValueError(f"{label}: value cannot be represented in SAC float32 storage")
    return stored


def write_sac(trace, path):
    """Validate an associated waveform and write fresh geographic SAC headers."""
    if not isinstance(trace, Trace):
        raise TypeError("write_sac requires one ObsPy Trace")
    source = trace.stats.get("geocsv")
    if not isinstance(source, Mapping):
        raise ValueError("write_sac requires stats.geocsv from geocsv.associate")
    association = source.get("association")
    if (not isinstance(association, Mapping)
            or association.get("type") not in {"single_segment", "anchor_segment"}):
        raise ValueError("write_sac requires a single_segment or anchor_segment association")
    waveform = association.get("waveform")
    if not isinstance(waveform, Mapping):
        raise ValueError("write_sac requires an association-time waveform snapshot")
    metadata = source.get("metadata")
    if not isinstance(metadata, GeoCSVMetadata):
        raise ValueError("write_sac requires attached GeoCSV dataset metadata")

    # Check the association-time waveform without reopening any source file.
    for field, key in (("Network", "network"), ("Station", "station"),
                       ("Location", "location"), ("Channel", "channel")):
        code = source.get(field)
        if (not isinstance(code, str) or code != trace.stats[key]
                or waveform.get(key) != trace.stats[key]):
            raise ValueError(f"{trace.id}: waveform {key} differs from its association")
        if (not code.isascii() or len(code) > 8 or code.strip() != code
                or code == "-12345"):
            raise ValueError(f"{trace.id}: {key} cannot be preserved in an "
                             "eight-byte ASCII SAC identity header")
    count = source.get("SampleCount")
    associated_count = waveform.get("sample_count")
    if (not len(trace.data) or np.ma.is_masked(trace.data)
            or len(trace.data) != trace.stats.npts
            or associated_count is None or pd.isna(associated_count)
            or associated_count != trace.stats.npts
            or count is None or pd.isna(count) or count <= 0
            or not float(count).is_integer()
            or (association["type"] == "single_segment" and count != trace.stats.npts)):
        raise ValueError(f"{trace.id}: requires the association-time loaded sample count "
                         "without masked gaps")
    if trace.data.dtype.kind not in "iuf" or not np.isfinite(trace.data).all():
        raise ValueError(f"{trace.id}: SAC export requires finite real samples")
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        samples = trace.data.astype(np.float32)
    if (not np.isfinite(samples).all()
            or np.any((trace.data != 0) & (samples == 0))):
        raise ValueError(f"{trace.id}: samples cannot be represented in SAC float32 storage")
    source_start = pd.Timestamp(source.get("StartTime"))
    difference = association.get("waveform_start_offset_seconds")
    associated_start = waveform.get("starttime")
    if (not isinstance(associated_start, UTCDateTime)
            or trace.stats.starttime.ns != associated_start.ns
            or pd.isna(source_start) or source_start.tzinfo is None
            or difference is None or pd.isna(difference) or not isfinite(float(difference))
            or trace.stats.starttime.ns != source_start.value + round(difference * 1e9)):
        raise ValueError(f"{trace.id}: waveform start differs from its association")
    rate = source.get("SampleRate")
    if (metadata.field_units.get("SampleRate") != "hertz"
            or rate is None or pd.isna(rate) or not isfinite(float(rate))
            or waveform.get("sampling_rate_hz") != trace.stats.sampling_rate
            or not isfinite(trace.stats.sampling_rate) or trace.stats.sampling_rate <= 0
            or not trace.stats.sampling_rate - SAMPLE_RATE_TOLERANCE_HZ
            <= rate <= trace.stats.sampling_rate + SAMPLE_RATE_TOLERANCE_HZ):
        raise ValueError(f"{trace.id}: waveform rate disagrees with its association")
    _float32_value(trace.stats.delta, f"{trace.id}: delta")
    if _float32_value(trace.stats.calib, f"{trace.id}: calib") == -12345:
        raise ValueError(f"{trace.id}: calib collides with the SAC undefined value")

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
        if pressure != 0 and headers["stdp"] == 0:
            raise ValueError(f"{trace.id}: stdp underflows before SAC float32 storage")
        _float32_value(headers["stdp"], f"{trace.id}: stdp")

    sac = SACTrace.from_obspy_trace(trace, keep_sac_header=False)
    for key, value in headers.items():
        setattr(sac, key, value)
    _float32_value(sac.e, f"{trace.id}: e")
    # Compute summaries from the actual stored values, using float64 accumulation
    # so a valid float32 array near its maximum does not overflow its mean.
    sac.data = samples.astype(np.float64)
    # Exclusive creation also protects against collisions between loop iterations.
    with Path(path).open("xb") as handle:
        sac.write(handle, byteorder="little")
