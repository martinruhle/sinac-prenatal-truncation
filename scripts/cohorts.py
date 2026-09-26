"""Building the cohorts and their attrition in the database (task 1.5.1).

The I/O of the cohorts lives here (rule 6): reading ``sql/cohorts/`` and running it on Postgres.
Every criterion is SQL (rule 5); the invariants the result must meet live in
:mod:`sinac_truncation.cohorts`.

A run first checks what it needs, before it touches anything: the years of ``--years`` loaded in
the CDM, and the concepts the SQL reads. It then replaces the cohort and the attrition of each
definition in one transaction, which commits only when every invariant of the attrition holds;
otherwise the previous cohort stays as it was, as the ETL does (D-073).
"""

import time
from collections.abc import Mapping, Sequence
from pathlib import Path

import psycopg
from psycopg import Cursor, sql
from psycopg.rows import TupleRow

import etl
import sql_runner
from sinac_truncation.cohorts import (
    MEXICO_CODE,
    SQL_FILES,
    AttritionStep,
    attrition_problems,
    cited_concept_keys,
    format_attrition,
)
from sinac_truncation.period import format_years
from sinac_truncation.sqltext import render_sql

#: Repository root, reached from this file so no absolute path is written down (rule 12).
REPO_ROOT = Path(__file__).resolve().parents[1]

SQL_DIR = REPO_ROOT / "sql" / "cohorts"

Cur = Cursor[TupleRow]


class CohortError(RuntimeError):
    """The cohorts could not be built for a reason the user has to act on."""


def read_sql(sql_dir: Path = SQL_DIR) -> dict[str, str]:
    """Every SQL file of the cohorts, by name."""
    return {name: (sql_dir / name).read_text(encoding="utf-8") for name in SQL_FILES}


def check_database(
    conn: sql_runner.Connection,
    years: Sequence[int],
    schemas: etl.Schemas,
    sql_texts: Mapping[str, str],
) -> None:
    """Refuse a database the cohorts cannot be built from, before anything is written.

    Every year of ``years`` must be loaded in the CDM, whose counts give steps 0 and 1. Every
    concept the SQL reads must be there too: a missing one would be NULL, and a NULL criterion
    would exclude every record without saying why.
    """
    etl_counts = sql.Identifier(schemas.results, "etl_counts")
    concept_sets = sql.Identifier(schemas.results, "concept_sets")
    stcm = sql.Identifier(schemas.cdm, "source_to_concept_map")
    try:
        with conn.transaction(), conn.cursor() as cur:
            cur.execute(
                sql.SQL(
                    "SELECT source_year FROM {} WHERE cdm_table = 'staging' AND rule = 'rows'"
                ).format(etl_counts)
            )
            loaded = {int(row[0]) for row in cur.fetchall()}
            missing = [year for year in years if year not in loaded]
            if missing:
                raise CohortError(
                    f"the CDM holds no load of {format_years(missing)} "
                    f"({schemas.results}.etl_counts): run `pipeline.py cdm --years "
                    f"{format_years(years)}` first"
                )

            keys = sorted(cited_concept_keys(sql_texts))
            cur.execute(
                sql.SQL("SELECT concept_key FROM {} WHERE concept_key = ANY(%s)").format(
                    concept_sets
                ),
                (keys,),
            )
            present = {str(row[0]) for row in cur.fetchall()}
            for key in keys:
                if key not in present:
                    raise CohortError(
                        f"{schemas.results}.concept_sets lacks the concept {key!r} that "
                        "sql/cohorts/ cites: run `pipeline.py cdm` again, which reloads "
                        "config/concept_sets.yml"
                    )

            vocabulary, code = MEXICO_CODE
            cur.execute(
                sql.SQL(
                    "SELECT count(*) FROM {} WHERE source_vocabulary_id = %s AND source_code = %s "
                    "AND invalid_reason IS NULL AND target_concept_id <> 0"
                ).format(stcm),
                (vocabulary, code),
            )
            row = cur.fetchone()
            targets = 0 if row is None else int(row[0])
            if targets != 1:
                raise CohortError(
                    f"{schemas.cdm}.source_to_concept_map maps {vocabulary} {code!r} to {targets} "
                    "concepts, and criterion 2 needs exactly one: run `pipeline.py cdm` again, "
                    "which reloads config/source_to_concept_map.csv"
                )
    except psycopg.errors.UndefinedTable as error:
        raise CohortError(
            f"{str(error).strip()}. Run `pipeline.py db-init` and `cdm` first."
        ) from error


