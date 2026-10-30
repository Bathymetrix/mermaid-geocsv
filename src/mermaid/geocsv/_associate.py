"""Match waveform-acquisition rows and project MERMAID station metadata."""

from bisect import bisect_left, bisect_right
from decimal import Decimal, InvalidOperation
from math import isfinite

from obspy import Stream, Trace, UTCDateTime
from obspy.core.util import AttribDict
from obspy.io.sac import SACTrace
import numpy as np
import pandas as pd

from ._read import GeoCSVMetadata


IDENTITY = {"Network": "network", "Station": "station",
            "Location": "location", "Channel": "channel"}
SAMPLE_RATE_TOLERANCE_HZ = 0.00001  # Absolute rate agreement, independent of grid placement.


def _source_name(metadata):
    if metadata.source_path is not None:
        return str(metadata.source_path)
    return metadata.download.url if metadata.download is not None else "<memory>"


def _invalid_identity_fields(codes, *, source=False):
    """Return invalid SNCL field names; only Location may be a known empty string."""
    return [field for field, code in zip(IDENTITY, codes)
            if not isinstance(code, str)
            or (not code.strip() and not (field == "Location" and code == ("  " if source else "")))]


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
    elevation = row.get("Elevation")
    if metadata.field_units.get("Elevation") != "meters":
        raise ValueError(f"{trace.id}: Elevation requires declared units meters")
    if elevation is None or pd.isna(elevation) or not isfinite(float(elevation)) or elevation != 0:
        raise ValueError(f"{trace.id}: requires explicit zero Recording Elevation")
    # Only the explicit zero sea-level reference is supported. No geoid model.
    projected["elevation"] = float(elevation)
    return AttribDict(projected)


def _sac_header(trace, row, metadata, coordinates):
    """Create ObsPy's fresh SAC baseline plus four station location fields."""
    pressure = row.get("WaterPressure")
    if pressure is None or pd.isna(pressure):
        quality = row.get("DataQuality")
        if not isinstance(quality, str) or quality != "D":
            raise ValueError(f"{trace.id}: missing WaterPressure; "
                             "only REQ source records (DataQuality D) may omit depth")
        depth = -12345.0  # SAC undefined; never borrow another record's pressure.
    else:
        if metadata.field_units.get("WaterPressure") != "mbar":
            raise ValueError(f"{trace.id}: WaterPressure requires declared units mbar")
        if not isfinite(float(pressure)) or pressure < 0:
            raise ValueError(f"{trace.id}: requires finite nonnegative WaterPressure")
        # MERMAID station depth for SAC stdp: 100 mbar = 1 dbar, approximately 1 m.
        # This station projection supplies no earthquake-source (ev*) metadata.
        depth = float(pressure) / 100

    sac = SACTrace.from_obspy_trace(trace, keep_sac_header=False)
    headers = sac.to_obspy_trace(round_sampling_interval=False).stats.sac
    headers.update({"stla": coordinates.latitude, "stlo": coordinates.longitude,
                    "stel": float(row["Elevation"]), "stdp": depth})
    return headers


def _source_last_sample_ns(time_ns, row):
    """Return last-sample UTC nanoseconds, or None for unusable count/rate."""
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
    """Yield same-SNCL interval candidates overlapping the trace within tolerance."""
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


