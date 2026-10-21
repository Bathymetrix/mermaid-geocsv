"""In-memory original-segment and containing-anchor MERMAID association."""

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


def _source_name(metadata):
    if metadata.source_path is not None:
        return str(metadata.source_path)
    return metadata.download.url if metadata.download is not None else "<memory>"


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


def _source_last_sample_ns(time_ns, row):
    """Return the inclusive source endpoint when count and rate are usable."""
    count, rate = row["SampleCount"], row["SampleRate"]
    if (pd.isna(count) or not isfinite(float(count)) or count <= 0
            or not float(count).is_integer() or pd.isna(rate)
            or not isfinite(float(rate)) or rate <= 0):
        return None
    return time_ns + round(Decimal(int(count) - 1) * 1_000_000_000 / Decimal(str(rate)))


def _record_context(dataset_index, record_index, metadata):
    return {"source": _source_name(metadata), "dataset": dataset_index,
            "record": record_index,
            "line": metadata.record_line_numbers.get(record_index, "unknown")}


def _overlapping_events(trace, datasets, tolerance_ns):
    """Find source intervals intersecting the trace, including earlier starts."""
    sncl = tuple(trace.stats[key] for key in IDENTITY.values())
    for dataset_index, event_index, metadata in datasets:
        indexed = event_index.get(sncl)
        if indexed is None:
            continue
        events, timed_rows, timed_times, _, latest_ends = indexed
        first = bisect_left(latest_ends, trace.stats.starttime.ns - tolerance_ns)
        last = bisect_right(timed_times, trace.stats.endtime.ns + tolerance_ns)
        for time_ns, record_index in timed_rows[first:last]:
            row = events.loc[record_index]
            end_ns = _source_last_sample_ns(time_ns, row)
            if end_ns is not None and end_ns < trace.stats.starttime.ns - tolerance_ns:
                continue
            yield dataset_index, record_index, row, metadata


def _validate_coverage(trace, overlapping, tolerance_ns):
    """Require gap-free source sample coverage, clipped to the waveform grid."""
    rate = Decimal(str(trace.stats.sampling_rate))
    intervals = []
    for dataset_index, record_index, row, metadata in overlapping:
        context = (f"{trace.id}: source coverage "
                   f"{_record_context(dataset_index, record_index, metadata)}")
        count, source_rate = row["SampleCount"], row["SampleRate"]
        if (pd.isna(count) or not isfinite(float(count)) or count <= 0
                or not float(count).is_integer()):
            raise ValueError(f"{context}: requires a positive integer SampleCount")
        if (pd.isna(source_rate) or not isfinite(float(source_rate))
                or float(source_rate) <= 0
                or not trace.stats.sampling_rate - SAMPLE_RATE_TOLERANCE_HZ
                <= float(source_rate)
                <= trace.stats.sampling_rate + SAMPLE_RATE_TOLERANCE_HZ):
            raise ValueError(f"{context}: incompatible SampleRate={source_rate}")
        offset_ns = pd.Timestamp(row["StartTime"]).value - trace.stats.starttime.ns
        first_sample = round(Decimal(offset_ns) * rate / 1_000_000_000)
        stop_sample = first_sample + int(count)
        clipped_first = max(0, first_sample)
        clipped_stop = min(trace.stats.npts, stop_sample)
        if clipped_stop <= clipped_first:
            continue
        # Only the retained source samples must align. Source data outside the
        # downloaded window do not have to fit inside that window.
        for sample in (clipped_first, clipped_stop - 1):
            source_ns = offset_ns + round(
                Decimal(sample - first_sample) * 1_000_000_000 / Decimal(str(source_rate)))
            waveform_ns = round(Decimal(sample) * 1_000_000_000 / rate)
            if abs(source_ns - waveform_ns) > tolerance_ns:
                raise ValueError(f"{context}: retained sample {sample} is off the waveform "
                                 "sample grid beyond time_tolerance")
            if any(abs(source_ns - round(Decimal(index) * 1_000_000_000 / rate))
                   <= tolerance_ns for index in (sample - 1, sample + 1)):
                raise ValueError(f"{context}: time_tolerance permits multiple waveform "
                                 "sample indices; source coverage is ambiguous")
        intervals.append((clipped_first, clipped_stop))
    covered = 0
    for first_sample, stop_sample in sorted(intervals):
        if first_sample > covered:
            raise ValueError(f"{trace.id}: source coverage has a gap at sample {covered}; "
                             f"next source range begins at {first_sample}")
        covered = max(covered, stop_sample)
    if covered != trace.stats.npts:
        raise ValueError(f"{trace.id}: source coverage contains {covered} unique samples "
                         f"after clipping and overlap removal; requires exactly "
                         f"npts={trace.stats.npts}")


