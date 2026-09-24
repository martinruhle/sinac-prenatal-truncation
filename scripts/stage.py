"""Staging the SINAC record files: ZIP → CSV → Parquet → the ``staging`` schema.

The I/O of the staging layer lives here (rule 6): the ZIP, the extracted CSV, DuckDB and
Postgres. Naming, counting and comparing are pure and live in :mod:`sinac_truncation.staging`.

Every source column stays text (D-033). A run first prepares the files, which needs no database,
then rebuilds the year's table and its ``load_counts`` rows in one transaction. Running twice
therefore leaves the same result, and a run that fails leaves the previous load as it was
(D-069).
"""

import os
import shutil
import time
import zipfile
import zlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import duckdb
from psycopg import Cursor, sql
from psycopg.rows import TupleRow

import download
import sql_runner
from sinac_truncation.staging import (
    SOURCE_ROW,
    CsvScan,
    Record,
    StagingError,
    count_mismatch,
    sample_mismatches,
    scan_records,
    single_csv_member,
    staged_columns,
    table_name,
)

#: Repository root, reached from this file so no absolute path is written down (rule 12).
REPO_ROOT = Path(__file__).resolve().parents[1]

EXTRACTED_DIR = download.RAW_DIR / "extracted"
INTERIM_DIR = REPO_ROOT / "data" / "interim"
LOAD_COUNTS_SQL = REPO_ROOT / "sql" / "staging" / "load_counts.sql"

#: One record in this many is compared field by field between the CSV and the table (D-070).
SAMPLE_EVERY = 100_000

#: Rows fetched from DuckDB per batch on the way to Postgres, so memory stays bounded.
BATCH_ROWS = 50_000

CHUNK_BYTES = 1024 * 1024

#: How DuckDB reads a record file. Every option is fixed rather than sniffed: comma, double
#: quotes escaped by doubling, a header and UTF-8 (docs/source_inventory.md, table 1).
#: ``all_varchar`` keeps every value as text (D-033); ``strict_mode`` and the default
#: ``ignore_errors = false`` make a malformed record stop the run instead of being dropped.
CSV_OPTIONS = (
    "header = true, all_varchar = true, delim = ',', quote = '\"', escape = '\"', "
    "encoding = 'utf-8', strict_mode = true"
)

Cur = Cursor[TupleRow]


class StageError(RuntimeError):
    """Staging stopped for a reason the user has to act on."""


@dataclass(frozen=True)
class Prepared:
    """What the file stages of one year produced, before anything reaches the database."""

    year: int
    source_sha256: str
    csv_path: Path
    parquet_path: Path
    scan: CsvScan
    columns: tuple[str, ...]
    parquet_rows: int


@dataclass(frozen=True)
class StageTime:
    """One stage as it is reported: its name, the rows it counted and how long it took."""

    stage: str
    rows: int | None
    seconds: float
    note: str


def _shown(path: Path) -> str:
    """A path as the user sees it: relative to the repository root when it is inside it."""
    return path.relative_to(REPO_ROOT).as_posix() if path.is_relative_to(REPO_ROOT) else str(path)


def _literal(path: Path) -> str:
    """A path as a SQL string literal, for the one DuckDB clause that takes no parameter."""
    return "'" + path.as_posix().replace("'", "''") + "'"


def _crc32(path: Path) -> int:
    crc = 0
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_BYTES):
            crc = zlib.crc32(chunk, crc)
    return crc


class Clock:
    """Times each stage and prints it as soon as it is done."""

    def __init__(self, year: int) -> None:
        self.year = year
        self.times: list[StageTime] = []
        self._start = time.perf_counter()

    def done(self, stage: str, rows: int | None, note: str) -> None:
        now = time.perf_counter()
        entry = StageTime(stage=stage, rows=rows, seconds=now - self._start, note=note)
        self.times.append(entry)
        shown_rows = "" if rows is None else f"{rows:,} rows"
        print(f"{self.year}  {stage:<8}{shown_rows:>17}  {entry.seconds:6.1f} s  {note}")
        self._start = time.perf_counter()


