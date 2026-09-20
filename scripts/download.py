"""Downloading the source files and verifying them against ``config/sources.yml``.

The I/O of the download layer lives here (rule 6): reading and writing the manifest, the HTTP
request, the bytes on disk. The digest and the manifest edit themselves are pure and live in
:mod:`sinac_truncation.integrity` and :mod:`sinac_truncation.manifest`.

Two rules shape everything below. A file already on disk is verified, never downloaded again and
never overwritten; and a hash already recorded is verified, never rewritten (D-044).
"""

import os
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import yaml

from sinac_truncation.integrity import (
    DigestResult,
    IntegrityError,
    digest_chunks,
    digests_match,
    mismatch_message,
    normalise_digest,
    version_from_url,
)
from sinac_truncation.manifest import ManifestError, record_fields

#: Repository root, reached from this file so no absolute path is written down (rule 12).
REPO_ROOT = Path(__file__).resolve().parents[1]

SOURCES_PATH = REPO_ROOT / "config" / "sources.yml"

#: Downloads land here. `/data/` is ignored by git (D-038): nothing under it is ever committed.
RAW_DIR = REPO_ROOT / "data" / "raw" / "dgis"

#: The fields `--record` writes, in the order they are reported.
RECORDED = ("sha256", "size_bytes", "retrieved_at")

CHUNK_BYTES = 1024 * 1024
PROGRESS_BYTES = 10 * CHUNK_BYTES

#: The DGIS server is slow and serves plain HTTP, so a dead host fails fast while a slow transfer
#: is given room.
DEFAULT_TIMEOUT = 60.0
CONNECT_TIMEOUT = 15.0


class DownloadError(RuntimeError):
    """The download or the verification failed for a reason the user has to act on."""


@dataclass(frozen=True)
class SourceEntry:
    """One ``downloads:`` entry of the manifest, as the downloader needs it."""

    id: str
    url: str
    version: str
    sha256: str | None
    size_bytes: int | None

    @property
    def filename(self) -> str:
        """The name the file takes on disk: the last segment of the URL path, without ``?V=``."""
        return Path(httpx.URL(self.url).path).name

    @property
    def recorded(self) -> DigestResult | None:
        """What the manifest says this file is, or ``None`` when nothing was recorded yet."""
        if self.sha256 is None or self.size_bytes is None:
            return None
        return DigestResult(sha256=self.sha256, size_bytes=self.size_bytes)


def _downloads(document: Any) -> list[dict[str, Any]]:
    entries = (document or {}).get("downloads") or []
    if not isinstance(entries, list):
        raise DownloadError("the `downloads:` block of the manifest is not a list")
    return [entry for entry in entries if isinstance(entry, dict)]


def load_entry(path: Path, entry_id: str) -> SourceEntry:
    """Read one entry from the manifest and check it against itself.

    Raises:
        DownloadError: the file, the entry or a required field is missing, or the version field
            disagrees with the ``?V=`` of its own URL.
    """
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise DownloadError(f"no manifest at {path}") from error
    except yaml.YAMLError as error:
        raise DownloadError(f"{path} is not valid YAML: {error}") from error

    entries = _downloads(document)
    found = [entry for entry in entries if entry.get("id") == entry_id]
    if not found:
        known = ", ".join(str(entry.get("id")) for entry in entries) or "none"
        raise DownloadError(f"no source with id {entry_id!r} (ids in the manifest: {known})")
    entry = found[0]

    for field in ("url", "version"):
        if not entry.get(field):
            raise DownloadError(f"source {entry_id!r} has no {field}")

    url, version = str(entry["url"]), str(entry["version"])
    published = version_from_url(url)
    if published != version:
        raise DownloadError(
            f"source {entry_id!r} declares version {version!r} but its URL carries "
            f"{published!r}. Copy both from the source page; do not edit one of them."
        )

    size = entry.get("size_bytes")
    sha256 = entry.get("sha256")
    try:
        return SourceEntry(
            id=entry_id,
            url=url,
            version=version,
            sha256=None if sha256 is None else normalise_digest(str(sha256)),
            size_bytes=None if size is None else int(size),
        )
    except (IntegrityError, ValueError) as error:
        raise DownloadError(f"source {entry_id!r}: {error}") from error


def target_path(entry: SourceEntry, dest_dir: Path) -> Path:
    """Where this source is kept on disk."""
    return dest_dir / entry.filename


def _file_chunks(path: Path) -> Iterator[bytes]:
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_BYTES):
            yield chunk


def _shown(path: Path) -> str:
    """A path as the user sees it: relative to the repository root when it is inside it."""
    return path.relative_to(REPO_ROOT).as_posix() if path.is_relative_to(REPO_ROOT) else str(path)


