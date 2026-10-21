"""Keep tutorial prose and executable examples synchronized."""

import json
import inspect
from pathlib import Path
import re

import pytest

from mermaid import geocsv


ROOT = Path(__file__).resolve().parents[1]
TUTORIALS = ROOT / "docs" / "tutorials"
NAMES = sorted(path.stem for path in TUTORIALS.glob("*.md"))


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
def test_tutorial_examples(name, working_directory, monkeypatch):
    if name in {"ASSOCIATE", "WRITE_SAC"}:
        pytest.importorskip("obspy")
    if name == "PLOTTING":
        matplotlib = pytest.importorskip("matplotlib")
        matplotlib.use("Agg")
    markdown = (TUTORIALS / f"{name}.md").read_text()
    examples = re.findall(r"(?m)^```python\n(.*?)^```", markdown, flags=re.S)
    monkeypatch.chdir(working_directory)
    namespace = {"__name__": "__main__"}
    for number, example in enumerate(examples, start=1):
        exec(compile(example, f"{name}.md:block-{number}", "exec"),
             namespace)
    if name == "PLOTTING":
        namespace["plt"].close("all")
    if name == "ASSOCIATE":
        window = namespace["window"]
        assert window.stats.geocsv.association.type == "anchor_segment"
        assert window.stats.geocsv.association.waveform_start_offset_seconds > 0.9
        assert window.stats.geocsv.association.waveform.sample_count == window.stats.npts
        assert len(window.stats.geocsv.association.coverage_segments) == 2
        assert window.stats.geocsv.association.coverage_segments[0].source_record_index == 101433
        assert window.stats.geocsv.association.max_sample_grid_offset.seconds > 0.001
    if name == "WRITE_SAC":
        assert namespace["trace"].stats.geocsv.association.type == "single_segment"
        assert namespace["written"].stdp is not None
        assert namespace["request_sac"].stdp is None
        assert namespace["merged"].stats.geocsv.association.type == "anchor_segment"
        assert namespace["merged_sac"].npts == namespace["merged"].stats.npts
        assert namespace["merged_sac"].stdp is None
