# ObsPy association sandbox

Exploratory retrieval examples for planning initial GeoCSV association.
These scripts do not implement an association API or change the parser.
Run from the repository root with an environment containing this package and
ObsPy. Downloaded responses go under ignored `downloads/`.

Install the sandbox dependency in the repository environment:

```bash
.venv/bin/python -m pip install -e '.[obspy]'
```

## Short acquisition examples

```bash
.venv/bin/python sandbox/obspy_association/retrieve_event_examples.py --raw
```

Add `--plot` for the seismograms. The examples use two `Algorithm(event)` rows
from the bundled P0006 GeoCSV fixture:

| Source record index | Acquisition | Start time (UTC) | Rate | Count | Source quality |
| --- | --- | --- | --- | --- | --- |
| 98 | Detected | 2018-06-29 17:07:31.205 | 20 Hz | 4832 | Q |
| 100 | Requested | 2018-07-06 01:49:28.590 | 20 Hz | 4800 | D |

Requests use complete SNCL `MH.P0006.00.BDH`, with a one-second margin around
the source's first and last sample. This is a retrieval margin, not our
future matching tolerance. Quality is not filtered, so we can inspect the
service's default behavior. The scripts do not explicitly trim, merge,
calibrate, or attach metadata.

The normal `get_waveforms` path parses MiniSEED and trims to request bounds
inside ObsPy. With `--raw`, a second request saves the service response before
that client-side parsing/trimming. Reading that file still assembles MiniSEED
records into traces. Neither result alone identifies original acquisitions.
See the [client implementation](https://docs.obspy.org/_modules/obspy/clients/fdsn/client.html)
and [retrieval parameters](https://docs.obspy.org/packages/autogen/obspy.clients.fdsn.client.Client.get_waveforms.html).

The explicit HTTPS EarthScope endpoint serves the role of `Client("IRIS")`
in the supplied example, without depending on alias behavior across versions.
Fixture timestamps are already corrected; do not apply `TimeCorrection` again.

## Longer window

```bash
.venv/bin/python sandbox/obspy_association/retrieve_long_window.py
```

The default request spans 30 days. A one-year probe is explicit:

```bash
.venv/bin/python sandbox/obspy_association/retrieve_long_window.py \
    --start 2018-06-29T00:00:00Z --end 2019-06-29T00:00:00Z
```

Inspect trace count, gaps/overlaps, rates, timing, and quality. A successful
request does not establish completeness; compare with eligible GeoCSV rows
before concluding that all expected acquisitions were returned.

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) for the running design questions
and [OBSERVATIONS.md](OBSERVATIONS.md) for execution evidence.
