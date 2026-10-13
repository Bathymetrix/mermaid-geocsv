"""Check MERMAID fixture quality flags against the documented stream map."""

from pathlib import Path

import pandas as pd
import pytest

from mermaid import geocsv


REPOSITORY = Path(__file__).parents[1]
MERMAID_FIXTURES = REPOSITORY / "data" / "fixtures"
EVENT_QUALITY = {"DET": "Q", "REQ": "D"}


def test_mermaid_geocsv_event_quality_values_follow_stream_map() -> None:
    """GeoCSV marks DET as Q and REQ as D, independent of sample rate."""
    paths = sorted(
        path
        for station_directory in MERMAID_FIXTURES.glob("P*")
        for path in station_directory.rglob("*.geocsv")
    )
    assert paths, "expected the canonical MERMAID GeoCSV fixture"

    event_rows = []
    for path in paths:
        for frame in geocsv.read(path):
            if "MethodIdentifier" not in frame or "DataQuality" not in frame:
                continue
            is_event = frame["MethodIdentifier"].astype("string").str.startswith(
                "Algorithm(event):", na=False
            )
            event_rows.append(frame.loc[is_event, ["DataQuality", "SampleRate"]])

    assert event_rows, "expected algorithm:event records in MERMAID GeoCSV fixtures"
    events = pd.concat(event_rows, ignore_index=True)
    assert len(events) > 0
    assert events["DataQuality"].notna().all()
    assert set(events["DataQuality"].unique()) == {"Q", "D"}

    # The fixture has both streams at the same nominal rate. This guards the
    # documented rule that data quality identifies stream type, not frequency.
    at_20_hz = events.loc[events["SampleRate"].eq(20.0), "DataQuality"]
    assert set(at_20_hz.unique()) == {"Q", "D"}


def test_mermaid_mseed_event_quality_matches_filename() -> None:
    """Every DET/REQ MiniSEED fixture carries its prescribed quality flag."""
    obspy = pytest.importorskip("obspy", reason="MiniSEED fixture checks require ObsPy")
    paths = sorted(MERMAID_FIXTURES.rglob("*.mseed"))
    if not paths:
        pytest.skip("no MiniSEED fixtures are currently present under data/fixtures")

    checked = 0
    for path in paths:
        stream_type = next(
            (name for name in EVENT_QUALITY if f".MER.{name}." in path.name), None
        )
        assert stream_type is not None, (
            f"MiniSEED fixture {path.relative_to(REPOSITORY)} has no recognized "
            "'.MER.DET.' or '.MER.REQ.' stream token; classify any new product type"
        )

        stream = obspy.read(str(path), headonly=True)
        assert len(stream), f"MiniSEED fixture {path.name} contains no traces"
        expected = EVENT_QUALITY[stream_type]
        for trace in stream:
            actual = trace.stats.get("mseed", {}).get("dataquality")
            assert actual == expected, (
                f"{path.name} identifies {stream_type} (expected {expected}) but "
                f"trace {trace.id} has dataquality {actual!r}"
            )
        checked += 1

    assert checked == len(paths)
