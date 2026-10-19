# Rebuilt processed waveform association fixtures

Waveform pairs were copied on 2026-10-13 from `$MERMAID/processed/`
(resolved source root in `manifest.json`). That source is read-only. The
fixtures contain 18 MiniSEED/SAC pairs from automaid v4.5.11 and 14 tracked
`association_subset.geocsv` files selected on 2026-10-16. The subsets contain
137 records in 36,085 bytes in total, instead of the 159,821,516 bytes of full
histories. All association tests run from distributed files when ObsPy is
installed; no ignored history is required.

MiniSEED fixtures are association inputs. SAC fixtures are independent output
references only: read them separately with ObsPy, then compare their inherited
`stats.sac` values key-by-key against approved SAC fields projected onto the
MiniSEED traces after GeoCSV association. Never use SAC reference headers to
fill or match association metadata. SAC-input association is outside scope
until further instruction; SAC output projection remains deferred without a placeholder argument.

Complete `geo_DET_REQ.csv` histories remain unchanged, local, and Git-ignored.
They are optional corpus references, not test prerequisites. To restore and
check them against the same processed snapshot, from the repository root:

```bash
.venv/bin/python scripts/fixtures/restore_geocsv_histories.py
.venv/bin/python scripts/fixtures/check_full_histories.py
```

Restoration checks recorded hashes and refuses to replace a different local
history. The second command verifies each subset byte-for-byte against the
recorded full-history extraction and independently runs all 18 sampled
waveform associations against complete histories. Neither command modifies
protected source data. A newer source snapshot requires a deliberate
fixture/provenance update.

## Sampling and provenance

The initial collection script,
[`collect_processed_examples.py`](../../../scripts/fixtures/collect_processed_examples.py),
selects up to three paired basenames per
DET/REQ × WLT1–WLT5/RAW combination using seed 20261013 and a sorted source
file inventory. Missing combinations remain explicit zeros. The sampled
MiniSEED and SAC files preserve the original float/cycle directory layout.
`manifest.json` records every waveform file, source-relative paths, population
counts, the seed, and SHA-256 hashes of both waveforms and complete histories.

The script preserves the original sampling procedure, but is not a complete
regeneration tool: the GeoCSV subsets, expected association indices, and
header audit below were subsequent additions. It refuses an existing fixture
destination. See the [maintenance notes](../../../scripts/fixtures/README.md)
for its historical scope and the current restore/check commands.

For each sampled waveform, the GeoCSV subset retains all same-SNCL event
rows within 1 ms of its start, irrespective of count or rate, two surrounding
source records on either side of each time candidate, and the previous and
next same-SNCL events in source-record order. It also retains the first record
of every non-event method for GPS/pressure/thermocline parsing context. Selected
records remain in original file order. Original header and record bytes are
unchanged; no values are recomputed. `subset_selection` records this policy.

Each history's `subset` entry records its subset path/hash, original file
size and record count, header line count, and ordered `source_record_indices`.
The list maps each zero-based subset record index to its original complete
history index. Each waveform separately records its expected
`original_source_record_index` and `subset_record_index`, determined by a
direct full-history CSV scan without calling the associator.

The reader's `source_record_index` and `metadata.source_path` refer to the
**subset actually read**, not the original history. Its preserved `#created`
comment dates the original source export. Use the manifest mapping and full
source hash to trace back to that export; never relabel subset indices or
source paths as complete-history provenance. Subsets do not prove uniqueness
against omitted rows. `check_full_histories.py` provides that separate check
for the 18 sampled waveforms.

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
in their tracked GeoCSV subset by complete SNCL, an explicit 1 ms time tolerance,
original sample count, and the provisional 0.01 Hz rate check. The largest
sampled GeoCSV/MiniSEED rate difference is below 0.000002 Hz. Tracked subset
GeoCSV event rows carry only Q/D values; independent DET/REQ labels are absent
from GeoCSV, so code-domain validation alone cannot prove stream classification
for unsampled events. The optional full-history check also confirms unique
matches for all 18 sampled waveforms in the recorded complete histories.

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
