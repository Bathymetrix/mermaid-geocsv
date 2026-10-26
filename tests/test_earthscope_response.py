"""Offline workflow evidence from a preserved, clipped EarthScope response."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

obspy = pytest.importorskip("obspy")
from obspy.io.sac import SACTrace

from mermaid import geocsv


FIXTURE = Path(__file__).parent / "fixtures/association/P0006_20180713_earthscope"
MANIFEST = json.loads((FIXTURE / "manifest.json").read_text())


def test_response_provenance_and_known_overlapping_originals():
    request = MANIFEST["request"]
    geocsv_source = MANIFEST["geocsv"]
    files = [request, geocsv_source]
    files.extend(original[extension] for original in MANIFEST["originals"]
                 for extension in ("mseed", "sac"))
    for item in files:
        content = (FIXTURE / item["path"]).read_bytes()
        assert len(content) == item["size_bytes"]
        assert hashlib.sha256(content).hexdigest() == item["sha256"]
    assert request["status"] == 200
    assert request["url"].startswith("https://service.earthscope.org/fdsnws/dataselect/1/query?")

    response, = obspy.read(str(FIXTURE / request["path"]), format="MSEED")
    detected, requested = [obspy.read(str(FIXTURE / item["mseed"]["path"]))[0]
                           for item in MANIFEST["originals"]]
    start = obspy.UTCDateTime(request["parameters"]["starttime"])
    end = obspy.UTCDateTime(request["parameters"]["endtime"])
    assert response.id == detected.id == requested.id == "MH.P0006.00.BDH"
    assert detected.stats.starttime < start < requested.stats.starttime
    assert requested.stats.starttime < detected.stats.endtime < end < requested.stats.endtime
    assert start <= response.stats.starttime < detected.stats.endtime
    assert detected.stats.endtime < response.stats.endtime <= end
    assert response.stats.npts == 9403
    assert response.stats.starttime.ns == 1531475290037533000
    assert abs(response.stats.endtime.ns - 1531475759971829792) <= 1
    assert response.stats.mseed.dataquality == "M"
    assert detected.stats.mseed.dataquality == "Q"
    assert requested.stats.mseed.dataquality == "D"
    assert response.stats.sampling_rate == detected.stats.sampling_rate == requested.stats.sampling_rate
    assert (detected.stats.npts, requested.stats.npts) == (4768, 9600)
    assert not np.ma.is_masked(response.data)
    # This is observed equality for this saved response, not an archive policy.
    np.testing.assert_array_equal(response.data[:4630], detected.data[138:4768])
    np.testing.assert_array_equal(response.data[4630:], requested.data[4192:8965])
    for original in MANIFEST["originals"]:
        mseed, = obspy.read(str(FIXTURE / original["mseed"]["path"]))
        sac, = obspy.read(str(FIXTURE / original["sac"]["path"]),
                          round_sampling_interval=False)
        assert sac.id == mseed.id
        np.testing.assert_array_equal(sac.data, mseed.data)


def test_clipped_earthscope_response_association_and_sac_export(tmp_path):
    # Read raw response bytes directly: no client trim, explicit merge, resampling or fill.
    waveform, = obspy.read(str(FIXTURE / MANIFEST["request"]["path"]), format="MSEED")
    tables = geocsv.read(FIXTURE / MANIFEST["geocsv"]["path"])
    original = waveform.copy()
    with pytest.raises(ValueError, match="no match"):
        geocsv.associate(waveform, tables, time_tolerance=0.001)
    assert waveform.stats == original.stats
    np.testing.assert_array_equal(waveform.data, original.data)
    # Source-grid placement is automatic; no absolute time override is needed.
    geocsv.associate(waveform, tables, allow_first_segment=True, create_sac_header=True)
    attached = waveform.stats.geocsv
    report = attached.association
    assert report.type == "anchor_segment"
    assert attached.source_record_index == 237
    assert attached.SampleCount == 4768
    assert attached.DataQuality == "Q"  # Native archive M is not a selection hint.
    assert report.waveform.sample_count == waveform.stats.npts == 9403
    assert report.waveform_start_offset_seconds == 6.898533
    first, second = report.coverage_segments
    assert first.location == second.location == waveform.stats.location == "00"
    assert [(row.dataset_index, row.source_record_index, row.source_line_number)
            for row in (first, second)] == [(0, 237, 247), (0, 238, 248)]
    assert [(row.waveform_sample_start, row.waveform_sample_stop)
            for row in (first, second)] == [(0, 4630), (438, 9403)]
    assert first.starttime < waveform.stats.starttime < first.endtime
    assert second.starttime < waveform.stats.endtime < second.endtime
    assert first.waveform_sample_stop - second.waveform_sample_start == 4192
    assert dict(report.max_sample_grid_offset) == {
        "seconds": 0.021813578, "dataset_index": 0, "source_record_index": 238,
        "source_line_number": 248, "waveform_sample_index": 438}
    assert report.max_sample_grid_offset.seconds < waveform.stats.delta / 2
    assert report.max_sample_rate_difference.hz == pytest.approx(1.8617771502249525e-7, abs=1e-15)
    assert all(waveform.stats[key] == value for key, value in original.stats.items())
    np.testing.assert_array_equal(waveform.data, original.data)

    before_export = waveform.copy()
    output = tmp_path / "P0006_clipped.sac"
    assert waveform.write(str(output), format="SAC") is None
    actual = SACTrace.read(str(output))
    reference = SACTrace.read(str(FIXTURE / MANIFEST["originals"][0]["sac"]["path"]))
    for key, field in (("stla", "Latitude"), ("stlo", "Longitude")):
        # The export must exactly reflect the current source at SAC precision.
        assert getattr(actual, key) == np.float32(attached[field])
        # GeoCSV's float64 calculation and the independent float32 SAC
        # reference may round to adjacent representable float32 values.
        np.testing.assert_array_max_ulp(
            np.float32(getattr(actual, key)),
            np.float32(getattr(reference, key)), maxulp=1)
    for key in ("stdp", "stel"):
        assert getattr(actual, key) == getattr(reference, key)
    assert actual.npts == waveform.stats.npts
    assert actual.delta == np.float32(waveform.stats.delta)
    reopened = actual.to_obspy_trace(round_sampling_interval=False)
    assert reopened.id == waveform.id
    assert abs(reopened.stats.starttime.ns - waveform.stats.starttime.ns) <= 1000
    np.testing.assert_array_equal(actual.data, original.data.astype(np.float32))
    assert waveform.stats == before_export.stats
    np.testing.assert_array_equal(waveform.data, before_export.data)
