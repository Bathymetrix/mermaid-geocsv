# Fetch GeoCSV files

Download MERMAID GeoCSV schema 1.0.0 metadata from the public
[Bathymetrix testing collection](https://bathymetrix.com/geocsv/testing/).
The collection currently contains P0006 and P0045. These data remain testing
only. `fetch` verifies downloaded bytes against the snapshot manifest;
`read` parses them into pandas tables.

Companions: [Markdown](01_fetch.md) · [Notebook](01_fetch.ipynb).

## Setup

Install the package from the cloned repository and activate its environment:

```bash
source .venv/bin/activate
python -m pip install .
```

The examples require mermaid-geocsv 0.27.0 or newer and internet access.
Fetching needs no local data fixtures or repository-path setup. See
[installation and notebook setup](../docs/installation.md) if needed.

## 1. Download one instrument from latest

`base_url` selects the public testing collection. `output_dir=None` downloads
into memory without saving a file:

```python
from mermaid import geocsv

base_url = "https://bathymetrix.com/geocsv/testing/"
downloads = geocsv.fetch("P0006", base_url=base_url, output_dir=None)
records = geocsv.read(downloads)[0]
records.head()
```

Inspect the selected snapshot and its schema:

```python
release = downloads[0].provenance.release_id
print(release)
print(downloads[0].provenance.testing_only)  # True
print(records.attrs["geocsv"].schema_version)  # 1.0.0
```

Without `release`, fetch resolves the collection's latest pointer. On
2026-10-30 it selects `2026-10-30T18:08:32.316000Z`. Latest can change;
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
two time-separator colons with hyphens: the current snapshot uses
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
