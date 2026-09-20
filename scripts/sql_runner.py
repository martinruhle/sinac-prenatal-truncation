"""Applying SQL files to the project database.

The I/O of the SQL layer lives here (rule 6): reading the files, connecting, executing. The text
handling itself is pure and lives in :mod:`sinac_truncation.sqltext`.
"""

import os
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.rows import TupleRow

from sinac_truncation.sqltext import is_valid_identifier, render_sql

Connection = psycopg.Connection[TupleRow]

#: Variables without a sensible default. They come from `.env` locally (`uv run --env-file .env`)
#: and from the job environment in CI, so both paths read the same names.
REQUIRED_ENV = ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = "5432"


class MissingEnvironmentError(RuntimeError):
    """A variable needed to reach the database is not set."""


def conninfo_from_env(env: Mapping[str, str] | None = None) -> str:
    """Build a psycopg connection string from the environment.

    The host defaults to 127.0.0.1 because scripts run on the host and compose publishes the
    port there, in development and in CI alike.
    """
    env = os.environ if env is None else env
    missing = [name for name in REQUIRED_ENV if not env.get(name)]
    if missing:
        raise MissingEnvironmentError(
            f"missing environment variable(s): {', '.join(missing)}. "
            "Copy .env.example to .env and run with `uv run --env-file .env`."
        )
    return psycopg.conninfo.make_conninfo(
        host=env.get("POSTGRES_HOST") or DEFAULT_HOST,
        port=env.get("POSTGRES_PORT") or DEFAULT_PORT,
        user=env["POSTGRES_USER"],
        password=env["POSTGRES_PASSWORD"],
        dbname=env["POSTGRES_DB"],
    )


def _checked(name: str) -> sql.Identifier:
    """Validate a schema name and wrap it for safe composition."""
    if not is_valid_identifier(name):
        raise ValueError(f"not a bare SQL identifier: {name!r}")
    return sql.Identifier(name)


def ensure_schemas(conn: Connection, names: Iterable[str]) -> None:
    """Create the given schemas if they do not exist."""
    with conn.transaction(), conn.cursor() as cur:
        for name in names:
            cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(_checked(name)))


def drop_schemas(conn: Connection, names: Iterable[str]) -> None:
    """Drop the given schemas and everything in them. Destructive."""
    with conn.transaction(), conn.cursor() as cur:
        for name in names:
            cur.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(_checked(name)))


def count_tables(conn: Connection, schema: str) -> int:
    """Number of base tables in ``schema``."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema = %s AND table_type = 'BASE TABLE'",
            (schema,),
        )
        row = cur.fetchone()
    return 0 if row is None else int(row[0])


def run_sql_file(conn: Connection, path: Path, schemas: Mapping[str, str]) -> None:
    """Apply one SQL file with its markers resolved.

    The whole file is sent in a single ``execute()``: psycopg uses the simple query protocol when
    no parameters are passed, which accepts several statements at once, so no statement splitter
    is needed. The transaction makes a half-applied file impossible.
    """
    statements = render_sql(path.read_text(encoding="utf-8"), schemas)
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(statements)


def run_sql_files(conn: Connection, paths: Sequence[Path], schemas: Mapping[str, str]) -> None:
    """Apply several SQL files in the given order."""
    for path in paths:
        run_sql_file(conn, path, schemas)