def verify_file(path: Path, entry: SourceEntry) -> DigestResult:
    """Check a file on disk against the digest recorded in the manifest.

    Raises:
        DownloadError: nothing is recorded for this source, or the file does not match it.
    """
    recorded = entry.recorded
    if recorded is None:
        raise DownloadError(
            f"no sha256 recorded for {entry.id}: run once with --record to write the hash, "
            "the size and the retrieval date into config/sources.yml."
        )
    actual = digest_chunks(_file_chunks(path))
    if not digests_match(recorded.sha256, actual.sha256):
        raise DownloadError(
            mismatch_message(
                source_id=entry.id,
                location=_shown(path),
                expected=recorded,
                actual=actual,
            )
        )
    return actual


def fetch(entry: SourceEntry, path: Path, *, client: httpx.Client) -> DigestResult:
    """Stream the file to ``path``, digesting as it arrives.

    The bytes go to a ``.part`` file and are renamed onto ``path`` only once the digest is
    accepted, so an interrupted or corrupt download never leaves something that looks complete.
    """
    partial = path.with_name(f"{path.name}.part")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with client.stream("GET", entry.url, follow_redirects=True) as response:
            response.raise_for_status()
            if str(response.url) != entry.url:
                print(f"redirected to {response.url}")
            with partial.open("wb") as handle:

                def chunks() -> Iterator[bytes]:
                    reported = 0
                    for chunk in response.iter_bytes(CHUNK_BYTES):
                        handle.write(chunk)
                        if response.num_bytes_downloaded - reported >= PROGRESS_BYTES:
                            reported = response.num_bytes_downloaded
                            print(f"  {reported // CHUNK_BYTES} MiB")
                        yield chunk

                digest = digest_chunks(chunks())
    except httpx.HTTPError:
        partial.unlink(missing_ok=True)
        raise

    recorded = entry.recorded
    if recorded is not None and not digests_match(recorded.sha256, digest.sha256):
        partial.unlink(missing_ok=True)
        raise DownloadError(
            mismatch_message(
                source_id=entry.id,
                location=f"{entry.url} (the download was discarded)",
                expected=recorded,
                actual=digest,
            )
        )

    os.replace(partial, path)
    return digest


def record(path: Path, entry: SourceEntry, digest: DigestResult) -> None:
    """Write the digest, the size and the retrieval date into the manifest.

    The patched text is parsed again before it is written, so a bad patch cannot reach the file.
    """
    values: dict[str, str | int] = {
        "sha256": digest.sha256,
        "size_bytes": digest.size_bytes,
        "retrieved_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    try:
        patched = record_fields(path.read_text(encoding="utf-8"), entry.id, values)
    except ManifestError as error:
        raise DownloadError(f"{path.name}: {error}") from error

    written = [
        candidate
        for candidate in _downloads(yaml.safe_load(patched))
        if candidate.get("id") == entry.id
    ]
    if len(written) != 1 or any(written[0].get(key) != value for key, value in values.items()):
        raise DownloadError(
            f"the edit of {path.name} did not produce the recorded values, so the file was left "
            "as it was. This is a bug in the recorder, not a problem with the download."
        )

    path.write_text(patched, encoding="utf-8", newline="")
    for key in RECORDED:
        print(f"recorded {key}: {values[key]}")


def run(
    entry_id: str,
    *,
    record_digest: bool,
    dest_dir: Path = RAW_DIR,
    sources_path: Path = SOURCES_PATH,
    timeout: float = DEFAULT_TIMEOUT,
    client: httpx.Client | None = None,
) -> None:
    """Download or verify one source. See ``pipeline.py download --help``.

    Raises:
        DownloadError: anything the user has to decide about.
        httpx.HTTPError: the server could not be reached or refused the request.
    """
    entry = load_entry(sources_path, entry_id)
    path = target_path(entry, dest_dir)

    if path.exists():
        digest = verify_file(path, entry)
        print(f"verified {_shown(path)}: sha256 {digest.sha256}, {digest.size_bytes} bytes")
        return

    if record_digest and entry.recorded is not None:
        raise DownloadError(
            f"{entry_id} already has a recorded sha256, so --record has nothing to write. "
            "Run without --record to download and verify against it."
        )
    if not record_digest and entry.recorded is None:
        raise DownloadError(
            f"no sha256 recorded for {entry_id}: run once with --record to write the hash, "
            "the size and the retrieval date into config/sources.yml."
        )

    print(f"downloading {entry.url}")
    owned = client is None
    http = client or httpx.Client(timeout=httpx.Timeout(timeout, connect=CONNECT_TIMEOUT))
    try:
        digest = fetch(entry, path, client=http)
    finally:
        if owned:
            http.close()

    print(f"wrote {_shown(path)}: sha256 {digest.sha256}, {digest.size_bytes} bytes")
    if record_digest:
        record(sources_path, entry, digest)
    else:
        print(f"verified against the sha256 recorded for {entry_id}")
