"""SAC export from associated MiniSEED, with independent automaid references."""

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
    return {item["path"]: geocsv.read(FIXTURES / item["subset"]["path"])
            for item in MANIFEST["geocsv"]}


@pytest.fixture
def trace(subsets):
    example = EXAMPLES[0]
    waveform, = obspy.read(str(FIXTURES / example["mseed"]))
    geocsv.associate(waveform, subsets[example["geocsv"]], time_tolerance=0.001)
    return waveform


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda item: item["mseed"])
def test_real_roundtrip_and_independent_sac_reference(example, subsets, tmp_path):
    trace, = obspy.read(str(FIXTURES / example["mseed"]))
    geocsv.associate(trace, subsets[example["geocsv"]], time_tolerance=0.001)
    before = trace.copy()
    path = tmp_path / "associated.sac"
    assert geocsv.write_sac(trace, path) is None
    actual = SACTrace.read(str(path))
    reference = SACTrace.read(str(FIXTURES / example["sac"]))
    source = trace.stats.geocsv
    assert actual.stla == np.float32(source.Latitude)
    assert actual.stlo == np.float32(source.Longitude)
    assert actual.stel == reference.stel == 0
    for key in ("stla", "stlo"):
        # GeoCSV renders six decimals; SAC then rounds to float32.
        tolerance = 0.5e-6 + abs(float(np.spacing(np.float32(getattr(reference, key)))))
        assert getattr(actual, key) == pytest.approx(getattr(reference, key), abs=tolerance)
    if example["group"].startswith("REQ."):
        assert pd.isna(source.WaterPressure)
        assert actual.stdp is reference.stdp is None
    else:
        assert actual.stdp == np.float32(source.WaterPressure / 100)
        assert actual.stdp == reference.stdp
    np.testing.assert_array_equal(actual.data, trace.data.astype(np.float32))
    np.testing.assert_array_equal(actual.data, reference.data)
    assert actual.npts == trace.stats.npts == reference.npts
    assert actual.delta == np.float32(trace.stats.delta)
    assert actual.scale == trace.stats.calib  # No sample calibration is applied.
    reopened = actual.to_obspy_trace(round_sampling_interval=False)
    assert reopened.id == trace.id
    assert abs(reopened.stats.starttime.ns - trace.stats.starttime.ns) <= 1000
    # Compare absolute first-sample times rather than requiring identical nz/b splits.
    original = reference.to_obspy_trace(round_sampling_interval=False)
    assert abs(reopened.stats.starttime.ns - original.stats.starttime.ns) <= 1000
    assert trace.stats == before.stats
    np.testing.assert_array_equal(trace.data, before.data)
    assert "sac" not in trace.stats


def test_attached_source_only_no_reread_or_existing_sac_defaults(trace, tmp_path, monkeypatch):
    trace.stats.coordinates = {"latitude": -80, "longitude": -90, "elevation": 99}
    trace.stats.sac = {"stla": -70, "stlo": -60, "stdp": 10, "stel": 99,
                       "evla": 30, "user0": 100}
    before = trace.copy()

    def fail_read(*args, **kwargs):
        raise AssertionError("Writer must not read GeoCSV")

    monkeypatch.setattr(geocsv, "read", fail_read)
    # The provenance path need not exist anymore.
    trace.stats.geocsv.metadata = replace(trace.stats.geocsv.metadata,
                                          source_path=tmp_path / "gone.csv")
    geocsv.write_sac(trace, str(tmp_path / "fresh.sac"))
    actual = SACTrace.read(str(tmp_path / "fresh.sac"))
    assert actual.stla == np.float32(trace.stats.geocsv.Latitude)
    assert actual.stlo == np.float32(trace.stats.geocsv.Longitude)
    assert actual.stdp == np.float32(trace.stats.geocsv.WaterPressure / 100)
    assert actual.stel == 0
    assert actual.evla is actual.user0 is None
    assert trace.stats.sac == before.stats.sac
    assert trace.stats.coordinates == before.stats.coordinates
    np.testing.assert_array_equal(trace.data, before.data)


def test_existing_file_is_preserved(trace, tmp_path):
    path = tmp_path / "existing.sac"
    path.write_bytes(b"keep me")
    with pytest.raises(FileExistsError):
        geocsv.write_sac(trace, path)
    assert path.read_bytes() == b"keep me"


