"""ObsPy's fresh SAC baseline plus four GeoCSV station location fields."""

from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

obspy = pytest.importorskip("obspy")
from obspy.io.sac import SACTrace

from mermaid import geocsv


FIXTURES = Path(__file__).parents[1] / "data/fixtures/association"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())
EXAMPLES = MANIFEST["examples"]


@pytest.fixture(scope="module")
def subsets():
    return {item["path"]: geocsv.read(FIXTURES.parent / "schema-1.0.0/association" / item["subset"]["path"])
            for item in MANIFEST["geocsv"]}


def event(subsets):
    example = EXAMPLES[0]
    trace, = obspy.read(str(FIXTURES / example["mseed"]))
    frame = subsets[example["geocsv"]][0].loc[[example["subset_record_index"]]].copy()
    return trace, frame


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda item: item["mseed"])
def test_real_roundtrip_and_independent_sac_reference(example, subsets, tmp_path):
    trace, = obspy.read(str(FIXTURES / example["mseed"]))
    original = trace.copy()
    baseline = SACTrace.from_obspy_trace(trace, keep_sac_header=False).to_obspy_trace(
        round_sampling_interval=False).stats.sac
    assert geocsv.associate(trace, subsets[example["geocsv"]], create_sac_header=True) is None
    source = trace.stats.geocsv
    expected = dict(baseline, stla=float(source.Latitude), stlo=float(source.Longitude),
                    stel=0.0, stdp=-12345.0 if pd.isna(source.WaterPressure)
                    else float(source.WaterPressure) / 100)
    assert trace.stats.sac == expected
    assert all(trace.stats[key] == value for key, value in original.stats.items())
    np.testing.assert_array_equal(trace.data, original.data)
    before_write = trace.copy()
    path = tmp_path / "located.sac"
    trace.write(str(path), format="SAC")
    actual = SACTrace.read(str(path))
    # Independent comparison reference is never supplied to association.
    reference = SACTrace.read(str(FIXTURES / example["sac"]))
    for field, key in (("Latitude", "stla"), ("Longitude", "stlo")):
        assert getattr(actual, key) == np.float32(source[field])
        tolerance = 0.5e-6 + abs(float(np.spacing(np.float32(getattr(reference, key)))))
        assert getattr(actual, key) == pytest.approx(getattr(reference, key), abs=tolerance)
    assert actual.stdp == reference.stdp
    assert actual.stel == reference.stel == 0
    np.testing.assert_array_equal(actual.data, trace.data.astype(np.float32))
    np.testing.assert_array_equal(actual.data, reference.data)
    assert actual.npts == trace.stats.npts == reference.npts
    assert actual.delta == np.float32(trace.stats.delta)
    assert actual.scale == np.float32(trace.stats.calib)
    reopened = actual.to_obspy_trace(round_sampling_interval=False)
    # Pressure supplies station depth; earthquake-source fields stay undefined.
    for field in ("evla", "evlo", "evel", "evdp"):
        assert field not in reopened.stats.sac
    assert reopened.id == trace.id
    assert abs(reopened.stats.starttime.ns - trace.stats.starttime.ns) <= 1000
    assert abs(reopened.stats.starttime.ns - reference.to_obspy_trace(
        round_sampling_interval=False).stats.starttime.ns) <= 1000
    assert trace.stats == before_write.stats
    np.testing.assert_array_equal(trace.data, before_write.data)


@pytest.mark.parametrize("existing", [None, {}, {"stla": -70, "user0": 99}])
def test_requested_destination_must_be_absent(subsets, existing):
    trace, frame = event(subsets)
    trace.stats.sac = existing
    before = trace.copy()
    with pytest.raises(ValueError, match=r"stats.sac already exists"):
        geocsv.associate(trace, [frame], create_sac_header=True)
    assert trace.stats == before.stats
    np.testing.assert_array_equal(trace.data, before.data)