def verify_zip(year: int, *, raw_dir: Path, sources_path: Path) -> tuple[Path, str]:
    """The year's record ZIP, checked against the sha256 recorded in the manifest (D-044)."""
    try:
        entry = download.load_entry(sources_path, download.record_id(year))
        path = download.target_path(entry, raw_dir)
        if not path.exists():
            raise StageError(
                f"{_shown(path)} is not on disk: run `pipeline.py download --years {year}` first"
            )
        digest = download.verify_file(path, entry)
    except download.DownloadError as error:
        raise StageError(str(error)) from error
    return path, digest.sha256


def extract(zip_path: Path, dest_dir: Path) -> tuple[Path, bool]:
    """Extract the one CSV member of a record ZIP, or reuse the copy already extracted.

    A copy is reused only when its size and CRC-32 are the ones the archive records for the
    member. Otherwise the member is written to a ``.part`` file and renamed once complete, so an
    interrupted run never leaves something that looks like a whole file.

    Returns:
        The extracted file and whether it was reused.
    """
    try:
        with zipfile.ZipFile(zip_path) as archive:
            member = archive.getinfo(single_csv_member(archive.namelist()))
            target = dest_dir / Path(member.filename).name
            if (
                target.exists()
                and target.stat().st_size == member.file_size
                and _crc32(target) == member.CRC
            ):
                return target, True

            dest_dir.mkdir(parents=True, exist_ok=True)
            partial = target.with_name(f"{target.name}.part")
            try:
                with archive.open(member) as source, partial.open("wb") as sink:
                    shutil.copyfileobj(source, sink, CHUNK_BYTES)
            except BaseException:
                partial.unlink(missing_ok=True)
                raise
    except (zipfile.BadZipFile, StagingError) as error:
        raise StageError(f"{_shown(zip_path)}: {error}") from error
    os.replace(partial, target)
    return target, False


def scan_csv(path: Path) -> CsvScan:
    """Count the records of the extracted file with Python's own parser (D-070)."""
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            return scan_records(handle, sample_every=SAMPLE_EVERY)
    except (StagingError, UnicodeDecodeError) as error:
        raise StageError(f"{_shown(path)}: {error}") from error


def duckdb_connection(interim_dir: Path) -> duckdb.DuckDBPyConnection:
    """An in-memory DuckDB that keeps file order and spills, if it must, under ``interim_dir``.

    The default spill directory is ``.tmp`` under the working directory, which would put it in
    the repository root.
    """
    return duckdb.connect(
        config={
            "preserve_insertion_order": True,
            "temp_directory": str(interim_dir / "duckdb_tmp"),
        }
    )


def write_parquet(duck: duckdb.DuckDBPyConnection, csv_path: Path, parquet_path: Path) -> int:
    """Rewrite the Parquet copy of the CSV, every value as text, in file order.

    DuckDB streams the file through, so it is never held in memory whole. Rows keep the order of
    the file because ``preserve_insertion_order`` is on, and ``source_row`` is later read from the
    position of each row in this file (D-070).

    Returns:
        The number of rows in the Parquet file.
    """
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    partial = parquet_path.with_name(f"{parquet_path.name}.part")
    partial.unlink(missing_ok=True)
    try:
        duck.execute(
            f"COPY (SELECT * FROM read_csv({_literal(csv_path)}, {CSV_OPTIONS})) "
            f"TO {_literal(partial)} (FORMAT parquet)"
        )
    except duckdb.Error as error:
        partial.unlink(missing_ok=True)
        raise StageError(f"DuckDB could not read {_shown(csv_path)}: {error}") from error
    os.replace(partial, parquet_path)

    row = duck.execute("SELECT count(*) FROM read_parquet($1)", [str(parquet_path)]).fetchone()
    return 0 if row is None else int(row[0])


def parquet_columns(duck: duckdb.DuckDBPyConnection, parquet_path: Path) -> list[tuple[str, str]]:
    """Name and DuckDB type of each column of a Parquet file, in order."""
    described = duck.execute("DESCRIBE SELECT * FROM read_parquet($1)", [str(parquet_path)])
    return [(str(name), str(kind)) for name, kind, *_ in described.fetchall()]