@pytest.mark.parametrize("value", [None, [], "waveform", obspy.Stream()])
def test_requires_one_trace(value, tmp_path):
    with pytest.raises(TypeError, match="one ObsPy Trace"):
        geocsv.write_sac(value, tmp_path / "invalid.sac")
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("attachment", [None, {}, {"association": "first_segment"}])
def test_requires_standard_association(trace, attachment, tmp_path):
    trace.stats.geocsv = attachment
    with pytest.raises(ValueError, match="requires"):
        geocsv.write_sac(trace, tmp_path / "invalid.sac")
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("field,value", [
    ("station", "OTHER"), ("starttime", obspy.UTCDateTime(0)),
    ("sampling_rate", 1), ("npts", 1),
])
def test_changed_waveform_is_rejected(trace, field, value, tmp_path):
    trace.stats[field] = value
    before = trace.copy()
    with pytest.raises(ValueError):
        geocsv.write_sac(trace, tmp_path / "invalid.sac")
    assert trace.stats == before.stats
    np.testing.assert_array_equal(trace.data, before.data)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("field,value", [
    ("Latitude", pd.NA), ("Longitude", None), ("Latitude", 91),
    ("Longitude", -181), ("Latitude", float("inf")),
    ("WaterPressure", pd.NA), ("WaterPressure", -1),
    ("WaterPressure", float("inf")),
])
def test_invalid_geographic_source_fails_before_creating_file(trace, field, value, tmp_path):
    trace.stats.geocsv[field] = value
    with pytest.raises(ValueError):
        geocsv.write_sac(trace, tmp_path / "invalid.sac")
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("field,unit", [
    ("Latitude", "radians"), ("Longitude", None),
    ("WaterPressure", "dbar"), ("SampleRate", "kilohertz"),
])
def test_declared_units_are_required(trace, field, unit, tmp_path):
    metadata = trace.stats.geocsv.metadata
    units = dict(metadata.field_units)
    units[field] = unit
    trace.stats.geocsv.metadata = replace(metadata, field_units=units)
    with pytest.raises(ValueError):
        geocsv.write_sac(trace, tmp_path / "invalid.sac")
    assert not list(tmp_path.iterdir())


def test_missing_request_pressure_uses_source_quality_and_never_previous_depth(trace, tmp_path):
    geocsv.write_sac(trace, tmp_path / "det.sac")
    request = trace.copy()
    request.stats.geocsv.WaterPressure = pd.NA
    request.stats.geocsv.DataQuality = "D"
    request.stats.sac = {"stdp": 999}
    # Synthetic policy case: native quality Q is independent of source D.
    assert request.stats.mseed.dataquality == "Q"
    geocsv.write_sac(request, tmp_path / "req.sac")
    assert SACTrace.read(str(tmp_path / "det.sac")).stdp is not None
    assert SACTrace.read(str(tmp_path / "req.sac")).stdp is None
    assert request.stats.sac.stdp == 999


def test_masked_and_empty_data_are_rejected(trace, tmp_path):
    trace.data = np.ma.array(trace.data, mask=np.arange(len(trace.data)) == 0)
    with pytest.raises(ValueError, match="masked gaps"):
        geocsv.write_sac(trace, tmp_path / "masked.sac")
    trace.data = np.array([], dtype=np.float32)
    with pytest.raises(ValueError, match="loaded sample count"):
        geocsv.write_sac(trace, tmp_path / "empty.sac")
    assert not list(tmp_path.iterdir())


def test_submicrosecond_start_empty_location_and_float32_samples(tmp_path):
    # Invented original segment: exercise SAC precision independently of real fixtures.
    content = b'''#dataset: GeoCSV
#field_type: string,datetime,string,string,string,string,string,float,float,float,float,integer
#field_unit: unitless,iso8601,unitless,unitless,unitless,unitless,unitless,degrees_north,degrees_east,mbar,hertz,unitless
MethodIdentifier,StartTime,Network,Station,Location,Channel,DataQuality,Latitude,Longitude,WaterPressure,SampleRate,SampleCount
Algorithm(event):synthetic:v0,2025-01-01T00:00:00.123456789Z,MH,SYN01,,BDH,Q,0,0,0,20,4
'''
    records = geocsv.read(content)
    start_ns = pd.Timestamp("2025-01-01T00:00:00.123456789Z").value
    waveform = obspy.Trace(np.array([0, 1, -10, 16777217], dtype=np.int32), header={
        "network": "MH", "station": "SYN01", "location": "", "channel": "BDH",
        "starttime": obspy.UTCDateTime(ns=start_ns), "sampling_rate": 20,
        "calib": 2.5,
    })
    geocsv.associate(waveform, records, time_tolerance=0)
    before = waveform.copy()
    geocsv.write_sac(waveform, tmp_path / "synthetic.sac")
    sac = SACTrace.read(str(tmp_path / "synthetic.sac"))
    reopened = sac.to_obspy_trace(round_sampling_interval=False)
    assert reopened.id == "MH.SYN01..BDH"
    assert abs(reopened.stats.starttime.ns - start_ns) <= 1000
    assert reopened.stats.starttime.ns != start_ns  # No nanosecond-preservation claim.
    assert sac.stla == sac.stlo == sac.stdp == sac.stel == 0
    assert sac.scale == 2.5
    np.testing.assert_array_equal(sac.data, waveform.data.astype(np.float32))
    assert sac.data[-1] == 16777216  # Float32 quantization, never calibration.
    assert waveform.stats == before.stats
    np.testing.assert_array_equal(waveform.data, before.data)