def test_default_leaves_existing_sac_untouched(subsets):
    trace, frame = event(subsets)
    trace.stats.sac = {"stla": -70, "user0": 99}
    before = trace.stats.sac.copy()
    geocsv.associate(trace, [frame])
    assert trace.stats.sac == before
    other, frame = event(subsets)
    geocsv.associate(other, [frame])
    assert "sac" not in other.stats


@pytest.mark.parametrize("value", [None, 0, 1, "true"])
def test_option_requires_bool(value):
    with pytest.raises(TypeError, match="create_sac_header must be a bool"):
        geocsv.associate(obspy.Stream(), [], create_sac_header=value)


@pytest.mark.parametrize("field,value", [
    ("Elevation", pd.NA), ("Elevation", 1), ("Latitude", pd.NA), ("Longitude", None), ("Latitude", 91),
    ("Longitude", -181), ("Latitude", np.inf),
    ("WaterPressure", pd.NA), ("WaterPressure", -1), ("WaterPressure", np.inf),
    ("DataQuality", pd.NA),
])
def test_invalid_geographic_source_fails_without_mutation(subsets, field, value):
    trace, frame = event(subsets)
    frame.loc[:, field] = value
    if field == "DataQuality":
        frame.loc[:, "WaterPressure"] = pd.NA
    before = trace.copy()
    with pytest.raises(ValueError):
        geocsv.associate(trace, [frame], create_sac_header=True)
    assert trace.stats == before.stats
    np.testing.assert_array_equal(trace.data, before.data)


@pytest.mark.parametrize("field,unit", [
    ("Elevation", "kilometers"), ("Latitude", "radians"), ("Longitude", None),
    ("WaterPressure", "dbar"), ("SampleRate", "kilohertz"),
])
def test_declared_units_are_required(subsets, field, unit):
    trace, frame = event(subsets)
    metadata = frame.attrs["geocsv"]
    frame.attrs["geocsv"] = replace(metadata, field_units={**metadata.field_units, field: unit})
    before = trace.copy()
    with pytest.raises(ValueError):
        geocsv.associate(trace, [frame], create_sac_header=True)
    assert trace.stats == before.stats


def test_fresh_headers_source_quality_and_no_reread(subsets, monkeypatch, tmp_path):
    trace, frame = event(subsets)
    request = trace.copy()
    requested = frame.copy()
    requested.loc[:, "WaterPressure"] = pd.NA
    requested.loc[:, "DataQuality"] = "D"  # Synthetic policy case; native Q stays Q.
    repeated = trace.copy()
    geocsv.associate(obspy.Stream([trace, repeated]), [frame], create_sac_header=True)
    assert repeated.stats.sac is not trace.stats.sac
    repeated.stats.sac.stla = -70
    assert trace.stats.sac.stla != -70
    geocsv.associate(request, [requested], create_sac_header=True)
    assert request.stats.mseed.dataquality == "Q"
    assert request.stats.sac.stdp == -12345
    assert trace.stats.sac.stdp != -12345
    request.stats.sac.stla = -80
    assert trace.stats.sac.stla != -80
    trace.stats.geocsv.metadata = replace(trace.stats.geocsv.metadata, source_path=tmp_path / "gone")
    monkeypatch.setattr(geocsv, "read", lambda *args: pytest.fail("must not reopen GeoCSV"))
    trace.write(str(tmp_path / "located.sac"), format="SAC")
    assert SACTrace.read(str(tmp_path / "located.sac")).stla == np.float32(trace.stats.geocsv.Latitude)


def test_batch_projection_failure_is_transactional(subsets):
    first, good = event(subsets)
    second = first.copy()
    second.stats.station = "BAD01"
    bad = good.copy()
    bad.loc[:, "Station"] = second.stats.station
    bad.loc[:, "WaterPressure"] = -1
    before = [trace.copy() for trace in (first, second)]
    with pytest.raises(ValueError, match="WaterPressure"):
        geocsv.associate(obspy.Stream([first, second]), [good, bad], create_sac_header=True)
    for trace, original in zip((first, second), before):
        assert trace.stats == original.stats
        np.testing.assert_array_equal(trace.data, original.data)


