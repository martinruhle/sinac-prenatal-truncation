"""Tests for the landmark cohorts of measure (d) (task 1.6.3, docs/protocol.md §The measures,
§Records analysed).

The records are the eight traps of ``tests/synthetic.py`` and the nine below. Each of the nine
passes every criterion of the base cohort, and seven also pass the analysis cohort, at the weeks on
either side of each landmark. The other two would leave at step 10, but fail step 8 or 9 first, so
they are counted there. The expected rows are written by hand from the records, never measured on
the database.

Tests marked ``db`` load the synthetic source through the ETL into schemas of this module's own,
dropped after it, and run the cohort SQL there.
"""

import datetime
import re
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import pytest

import cohorts
import etl
import sql_runner
from sinac_truncation.cohorts import SQL_FILES
from synthetic import RECORDS_2023, Source, fetch, module_schemas, pid, prepare_source

#: Records 9 to 17 of the 2023 file, in the order of SOURCE_COLUMNS: FECHANACIMIENTO,
#: FECHANACIMIENTOMADRE, EDAD, RESIDEEXTRANJERO, ENTIDADRESIDENCIA, EDADGESTACIONAL,
#: PRODUCTOEMBARAZO, TOTALCONSULTAS, TRIMESTREPRIMERCONSULTA, ESCOLARIDAD, SEXO, PESO. Each is the
#: normal case of record 1 (8 visits from the first trimester) but for its weeks and its trap.
LANDMARK_TRAPS_2023: tuple[tuple[str | None, ...], ...] = (
    # In the analysis cohort: the weeks on either side of each landmark, which is inclusive.
    # 9. 22 weeks, the first week of the base cohort.
    ("09/01/2023", "01/01/1990", "33", "2", "09", "22", "1", "8", "1", "51", "1", "3200"),
    # 10. 27 weeks.
    ("10/01/2023", "01/01/1990", "33", "2", "09", "27", "1", "8", "1", "51", "1", "3200"),
    # 11. 28 weeks.
    ("11/01/2023", "01/01/1990", "33", "2", "09", "28", "1", "8", "1", "51", "1", "3200"),
    # 12. 31 weeks.
    ("12/01/2023", "01/01/1990", "33", "2", "09", "31", "1", "8", "1", "51", "1", "3200"),
    # 13. 32 weeks.
    ("13/01/2023", "01/01/1990", "33", "2", "09", "32", "1", "8", "1", "51", "1", "3200"),
    # 14. 33 weeks.
    ("14/01/2023", "01/01/1990", "33", "2", "09", "33", "1", "8", "1", "51", "1", "3200"),
    # 15. 34 weeks.
    ("15/01/2023", "01/01/1990", "33", "2", "09", "34", "1", "8", "1", "51", "1", "3200"),
    # A record leaves at the first step it fails, so neither of these is counted at step 10.
    # 16. 27 weeks and a count of 99, "No Especificado": step 8.
    ("16/01/2023", "01/01/1990", "33", "2", "09", "27", "1", "99", "1", "51", "1", "3200"),
    # 17. 30 weeks and education 99, "SE IGNORA": step 9.
    ("17/01/2023", "01/01/1990", "33", "2", "09", "30", "1", "8", "1", "99", "1", "3200"),
)

#: The landmark files, as (file, definition, week): D-077 numbers a definition by its file, and
#: D-090 sets the weeks.
LANDMARKS: tuple[tuple[str, int, int], ...] = (
    ("03_landmark_28.sql", 3, 28),
    ("04_landmark_32.sql", 4, 32),
    ("05_landmark_34.sql", 5, 34),
)

#: The kind and description of steps 0 to 9 of every landmark cohort: those of definition 2.
STEPS: tuple[tuple[str | None, str], ...] = (
    (None, "Records in the files of the study period"),
    ("data model", "Mother's year of birth known"),
    ("coverage", "Born in the study period"),
    ("coverage", "Mother resident in Mexico"),
    ("validity", "Gestational age specified"),
    ("validity", "Multiplicity specified"),
    ("design", "Singleton"),
    ("design", "22 completed weeks or more"),
    ("validity", "Prenatal care data known and coherent"),
    ("validity", "Covariates known"),
)

#: (remaining, excluded) per step of the 2023 file, with --years 2023, up to step 9.
ATTRITION_TO_STEP_9: tuple[tuple[int, int | None], ...] = (
    (17, None),  # 0. The 8 records of RECORDS_2023 and the 9 above.
    (16, 1),  # 1. Record 6.
    (16, 0),  # 2. Every delivery is of 2023.
    (13, 3),  # 3. Records 4, 5 and 7.
    (13, 0),  # 4. Records 4, 5 and 7 carry the unknown weeks, and left at step 3.
    (13, 0),  # 5. Record 4, the same.
    (11, 2),  # 6. Records 3 and 8. Record 8, twins of 34 weeks, never reaches step 10.
    (11, 0),  # 7. Record 3 is the one under 22 weeks, and left at step 6.
    (10, 1),  # 8. Record 16.
    (9, 1),  # 9. Record 17. Left: records 1, 2 and 9 to 15.
)

