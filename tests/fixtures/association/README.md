# Historical synthetic association fixtures

These unsupported-schema files are retained unchanged as source
evidence and are unsupported by the current reader. Active synthetic tests
use the separate [schema 1.0.0 fixtures](../schema-1.0.0/README.md). The
descriptions below record the original fixtures and their former test purpose.

Every station, time, coordinate, and sample count in `synthetic.geocsv` was
invented for testing. No source MERMAID history was cut or searched to choose
matching lines. Tests independently construct four-sample ObsPy traces with
explicit station/time/rate headers, then ask the associator to find a match
among all fixture records. A GPS record shares the first event's timestamp
and identity, exercising event-category selection.

Source times deliberately mix three and nine fractional digits. Coordinates
include complete pairs, either component missing, and both missing. This
fixture formerly supplied CI unit coverage alongside the
[tracked real-data subsets](../../../data/fixtures/association/README.md).
Full real histories remain unchanged for separate local corpus checks.

Two additional event rows provide contiguous six-sample continuations of the
first two four-sample events. They exercise exact merged coverage and preserve
the anchor coordinates separately from the continuation coordinates.
`indexed.geocsv` is also entirely invented. Its unsorted competitors exercise
both sides of the fixed time window, category and count filtering, missing time,
and station identity; tests assert a predetermined source record and position.
