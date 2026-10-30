"""Smoke-test an installed wheel using tracked fixtures, outside the checkout.

Run with the wheel environment's Python in isolated mode (-I), passing the
absolute path to data/fixtures/association. CI builds and installs the wheel
in a fresh environment before running this script on each supported Python
minor version.
"""

from importlib.metadata import distribution
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from mermaid import geocsv


def main():
    fixtures = Path(sys.argv[1]).resolve()
    repository = fixtures.parents[2]
    package = distribution("mermaid-geocsv")
    installed_directory = Path(package.locate_file("mermaid/geocsv")).resolve()
    imported_path = Path(geocsv.__file__).resolve()
    assert installed_directory.is_relative_to(Path(sys.prefix).resolve()), (
        "the distribution must be installed in the wheel test environment")
    assert imported_path == installed_directory / "__init__.py", (
        f"expected the installed wheel, imported {imported_path}")
    assert not Path.cwd().resolve().is_relative_to(repository), (
        "run the smoke check outside the repository")
    assert geocsv.__version__ == package.version
    assert not hasattr(geocsv, "write_sac")
    assert not (installed_directory / "_write_sac.py").exists()
    assert "obspy" not in sys.modules, "ObsPy must remain a lazy dependency"

    import numpy as np
    from obspy import read

    manifest = json.loads((fixtures / "manifest.json").read_text())
    example = manifest["examples"][0]
    history = next(item for item in manifest["geocsv"]
                   if item["path"] == example["geocsv"])
    tables = geocsv.read(fixtures.parent / "schema-1.0.0/association" / history["subset"]["path"])
    frame, = tables
    assert frame.index.name == "source_record_index"
    assert str(frame["SampleCount"].dtype) == "Int64"
    assert frame.attrs["geocsv"].source_path.is_absolute()

    waveform, = read(str(fixtures / example["mseed"]))
    geocsv.associate(waveform, tables, create_sac_header=True)
    source = waveform.stats.geocsv
    assert source.source_record_index == example["subset_record_index"]
    assert source.association.type == "single_segment"

    with TemporaryDirectory(prefix="geocsv-wheel-sac-") as temporary:
        output = Path(temporary) / "associated.sac"
        waveform.write(str(output), format="SAC")
        exported, = read(str(output), round_sampling_interval=False)
        assert exported.id == waveform.id
        assert exported.stats.npts == waveform.stats.npts
        assert abs(exported.stats.starttime.ns - waveform.stats.starttime.ns) <= 1000
        assert exported.stats.sac.delta == np.float32(waveform.stats.delta)
        assert exported.stats.sac.stla == np.float32(source.Latitude)
        assert exported.stats.sac.stlo == np.float32(source.Longitude)
        assert exported.stats.sac.stel == np.float32(source.Elevation)
        assert exported.stats.sac.stdp == np.float32(source.WaterPressure / 100)
        np.testing.assert_array_equal(exported.data, waveform.data.astype(np.float32))

    print(f"Wheel {package.version}: read/associate/create_sac_header/Trace.write passed ({imported_path})")


if __name__ == "__main__":
    main()
