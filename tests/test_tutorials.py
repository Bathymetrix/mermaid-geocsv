"""Keep tutorial prose and executable examples synchronized."""

import json
from pathlib import Path
import re

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("name", ["TUTORIAL", "ASSOCIATION_TUTORIAL"])
def test_markdown_notebook_parity(name):
    markdown = (ROOT / "docs" / f"{name}.md").read_text()
    notebook = json.loads((ROOT / "docs" / f"{name}.ipynb").read_text())
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


@pytest.mark.parametrize("working_directory", [ROOT, ROOT / "docs"])
def test_association_tutorial_examples(working_directory, monkeypatch):
    pytest.importorskip("obspy")
    markdown = (ROOT / "docs" / "ASSOCIATION_TUTORIAL.md").read_text()
    examples = re.findall(r"(?m)^```python\n(.*?)^```", markdown, flags=re.S)
    monkeypatch.chdir(working_directory)
    namespace = {"__name__": "__main__"}
    for number, example in enumerate(examples, start=1):
        exec(compile(example, f"ASSOCIATION_TUTORIAL.md:block-{number}", "exec"),
             namespace)
