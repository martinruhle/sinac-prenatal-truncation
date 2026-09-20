"""Tests for the download layer.

Nothing here reaches the network: the HTTP responses come from ``httpx.MockTransport`` and the
payload is synthetic, so CI downloads no data (D-016). The manifest is a small synthetic file in
``tmp_path``; the real ``config/sources.yml`` is never written to.
"""

import hashlib
import re
import textwrap
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest
import yaml

import download
import pipeline

PAYLOAD = b"PK\x03\x04synthetic zip payload\x00\xff" * 40
DIGEST = hashlib.sha256(PAYLOAD).hexdigest()
URL = "http://example.test/datosabiertos/nacimientos/sinac_2023.zip?V=2024.05.14"

MANIFEST = textwrap.dedent(
    f"""\
    downloads:
      - id: dgis_sinac_2023
        url: {URL}
        version: "2024.05.14"
        retrieved_at:
        size_bytes:
        sha256:
      - id: other_source
        url: http://example.test/other.zip?V=1.1
        version: "1.1"
        retrieved_at:
        size_bytes:
        sha256:
    """
)


@pytest.fixture
def manifest(tmp_path: Path) -> Path:
    path = tmp_path / "sources.yml"
    path.write_text(MANIFEST, encoding="utf-8")
    return path


@pytest.fixture
def dest(tmp_path: Path) -> Path:
    return tmp_path / "raw"


def client_serving(content: bytes = PAYLOAD, status: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, content=content)

    return httpx.Client(transport=httpx.MockTransport(handler))


def client_that_must_not_be_used() -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"the network was used for {request.url}")

    return httpx.Client(transport=httpx.MockTransport(handler))


def entry_of(manifest: Path, entry_id: str = "dgis_sinac_2023") -> dict[str, object]:
    entries = yaml.safe_load(manifest.read_text(encoding="utf-8"))["downloads"]
    return next(entry for entry in entries if entry["id"] == entry_id)


def record_run(manifest: Path, dest: Path, content: bytes = PAYLOAD) -> None:
    with client_serving(content) as client:
        download.run(
            "dgis_sinac_2023",
            record_digest=True,
            dest_dir=dest,
            sources_path=manifest,
            client=client,
        )


def test_record_writes_the_file_and_the_manifest(manifest: Path, dest: Path) -> None:
    record_run(manifest, dest)

    assert (dest / "sinac_2023.zip").read_bytes() == PAYLOAD
    entry = entry_of(manifest)
    assert entry["sha256"] == DIGEST
    assert entry["size_bytes"] == len(PAYLOAD)
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", str(entry["retrieved_at"]))


def test_the_query_string_never_reaches_the_file_name(manifest: Path, dest: Path) -> None:
    record_run(manifest, dest)
    assert [path.name for path in dest.iterdir()] == ["sinac_2023.zip"]


def test_a_second_run_verifies_without_downloading_again(manifest: Path, dest: Path) -> None:
    record_run(manifest, dest)
    before = (dest / "sinac_2023.zip").stat().st_mtime_ns

    with client_that_must_not_be_used() as client:
        download.run(
            "dgis_sinac_2023",
            record_digest=False,
            dest_dir=dest,
            sources_path=manifest,
            client=client,
        )

    assert (dest / "sinac_2023.zip").stat().st_mtime_ns == before


def test_a_corrupt_local_file_fails_with_both_digests(manifest: Path, dest: Path) -> None:
    record_run(manifest, dest)
    path = dest / "sinac_2023.zip"
    damaged = bytearray(PAYLOAD)
    damaged[1000] ^= 0xFF
    path.write_bytes(bytes(damaged))

    with pytest.raises(download.DownloadError) as error:
        download.run("dgis_sinac_2023", record_digest=False, dest_dir=dest, sources_path=manifest)

    message = str(error.value)
    assert "sha256 mismatch for dgis_sinac_2023" in message
    assert DIGEST in message
    assert hashlib.sha256(bytes(damaged)).hexdigest() in message
    assert path.read_bytes() == bytes(damaged), "a failed verification must not touch the file"


