"""The vendored OMOP CDM v5.4 DDL applies cleanly and leaves the tables this project needs.

The expected counts are read from the vendored files themselves, so an upstream change shows up
as a failure here instead of as a number quietly going stale in a test.
"""

from collections.abc import Sequence
from pathlib import Path

import pytest

import sql_runner

pytestmark = pytest.mark.db

TABLES = "OMOPCDM_postgresql_5.4_ddl.sql"
PRIMARY_KEYS = "OMOPCDM_postgresql_5.4_primary_keys.sql"
INDICES = "OMOPCDM_postgresql_5.4_indices.sql"

#: Tables this project will populate: the OMOP destinations in docs/roadmap.md ("Planned OMOP
#: mapping decisions"), plus the vocabulary tables the mapping relies on (D-032, rule 8).
TABLES_THE_PROJECT_POPULATES = (
    "person",
    "observation_period",
    "visit_occurrence",
    "measurement",
    "observation",
    "location",
    "care_site",
    "fact_relationship",
    "payer_plan_period",
    "concept",
    "source_to_concept_map",
)


def _ddl_file(ddl_files: Sequence[Path], name: str) -> Path:
    """Pick a vendored file by name: positional indexing would hide a missing file."""
    for path in ddl_files:
        if path.name == name:
            return path
    raise AssertionError(f"{name} is not among the files db-init applies")


def _statements(path: Path, prefix: str) -> int:
    """Count statements starting with ``prefix``, ignoring the lines upstream commented out."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return sum(1 for line in lines if line.strip().upper().startswith(prefix))


def _scalar(connection: sql_runner.Connection, query: str, *params: object) -> int:
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        row = cursor.fetchone()
    assert row is not None
    return int(row[0])


def test_every_table_of_the_ddl_is_created(
    db_connection: sql_runner.Connection, omop_schema: str, ddl_files: Sequence[Path]
) -> None:
    expected = _statements(_ddl_file(ddl_files, TABLES), "CREATE TABLE")
    assert sql_runner.count_tables(db_connection, omop_schema) == expected


@pytest.mark.parametrize("table", TABLES_THE_PROJECT_POPULATES)
def test_table_the_project_populates_exists(
    db_connection: sql_runner.Connection, omop_schema: str, table: str
) -> None:
    found = _scalar(
        db_connection,
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema = %s AND table_name = %s",
        omop_schema,
        table,
    )
    assert found == 1


def test_primary_keys_are_applied(
    db_connection: sql_runner.Connection, omop_schema: str, ddl_files: Sequence[Path]
) -> None:
    expected = _statements(_ddl_file(ddl_files, PRIMARY_KEYS), "ALTER TABLE")
    applied = _scalar(
        db_connection,
        "SELECT count(*) FROM pg_constraint c "
        "JOIN pg_class t ON t.oid = c.conrelid "
        "JOIN pg_namespace n ON n.oid = t.relnamespace "
        "WHERE n.nspname = %s AND c.contype = 'p'",
        omop_schema,
    )
    assert applied == expected


def test_indices_are_applied(
    db_connection: sql_runner.Connection, omop_schema: str, ddl_files: Sequence[Path]
) -> None:
    """Every index of the indices file, plus the one each primary key brings with it."""
    expected = _statements(_ddl_file(ddl_files, INDICES), "CREATE INDEX") + _statements(
        _ddl_file(ddl_files, PRIMARY_KEYS), "ALTER TABLE"
    )
    applied = _scalar(
        db_connection,
        "SELECT count(*) FROM pg_indexes WHERE schemaname = %s",
        omop_schema,
    )
    assert applied == expected


def test_foreign_keys_are_not_applied(
    db_connection: sql_runner.Connection, omop_schema: str
) -> None:
    """D-032: referential rules are anti-join checks in the ETL, not enforced constraints."""
    foreign_keys = _scalar(
        db_connection,
        "SELECT count(*) FROM pg_constraint c "
        "JOIN pg_class t ON t.oid = c.conrelid "
        "JOIN pg_namespace n ON n.oid = t.relnamespace "
        "WHERE n.nspname = %s AND c.contype = 'f'",
        omop_schema,
    )
    assert foreign_keys == 0
