"""Verify the sandbox associator with rebuilt, paired waveform fixtures."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

obspy = pytest.importorskip("obspy")
from associate import associate
from mermaid import geocsv


FIXTURES = Path(__file__).parents[1] / "data" / "fixtures" / "association"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())
EXAMPLES = MANIFEST["examples"]
CONFIGURATION = {
    "WLT1": ("MDH", "20"), "WLT2": ("MDH", "10"),
    "WLT3": ("MDH", "00"), "WLT4": ("BDH", "20"),
    "WLT5": ("BDH", "00"), "RAW": ("BDH", "10"),
}


@pytest.fixture(scope="module")
def histories():
    missing = [item["path"] for item in MANIFEST["geocsv"]
               if not (FIXTURES / item["path"]).is_file()]
    if missing:
        pytest.skip("complete local GeoCSV histories unavailable; restore them "
                    "with sandbox/obspy_association/restore_geocsv_histories.py")
    return {item["path"]: geocsv.read(FIXTURES / item["path"])
            for item in MANIFEST["geocsv"]}


def load_trace(example=EXAMPLES[0]):
    trace, = obspy.read(str(FIXTURES / example["mseed"]))
    return trace


def one_event(histories):
    """Keep one known matching row for focused matching-policy tests."""
    example = EXAMPLES[0]
    trace = load_trace(example)
    # P0030's first manifest example corresponds to full-history record 689.
    source = histories[example["geocsv"]][0]
    frame = source.loc[[689]].copy()
    return trace, frame


def test_default_rejects_real_writer_offset_beyond_100_microseconds(histories):
    trace = load_trace()
    records = histories[EXAMPLES[0]['geocsv']]
    assert trace.stats.starttime.ns - records[0].loc[689, 'StartTime'].value == 349_000
    before = trace.copy()
    with pytest.raises(ValueError, match='no match'):
        associate(trace, records)
    assert trace.stats == before.stats
    assert (trace.data == before.data).all()
    associate(trace, records, time_tolerance=0.001)
    assert trace.stats.geocsv.source_record_index == 689


def test_sample_coverage_and_verbatim_copy_hashes():
    assert len(MANIFEST["population"]) == 12
    for group, population in MANIFEST["population"].items():
        examples = [item for item in EXAMPLES if item["group"] == group]
        assert len(examples) == min(3, population["paired"]) == population["selected"]
    for example in EXAMPLES:
        for extension in ("mseed", "sac"):
            with (FIXTURES / example[extension]).open("rb") as handle:
                assert hashlib.file_digest(handle, "sha256").hexdigest() == example[f"{extension}_sha256"]


def test_complete_history_hashes(histories):
    for item in MANIFEST["geocsv"]:
        with (FIXTURES / item["path"]).open("rb") as handle:
            assert hashlib.file_digest(handle, "sha256").hexdigest() == item["sha256"]


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda item: item["mseed"])
@pytest.mark.filterwarnings("ignore:Sample spacing read from SAC file:UserWarning")
def test_sampled_sncl_and_quality(example):
    trace = load_trace(example)
    sac, = obspy.read(str(FIXTURES / example["sac"]), headonly=True)
    stream_type, product = example["group"].split(".")
    float_name = Path(example["mseed"]).parts[0].split("-")
    station = f"{float_name[-2]}{int(float_name[-1]):04d}"
    channel, location = CONFIGURATION[product]
    assert trace.id == f"MH.{station}.{location}.{channel}" == sac.id
    assert sac.stats.sac.kuser1 == example["group"]
    expected_quality = {"DET": "Q", "REQ": "D"}[stream_type]
    assert trace.stats.mseed.dataquality == expected_quality


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda item: item["mseed"])
def test_sampled_association(example, histories):
    trace = load_trace(example)
    stream_type = example["group"].split(".")[0]
    expected_quality = {"DET": "Q", "REQ": "D"}[stream_type]
    core = {key: deepcopy(trace.stats[key]) for key in trace.stats.defaults}
    samples = trace.data.copy()
    records = histories[example["geocsv"]]
    assert associate(trace, records, time_tolerance=0.001) is None
    attachment = trace.stats.geocsv
    assert attachment.DataQuality == expected_quality
    row = records[attachment.dataset_index].loc[attachment.source_record_index]
    for field, value in row.items():
        actual = attachment[field]
        assert pd.isna(actual) if pd.isna(value) else actual == value
    assert attachment.metadata is records[attachment.dataset_index].attrs["geocsv"]
    assert {key: trace.stats[key] for key in core} == core
    assert (trace.data == samples).all()
    assert trace.stats.coordinates.latitude == attachment.Latitude
    assert trace.stats.coordinates.longitude == attachment.Longitude
    assert trace.stats.coordinates.elevation == 0
    assert "sac" not in trace.stats


def test_full_history_event_quality_domain(histories):
    for records in histories.values():
        for frame in records:
            events = frame.loc[frame["MethodIdentifier"].str.startswith("Algorithm(event):")]
            assert events["DataQuality"].notna().all()
            assert set(events["DataQuality"]) <= {"Q", "D"}


def test_stream_supports_records_from_multiple_floats(histories):
    stream = obspy.Stream([load_trace(item) for item in EXAMPLES])
    records = [frame for frames in histories.values() for frame in frames]
    assert associate(stream, records, time_tolerance=0.001) is None
    assert all("geocsv" in trace.stats for trace in stream)


def test_independent_traces_can_use_the_same_source_row(histories):
    trace, frame = one_event(histories)
    stream = obspy.Stream([trace, trace.copy()])
    associate(stream, [frame], time_tolerance=0.001)
    assert stream[0].stats.geocsv.source_record_index == stream[1].stats.geocsv.source_record_index
    assert stream[0].stats.geocsv is not stream[1].stats.geocsv


def test_ambiguous_records_are_rejected_without_mutation(histories):
    trace, frame = one_event(histories)
    before = deepcopy(trace.stats)
    with pytest.raises(ValueError, match="ambiguous.*record"):
        associate(trace, [frame, frame], time_tolerance=0.001)
    assert trace.stats == before


def test_stream_failure_does_not_partially_associate(histories):
    good = load_trace()
    bad = good.copy()
    bad.stats.location = "99"
    stream = obspy.Stream([good, bad])
    before = [deepcopy(trace.stats) for trace in stream]
    with pytest.raises(ValueError, match="no match"):
        associate(stream, histories[EXAMPLES[0]["geocsv"]], time_tolerance=0.001)
    assert [trace.stats for trace in stream] == before


@pytest.mark.parametrize("field,value", [("SampleCount", 1), ("SampleRate", 99.0)])
def test_count_and_rate_mismatches_fail(histories, field, value):
    trace, frame = one_event(histories)
    frame.loc[:, field] = value
    with pytest.raises(ValueError, match="no match"):
        associate(trace, [frame], time_tolerance=0.001)
    assert "geocsv" not in trace.stats


def test_provisional_rate_check_and_waveform_authority(histories):
    trace, frame = one_event(histories)
    original = trace.stats.sampling_rate
    frame.loc[:, "SampleRate"] = original + 0.00999
    associate(trace, [frame], time_tolerance=0.001)
    assert trace.stats.sampling_rate == original
    trace = load_trace()
    frame.loc[:, "SampleRate"] = original + 0.01001
    with pytest.raises(ValueError, match="no match"):
        associate(trace, [frame], time_tolerance=0.001)


def test_equivalent_timezone_and_source_resolution(histories):
    trace, frame = one_event(histories)
    time = frame.iloc[0]["StartTime"].tz_convert("Pacific/Honolulu")
    frame.loc[:, "StartTime"] = time
    associate(trace, [frame], time_tolerance=0.001)
    assert trace.stats.geocsv.StartTime == time
    trace = load_trace()
    frame.loc[:, "StartTime"] = time + pd.Timedelta(milliseconds=2)
    with pytest.raises(ValueError, match="no match"):
        associate(trace, [frame], time_tolerance=0.001)


def test_quality_is_preserved_and_does_not_select_matches(histories):
    trace, frame = one_event(histories)
    frame.loc[:, "DataQuality"] = "D"
    associate(trace, [frame], time_tolerance=0.001)
    assert trace.stats.mseed.dataquality == "Q"
    assert trace.stats.geocsv.DataQuality == "D"


def test_missing_coordinate_pair_fails_without_attachment(histories):
    trace, frame = one_event(histories)
    frame.loc[:, ["Latitude", "Longitude", "WaterPressure"]] = pd.NA
    before = deepcopy(trace.stats)
    with pytest.raises(ValueError, match="requires both Latitude and Longitude"):
        associate(trace, [frame], time_tolerance=0.001)
    assert trace.stats == before


def test_coordinate_conflict_is_rejected_without_attachment(histories):
    trace, frame = one_event(histories)
    trace.stats.coordinates = {"latitude": 0.0}
    with pytest.raises(ValueError, match="stats.coordinates already exists"):
        associate(trace, [frame], time_tolerance=0.001)
    assert "geocsv" not in trace.stats
    assert trace.stats.coordinates.latitude == 0


def test_bad_coordinate_units_are_rejected(histories):
    from dataclasses import replace
    trace, frame = one_event(histories)
    units = dict(frame.attrs["geocsv"].field_units)
    units["Latitude"] = "radians"
    frame.attrs["geocsv"] = replace(frame.attrs["geocsv"], field_units=units)
    with pytest.raises(ValueError, match="Latitude requires declared units"):
        associate(trace, [frame], time_tolerance=0.001)
    assert "geocsv" not in trace.stats


def test_bad_rate_units_are_rejected(histories):
    from dataclasses import replace
    trace, frame = one_event(histories)
    units = dict(frame.attrs["geocsv"].field_units)
    units["SampleRate"] = "kilohertz"
    frame.attrs["geocsv"] = replace(frame.attrs["geocsv"], field_units=units)
    with pytest.raises(ValueError, match="SampleRate requires declared units hertz"):
        associate(trace, [frame], time_tolerance=0.001)
    assert "geocsv" not in trace.stats


def test_sac_option_is_explicitly_unimplemented(histories):
    trace = load_trace()
    before = deepcopy(trace.stats)
    with pytest.raises(NotImplementedError, match="SAC projection"):
        associate(trace, histories[EXAMPLES[0]["geocsv"]], project_sac=True, time_tolerance=0.001)
    assert trace.stats == before
