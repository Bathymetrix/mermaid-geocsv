"""Public imports and optional ObsPy dependency behavior."""

import inspect
from pathlib import Path
import subprocess
import sys
from textwrap import dedent

import pytest

from mermaid import geocsv


def test_fetch_public_api():
    assert geocsv.__version__ == "0.16.0"
    assert {"fetch", "GeoCSVFetchResult", "GeoCSVDownload", "GeoCSVFetchError"} <= set(geocsv.__all__)
    parameters = inspect.signature(geocsv.fetch).parameters
    assert parameters["instrument_ids"].default is None
    assert parameters["base_url"].default is inspect.Parameter.empty
    assert parameters["output_dir"].default == "."
    assert parameters["release"].default is None


def test_associate_public_signature():
    assert "associate" in geocsv.__all__
    assert str(inspect.signature(geocsv.associate)) == (
        "(waveforms, records, *, time_tolerance=0.0001, allow_merge=False)"
    )


@pytest.mark.parametrize("missing_module", ["obspy", "unrelated_dependency"])
def test_optional_obspy_imports(missing_module):
    # A fresh interpreter also exercises installations where ObsPy is absent.
    script = dedent('''
        import importlib.abc
        import sys

        missing_module = sys.argv[1]

        class BlockObsPy(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname == "obspy":
                    raise ModuleNotFoundError(
                        "Blocked dependency", name=missing_module)

        sys.meta_path.insert(0, BlockObsPy())
        from mermaid import geocsv

        assert "obspy" not in sys.modules
        assert "mermaid.geocsv._associate" not in sys.modules
        frame, = geocsv.read(sys.argv[2])
        assert len(frame) == 2
        assert frame.index.name == "source_record_index"
        assert str(frame["Latitude"].dtype) == "Float64"
        assert frame.attrs["geocsv"].source_path.is_absolute()
        try:
            geocsv.associate(None, [frame])
        except ImportError as exc:
            if missing_module == "obspy":
                assert "mermaid-geocsv[obspy]" in str(exc)
                assert isinstance(exc.__cause__, ModuleNotFoundError)
            else:
                assert isinstance(exc, ModuleNotFoundError)
                assert exc.name == missing_module
                assert "mermaid-geocsv[obspy]" not in str(exc)
        else:
            raise AssertionError("Expected an import error")
    ''')
    fixture = Path(__file__).parent / "fixtures" / "typed.geocsv"
    result = subprocess.run(
        [sys.executable, "-c", script, missing_module, str(fixture.resolve())],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
