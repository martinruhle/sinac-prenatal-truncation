"""Tests for the pure SQL text helpers. They touch no database."""

from collections.abc import Sequence
from pathlib import Path

import pytest

from sinac_truncation.sqltext import (
    UnknownPlaceholderError,
    find_placeholders,
    is_valid_identifier,
    render_sql,
    schema_mapping,
)

SCHEMAS = schema_mapping(cdm="cdm", staging="staging", results="results")


def test_schema_mapping_covers_both_conventions() -> None:
    assert SCHEMAS["cdmDatabaseSchema"] == SCHEMAS["cdm_schema"] == "cdm"
    assert SCHEMAS["staging_schema"] == "staging"
    assert SCHEMAS["results_schema"] == "results"


def test_every_marker_is_replaced() -> None:
    sql = "SELECT * FROM @cdmDatabaseSchema.person, @staging_schema.births, @results_schema.n;"
    rendered = render_sql(sql, SCHEMAS)
    assert rendered == "SELECT * FROM cdm.person, staging.births, results.n;"
    assert find_placeholders(rendered) == frozenset()


def test_a_marker_that_is_a_prefix_of_another_is_not_corrupted() -> None:
    """@cdm_schema and @cdmDatabaseSchema share a prefix; one pass keeps them apart."""
    rendered = render_sql("@cdm_schema.a @cdmDatabaseSchema.b", schema_mapping("c", "s", "r"))
    assert rendered == "c.a c.b"


def test_text_without_markers_is_returned_unchanged() -> None:
    sql = "CREATE TABLE person (person_id integer NOT NULL);"
    assert render_sql(sql, SCHEMAS) == sql


def test_unknown_marker_raises_and_names_it() -> None:
    with pytest.raises(UnknownPlaceholderError, match="@vocabDatabaseSchema"):
        render_sql("SELECT 1 FROM @vocabDatabaseSchema.concept;", SCHEMAS)


def test_schema_name_that_is_not_an_identifier_raises() -> None:
    with pytest.raises(ValueError, match="bare SQL identifier"):
        render_sql("SELECT 1 FROM @cdm_schema.t;", {"cdm_schema": "cdm; DROP SCHEMA public"})


@pytest.mark.parametrize(
    ("name", "valid"),
    [
        ("cdm", True),
        ("test_cdm_0a1b2c3d", True),
        ("_private", True),
        ("", False),
        ("2cdm", False),
        ("cdm-schema", False),
        ("cdm schema", False),
        ('cdm"; --', False),
    ],
)
def test_is_valid_identifier(name: str, valid: bool) -> None:
    assert is_valid_identifier(name) is valid


def test_vendored_ddl_uses_only_the_expected_marker(ddl_files: Sequence[Path]) -> None:
    """An upstream file introducing a new marker must fail here, not against the database."""
    for path in ddl_files:
        assert find_placeholders(path.read_text(encoding="utf-8")) == frozenset(
            {"cdmDatabaseSchema"}
        )
