# Local fetch collection and protocol reference

Supporting reference for development and detailed investigation. The [short
tutorial](../tutorials/FETCH.md) and [notebook](../tutorials/FETCH.ipynb)
provide the introductory workflow.

The extended examples below preserve the scientific explanations, diagnostic
checks, and fixture coverage from the longer walkthrough. Run their Python
blocks in order from the repository root, `docs/`, or `docs/development/`,
using the [installation guide](../INSTALLATION.md). These reference pages are
independent of the tutorial notebook pairs.

## 1. Start a temporary local test collection

Production hosting is inactive; the public testing collection is available. This standalone example serves tracked
P0006 and P0045 fixtures over loopback HTTP using only the standard library.
It creates an illustrative `test-001` release in a temporary directory; this is not a
published scientific release. The context manager stops the server and removes
the temporary files even if a download fails.

```python
from contextlib import contextmanager
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.parse import quote

from mermaid import geocsv

repository_root = Path.cwd()
if repository_root.name in {"tutorials", "development"}:
    repository_root = repository_root.parent.parent
elif repository_root.name == "docs":
    repository_root = repository_root.parent
fixture_path = repository_root / "data/fixtures/P0006/P0006.geocsv"


@contextmanager
def local_collection(release_id="test-001"):
    with TemporaryDirectory(prefix="geocsv-tutorial-") as temporary:
        directory = Path(temporary)
        server_root = directory / "server"
        release_directory = server_root / "releases" / release_id
        release_directory.mkdir(parents=True)
        entries = []
        for instrument in ("P0006", "P0045"):
            source = fixture_path.parent.parent / instrument / f"{instrument}.geocsv"
            content = source.read_bytes()
            (release_directory / source.name).write_bytes(content)
            entries.append({
                "instrument_id": instrument, "filename": source.name,
                "size_bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
                "provenance": {"notes": "Unmodified tracked test fixture"},
            })
        manifest = {
            "release_id": release_id, "testing_only": True,
            "files": entries,
        }
        (release_directory / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8",
        )
        (server_root / "latest.json").write_text(json.dumps({
            "release_id": release_id, "testing_only": True,
            "manifest": f"releases/{quote(release_id, safe='')}/manifest.json",
        }), encoding="utf-8")
        handler = partial(SimpleHTTPRequestHandler, directory=str(server_root))
        with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                yield f"http://127.0.0.1:{server.server_port}/", directory / "downloads"
            finally:
                server.shutdown()
                thread.join()
```

## 2. Fetch one file into memory

Start with one instrument and no persistent download files. `base_url` is
required; `output_dir=None` keeps the verified bytes in memory.

```python
with local_collection() as (collection_url, output_directory):
    downloads = geocsv.fetch("P0006", base_url=collection_url, output_dir=None)

# The temporary server is stopped; the memory result remains usable.
assert downloads[0].content == fixture_path.read_bytes()
tables = geocsv.read(downloads)
assert tables[0].attrs["geocsv"].download.testing_only is True
```

## 3. Select a list or discover the entire release

A list selects instruments in the requested order. Omitting the selection
fetches every instrument in manifest order. Select the two real floats in the
reverse order to make the difference visible, then select only P0045:

```python
with local_collection() as (collection_url, output_directory):
    selected = geocsv.fetch(["P0045", "P0006"], base_url=collection_url,
                            output_dir=None)
    discovered = geocsv.fetch(base_url=collection_url, output_dir=None)
    only_p0045 = geocsv.fetch("P0045", base_url=collection_url, output_dir=None)
assert [item.provenance.instrument_id for item in selected] == ["P0045", "P0006"]
assert [item.provenance.instrument_id for item in discovered] == ["P0006", "P0045"]
assert len(only_p0045) == 1
selected_tables = geocsv.read(selected)
assert selected_tables[0]["Station"].eq("P0045").all()
assert selected_tables[1]["Station"].eq("P0006").all()
assert selected_tables[0].attrs["geocsv"].download is selected[0].provenance
assert selected_tables[1].attrs["geocsv"].download is selected[1].provenance
```

## 4. Save verified files to disk and reuse them

Omitting `output_dir` saves beneath the current directory. Here an explicit
temporary directory keeps the exercise self-contained:

```python
with local_collection() as (collection_url, output_directory):
    saved = geocsv.fetch("P0006", base_url=collection_url,
                         output_dir=output_directory)
    saved_tables = geocsv.read(saved)
    print(saved[0].path)
    assert saved[0].path.is_file()
    reused = geocsv.fetch("P0006", base_url=collection_url,
                          output_dir=output_directory)
    assert reused == saved
```

The temporary disk files have now been removed. For research downloads, use a
persistent directory of your choice instead of this temporary collection.

## 5. Pin a release instead of consulting latest.json

```python
with local_collection() as (collection_url, output_directory):
    pinned = geocsv.fetch("P0006", base_url=collection_url,
                          release="test-001", output_dir=None)
assert pinned[0].content == downloads[0].content
help(geocsv.fetch)
```

