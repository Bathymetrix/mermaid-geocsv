"""Inspect two original P0006 waveform requests against their GeoCSV rows."""

import argparse
from pathlib import Path

import obspy
from obspy import UTCDateTime
from obspy.clients.fdsn import Client

from mermaid import geocsv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plot", action="store_true")
    parser.add_argument("--raw", action="store_true", help="Also save a separate raw service response.")
    args = parser.parse_args()

    sandbox = Path(__file__).resolve().parent
    source = sandbox.parents[1] / "data/fixtures/P0006/P0006.geocsv"
    frame = geocsv.read(source)[0]
    # An explicit HTTPS URL targets the former IRIS waveform service without
    # relying on version-dependent IRIS/EARTHSCOPE aliases.
    client = Client("https://service.earthscope.org", timeout=30)

    for record_index, label in ((98, "detected"), (100, "requested")):
        row = frame.loc[record_index]
        assert row["MethodIdentifier"].startswith("Algorithm(event):")
        start = UTCDateTime(row["StartTime"].isoformat())
        rate = float(row["SampleRate"])
        count = int(row["SampleCount"])
        last_sample = start + (count - 1) / rate
        # A one-second retrieval margin is experimental, not a match tolerance.
        # Do not reapply TimeCorrection: StartTime is already corrected.
        request = dict(
            network=row["Network"],
            station=row["Station"],
            location=row["Location"],
            channel=row["Channel"],
            starttime=start - 1,
            endtime=last_sample + 1,
        )
        print(f"\n{label}: source_record_index={record_index}")
        print(f"Source: {source}")
        print(row.to_string())
        print(f"Request: {request}")
        # Do not filter quality yet: observe the service's default selection.
        st = client.get_waveforms(**request)
        print(st.__str__(extended=True))
        st.print_gaps()
        for trace in st:
            print(f"\n{trace.id}")
            print(f"starttime={trace.stats.starttime.isoformat()}, ns={trace.stats.starttime.ns}")
            print(f"start difference [s]={trace.stats.starttime - start:.9f}")
            print(f"rate={trace.stats.sampling_rate}, npts={trace.stats.npts}, len(data)={len(trace.data)}")
            print(f"sample-count difference={trace.stats.npts - count}")
            print(f"MiniSEED metadata: {trace.stats.get('mseed')}")
            print(f"Processing history: {trace.stats.get('processing', [])}")

        if args.raw:
            output = sandbox / "downloads"
            output.mkdir(exist_ok=True)
            filename = output / f"P0006_record_{record_index}.mseed"
            # filename bypasses client-side parsing/trimming. This is a SECOND
            # request; compare its parsed result, not byte identity, with st.
            client.get_waveforms(**request, filename=str(filename))
            raw_stream = obspy.read(str(filename), format="MSEED")
            print(f"\nRaw response saved to {filename}")
            print(raw_stream.__str__(extended=True))
            raw_stream.print_gaps()
        if args.plot:
            st.plot()


if __name__ == "__main__":
    main()