def prepare(
    year: int,
    *,
    raw_dir: Path = download.RAW_DIR,
    extracted_dir: Path = EXTRACTED_DIR,
    interim_dir: Path = INTERIM_DIR,
    sources_path: Path = download.SOURCES_PATH,
    clock: Clock | None = None,
) -> Prepared:
    """The file stages of one year: verify, extract, count and write the Parquet copy.

    Nothing here touches the database, so it runs without one.

    Raises:
        StageError: anything the user has to decide about, including a Parquet file that does
            not hold as many rows as the CSV.
    """
    clock = clock or Clock(year)

    zip_path, sha256 = verify_zip(year, raw_dir=raw_dir, sources_path=sources_path)
    clock.done("verify", None, f"{_shown(zip_path)}, sha256 {sha256[:12]}")

    csv_path, reused = extract(zip_path, extracted_dir)
    clock.done("extract", None, f"{_shown(csv_path)}{' (reused)' if reused else ''}")

    scan = scan_csv(csv_path)
    try:
        columns = staged_columns(scan.header)
    except StagingError as error:
        raise StageError(f"{_shown(csv_path)}: {error}") from error
    clock.done("csv", scan.records, f"{len(columns)} columns, Python csv parser")

    parquet_path = interim_dir / f"{table_name(year)}.parquet"
    with duckdb_connection(interim_dir) as duck:
        parquet_rows = write_parquet(duck, csv_path, parquet_path)
        described = parquet_columns(duck, parquet_path)
    if described != [(name, "VARCHAR") for name in scan.header]:
        raise StageError(
            f"{_shown(parquet_path)} does not hold the columns of the CSV header, all as text"
        )
    mismatch = count_mismatch({"csv": scan.records, "parquet": parquet_rows})
    if mismatch is not None:
        raise StageError(f"{year}: {mismatch}. Nothing was loaded.")
    clock.done("parquet", parquet_rows, _shown(parquet_path))

    return Prepared(
        year=year,
        source_sha256=sha256,
        csv_path=csv_path,
        parquet_path=parquet_path,
        scan=scan,
        columns=columns,
        parquet_rows=parquet_rows,
    )


def _create_table(cur: Cur, table: sql.Identifier, columns: Sequence[str]) -> None:
    cur.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(table))
    definitions = [sql.SQL("{} integer NOT NULL").format(sql.Identifier(SOURCE_ROW))]
    definitions += [sql.SQL("{} text").format(sql.Identifier(column)) for column in columns]
    cur.execute(sql.SQL("CREATE TABLE {} ({})").format(table, sql.SQL(", ").join(definitions)))


def _copy_rows(
    cur: Cur,
    table: sql.Identifier,
    columns: Sequence[str],
    duck: duckdb.DuckDBPyConnection,
    parquet_path: Path,
) -> None:
    """Stream the Parquet rows into the table with ``COPY``, one bounded batch at a time.

    ``source_row`` is the position of the row in the Parquet file, plus one (D-070). Each row
    carries its own ordinal, so the order the batches arrive in does not matter.
    """
    statement = sql.SQL("COPY {} ({}) FROM STDIN").format(
        table, sql.SQL(", ").join(sql.Identifier(name) for name in (SOURCE_ROW, *columns))
    )
    duck.execute(
        "SELECT file_row_number + 1, * EXCLUDE (file_row_number) "
        "FROM read_parquet($1, file_row_number = true)",
        [str(parquet_path)],
    )
    with cur.copy(statement) as copy:
        while batch := duck.fetchmany(BATCH_ROWS):
            for row in batch:
                copy.write_row(row)


def _scalar(cur: Cur, query: sql.Composed, params: Sequence[object] = ()) -> int:
    cur.execute(query, params)
    row = cur.fetchone()
    return 0 if row is None else int(row[0])