Scientific snapshot IDs retain the exact upstream UTC `#created` timestamp.
Pass the literal timestamp to `release`; URLs and local directory names encode
its colons as `%3A`. Fractional digits are preserved without rounding or padding.
This local demonstration uses the same fixture bytes under a timestamp ID;
it does not implement the publisher's snapshot-wide `#created` validation:

```python
release_id = "2026-10-21T22:48:33.277Z"
with local_collection(release_id) as (collection_url, output_directory):
    timestamp_saved = geocsv.fetch("P0006", base_url=collection_url,
                                   release=release_id, output_dir=output_directory)
    timestamp_latest = geocsv.fetch("P0006", base_url=collection_url,
                                    output_dir=None)
    assert timestamp_saved[0].path.parent.name == "2026-10-21T22%3A48%3A33.277Z"
    assert timestamp_saved[0].provenance.release_id == release_id
    assert timestamp_latest[0].provenance.release_id == release_id
    assert timestamp_latest[0].content == timestamp_saved[0].path.read_bytes()
```

## The fetch interface

The full signature is
`fetch(instrument_ids=None, *, base_url, output_dir=".", release=None, timeout=30)`.
For an actual collection, supply its publisher-provided URL as `base_url`.
The local fixture provenance is documented in the
[fixture notes](../../data/fixtures/P0006/README.md).

`base_url` explicitly selects a collection. It must be an
HTTP(S) collection URL without query parameters or a fragment; a trailing slash
is optional. Use HTTPS for public hosting. The example above uses a temporary
local test endpoint, not a published scientific data release. It needs neither the website
checkout nor an internet connection.

Omit `instrument_ids` or pass None to discover every file from the manifest,
in manifest order. A string selects one float; a sequence selects floats in
the requested order. Identifiers are exact and case-sensitive. Empty selections,
duplicate identifiers, and non-string identifiers raise. A missing float is an
error before downloading any files or creating output directories. Files are
never discovered by probing numbers or scraping a directory page.

`fetch` always returns a list of immutable `GeoCSVFetchResult` values, including
for one file. Each has `provenance` and exactly one of:

| Storage | Result field | Behavior |
| --- | --- | --- |
| `output_dir="."` (default) | `path` | Absolute path under the current working directory's `<release_component>/` |
| Explicit output directory | `path` | Absolute path under `<output_dir>/<release_component>/`; missing directories are created |
| `output_dir=None` | `content` | Verified GeoCSV bytes retained in memory; no files or directories written |

Disk output includes the exact release `manifest.json` alongside the selected
files. Its inventory describes the complete release, even when only selected
files were downloaded. Existing files are checked before reuse; a different
file or manifest raises `FileExistsError` without overwriting it. Separate
releases use separate directories. Use different output directories for
different collections, particularly if they use the same release ID. There is
no implicit persistent cache, offline release discovery, or automatic lookup
of saved files outside the requested directory. Each operation still retrieves
the selected manifest and, when applicable, latest.

## Parsing and memory

```python
tables = geocsv.read(downloads)     # Flat list of dataset tables.
tables = geocsv.read(downloads[0])  # Datasets from one downloaded file.
```

`read` accepts one result or its list/tuple, local paths, and raw UTF-8 bytes.
It returns one DataFrame per dataset in result/dataset order. Files are not
concatenated, and their schemas need not match. Each file starts its own
zero-based `source_record_index`; indices continue across datasets within
that file. `datetime_timezone` works identically for every source type.

Saved results are reverified before parsing so a changed local file cannot
silently inherit the earlier checksum provenance. Reading a bare saved path
records its local path but does not automatically discover nearby manifests.
Reading bare bytes records no local path or download provenance.

Memory-only retrieval retains all selected raw file bytes. The historical full source
collection was approximately 569 MB; the hosted two-float testing collection
is smaller. Actual transfer sizes come from the selected manifest. Parsed pandas tables and parser
working storage can require substantially more memory. Retaining `downloads`
while parsing also retains the raw payloads. Parsed metadata retains only
retrieval provenance, so `del downloads` can release the downloaded bytes once
they are no longer needed. Disk downloads stream through temporary files with
bounded transfer buffers. Downloads are sequential; there is no batch size cap.

## Provenance

```python
import json

metadata = tables[0].attrs["geocsv"]
metadata.source_path          # Absolute Path for disk input; None for memory.
download = metadata.download
download.instrument_id
download.release_id
download.url
download.manifest_url
download.size_bytes
download.sha256
download.testing_only
manifest = json.loads(download.manifest)
```

`metadata.download` is an immutable `GeoCSVDownload` when the source is a fetch
result, otherwise None. `manifest` contains the exact UTF-8 JSON response bytes,
including the complete release inventory and publisher-provided source
provenance. Requested file and manifest URLs are retained; they do not describe
any HTTP redirect chain. Byte count and SHA-256 refer to the uncompressed
GeoCSV file bytes. Checksums verify integrity against the supplied manifest;
they do not independently establish publisher authenticity.

