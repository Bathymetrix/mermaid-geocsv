# Published schema 1.0.0 tutorial replay inputs

These are byte-preserving prefixes of the P0006/P0045 histories published at
`https://bathymetrix.com/geocsv/testing/`, snapshot
`2026-10-30T18:08:32.316000Z`, downloaded on 2026-10-30. Each retains the
original header and first 300 data records, without conversion or rewriting.
The manifest records published-source URLs, complete-file sizes/hashes,
subset sizes/hashes and the mapping to complete-history record indices.
The creation timestamp belongs to the published source, not this extraction.

Ordinary tutorial tests serve these prefixes over loopback HTTP and replay
saved waveform responses. The tutorial code itself downloads real public data.
These prefixes preserve the three P0006 examples and nearby candidates but
cannot establish uniqueness across omitted complete-history rows. Separate
live verification uses the complete downloaded histories. Original waveform
fixtures and their historical request manifests remain unchanged.
