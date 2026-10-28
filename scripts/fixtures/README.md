# Association fixture maintenance

These repository scripts maintain and check the association fixture snapshot.
They are separate from the package API and publisher acceptance gate.
Run commands from the repository root with its `.venv`; the corpus check also
requires the optional ObsPy dependency.

## Restore complete local histories

The ordinary tests use tracked GeoCSV subsets and need no restoration. For
optional checks against the complete histories recorded in the manifest:

```bash
.venv/bin/python scripts/fixtures/restore_geocsv_histories.py
.venv/bin/python scripts/fixtures/check_full_histories.py
```

Restoration reads `$MERMAID/processed/` and copies only missing histories into
the repository's ignored fixture paths. It checks source and destination
hashes against the manifest, refuses to replace a differing existing file,
and never modifies the protected source tree. A changed source snapshot
requires a deliberate fixture/provenance update.

The check reads local copies only. It verifies complete-history and subset
hashes, verbatim subset extraction, event quality domains, and all 18 expected
waveform associations against complete histories. It writes nothing. A subset
alone cannot establish uniqueness among omitted source records. See the
[fixture inventory and provenance](../../data/fixtures/association/README.md).

## Initial collection script: historical scope

`collect_processed_examples.py` records the initial 2026-10-13 sampling
procedure: sorted source inventory, seed 20261013, up to three paired
MiniSEED/SAC basenames per observed DET/REQ and WLT/RAW combination, and
verbatim complete histories with hashes. It reads `$MERMAID/processed/` and
refuses an existing `data/fixtures/association/` destination.

This is **not a complete regeneration tool for the current fixtures**. It
does not produce the later GeoCSV subsets, subset-to-original record maps,
expected waveform association indices, or `header_audit.json`. The fixture
documentation and current manifest record those additions. Retain the script for sampling
provenance; replacing or regenerating fixtures requires a separately chosen
snapshot and a complete provenance/audit update. Do not remove the current
fixture directory to run it.

## Current fixture snapshots

Canonical fixture provenance is maintained with the data:

- [P0006](../../data/fixtures/P0006/README.md) and [P0045](../../data/fixtures/P0045/README.md): complete shared GeoCSV files.
- [Association](../../data/fixtures/association/README.md): paired waveforms, sampled subsets, and record mappings.
- [P0006 responses](../../data/fixtures/P0006/waveforms/README.md): three original pairs and unmodified EarthScope responses for offline tutorial replay.
- [Combined P0045 window](../../tests/fixtures/association/P0045_20220115/README.md) and [clipped P0006 response](../../tests/fixtures/association/P0006_20180713_earthscope/README.md): coverage examples.

Future refreshes must replace superseded snapshots, check dependent tests and
tutorials, and update hashes, record maps, and provenance together. Never
rewrite protected processed inputs or regenerate fixtures during tests.