def _attrition(cur: Cur, schemas: etl.Schemas) -> list[AttritionStep]:
    cur.execute(
        sql.SQL(
            "SELECT cohort_definition_id, source_year, step, kind, description, remaining, "
            "excluded FROM {} ORDER BY cohort_definition_id, source_year, step"
        ).format(sql.Identifier(schemas.results, "attrition"))
    )
    return [AttritionStep(*row) for row in cur.fetchall()]


def _cohort_rows(cur: Cur, schemas: etl.Schemas) -> dict[tuple[int, int], int]:
    """The rows of ``results.cohort`` per definition and year of the subject's record file."""
    cur.execute(
        sql.SQL(
            "SELECT c.cohort_definition_id, split_part(p.person_source_value, ':', 1)::integer, "
            "count(*) FROM {} AS c INNER JOIN {} AS p ON c.subject_id = p.person_id "
            "GROUP BY 1, 2"
        ).format(sql.Identifier(schemas.results, "cohort"), sql.Identifier(schemas.cdm, "person"))
    )
    return {(int(definition), int(year)): int(count) for definition, year, count in cur}


def load(
    conn: sql_runner.Connection,
    years: Sequence[int],
    schemas: etl.Schemas,
    sql_texts: Mapping[str, str],
) -> None:
    """Replace every cohort and its attrition in one transaction that commits only when consistent.

    Raises:
        CohortError: an invariant of the attrition fails, or the database refuses a row; the
            previous cohort is kept.
    """
    try:
        with conn.transaction(), conn.cursor() as cur:
            for name in SQL_FILES:
                start = time.perf_counter()
                cur.execute(render_sql(sql_texts[name], schemas.markers))
                if name == SQL_FILES[0]:
                    cur.execute(
                        "INSERT INTO pg_temp.cohort_years (source_year) "
                        "SELECT unnest(%s::integer[])",
                        (list(years),),
                    )
                print(f"  {name:<24}{time.perf_counter() - start:7.1f} s")
            problems = attrition_problems(_attrition(cur, schemas), _cohort_rows(cur, schemas))
            if problems:
                listed = "\n  ".join(problems)
                raise CohortError(
                    f"{len(problems)} attrition check(s) failed, so nothing was committed and "
                    f"the previous cohort was kept:\n  {listed}"
                )
    except (psycopg.errors.DataError, psycopg.errors.IntegrityError) as error:
        raise CohortError(
            f"the database refused the cohorts: {str(error).strip()}. The previous cohort was kept."
        ) from error


def read_attrition(conn: sql_runner.Connection, schemas: etl.Schemas) -> list[AttritionStep]:
    """The rows of ``results.attrition``, in order."""
    with conn.transaction(), conn.cursor() as cur:
        return _attrition(cur, schemas)


def run(
    conn: sql_runner.Connection,
    years: Sequence[int],
    *,
    schemas: etl.Schemas,
    sql_dir: Path = SQL_DIR,
) -> list[AttritionStep]:
    """Build every cohort of ``sql/cohorts/`` on the files of ``years``.

    See ``pipeline.py cohorts --help``.

    Returns:
        The rows of ``results.attrition``, already printed.

    Raises:
        CohortError: anything the user has to act on. The cohorts keep their previous content
            whenever it is raised.
    """
    start = time.perf_counter()
    sql_texts = read_sql(sql_dir)
    check_database(conn, years, schemas, sql_texts)
    print(f"building the cohorts of {format_years(years)}")
    load(conn, years, schemas, sql_texts)
    steps = read_attrition(conn, schemas)
    print()
    for line in format_attrition(steps):
        print(line)
    print(
        f"\nevery attrition check holds; built in {time.perf_counter() - start:.1f} s. Rows in "
        f"{schemas.results}.cohort and {schemas.results}.attrition"
    )
    return steps
