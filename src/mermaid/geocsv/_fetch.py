"""Retrieve immutable GeoCSV releases using their published manifests."""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass
from http.client import HTTPException
from os import PathLike
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen


class GeoCSVFetchError(RuntimeError):
    """A download, release manifest, or file integrity check failed."""


@dataclass(frozen=True)
class GeoCSVDownload:
    """Immutable retrieval provenance, without retaining the GeoCSV payload.

    ``url`` and ``manifest_url`` are the requested file and manifest URLs.
    ``manifest`` retains the exact UTF-8 JSON response bytes, including source
    provenance and the complete release inventory. ``size_bytes`` and
    ``sha256`` describe the verified, uncompressed GeoCSV bytes. The checksum
    verifies integrity against the publisher's manifest, not authenticity.
    ``testing_only`` distinguishes a test collection from scientific releases.
    """

    instrument_id: str
    release_id: str
    url: str
    manifest_url: str
    size_bytes: int
    sha256: str
    testing_only: bool
    manifest: bytes

    def __deepcopy__(self, memo: dict) -> GeoCSVDownload:
        return self


@dataclass(frozen=True)
class GeoCSVFetchResult:
    """One verified download, saved at ``path`` or retained as ``content``.

    Exactly one of ``path`` (an absolute Path) and ``content`` (bytes) is set.
    ``provenance`` records the selected release and its original manifest.
    Pass a result, or the result list from :func:`fetch`, to :func:`read` to
    retain that provenance on freshly parsed tables. Reading a bare saved path
    records only local provenance; it does not discover adjacent manifests.
    """

    provenance: GeoCSVDownload
    path: Path | None = None
    content: bytes | None = None

    def __post_init__(self) -> None:
        if (self.path is None) == (self.content is None):
            raise ValueError("a fetch result requires exactly one of path and content")


