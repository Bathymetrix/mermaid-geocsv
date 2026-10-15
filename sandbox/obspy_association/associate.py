"""Experimental in-memory association for original processed MERMAID traces.

This sandbox interface is not yet part of ``mermaid.geocsv``'s public API.
"""

from math import isfinite
from decimal import Decimal, InvalidOperation

from obspy import Stream, Trace
from obspy.core.util import AttribDict
import numpy as np
import pandas as pd

from mermaid.geocsv import GeoCSVMetadata


IDENTITY = {"Network": "network", "Station": "station",
            "Location": "location", "Channel": "channel"}
SAMPLE_RATE_TOLERANCE_HZ = 0.01  # Provisional; revisit against MER timing precision.


def _project_sac():
    raise NotImplementedError("SAC projection is reserved but not implemented")


def _coordinates(trace, row, metadata):
    missing = [field for field in ("Latitude", "Longitude")
               if pd.isna(row.get(field, pd.NA))]
    if missing:
        raise ValueError(f"{trace.id}: coordinate projection requires both Latitude "
                         f"and Longitude; missing {', '.join(missing)}")
    projected = {}
    for field, key, unit, lower, upper in (
        ("Latitude", "latitude", "degrees_north", -90, 90),
        ("Longitude", "longitude", "degrees_east", -180, 180),
    ):
        value = row[field]
        if metadata.field_units.get(field) != unit:
            raise ValueError(f"{trace.id}: {field} requires declared units {unit}")
        if not isfinite(float(value)) or not lower <= value <= upper:
            raise ValueError(f"{trace.id}: invalid {field} {value!r}")
        projected[key] = float(value)
    projected["elevation"] = 0.0  # Sea-level convention; no geoid model.
    return AttribDict(projected)


