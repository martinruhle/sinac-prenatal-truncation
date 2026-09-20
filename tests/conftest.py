"""Fixtures shared by the test suite.

The database fixtures skip when there is no database, so a clone without Docker still runs the
rest of the suite. ``REQUIRE_DB=1`` turns that skip into a failure, which is how CI makes sure
the database tests can never disappear silently.
"""

import os
import uuid
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path

import psycopg
import pytest

import pipeline
import sql_runner
from sinac_truncation.sqltext import schema_mapping


def _database_required() -> bool:
    return os.environ.get("REQUIRE_DB") == "1"


@pytest.fixture(scope="session")
def ddl_files() -> Sequence[Path]:
    """The vendored OHDSI files, in the order ``pipeline.py db-init`` applies them."""
    return pipeline.DDL_FILES


@pytest.fixture(scope="session")
def db_connection() -> Iterator[sql_runner.Connection]:
    """Connection to the compose database, or a skip when it is not there."""
    try:
        conninfo = sql_runner.conninfo_from_env()
    except sql_runner.MissingEnvironmentError as error:
        if _database_required():
            pytest.fail(f"REQUIRE_DB=1 but the database cannot be reached: {error}")
        pytest.skip(str(error))

    try:
        connection = psycopg.connect(conninfo)
    except psycopg.OperationalError as error:
        if _database_required():
            pytest.fail(f"REQUIRE_DB=1 but the database cannot be reached: {error}")
        pytest.skip(f"no database: {error}")

    with connection:
        yield connection


@pytest.fixture(scope="session")
def temp_schemas(db_connection: sql_runner.Connection) -> Iterator[Mapping[str, str]]:
    """Throwaway cdm, staging and results schemas, dropped when the session ends.

    The tests never touch the schemas `db-init` writes to, so running them cannot damage a
    loaded database.
    """
    suffix = uuid.uuid4().hex[:8]
    schemas = {
        "cdm": f"test_cdm_{suffix}",
        "staging": f"test_staging_{suffix}",
        "results": f"test_results_{suffix}",
    }
    sql_runner.ensure_schemas(db_connection, schemas.values())
    try:
        yield schemas
    finally:
        sql_runner.drop_schemas(db_connection, schemas.values())


@pytest.fixture(scope="session")
def omop_schema(
    db_connection: sql_runner.Connection,
    temp_schemas: Mapping[str, str],
    ddl_files: Sequence[Path],
) -> str:
    """Name of a temporary schema with the vendored OMOP CDM v5.4 DDL applied."""
    markers = schema_mapping(
        cdm=temp_schemas["cdm"],
        staging=temp_schemas["staging"],
        results=temp_schemas["results"],
    )
    sql_runner.run_sql_files(db_connection, ddl_files, markers)
    return temp_schemas["cdm"]
