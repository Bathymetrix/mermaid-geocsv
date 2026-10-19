"""In-memory association for original processed MERMAID traces."""

from bisect import bisect_left, bisect_right
from decimal import Decimal, InvalidOperation
from math import isfinite

from obspy import Stream, Trace
from obspy.core.util import AttribDict
import numpy as np
import pandas as pd

from .read import GeoCSVMetadata


IDENTITY = {"Network": "network", "Station": "station",
            "Location": "location", "Channel": "channel"}
SAMPLE_RATE_TOLERANCE_HZ = 0.01  # Provisional; revisit against MER timing precision.


def _invalid_identity_fields(codes):
    """Only Location may be a known empty string; missing codes are invalid."""
    return [field for field, code in zip(IDENTITY, codes)
            if not isinstance(code, str)
            or (not code.strip() and not (field == "Location" and code == ""))]


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


def _validate_merged_coverage(trace, datasets, tolerance_ns):
    """Require exact, gap-free source sample coverage on the waveform grid."""
    sncl = tuple(trace.stats[key] for key in IDENTITY.values())
    rate = Decimal(str(trace.stats.sampling_rate))
    intervals = []
    for dataset_index, event_index, metadata in datasets:
        indexed = event_index.get(sncl)
        if indexed is None:
            continue
        events, timed_rows, timed_times, _ = indexed
        first = bisect_left(timed_times, trace.stats.starttime.ns - tolerance_ns)
        last = bisect_right(timed_times, trace.stats.endtime.ns + tolerance_ns)
        for time_ns, record_index in timed_rows[first:last]:
            row = events.loc[record_index]
            context = (f"{trace.id}: merged coverage source {metadata.source_path}, "
                       f"dataset {dataset_index}, record {record_index}")
            count, source_rate = row['SampleCount'], row['SampleRate']
            if (pd.isna(count) or not isfinite(float(count)) or count <= 0
                    or not float(count).is_integer()):
                raise ValueError(f"{context}: requires a positive integer SampleCount")
            if (pd.isna(source_rate) or not isfinite(float(source_rate))
                    or float(source_rate) <= 0
                    or not trace.stats.sampling_rate - SAMPLE_RATE_TOLERANCE_HZ
                    <= float(source_rate)
                    <= trace.stats.sampling_rate + SAMPLE_RATE_TOLERANCE_HZ):
                raise ValueError(f"{context}: incompatible SampleRate={source_rate}")
            offset_ns = time_ns - trace.stats.starttime.ns
            first_sample = round(Decimal(offset_ns) * rate / 1_000_000_000)
            grid_start_ns = round(Decimal(first_sample) * 1_000_000_000 / rate)
            if abs(offset_ns - grid_start_ns) > tolerance_ns:
                raise ValueError(f"{context}: start time is off the waveform sample grid "
                                 "beyond time_tolerance")
            if any(abs(offset_ns - round(Decimal(index) * 1_000_000_000 / rate))
                   <= tolerance_ns for index in (first_sample - 1, first_sample + 1)):
                raise ValueError(f"{context}: time_tolerance permits multiple waveform "
                                 "sample indices; merged coverage is ambiguous")
            stop_sample = first_sample + int(count)
            source_last_ns = offset_ns + round(
                Decimal(int(count) - 1) * 1_000_000_000 / Decimal(str(source_rate)))
            waveform_last_ns = round(Decimal(stop_sample - 1) * 1_000_000_000 / rate)
            if abs(source_last_ns - waveform_last_ns) > tolerance_ns:
                raise ValueError(f"{context}: source rate accumulates last-sample "
                                 "misalignment beyond time_tolerance")
            if first_sample < 0 or stop_sample > trace.stats.npts:
                raise ValueError(f"{context}: source sample range "
                                 f"[{first_sample}, {stop_sample}) exceeds waveform "
                                 f"range [0, {trace.stats.npts})")
            intervals.append((first_sample, stop_sample))
    covered = 0
    for first_sample, stop_sample in sorted(intervals):
        if first_sample > covered:
            raise ValueError(f"{trace.id}: merged coverage has a gap at sample {covered}; "
                             f"next source range begins at {first_sample}")
        covered = max(covered, stop_sample)
    if covered != trace.stats.npts:
        raise ValueError(f"{trace.id}: merged coverage contains {covered} unique samples "
                         f"after overlap removal; requires exactly npts={trace.stats.npts}")


