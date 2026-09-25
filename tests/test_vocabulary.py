"""Tests for the pure helpers of the vocabulary load. Synthetic values only; no package is read."""

import copy
from typing import Any

import pytest

from sinac_truncation.integrity import DigestResult
from sinac_truncation.vocabulary import (
    LOADED_TABLES,
    QUOTE,
    StreamTally,
    VocabularyError,
    digest_problem,
    header_problem,
    member_name,
    member_problems,
    package_from_manifest,
    version_from_lines,
)

SHA256 = "ab" * 32

BLOCK: dict[str, Any] = {
    "vocabulary": {
        "publisher": "Synthetic",
        "file": "data/raw/athena/2000-01-01/package.zip",
        "size_bytes": 1234,
        "sha256": SHA256.upper(),
        "vocabulary_version": "v5.0 SYNTH",
        "rows": {table: position for position, table in enumerate(LOADED_TABLES)},
        "not_loaded": ["CONCEPT_SYNONYM.csv"],
        "database_bytes": 99,
    }
}

LOADED_MEMBERS = [member_name(table) for table in LOADED_TABLES]


def _with(key: str, value: object) -> dict[str, Any]:
    document = copy.deepcopy(BLOCK)
    if value is None:
        del document["vocabulary"][key]
    else:
        document["vocabulary"][key] = value
    return document


def test_the_block_is_read_with_its_digest_normalised() -> None:
    package = package_from_manifest(BLOCK)
    assert package.sha256 == SHA256
    assert package.rows["concept"] == LOADED_TABLES.index("concept")
    assert package.not_loaded == ("CONCEPT_SYNONYM.csv",)


def test_member_names_are_the_table_names_in_upper_case() -> None:
    assert member_name("concept_relationship") == "CONCEPT_RELATIONSHIP.csv"


@pytest.mark.parametrize("document", [{}, {"vocabulary": []}, None, ["vocabulary"]])
def test_a_manifest_without_the_block_is_refused(document: object) -> None:
    with pytest.raises(VocabularyError, match="no `vocabulary:` block"):
        package_from_manifest(document)


@pytest.mark.parametrize(
    ("key", "value", "expected"),
    [
        ("file", None, "file is missing"),
        ("file", "/data/package.zip", "relative to the repository root"),
        ("file", "C:\\data\\package.zip", "relative to the repository root"),
        ("size_bytes", 0, "size_bytes must be a positive integer"),
        ("size_bytes", True, "size_bytes must be a positive integer"),
        ("sha256", "abc", "not a sha256"),
        ("vocabulary_version", "", "vocabulary_version is missing"),
        ("rows", {"concept": 1}, "rows must list exactly"),
        ("not_loaded", "CONCEPT_SYNONYM.csv", "not_loaded must be a list"),
    ],
)
def test_each_broken_field_is_refused(key: str, value: object, expected: str) -> None:
    with pytest.raises(VocabularyError, match=expected):
        package_from_manifest(_with(key, value))


@pytest.mark.parametrize("count", [-1, "10", None, 1.5])
def test_a_row_count_must_be_a_whole_number(count: object) -> None:
    rows = dict(BLOCK["vocabulary"]["rows"], concept=count)
    with pytest.raises(VocabularyError, match="rows of concept must be an integer"):
        package_from_manifest(_with("rows", rows))


def test_not_loaded_may_be_left_out() -> None:
    assert package_from_manifest(_with("not_loaded", None)).not_loaded == ()


def test_the_declared_zip_passes_and_any_other_is_refused() -> None:
    package = package_from_manifest(BLOCK)
    assert digest_problem(package, DigestResult(sha256=SHA256, size_bytes=1234)) is None

    problem = digest_problem(package, DigestResult(sha256="cd" * 32, size_bytes=1234))
    assert problem is not None
    assert "do not edit the hash to fit" in problem
    assert digest_problem(package, DigestResult(sha256=SHA256, size_bytes=1)) is not None


