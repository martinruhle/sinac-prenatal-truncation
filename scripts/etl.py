"""Populating the CDM tables of the vertical slice from ``staging`` (task 1.4.4).

The I/O of the ETL lives here (rule 6): the configuration, the manifest, git and Postgres. Every
rule of the mapping is SQL, in ``sql/etl/``; what can be decided from text alone lives in
:mod:`sinac_truncation.etl`.

A run first checks what it needs, before it touches anything: the configuration, the manifest,
the loaded vocabulary and the staged years. It then empties the populated tables and refills them
in one transaction, with ``INSERT … SELECT`` inside the database. The transaction commits only when
no record stops the load and every post-load check counts 0; otherwise the previous load stays as
it was (D-073). The CDM then holds exactly the years of the run.
"""

import subprocess
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import psycopg
from psycopg import Cursor, sql
from psycopg.rows import TupleRow

import download
import load_vocab
import sql_runner
import validate_concepts
from sinac_truncation.concepts import STCM_COLUMNS
from sinac_truncation.etl import (
    CATALOGUE_SOURCE,
    DESCRIPTOR_SOURCE,
    LOAD_FILES,
    POPULATED_TABLES,
    SETUP_FILES,
    SOURCE_COLUMNS,
    SQL_FILES,
    UNLOADABLE_FILE,
    CountRow,
    RecordFile,
    Reference,
    config_problems,
    etl_reference,
    format_counts,
    release_date,
    source_description,
    vocabulary_rows,
    year_problems,
)
from sinac_truncation.sqltext import render_sql, schema_mapping
from sinac_truncation.staging import SOURCE_ROW, staged_columns, table_name

#: Repository root, reached from this file so no absolute path is written down (rule 12).
REPO_ROOT = Path(__file__).resolve().parents[1]

SQL_DIR = REPO_ROOT / "sql" / "etl"

#: The temporary objects of a run. They live in ``pg_temp`` and are dropped when it ends.
STAGED_VIEW = "staged_records"
RUN_TABLE = "etl_run"
RECORDS_TABLE = "records"

Cur = Cursor[TupleRow]


class EtlError(RuntimeError):
    """The ETL stopped for a reason the user has to act on."""


@dataclass(frozen=True)
class Schemas:
    """The three schemas of the project (D-032)."""

    cdm: str
    staging: str
    results: str

    @property
    def markers(self) -> dict[str, str]:
        return schema_mapping(self.cdm, self.staging, self.results)


@dataclass(frozen=True)
class Inputs:
    """What a run reads from the configuration and the manifest, checked before any query."""

    concepts: Mapping[str, object]
    source_vocabularies: Mapping[str, object]
    map_rows: Sequence[Mapping[str, str]]
    record_files: Sequence[RecordFile]
    documentation: str | None
    vocabulary_version: str
    descriptor: Reference
    catalogues: Reference


def read_sql(sql_dir: Path = SQL_DIR) -> dict[str, str]:
    """Every SQL file of the ETL, by name."""
    return {name: (sql_dir / name).read_text(encoding="utf-8") for name in SQL_FILES}


def _entry(sources_path: Path, entry_id: str) -> download.SourceEntry:
    try:
        return download.load_entry(sources_path, entry_id)
    except download.DownloadError as error:
        raise EtlError(str(error)) from error


def read_inputs(
    years: Sequence[int], sql_texts: Mapping[str, str], *, config_dir: Path, sources_path: Path
) -> Inputs:
    """Read the configuration and the manifest, and refuse anything the run could not use.

    Raises:
        EtlError: the configuration fails its own checks or lacks what the SQL cites, a year is
            outside what the ids can hold, or a record file has no recorded hash.
    """
    config, map_rows, problems = validate_concepts.read_config(config_dir)
    concepts = config.get("concepts")
    vocabularies = config.get("source_vocabularies")
    if not problems and isinstance(concepts, Mapping) and isinstance(vocabularies, Mapping):
        problems = config_problems(sql_texts, concepts, vocabularies)
    problems += year_problems(years)
    if problems or not isinstance(concepts, Mapping) or not isinstance(vocabularies, Mapping):
        listed = "\n  ".join(problems)
        raise EtlError(f"the configuration cannot be loaded; nothing was touched.\n  {listed}")

    record_files: list[RecordFile] = []
    pages: set[str] = set()
    for year in years:
        entry = _entry(sources_path, download.record_id(year))
        if entry.sha256 is None or entry.retrieved_at is None:
            raise EtlError(
                f"{entry.id} has no recorded sha256 or retrieval date: run "
                f"`pipeline.py download --years {year} --record` first"
            )
        record_files.append(
            RecordFile(
                year=year,
                url=entry.url,
                version=entry.version,
                sha256=entry.sha256,
                retrieved_at=entry.retrieved_at,
            )
        )
        if entry.page:
            pages.add(entry.page)

    descriptor = _entry(sources_path, DESCRIPTOR_SOURCE)
    catalogues = _entry(sources_path, CATALOGUE_SOURCE)
    try:
        package = load_vocab.read_package(sources_path)
    except load_vocab.VocabError as error:
        raise EtlError(str(error)) from error

    return Inputs(
        concepts=concepts,
        source_vocabularies=vocabularies,
        map_rows=map_rows,
        record_files=record_files,
        documentation="; ".join(sorted(pages)) or None,
        vocabulary_version=package.vocabulary_version,
        descriptor=Reference(url=descriptor.url, version=descriptor.version),
        catalogues=Reference(url=catalogues.url, version=catalogues.version),
    )


