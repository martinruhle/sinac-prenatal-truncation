"""Pure integrity checks for the files this project downloads.

There is no file or network I/O here (CLAUDE.md rule 6): callers in ``scripts/`` produce the
bytes, from an HTTP response or from a file on disk, and these functions turn them into a digest
and compare it with the one recorded in ``config/sources.yml``.

The digest is the tripwire for a republication: DGIS serves these files over plain HTTP, so the
sha256 does not authenticate the first download, it only proves the bytes have not changed since
that download (D-016).
"""

import hashlib
import hmac
import re
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit

__all__ = [
    "DIGEST",
    "DigestResult",
    "IntegrityError",
    "digest_chunks",
    "digests_match",
    "mismatch_message",
    "normalise_digest",
    "version_from_url",
]

#: A sha256 as it is written in the manifest: 64 hexadecimal characters, nothing else.
DIGEST = re.compile(r"\A[0-9a-f]{64}\Z")

#: The query parameter DGIS publishes its file version under, as it appears in the download URL.
VERSION_PARAM = "V"


class IntegrityError(ValueError):
    """A digest is not a sha256, or two digests that had to be equal are not."""


@dataclass(frozen=True)
class DigestResult:
    """What one pass over a stream of bytes measured."""

    sha256: str
    size_bytes: int


def digest_chunks(chunks: Iterable[bytes]) -> DigestResult:
    """Hash and measure a stream of byte chunks in a single pass.

    The caller decides where the chunks come from, so the same function serves the download and
    the verification of a file already on disk. How the stream is split makes no difference to
    the result.
    """
    digest = hashlib.sha256()
    size = 0
    for chunk in chunks:
        digest.update(chunk)
        size += len(chunk)
    return DigestResult(sha256=digest.hexdigest(), size_bytes=size)


def normalise_digest(value: str) -> str:
    """Return ``value`` as a bare lower-case sha256.

    Raises:
        IntegrityError: it is not 64 hexadecimal characters. A digest that was truncated or
            mistyped in the manifest must fail here, not silently compare unequal later.
    """
    candidate = value.strip().lower()
    if DIGEST.match(candidate) is None:
        raise IntegrityError(f"not a sha256 digest: {value!r}")
    return candidate


def digests_match(expected: str, actual: str) -> bool:
    """Whether two sha256 digests are the same, ignoring case and surrounding blanks."""
    return hmac.compare_digest(normalise_digest(expected), normalise_digest(actual))


def mismatch_message(
    *,
    source_id: str,
    location: str,
    expected: DigestResult,
    actual: DigestResult,
) -> str:
    """The message a failed verification prints.

    It is built here, and not where the failure happens, so that what the user reads when a file
    is corrupt is covered by a unit test that needs no network and no data.
    """
    return (
        f"sha256 mismatch for {source_id}: {location}\n"
        f"  expected {expected.sha256} ({expected.size_bytes} bytes, from config/sources.yml)\n"
        f"  actual   {actual.sha256} ({actual.size_bytes} bytes)\n"
        "The file does not match the one that was recorded. Either it is damaged, or DGIS "
        "republished it: check the version on the source page before touching the manifest."
    )


def version_from_url(url: str) -> str | None:
    """The ``?V=`` value DGIS publishes in a download URL, or ``None`` when there is none.

    The manifest states that version in its own field; comparing the two catches an entry whose
    URL and version were edited apart, before anything is downloaded.
    """
    values = parse_qs(urlsplit(url).query).get(VERSION_PARAM)
    return values[0] if values else None
