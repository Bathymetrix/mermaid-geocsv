"""Keep tutorial prose and executable examples synchronized."""

import json
import inspect
import hashlib
from pathlib import Path
import re
from types import SimpleNamespace
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from mermaid import geocsv


ROOT = Path(__file__).resolve().parents[1]
TUTORIALS = ROOT / "tutorials"
NAMES = sorted(path.stem for path in TUTORIALS.glob("*.md"))
TEST_RELEASE = "2026-10-30T18:08:32.316000Z"
HOSTED_FIXTURES = ROOT / "data/fixtures/schema-1.0.0/hosted"


@pytest.fixture
def tutorial_collection(tmp_path):
    """Replay published prefixes without requiring public network availability."""
    server_root = tmp_path / "server"
    component = TEST_RELEASE.replace(":", "-")
    directory = server_root / "releases" / component
    directory.mkdir(parents=True)
    entries = []
    for instrument in ("P0006", "P0045"):
        name = f"{instrument}.geocsv"
        content = (HOSTED_FIXTURES / name).read_bytes()
        (directory / name).write_bytes(content)
        entries.append({
            "instrument_id": instrument, "filename": name,
            "size_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(),
            "provenance": {"notes": "Offline replay prefix; not the complete hosted file"},
        })
    (directory / "manifest.json").write_text(json.dumps({
        "release_id": TEST_RELEASE, "testing_only": True, "files": entries}))
    (server_root / "latest.json").write_text(json.dumps({
        "release_id": TEST_RELEASE, "testing_only": True,
        "manifest": f"releases/{component}/manifest.json"}))
    handler = partial(SimpleHTTPRequestHandler, directory=str(server_root))
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        thread = Thread(target=server.serve_forever,
                        kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}/"
        finally:
            server.shutdown()
            thread.join()


def test_public_functions_have_tutorial_pairs():
    public_functions = {
        name.replace("_", "-") for name in geocsv.__all__
        if inspect.isfunction(getattr(geocsv, name))
    }
    assert public_functions <= {name.split("_", 1)[1] for name in NAMES}
    assert NAMES == ["01_fetch", "02_read", "03_associate", "04_write-sac",
                     "05_earthscope", "06_plotting"]
    assert set(NAMES) == {path.stem for path in TUTORIALS.glob("*.ipynb")}