def test_a_download_that_does_not_match_leaves_nothing_behind(manifest: Path, dest: Path) -> None:
    record_run(manifest, dest)
    (dest / "sinac_2023.zip").unlink()

    with client_serving(PAYLOAD + b"tampered") as client, pytest.raises(download.DownloadError):
        download.run(
            "dgis_sinac_2023",
            record_digest=False,
            dest_dir=dest,
            sources_path=manifest,
            client=client,
        )

    assert list(dest.iterdir()) == [], "neither the file nor the .part may survive"


def test_verifying_without_a_recorded_hash_says_to_record_first(manifest: Path, dest: Path) -> None:
    with pytest.raises(download.DownloadError, match="run once with --record"):
        download.run("dgis_sinac_2023", record_digest=False, dest_dir=dest, sources_path=manifest)


def test_record_refuses_to_overwrite_a_recorded_hash(manifest: Path, dest: Path) -> None:
    record_run(manifest, dest)
    (dest / "sinac_2023.zip").unlink()

    with pytest.raises(download.DownloadError, match="already has a recorded sha256"):
        record_run(manifest, dest)


def test_an_unknown_id_lists_the_ids_of_the_manifest(manifest: Path, dest: Path) -> None:
    with pytest.raises(download.DownloadError, match="dgis_sinac_2023, other_source"):
        download.run("dgis_sinac_2019", record_digest=True, dest_dir=dest, sources_path=manifest)


def test_a_version_that_disagrees_with_its_own_url_is_refused(manifest: Path, dest: Path) -> None:
    manifest.write_text(MANIFEST.replace('"2024.05.14"', '"2025.06.24"', 1), encoding="utf-8")
    with pytest.raises(download.DownloadError, match="but its URL carries"):
        download.run("dgis_sinac_2023", record_digest=True, dest_dir=dest, sources_path=manifest)


def test_a_recorded_digest_that_is_not_a_sha256_is_refused(manifest: Path, dest: Path) -> None:
    manifest.write_text(MANIFEST.replace("sha256:\n", "sha256: deadbeef\n", 1), encoding="utf-8")
    with pytest.raises(download.DownloadError, match="not a sha256 digest"):
        download.run("dgis_sinac_2023", record_digest=False, dest_dir=dest, sources_path=manifest)


def test_a_missing_manifest_is_reported_as_such(tmp_path: Path, dest: Path) -> None:
    with pytest.raises(download.DownloadError, match="no manifest at"):
        download.run(
            "dgis_sinac_2023",
            record_digest=True,
            dest_dir=dest,
            sources_path=tmp_path / "absent.yml",
        )


def test_a_refused_request_raises_an_http_error(manifest: Path, dest: Path) -> None:
    with client_serving(b"not found", status=404) as client, pytest.raises(httpx.HTTPStatusError):
        download.run(
            "dgis_sinac_2023",
            record_digest=True,
            dest_dir=dest,
            sources_path=manifest,
            client=client,
        )

    assert not dest.exists() or list(dest.iterdir()) == []
    assert entry_of(manifest)["sha256"] is None, "a failed download records nothing"


def _stub(error: Exception) -> Callable[..., None]:
    def run(*args: object, **kwargs: object) -> None:
        raise error

    return run


def test_pipeline_returns_1_for_a_manifest_or_verification_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(download, "run", _stub(download.DownloadError("sha256 mismatch")))
    assert pipeline.main(["download", "--id", "dgis_sinac_2023"]) == 1
    assert "error: sha256 mismatch" in capsys.readouterr().err


def test_pipeline_returns_2_when_the_server_cannot_be_reached(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(download, "run", _stub(httpx.ConnectTimeout("timed out")))
    assert pipeline.main(["download", "--id", "dgis_sinac_2023"]) == 2
    assert "the download failed" in capsys.readouterr().err


def test_pipeline_passes_the_arguments_through(
    monkeypatch: pytest.MonkeyPatch, manifest: Path, dest: Path
) -> None:
    seen: dict[str, object] = {}

    def run(entry_id: str, **kwargs: object) -> None:
        seen.update(kwargs, entry_id=entry_id)

    monkeypatch.setattr(download, "run", run)
    assert pipeline.main(["download", "--id", "x", "--record", "--dest", str(dest)]) == 0
    assert seen == {
        "entry_id": "x",
        "record_digest": True,
        "dest_dir": dest,
        "timeout": download.DEFAULT_TIMEOUT,
    }


def test_download_needs_an_id() -> None:
    with pytest.raises(SystemExit):
        pipeline.main(["download"])