def _association_details(trace, anchor, association_type, ranges):
    """Snapshot the source ranges and alignment evidence used for this trace."""
    rate = Decimal(str(trace.stats.sampling_rate))
    segments = []
    max_grid = None
    max_rate = None
    # Stable ordering also determines the reported source/sample in a tie.
    ranges = sorted(ranges, key=lambda item: (
        pd.Timestamp(item[0][2]["Time"]).value, item[0][0], item[0][1]))
    for match, first_sample, clipped_first, clipped_stop in ranges:
        dataset_index, record_index, row, metadata = match
        start_ns = pd.Timestamp(row["Time"]).value
        source_rate = Decimal(str(row["SampleRate"]))
        reference = {"dataset_index": dataset_index,
                     "source_record_index": int(record_index),
                     "source_line_number": metadata.record_line_numbers.get(record_index)}
        segments.append(AttribDict({
            **{key: row[field] for field, key in IDENTITY.items()},
            "starttime": UTCDateTime(ns=start_ns),
            "endtime": UTCDateTime(ns=_source_last_sample_ns(start_ns, row)),
            "sampling_rate_hz": float(source_rate),
            "sample_count": int(row["SampleCount"]),
            **reference,
            "waveform_sample_start": clipped_first,
            "waveform_sample_stop": clipped_stop,
        }))
        offset_ns = start_ns - trace.stats.starttime.ns
        for sample in (clipped_first, clipped_stop - 1):
            source_ns = offset_ns + round(
                Decimal(sample - first_sample) * 1_000_000_000 / source_rate)
            waveform_ns = round(Decimal(sample) * 1_000_000_000 / rate)
            difference_ns = abs(source_ns - waveform_ns)
            if max_grid is None or difference_ns > max_grid[0]:
                max_grid = (difference_ns, {**reference, "waveform_sample_index": sample})
        difference_hz = abs(float(source_rate) - trace.stats.sampling_rate)
        if max_rate is None or difference_hz > max_rate[0]:
            max_rate = (difference_hz, reference)
    return AttribDict({
        "type": association_type,
        "waveform": {
            **{key: trace.stats[key] for key in IDENTITY.values()},
            "starttime": UTCDateTime(ns=trace.stats.starttime.ns),
            "endtime": UTCDateTime(ns=trace.stats.endtime.ns),
            "sampling_rate_hz": trace.stats.sampling_rate,
            "sample_count": trace.stats.npts,
        },
        "coverage_segments": tuple(segments),
        "waveform_start_offset_seconds": (
            trace.stats.starttime.ns - pd.Timestamp(anchor[2]["Time"]).value
        ) / 1_000_000_000,
        "max_sample_grid_offset": {"seconds": max_grid[0] / 1_000_000_000,
                                   **max_grid[1]},
        "max_sample_rate_difference": {"hz": max_rate[0], **max_rate[1]},
    })


def _validate_coverage(trace, overlapping):
    """Return clipped source ranges with unambiguous, gap-free grid coverage."""
    rate = Decimal(str(trace.stats.sampling_rate))
    intervals = []
    ranges = []
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
        offset_ns = pd.Timestamp(row["Time"]).value - trace.stats.starttime.ns
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
            # Compare in sample units before rounding the waveform time to ns.
            # A half-sample tie has no unique placement, even at a window edge.
            displacement = Decimal(source_ns) * rate / 1_000_000_000 - sample
            if abs(displacement) == Decimal("0.5"):
                raise ValueError(f"{context}: retained sample {sample} is exactly halfway "
                                 "between waveform sample indices; source coverage is ambiguous")
            if abs(displacement) > Decimal("0.5"):
                raise ValueError(f"{context}: retained sample {sample} is off the waveform "
                                 "sample grid by more than half a sample interval")
        intervals.append((clipped_first, clipped_stop))
        ranges.append(((dataset_index, record_index, row, metadata),
                       first_sample, clipped_first, clipped_stop))
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

    return ranges


