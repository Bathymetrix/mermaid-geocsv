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
def subsets():
    # These real-data subsets are tracked and required, including on CI.
    return {item["path"]: geocsv.read(FIXTURES / item["subset"]["path"])
            for item in MANIFEST["geocsv"]}


def load_trace(example=EXAMPLES[0]):
    trace, = obspy.read(str(FIXTURES / example["mseed"]))
    return trace


def one_event(subsets):
    """Keep one known matching row for focused matching-policy tests."""
    example = EXAMPLES[0]
    trace = load_trace(example)
    source = subsets[example["geocsv"]][0]
    frame = source.loc[[example["subset_record_index"]]].copy()
    return trace, frame


def test_default_rejects_real_writer_offset_beyond_100_microseconds(subsets):
    trace = load_trace()
    records = subsets[EXAMPLES[0]['geocsv']]
    record_index = EXAMPLES[0]['subset_record_index']
    assert trace.stats.starttime.ns - records[0].loc[record_index, 'StartTime'].value == 349_000
    before = trace.copy()
    with pytest.raises(ValueError, match='no match'):
        associate(trace, records)
    assert trace.stats == before.stats
    assert (trace.data == before.data).all()
    associate(trace, records, time_tolerance=0.001)
    assert trace.stats.geocsv.source_record_index == record_index


def test_sample_coverage_and_verbatim_copy_hashes():
    assert len(MANIFEST["population"]) == 12
    for group, population in MANIFEST["population"].items():
        examples = [item for item in EXAMPLES if item["group"] == group]
        assert len(examples) == min(3, population["paired"]) == population["selected"]
    for example in EXAMPLES:
        for extension in ("mseed", "sac"):
            with (FIXTURES / example[extension]).open("rb") as handle:
                assert hashlib.file_digest(handle, "sha256").hexdigest() == example[f"{extension}_sha256"]


def test_tracked_subset_hashes_and_record_maps(subsets):
    for item in MANIFEST["geocsv"]:
        subset = item["subset"]
        path = FIXTURES / subset["path"]
        with path.open("rb") as handle:
            assert hashlib.file_digest(handle, "sha256").hexdigest() == subset["sha256"]
        frame, = subsets[item["path"]]
        original_indices = subset["source_record_indices"]
        assert original_indices == sorted(set(original_indices))
        assert 0 <= min(original_indices) <= max(original_indices) < subset["source_record_count"]
        assert frame.index.equals(pd.RangeIndex(len(original_indices), name="source_record_index"))
        assert frame.attrs["geocsv"].source_path == path.resolve()
        assert frame["SampleCount"].dtype == pd.Int64Dtype()
        assert frame["Location"].dtype == pd.StringDtype()
        for example in EXAMPLES:
            if example["geocsv"] == item["path"]:
                assert original_indices[example["subset_record_index"]] == example["original_source_record_index"]


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
def test_sampled_association(example, subsets):
    trace = load_trace(example)
    stream_type = example["group"].split(".")[0]
    expected_quality = {"DET": "Q", "REQ": "D"}[stream_type]
    core = {key: deepcopy(trace.stats[key]) for key in trace.stats.defaults}
    samples = trace.data.copy()
    records = subsets[example["geocsv"]]
    assert associate(trace, records, time_tolerance=0.001) is None
    attachment = trace.stats.geocsv
    assert attachment.DataQuality == expected_quality
    assert attachment.dataset_index == 0
    assert attachment.source_record_index == example["subset_record_index"]
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


def test_subset_event_quality_domain(subsets):
    for records in subsets.values():
        for frame in records:
            events = frame.loc[frame["MethodIdentifier"].str.startswith("Algorithm(event):")]
            assert events["DataQuality"].notna().all()
            assert set(events["DataQuality"]) <= {"Q", "D"}


def test_stream_supports_records_from_multiple_floats(subsets):
    stream = obspy.Stream([load_trace(item) for item in EXAMPLES])
    records = [frame for frames in subsets.values() for frame in frames]
    assert associate(stream, records, time_tolerance=0.001) is None
    assert all("geocsv" in trace.stats for trace in stream)


def test_independent_traces_can_use_the_same_source_row(subsets):
    trace, frame = one_event(subsets)
    stream = obspy.Stream([trace, trace.copy()])
    associate(stream, [frame], time_tolerance=0.001)
    assert stream[0].stats.geocsv.source_record_index == stream[1].stats.geocsv.source_record_index
    assert stream[0].stats.geocsv is not stream[1].stats.geocsv


