# Bathymetrix®
# https://bathymetrix.com
# © 2026 Bathymetrix, LLC
# Author: Joel D. Simon <jdsimon@bathymetrix.com>
# SPDX-License-Identifier: MIT

"""Fetch and read MERMAID GeoCSV and associate waveform station locations."""

from ._fetch import GeoCSVDownload, GeoCSVFetchError, GeoCSVFetchResult, fetch
from ._read import GeoCSVComment, GeoCSVError, GeoCSVMetadata, read

__author__ = "Joel D. Simon <jdsimon@bathymetrix.com>"
__license__ = "MIT"
__copyright__ = "© 2026 Bathymetrix, LLC"
__version__ = "0.25.0"

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
        MiniSEED-derived waveforms with loaded samples. Modified in
        place only after every match and projection validates. The destinations
        ``stats.geocsv`` and ``stats.coordinates`` must be absent;
        ``stats.sac`` must also be absent when requested.
    records : list of pandas.DataFrame
        Tables returned by :func:`read`, retaining their source indices and
        immutable ``frame.attrs["geocsv"]`` provenance. May span datasets/files.
    time_tolerance : float, optional
        Inclusive absolute start/containment tolerance in seconds. Default is 0.001
        (1 millisecond); zero removes absolute timing slack. Must be finite and
        nonnegative. Full UTC nanosecond values are compared; source lexical
        resolution does not enlarge the tolerance.
    allow_first_segment : bool, optional
        Must be a bool. Default False requires the original sample count.
        If True, require one source segment containing the waveform start.
        A trace without a standard match may adopt that anchor's metadata,
        including for clipped or combined windows. Source sample ranges must
        cover its grid without gaps after clipping and counting overlaps once.
        Multiple containing anchors raise, even if one is a standard match.
        No waveform merging is performed.

    create_sac_header : bool, optional
        Default False leaves ``stats.sac`` untouched. If True, create fresh SAC
        headers using ObsPy's default conversion, then populate station latitude
        (``stla``), longitude (``stlo``), adopted sea-level elevation (``stel``),
        and approximate depth (``stdp``) from the documented GeoCSV mapping.
        Requires ``stats.sac`` to be absent. Missing REQ pressure leaves depth
        undefined; missing DET pressure raises. All projections validate before
        any trace is modified. Write with ``trace.write(path, format="SAC")``.

    Returns
    -------
    None
        Each trace receives fresh ``stats.geocsv`` and ``stats.coordinates``
        containers, plus ``stats.sac`` when requested. Waveform data and native
        headers remain unchanged.

    Raises
    ------
    ImportError
        ObsPy is unavailable; install ``mermaid-geocsv[obspy]``.
    TypeError
        The waveform argument is not an ObsPy Trace or Stream, or
        allow_first_segment or create_sac_header is not a bool.
    ValueError
        Inputs, provenance, or destination containers are invalid, a trace has
        no unique eligible event row, or a requested projection is invalid.

    Notes
    -----
    Standard matches require complete, exact SNCL (only Location may be empty),
    zoned UTC-comparable times, nonempty loaded sample count equality, and rates
    within 0.00001 Hz. This is rate agreement, not physical clock accuracy.
    DataQuality is retained as source evidence, independent of waveform quality.
    Invalid event identities and duplicate complete SNCL/time/count/rate keys
    fail source preflight; multiple traces may independently use the same row.

    ``stats.geocsv`` preserves all source columns and adds ``dataset_index``,
    ``source_record_index``, immutable ``metadata``, and a nested ``association``
    AttribDict. Its ``type`` is ``single_segment`` or ``anchor_segment``. It
    snapshots ``waveform`` identity, start/end times, rate and count, and a
    chronological tuple of ``coverage_segments`` with complete source segment
    descriptions, dataset/record/line references and clipped waveform sample
    ranges [start, stop). The first segment supplies geographic metadata.
    ``waveform_start_offset_seconds`` is signed waveform minus anchor start.
    ``max_sample_grid_offset`` reports the largest absolute difference at the
    retained segment boundary samples, in seconds, with its source and waveform
    sample index. ``max_sample_rate_difference`` reports the largest absolute
    rate difference in hertz with its source. No tolerances are stored.
    Coverage boundaries use unique nearest-sample placement within half a
    waveform sample interval, independent of ``time_tolerance``. Source counts
    fix the range length: retained last-sample drift must also fit the same
    placement. Exact half-sample ties raise. Native times and samples are not
    shifted or interpolated; full coverage is still required. This resembles
    ObsPy record joining but compares source ranges to the assembled trace.
    All nested mappings, including coverage entries, support attribute access.
    These keys and ObsPy AttribDict attributes/methods are reserved against
    source-column collisions. Coordinates require latitude/longitude declared
    in degrees_north/degrees_east; elevation is the adopted sea-level reference
    0.0, with no geoid model. Zero is the same in metres and kilometres; no
    nonzero elevation unit convention is established here. Position refers to
    the source segment's first sample, not an average over the trace. For
    anchor_segment, the anchor's geographic metadata is adopted for the whole
    waveform under the MERMAID negligible-drift convention; raw fields still
    describe only the anchor row. Association guarantees end at initial
    attachment; later waveform processing does not refresh it. Optional SAC
    headers use the same anchor for either association label. ``stdp`` is
    WaterPressure[mbar]/100 in approximate metres, following automaid's
    convention, not a physical pressure-to-depth model. Missing REQ pressure
    (source DataQuality D) uses SAC undefined (-12345); pressure is never
    borrowed from another row. Only the four station location fields are
    added to ObsPy's fresh-header baseline. Other source fields remain in
    ``stats.geocsv``; calibration, response removal and counts-to-pressure
    conversion are outside scope. Samples are never scaled. Native waveform
    Stats are never replaced by values rounded through SAC conversion.
    ObsPy owns file writing, format precision and writer options; its default
    ``keep_sac_header=True`` preserves these headers. Passing False discards
    them. Header creation does not promise later export validation or serialize
    GeoCSV provenance. Publisher tooling owns export and round-trip verification.
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
