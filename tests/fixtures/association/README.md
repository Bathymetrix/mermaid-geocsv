# Synthetic association fixture

Every station, time, coordinate, and sample count in `synthetic.geocsv` was
invented for testing. No source MERMAID history was cut or searched to choose
matching lines. Tests independently construct four-sample ObsPy traces with
explicit station/time/rate headers, then ask the associator to find a match
among all fixture records. A GPS record shares the first event's timestamp
and identity, exercising event-category selection.

Source times deliberately mix three and nine fractional digits. Coordinates
include complete pairs, either component missing, and both missing. This
tracked fixture supplies reproducible CI unit coverage; full real histories
remain unchanged, local integration fixtures.