def check_database(
    conn: sql_runner.Connection, years: Sequence[int], schemas: Schemas, inputs: Inputs
) -> None:
    """Refuse a database the run cannot load from, before anything is written.

    It must hold the vocabulary version the manifest declares, and, for each year, a staging table
    with the columns the ETL reads, staged from the file whose sha256 the manifest records.
    Everything is read in a transaction of its own, so the load that follows is one too.
    """
    needed = (SOURCE_ROW, *staged_columns(SOURCE_COLUMNS))
    try:
        with conn.transaction(), conn.cursor() as cur:
            version = validate_concepts.loaded_version(conn, schemas.cdm)
            if version != inputs.vocabulary_version:
                raise EtlError(
                    f"the database holds vocabulary {version!r} and config/sources.yml declares "
                    f"{inputs.vocabulary_version!r}: run `pipeline.py vocab` first"
                )
            for record in inputs.record_files:
                table = table_name(record.year)
                cur.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = %s AND table_name = %s",
                    (schemas.staging, table),
                )
                present = {str(row[0]) for row in cur.fetchall()}
                missing = [column for column in needed if column not in present]
                if missing:
                    raise EtlError(
                        f"{schemas.staging}.{table} is missing or lacks {', '.join(missing)}: "
                        f"run `pipeline.py stage --years {record.year}` first"
                    )
                cur.execute(
                    sql.SQL(
                        "SELECT source_sha256 FROM {} WHERE source_year = %s AND stage = 'table'"
                    ).format(sql.Identifier(schemas.staging, "load_counts")),
                    (record.year,),
                )
                staged = [str(row[0]) for row in cur.fetchall()]
                if staged != [record.sha256]:
                    raise EtlError(
                        f"{schemas.staging}.{table} was not staged from the file "
                        f"config/sources.yml "
                        f"records for {record.year} (sha256 {record.sha256[:12]}): run "
                        f"`pipeline.py stage --years {record.year}` again"
                    )
    except psycopg.errors.UndefinedTable as error:
        raise EtlError(
            f"{str(error).strip()}. Run `pipeline.py db-init`, `vocab` and `stage` first."
        ) from error


def git_reference(repo_root: Path = REPO_ROOT) -> str | None:
    """The repository and commit the ETL runs from, or ``None`` when git cannot tell."""

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(repo_root), *args], check=True, capture_output=True, text=True
        ).stdout

    try:
        remote = git("remote", "get-url", "origin")
        commit = git("rev-parse", "HEAD")
        dirty = bool(git("status", "--porcelain").strip())
    except (OSError, subprocess.CalledProcessError):
        return None
    return etl_reference(remote, commit, dirty=dirty)


def _copy(
    cur: Cur, table: sql.Identifier, columns: Sequence[str], rows: Sequence[Sequence[object]]
) -> None:
    statement = sql.SQL("COPY {} ({}) FROM STDIN").format(
        table, sql.SQL(", ").join(sql.Identifier(column) for column in columns)
    )
    with cur.copy(statement) as copy:
        for row in rows:
            copy.write_row(row)


