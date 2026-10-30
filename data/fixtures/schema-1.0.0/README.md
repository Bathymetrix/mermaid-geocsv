# Schema 1.0.0 fixtures

These separate fixtures project retained historical source evidence into the
selected schema for portable parser, association and tutorial tests. They are
not newly calculated observations or direct output from the migrated writer.
`manifest.json` records each source/hash and the mapping from each subset index to its historical source record.
P0006 retains its first 300 records plus 12 GPS fixes for the plotting example.
P0045 retains five initial context rows and 20 rows around the merge example.
All original files remain unchanged in their former locations.

Column and method names, model notation and missing-cell spelling follow the
new profile. Recording Elevation explicitly contains synthetic zero according
to the selected producer convention. Historical printed epochs retain their
value with six digits; additional zeros do not recover submillisecond timing.
Crossing direction comes from the corresponding saved cycle's explicit descent
or ascent attribute, with its pickle hash recorded. No interpolation is rerun.
Negative pressure-sensor readings remain unchanged. Fixture subsets do not
establish uniqueness across complete source histories.

Independent original MiniSEED/SAC files remain under the original association
fixture tree. Temporary writer-generated candidates and their exhaustive
verification are separate local artifacts. The separately [published tutorial replay prefixes](hosted/README.md) preserve
actual schema 1.0.0 writer output for offline tests. Fetch and EarthScope
tutorials download complete public testing histories directly.
