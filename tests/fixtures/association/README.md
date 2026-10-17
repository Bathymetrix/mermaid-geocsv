# Synthetic association fixture

Every station, time, coordinate, and sample count in `synthetic.geocsv` was
invented for testing. No source MERMAID history was cut or searched to choose
matching lines. Tests independently construct four-sample ObsPy traces with
explicit station/time/rate headers, then ask the associator to find a match
among all fixture records. A GPS record shares the first event's timestamp
and identity, exercising event-category selection.

Source times deliberately mix three and nine fractional digits. Coordinates
include complete pairs, either component missing, and both missing. This
tracked fixture supplies reproducible CI unit coverage alongside the
[tracked real-data subsets](../../../data/fixtures/association/README.md).
Full real histories remain unchanged for separate local corpus checks.

Two additional event rows provide contiguous six-sample continuations of the
first two four-sample events. They exercise exact merged coverage and preserve
the anchor coordinates separately from the continuation coordinates.
`indexed.geocsv` is also entirely invented. Its unsorted competitors exercise
both sides of the fixed time window, category and count filtering, missing time,
and station identity; tests assert a predetermined source record and position.
