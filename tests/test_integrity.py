"""Tests for the pure digest helpers. They touch no network, no database and no real data."""

import hashlib

import pytest

from sinac_truncation.integrity import (
    DigestResult,
    IntegrityError,
    digest_chunks,
    digests_match,
    mismatch_message,
    normalise_digest,
    version_from_url,
)

#: Synthetic bytes standing in for a downloaded file (D-016: CI never has the real one).
PAYLOAD = b"PK\x03\x04synthetic zip payload\x00\xff" * 40


def test_digest_matches_hashlib_over_the_whole_payload() -> None:
    result = digest_chunks([PAYLOAD])
    assert result.sha256 == hashlib.sha256(PAYLOAD).hexdigest()
    assert result.size_bytes == len(PAYLOAD)


def test_how_the_stream_is_split_does_not_change_the_result() -> None:
    """The downloader chunks by socket reads and the verifier by file reads; both must agree."""
    whole = digest_chunks([PAYLOAD])
    in_pieces = digest_chunks([PAYLOAD[i : i + 7] for i in range(0, len(PAYLOAD), 7)])
    byte_by_byte = digest_chunks([bytes([value]) for value in PAYLOAD])
    assert whole == in_pieces == byte_by_byte


def test_empty_stream_is_the_digest_of_nothing() -> None:
    result = digest_chunks([])
    assert result == DigestResult(sha256=hashlib.sha256(b"").hexdigest(), size_bytes=0)


def test_digest_is_normalised_for_comparison() -> None:
    digest = hashlib.sha256(PAYLOAD).hexdigest()
    assert digests_match(f"  {digest.upper()}  ", digest)


def test_different_payloads_do_not_match() -> None:
    assert not digests_match(
        hashlib.sha256(PAYLOAD).hexdigest(),
        hashlib.sha256(PAYLOAD + b"!").hexdigest(),
    )


@pytest.mark.parametrize(
    "value",
    [
        "",
        "not a digest",
        "abc123",  # too short: a hash truncated when it was copied
        "z" * 64,  # right length, not hexadecimal
        hashlib.sha256(PAYLOAD).hexdigest()[:-1],
    ],
)
def test_a_value_that_is_not_a_sha256_raises(value: str) -> None:
    with pytest.raises(IntegrityError, match="not a sha256 digest"):
        normalise_digest(value)


def test_normalise_digest_lower_cases() -> None:
    digest = hashlib.sha256(PAYLOAD).hexdigest()
    assert normalise_digest(digest.upper()) == digest


def test_mismatch_message_names_the_source_the_file_and_both_digests() -> None:
    expected = DigestResult(sha256="a" * 64, size_bytes=57_500_000)
    actual = DigestResult(sha256="b" * 64, size_bytes=57_499_999)
    message = mismatch_message(
        source_id="dgis_sinac_2023",
        location="data/raw/dgis/sinac_2023.zip",
        expected=expected,
        actual=actual,
    )
    assert "sha256 mismatch for dgis_sinac_2023" in message
    assert "data/raw/dgis/sinac_2023.zip" in message
    assert "a" * 64 in message
    assert "b" * 64 in message
    assert "57500000" in message
    assert "57499999" in message
    assert "config/sources.yml" in message


@pytest.mark.parametrize(
    ("url", "version"),
    [
        ("http://example.test/nacimientos/sinac_2023.zip?V=2024.05.14", "2024.05.14"),
        ("http://example.test/nacimientos/sinac_2019.zip?V=1.1", "1.1"),
        ("http://example.test/nacimientos/sinac_2023.zip", None),
        ("http://example.test/nacimientos/sinac_2023.zip?other=1", None),
        ("http://example.test/nacimientos/sinac_2023.zip?other=1&V=2024.05.14", "2024.05.14"),
    ],
)
def test_version_from_url(url: str, version: str | None) -> None:
    assert version_from_url(url) == version
