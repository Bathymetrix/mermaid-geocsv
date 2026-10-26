"""Keep tutorial prose and executable examples synchronized."""

import json
import inspect
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
from threading import Thread

import pytest

from mermaid import geocsv


ROOT = Path(__file__).resolve().parents[1]
TUTORIALS = ROOT / "docs" / "tutorials"
NAMES = sorted(path.stem for path in TUTORIALS.glob("*.md"))
TEST_RELEASE = "2026-10-21T22:48:33.277Z"


@pytest.fixture
def tutorial_collection(tmp_path):
    """Keep hosted tutorial examples runnable without the public service."""
    server_root = tmp_path / "server"
    release_directory = server_root / "releases" / TEST_RELEASE
    release_directory.mkdir(parents=True)
    entries = []
    for instrument in ("P0006", "P0045"):
        source = ROOT / f"data/fixtures/{instrument}/{instrument}.geocsv"
        content = source.read_bytes()
        (release_directory / source.name).write_bytes(content)
        entries.append({
            "instrument_id": instrument, "filename": source.name,
            "size_bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "provenance": {"notes": "Unmodified tracked fixture"},
        })
    manifest = {"release_id": TEST_RELEASE, "testing_only": True, "files": entries}
    (release_directory / "manifest.json").write_text(json.dumps(manifest))
    (server_root / "latest.json").write_text(json.dumps({
        "release_id": TEST_RELEASE, "testing_only": True,
        "manifest": "releases/2026-10-21T22%3A48%3A33.277Z/manifest.json",
    }))
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
        name.upper() for name in geocsv.__all__
        if inspect.isfunction(getattr(geocsv, name))
    }
    assert public_functions <= set(NAMES)
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
    if name in {"ASSOCIATE", "WRITE_SAC"}:
        pytest.importorskip("obspy")
    if name == "PLOTTING":
        matplotlib = pytest.importorskip("matplotlib")
        matplotlib.use("Agg")
    if name == "FETCH":
        collection_url = request.getfixturevalue("tutorial_collection")
        real_fetch = geocsv.fetch

        def fetch_from_local_collection(*args, **kwargs):
            assert kwargs["base_url"] == "https://bathymetrix.com/geocsv/testing/"
            kwargs["base_url"] = collection_url
            if kwargs.get("output_dir") is not None:
                assert kwargs["output_dir"] == "geocsv-downloads"
                kwargs["output_dir"] = tmp_path / "downloads"
            return real_fetch(*args, **kwargs)

        monkeypatch.setattr(geocsv, "fetch", fetch_from_local_collection)
    markdown = (TUTORIALS / f"{name}.md").read_text()
    examples = re.findall(r"(?m)^```python\n(.*?)^```", markdown, flags=re.S)
    monkeypatch.chdir(working_directory)
    namespace = {"__name__": "__main__"}
    for number, example in enumerate(examples, start=1):
        exec(compile(example, f"{name}.md:block-{number}", "exec"),
             namespace)
    if name == "PLOTTING":
        assert not namespace["pressure"].empty
        assert not namespace["gps"].empty
        namespace["plt"].close("all")
    if name == "ASSOCIATE":
        assert namespace["trace"].stats.geocsv.association.type == "single_segment"
        assert len(namespace["stream"]) == 3
        assert all(item.stats.geocsv.association.type == "single_segment"
                   for item in namespace["stream"])
        window = namespace["window"]
        assert window.stats.geocsv.association.type == "anchor_segment"
        assert window.stats.geocsv.association.waveform_start_offset_seconds > 0.9
        assert window.stats.geocsv.association.waveform.sample_count == window.stats.npts
        assert len(window.stats.geocsv.association.coverage_segments) == 1
    if name == "WRITE_SAC":
        import numpy as np

        assert "sac" in namespace["trace"].stats
        assert namespace["trace"].stats.geocsv.association.type == "single_segment"
        reopened = namespace["reopened"]
        assert reopened.stats.sac.stla == np.float32(namespace["trace"].stats.geocsv.Latitude)
        assert reopened.stats.sac.stlo == np.float32(namespace["trace"].stats.geocsv.Longitude)
        np.testing.assert_array_equal(reopened.data, namespace["trace"].data.astype(np.float32))
    if name == "FETCH":
        assert namespace["downloads"][0].provenance.testing_only is True
        assert namespace["records"]["Station"].eq("P0006").all()
        saved = namespace["saved"]
        assert [item.provenance.instrument_id for item in saved] == ["P0006", "P0045"]
        assert all(item.path.is_file() for item in saved)
        assert namespace["pinned"][0].provenance.release_id == TEST_RELEASE
        assert namespace["pinned"][0].content == namespace["downloads"][0].content


@pytest.mark.parametrize("name", NAMES)
def test_development_examples(name, monkeypatch):
    """Retain executable checks moved out of the introductory tutorials."""
    if name in {"ASSOCIATE", "WRITE_SAC"}:
        pytest.importorskip("obspy")
    if name == "PLOTTING":
        matplotlib = pytest.importorskip("matplotlib")
        matplotlib.use("Agg")
    markdown = (ROOT / "docs/development" / f"{name}.md").read_text()
    examples = re.findall(r"(?m)^```python\n(.*?)^```", markdown, flags=re.S)
    monkeypatch.chdir(ROOT)
    namespace = {"__name__": "__main__"}
    for number, example in enumerate(examples, start=1):
        exec(compile(example, f"development/{name}.md:block-{number}", "exec"),
             namespace)
    if name == "PLOTTING":
        namespace["plt"].close("all")
    if name == "ASSOCIATE":
        sac_trace = namespace["sac_trace"]
        assert sac_trace.stats.sac.stla == sac_trace.stats.geocsv.Latitude
        assert sac_trace.stats.sac.stlo == sac_trace.stats.geocsv.Longitude
        window = namespace["window"]
        assert window.stats.geocsv.association.type == "anchor_segment"
        assert window.stats.geocsv.association.waveform_start_offset_seconds > 0.9
        assert window.stats.geocsv.association.waveform.sample_count == window.stats.npts
        assert len(window.stats.geocsv.association.coverage_segments) == 2
        assert window.stats.geocsv.association.coverage_segments[0].source_record_index == 101433
        assert 0.001 < window.stats.geocsv.association.max_sample_grid_offset.seconds < window.stats.delta / 2
    if name == "WRITE_SAC":
        assert namespace["request"].stats.sac.stdp == -12345.0
        assert namespace["written"].stdp is not None
        assert namespace["request_sac"].stdp is None
        assert namespace["merged"].stats.geocsv.association.type == "anchor_segment"
        assert namespace["merged_sac"].npts == namespace["merged"].stats.npts
        assert namespace["merged_sac"].stdp is None