def load_configuration(cur: Cur, schemas: Schemas, inputs: Inputs) -> None:
    """Empty the populated tables and write the configuration they are built from, with ``COPY``.

    ``results.concept_sets`` gets the concepts by key, ``source_to_concept_map`` the map, and
    ``vocabulary`` one row per local vocabulary (its previous rows are deleted first; the
    vocabularies of the Athena package are left alone).
    """
    tables = [sql.Identifier(schemas.cdm, table) for table in POPULATED_TABLES]
    tables += [sql.Identifier(schemas.results, table) for table in ("etl_counts", "concept_sets")]
    cur.execute(sql.SQL("TRUNCATE {}").format(sql.SQL(", ").join(tables)))

    vocabularies = vocabulary_rows(
        inputs.source_vocabularies, descriptor=inputs.descriptor, catalogues=inputs.catalogues
    )
    vocabulary = sql.Identifier(schemas.cdm, "vocabulary")
    cur.execute(
        sql.SQL("DELETE FROM {} WHERE vocabulary_id = ANY(%s)").format(vocabulary),
        ([row[0] for row in vocabularies],),
    )
    _copy(
        cur,
        vocabulary,
        (
            "vocabulary_id",
            "vocabulary_name",
            "vocabulary_reference",
            "vocabulary_version",
            "vocabulary_concept_id",
        ),
        vocabularies,
    )

    concepts = [
        (str(key), int(entry["concept_id"]))
        for key, entry in inputs.concepts.items()
        if isinstance(entry, Mapping)
    ]
    _copy(
        cur,
        sql.Identifier(schemas.results, "concept_sets"),
        ("concept_key", "concept_id"),
        concepts,
    )
    _copy(
        cur,
        sql.Identifier(schemas.cdm, "source_to_concept_map"),
        STCM_COLUMNS,
        [[row[column] or None for column in STCM_COLUMNS] for row in inputs.map_rows],
    )


def create_run_objects(
    cur: Cur,
    years: Sequence[int],
    schemas: Schemas,
    inputs: Inputs,
    reference: str | None,
) -> None:
    """The temporary view over the staged years, and the one row CDM_SOURCE reads."""
    cur.execute(sql.SQL("DROP VIEW IF EXISTS pg_temp.{}").format(sql.Identifier(STAGED_VIEW)))
    columns = sql.SQL(", ").join(
        sql.Identifier(column) for column in staged_columns(SOURCE_COLUMNS)
    )
    selects = [
        sql.SQL("SELECT {year} AS source_year, {row}, {columns} FROM {table}").format(
            year=sql.Literal(year),
            row=sql.Identifier(SOURCE_ROW),
            columns=columns,
            table=sql.Identifier(schemas.staging, table_name(year)),
        )
        for year in years
    ]
    cur.execute(
        sql.SQL("CREATE TEMP VIEW {} AS {}").format(
            sql.Identifier(STAGED_VIEW), sql.SQL(" UNION ALL ").join(selects)
        )
    )

    cur.execute(sql.SQL("DROP TABLE IF EXISTS pg_temp.{}").format(sql.Identifier(RUN_TABLE)))
    cur.execute(
        sql.SQL(
            "CREATE TEMP TABLE {} (source_description text, source_documentation_reference text, "
            "cdm_etl_reference text, source_release_date date) ON COMMIT DROP"
        ).format(sql.Identifier(RUN_TABLE))
    )
    cur.execute(
        sql.SQL("INSERT INTO {} VALUES (%s, %s, %s, %s)").format(sql.Identifier(RUN_TABLE)),
        (
            source_description(inputs.record_files),
            inputs.documentation,
            reference,
            release_date(inputs.record_files),
        ),
    )


def _drop_run_objects(cur: Cur) -> None:
    cur.execute(sql.SQL("DROP VIEW IF EXISTS pg_temp.{}").format(sql.Identifier(STAGED_VIEW)))
    for table in (RECORDS_TABLE, RUN_TABLE):
        cur.execute(sql.SQL("DROP TABLE IF EXISTS pg_temp.{}").format(sql.Identifier(table)))


def _timed(conn: sql_runner.Connection, name: str, text: str, schemas: Schemas) -> None:
    start = time.perf_counter()
    statements = render_sql(text, schemas.markers)
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(statements)
    print(f"  {name:<24}{time.perf_counter() - start:7.1f} s")


def _stop_on_unloadable(cur: Cur, text: str, schemas: Schemas) -> None:
    cur.execute(render_sql(text, schemas.markers))
    rows = cur.fetchall()
    if rows:
        total = int(rows[0][3])
        listed = "\n  ".join(
            f"{year} source_row {row}: {problem}" for year, row, problem, _ in rows
        )
        raise EtlError(
            f"{total:,} record(s) cannot be loaded as they are (D-075); nothing was loaded and "
            f"the previous load was kept. The first {len(rows)}:\n  {listed}"
        )


