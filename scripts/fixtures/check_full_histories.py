"""Check tracked subset provenance and sampled matches against full histories.

Run from the repository root after restore_geocsv_histories.py. This optional
source-corpus check verifies frozen original bytes without parsing them, then
reads separate new-schema histories from the required source_root. It writes nothing.
"""

import argparse
import hashlib
import json
from pathlib import Path

from obspy import read

from mermaid import geocsv


def check(source_root):
    fixtures = Path(__file__).resolve().parents[2] / "data/fixtures/association"
    manifest = json.loads((fixtures / "manifest.json").read_text())
    checked = 0
    for item in manifest["geocsv"]:
        path = fixtures / item["path"]
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != item["sha256"]:
            raise ValueError(f"full history differs from manifest: {path}")
        subset = item["subset"]
        lines = raw.splitlines(keepends=True)
        header_count = subset["source_header_line_count"]
        if len(lines) - header_count != subset["source_record_count"]:
            raise ValueError(f"unexpected full-history record count: {path}")
        expected = b"".join(lines[:header_count] + [
            lines[header_count + index] for index in subset["source_record_indices"]])
        target = fixtures / subset["path"]
        if (target.read_bytes() != expected
                or hashlib.sha256(expected).hexdigest() != subset["sha256"]):
            raise ValueError(f"subset is not the recorded verbatim extraction: {target}")
        records = geocsv.read(Path(source_root) / item["path"])
        for frame in records:
            events = frame.loc[frame["MethodIdentifier"].str.startswith(
                "Derivation:Recording:", na=False)]
            if (events["DataQuality"].isna().any()
                    or not set(events["DataQuality"]) <= {"Q", "D"}):
                raise ValueError(f"unexpected full-history event quality: {path}")
        for example in manifest["examples"]:
            if example["geocsv"] != item["path"]:
                continue
            trace, = read(str(fixtures / example["mseed"]))
            geocsv.associate(trace, records, time_tolerance=0.001)
            # The migrated writer's finer timestamp ordering does not promise
            # historical source indices. The public strict match owns selection.
            if trace.stats.geocsv.association.type != "single_segment":
                raise ValueError(f"unexpected full-history match: {example['mseed']}")
            checked += 1
    print(f"Verified {len(manifest['geocsv'])} verbatim subsets and "
          f"{checked} unique full-history waveform associations.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=Path, help="isolated newly generated schema-1.0.0 histories")
    check(parser.parse_args().source_root)
