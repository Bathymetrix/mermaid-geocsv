# Fetch GeoCSV releases

Version 0.16.0 adds verified retrieval into local files or memory. Fetching
preserves the released GeoCSV bytes and does not parse or alter scientific
metadata. Parsing remains the separate `read` operation.

## Selection and storage

```python
from mermaid import geocsv

# Website test collection when its repository is being served locally.
collection_url = "http://localhost:8000/data/geocsv/testing/"

# One float; save beneath ./<release_id>/.
downloads = geocsv.fetch("P0006", base_url=collection_url)

# A selection; save beneath ./data/<release_id>/.
downloads = geocsv.fetch(["P0006"], base_url=collection_url, output_dir="data")

# Every float in the release; no persistent files.
downloads = geocsv.fetch(base_url=collection_url, output_dir=None)
tables = geocsv.read(downloads)

# Pin a release instead of following latest.
downloads = geocsv.fetch(
    base_url=collection_url, release="test-001", output_dir=None,
)
```

The full signature is:

```python
fetch(instrument_ids=None, *, base_url, output_dir=".", release=None, timeout=30)
```

Production hosting is undecided, so `base_url` is required. It must be an
HTTP(S) collection URL without query parameters or a fragment; a trailing slash
is optional. Use HTTPS for public hosting. The URL above is a local test
endpoint, not a published scientific data release. To preview it, run
`python3 -m http.server 8000 --bind 127.0.0.1` from the website repository.
Routine package tests need neither that checkout nor an internet connection.

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
| `output_dir="."` (default) | `path` | Absolute path under the current working directory's `<release_id>/` |
| Explicit output directory | `path` | Absolute path under `<output_dir>/<release_id>/`; missing directories are created |
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

Memory-only retrieval retains all selected raw file bytes. The current full
collection is approximately 569M according to the author's inventory; actual
transfer sizes come from the selected manifest. Parsed pandas tables and parser
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

The initial protocol follows the website's shared download agreement at
`bathymetrix-site/data/geocsv/testing/CONTRACT.md`. The website chat owns hosting,
publication, URLs, and manifests; the package chat owns this client. Changes to
the protocol require coordination. The collection layout is:

```text
latest.json
releases/<release_id>/manifest.json
releases/<release_id>/<filename>
```

For latest selection, fetch `latest.json` once, read its `release_id`,
`testing_only`, and `manifest`, and require that manifest path to be
`releases/<release_id>/manifest.json`. Fetch that manifest once and require its
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
filenames must be unique. Release IDs and filenames must be plain components
starting with an ASCII letter or digit and containing only ASCII letters,
digits, dots, underscores, and hyphens; `.` and `..` are excluded. A filename
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
and fixed checksum are recorded in `tests/fixtures/geocsv/README.md`.

ObsPy source conventions were inspected at checkout commit
`50033e1daf95233cd4f30e95a49c37fd50be2ccd`, including the generic reader and
download helper, nearby utility tests, contribution instructions, and coding
style. That read-only reference is distinct from the repository environment's
installed ObsPy 1.5.1. Fetching adds no ObsPy dependency or scientific matching
policy; association diagnostics now identify memory-fetched sources by URL.