def associate(waveforms, records, *, time_tolerance=0.0001, allow_merge=False):
    """Associate a Trace or Stream with event rows returned by geocsv.read.

    Validate all matches before modifying any trace; return None. By default require exact
    SNCL, UTC times within 100 microseconds by default, exact
    sample count, and rate difference <= 0.01 Hz. Waveform core fields remain
    authoritative. Quality is retained separately and is not a match filter.
    Guarantees end at initial association. SAC projection is deferred.
    Missing Latitude or Longitude fails. Destination containers must be absent:
    geocsv and coordinates. Nothing is merged or overwritten.
    Source columns must not collide with association keys or attributes and
    methods of the ObsPy AttribDict used for stats.geocsv.
    Only Location may be a known empty string; no SNCL field may be missing.
    Source preflight rejects invalid event identities and duplicate complete
    SNCL/UTC-time/count/rate keys. All trace matches resolve before projections.
    ``time_tolerance`` is finite nonnegative seconds, including
    zero for exact matching. Comparisons preserve full nanosecond values.
    ``stats.geocsv.starttime_difference_seconds`` records waveform minus source
    start time, computed in integer nanoseconds before conversion to seconds.
    ``allow_merge=True`` requires a unique SNCL/start-time anchor and exact,
    gap-free source sample coverage after overlap removal on the waveform grid.
    No waveform merging is performed. ``stats.geocsv.association`` records
    ``one_segment`` for a standard match or ``first_segment`` for this fallback.
    In the latter case, source fields describe only the anchor; its location
    is adopted for the entire trace without reconstructing merge provenance.
    """
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

    for trace in traces:
        for key in ("geocsv", "coordinates"):
            if key in trace.stats:
                raise ValueError(f"{trace.id}: stats.{key} already exists; "
                                 "association requires absent destination containers")
    datasets = []
    seen_events = {}
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
        reserved = {"source_record_index", "dataset_index", "metadata", "association",
                    "starttime_difference_seconds"} & set(frame.columns)
        if reserved:
            raise ValueError(f"event columns collide with attachment keys: {sorted(reserved)}")
        container_conflicts = set(frame.columns) & set(dir(AttribDict))
        if container_conflicts:
            raise ValueError(
                f"event dataset {dataset_index} ({metadata.source_path}): columns collide "
                f"with reserved ObsPy AttribDict attributes or methods: "
                f"{sorted(container_conflicts)}; stats.geocsv uses this container, "
                "so source columns must not shadow its attributes or methods")
        event_index = {}
        for sncl, group in events.groupby(list(IDENTITY), sort=False, dropna=False):
            invalid = _invalid_identity_fields(sncl)
            if invalid:
                raise ValueError(
                    f"{metadata.source_path}, dataset {dataset_index}, records "
                    f"{list(group.index)}: invalid event identity fields {invalid}; "
                    "Network, Station, Channel require nonempty strings; Location "
                    "may be an empty string but must not be missing")
            timed_rows, incomplete_rows = [], []
            for record_index, row in group.iterrows():
                time = row["StartTime"]
                if pd.isna(time) or pd.Timestamp(time).tzinfo is None:
                    incomplete_rows.append((record_index,
                                            "missing or timezone-naive StartTime; row is ineligible"))
                    continue
                time_ns = pd.Timestamp(time).value
                count, source_rate = row['SampleCount'], row['SampleRate']
                if (not pd.isna(count) and isfinite(float(count)) and count > 0
                        and float(count).is_integer() and not pd.isna(source_rate)
                        and isfinite(float(source_rate)) and source_rate > 0):
                    key = (sncl, time_ns, int(count), float(source_rate))
                    source = (str(metadata.source_path), dataset_index, record_index)
                    if key in seen_events:
                        raise ValueError(
                            f"ambiguous duplicate GeoCSV event rows for SNCL {sncl}, "
                            f"UTC StartTime={pd.Timestamp(time).tz_convert('UTC').isoformat()}, "
                            f"SampleCount={count}, SampleRate={source_rate}: "
                            f"(source, dataset, record) {seen_events[key]} and {source}; "
                            "quality and coordinates do not disambiguate matching keys")
                    seen_events[key] = source
                timed_rows.append((time_ns, record_index))
            timed_rows.sort()
            timed_times = tuple(item[0] for item in timed_rows)
            event_index[sncl] = (group, timed_rows, timed_times, incomplete_rows)
        datasets.append((dataset_index, event_index, metadata))

    associations = []
    for trace_index, trace in enumerate(traces):
        sncl = tuple(trace.stats[key] for key in IDENTITY.values())
        invalid = _invalid_identity_fields(sncl)
        if invalid:
            raise ValueError(f"trace {trace_index} {trace.id}: invalid waveform identity "
                             f"fields {invalid}; only Location may be an empty string; "
                             "no identity field may be missing")
        if trace.stats.npts != len(trace.data):
            raise ValueError(f"{trace.id}: npts differs from data length; load the samples")
        rate = trace.stats.sampling_rate
        if not isfinite(rate) or rate <= 0:
            raise ValueError(f"{trace.id}: sampling_rate must be finite and positive")
        if np.ma.is_masked(trace.data):
            raise ValueError(f"trace {trace_index} {trace.id}: masked gaps prevent "
                             "contiguous segment association")
        matches, anchors, candidates, incomplete_events = [], [], [], []
        trace_time_ns = trace.stats.starttime.ns
        for dataset_index, event_index, metadata in datasets:
            indexed = event_index.get(sncl)
            if indexed is None:
                continue
            events, timed_rows, timed_times, incomplete_rows = indexed
            incomplete_events.extend({
                "source": str(metadata.source_path), "dataset": dataset_index,
                "record": record_index, "reason": reason,
            } for record_index, reason in incomplete_rows)
            first = bisect_left(timed_times, trace_time_ns - tolerance_ns)
            last = bisect_right(timed_times, trace_time_ns + tolerance_ns)
            for time_ns, record_index in timed_rows[first:last]:
                row = events.loc[record_index]
                difference_ns = abs(time_ns - trace_time_ns)
                if difference_ns > tolerance_ns:
                    continue
                count, source_rate = row["SampleCount"], row["SampleRate"]
                reasons = []
                if pd.isna(count) or count != trace.stats.npts:
                    reasons.append(f"SampleCount={count} differs from npts={trace.stats.npts}")
                rate_ok = (not pd.isna(source_rate) and isfinite(float(source_rate))
                           and float(source_rate) > 0
                           and rate - SAMPLE_RATE_TOLERANCE_HZ <= float(source_rate)
                           <= rate + SAMPLE_RATE_TOLERANCE_HZ)
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
                        and float(count).is_integer() and trace.stats.npts > count):
                    _validate_merged_coverage(trace, datasets, tolerance_ns)
                    matches = [anchor]
                    association = "first_segment"
                else:
                    candidates[0]["reasons"].append(
                        "allow_merge requires a longer trace "
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
                             f"SNCL/time candidates (source, dataset, record, reasons): {candidates}; "
                             f"incomplete event rows (source, dataset, record, reason): "
                             f"{incomplete_events}")
        associations.append((trace, matches[0], association))

    plans = []
    for trace, (dataset_index, record_index, row, metadata), association in associations:
        starttime_difference_seconds = (
            trace.stats.starttime.ns - pd.Timestamp(row["StartTime"]).value
        ) / 1_000_000_000
        attachment = AttribDict({**row.to_dict(), "source_record_index": record_index,
                                 "dataset_index": dataset_index, "metadata": metadata,
                                 "association": association,
                                 "starttime_difference_seconds": starttime_difference_seconds})
        plans.append((trace, attachment, _coordinates(trace, row, metadata)))

    for trace, attachment, coordinates in plans:
        trace.stats.geocsv = attachment
        trace.stats.coordinates = coordinates
