"""The normative example is executable; historical generic examples are unsupported."""
from pathlib import Path
import re
import pytest
from mermaid import geocsv

ROOT = Path(__file__).parents[1]


def test_complete_specification_example_matches_fixture():
    example = re.findall(r'```csv\n(.*?)```', (ROOT / 'docs/format-spec.md').read_text(), re.S)[-1]
    assert example.encode() == (ROOT / 'tests/fixtures/schema-1.0.0/example.geocsv').read_bytes()
    frame, = geocsv.read(example.encode())
    assert len(frame) == 8
    assert frame.MethodIdentifier.str.split(':').str[:2].astype(str).nunique() == 5


REFERENCE_EXAMPLES = ROOT / 'docs/references/geocsv-v2.0.4-examples'


@pytest.mark.parametrize('path', [REFERENCE_EXAMPLES / name for name in (
    'unavco.geocsv', 'iris.geocsv', 'minimal_iris.geocsv', 'event.geocsv', 'r2r.geocsv',
)] + [ROOT / 'data/fixtures/P0006/P0006.geocsv'])
def test_historical_and_generic_payloads_are_explicitly_unsupported(path):
    with pytest.raises(geocsv.GeoCSVError, match='schema'):
        geocsv.read(path)
