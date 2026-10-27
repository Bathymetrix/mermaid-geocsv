"""Check fresh full installations with the supplied Python interpreters.

Run from the repository's .venv, passing Python 3.11–3.14 executable names or
paths. Each interpreter checks both resolved dependencies and the declared
minimum pandas and ObsPy versions in separate temporary environments.
"""

from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]


def run(command, directory):
    print(f"Running: {' '.join(map(str, command))}", flush=True)
    subprocess.run(command, cwd=directory, check=True)


def check_installation(interpreter, requirements):
    with TemporaryDirectory(prefix="geocsv-install-") as temporary:
        directory = Path(temporary)
        run([interpreter, "-m", "venv", str(directory / "env")], directory)
        python = str(directory / "env/bin/python")
        # A fresh download has no stale setuptools build output. Copy only
        # packaging inputs, keeping the checkout and its existing build intact.
        source = directory / "source"
        source.mkdir()
        for name in ("pyproject.toml", "README.md", "LICENSE"):
            shutil.copy2(ROOT / name, source / name)
        shutil.copytree(ROOT / "src", source / "src",
                        ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
        # Exercise the documented full install before adding test dependencies.
        run([python, "-m", "pip", "install", f"{source}[obspy]", *requirements], directory)
        run([python, "-m", "pip", "check"], directory)
        run([python, "--version"], directory)
        run([python, "-m", "pip", "list", "--format=freeze"], directory)
        run([python, "-I", str(ROOT / "scripts/check_wheel.py"),
             str(ROOT / "data/fixtures/association")], directory)
        run([python, "-m", "pip", "install", "pytest>=8"], directory)
        # Disable the checkout's src path so the full suite tests the installed
        # distribution, rather than silently importing the working tree.
        run([python, "-X", "faulthandler", "-I", "-m", "pytest", "-q", "-o", "pythonpath=",
             str(ROOT / "tests")], directory)


def main():
    interpreters = sys.argv[1:] or [f"python3.{minor}" for minor in range(11, 15)]
    results = []
    for interpreter in interpreters:
        version = subprocess.check_output(
            [interpreter, "-c", "import sys; print('.'.join(map(str, sys.version_info[:2])))"],
            text=True).strip()
        cases = [
            ("resolved dependencies", []),
            ("minimum pandas and ObsPy", ["pandas==2.3.3", "obspy==1.5.1"]),
        ]
        for label, requirements in cases:
            name = f"Python {version} / {label}"
            print(f"\nChecking {name} ({interpreter})", flush=True)
            try:
                check_installation(interpreter, requirements)
            except subprocess.CalledProcessError as error:
                print(f"FAIL: {name}: {error}", flush=True)
                results.append((name, False))
            else:
                results.append((name, True))

    print("\nInstallation results:", flush=True)
    for name, passed in results:
        print(f"{'PASS' if passed else 'FAIL'}: {name}", flush=True)
    return 0 if all(passed for _, passed in results) else 1


if __name__ == "__main__":
    sys.exit(main())
