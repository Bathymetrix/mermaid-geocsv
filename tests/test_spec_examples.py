"""The canonical format example is executable."""
from pathlib import Path
import re

from mermaid import geocsv


ROOT = Path(__file__).parents[1]


def test_complete_specification_example_matches_fixture():
    example = re.findall(r'```csv\n(.*?)```', (ROOT / 'docs/format-spec.md').read_text(), re.S)[-1]
    assert example.encode() == (ROOT / 'tests/fixtures/schema-1.0.0-rc2/example.geocsv').read_bytes()
    frame, = geocsv.read(example.encode())
    assert set(frame['type']) == {'gps', 'pressure', 'downcrossing', 'upcrossing', 'waveform'}
