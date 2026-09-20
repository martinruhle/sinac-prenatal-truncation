"""Tests for the pure manifest patcher. Synthetic YAML only, no file is read or written."""

import textwrap

import pytest
import yaml

from sinac_truncation.manifest import ManifestError, record_fields

MANIFEST = textwrap.dedent(
    """\
    # A comment that must survive every edit.

    vendored:
      - name: something
        sha256: 0123456789abcdef

    downloads:
      - id: first_source
        url: http://example.test/first.zip?V=1.1
        notes: >-
          A folded note mentioning sha256: on purpose.
        # Written by --record.
        retrieved_at:
        size_bytes:
        sha256:
      - id: second_source
        url: http://example.test/second.zip?V=2.0
        retrieved_at:
        size_bytes:
        sha256:
    """
)

VALUES: dict[str, str | int] = {
    "sha256": "c" * 64,
    "size_bytes": 57_500_000,
    "retrieved_at": "2026-09-20T12:34:56Z",
}


def test_only_the_recorded_lines_change() -> None:
    patched = record_fields(MANIFEST, "first_source", VALUES)
    before = MANIFEST.splitlines()
    after = patched.splitlines()
    assert len(before) == len(after)
    changed = [line for old, line in zip(before, after, strict=True) if old != line]
    assert changed == [  # in the order of the file, not the order they were passed in
        '    retrieved_at: "2026-09-20T12:34:56Z"',
        "    size_bytes: 57500000",
        f'    sha256: "{"c" * 64}"',
    ]


def test_the_patched_text_parses_back_to_the_recorded_values() -> None:
    entry = yaml.safe_load(record_fields(MANIFEST, "first_source", VALUES))["downloads"][0]
    assert entry["id"] == "first_source"
    assert {key: entry[key] for key in VALUES} == VALUES


def test_a_timestamp_comes_back_as_a_string_not_a_datetime() -> None:
    """Unquoted, PyYAML would resolve an ISO timestamp to a datetime and the check would fail."""
    entry = yaml.safe_load(record_fields(MANIFEST, "first_source", VALUES))["downloads"][0]
    assert entry["retrieved_at"] == "2026-09-20T12:34:56Z"
    assert isinstance(entry["sha256"], str)


def test_the_other_entry_is_untouched() -> None:
    patched = yaml.safe_load(record_fields(MANIFEST, "first_source", VALUES))
    assert patched["downloads"][1] == yaml.safe_load(MANIFEST)["downloads"][1]


def test_each_entry_can_be_recorded_independently() -> None:
    once = record_fields(MANIFEST, "first_source", VALUES)
    twice = record_fields(once, "second_source", VALUES | {"size_bytes": 1})
    entries = yaml.safe_load(twice)["downloads"]
    assert entries[0]["size_bytes"] == 57_500_000
    assert entries[1]["size_bytes"] == 1


def test_an_unknown_entry_raises_and_lists_the_ids() -> None:
    with pytest.raises(ManifestError, match="first_source, second_source"):
        record_fields(MANIFEST, "missing_source", VALUES)


def test_a_duplicated_id_raises_instead_of_patching_the_first_one() -> None:
    doubled = MANIFEST.replace("second_source", "first_source")
    with pytest.raises(ManifestError, match="appears more than once"):
        record_fields(doubled, "first_source", VALUES)


def test_a_key_the_entry_does_not_have_raises() -> None:
    with pytest.raises(ManifestError, match="no key 'license'"):
        record_fields(MANIFEST, "first_source", {"license": "Apache-2.0"})


def test_a_key_that_already_holds_a_value_is_not_overwritten() -> None:
    recorded = record_fields(MANIFEST, "first_source", VALUES)
    with pytest.raises(ManifestError, match="already has sha256"):
        record_fields(recorded, "first_source", VALUES)


def test_a_key_of_another_block_is_not_reached() -> None:
    """`sha256` also exists under `vendored:` and inside a folded note; neither is a target."""
    patched = record_fields(MANIFEST, "first_source", {"sha256": "d" * 64})
    assert "sha256: 0123456789abcdef" in patched
    assert "A folded note mentioning sha256: on purpose." in patched


def test_recording_nothing_returns_the_text_unchanged() -> None:
    assert record_fields(MANIFEST, "first_source", {}) == MANIFEST


def test_line_endings_are_preserved() -> None:
    patched = record_fields(MANIFEST.replace("\n", "\r\n"), "first_source", VALUES)
    assert "\n" not in patched.replace("\r\n", "")


def test_a_key_repeated_inside_one_entry_raises() -> None:
    """Duplicated keys are legal YAML but the last one wins, so patching one is ambiguous."""
    repeated = MANIFEST.replace("    sha256:\n", "    sha256:\n    sha256:\n", 1)
    with pytest.raises(ManifestError, match="has key 'sha256' more than once"):
        record_fields(repeated, "first_source", VALUES)
