# Fetch GeoCSV files

`geocsv.fetch` verifies exact bytes against a snapshot manifest and returns a
list of results. `geocsv.read` parses schema 1.0.0 results into pandas tables.
These examples use a temporary local testing collection. Public testing latest
now serves the compatible schema 1.0.0 P0006/P0045 snapshot
`2026-10-30T18:08:32.316000Z`; these examples retain local fixtures for reproducibility.
No download example here publishes data or changes a pointer outside its temporary server.

Companions: [Markdown](01_fetch.md) · [Notebook](01_fetch.ipynb).

## Setup

Install the local package from the cloned repository:

```bash
.venv/bin/python -m pip install .
```

The examples require mermaid-geocsv 0.27.0 or newer and run offline from the
repository root, `docs/`, or `tutorials/`. First create a local HTTP collection
from the documented [schema fixtures](../data/fixtures/schema-1.0.0/README.md):

```python
from pathlib import Path
from mermaid import geocsv

root = Path.cwd()
if root.name in {"docs", "tutorials"}:
    root = root.parent

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from tempfile import TemporaryDirectory
from threading import Thread
import hashlib
import json

collection_directory = TemporaryDirectory()
server_root = Path(collection_directory.name)
release = "2026-10-29T00:00:00.000000Z"
component = release.replace(":", "-")
release_directory = server_root / "releases" / component
release_directory.mkdir(parents=True)
entries = []
for instrument in ["P0006", "P0045"]:
    name = f"{instrument}.geocsv"
    content = (root / "data/fixtures/schema-1.0.0" / instrument / name).read_bytes()
    (release_directory / name).write_bytes(content)
    entries.append({"instrument_id": instrument, "filename": name,
                    "size_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(),
                    "provenance": {"notes": "Local schema fixture; see its provenance manifest"}})
manifest = {"release_id": release, "testing_only": True, "files": entries}
(release_directory / "manifest.json").write_text(json.dumps(manifest))
(server_root / "latest.json").write_text(json.dumps({
    "release_id": release, "testing_only": True,
    "manifest": f"releases/{component}/manifest.json"}))
handler = partial(SimpleHTTPRequestHandler, directory=str(server_root))
server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
server_thread = Thread(target=server.serve_forever, daemon=True)
server_thread.start()
base_url = f"http://127.0.0.1:{server.server_port}/"
```

## 1. Fetch one instrument into memory

`base_url` selects the collection. `output_dir=None` retains bytes in memory:

```python
downloads = geocsv.fetch("P0006", base_url=base_url, output_dir=None)
records = geocsv.read(downloads)[0]
records.head()
print(downloads[0].provenance.release_id)
print(downloads[0].provenance.testing_only)  # True
```

The literal release identity is retained, together with the manifest, size,
checksum and retrieval URL. Parsed metadata also retains schema and creation identity.

## 2. Save every instrument and reuse identical local files

Omit instrument selection to fetch the complete snapshot. `output_dir` chooses
the parent directory. Repeating the call verifies and reuses identical bytes:

```python
saved = geocsv.fetch(base_url=base_url, output_dir="geocsv-downloads")
reused = geocsv.fetch(base_url=base_url, output_dir="geocsv-downloads")
assert [item.path for item in saved] == [item.path for item in reused]
for item in saved:
    print(item.provenance.instrument_id, item.path)
```

The directory uses `2026-10-29T00-00-00.000000Z`; only the two timestamp
time-separator colons change. Provenance keeps the original colons and every
fractional digit. Conflicting local bytes raise. `fetch(["P0006", "P0045"], ...)`
selects several instruments explicitly. Pass saved results directly to `read`
to preserve download provenance.

## 3. Pin an immutable snapshot

An explicit literal `release` bypasses latest and never falls back:

```python
pinned = geocsv.fetch("P0006", base_url=base_url, release=release, output_dir=None)
assert pinned[0].content == downloads[0].content
print(pinned[0].provenance.release_id)
```

Stop the temporary server when finished:

```python
server.shutdown()
server.server_close()
server_thread.join()
collection_directory.cleanup()
```

For result fields and transport rules, see the [fetch reference](../docs/fetch.md).
Schema compatibility is a separate reader requirement; fetch can retrieve
historical exact bytes without making them parseable by the new reader.
