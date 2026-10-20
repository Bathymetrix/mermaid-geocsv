# Association fixture maintenance

These repository scripts maintain and check the association fixture snapshot.
They are separate from the package API and the exploratory
[EarthScope retrieval sandbox](../../sandbox/obspy_association/README.md).
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

These scripts previously lived under `sandbox/obspy_association/`; use the
paths above for current maintenance commands.

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

## Deferred general-fixture consolidation

The older general fixture `data/fixtures/P0006/P0006.geocsv` and current
real fixtures under `tests/fixtures/geocsv/` still need consolidation. Choose
one authoritative copy of each instrument file; update parser tests,
reading/plotting tutorial pairs, provenance notes, and all path references
before removing superseded copies. Do not retain different exports under
the same purported fixture identity. This task remains deferred; the docs
cleanup does not replace or delete any fixture.
