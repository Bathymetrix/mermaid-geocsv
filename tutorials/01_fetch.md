# Fetch GeoCSV files

Fetch schema 1.0.0-rc1 fixture metadata through a temporary local collection.
The published testing collection still uses the old header and is not input
for this reader. This example exercises the same fetch/read APIs without
publishing new data. The fixture prefixes are not complete instrument histories.

Companions: [Markdown](01_fetch.md) · [Notebook](01_fetch.ipynb).

## Setup

Install the package from the cloned repository and activate its environment:

```bash
source .venv/bin/activate
python -m pip install .
```

The examples require mermaid-geocsv 0.29.0 or newer.
The cloned repository supplies local fixtures. Hosted examples require an
rc1 snapshot to be published separately; no upload is part of this tutorial.
See [installation and notebook setup](../docs/installation.md).

## 1. Download one instrument from latest

`base_url` selects the temporary local testing collection. `output_dir=None` downloads
into memory without saving a file:

```python
from mermaid import geocsv

from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from tempfile import TemporaryDirectory
import hashlib
import json
import shutil

repository = next(path for path in (Path.cwd(), Path.cwd().parent)
                  if (path / "data/fixtures/schema-1.0.0-rc1").is_dir())
fixtures = repository / "data/fixtures/schema-1.0.0-rc1/hosted"
workspace = TemporaryDirectory(prefix="mermaid-geocsv-tutorial-")
server_root = Path(workspace.name)
release = "2026-10-30T18:08:32.316000Z"
component = release.replace(":", "-")
directory = server_root / "releases" / component
directory.mkdir(parents=True)
entries = []
for instrument in ("P0006", "P0045"):
    filename = f"{instrument}.geocsv"
    content = (fixtures / filename).read_bytes()
    (directory / filename).write_bytes(content)
    entries.append(dict(instrument_id=instrument, filename=filename,
                        size_bytes=len(content), sha256=hashlib.sha256(content).hexdigest(),
                        provenance={"notes": "Local rc1 fixture projection; not a hosted snapshot"}))
(directory / "manifest.json").write_text(json.dumps(dict(
    release_id=release, testing_only=True, files=entries)))
(server_root / "latest.json").write_text(json.dumps(dict(
    release_id=release, testing_only=True,
    manifest=f"releases/{component}/manifest.json")))
server = ThreadingHTTPServer(("127.0.0.1", 0),
    partial(SimpleHTTPRequestHandler, directory=str(server_root)))
thread = Thread(target=server.serve_forever, daemon=True)
thread.start()
base_url = f"http://127.0.0.1:{server.server_port}/"
downloads = geocsv.fetch("P0006", base_url=base_url, output_dir=None)
records = geocsv.read(downloads)[0]
records.head()
```

Inspect the selected snapshot and its schema:

```python
release = downloads[0].provenance.release_id
print(release)
print(downloads[0].provenance.testing_only)  # True
print(records.attrs["geocsv"].schema_version)  # 1.0.0-rc1
```

Without `release`, fetch resolves the collection's latest pointer. Latest can change;
retain the returned literal release ID to reproduce this download.

## 2. Save every instrument and reuse identical local files

Omit instrument selection to download every instrument in the manifest.
Pin `release` to keep using the snapshot selected above. `output_dir` chooses
the parent directory:

```python
saved = geocsv.fetch(base_url=base_url, release=release,
                     output_dir="geocsv-downloads")
reused = geocsv.fetch(base_url=base_url, release=release,
                      output_dir="geocsv-downloads")
assert [item.path for item in saved] == [item.path for item in reused]
for item in saved:
    print(item.provenance.instrument_id, item.path)
```

Identical local files are verified and reused. Conflicting bytes raise rather
than being overwritten. The snapshot directory replaces only the timestamp's
two time-separator colons with hyphens: this fixture collection uses
`2026-10-30T18-08-32.316000Z`. Provenance retains the original colons and every
fractional digit. Pass saved results directly to `read` to retain download
provenance. `fetch(["P0006", "P0045"], ...)` selects instruments explicitly.

## 3. Download one instrument from the pinned snapshot

An explicit literal `release` bypasses latest and never falls back:

```python
pinned = geocsv.fetch("P0006", base_url=base_url, release=release, output_dir=None)
assert pinned[0].content == downloads[0].content
print(pinned[0].provenance.release_id)
```

For result fields and transport rules, see the [fetch reference](../docs/fetch.md).
Testing snapshots may be retired through separately authorized cleanup; pinning
identifies exact bytes but does not promise indefinite testing availability.

## Close the temporary collection

```python
server.shutdown()
server.server_close()
thread.join()
workspace.cleanup()
```