def test_default_does_not_require_pressure(subsets):
    trace, frame = event(subsets)
    frame.loc[:, "WaterPressure"] = pd.NA
    geocsv.associate(trace, [frame])
    assert "sac" not in trace.stats


def test_existing_sac_on_later_trace_leaves_whole_batch_unchanged(subsets):
    first, frame = event(subsets)
    second = first.copy()
    second.stats.sac = {}
    before = [trace.copy() for trace in (first, second)]
    with pytest.raises(ValueError, match=r"stats.sac already exists"):
        geocsv.associate(obspy.Stream([first, second]), [frame], create_sac_header=True)
    for trace, original in zip((first, second), before):
        assert trace.stats == original.stats
        np.testing.assert_array_equal(trace.data, original.data)


@pytest.mark.parametrize("start_sample", [0, 10])
def test_clipped_real_det_uses_containing_anchor_geography(subsets, tmp_path, start_sample):
    trace, frame = event(subsets)
    trace.stats.starttime += start_sample / trace.stats.sampling_rate
    trace.data = trace.data[start_sample:start_sample + 25].copy()
    geocsv.associate(trace, [frame], allow_first_segment=True, create_sac_header=True)
    source = trace.stats.geocsv
    assert source.association.type == "anchor_segment"
    assert source.SampleCount != trace.stats.npts == source.association.waveform.sample_count == 25
    path = tmp_path / "clipped.sac"
    trace.write(str(path), format="SAC")
    actual = SACTrace.read(str(path))
    assert actual.stla == np.float32(source.Latitude)
    assert actual.stlo == np.float32(source.Longitude)
    assert actual.stdp == np.float32(source.WaterPressure / 100)
    assert actual.stel == 0


def test_stream_mixes_standard_and_anchor_matches_with_fresh_sac_headers(subsets):
    """Create independent SAC projections for strict and clipped Stream members."""
    original, frame = event(subsets)
    clipped = original.copy()
    clipped.stats.starttime += 10 / clipped.stats.sampling_rate
    clipped.data = clipped.data[10:35].copy()
    stream = obspy.Stream([original, clipped])
    before = stream.copy()

    assert geocsv.associate(stream, [frame], allow_first_segment=True,
                            create_sac_header=True) is None
    assert [trace.stats.geocsv.association.type for trace in stream] == [
        "single_segment", "anchor_segment"]
    row = frame.iloc[0]
    expected = {"stla": float(row.Latitude), "stlo": float(row.Longitude),
                "stel": 0.0, "stdp": float(row.WaterPressure) / 100}
    for trace, native in zip(stream, before):
        assert trace.stats.geocsv.source_record_index == frame.index[0]
        assert trace.stats.geocsv.SampleCount == row.SampleCount
        assert trace.stats.geocsv.association.waveform.sample_count == trace.stats.npts
        assert {key: trace.stats.sac[key] for key in expected} == expected
        assert all(trace.stats[key] == value for key, value in native.stats.items())
        np.testing.assert_array_equal(trace.data, native.data)
    for key in ("geocsv", "coordinates", "sac"):
        assert stream[0].stats[key] is not stream[1].stats[key]
    assert stream[0].stats.geocsv.association is not stream[1].stats.geocsv.association


def test_native_nanoseconds_and_calibration_survive_header_initialization(subsets):
    trace, frame = event(subsets)
    trace.stats.starttime += 0.000000123
    trace.stats.calib = 2.5
    before = trace.copy()
    geocsv.associate(trace, [frame], create_sac_header=True)
    assert trace.stats.starttime.ns == before.stats.starttime.ns
    assert trace.stats.sampling_rate == before.stats.sampling_rate
    assert trace.stats.calib == 2.5
    assert trace.stats.sac.scale == np.float32(2.5)
    np.testing.assert_array_equal(trace.data, before.data)
