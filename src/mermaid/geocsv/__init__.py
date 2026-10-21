# Bathymetrix®
# https://bathymetrix.com
# © 2026 Bathymetrix, LLC
# Author: Joel D. Simon <jdsimon@bathymetrix.com>
# SPDX-License-Identifier: MIT

"""Fetch and read MERMAID GeoCSV, associate waveforms, and write located SAC files."""

from ._fetch import GeoCSVDownload, GeoCSVFetchError, GeoCSVFetchResult, fetch
from .read import GeoCSVComment, GeoCSVError, GeoCSVMetadata, read

__author__ = "Joel D. Simon <jdsimon@bathymetrix.com>"
__license__ = "MIT"
__copyright__ = "© 2026 Bathymetrix, LLC"
__version__ = "0.20.0"

__all__ = [
    "__version__",
    "read",
    "fetch",
    "associate",
    "write_sac",
    "GeoCSVError",
    "GeoCSVComment",
    "GeoCSVMetadata",
    "GeoCSVDownload",
    "GeoCSVFetchError",
    "GeoCSVFetchResult",
]


def associate(waveforms, records, *, time_tolerance=0.0001, allow_first_segment=False):
    """Attach uniquely matched GeoCSV event metadata to ObsPy waveforms.

    Parameters
    ----------
    waveforms : obspy.Trace or obspy.Stream
        MiniSEED-derived waveforms with loaded samples. Modified in
        place only after every match and projection validates. The destinations
        ``stats.geocsv`` and ``stats.coordinates`` must be absent.
    records : list of pandas.DataFrame
        Tables returned by :func:`read`, retaining their source indices and
        immutable ``frame.attrs["geocsv"]`` provenance. May span datasets/files.
    time_tolerance : float, optional
        Inclusive absolute timing tolerance in seconds. Default is 0.0001
        (100 microseconds); zero requires exact matching. Must be finite and
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
        The waveform argument is not an ObsPy Trace or Stream, or
        allow_first_segment is not a bool.
    ValueError
        Inputs, provenance, or destination containers are invalid, a trace has
        no unique eligible event row, or a coordinate projection is incomplete.

    Notes
    -----
    Standard matches require complete, exact SNCL (only Location may be empty),
    zoned UTC-comparable times, nonempty loaded sample count equality, and rates
    within 0.01 Hz. This rate threshold is provisional scientific policy.
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
    attachment; later waveform processing does not refresh it. Use :func:`write_sac` separately
    to export either association with geographic SAC headers.
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
                      allow_first_segment=allow_first_segment)


def write_sac(trace, path):
    """Write one associated waveform to a new binary SAC file.

    Parameters
    ----------
    trace : obspy.Trace
        MiniSEED-derived trace with loaded, unmasked, finite real samples and
        a ``single_segment`` or ``anchor_segment`` attachment from :func:`associate`.
        Associate the final downloaded/clipped/combined window before export.
    path : str or os.PathLike
        Explicit output filename in an existing directory. Must not exist.

    Returns
    -------
    None
        The input trace, including any existing ``stats.sac``, is unchanged.

    Raises
    ------
    ImportError
        ObsPy is unavailable; install ``mermaid-geocsv[obspy]``.
    TypeError
        The waveform argument is not one ObsPy Trace.
    ValueError
        Association, waveform consistency, required coordinates, pressure,
        declared units, or SAC storage representations are invalid.
        Missing pressure is allowed only for
        REQ source records, identified by source ``DataQuality="D"``.
    FileExistsError
        The output path already exists; it is never overwritten.
    OSError
        The output cannot be created or written. An I/O failure can leave a
        partial output file.

    Notes
    -----
    Fresh SAC headers are constructed using ObsPy's SACTrace, ignoring any
    existing SAC headers and ``stats.coordinates``. ``stla``/``stlo`` come
    from attached GeoCSV Latitude/Longitude in degrees_north/degrees_east;
    ``stel=0`` adopts sea level. ``stdp=WaterPressure/100`` requires mbar and
    reproduces automaid's approximate convention of 1 dbar as 1 metre, not a
    physical pressure-to-depth calculation. Missing REQ pressure leaves stdp
    undefined (SAC -12345). No GeoCSV source file is reopened.

    ObsPy supplies waveform identity, timing, sampling and default headers.
    Binary SAC stores samples and floating headers at float32 precision;
    nonfinite samples, overflow, and nonzero values lost to zero are rejected.
    Identity codes must fit eight ASCII bytes without padding or SAC null tokens.
    Export does not apply calibration. Other automaid headers are not
    reconstructed, and GeoCSV provenance is not serialized into SAC.
    Identity, start, sample count and source rate agreement are checked, but
    these checks cannot establish an unmodified sample history. For
    anchor_segment, anchor geography and approximate depth describe the whole
    waveform by the MERMAID negligible-drift convention. Each call writes one file;
    loop over a Stream with explicit distinct paths for multiple traces.
    """
    try:
        from ._write_sac import write_sac as _write_sac
    except ModuleNotFoundError as exc:
        if exc.name != "obspy":
            raise
        raise ImportError(
            "GeoCSV SAC writing requires ObsPy; install it with "
            "pip install 'mermaid-geocsv[obspy]'"
        ) from exc
    return _write_sac(trace, path)
