# Bathymetrix®
# https://bathymetrix.com
# © 2026 Bathymetrix, LLC
# Author: Joel D. Simon <jdsimon@bathymetrix.com>
# SPDX-License-Identifier: MIT

"""Fetch and read MERMAID GeoCSV, and associate event metadata with ObsPy traces."""

from ._fetch import GeoCSVDownload, GeoCSVFetchError, GeoCSVFetchResult, fetch
from .read import GeoCSVComment, GeoCSVError, GeoCSVMetadata, read

__author__ = "Joel D. Simon <jdsimon@bathymetrix.com>"
__license__ = "MIT"
__copyright__ = "© 2026 Bathymetrix, LLC"
__version__ = "0.16.0"

__all__ = [
    "__version__",
    "read",
    "fetch",
    "associate",
    "GeoCSVError",
    "GeoCSVComment",
    "GeoCSVMetadata",
    "GeoCSVDownload",
    "GeoCSVFetchError",
    "GeoCSVFetchResult",
]


def associate(waveforms, records, *, time_tolerance=0.0001, allow_merge=False):
    """Attach uniquely matched GeoCSV event metadata to ObsPy waveforms.

    Parameters
    ----------
    waveforms : obspy.Trace or obspy.Stream
        Original MiniSEED-derived waveforms with loaded samples. Modified in
        place only after every match and projection validates. The destinations
        ``stats.geocsv`` and ``stats.coordinates`` must be absent.
    records : list of pandas.DataFrame
        Tables returned by :func:`read`, retaining their source indices and
        immutable ``frame.attrs["geocsv"]`` provenance. May span datasets/files.
    time_tolerance : float, optional
        Inclusive absolute start-time tolerance in seconds. Default is 0.0001
        (100 microseconds); zero requires exact matching. Must be finite and
        nonnegative. Full UTC nanosecond values are compared; source lexical
        resolution does not enlarge the tolerance.
    allow_merge : bool, optional
        Default False requires the original sample count. If True, a longer
        trace without a standard match may adopt a unique first segment's
        location, provided source sample ranges cover its grid exactly without
        gaps after overlaps are counted once. No waveform merging is performed.

    Returns
    -------
    None
        Each trace receives fresh ``stats.geocsv`` and ``stats.coordinates``
        containers. Waveform data and native headers remain unchanged.

    Raises
    ------
    ImportError
        ObsPy is unavailable; install ``mermaid-geocsv[obspy]``.
    TypeError
        The waveform argument is not an ObsPy Trace or Stream.
    ValueError
        Inputs, provenance, or destination containers are invalid, a trace has
        no unique eligible event row, or a coordinate projection is incomplete.

    Notes
    -----
    Matches require complete, exact SNCL (only Location may be empty), zoned
    UTC-comparable times, loaded sample count equality, and measured rates
    within 0.01 Hz. This rate threshold is provisional scientific policy.
    DataQuality is retained as source evidence, independent of waveform quality.
    Invalid event identities and duplicate complete SNCL/time/count/rate keys
    fail source preflight; multiple traces may independently use the same row.

    ``stats.geocsv`` preserves all source columns and adds ``dataset_index``,
    ``source_record_index``, immutable ``metadata``, ``association``
    (``one_segment`` or ``first_segment``), and
    ``starttime_difference_seconds`` (waveform minus matched source start).
    These keys and ObsPy AttribDict attributes/methods are reserved against
    source-column collisions. Coordinates require latitude/longitude declared
    in degrees_north/degrees_east; elevation is the adopted sea-level reference
    0.0, with no geoid model. Zero is the same in metres and kilometres; no
    nonzero elevation unit convention is established here. Position refers to
    the first sample, not an average over the trace. For first_segment, raw
    fields still describe only
    the anchor row. Association guarantees end at initial attachment; later
    waveform processing does not refresh it. SAC projection is deferred.
    """
    try:
        from ._associate import associate as _associate
    except ModuleNotFoundError as exc:
        if exc.name != "obspy":
            raise
        raise ImportError(
            "GeoCSV association requires ObsPy; install it with "
            "pip install 'mermaid-geocsv[obspy]'"
        ) from exc
    return _associate(waveforms, records, time_tolerance=time_tolerance,
                      allow_merge=allow_merge)