@pytest.mark.parametrize("name", NAMES)
def test_markdown_notebook_parity(name):
    markdown = (TUTORIALS / f"{name}.md").read_text()
    notebook = json.loads((TUTORIALS / f"{name}.ipynb").read_text())
    parts = re.split(r"(?m)^```python\n(.*?)^```\n?", markdown, flags=re.S)
    markdown_prose = "".join(parts[::2])
    markdown_code = "\n".join(parts[1::2])
    notebook_prose = ""
    notebook_code = []
    for cell in notebook["cells"]:
        source = "".join(cell["source"])
        if cell["cell_type"] == "markdown":
            notebook_prose += source
        else:
            assert cell["cell_type"] == "code"
            assert cell["execution_count"] is None
            assert cell["outputs"] == []
            notebook_code.append(source)
    assert markdown_prose.split() == notebook_prose.split()
    # Cell boundaries and blank lines can differ for interactive readability.
    assert [line.rstrip() for line in markdown_code.splitlines() if line.strip()] == [
        line.rstrip() for line in "\n".join(notebook_code).splitlines() if line.strip()
    ]


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("working_directory", [ROOT, ROOT / "docs", TUTORIALS])
def test_tutorial_examples(name, working_directory, monkeypatch, tmp_path, request):
    operation = name.split("_", 1)[1]
    if operation in {"associate", "write-sac", "earthscope"}:
        pytest.importorskip("obspy")
    if operation == "plotting":
        matplotlib = pytest.importorskip("matplotlib")
        matplotlib.use("Agg")
    if operation in {"fetch", "earthscope"}:
        real_fetch = geocsv.fetch
        local_base_url = request.getfixturevalue("tutorial_collection")

        def fetch_from_local_collection(*args, **kwargs):
            assert kwargs["base_url"] == "https://bathymetrix.com/geocsv/testing/"
            kwargs["base_url"] = local_base_url
            if kwargs.get("output_dir") is not None:
                assert kwargs["output_dir"] == "geocsv-downloads"
                kwargs["output_dir"] = tmp_path / "downloads"
            return real_fetch(*args, **kwargs)

        monkeypatch.setattr(geocsv, "fetch", fetch_from_local_collection)
    if operation == "earthscope":
        import tempfile

        fixtures = ROOT / "data/fixtures/P0006/waveforms"
        manifest = json.loads((fixtures / "manifest.json").read_text())
        waveform_requests = []
        source, = geocsv.read(HOSTED_FIXTURES / "P0006.geocsv")

        def replay_waveforms(**kwargs):
            example = manifest["examples"][len(waveform_requests)]
            parameters = example["request"]["parameters"]
            assert set(kwargs) == set(parameters) | {"filename"}
            for key, value in parameters.items():
                if key in {"starttime", "endtime"}:
                    from obspy import UTCDateTime

                    row = source.loc[example["source_record_index"]]
                    start = UTCDateTime(row.Time.isoformat())
                    last = start + (int(row.SampleCount) - 1) / float(row.SampleRate)
                    expected = start - 1 if key == "starttime" else last + 1
                    assert kwargs[key].ns == expected.ns
                else:
                    assert kwargs[key] == value
            Path(kwargs["filename"]).write_bytes(
                (fixtures / example["request"]["path"]).read_bytes())
            waveform_requests.append(example["source_record_index"])

        def replay_client(base_url, timeout):
            assert base_url == "https://service.earthscope.org"
            assert timeout == 30
            return SimpleNamespace(get_waveforms=replay_waveforms)

        monkeypatch.setattr("obspy.clients.fdsn.Client", replay_client)
        real_mkdtemp = tempfile.mkdtemp

        def local_mkdtemp(suffix=None, prefix=None, dir=None):
            return real_mkdtemp(suffix=suffix, prefix=prefix,
                                dir=tmp_path if dir is None else dir)

        monkeypatch.setattr(tempfile, "mkdtemp", local_mkdtemp)
    markdown = (TUTORIALS / f"{name}.md").read_text()
    examples = re.findall(r"(?m)^```python\n(.*?)^```", markdown, flags=re.S)
    monkeypatch.chdir(working_directory)
    namespace = {"__name__": "__main__"}
    for number, example in enumerate(examples, start=1):
        exec(compile(example, f"{name}.md:block-{number}", "exec"),
             namespace)
    if operation == "plotting":
        assert not namespace["pressure"].empty
        assert not namespace["gps"].empty
        namespace["plt"].close("all")
    if operation == "associate":
        assert namespace["trace"].stats.geocsv.association.type == "single_segment"
        assert len(namespace["stream"]) == 3
        assert all(item.stats.geocsv.association.type == "single_segment"
                   for item in namespace["stream"])
        window = namespace["window"]
        assert window.stats.geocsv.association.type == "anchor_segment"
        assert window.stats.geocsv.association.waveform_start_offset_seconds > 0.9
        assert window.stats.geocsv.association.waveform.sample_count == window.stats.npts
        assert len(window.stats.geocsv.association.coverage_segments) == 1
        combined, = namespace["combined"]
        assert combined.stats.npts == 45683
        assert combined.stats.geocsv.association.type == "anchor_segment"
        assert combined.stats.geocsv.source_record_index == 13
        assert len(combined.stats.geocsv.association.coverage_segments) == 2
    if operation == "write-sac":
        import numpy as np

        assert "sac" in namespace["trace"].stats
        assert namespace["trace"].stats.geocsv.association.type == "single_segment"
        reopened = namespace["reopened"]
        assert reopened.stats.sac.stla == np.float32(namespace["trace"].stats.geocsv.Latitude)
        assert reopened.stats.sac.stlo == np.float32(namespace["trace"].stats.geocsv.Longitude)
        np.testing.assert_array_equal(reopened.data, namespace["trace"].data.astype(np.float32))
        assert namespace["written_names"] == [
            "segment01.sac", "segment02.sac", "segment03.sac"]
        assert all("sac" in trace.stats for trace in namespace["stream"])
    if operation == "fetch":
        assert namespace["downloads"][0].provenance.testing_only is True
        assert namespace["records"]["Station"].eq("P0006").all()
        saved = namespace["saved"]
        assert [item.provenance.instrument_id for item in saved] == ["P0006", "P0045"]
        assert all(item.path.is_file() for item in saved)
        assert namespace["pinned"][0].provenance.release_id == TEST_RELEASE
        assert namespace["pinned"][0].content == namespace["downloads"][0].content
    if operation == "earthscope":
        assert waveform_requests == [98, 169, 239]
        assert namespace["trace"].stats.geocsv.association.type == "single_segment"
        assert namespace["waveform"].stats.geocsv.source_record_index == 239
        output_dir = namespace["output_dir"]
        assert len(list(output_dir.glob("*.mseed"))) == 3
        assert len(list(output_dir.glob("*.sac"))) == 3
        assert namespace["downloads"][0].provenance.release_id == TEST_RELEASE


def test_earthscope_tutorial_fixture_provenance():
    fixtures = ROOT / "data/fixtures/P0006/waveforms"
    manifest = json.loads((fixtures / "manifest.json").read_text())
    entries = [manifest["geocsv"]]
    for example in manifest["examples"]:
        entries.extend(example[key] for key in ("mseed", "sac", "request"))
    for entry in entries:
        content = (fixtures / entry["path"]).read_bytes()
        assert len(content) == entry["size_bytes"]
        assert hashlib.sha256(content).hexdigest() == entry["sha256"]


def test_hosted_tutorial_prefix_provenance():
    manifest = json.loads((HOSTED_FIXTURES / "manifest.json").read_text())
    assert manifest["release_id"] == TEST_RELEASE
    for item in manifest["files"]:
        path = HOSTED_FIXTURES / item["path"]
        content = path.read_bytes()
        assert len(content) == item["size_bytes"]
        assert hashlib.sha256(content).hexdigest() == item["sha256"]
        frame, = geocsv.read(path)
        assert frame.index.tolist() == item["source_record_indices"] == list(range(300))
        assert frame.attrs["geocsv"].created == TEST_RELEASE
