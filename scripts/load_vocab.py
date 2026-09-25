"""Loading the OMOP standardized vocabularies from the Athena package into ``cdm``.

The I/O of the vocabulary layer lives here (rule 6): the manifest, the ZIP and Postgres. What is
checked, and how the stream is counted, is pure and lives in :mod:`sinac_truncation.vocabulary`.

The package is read straight from its ZIP and each file streams byte for byte into ``COPY``: nothing
is extracted and nothing in the vocabulary is rewritten (D-071). Every check that needs no table
rows runs before the first table is touched. The seven tables are then emptied and loaded in one
transaction, which commits only when the rows recorded in ``config/sources.yml``, the rows in the
file and the rows in the table agree (D-072), so a failed load leaves the previous one in place.

This step never runs in CI: the package is downloaded by hand and is never committed. The tests
load a small synthetic package instead.
"""

import time
import zipfile
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import IO

import psycopg
import yaml
from psycopg import Cursor, sql
from psycopg.rows import TupleRow

import download
import sql_runner
from sinac_truncation.integrity import digest_chunks
from sinac_truncation.staging import count_mismatch
from sinac_truncation.vocabulary import (
    DELIMITER,
    LOADED_TABLES,
    QUOTE,
    StreamTally,
    VocabularyError,
    VocabularyPackage,
    digest_problem,
    header_problem,
    member_name,
    member_problems,
    package_from_manifest,
    version_from_lines,
)

#: Repository root, reached from this file so no absolute path is written down (rule 12).
REPO_ROOT = Path(__file__).resolve().parents[1]

CHUNK_BYTES = 1024 * 1024

Cur = Cursor[TupleRow]


class VocabError(RuntimeError):
    """The vocabulary load stopped for a reason the user has to act on."""


@dataclass(frozen=True)
class TableLoad:
    """One loaded table as it is reported."""

    table: str
    rows: int
    seconds: float
    #: ``pg_total_relation_size``: the table with its indices, measured after ``ANALYZE``.
    size_bytes: int


def read_package(sources_path: Path = download.SOURCES_PATH) -> VocabularyPackage:
    """The ``vocabulary:`` block of the manifest, checked."""
    try:
        document = yaml.safe_load(sources_path.read_text(encoding="utf-8"))
        return package_from_manifest(document)
    except FileNotFoundError as error:
        raise VocabError(f"no manifest at {sources_path}") from error
    except yaml.YAMLError as error:
        raise VocabError(f"{sources_path} is not valid YAML: {error}") from error
    except VocabularyError as error:
        raise VocabError(f"{sources_path.name}: {error}") from error


def _chunks(handle: IO[bytes]) -> Iterator[bytes]:
    while chunk := handle.read(CHUNK_BYTES):
        yield chunk


def verify_package(path: Path, package: VocabularyPackage) -> None:
    """Check the ZIP on disk against the sha256 and the size the manifest records."""
    if not path.exists():
        raise VocabError(
            f"{package.file} is not on disk. Athena packages are downloaded by hand: put the "
            "ZIP there, as config/sources.yml declares it."
        )
    with path.open("rb") as handle:
        problem = digest_problem(package, digest_chunks(_chunks(handle)))
    if problem is not None:
        raise VocabError(problem)


def table_columns(conn: sql_runner.Connection, schema: str) -> dict[str, list[str]]:
    """The columns of each vocabulary table in ``schema``, in table order.

    Read in a transaction of its own, so the load that follows is a transaction of its own too.
    """
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = ANY(%s) "
            "ORDER BY table_name, ordinal_position",
            (schema, list(LOADED_TABLES)),
        )
        columns: dict[str, list[str]] = {}
        for table, column in cur.fetchall():
            columns.setdefault(str(table), []).append(str(column))
    missing = [table for table in LOADED_TABLES if table not in columns]
    if missing:
        raise VocabError(
            f"schema {schema!r} has no {', '.join(missing)} table: run `pipeline.py db-init` first"
        )
    return columns


def _first_line(archive: zipfile.ZipFile, name: str) -> str:
    with archive.open(name) as member:
        return member.readline().decode("utf-8")


def _lines(archive: zipfile.ZipFile, name: str) -> list[str]:
    with archive.open(name) as member:
        return member.read().decode("utf-8").splitlines()


def preflight(
    archive: zipfile.ZipFile, package: VocabularyPackage, columns: Mapping[str, Sequence[str]]
) -> None:
    """Every check that reads no more than the headers and VOCABULARY, before a table is touched.

    Raises:
        VocabError: a member is missing or undeclared, a header does not name its table's columns,
            or the package carries another vocabulary version than the manifest.
    """
    problems = member_problems(archive.namelist(), package.not_loaded)
    if not problems:
        for table in LOADED_TABLES:
            problem = header_problem(
                table, _first_line(archive, member_name(table)), columns[table]
            )
            if problem is not None:
                problems.append(problem)
    if not problems:
        version = version_from_lines(_lines(archive, member_name("vocabulary")))
        if version != package.vocabulary_version:
            problems.append(
                f"the package is vocabulary version {version!r}; config/sources.yml declares "
                f"{package.vocabulary_version!r}"
            )
    if problems:
        listed = "\n  ".join(problems)
        raise VocabError(f"{package.file} cannot be loaded; nothing was touched.\n  {listed}")


