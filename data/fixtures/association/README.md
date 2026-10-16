# Rebuilt processed waveform association fixtures

Copied on 2026-10-13 from `$MERMAID/processed/` (resolved source root in
`manifest.json`). That source is read-only: never modify it without the user's
express instruction. The fixtures contain 18 MiniSEED/SAC pairs and 14
**complete**, verbatim `geo_DET_REQ.csv` histories from automaid v4.5.11,
including GPS, pressure, thermocline, and event records. GeoCSV histories must
not be subset to the selected waveform rows.

MiniSEED fixtures are association inputs. SAC fixtures are independent output
references only: read them separately with ObsPy, then compare their inherited
`stats.sac` values key-by-key against approved SAC fields projected onto the
MiniSEED traces after GeoCSV association. Never use SAC reference headers to
fill or match association metadata. SAC-input association is outside scope
until further instruction; the optional output projection remains reserved.

The complete GeoCSV copies are local, ignored files; they are not distributed
through GitHub. Waveform pairs, the manifest, and audit results remain tracked.
On a fresh checkout, waveform header/hash tests still run; tests requiring
the full histories explicitly skip until restored. With the same processed
snapshot available under `$MERMAID/processed/`, restore them from the
repository root:

```bash
.venv/bin/python sandbox/obspy_association/restore_geocsv_histories.py
```

The restoration reads the source without modifying it, checks the recorded
hashes, and refuses to replace an existing different local history. A newer
source snapshot requires a deliberate fixture/provenance update.

## Sampling and provenance

`collect_processed_examples.py` selects up to three paired basenames per
DET/REQ × WLT1–WLT5/RAW combination using seed 20261013 and a sorted source
file inventory. Missing combinations remain explicit zeros. The sampled
MiniSEED and SAC files preserve the original float/cycle directory layout.
`manifest.json` records every copied file, source-relative paths, population
counts, the seed, and SHA-256 hashes. GeoCSV source record indices remain valid
because complete files are copied. The reader's source path correctly refers
to the fixture copy; the manifest traces it back to the source tree.

| Combination | Source MiniSEED files | Paired basenames | Selected pairs |
| --- | ---: | ---: | ---: |
| DET.WLT1 | 0 | 0 | 0 |
| DET.WLT2 | 22 | 22 | 3 |
| DET.WLT3 | 0 | 0 | 0 |
| DET.WLT4 | 0 | 0 | 0 |
| DET.WLT5 | 39,677 | 39,677 | 3 |
| DET.RAW | 0 | 0 | 0 |
| REQ.WLT1 | 0 | 0 | 0 |
| REQ.WLT2 | 0 | 0 | 0 |
| REQ.WLT3 | 16 | 16 | 3 |
| REQ.WLT4 | 7 | 7 | 3 |
| REQ.WLT5 | 3,438 | 3,438 | 3 |
| REQ.RAW | 177 | 177 | 3 |

Each selected basename has both `.mseed` and `.sac`; six combinations were
present and six absent. No physically recovered continuous-buffer products
are included. `REQ.RAW` is an event product with quality D, not the recovered
buffer stream with quality R.

## Header audit

The read-only source audit checked all **43,337 MiniSEED files**, including
all traces returned by ObsPy, against network MH, station identity derived
from the float directory, the documented WLT/RAW channel and location mapping,
and **DET Q / REQ D regardless of sample rate**. It found **zero
inconsistencies**; aggregate results are in `header_audit.json`. This corpus
audit did not compare every source waveform to SAC or GeoCSV.

The repeatable fixture tests compare all 18 copied MiniSEED/SAC pairs' SNCL,
SAC `kuser1` product labels, MiniSEED quality flags, and their matched GeoCSV
event quality values. All agree. All sampled waveforms match exactly one row
in their full GeoCSV history by complete SNCL, an explicit 1 ms time tolerance,
original sample count, and the provisional 0.01 Hz rate check. The largest
sampled GeoCSV/MiniSEED rate difference is below 0.000002 Hz. Full-history
GeoCSV event rows carry only Q/D values; independent DET/REQ labels are absent
from GeoCSV, so full-history code-domain validation alone cannot prove stream
classification for unsampled events.

The non-20-Hz DET.WLT2 sample uses `MH.P0030.10.MDH` and Q. RAW requested
products use location 10 and D. Paired SAC geographic/depth header comparisons
remain future work. ObsPy emits sample-spacing warnings for some SAC inputs:
its reader rounds float32 SAC delta to microsecond precision when constructing
core sampling metadata. SAC core sampling rates should therefore not be
assumed bit-identical to MiniSEED or the original `stats.sac.delta` header.
MiniSEED remains the ground truth for this association stage.

Run the checks from the repository root:

```bash
.venv/bin/pytest -q tests/test_associate_synthetic.py tests/test_associate.py tests/test_data_quality_fixtures.py
```

Do not overwrite/regenerate these fixtures during tests. The collection script
refuses an existing destination. Replacing fixtures is a separate explicit
operation, with new provenance and another header audit.
