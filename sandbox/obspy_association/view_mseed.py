"""Print MiniSEED trace headers and display the waveform with ObsPy."""

import argparse

from obspy import read


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", help="path to a MiniSEED file")
    path = parser.parse_args().file

    stream = read(path, format="MSEED")
    print(stream.__str__(extended=True))
    for trace in stream:
        quality = trace.stats.mseed.get("dataquality", "not present")
        print(f"{trace.id}: dataquality={quality}")
    stream.plot()


if __name__ == "__main__":
    main()