def _failed_checks(cur: Cur, schemas: Schemas) -> list[tuple[str, int]]:
    cur.execute(
        sql.SQL(
            "SELECT rule, row_count FROM {} WHERE cdm_table = 'check' AND row_count <> 0 "
            "ORDER BY rule"
        ).format(sql.Identifier(schemas.results, "etl_counts"))
    )
    return [(str(rule), int(count)) for rule, count in cur.fetchall()]


def load(
    conn: sql_runner.Connection,
    years: Sequence[int],
    schemas: Schemas,
    inputs: Inputs,
    sql_texts: Mapping[str, str],
    reference: str | None,
) -> None:
    """Empty and refill the populated tables in one transaction that commits only when it is clean.

    Each SQL file runs in a savepoint of that transaction. Any exception, an unloadable record or a
    failed check included, rolls the whole of it back.
    """
    sql_runner.ensure_schemas(conn, [schemas.results])
    try:
        with conn.transaction(), conn.cursor() as cur:
            _timed(conn, "tables.sql", sql_texts["tables.sql"], schemas)
            load_configuration(cur, schemas, inputs)
            create_run_objects(cur, years, schemas, inputs, reference)
            for name in SETUP_FILES[1:]:
                _timed(conn, name, sql_texts[name], schemas)
            _stop_on_unloadable(cur, sql_texts[UNLOADABLE_FILE], schemas)
            for name in LOAD_FILES:
                _timed(conn, name, sql_texts[name], schemas)
            failed = _failed_checks(cur, schemas)
            if failed:
                listed = "\n  ".join(f"{rule}: {count:,}" for rule, count in failed)
                raise EtlError(
                    f"{len(failed)} check(s) failed, so nothing was committed and the previous "
                    f"load was kept:\n  {listed}"
                )
            _drop_run_objects(cur)
    except (psycopg.errors.DataError, psycopg.errors.IntegrityError) as error:
        raise EtlError(
            f"the database refused the load: {str(error).strip()}. The previous load was kept."
        ) from error


def analyze(conn: sql_runner.Connection, schemas: Schemas) -> None:
    """Refresh the planner statistics of the tables just loaded."""
    with conn.transaction(), conn.cursor() as cur:
        for table in POPULATED_TABLES:
            cur.execute(sql.SQL("ANALYZE {}").format(sql.Identifier(schemas.cdm, table)))


def read_counts(conn: sql_runner.Connection, schemas: Schemas) -> list[CountRow]:
    """The rows of ``results.etl_counts``."""
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(
            sql.SQL("SELECT source_year, cdm_table, rule, row_count FROM {}").format(
                sql.Identifier(schemas.results, "etl_counts")
            )
        )
        return [
            (None if year is None else int(year), str(table), str(rule), int(count))
            for year, table, rule, count in cur.fetchall()
        ]


def run(
    conn: sql_runner.Connection,
    years: Sequence[int],
    *,
    schemas: Schemas,
    config_dir: Path = validate_concepts.CONFIG_DIR,
    sources_path: Path = download.SOURCES_PATH,
    sql_dir: Path = SQL_DIR,
    reference: str | None = None,
) -> list[CountRow]:
    """Populate the CDM tables of the slice from the staged years. See ``pipeline.py cdm --help``.

    Returns:
        The rows of ``results.etl_counts``, already printed.

    Raises:
        EtlError: anything the user has to act on. The tables keep their previous content
            whenever it is raised.
    """
    start = time.perf_counter()
    sql_texts = read_sql(sql_dir)
    inputs = read_inputs(years, sql_texts, config_dir=config_dir, sources_path=sources_path)
    check_database(conn, years, schemas, inputs)
    print(f"loading {', '.join(str(year) for year in years)} into {schemas.cdm}")
    load(conn, years, schemas, inputs, sql_texts, reference)
    analyze(conn, schemas)
    counts = read_counts(conn, schemas)
    print()
    for line in format_counts(counts):
        print(line)
    checks = [row for row in counts if row[1] == "check"]
    print(
        f"\nevery one of the {len(checks)} checks is 0; loaded in "
        f"{time.perf_counter() - start:.1f} s. Counts in {schemas.results}.etl_counts"
    )
    return counts