def fetch(
    instrument_ids: str | Sequence[str] | None = None,
    *,
    base_url: str,
    output_dir: str | PathLike[str] | None = ".",
    release: str | None = None,
    timeout: float = 30,
) -> list[GeoCSVFetchResult]:
    """Fetch one, selected, or all GeoCSV files from a manifest-based release.

    Parameters
    ----------
    instrument_ids : str or sequence of str, optional
        Exact, case-sensitive manifest identifiers. Omit or pass None to fetch
        every file in manifest order. A selection retains the requested order;
        empty or repeated selections raise ValueError. Missing identifiers
        raise GeoCSVFetchError before any file download or directory creation.
    base_url : str
        HTTP(S) collection URL containing ``latest.json`` and ``releases/``.
        Required while production hosting is undecided. A trailing slash is
        optional. HTTP supports local testing; use HTTPS for public hosting.
    output_dir : path-like or None, optional
        Default "." saves files and the original ``manifest.json`` beneath
        ``<output_dir>/<release_id>/``. Missing directories are created.
        None retains file bytes and manifests in memory without writing files.
        Existing identical files are verified and reused; differing files or
        manifests raise FileExistsError and are never overwritten. There is no
        implicit persistent cache or discovery of previously saved releases.
    release : str, optional
        An explicit release ID bypasses latest. None resolves latest once for
        the whole operation. Unavailable releases never fall back to another.
    timeout : float, optional
        Positive finite socket timeout in seconds, default 30; not a total
        batch deadline. Downloads are sequential.

    Returns
    -------
    list of GeoCSVFetchResult
        Always a list, including for one file. Every file is checked against
        the manifest's byte count and SHA-256 before acceptance. Disk downloads
        use a temporary file so incomplete payloads are never accepted.

    Raises
    ------
    GeoCSVFetchError
        Network failure, malformed/inconsistent manifest, missing instrument,
        or file integrity failure. Errors identify the affected URL or float.
        On batch failure no partial list is returned; earlier verified files
        saved to disk remain available, together with the manifest.
    ValueError, TypeError
        Invalid arguments.
    OSError
        Local filesystem failure, including conflicting existing outputs.

    Notes
    -----
    This retrieves bytes without parsing or changing scientific content.
    Memory-only batches retain the complete selected payload; parsing and
    retaining pandas tables can require substantially more memory.
    """
    base = urlsplit(base_url)
    if base.scheme not in {"http", "https"} or not base.netloc or base.query or base.fragment:
        raise ValueError("base_url must be an HTTP(S) collection URL without query or fragment")
    base_url = base_url.rstrip("/") + "/"
    if isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be positive and finite")
    if instrument_ids is None:
        requested = None
    else:
        if isinstance(instrument_ids, str):
            requested = [instrument_ids]
        elif isinstance(instrument_ids, Sequence):
            requested = list(instrument_ids)
        else:
            raise TypeError("instrument_ids must be a string, sequence of strings, or None")
        if not requested or any(not isinstance(item, str) or not item for item in requested):
            raise ValueError("instrument_ids must contain nonempty strings")
        if len(set(requested)) != len(requested):
            raise ValueError("instrument_ids must not contain duplicates")

    pointer = None
    if release is None:
        pointer, _ = _get_json(urljoin(base_url, "latest.json"), timeout)
        release = pointer.get("release_id")
        _check_component(release, "latest release_id")
        if pointer.get("manifest") != f"releases/{release}/manifest.json":
            raise GeoCSVFetchError("latest manifest path must identify its selected release")
    else:
        if not _is_component(release):
            raise ValueError("release must be a nonempty, plain URL path component")

    manifest_url = urljoin(base_url, f"releases/{release}/manifest.json")
    manifest, manifest_bytes = _get_json(manifest_url, timeout)
    entries = _check_manifest(manifest, release, manifest_url)
    if pointer is not None and (type(pointer.get("testing_only")) is not bool
                                or pointer["testing_only"] != manifest["testing_only"]):
        raise GeoCSVFetchError("latest and manifest testing_only flags must agree")
    by_instrument = {entry["instrument_id"]: entry for entry in entries}
    if requested is not None:
        missing = [item for item in requested if item not in by_instrument]
        if missing:
            raise GeoCSVFetchError(f"release {release}: instruments not found: {missing}")
        entries = [by_instrument[item] for item in requested]

    directory = None
    if output_dir is not None:
        directory = Path(output_dir).resolve() / release
        directory.mkdir(parents=True, exist_ok=True)
        manifest_path = directory / "manifest.json"
        if manifest_path.exists():
            if manifest_path.read_bytes() != manifest_bytes:
                raise FileExistsError(f"different manifest already exists: {manifest_path}")
        else:
            with manifest_path.open("xb") as stream:
                stream.write(manifest_bytes)

    results = []
    for entry in entries:
        url = urljoin(manifest_url, entry["filename"])
        provenance = GeoCSVDownload(
            instrument_id=entry["instrument_id"], release_id=release,
            url=url, manifest_url=manifest_url,
            size_bytes=entry["size_bytes"], sha256=entry["sha256"],
            testing_only=manifest["testing_only"], manifest=manifest_bytes,
        )
        try:
            if directory is None:
                with io.BytesIO() as stream:
                    _download(url, stream, provenance, timeout)
                    content = stream.getvalue()
                results.append(GeoCSVFetchResult(provenance, content=content))
            else:
                path = directory / entry["filename"]
                if path.exists():
                    try:
                        _verify_file(path, provenance)
                    except GeoCSVFetchError as exc:
                        raise FileExistsError(f"different file already exists: {path}") from exc
                else:
                    # Temporary output stays on the same filesystem. Linking
                    # accepts it without replacing a file created meanwhile.
                    with NamedTemporaryFile(dir=directory, prefix=".geocsv-", delete=False) as stream:
                        temporary = Path(stream.name)
                        try:
                            _download(url, stream, provenance, timeout)
                            stream.close()
                            os.link(temporary, path)
                        finally:
                            temporary.unlink()
                results.append(GeoCSVFetchResult(provenance, path=path))
        except GeoCSVFetchError as exc:
            raise GeoCSVFetchError(f"{entry['instrument_id']}: {exc}") from exc
    return results


def _is_component(value) -> bool:
    return (isinstance(value, str) and value not in {".", ".."}
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value) is not None)


