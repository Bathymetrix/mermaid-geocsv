"""Initial 2026-10-13 collection from the read-only processed tree.

Creates the original paired-waveform/full-history snapshot only, not the later
GeoCSV subsets, expected association indices, or corpus audit. See README.md.
Refuses an existing fixture destination; never use it to refresh fixtures.
"""

import hashlib
import json
import os
from pathlib import Path
import random
import shutil

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = ROOT / "data" / "fixtures" / "association"
SEED = 20261013
PRODUCTS = ["WLT1", "WLT2", "WLT3", "WLT4", "WLT5", "RAW"]


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def collect():
    source = (Path(os.environ["MERMAID"]) / "processed").resolve()
    # Only create a new repository fixture directory; never write to the input.
    if DESTINATION.exists():
        raise FileExistsError(f"fixture destination already exists: {DESTINATION}")
    groups = {f"{stream}.{product}": []
              for stream in ("DET", "REQ") for product in PRODUCTS}
    for path in sorted(source.rglob("*.mseed")):
        group = ".".join(path.name.split(".")[-3:-1])
        if group in groups:
            groups[group].append(path)

    rng = random.Random(SEED)
    manifest = {"source_root": str(source), "seed": SEED,
                "population": {}, "examples": [], "geocsv": []}
    selected_floats = set()
    for group, paths in groups.items():
        paired = [path for path in paths if path.with_suffix(".sac").is_file()]
        selected = rng.sample(paired, min(3, len(paired)))
        manifest["population"][group] = {
            "mseed": len(paths), "paired": len(paired), "selected": len(selected)}
        for path in selected:
            relative = path.relative_to(source)
            selected_floats.add(relative.parts[0])
            files = {}
            for extension in ("mseed", "sac"):
                original = path.with_suffix(f".{extension}")
                target = DESTINATION / relative.with_suffix(f".{extension}")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original, target)
                files[extension] = str(target.relative_to(DESTINATION))
                files[f"{extension}_sha256"] = digest(original)
            manifest["examples"].append({**files, "group": group,
                "geocsv": f"{relative.parts[0]}/geo_DET_REQ.csv"})

    for float_directory in sorted(selected_floats):
        original = source / float_directory / "geo_DET_REQ.csv"
        target = DESTINATION / float_directory / original.name
        shutil.copyfile(original, target)
        manifest["geocsv"].append({
            "path": str(target.relative_to(DESTINATION)),
            "source_path": str(original.relative_to(source)),
            "sha256": digest(original)})
    (DESTINATION / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["population"], indent=2))


if __name__ == "__main__":
    collect()