def associate(waveforms, records, *, time_tolerance=0.0001, allow_first_segment=False):
    """Associate a Trace or Stream with event rows returned by geocsv.read.

    Validate all matches before modifying any trace; return None. By default require exact
    SNCL, UTC times within 100 microseconds by default, exact
    sample count, and rate difference <= 0.01 Hz. Waveform core fields remain
    authoritative. Quality is retained separately and is not a match filter.
    Guarantees end at initial association. SAC export is a separate operation.
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
    ``allow_first_segment=True`` requires a unique same-SNCL source interval
    containing the first sample, never merely the nearest preceding row.
    Require gap-free source sample coverage after clipping to the waveform
    grid and counting overlaps once. Multiple containing anchors raise.
    No waveform merging is performed. ``stats.geocsv.association`` records
    ``one_segment`` for a standard match or ``first_segment`` for this fallback.
    In the latter case, source fields describe only the anchor; its location
    is adopted for the entire trace without reconstructing merge provenance.
    Source record indices and physical starting line numbers identify failures.
    """
    if not isinstance(allow_first_segment, bool):
        raise TypeError("allow_first_segment must be a bool")
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
                    "starttime_difference_seconds", "waveform_sample_count"} & set(frame.columns)
        if reserved:
            raise ValueError(f"event columns collide with attachment keys: {sorted(reserved)}")
        container_conflicts = set(frame.columns) & set(dir(AttribDict))
        if container_conflicts:
            raise ValueError(
                f"event dataset {dataset_index} ({_source_name(metadata)}): columns collide "
                f"with reserved ObsPy AttribDict attributes or methods: "
                f"{sorted(container_conflicts)}; stats.geocsv uses this container, "
                "so source columns must not shadow its attributes or methods")
        event_index = {}
        for sncl, group in events.groupby(list(IDENTITY), sort=False, dropna=False):
            invalid = _invalid_identity_fields(sncl)
            if invalid:
                raise ValueError(
                    f"{_source_name(metadata)}, dataset {dataset_index}, records "
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
                    source = _record_context(dataset_index, record_index, metadata)
                    if key in seen_events:
                        end_ns = _source_last_sample_ns(time_ns, row)
                        affected = [
                            f"trace {index} {trace.id} at {trace.stats.starttime} "
                            f"through {trace.stats.endtime}"
                            for index, trace in enumerate(traces)
                            if tuple(trace.stats[name] for name in IDENTITY.values()) == sncl
                            and time_ns - tolerance_ns <= trace.stats.starttime.ns
                            <= end_ns + tolerance_ns]
                        raise ValueError(
                            f"ambiguous duplicate GeoCSV event rows for SNCL {sncl}, "
                            f"UTC StartTime={pd.Timestamp(time).tz_convert('UTC').isoformat()}, "
                            f"SampleCount={count}, SampleRate={source_rate}: "
                            f"(source, dataset, record) {seen_events[key]} and {source}; "
                            f"affected traces: {affected}; source line numbers are one-based "
                            "physical starting lines. Quality and coordinates do not "
                            "disambiguate matching keys. No anchor was chosen; resolve "
                            "the source ambiguity or fill headers manually outside "
                            "geocsv.associate")
                    seen_events[key] = source
                timed_rows.append((time_ns, record_index))
            timed_rows.sort()
            timed_times = tuple(item[0] for item in timed_rows)
            latest_ends = []
            for time_ns, record_index in timed_rows:
                end_ns = _source_last_sample_ns(time_ns, group.loc[record_index])
                latest_ends.append(max(end_ns if end_ns is not None else time_ns,
                                       latest_ends[-1] if latest_ends else time_ns))
            event_index[sncl] = (group, timed_rows, timed_times, incomplete_rows, latest_ends)
        datasets.append((dataset_index, event_index, metadata))

    associations = []
    failures = []
    for trace_index, trace in enumerate(traces):
        sncl = tuple(trace.stats[key] for key in IDENTITY.values())
        invalid = _invalid_identity_fields(sncl)
        if invalid:
            raise ValueError(f"trace {trace_index} {trace.id}: invalid waveform identity "
                             f"fields {invalid}; only Location may be an empty string; "
                             "no identity field may be missing")
        if not len(trace.data):
            raise ValueError(f"{trace.id}: association requires nonempty loaded samples")
        if trace.stats.npts != len(trace.data):
            raise ValueError(f"{trace.id}: npts differs from data length; load the samples")
        rate = trace.stats.sampling_rate
        if not isfinite(rate) or rate <= 0:
            raise ValueError(f"{trace.id}: sampling_rate must be finite and positive")
        if np.ma.is_masked(trace.data):
            raise ValueError(f"trace {trace_index} {trace.id}: masked gaps prevent "
                             "contiguous segment association")
        matches, candidates, incomplete_events = [], [], []
        trace_time_ns = trace.stats.starttime.ns
        for dataset_index, event_index, metadata in datasets:
            indexed = event_index.get(sncl)
            if indexed is None:
                continue
            events, timed_rows, timed_times, incomplete_rows, _ = indexed
            incomplete_events.extend({
                "source": _source_name(metadata), "dataset": dataset_index,
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
                candidates.append({**_record_context(dataset_index, record_index, metadata),
                                   "reasons": reasons})
                if reasons:
                    continue
                matches.append(match)
        association = "one_segment"
        if allow_first_segment:
            overlapping = list(_overlapping_events(trace, datasets, tolerance_ns))
            anchors = []
            for match in overlapping:
                dataset_index, record_index, row, metadata = match
                source_ns = pd.Timestamp(row["StartTime"]).value
                end_ns = _source_last_sample_ns(source_ns, row)
                if (end_ns is not None and source_ns - tolerance_ns
                        <= trace_time_ns <= end_ns + tolerance_ns):
                    anchors.append(match)
            if len(anchors) > 1:
                contexts = [dict(_record_context(item[0], item[1], item[3]),
                                 StartTime=str(item[2]["StartTime"]),
                                 SampleCount=item[2]["SampleCount"],
                                 SampleRate=item[2]["SampleRate"])
                            for item in anchors]
                failures.append(
                    f"trace {trace_index} {trace.id} at {trace.stats.starttime} through "
                    f"{trace.stats.endtime}: ambiguous ({len(anchors)} containing anchor rows). "
                    f"Source candidates (zero-based record, one-based physical starting line): "
                    f"{contexts}. No anchor was chosen. Resolve the source ambiguity or "
                    "fill headers manually outside geocsv.associate.")
                continue
            if not matches and len(anchors) == 1:
                try:
                    _validate_coverage(trace, overlapping, tolerance_ns)
                except ValueError as exc:
                    failures.append(f"trace {trace_index} {trace.id}: {exc}")
                    continue
                matches = anchors
                association = "first_segment"
        if len(matches) != 1:
            outcome = "no match" if not matches else f"ambiguous ({len(matches)} matches)"
            if not matches and allow_first_segment and not anchors:
                outcome += " (no containing source segment for the waveform start)"
            failures.append(
                f"trace {trace_index} {trace.id} at {trace.stats.starttime} "
                f"through {trace.stats.endtime}: {outcome}; "
                f"required npts={trace.stats.npts}, rate={rate} Hz "
                f"within {SAMPLE_RATE_TOLERANCE_HZ} Hz; "
                f"SNCL/time candidates (source, dataset, record, line, reasons): {candidates}; "
                f"incomplete event rows (source, dataset, record, reason): {incomplete_events}")
            continue
        associations.append((trace, matches[0], association))

    if failures:
        raise ValueError("GeoCSV association failed; no traces were modified:\n"
                         + "\n".join(failures))

    plans = []
    for trace, (dataset_index, record_index, row, metadata), association in associations:
        starttime_difference_seconds = (
            trace.stats.starttime.ns - pd.Timestamp(row["StartTime"]).value
        ) / 1_000_000_000
        attachment = AttribDict({**row.to_dict(), "source_record_index": record_index,
                                 "dataset_index": dataset_index, "metadata": metadata,
                                 "association": association,
                                 "waveform_sample_count": trace.stats.npts,
                                 "starttime_difference_seconds": starttime_difference_seconds})
        plans.append((trace, attachment, _coordinates(trace, row, metadata)))

    for trace, attachment, coordinates in plans:
        trace.stats.geocsv = attachment
        trace.stats.coordinates = coordinates