#: The records of each landmark cohort: those of the analysis cohort that reached its week.
KEPT: dict[int, tuple[int, ...]] = {
    3: (1, 2, 11, 12, 13, 14, 15),
    4: (1, 2, 13, 14, 15),
    5: (1, 2, 15),
}


@pytest.fixture(scope="module")
def schemas(
    db_connection: sql_runner.Connection, ddl_files: Sequence[Path]
) -> Iterator[etl.Schemas]:
    with module_schemas(db_connection, ddl_files, "test_landmarks") as names:
        yield names


@pytest.fixture
def source(db_connection: sql_runner.Connection, schemas: etl.Schemas, tmp_path: Path) -> Source:
    """The synthetic source with the traps above staged as rows 9 to 17 of the 2023 file."""
    prepared = prepare_source(db_connection, schemas, tmp_path)
    prepared.stage(2023, (*RECORDS_2023, *LANDMARK_TRAPS_2023))
    results = schemas.results
    with db_connection.cursor() as cursor:
        cursor.execute(
            f"DROP TABLE IF EXISTS {results}.cohort, {results}.attrition, {results}.exposure"
        )
    return prepared


def built(source: Source) -> Source:
    source.run((2023,))
    cohorts.run(source.connection, (2023,), schemas=source.schemas)
    return source


def attrition(source: Source, definition: int) -> list[tuple[Any, ...]]:
    return fetch(
        source.connection,
        f"SELECT step, kind, description, remaining, excluded "
        f"FROM {source.schemas.results}.attrition "
        "WHERE cohort_definition_id = %s AND source_year = 2023 ORDER BY step",
        definition,
    )


def cohort(source: Source, definition: int) -> list[tuple[Any, ...]]:
    return fetch(
        source.connection,
        f"SELECT subject_id, cohort_start_date, cohort_end_date "
        f"FROM {source.schemas.results}.cohort WHERE cohort_definition_id = %s "
        "ORDER BY subject_id",
        definition,
    )


def code(text: str) -> str:
    """The SQL of a file without its comments."""
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("--"))


# --- The SQL of the landmark files: no database --------------------------------------------------


def test_the_landmark_files_run_after_the_analysis_cohort() -> None:
    names = [name for name, *_ in LANDMARKS]
    start = SQL_FILES.index("02_analysis.sql") + 1
    assert list(SQL_FILES[start : start + len(names)]) == names


def test_the_landmark_files_differ_only_in_their_definition_and_week() -> None:
    """A landmark is the same filter with another week (D-090), so a copy cannot drift."""
    texts = cohorts.read_sql()
    generic = set()
    for name, definition, week in LANDMARKS:
        body = code(texts[name])
        assert f"cohort_definition_id = {definition};" in body
        assert f"'Reached week {week}'" in body
        assert body.count(f"b.weeks >= {week}") == 2
        generic.add(re.sub(rf"\b{definition}\b", "<id>", re.sub(rf"\b{week}\b", "<week>", body)))
    assert len(generic) == 1


# --- The landmark cohorts on the compose database ------------------------------------------------


@pytest.mark.db
@pytest.mark.parametrize(
    ("definition", "remaining", "excluded"),
    [(3, 7, 2), (4, 5, 4), (5, 3, 6)],
    ids=["week-28", "week-32", "week-34"],
)
def test_step_10_removes_the_pregnancies_that_did_not_reach_the_week(
    source: Source, definition: int, remaining: int, excluded: int
) -> None:
    """Week 28 removes records 9 and 10; week 32 also 11 and 12; week 34 also 13 and 14."""
    built(source)
    week = {d: w for _, d, w in LANDMARKS}[definition]
    common = [
        (step, kind, description, left, out)
        for step, ((kind, description), (left, out)) in enumerate(
            zip(STEPS, ATTRITION_TO_STEP_9, strict=True)
        )
    ]
    assert attrition(source, definition) == [
        *common,
        (10, "design", f"Reached week {week}", remaining, excluded),
    ]
    # Its first steps are those of the analysis cohort, which the landmarks leave unchanged.
    assert attrition(source, 2) == common


@pytest.mark.db
def test_each_landmark_cohort_holds_the_records_that_reached_its_week(source: Source) -> None:
    built(source)
    records = dict(enumerate((*RECORDS_2023, *LANDMARK_TRAPS_2023), start=1))
    delivered = {
        row: datetime.datetime.strptime(str(record[0]), "%d/%m/%Y").date()
        for row, record in records.items()
    }
    assert [row[0] for row in cohort(source, 2)] == [pid(row) for row in (1, 2, *range(9, 16))]
    for definition, rows in KEPT.items():
        assert cohort(source, definition) == [
            (pid(row), delivered[row], delivered[row]) for row in rows
        ]