def test_a_package_with_every_declared_member_passes() -> None:
    assert member_problems([*LOADED_MEMBERS, "CONCEPT_SYNONYM.csv"], ["CONCEPT_SYNONYM.csv"]) == []


@pytest.mark.parametrize(
    ("names", "not_loaded", "expected"),
    [
        (LOADED_MEMBERS[1:], [], "VOCABULARY.csv is missing from the package"),
        ([*LOADED_MEMBERS, "NEW_TABLE.csv"], [], "NEW_TABLE.csv is in the package but neither"),
        (LOADED_MEMBERS, ["DRUG_STRENGTH.csv"], "DRUG_STRENGTH.csv is listed in not_loaded but"),
        (LOADED_MEMBERS, ["CONCEPT.csv"], "CONCEPT.csv is a loaded table"),
    ],
)
def test_each_member_mismatch_is_reported(
    names: list[str], not_loaded: list[str], expected: str
) -> None:
    problems = member_problems(names, not_loaded)
    assert any(expected in problem for problem in problems), problems


COLUMNS = ("domain_id", "domain_name", "domain_concept_id")


def test_a_header_naming_the_columns_in_order_passes() -> None:
    assert (
        header_problem("domain", "domain_id\tdomain_name\tdomain_concept_id\r\n", COLUMNS) is None
    )


@pytest.mark.parametrize(
    "header",
    [
        "domain_name\tdomain_id\tdomain_concept_id\n",
        "domain_id,domain_name,domain_concept_id\n",
        "\ufeffdomain_id\tdomain_name\tdomain_concept_id\n",
        "domain_id\tdomain_name\n",
    ],
)
def test_a_header_that_differs_is_reported(header: str) -> None:
    problem = header_problem("domain", header, COLUMNS)
    assert problem is not None
    assert problem.startswith("DOMAIN.csv has the columns")


VOCABULARY_LINES = [
    "vocabulary_id\tvocabulary_name\tvocabulary_reference\tvocabulary_version\tvocabulary_concept_id",
    "SYNTH\tSynthetic\tOMOP generated\tSYNTH 1.0\t2000000100",
    "None\tOMOP Standardized Vocabularies\tOMOP generated\tv5.0 SYNTH\t2000000101",
]


def test_the_version_is_the_one_of_the_none_row() -> None:
    assert version_from_lines(VOCABULARY_LINES) == "v5.0 SYNTH"


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        (VOCABULARY_LINES[:2], "found 0"),
        ([*VOCABULARY_LINES, VOCABULARY_LINES[2]], "found 2"),
        ([VOCABULARY_LINES[0], "None\tx\ty\t\t1"], "found 1"),
        (["vocabulary_id\tvocabulary_name"], "no vocabulary_id and vocabulary_version"),
        ([], "no vocabulary_id and vocabulary_version"),
    ],
)
def test_a_missing_or_ambiguous_version_is_refused(lines: list[str], expected: str) -> None:
    with pytest.raises(VocabularyError, match=expected):
        version_from_lines(lines)


def _tally(*chunks: bytes) -> StreamTally:
    tally = StreamTally()
    for chunk in chunks:
        tally.update(chunk)
    return tally


@pytest.mark.parametrize(
    "chunks",
    [
        (b"a\tb\n1\t2\n3\t4\n",),
        (b"a\tb\n1\t", b"2\n3", b"\t4\n"),
        (b"a\tb\n1\t2\n3\t4",),
        (b"a\tb\n", b"", b"1\t2\n3\t4\n"),
    ],
)
def test_the_tally_counts_data_rows_wherever_the_chunks_split(chunks: tuple[bytes, ...]) -> None:
    assert _tally(*chunks).records == 2


def test_an_empty_stream_or_a_header_alone_has_no_rows() -> None:
    assert _tally().records == 0
    assert _tally(b"a\tb\n").records == 0


def test_the_tally_counts_the_byte_copy_reads_as_a_quote() -> None:
    assert _tally(b'a\tb\n"quoted"\tname\n').quote_bytes == 0
    assert _tally(b"a\tb\n1\t" + QUOTE.encode() + b"\n").quote_bytes == 1
