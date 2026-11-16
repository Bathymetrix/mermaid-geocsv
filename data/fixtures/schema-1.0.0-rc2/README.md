# Producer rc2 examples

These contiguous subsets preserve the header and selected data-row bytes
from temporary GeoCSV exports by automaid v4.11.2 at commit `d973be5`.
Automaid loaded saved cycles from the November 5 processed history, reran
the station location calculation with the 50 m boundary, and wrote files
under a common local creation timestamp. The examples use BDH acquisitions,
whose source location codes agree with the included waveform references.
These files are tutorial data. The rebuilt processed corpus and its published
snapshots have separate provenance.

The [manifest](manifest.json) records the SHA-256 of each subset and its
complete source export. Ranges are zero-based and half-open. Adding the
range start to a subset source index identifies the source export record.
P0006 retains its first 300 rows and includes all three EarthScope tutorial
acquisitions. P0045 retains the interval containing the overlapping segments
used in the combined window example. Subset association does not establish
uniqueness across the complete history.
