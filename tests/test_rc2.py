"""Exercise rc2 using exact bytes from an automaid export."""

import csv
import hashlib
import io
import json
from pathlib import Path

import pandas as pd
import pytest

from mermaid import geocsv


FIXTURES = Path(__file__).resolve().parents[1] / "data/fixtures/schema-1.0.0-rc2"


def test_rc2_fixture_provenance_and_typed_source_columns():
    manifest = json.loads((FIXTURES / "manifest.json").read_text())
    for entry in manifest["files"]:
        path = FIXTURES / entry["path"]
        content = path.read_bytes()
        assert len(content) == entry["size_bytes"]
        assert hashlib.sha256(content).hexdigest() == entry["sha256"]
        frame, = geocsv.read(path)
        metadata = frame.attrs["geocsv"]
        assert metadata.schema_version == "1.0.0-rc2"
        assert metadata.created == manifest["created"]
        assert frame.index.equals(pd.RangeIndex(len(frame), name="source_index"))
        for name in ("measured_time", "derived_time"):
            assert str(frame[name].dtype) == "datetime64[ns, UTC]"
            assert set(metadata.datetime_resolution_ns[name]) == set(frame.index[frame[name].notna()])
        assert str(frame["sample_count"].dtype) == "Int64"
        assert str(frame["measured_pressure"].dtype) == "Float64"
        assert metadata.field_units["estimated_pressure"] == "mbar"
        waveforms = frame.loc[frame["type"].eq("waveform")]
        assert "00" in set(waveforms.location)
        assert waveforms.measured_time.isna().all()
        assert waveforms.time_correction_applied.notna().all()
    frame, = geocsv.read(FIXTURES / "P0006.geocsv")
    assert set(frame["type"]) == {"gps", "pressure", "downcrossing", "upcrossing", "waveform"}
    assert frame.loc[frame["type"].eq("pressure"), "estimated_latitude"].notna().any()


@pytest.mark.parametrize("kind,changes,message", [
    ("downcrossing", {"time_correction_applied": "0"}, "inapplicable to downcrossing"),
    ("pressure", {"estimated_latitude": "10", "estimated_longitude": ""}, "occur together"),
    ("pressure", {"derived_time": "2018-07-01T00:00:00.000000Z"}, "inapplicable to pressure"),
    ("waveform", {"sample_count": "0"}, "must be positive"),
    ("gps", {"measured_latitude": "91"}, "outside"),
])
def test_rc2_rejects_invalid_fields(kind, changes, message):
    lines = (FIXTURES / "P0006.geocsv").read_text().splitlines(keepends=True)
    header = next(i for i, line in enumerate(lines) if not line.startswith("#"))
    fields = next(csv.reader([lines[header]]))
    source = next(row for row in csv.DictReader(lines[header:]) if row["type"] == kind)
    source.update(changes)
    contents = io.StringIO(newline="")
    contents.writelines(lines[:header + 1])
    csv.DictWriter(contents, fields, lineterminator="\n").writerow(source)
    with pytest.raises(geocsv.GeoCSVError, match=message):
        geocsv.read(contents.getvalue().encode())


@pytest.mark.parametrize("source_code,trace_code", [("40", "40"), ("  ", "")])
def test_rc2_associates_literal_location_codes(source_code, trace_code):
    obspy = pytest.importorskip("obspy")
    import numpy as np

    lines = (FIXTURES / "P0006.geocsv").read_text().splitlines(keepends=True)
    header = next(i for i, line in enumerate(lines) if not line.startswith("#"))
    fields = next(csv.reader([lines[header]]))
    match = next(row for row in csv.DictReader(lines[header:]) if row["type"] == "waveform")
    match.update(location=source_code, channel="MDH", sample_rate="2.5", sample_count="4")
    contents = io.StringIO(newline="")
    contents.writelines(lines[:header + 1])
    csv.DictWriter(contents, fields, quoting=csv.QUOTE_ALL, lineterminator="\n").writerow(match)
    tables = geocsv.read(contents.getvalue().encode())
    trace = obspy.Trace(np.arange(4, dtype=np.int32), header={
        "network": match["network"], "station": match["station"], "location": trace_code,
        "channel": "MDH", "starttime": obspy.UTCDateTime(match["derived_time"]),
        "sampling_rate": 2.5,
    })
    geocsv.associate(trace, tables, create_sac_header=True)
    assert trace.stats.geocsv.location == source_code
    assert trace.stats.geocsv.type == "waveform"
    assert set(trace.stats.coordinates) == {"latitude", "longitude"}
    assert "stel" not in trace.stats.sac