def associate(waveforms, records, *, project_sac=False, time_tolerance=None,
              allow_merge=False):
    """Associate a Trace or Stream with event rows returned by geocsv.read.

    Validate all matches before modifying any trace; return None. By default require exact
    SNCL, UTC times within the source timestamp resolution by default, exact
    sample count, and rate difference <= 0.01 Hz. Waveform core fields remain
    authoritative. Quality is retained separately and is not a match filter.
    Guarantees end at initial association. ``project_sac=True`` is reserved.
    Missing Latitude or Longitude fails. Destination containers must be absent:
    geocsv, coordinates, and sac when requested. Nothing is merged or overwritten.
    ``time_tolerance`` overrides the per-record default in seconds, including
    zero for exact matching. Comparisons preserve full nanosecond values.
    ``allow_merge=True`` permits a longer, unmasked trace anchored to exactly
    one SNCL/start-time row with compatible rate and full anchor duration.
    No waveform merging is performed. ``stats.geocsv.association`` records
    ``one_segment`` for a standard match or ``first_segment`` for this fallback.
    In the latter case, source fields describe only the anchor; its location
    is adopted for the entire trace without reconstructing merge provenance.
    """
    tolerance_ns = None
    if time_tolerance is not None:
        try:
            tolerance_ns = Decimal(str(time_tolerance)) * 1_000_000_000
        except InvalidOperation as exc:
            raise ValueError("time_tolerance must be finite, nonnegative seconds") from exc
        if not tolerance_ns.is_finite() or tolerance_ns < 0:
            raise ValueError("time_tolerance must be finite, nonnegative seconds")
    if isinstance(waveforms, Trace):
        traces = [waveforms]
    elif isinstance(waveforms, Stream):
        traces = list(waveforms)
    else:
        raise TypeError("waveforms must be an ObsPy Trace or Stream")

    destinations = ("geocsv", "coordinates", "sac") if project_sac else ("geocsv", "coordinates")
    for trace in traces:
        for key in destinations:
            if key in trace.stats:
                raise ValueError(f"{trace.id}: stats.{key} already exists; "
                                 "association requires absent destination containers")
    if project_sac:
        _project_sac()

    datasets = []
    required = set(IDENTITY) | {"MethodIdentifier", "StartTime", "SampleRate",
                                "SampleCount"}
    for dataset_index, frame in enumerate(records):
        if "MethodIdentifier" not in frame:
            continue
        events = frame.loc[frame["MethodIdentifier"].str.startswith(
            "Algorithm(event):", na=False)]
        if events.empty:
            continue
        missing = required - set(events.columns)
        if missing:
            raise ValueError(f"event dataset {dataset_index} lacks columns {sorted(missing)}")
        metadata = frame.attrs.get("geocsv")
        if not isinstance(metadata, GeoCSVMetadata):
            raise ValueError(f"dataset {dataset_index} lacks geocsv.read provenance")
        if metadata.field_units.get("SampleRate") != "hertz":
            raise ValueError(f"dataset {dataset_index}: SampleRate requires declared units hertz")
        reserved = {"source_record_index", "dataset_index", "metadata", "association"} & set(frame.columns)
        if reserved:
            raise ValueError(f"event columns collide with attachment keys: {sorted(reserved)}")
        datasets.append((dataset_index, events, metadata))

    plans = []
    for trace_index, trace in enumerate(traces):
        if trace.stats.npts != len(trace.data):
            raise ValueError(f"{trace.id}: npts differs from data length; load the samples")
        rate = trace.stats.sampling_rate
        if not isfinite(rate) or rate <= 0:
            raise ValueError(f"{trace.id}: sampling_rate must be finite and positive")
        if np.ma.is_masked(trace.data):
            raise ValueError(f"trace {trace_index} {trace.id}: masked gaps prevent "
                             "contiguous segment association")
        matches, anchors, candidates = [], [], []
        for dataset_index, events, metadata in datasets:
            mask = pd.Series(True, index=events.index)
            for field, key in IDENTITY.items():
                mask &= events[field].eq(trace.stats[key]).fillna(False)
            for record_index, row in events.loc[mask].iterrows():
                time = row["StartTime"]
                if pd.isna(time) or pd.Timestamp(time).tzinfo is None:
                    raise ValueError(f"{trace.id}: record {record_index} lacks aware StartTime")
                allowed_ns = tolerance_ns
                if allowed_ns is None:
                    allowed_ns = metadata.datetime_resolution_ns.get("StartTime", {}).get(record_index)
                    if allowed_ns is None:
                        raise ValueError(f"{trace.id}: record {record_index} lacks source "
                                         "time resolution; reread GeoCSV or set time_tolerance")
                difference_ns = abs(pd.Timestamp(time).value - trace.stats.starttime.ns)
                if difference_ns > allowed_ns:
                    continue
                count, source_rate = row["SampleCount"], row["SampleRate"]
                reasons = []
                if pd.isna(count) or count != trace.stats.npts:
                    reasons.append(f"SampleCount={count} differs from npts={trace.stats.npts}")
                rate_ok = (not pd.isna(source_rate) and isfinite(float(source_rate))
                           and float(source_rate) > 0
                           and abs(rate - float(source_rate)) <= SAMPLE_RATE_TOLERANCE_HZ)
                if not rate_ok:
                    reasons.append(f"SampleRate={source_rate} incompatible with {rate} Hz")
                match = (dataset_index, record_index, row, metadata)
                anchors.append((match, rate_ok))
                candidates.append({"source": str(metadata.source_path),
                                   "dataset": dataset_index, "record": record_index,
                                   "reasons": reasons})
                if reasons:
                    continue
                matches.append(match)
        association = "one_segment"
        if not matches and allow_merge and len(anchors) == 1:
            anchor, rate_ok = anchors[0]
            dataset_index, record_index, row, metadata = anchor
            count, source_rate = row["SampleCount"], row["SampleRate"]
            if rate_ok:
                if (not pd.isna(count) and isfinite(float(count)) and count > 0
                        and float(count).is_integer() and trace.stats.npts > count
                        and (trace.stats.npts - 1) / rate >= (count - 1) / float(source_rate)):
                    matches = [anchor]
                    association = "first_segment"
                else:
                    candidates[0]["reasons"].append(
                        "allow_merge requires a longer trace covering the full anchor duration "
                        "and a positive integer anchor SampleCount")
        if len(matches) != 1:
            outcome = "no match" if not matches else f"ambiguous ({len(matches)} matches)"
            if not matches and allow_merge and len(anchors) > 1:
                outcome = (f"ambiguous ({len(anchors)} SNCL/start-time anchors; "
                           "no standard match)")
            raise ValueError(f"trace {trace_index} {trace.id} at {trace.stats.starttime} "
                             f"through {trace.stats.endtime}: {outcome}; "
                             f"required npts={trace.stats.npts}, rate={rate} Hz "
                             f"within {SAMPLE_RATE_TOLERANCE_HZ} Hz; "
                             f"SNCL/time candidates (source, dataset, record, reasons): {candidates}")
        dataset_index, record_index, row, metadata = matches[0]
        attachment = AttribDict({**row.to_dict(), "source_record_index": record_index,
                                 "dataset_index": dataset_index, "metadata": metadata,
                                 "association": association})
        plans.append((trace, attachment, _coordinates(trace, row, metadata)))

    for trace, attachment, coordinates in plans:
        trace.stats.geocsv = attachment
        trace.stats.coordinates = coordinates
