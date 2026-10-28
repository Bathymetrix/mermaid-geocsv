# Bathymetrix®
# https://bathymetrix.com
# © 2026 Bathymetrix, LLC
# Author: Joel D. Simon <jdsimon@bathymetrix.com>
# SPDX-License-Identifier: MIT

"""Fetch and read MERMAID GeoCSV metadata and associate ObsPy waveforms."""

from ._fetch import GeoCSVDownload, GeoCSVFetchError, GeoCSVFetchResult, fetch
from ._read import GeoCSVComment, GeoCSVError, GeoCSVMetadata, read

__author__ = "Joel D. Simon <jdsimon@bathymetrix.com>"
__license__ = "MIT"
__copyright__ = "© 2026 Bathymetrix, LLC"
__version__ = "0.26.0"

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


def associate(waveforms, records, *, time_tolerance=0.001, allow_first_segment=False,
              create_sac_header=False):
    """Attach uniquely matched GeoCSV event metadata to ObsPy waveforms.

    Parameters
    ----------
    waveforms : obspy.Trace or obspy.Stream
        MiniSEED-derived waveforms with nonempty, loaded, unmasked samples.
        The destinations ``stats.geocsv`` and ``stats.coordinates`` must be
        absent. Every match and projection validates before any trace is modified.
    records : list of pandas.DataFrame
        Tables returned by ``read``, retaining source indices and immutable
        ``frame.attrs["geocsv"]`` metadata. May span datasets and files. Matching
        requires complete SNCL, timezone-aware starts, sample counts, and rates
        in ``hertz``. Only Location may be empty. Coordinates require latitude
        and longitude in ``degrees_north`` and ``degrees_east``.
    time_tolerance : float, optional
        Inclusive absolute start/containment tolerance in seconds. Default 0.001
        is 1 millisecond; zero requires exact times. Must be finite and nonnegative.
        Comparisons retain UTC nanoseconds, independent of timestamp spelling.
    allow_first_segment : bool, optional
        Default False requires the original segment's sample count. True permits
        a clipped or combined window with one source segment containing its start
        and gap-free source sample coverage of its grid. Multiple containing anchors
        raise, even if one passes standard matching. No waveform merge is performed.
    create_sac_header : bool, optional
        Default False leaves ``stats.sac`` untouched. True requires it to be absent
        and creates ObsPy's fresh SAC baseline plus ``stla``, ``stlo``, ``stel``,
        and ``stdp`` using the documented marine position/depth conventions.
        Missing pressure is allowed only for source DataQuality D, leaving depth
        undefined. Write with ObsPy's ``Trace.write`` or ``Stream.write``.

    Returns
    -------
    None
        Each trace receives fresh ``stats.geocsv`` and ``stats.coordinates``
        containers, plus ``stats.sac`` when requested. Samples and native waveform
        headers are preserved. Coordinate elevation uses a sea-level reference
        of 0.0.

    Raises
    ------
    ImportError
        ObsPy is unavailable; install ``mermaid-geocsv[obspy]``.
    TypeError
        The waveform argument is not an ObsPy Trace or Stream, or either boolean
        option is not a bool.
    ValueError
        Inputs, provenance, or destinations are invalid, matching is absent or
        ambiguous, source coverage is incomplete, or a projection is invalid.

    See Also
    --------
    read : Parse GeoCSV sources into tables with provenance.

    Notes
    -----
    Standard matches require start/count agreement and rates within 0.00001 Hz.
    Source DataQuality and waveform quality are retained independently, without
    filtering matches. Later processing does not refresh the association snapshot.
    Matching rules, report fields, and projection conventions are documented at:
    https://github.com/Bathymetrix/mermaid-geocsv/blob/main/docs/obspy-association.md
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
                      allow_first_segment=allow_first_segment,
                      create_sac_header=create_sac_header)
