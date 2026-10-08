"""Inspect segmentation in a longer P0006 request without explicit merging."""

import argparse
from pathlib import Path

import obspy
from obspy import UTCDateTime
from obspy.clients.fdsn import Client


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2018-06-29T00:00:00Z")
    parser.add_argument("--end", default="2018-07-29T00:00:00Z")
    parser.add_argument("--plot", action="store_true")
    args = parser.parse_args()
    start = UTCDateTime(args.start)
    end = UTCDateTime(args.end)
    if end <= start:
        parser.error("--end must be later than --start")

    client = Client("https://service.earthscope.org", timeout=60)
    output = Path(__file__).resolve().parent / "downloads"
    output.mkdir(exist_ok=True)
    filename = output / f"P0006_{start.strftime('%Y%m%dT%H%M%S')}_{end.strftime('%Y%m%dT%H%M%S')}.mseed"
    # Preserve the actual response, rather than reserializing a parsed Stream.
    client.get_waveforms(
        network="MH",
        station="P0006",
        location="00",
        channel="BDH",
        starttime=start,
        endtime=end,
        filename=str(filename),
    )
    # Reading MiniSEED itself assembles records into traces. This is not a
    # direct description of either archive acquisitions or server-side merges.
    st = obspy.read(str(filename), format="MSEED")
    print(f"ObsPy {obspy.__version__}; client={client.base_url}")
    print(f"Request: MH.P0006.00.BDH, {start.isoformat()} through {end.isoformat()}")
    print(f"Raw response: {filename}, {filename.stat().st_size} bytes")
    print(st.__str__(extended=True))
    st.print_gaps()
    for index, trace in enumerate(st):
        print(f"\nTrace {index}: {trace.id}")
        print(f"start_ns={trace.stats.starttime.ns}; end_ns={trace.stats.endtime.ns}")
        print(f"rate={trace.stats.sampling_rate}; npts={trace.stats.npts}")
        print(f"MiniSEED metadata: {trace.stats.get('mseed')}")
    if args.plot:
        st.plot()


if __name__ == "__main__":
    main()
