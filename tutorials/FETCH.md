# Fetch GeoCSV files

Download GeoCSV metadata from the [Bathymetrix test collection](https://bathymetrix.com/geocsv/).
`geocsv.fetch` checks each file's size and checksum and returns a list of results.
Use `geocsv.read` to turn those results into pandas tables.

Companions: [Markdown](FETCH.md) · [Notebook](FETCH.ipynb).

## Setup

From the cloned repository, activate your environment and install the package:

```bash
source .venv/bin/activate
python -m pip install .
```

See [installation and notebook setup](../docs/INSTALLATION.md) if needed. Run the
Python examples below in order. They require an internet connection.

## 1. Fetch one float into memory

`base_url` selects the collection. `output_dir=None` keeps the download in
memory without creating files.

```python
from mermaid import geocsv

base_url = "https://bathymetrix.com/geocsv/testing/"
downloads = geocsv.fetch("P0006", base_url=base_url, output_dir=None)
records = geocsv.read(downloads)[0]
records.head()
```

The documented collection is **testing only**; its recorded inventory contains
P0006 and P0045.
These initial test snapshots may be retired. To see which snapshot supplied
the file:

```python
print(downloads[0].provenance.release_id)
print(downloads[0].provenance.testing_only)  # True
```

## 2. Save the whole test set to disk

Omit the float selection to download every file in the selected snapshot.
`output_dir` chooses where to save them:

```python
saved = geocsv.fetch(base_url=base_url, output_dir="geocsv-downloads")
for item in saved:
    print(item.provenance.instrument_id, item.path)
```

Files and their manifest are saved in a snapshot directory beneath
`geocsv-downloads/`. Repeating the call verifies and reuses identical files;
conflicting files raise an error. Pass `saved` directly to `geocsv.read` to
retain download provenance. For a selection, use `fetch(["P0006", "P0045"], ...)`.

## 3. Fetch a specific snapshot

The default selects the latest snapshot. Supply `release` to repeat a download
from a particular snapshot while it remains hosted:

```python
pinned = geocsv.fetch(
    "P0006",
    base_url=base_url,
    release="2026-10-21T22:48:33.277Z",
    output_dir=None,
)
print(pinned[0].provenance.release_id)
```

Pass the timestamp literally; `fetch` handles URL encoding.
For result fields, memory use, error behavior, and protocol details, see the
[fetch reference](../docs/FETCH.md#the-fetch-interface).
