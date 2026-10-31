# Fetching GeoCSV collections

The [fetch tutorial](../tutorials/01_fetch.md) demonstrates memory retrieval,
disk downloads, and release pinning. This reference defines client behavior;
the publisher owns the [publication/download contract](../../mermaid-publisher/docs/geocsv/contract.md).
Hosted collections are currently testing only; see [hosting](hosting.md).

## The fetch interface

`fetch(instrument_ids=None, *, base_url, output_dir=".", release=None, timeout=30)`
returns a list of immutable `GeoCSVFetchResult` values, including for one file.
It retrieves and verifies bytes; `read` separately validates GeoCSV syntax.

`base_url` must explicitly select an HTTP(S) collection, without a query or
fragment. A trailing slash is optional. Use HTTPS for public hosting.
Omitting `instrument_ids` selects all files in manifest order; a string selects
one instrument, and a sequence selects instruments in caller order. Selection
is exact and case-sensitive. Empty selections, duplicates, non-string IDs,
and unknown instruments raise before downloading payloads. Discovery uses the
manifest, without probing instrument numbers or scraping directory pages.

| Storage choice | Result | Location |
| --- | --- | --- |
| `output_dir="."` (default) | Absolute `path`; `content=None` | `<working directory>/<release_component>/<filename>` |
| Explicit output directory | Absolute `path`; `content=None` | `<output_dir>/<release_component>/<filename>` |
| `output_dir=None` | Verified `content` bytes; `path=None` | Memory only; no files created |

Disk output also retains the exact release `manifest.json`, whose inventory
describes the complete release even for a partial selection. Existing files
and manifests must match before reuse; differing bytes raise `FileExistsError`
without overwriting. Use separate output roots for different collections,
especially when their release IDs overlap. Every call still retrieves the
manifest and, when needed, latest; there is no offline discovery or implicit
persistent cache.

## Release selection and validation

The collection layout is:

```text
latest.json
releases/<release_component>/manifest.json
releases/<release_component>/<filename>
```

Latest selection retrieves `latest.json` once and requires its manifest path
to match the selected release. The manifest's release ID and boolean
`testing_only` must agree with latest. An explicit `release` bypasses latest
and never falls back if unavailable. All selected files come from that one
manifest; published release bytes are assumed immutable.

Release IDs accept plain ASCII tokens or valid UTC timestamps
`YYYY-MM-DDTHH:MM:SS[.digits]Z`. Pass the literal ID, without pre-encoding or
normalizing fractional digits. URL and local directory
components replace only the creation timestamp's time-separator colons with
hyphens: `release_id.replace(":", "-")`. For example,
`2026-10-21T22:48:33.277Z` uses `2026-10-21T22-48-33.277Z`. Every fractional
digit is retained. Plain test-token IDs are unchanged. GeoCSV contents,
`#created`, manifest/provenance release IDs and other timestamps retain their
original spelling. Pass the literal creation timestamp as `release`, rather
than its directory spelling.

Encoded release-path aliases and automatic fallback are unsupported. Each call
uses the hyphenated directory spelling and retains the exact manifest. Existing
downloads are never renamed implicitly.

The manifest contains `release_id`, `testing_only`, and `files`. Each entry
requires a nonempty string `instrument_id`, a `filename`, a nonnegative
integer `size_bytes`, a lowercase 64-digit hexadecimal `sha256`, and a
`provenance` object. Instrument IDs and filenames must be unique. Plain-token
release IDs and filenames start with an ASCII letter or digit and contain
only ASCII letters, digits, dots, underscores, and hyphens; `.` and `..` are
excluded, and a payload cannot be named `manifest.json`. Source provenance
paths are descriptive and are never opened by the downloader. Unknown fields
remain available in the original manifest bytes.

Every payload must match its declared size and SHA-256 before acceptance.
Checksums establish integrity against the manifest, not publisher authenticity.
Compression is outside this protocol.

## Provenance

Each result's immutable `GeoCSVDownload` provenance records instrument and
release IDs, requested file and manifest URLs, verified size and SHA-256,
`testing_only`, and the exact UTF-8 manifest bytes. URLs describe the requests,
not any redirect chain. Provenance contains no GeoCSV payload bytes.

Pass fetch results directly to `read` to retain this provenance as
`frame.attrs["geocsv"].download`. Saved results are reverified before parsing.
Reading a bare path records its resolved local path but does not discover an
adjacent manifest; bare bytes have neither path nor download provenance.
The [reader specification](reader-spec.md) defines table order, record indices,
and the lifetime of parsed metadata.

Memory retrieval retains every selected raw payload, and parsing needs
additional working memory and pandas storage. Release sizes come from the
manifest. Delete unneeded result objects to release their payload bytes;
parsed metadata retains provenance only. Disk transfers use temporary files
and bounded transfer buffers. Files are downloaded sequentially.

## Failures

Network, manifest, missing-instrument, and integrity failures raise
`GeoCSVFetchError`. Invalid arguments raise `TypeError` or `ValueError`;
local output conflicts raise `FileExistsError`, and other filesystem failures
can raise `OSError`. `timeout` is a positive finite socket timeout in seconds,
not a whole-batch deadline. There are no automatic retries.

A failure returns no partial result list. Earlier verified disk downloads and
the manifest remain; failed temporary downloads are removed. A later call can
verify and reuse the successful files. Memory results are returned only after
the whole batch succeeds. Parsing failures belong to `read` and raise
`GeoCSVError` with the source path or download URL.

`tests/test_fetch.py` covers selection, pinning, reuse, integrity, failure
behavior, and provenance using tracked fixtures over loopback HTTP. Ordinary
tests do not require public hosting.

## Payload compatibility

The reader requires MERMAID schema 1.0.0. Testing latest serves the
compatible P0006/P0045 snapshot `2026-10-30T18:08:32.316000Z`. Other retained schemas can be downloaded as exact bytes, but cannot be parsed
by this reader.
The [fetch tutorial](../tutorials/01_fetch.md) downloads directly from the public
testing collection. Ordinary tests replay published prefixes over loopback HTTP.
Transport continues to preserve token IDs, exact bytes, literal release IDs and
all fractional digits. No encoded aliases or automatic fallback are supported.