def _check_component(value, label: str) -> None:
    if not _is_component(value):
        raise GeoCSVFetchError(f"{label} must be a nonempty, plain URL path component")


def _get_json(url: str, timeout: float) -> tuple[dict, bytes]:
    try:
        with urlopen(Request(url, headers={"Accept-Encoding": "identity"}), timeout=timeout) as response:
            content = response.read()
    except (OSError, HTTPException) as exc:
        raise GeoCSVFetchError(f"{url}: {exc}") from exc
    try:
        value = json.loads(content.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise GeoCSVFetchError(f"{url}: invalid UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise GeoCSVFetchError(f"{url}: expected a JSON object")
    return value, content


def _check_manifest(manifest: dict, release: str, url: str) -> list[dict]:
    if manifest.get("release_id") != release:
        raise GeoCSVFetchError(f"{url}: manifest release_id does not match {release}")
    if type(manifest.get("testing_only")) is not bool:
        raise GeoCSVFetchError(f"{url}: manifest requires a boolean testing_only")
    entries = manifest.get("files")
    if not isinstance(entries, list):
        raise GeoCSVFetchError(f"{url}: manifest requires a files array")
    instruments, filenames = set(), set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise GeoCSVFetchError(f"{url}: every file entry must be an object")
        instrument = entry.get("instrument_id")
        if not isinstance(instrument, str) or not instrument:
            raise GeoCSVFetchError(f"{url}: file requires a nonempty instrument_id")
        filename = entry.get("filename")
        _check_component(filename, f"{url}: filename")
        if filename == "manifest.json":
            raise GeoCSVFetchError(f"{url}: filename collides with manifest.json")
        if instrument in instruments or filename in filenames:
            raise GeoCSVFetchError(f"{url}: duplicate instrument_id or filename")
        instruments.add(instrument)
        filenames.add(filename)
        if type(entry.get("size_bytes")) is not int or entry["size_bytes"] < 0:
            raise GeoCSVFetchError(f"{url}: {instrument}: size_bytes must be a nonnegative integer")
        checksum = entry.get("sha256")
        if not isinstance(checksum, str) or re.fullmatch(r"[0-9a-f]{64}", checksum) is None:
            raise GeoCSVFetchError(f"{url}: {instrument}: sha256 must be 64 lowercase hex digits")
        if not isinstance(entry.get("provenance"), dict):
            raise GeoCSVFetchError(f"{url}: {instrument}: file requires a provenance object")
    return entries


def _check_integrity(size: int, checksum: str, provenance: GeoCSVDownload) -> None:
    if size != provenance.size_bytes:
        raise GeoCSVFetchError(
            f"{provenance.url}: byte count {size} does not match {provenance.size_bytes}")
    if checksum != provenance.sha256:
        raise GeoCSVFetchError(f"{provenance.url}: SHA-256 does not match manifest")


def _verify_file(path: Path, provenance: GeoCSVDownload) -> None:
    with path.open("rb") as stream:
        checksum = hashlib.file_digest(stream, "sha256").hexdigest()
        size = os.fstat(stream.fileno()).st_size
    _check_integrity(size, checksum, provenance)


def _download(url: str, stream, provenance: GeoCSVDownload, timeout: float) -> None:
    checksum = hashlib.sha256()
    size = 0
    try:
        response = urlopen(Request(url, headers={"Accept-Encoding": "identity"}), timeout=timeout)
    except (OSError, HTTPException) as exc:
        raise GeoCSVFetchError(f"{url}: {exc}") from exc
    with response:
        while True:
            try:
                chunk = response.read(1024 * 1024)
            except (OSError, HTTPException) as exc:
                raise GeoCSVFetchError(f"{url}: {exc}") from exc
            if not chunk:
                break
            size += len(chunk)
            if size > provenance.size_bytes:
                raise GeoCSVFetchError(f"{url}: byte count exceeds {provenance.size_bytes}")
            checksum.update(chunk)
            stream.write(chunk)
    _check_integrity(size, checksum.hexdigest(), provenance)