def test_ambiguous_records_are_rejected_without_mutation(subsets):
    trace, frame = one_event(subsets)
    before = deepcopy(trace.stats)
    with pytest.raises(ValueError, match="ambiguous.*record"):
        associate(trace, [frame, frame], time_tolerance=0.001)
    assert trace.stats == before


def test_stream_failure_does_not_partially_associate(subsets):
    good = load_trace()
    bad = good.copy()
    bad.stats.location = "99"
    stream = obspy.Stream([good, bad])
    before = [deepcopy(trace.stats) for trace in stream]
    with pytest.raises(ValueError, match="no match"):
        associate(stream, subsets[EXAMPLES[0]["geocsv"]], time_tolerance=0.001)
    assert [trace.stats for trace in stream] == before


@pytest.mark.parametrize("field,value", [("SampleCount", 1), ("SampleRate", 99.0)])
def test_count_and_rate_mismatches_fail(subsets, field, value):
    trace, frame = one_event(subsets)
    frame.loc[:, field] = value
    with pytest.raises(ValueError, match="no match"):
        associate(trace, [frame], time_tolerance=0.001)
    assert "geocsv" not in trace.stats


def test_provisional_rate_check_and_waveform_authority(subsets):
    trace, frame = one_event(subsets)
    original = trace.stats.sampling_rate
    frame.loc[:, "SampleRate"] = original + 0.00999
    associate(trace, [frame], time_tolerance=0.001)
    assert trace.stats.sampling_rate == original
    trace = load_trace()
    frame.loc[:, "SampleRate"] = original + 0.01001
    with pytest.raises(ValueError, match="no match"):
        associate(trace, [frame], time_tolerance=0.001)


def test_equivalent_timezone_and_source_resolution(subsets):
    trace, frame = one_event(subsets)
    time = frame.iloc[0]["StartTime"].tz_convert("Pacific/Honolulu")
    frame.loc[:, "StartTime"] = time
    associate(trace, [frame], time_tolerance=0.001)
    assert trace.stats.geocsv.StartTime == time
    trace = load_trace()
    frame.loc[:, "StartTime"] = time + pd.Timedelta(milliseconds=2)
    with pytest.raises(ValueError, match="no match"):
        associate(trace, [frame], time_tolerance=0.001)


def test_quality_is_preserved_and_does_not_select_matches(subsets):
    trace, frame = one_event(subsets)
    frame.loc[:, "DataQuality"] = "D"
    associate(trace, [frame], time_tolerance=0.001)
    assert trace.stats.mseed.dataquality == "Q"
    assert trace.stats.geocsv.DataQuality == "D"


def test_missing_coordinate_pair_fails_without_attachment(subsets):
    trace, frame = one_event(subsets)
    frame.loc[:, ["Latitude", "Longitude", "WaterPressure"]] = pd.NA
    before = deepcopy(trace.stats)
    with pytest.raises(ValueError, match="requires both Latitude and Longitude"):
        associate(trace, [frame], time_tolerance=0.001)
    assert trace.stats == before


def test_coordinate_conflict_is_rejected_without_attachment(subsets):
    trace, frame = one_event(subsets)
    trace.stats.coordinates = {"latitude": 0.0}
    with pytest.raises(ValueError, match="stats.coordinates already exists"):
        associate(trace, [frame], time_tolerance=0.001)
    assert "geocsv" not in trace.stats
    assert trace.stats.coordinates.latitude == 0


def test_bad_coordinate_units_are_rejected(subsets):
    from dataclasses import replace
    trace, frame = one_event(subsets)
    units = dict(frame.attrs["geocsv"].field_units)
    units["Latitude"] = "radians"
    frame.attrs["geocsv"] = replace(frame.attrs["geocsv"], field_units=units)
    with pytest.raises(ValueError, match="Latitude requires declared units"):
        associate(trace, [frame], time_tolerance=0.001)
    assert "geocsv" not in trace.stats


def test_bad_rate_units_are_rejected(subsets):
    from dataclasses import replace
    trace, frame = one_event(subsets)
    units = dict(frame.attrs["geocsv"].field_units)
    units["SampleRate"] = "kilohertz"
    frame.attrs["geocsv"] = replace(frame.attrs["geocsv"], field_units=units)
    with pytest.raises(ValueError, match="SampleRate requires declared units hertz"):
        associate(trace, [frame], time_tolerance=0.001)
    assert "geocsv" not in trace.stats
