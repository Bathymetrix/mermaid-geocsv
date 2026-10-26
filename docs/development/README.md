# Development examples and checks

The [tutorials](../README.md#tutorials) provide short introductions. These
supporting pages retain the extended examples, scientific explanations,
diagnostic assertions, and fixture checks from the longer walkthroughs:

- [Reader and pandas](READ.md): indexing, missing values, time selection,
  aggregation, source metadata, bytes, and timezone conversion.
- [Fetch](FETCH.md): an offline HTTP test collection, selection order, disk
  reuse, timestamp encoding, result fields, memory, provenance, and failures.
- [Association](ASSOCIATE.md): strict tolerances, fresh destinations, source
  record mappings, batch failures, overlapping P0045 segments, clipped windows,
  and sample-grid placement.
- [SAC](WRITE_SAC.md): geographic mappings, pressure conventions, float32
  precision, independent reference comparisons, missing REQ pressure,
  overwrite refusal, merged windows, and migration from the former writer.
- [Plotting](PLOTTING.md): pressure overlays, longitude wrapping, surface
  distance estimates, and pressure-derived 3D tracks with their assumptions.

The Python blocks in each page run in order with the dependencies described
in the [installation guide](../INSTALLATION.md). `tests/test_tutorials.py`
checks tutorial/notebook parity, runs the short examples, and retains execution
checks for these extended examples. Ordinary tests redirect the short fetch
tutorial to a temporary local collection with the same two instrument IDs and
snapshot ID. A live run of the fetch tutorial separately checks public hosting.

The fixture examples use tracked data and require no complete local histories.
GeoCSV subsets demonstrate the selected cases without establishing uniqueness
across omitted history records. Full-history restoration and corpus checks
remain in the [fixture maintenance guide](../../scripts/fixtures/README.md).
