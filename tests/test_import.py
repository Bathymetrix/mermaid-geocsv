"""Package-surface tests."""

from mermaid import geocsv


def test_import_exposes_package_version() -> None:
    assert geocsv.__version__ == "0.1.0"
