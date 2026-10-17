"""Check tracked subset provenance and sampled matches against full histories.

Run from the repository root after restore_geocsv_histories.py. This optional
source-corpus check reads local copies only and writes nothing.
"""

import hashlib
import json
from pathlib import Path

from obspy import read

from associate import associate
from mermaid import geocsv


def check():
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
        records = geocsv.read(path)
        for frame in records:
            events = frame.loc[frame["MethodIdentifier"].str.startswith(
                "Algorithm(event):", na=False)]
            if (events["DataQuality"].isna().any()
                    or not set(events["DataQuality"]) <= {"Q", "D"}):
                raise ValueError(f"unexpected full-history event quality: {path}")
        for example in manifest["examples"]:
            if example["geocsv"] != item["path"]:
                continue
            trace, = read(str(fixtures / example["mseed"]))
            associate(trace, records, time_tolerance=0.001)
            if (trace.stats.geocsv.dataset_index != 0
                    or trace.stats.geocsv.source_record_index
                    != example["original_source_record_index"]):
                raise ValueError(f"unexpected full-history match: {example['mseed']}")
            checked += 1
    print(f"Verified {len(manifest['geocsv'])} verbatim subsets and "
          f"{checked} unique full-history waveform associations.")


if __name__ == "__main__":
    check()