def associate(waveforms, records, *, time_tolerance=0.001, allow_first_segment=False,
              create_sac_header=False):
    """Validate and attach metadata for the public association operation.

    See ``mermaid.geocsv.associate`` for parameters, errors, and guarantees.
    """
    if not isinstance(allow_first_segment, bool):
        raise TypeError("allow_first_segment must be a bool")
    if not isinstance(create_sac_header, bool):
        raise TypeError("create_sac_header must be a bool")
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

    destinations = (("geocsv", "coordinates", "sac") if create_sac_header
                    else ("geocsv", "coordinates"))
    for trace in traces:
        for key in destinations:
            if key in trace.stats:
                raise ValueError(f"{trace.id}: stats.{key} already exists; "
                                 "association requires absent destination containers")
    datasets = []
    seen_events = {}
    required = set(IDENTITY) | {"MethodIdentifier", "Time", "SampleRate",
                                "SampleCount"}
    for dataset_index, frame in enumerate(records):
        if "MethodIdentifier" not in frame:
            continue
        events = frame.loc[frame["MethodIdentifier"].str.startswith(
            "Derivation:Recording:", na=False)]
        if events.empty:
            continue
        missing = required - set(events.columns)
        if missing:
            raise ValueError(f"event dataset {dataset_index} lacks columns {sorted(missing)}")
        metadata = frame.attrs.get("geocsv")
        if not isinstance(metadata, GeoCSVMetadata) or metadata.schema_version != "1.0.0":
            raise ValueError(f"dataset {dataset_index} lacks geocsv.read provenance")
        if metadata.field_units.get("SampleRate") != "hertz":
            raise ValueError(f"dataset {dataset_index}: SampleRate requires declared units hertz")
        reserved = {"source_record_index", "dataset_index", "metadata",
                    "association"} & set(frame.columns)
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
            invalid = _invalid_identity_fields(sncl, source=True)
            if invalid:
                raise ValueError(
                    f"{_source_name(metadata)}, dataset {dataset_index}, records "
                    f"{list(group.index)}: invalid event identity fields {invalid}; "
                    "Network, Station, Channel require nonempty strings; Location "
                    "requires a nonempty code or two literal spaces")
            # Compare the defined source blank code without rewriting either identity.
            sncl = tuple("" if field == "Location" and code == "  " else code
                         for field, code in zip(IDENTITY, sncl))
            timed_rows, incomplete_rows = [], []
            for record_index, row in group.iterrows():
                time = row["Time"]
                if pd.isna(time) or pd.Timestamp(time).tzinfo is None:
                    incomplete_rows.append((record_index,
                                            "missing or timezone-naive Time; row is ineligible"))
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
                            f"UTC Time={pd.Timestamp(time).tz_convert('UTC').isoformat()}, "
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
        association_type = "single_segment"
        ranges = None
        if allow_first_segment:
            overlapping = list(_overlapping_events(trace, datasets, tolerance_ns))
            anchors = []
            for match in overlapping:
                dataset_index, record_index, row, metadata = match
                source_ns = pd.Timestamp(row["Time"]).value
                end_ns = _source_last_sample_ns(source_ns, row)
                if (end_ns is not None and source_ns - tolerance_ns
                        <= trace_time_ns <= end_ns + tolerance_ns):
                    anchors.append(match)
            if len(anchors) > 1:
                contexts = [dict(_record_context(item[0], item[1], item[3]),
                                 Time=str(item[2]["Time"]),
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
                    # Coverage selection uses half a waveform sample at either
                    # edge, independently of the absolute anchor time tolerance.
                    grid_tolerance_ns = Decimal(500_000_000) / Decimal(str(rate))
                    coverage = _overlapping_events(trace, datasets, grid_tolerance_ns)
                    ranges = _validate_coverage(trace, coverage)
                except ValueError as exc:
                    failures.append(f"trace {trace_index} {trace.id}: {exc}")
                    continue
                matches = anchors
                association_type = "anchor_segment"
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
        if ranges is None:
            ranges = [(matches[0], 0, 0, trace.stats.npts)]
        associations.append((trace, matches[0], association_type, ranges))

    if failures:
        raise ValueError("GeoCSV association failed; no traces were modified:\n"
                         + "\n".join(failures))

    plans = []
    for trace, anchor, association_type, ranges in associations:
        dataset_index, record_index, row, metadata = anchor
        attachment = AttribDict({**row.to_dict(), "source_record_index": record_index,
                                 "dataset_index": dataset_index, "metadata": metadata,
                                 "association": _association_details(
                                     trace, anchor, association_type, ranges)})
        coordinates = _coordinates(trace, row, metadata)
        headers = _sac_header(trace, row, metadata, coordinates) if create_sac_header else None
        plans.append((trace, attachment, coordinates, headers))

    for trace, attachment, coordinates, headers in plans:
        trace.stats.geocsv = attachment
        trace.stats.coordinates = coordinates
        if headers is not None:
            trace.stats.sac = headers
