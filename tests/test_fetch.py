"""Manifest-based downloads through a local HTTP server; no public endpoint."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
from threading import Thread
from types import SimpleNamespace

import pandas as pd
import pytest

from mermaid import geocsv


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def collection(tmp_path):
    root = tmp_path / "server"
    directory = root / "releases" / "test-001"
    directory.mkdir(parents=True)
    entries = []
    # Two real instruments plus an invented entry for multiple-dataset parsing.
    # Keep the small synthetic entry second for the partial-batch failure test.
    for instrument, source in [("P0006", FIXTURES / "geocsv/P0006.geocsv"),
                               ("P_TEST", FIXTURES / "typed.geocsv"),
                               ("P0045", FIXTURES / "geocsv/P0045.geocsv")]:
        destination = directory / f"{instrument}.geocsv"
        shutil.copyfile(source, destination)
        if instrument == "P_TEST":
            with destination.open("ab") as stream:
                stream.write((FIXTURES / "multiline.geocsv").read_bytes())
        content = destination.read_bytes()
        entries.append({
            "instrument_id": instrument, "filename": destination.name,
            "size_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(),
            "provenance": {"source_path": str(source), "manual_edits": instrument == "P_TEST",
                           "notes": "Package-local test fixture"},
        })
    manifest = {"release_id": "test-001", "testing_only": True,
                "created_utc": "2026-10-20T00:00:00Z",
                "description": "Local download tests", "files": entries}
    manifest_path = directory / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    latest = {"release_id": "test-001", "testing_only": True,
              "manifest": "releases/test-001/manifest.json"}
    (root / "latest.json").write_text(json.dumps(latest), encoding="utf-8")
    requests = []

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

        def do_GET(self):
            requests.append(self.path)
            super().do_GET()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    client = tmp_path / "client"
    client.mkdir()
    try:
        yield SimpleNamespace(
            root=root, directory=directory, manifest=manifest,
            manifest_path=manifest_path, requests=requests, client=client,
            url=f"http://127.0.0.1:{server.server_port}/",
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def update_manifest(collection):
    collection.manifest_path.write_text(json.dumps(collection.manifest), encoding="utf-8")


def test_memory_all_real_fixture_and_metadata(collection, monkeypatch):
    monkeypatch.chdir(collection.client)
    results = geocsv.fetch(base_url=collection.url, output_dir=None)
    assert [result.provenance.instrument_id for result in results] == ["P0006", "P_TEST", "P0045"]
    assert list(collection.client.iterdir()) == []
    assert all(result.path is None and isinstance(result.content, bytes) for result in results)
    first = results[0]
    assert len(first.content) == 3_001_102
    assert first.provenance.sha256 == "07dfbbe639bacde403bb2b9d15eaf5d3ea8840ad17f11e3dde36d52ccbd17fa3"
    assert first.provenance.manifest == collection.manifest_path.read_bytes()
    assert first.provenance.testing_only is True
    assert first.provenance.release_id == "test-001"
    assert json.loads(first.provenance.manifest)["files"][0]["provenance"]["manual_edits"] is False
    frames = geocsv.read(results)
    assert len(frames) == 4
    assert len(results[2].content) == 18_031_573
    assert frames[3]["Station"].eq("P0045").all()
    assert frames[3].index.equals(pd.RangeIndex(len(frames[3]), name="source_record_index"))
    assert frames[3]["SampleCount"].dtype == pd.Int64Dtype()
    assert frames[3].attrs["geocsv"].download is results[2].provenance
    frame = frames[0]
    assert len(frame) == 20_345
    assert frame.index.equals(pd.RangeIndex(20_345, name="source_record_index"))
    assert frame["SampleCount"].dtype == pd.Int64Dtype()
    assert frame["Latitude"].dtype == pd.Float64Dtype()
    assert frame["Station"].dtype == pd.StringDtype()
    assert frame["StartTime"].iloc[0].tzinfo is not None
    metadata = frame.attrs["geocsv"]
    assert metadata.source_path is None
    assert metadata.download is first.provenance
    assert metadata.download.url == collection.url + "releases/test-001/P0006.geocsv"
    assert metadata.field_units["Latitude"] == "degrees_north"
    assert metadata.datetime_resolution_ns["StartTime"][0] == 1_000_000
    assert deepcopy(metadata) is metadata
    with pytest.raises(FrozenInstanceError):
        metadata.download.release_id = "changed"
    expected, = geocsv.read(FIXTURES / "geocsv/P0006.geocsv")
    pd.testing.assert_frame_equal(frame, expected)
    assert frames[1].index.tolist() == [0, 1]
    assert frames[2].index.tolist() == [2, 3]
    assert frames[1].attrs["geocsv"].download is results[1].provenance
    assert frames[2].attrs["geocsv"].download is results[1].provenance
    assert collection.requests.count("/latest.json") == 1
    assert collection.requests.count("/releases/test-001/manifest.json") == 1


def test_default_local_output_and_reuse(collection, monkeypatch):
    monkeypatch.chdir(collection.client)
    first, = geocsv.fetch("P0006", base_url=collection.url.rstrip("/"))
    assert first.path == collection.client / "test-001/P0006.geocsv"
    assert first.content is None
    assert first.path.read_bytes() == (FIXTURES / "geocsv/P0006.geocsv").read_bytes()
    assert (first.path.parent / "manifest.json").read_bytes() == first.provenance.manifest
    frame, = geocsv.read(first)
    assert frame.attrs["geocsv"].source_path == first.path
    assert frame.attrs["geocsv"].download is first.provenance
    local, = geocsv.read(first.path)
    assert local.attrs["geocsv"].download is None
    collection.requests.clear()
    second, = geocsv.fetch("P0006", base_url=collection.url)
    assert second == first
    assert collection.requests == ["/latest.json", "/releases/test-001/manifest.json"]


def test_selected_order_and_explicit_release_bypass_latest(collection):
    (collection.root / "latest.json").unlink()
    results = geocsv.fetch(["P0045", "P0006"], base_url=collection.url,
                           output_dir=collection.client / "downloads", release="test-001")
    assert [result.provenance.instrument_id for result in results] == ["P0045", "P0006"]
    assert results[0].path.parent == collection.client / "downloads/test-001"
    assert "/latest.json" not in collection.requests
    frames = geocsv.read(results)
    assert frames[0]["Station"].eq("P0045").all()
    assert frames[1]["Station"].eq("P0006").all()
    assert frames[0].attrs["geocsv"].download is results[0].provenance
    assert frames[1].attrs["geocsv"].download is results[1].provenance
    assert "/releases/test-001/P_TEST.geocsv" not in collection.requests


def test_missing_instrument_has_no_partial_output(collection):
    with pytest.raises(geocsv.GeoCSVFetchError, match="instruments not found.*p0006"):
        geocsv.fetch(["P0006", "p0006"], base_url=collection.url, output_dir=collection.client)
    assert list(collection.client.iterdir()) == []
    assert not any(path.endswith(".geocsv") for path in collection.requests)


def test_explicit_missing_release_never_falls_back(collection):
    with pytest.raises(geocsv.GeoCSVFetchError, match="404"):
        geocsv.fetch(base_url=collection.url, release="absent", output_dir=None)
    assert collection.requests == ["/releases/absent/manifest.json"]


@pytest.mark.parametrize("output_memory", [False, True])
@pytest.mark.parametrize("damage,match", [("short", "byte count"), ("long", "byte count"),
                                         ("corrupt", "SHA-256")])
def test_integrity_failure_does_not_accept_file(collection, output_memory, damage, match):
    path = collection.directory / "P0006.geocsv"
    content = path.read_bytes()
    path.write_bytes({"short": content[:-1], "long": content + b"x",
                      "corrupt": b"!" + content[1:]}[damage])
    with pytest.raises(geocsv.GeoCSVFetchError, match=f"P0006:.*{match}"):
        geocsv.fetch("P0006", base_url=collection.url,
                     output_dir=None if output_memory else collection.client)
    assert not list(collection.client.rglob("*.geocsv"))
    assert not list(collection.client.rglob(".geocsv-*"))


def test_later_failure_retains_earlier_verified_file(collection):
    (collection.directory / "P_TEST.geocsv").unlink()
    with pytest.raises(geocsv.GeoCSVFetchError, match="P_TEST:.*404"):
        geocsv.fetch(base_url=collection.url, output_dir=collection.client)
    saved = collection.client / "test-001/P0006.geocsv"
    assert saved.read_bytes() == (collection.directory / "P0006.geocsv").read_bytes()
    assert (saved.parent / "manifest.json").is_file()
    assert not list(saved.parent.glob(".geocsv-*"))


@pytest.mark.parametrize("target", ["manifest.json", "P0006.geocsv"])
def test_conflicting_output_is_not_overwritten(collection, target):
    directory = collection.client / "test-001"
    directory.mkdir()
    path = directory / target
    path.write_bytes(b"existing user content")
    with pytest.raises(FileExistsError, match="different"):
        geocsv.fetch("P0006", base_url=collection.url, output_dir=collection.client)
    assert path.read_bytes() == b"existing user content"


def test_saved_result_is_reverified_when_read(collection):
    result, = geocsv.fetch("P0006", base_url=collection.url, output_dir=collection.client)
    result.path.write_bytes(b"modified after fetch\n")
    with pytest.raises(geocsv.GeoCSVFetchError, match="byte count"):
        geocsv.read(result)


def test_release_directories_remain_distinct(collection):
    first, = geocsv.fetch("P0006", base_url=collection.url, output_dir=collection.client)
    second_directory = collection.root / "releases/test-002"
    shutil.copytree(collection.directory, second_directory)
    manifest = deepcopy(collection.manifest)
    manifest["release_id"] = "test-002"
    (second_directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    second, = geocsv.fetch("P0006", base_url=collection.url, output_dir=collection.client,
                           release="test-002")
    assert first.path.parent.name == "test-001"
    assert second.path.parent.name == "test-002"
    assert first.path.read_bytes() == second.path.read_bytes()
    assert first.provenance.release_id != second.provenance.release_id


def test_memory_result_associates_without_losing_download_provenance(collection):
    obspy = pytest.importorskip("obspy")
    import numpy as np

    content = (FIXTURES / "association/synthetic.geocsv").read_bytes()
    (collection.directory / "P0006.geocsv").write_bytes(content)
    collection.manifest["files"][0].update(size_bytes=len(content),
                                           sha256=hashlib.sha256(content).hexdigest())
    update_manifest(collection)
    results = geocsv.fetch("P0006", base_url=collection.url, output_dir=None)
    trace = obspy.Trace(np.arange(4, dtype=np.float32), header={
        "network": "MH", "station": "SYN01", "location": "00", "channel": "BDH",
        "sampling_rate": 20,
        "starttime": obspy.UTCDateTime(ns=pd.Timestamp("2025-01-01T00:00:00.123456789Z").value),
    })
    geocsv.associate(trace, geocsv.read(results))
    assert trace.stats.geocsv.metadata.source_path is None
    assert trace.stats.geocsv.metadata.download is results[0].provenance
    assert trace.stats.coordinates.latitude == 10
    assert trace.stats.geocsv.source_record_index == 1


@pytest.mark.parametrize("change,match", [
    (lambda m: m.update(release_id="other"), "release_id"),
    (lambda m: m.update(testing_only=False), "flags must agree"),
    (lambda m: m["files"].append(m["files"][0]), "duplicate"),
    (lambda m: m["files"][0].update(filename="../escape.geocsv"), "filename"),
    (lambda m: m["files"][0].update(size_bytes=True), "size_bytes"),
    (lambda m: m["files"][0].update(sha256="wrong"), "sha256"),
])
def test_invalid_manifest_fails_before_output(collection, change, match):
    change(collection.manifest)
    update_manifest(collection)
    with pytest.raises(geocsv.GeoCSVFetchError, match=match):
        geocsv.fetch(base_url=collection.url, output_dir=collection.client)
    assert list(collection.client.iterdir()) == []
    assert not any(path.endswith(".geocsv") for path in collection.requests)


def test_invalid_json_and_pointer_path(collection):
    pointer = collection.root / "latest.json"
    pointer.write_bytes(b"not json")
    with pytest.raises(geocsv.GeoCSVFetchError, match="invalid UTF-8 JSON"):
        geocsv.fetch(base_url=collection.url, output_dir=None)
    pointer.write_text(json.dumps({"release_id": "test-001", "testing_only": True,
                                   "manifest": "https://elsewhere/manifest.json"}))
    with pytest.raises(geocsv.GeoCSVFetchError, match="manifest path"):
        geocsv.fetch(base_url=collection.url, output_dir=None)


@pytest.mark.parametrize("kwargs", [
    {"instrument_ids": []}, {"instrument_ids": ["P0006", "P0006"]},
    {"release": "../escape"}, {"timeout": 0}, {"timeout": float("nan")},
    {"base_url": "file:///tmp/collection/"},
])
def test_invalid_arguments_do_not_request(collection, kwargs):
    arguments = {"base_url": collection.url, "output_dir": None, **kwargs}
    with pytest.raises(ValueError):
        geocsv.fetch(**arguments)
    assert collection.requests == []


def test_byte_input_uses_same_parser_and_no_invented_provenance():
    content = (FIXTURES / "typed.geocsv").read_bytes()
    frame, = geocsv.read(content, datetime_timezone="UTC")
    assert frame.attrs["geocsv"].source_path is None
    assert frame.attrs["geocsv"].download is None
    assert str(frame["StartTime"].dtype).endswith(", UTC]")
    with pytest.raises(geocsv.GeoCSVError, match="<memory>:.*invalid UTF-8"):
        geocsv.read(b"#dataset: GeoCSV\nHeader\n\xff\n")
    with pytest.raises(geocsv.GeoCSVError, match="LF or CRLF"):
        geocsv.read(b"#dataset: GeoCSV\nHeader\nvalue")
    with pytest.raises(TypeError, match="GeoCSVFetchResult"):
        geocsv.read([FIXTURES / "typed.geocsv"])


def test_fetched_parser_error_identifies_url(collection):
    path = collection.directory / "P0006.geocsv"
    content = b"#dataset: GeoCSV\nHeader\nunterminated"
    path.write_bytes(content)
    collection.manifest["files"][0].update(size_bytes=len(content),
                                           sha256=hashlib.sha256(content).hexdigest())
    update_manifest(collection)
    results = geocsv.fetch("P0006", base_url=collection.url, output_dir=None)
    with pytest.raises(geocsv.GeoCSVError, match=r"http://.*P0006.geocsv:.*LF or CRLF"):
        geocsv.read(results)


@pytest.mark.parametrize('memory', [False, True])
@pytest.mark.parametrize('clipped', [False, True])
def test_real_download_read_associate_write_sac_pipeline(collection, memory, clipped):
    obspy = pytest.importorskip('obspy')
    import numpy as np
    from obspy.io.sac import SACTrace

    downloads = geocsv.fetch('P0045', base_url=collection.url,
                             output_dir=None if memory else collection.client)
    tables = geocsv.read(downloads)
    directory = FIXTURES / 'association/P0045_20220115'
    manifest = json.loads((directory / 'manifest.json').read_text())
    item = manifest['selected'][0]
    trace, = obspy.read(str(directory / item['mseed']['path']))
    if clipped:
        trace.stats.starttime += 10 / trace.stats.sampling_rate
        trace.data = trace.data[10:110].copy()
    geocsv.associate(trace, tables, time_tolerance=0.001, allow_first_segment=clipped)
    assert trace.stats.geocsv.metadata.download is downloads[0].provenance
    assert trace.stats.geocsv.association == ('first_segment' if clipped else 'one_segment')
    output = collection.client / 'located.sac'
    geocsv.write_sac(trace, output)
    actual = SACTrace.read(str(output))
    reference = SACTrace.read(str(directory / item['sac']['path']))
    assert actual.to_obspy_trace(round_sampling_interval=False).id == trace.id
    assert actual.stla == np.float32(trace.stats.geocsv.Latitude)
    assert actual.stlo == np.float32(trace.stats.geocsv.Longitude)
    assert actual.stdp is reference.stdp is None  # REQ has no measured pressure.
    expected = reference.data[10:110] if clipped else reference.data
    np.testing.assert_array_equal(actual.data, expected)