GeoCSV declarations, units, comments, and timestamp notation remain in the
existing metadata fields. Download metadata retains no GeoCSV payload bytes.
Metadata is guaranteed on freshly parsed frames. Persistence through arbitrary
pandas transformations, concatenation, or exports is not guaranteed; keep the
metadata or retrieval result separately when needed. Association retains this
same immutable provenance for the uniquely matched dataset.

## Release protocol and failures

The publication and download contract is recorded at
`mermaid-publisher/docs/geocsv/CONTRACT.md`. The timestamp contract is
summarized in the [hosting plan](../HOSTING.md#release-path-contract).
`mermaid-publisher` owns snapshot creation, full-archive validation, evidence,
gating and publication. `bathymetrix-site` owns its read-only hosting. The
publisher uses this package's public scientific APIs; this package owns those
APIs and the fetch client. Publisher and consumer versions evolve independently;
shared contract changes require explicit compatibility review. The URL layout is:

```text
latest.json
releases/<release_component>/manifest.json
releases/<release_component>/<filename>
```

For latest selection, fetch `latest.json` once, read its `release_id`,
`testing_only`, and `manifest`, and require that manifest path to be
`releases/<release_component>/manifest.json`. Fetch that manifest once and require its
release ID and test flag to agree. Every requested file comes from that one
inventory, so latest cannot change the selected release between files.
An explicit `release` requests its manifest directly and never consults latest
or falls back when unavailable. Published releases are assumed immutable.

The manifest contains `release_id`, boolean `testing_only`, and `files`.
The website also supplies descriptive `created_utc` and `description` fields;
these are retained without interpreting them as observation coverage or
publication evidence. Each file entry requires a nonempty string
`instrument_id`, `filename`, nonnegative integer `size_bytes`, lowercase
64-digit hexadecimal `sha256`, and a `provenance` object. Instrument IDs and
filenames must be unique. Release IDs accept either a plain ASCII token or a
valid UTC timestamp `YYYY-MM-DDTHH:MM:SS[.digits]Z`; timestamps use valid calendar
dates, hours 00–23 and seconds 00–59. Literal IDs are retained in manifests and
provenance. URL/local `release_component` is `quote(release_id, safe="")`:
colons become uppercase `%3A`, and fractional digits retain their exact spelling.
Do not supply a pre-encoded ID, normalize equivalent timestamps, or decode local
directory names before opening them. Plain tokens and filenames start with an
ASCII letter or digit and contain only ASCII letters, digits, dots, underscores,
and hyphens; `.` and `..` are excluded. A filename
cannot be `manifest.json`. This prevents remote declarations from escaping the
selected local release directory. Source provenance paths are descriptive;
the downloader does not open them. Unknown manifest fields are retained in the
original JSON bytes.

Every downloaded file must match both its declared byte count and SHA-256
before acceptance. Compression is outside the current protocol. Network,
manifest, missing-instrument, and integrity failures raise `GeoCSVFetchError`.
Errors identify the relevant URL or instrument. Invalid arguments raise
`ValueError` or `TypeError`; local output conflicts raise `FileExistsError`.
`timeout=30` is a positive finite socket timeout in seconds, not a total batch
deadline. There are no automatic retries.

A failure stops the batch and returns no partial result list. Earlier verified
disk downloads and the manifest remain available; temporary failed downloads
are removed. A subsequent operation can verify and reuse those files. Memory
results are returned only if the entire batch succeeds. Invalid GeoCSV syntax
is detected separately by `read` and raises `GeoCSVError`, with the source path
or download URL in its message.

## Verification

`tests/test_fetch.py` serves package-local fixtures through an ephemeral
loopback HTTP server. It verifies real P0006 bytes and parsed tables, complete
release discovery, selection order, pinned releases, disk reuse, integrity and
batch failures, provenance, and in-memory association. The fixture provenance
and fixed checksum are recorded in `data/fixtures/P0006/README.md`.

ObsPy source conventions were inspected at checkout commit
`50033e1daf95233cd4f30e95a49c37fd50be2ccd`, including the generic reader and
download helper, nearby utility tests, contribution instructions, and coding
style. That read-only reference is distinct from the repository environment's
installed ObsPy 1.5.1. Fetching adds no ObsPy dependency or scientific matching
policy; association diagnostics now identify memory-fetched sources by URL.

## Fixture coverage

These examples exercise memory retrieval, disk retrieval and reuse, release
pinning, literal timestamp IDs with encoded paths, and download provenance using
real P0006 and P0045 GeoCSV payloads
served as a temporary test release. Assertions distinguish explicit reverse
selection order, manifest discovery order, and a one-instrument selection,
then verify the station and provenance of each parsed table. No public
production endpoint is exercised here.