def _staged_sample(
    cur: Cur, table: sql.Identifier, columns: Sequence[str], rows: Sequence[int]
) -> dict[int, Record]:
    cur.execute(
        sql.SQL("SELECT {}, {} FROM {} WHERE {} = ANY(%s)").format(
            sql.Identifier(SOURCE_ROW),
            sql.SQL(", ").join(sql.Identifier(column) for column in columns),
            table,
            sql.Identifier(SOURCE_ROW),
        ),
        (list(rows),),
    )
    return {int(row[0]): tuple(row[1:]) for row in cur.fetchall()}


def load(conn: sql_runner.Connection, prepared: Prepared, *, schema: str, clock: Clock) -> int:
    """Rebuild the year's staging table and its ``load_counts`` rows, in one transaction.

    The table is dropped, created, filled with ``COPY`` and given its primary key; then the
    three counts and the sample are checked, and only then are the counts recorded. A failed
    check raises inside the transaction, so the previous table and counts stay as they were.

    Returns:
        The number of rows in the table.
    """
    sql_runner.ensure_schemas(conn, [schema])
    sql_runner.run_sql_file(conn, LOAD_COUNTS_SQL, {"staging_schema": schema})

    name = table_name(prepared.year)
    table = sql.Identifier(schema, name)
    counts_table = sql.Identifier(schema, "load_counts")
    member = prepared.csv_path.name

    with conn.transaction(), conn.cursor() as cur:
        _create_table(cur, table, prepared.columns)
        with duckdb_connection(prepared.parquet_path.parent) as duck:
            _copy_rows(cur, table, prepared.columns, duck, prepared.parquet_path)
        cur.execute(
            sql.SQL("ALTER TABLE {} ADD PRIMARY KEY ({})").format(table, sql.Identifier(SOURCE_ROW))
        )
        table_rows = _scalar(cur, sql.SQL("SELECT count(*) FROM {}").format(table))

        counts = {
            "csv": prepared.scan.records,
            "parquet": prepared.parquet_rows,
            "table": table_rows,
        }
        mismatch = count_mismatch(counts)
        if mismatch is not None:
            raise StageError(f"{prepared.year}: {mismatch}. The previous load was kept.")

        staged = _staged_sample(cur, table, prepared.columns, list(prepared.scan.samples))
        problems = sample_mismatches(prepared.scan.samples, staged, prepared.columns)
        if problems:
            listed = "\n  ".join(problems[:10])
            raise StageError(
                f"{prepared.year}: the table does not hold what the CSV holds "
                f"({len(problems)} differences). The previous load was kept.\n  {listed}"
            )

        cur.execute(
            sql.SQL("DELETE FROM {} WHERE source_year = %s").format(counts_table), (prepared.year,)
        )
        cur.executemany(
            sql.SQL(
                "INSERT INTO {} (source_year, stage, row_count, source_member, source_sha256) "
                "VALUES (%s, %s, %s, %s, %s)"
            ).format(counts_table),
            [
                (prepared.year, stage, rows, member, prepared.source_sha256)
                for stage, rows in counts.items()
            ],
        )

    clock.done(
        "table",
        table_rows,
        f"{schema}.{name}, {len(prepared.scan.samples)} sampled records match the CSV",
    )
    return table_rows


def run(
    year: int,
    *,
    conn: sql_runner.Connection,
    schema: str,
    raw_dir: Path = download.RAW_DIR,
    extracted_dir: Path = EXTRACTED_DIR,
    interim_dir: Path = INTERIM_DIR,
    sources_path: Path = download.SOURCES_PATH,
) -> list[StageTime]:
    """Stage one year. See ``pipeline.py stage --help``.

    Returns:
        Each stage with the rows it counted and the seconds it took.

    Raises:
        StageError: anything the user has to decide about.
    """
    clock = Clock(year)
    prepared = prepare(
        year,
        raw_dir=raw_dir,
        extracted_dir=extracted_dir,
        interim_dir=interim_dir,
        sources_path=sources_path,
        clock=clock,
    )
    load(conn, prepared, schema=schema, clock=clock)
    return clock.times
