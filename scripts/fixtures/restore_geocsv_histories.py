"""Restore ignored full GeoCSV histories from the read-only processed tree."""

import hashlib
import json
import os
from pathlib import Path
import shutil


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def restore():
    fixtures = Path(__file__).resolve().parents[2] / "data/fixtures/association"
    manifest = json.loads((fixtures / "manifest.json").read_text())
    source_root = Path(os.environ["MERMAID"]) / "processed"
    for item in manifest["geocsv"]:
        target = fixtures / item["path"]
        if target.exists():
            if digest(target) != item["sha256"]:
                raise ValueError(f"existing local history differs from manifest: {target}")
            continue
        source = source_root / item["source_path"]
        if digest(source) != item["sha256"]:
            raise ValueError(f"source history differs from the fixture snapshot: {source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    print("All complete GeoCSV histories are available and match the manifest.")


if __name__ == "__main__":
    restore()