def _copy_member(cur: Cur, table: sql.Identifier, archive: zipfile.ZipFile, name: str) -> int:
    """Stream one member into its table unchanged, and return the data rows the file held.

    ``QUOTE`` names a byte Athena never writes, which turns CSV quoting off while keeping an empty
    field NULL; ``HEADER MATCH`` has the server refuse a header that does not name the columns.
    """
    statement = sql.SQL(
        "COPY {} FROM STDIN (FORMAT csv, DELIMITER {}, QUOTE {}, HEADER MATCH, ENCODING 'UTF8')"
    ).format(table, sql.Literal(DELIMITER), sql.Literal(QUOTE))
    tally = StreamTally()
    with archive.open(name) as member, cur.copy(statement) as copy:
        for chunk in _chunks(member):
            tally.update(chunk)
            copy.write(chunk)
    if tally.quote_bytes:
        raise VocabError(
            f"{name} holds {tally.quote_bytes} backspace bytes, the character COPY was told to "
            "read as a quote, so some values may have been rewritten. The previous load was "
            "kept: the package format has to be looked at before it is loaded."
        )
    return tally.records


def _scalar(cur: Cur, query: sql.SQL | sql.Composed, params: Sequence[object] = ()) -> int:
    cur.execute(query, params)
    row = cur.fetchone()
    return 0 if row is None else int(row[0])


def load(
    conn: sql_runner.Connection,
    archive: zipfile.ZipFile,
    package: VocabularyPackage,
    *,
    schema: str,
) -> list[tuple[str, int, float]]:
    """Empty the seven tables and load them, in one transaction.

    Returns:
        Each table with its rows and the seconds its ``COPY`` and count took.
    """
    tables = {table: sql.Identifier(schema, table) for table in LOADED_TABLES}
    loaded: list[tuple[str, int, float]] = []
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(sql.SQL("TRUNCATE {}").format(sql.SQL(", ").join(tables.values())))
        for table, identifier in tables.items():
            start = time.perf_counter()
            file_rows = _copy_member(cur, identifier, archive, member_name(table))
            table_rows = _scalar(cur, sql.SQL("SELECT count(*) FROM {}").format(identifier))
            counts = {
                "config/sources.yml": package.rows[table],
                "file": file_rows,
                "table": table_rows,
            }
            mismatch = count_mismatch(counts)
            if mismatch is not None:
                raise VocabError(f"{table}: {mismatch}. The previous load was kept.")
            seconds = time.perf_counter() - start
            print(f"{table:<22}{table_rows:>14,} rows  {seconds:7.1f} s")
            loaded.append((table, table_rows, seconds))
    return loaded


def analyze(conn: sql_runner.Connection, schema: str) -> dict[str, int]:
    """Refresh the planner statistics, and measure each table with its indices."""
    sizes: dict[str, int] = {}
    with conn.transaction(), conn.cursor() as cur:
        for table in LOADED_TABLES:
            identifier = sql.Identifier(schema, table)
            cur.execute(sql.SQL("ANALYZE {}").format(identifier))
            sizes[table] = _scalar(
                cur, sql.SQL("SELECT pg_total_relation_size(%s::regclass)"), [f"{schema}.{table}"]
            )
    return sizes


def report(loads: Sequence[TableLoad], package: VocabularyPackage, *, schema: str) -> None:
    """Print each table's rows and size on disk, and the totals."""
    print(f"\n{schema + ' table':<22}{'rows':>14}  {'bytes on disk':>15}")
    for entry in loads:
        print(f"{entry.table:<22}{entry.rows:>14,}  {entry.size_bytes:>15,}")
    rows = sum(entry.rows for entry in loads)
    size = sum(entry.size_bytes for entry in loads)
    print(f"{'total':<22}{rows:>14,}  {size:>15,}")
    print(
        f"vocabulary version {package.vocabulary_version!r} from {package.file} "
        f"({package.size_bytes:,} bytes on disk)"
    )


def run(
    conn: sql_runner.Connection,
    *,
    schema: str,
    sources_path: Path = download.SOURCES_PATH,
    repo_root: Path = REPO_ROOT,
) -> list[TableLoad]:
    """Load the package the manifest declares. See ``pipeline.py vocab --help``.

    Raises:
        VocabError: anything the user has to decide about. The tables keep their previous
            content whenever it is raised.
    """
    package = read_package(sources_path)
    path = repo_root / package.file
    verify_package(path, package)
    print(f"verified {package.file}: sha256 {package.sha256[:12]}, {package.size_bytes:,} bytes")

    try:
        with zipfile.ZipFile(path) as archive:
            preflight(archive, package, table_columns(conn, schema))
            loaded = load(conn, archive, package, schema=schema)
    except (zipfile.BadZipFile, VocabularyError, UnicodeDecodeError) as error:
        raise VocabError(f"{package.file}: {error}. The previous load was kept.") from error
    except (psycopg.errors.DataError, psycopg.errors.IntegrityError) as error:
        raise VocabError(
            f"COPY refused the package: {str(error).strip()}. The previous load was kept."
        ) from error

    sizes = analyze(conn, schema)
    loads = [
        TableLoad(table=table, rows=rows, seconds=seconds, size_bytes=sizes[table])
        for table, rows, seconds in loaded
    ]
    report(loads, package, schema=schema)
    return loads