@pytest.mark.parametrize("field", ["Station", "SampleCount", "waveform_sample_count", "StartTime",
                                   "starttime_difference_seconds", "DataQuality"])
def test_incomplete_attachment_is_rejected(trace, field, tmp_path):
    trace.stats.geocsv[field] = pd.NA
    if field == "DataQuality":
        trace.stats.geocsv.WaterPressure = pd.NA
    with pytest.raises(ValueError):
        geocsv.write_sac(trace, tmp_path / "invalid.sac")
    assert not list(tmp_path.iterdir())


def test_missing_dataset_provenance_is_rejected(trace, tmp_path):
    del trace.stats.geocsv.metadata
    with pytest.raises(ValueError, match="dataset metadata"):
        geocsv.write_sac(trace, tmp_path / "invalid.sac")
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('start_sample,count', [(0, 25), (10, 25)])
def test_clipped_real_det_uses_containing_anchor_geography(subsets, tmp_path, start_sample, count):
    example = EXAMPLES[0]
    trace, = obspy.read(str(FIXTURES / example['mseed']))
    trace.stats.starttime += start_sample / trace.stats.sampling_rate
    trace.data = trace.data[start_sample:start_sample + count].copy()
    before = trace.copy()
    geocsv.associate(trace, subsets[example['geocsv']],
                     allow_first_segment=True, time_tolerance=0.001)
    source = trace.stats.geocsv
    assert source.association == 'first_segment'
    assert source.SampleCount != trace.stats.npts == source.waveform_sample_count == count
    path = tmp_path / 'clipped.sac'
    geocsv.write_sac(trace, path)
    actual = SACTrace.read(str(path))
    reference = SACTrace.read(str(FIXTURES / example['sac']))
    for key in ('stla', 'stlo'):
        tolerance = 0.5e-6 + abs(float(np.spacing(np.float32(getattr(reference, key)))))
        assert getattr(actual, key) == pytest.approx(getattr(reference, key), abs=tolerance)
    assert actual.stdp == reference.stdp
    assert actual.stel == reference.stel == 0
    np.testing.assert_array_equal(actual.data, before.data.astype(np.float32))
    assert abs(actual.to_obspy_trace(round_sampling_interval=False).stats.starttime.ns
               - before.stats.starttime.ns) <= 1000
    np.testing.assert_array_equal(trace.data, before.data)
    # An association-time snapshot prevents a later length change from silently
    # exporting samples whose source coverage has never been checked.
    trace.data = np.append(trace.data, 0)
    with pytest.raises(ValueError, match='association-time loaded sample count'):
        geocsv.write_sac(trace, tmp_path / 'changed.sac')
    assert not (tmp_path / 'changed.sac').exists()


@pytest.mark.parametrize('value', [1e100, 1e-100, np.nan, np.inf, 1 + 2j])
def test_unrepresentable_samples_fail_before_file_creation(trace, tmp_path, value):
    trace.data = np.full(trace.stats.npts, value)
    before = trace.copy()
    with pytest.raises(ValueError, match='samples'):
        geocsv.write_sac(trace, tmp_path / 'invalid.sac')
    np.testing.assert_array_equal(trace.data, before.data)
    assert trace.stats == before.stats
    assert not list(tmp_path.iterdir())


def test_large_finite_float32_samples_have_finite_summary_headers(trace, tmp_path):
    trace.data = np.full(trace.stats.npts, np.finfo(np.float32).max, dtype=np.float32)
    geocsv.write_sac(trace, tmp_path / 'large.sac')
    written = SACTrace.read(str(tmp_path / 'large.sac'), headonly=True)
    assert written.depmin == written.depmax == written.depmen == np.finfo(np.float32).max


@pytest.mark.parametrize('code', ['ABCDEFGHI', 'SYNé', ' PAD ', '-12345'])
def test_identity_must_survive_sac_serialization(trace, tmp_path, code):
    trace.stats.station = trace.stats.geocsv.Station = code
    with pytest.raises(ValueError, match='ASCII SAC identity'):
        geocsv.write_sac(trace, tmp_path / 'invalid.sac')
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('field,value', [('WaterPressure', 1e100),
                                        ('WaterPressure', 1e-100),
                                        ('WaterPressure', 5e-324),
                                        ('calib', 1e100), ('calib', 1e-100),
                                        ('calib', -12345), ('calib', -12344.99999),
                                        ('SampleRate', 1e100)])
def test_unrepresentable_numeric_headers_fail_before_file_creation(trace, tmp_path, field, value):
    if field == 'calib':
        trace.stats.calib = value
    else:
        trace.stats.geocsv[field] = value
        if field == 'SampleRate':
            trace.stats.sampling_rate = value
    with pytest.raises(ValueError, match='float32|undefined'):
        geocsv.write_sac(trace, tmp_path / 'invalid.sac')
    assert not list(tmp_path.iterdir())
