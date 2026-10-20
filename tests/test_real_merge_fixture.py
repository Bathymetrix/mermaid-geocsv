"""Verify the real P0045 merge fixture and its recorded selection evidence."""

import hashlib
import json
from pathlib import Path


DIRECTORY = Path(__file__).parent / "fixtures/association/P0045_20220115"


def test_fixture_bytes_match_provenance():
    manifest = json.loads((DIRECTORY / "manifest.json").read_text())
    files = [manifest["geocsv"]]
    files += [item[extension] for item in manifest["selected"]
              for extension in ("mseed", "sac")]
    for item in files:
        path = DIRECTORY / item["path"]
        assert path.stat().st_size == item["size_bytes"]
        with path.open("rb") as source:
            assert hashlib.file_digest(source, "sha256").hexdigest() == item["sha256"]


def test_selected_span_is_longest_in_recorded_day_inventory():
    manifest = json.loads((DIRECTORY / "manifest.json").read_text())
    inventory = manifest["day_inventory"]
    assert len(inventory) == 9
    groups = {(item["id"], item["sample_rate"]) for item in inventory}
    spans = []
    for identity, rate in groups:
        ordered = sorted(
            (item for item in inventory
             if item["id"] == identity and item["sample_rate"] == rate),
            key=lambda item: item["starttime_ns"],
        )
        current = []
        end_ns = 0
        for item in ordered:
            if current and item["starttime_ns"] > end_ns + round(1e9 / rate):
                spans.append(current)
                current = []
            current.append(item)
            end_ns = max(member["endtime_ns"] for member in current)
        spans.append(current)
    longest = max(spans, key=lambda span: max(item["endtime_ns"] for item in span)
                  - span[0]["starttime_ns"])
    assert {item["source_path"] for item in longest} == {
        item["mseed"]["source_path"] for item in manifest["selected"]
    }
