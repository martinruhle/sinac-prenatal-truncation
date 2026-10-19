"""Tests for the analysis cohort with multiple pregnancies, definition 6 (task 1.8.1,
docs/protocol.md §Sensitivity of the definition).

The records are the eight traps of ``tests/synthetic.py`` and the five multiple pregnancies below.
Two pass every criterion but "Singleton"; each of the other three fails one step of definition 6.
The expected rows are written by hand from the records, never measured on the database.

Tests marked ``db`` load the synthetic source through the ETL into schemas of this module's own,
dropped after it, and run the cohort SQL there.
"""

import datetime
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import pytest

import cohorts
import etl
import sql_runner
from sinac_truncation.cohorts import MULTIPLES_DEFINITION, SQL_FILES
from synthetic import RECORDS_2023, Source, fetch, module_schemas, pid, prepare_source

#: Records 9 to 13 of the 2023 file, in the order of SOURCE_COLUMNS: FECHANACIMIENTO,
#: FECHANACIMIENTOMADRE, EDAD, RESIDEEXTRANJERO, ENTIDADRESIDENCIA, EDADGESTACIONAL,
#: PRODUCTOEMBARAZO, TOTALCONSULTAS, TRIMESTREPRIMERCONSULTA, ESCOLARIDAD, SEXO, PESO. Each is the
#: normal case of record 1 (8 visits from the first trimester) but for its plurality and its trap.
MULTIPLE_TRAPS_2023: tuple[tuple[str | None, ...], ...] = (
    # 9. Twins, "GEMELAR": in definition 6.
    ("09/01/2023", "01/01/1990", "33", "2", "09", "36", "2", "8", "1", "51", "1", "2600"),
    # 10. Triplets or more, "TRES O MÁS": in definition 6.
    ("10/01/2023", "01/01/1990", "33", "2", "09", "33", "3", "8", "1", "51", "1", "1900"),
    # 11. Twins of 21 weeks: step 6.
    ("11/01/2023", "01/01/1990", "33", "2", "09", "21", "2", "8", "1", "51", "1", "450"),
    # 12. Twins with a count of 99, "No Especificado": step 7.
    ("12/01/2023", "01/01/1990", "33", "2", "09", "36", "2", "99", "1", "51", "1", "2600"),
    # 13. Twins with education 99, "SE IGNORA": step 8.
    ("13/01/2023", "01/01/1990", "33", "2", "09", "36", "2", "8", "1", "99", "1", "2600"),
)

#: The steps of definition 2 without "Singleton", as (kind, description, remaining, excluded) of
#: the 2023 file with --years 2023.
ATTRITION: tuple[tuple[str | None, str, int, int | None], ...] = (
    (None, "Records in the files of the study period", 13, None),
    ("data model", "Mother's year of birth known", 12, 1),  # Record 6.
    ("coverage", "Born in the study period", 12, 0),
    ("coverage", "Mother resident in Mexico", 9, 3),  # Records 4, 5 and 7.
    ("validity", "Gestational age specified", 9, 0),  # Records 4, 5 and 7 left at step 3.
    ("validity", "Multiplicity specified", 9, 0),  # Record 4, the same.
    ("design", "22 completed weeks or more", 7, 2),  # Records 3 (triplets of 12 weeks) and 11.
    # Record 8, twins with no visits and a first visit in the first trimester, and record 12.
    ("validity", "Prenatal care data known and coherent", 5, 2),
    ("validity", "Covariates known", 4, 1),  # Record 13. Left: records 1, 2, 9 and 10.
)

#: Definition 2 on the same records: "Singleton" removes records 3 and 8 and the five above.
ATTRITION_2: tuple[tuple[int, int | None], ...] = (
    (13, None),
    (12, 1),
    (12, 0),
    (9, 3),
    (9, 0),
    (9, 0),
    (2, 7),
    (2, 0),
    (2, 0),
    (2, 0),
)


@pytest.fixture(scope="module")
def schemas(
    db_connection: sql_runner.Connection, ddl_files: Sequence[Path]
) -> Iterator[etl.Schemas]:
    with module_schemas(db_connection, ddl_files, "test_multiples") as names:
        yield names


@pytest.fixture
def source(db_connection: sql_runner.Connection, schemas: etl.Schemas, tmp_path: Path) -> Source:
    """The synthetic source with the traps above staged as rows 9 to 13 of the 2023 file."""
    prepared = prepare_source(db_connection, schemas, tmp_path)
    prepared.stage(2023, (*RECORDS_2023, *MULTIPLE_TRAPS_2023))
    results = schemas.results
    with db_connection.cursor() as cursor:
        cursor.execute(
            f"DROP TABLE IF EXISTS {results}.cohort, {results}.attrition, {results}.exposure, "
            f"{results}.excluded_profile"
        )
    source = prepared
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


# --- The SQL of the file: no database ------------------------------------------------------------


def test_the_definition_with_multiples_runs_after_the_other_definitions() -> None:
    """It reads the criteria of 01_base.sql and 02_analysis.sql, and attrition.sql counts it."""
    position = SQL_FILES.index("06_multiples.sql")
    assert SQL_FILES.index("05_landmark_34.sql") < position < SQL_FILES.index("attrition.sql")


def test_the_file_is_the_definition_of_its_number_and_drops_the_singleton_criterion_alone() -> None:
    """D-077 numbers a definition by its file; D-054 lets the axis change one side only."""
    text = cohorts.read_sql()["06_multiples.sql"]
    code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("--"))
    assert f"cohort_definition_id = {MULTIPLES_DEFINITION};" in code
    assert "singleton" not in code
    for criterion in (
        "born_in_period",
        "resident_in_mexico",
        "weeks_specified",
        "multiplicity_specified",
        "at_least_22_weeks",
        "prenatal_care_known",
        "covariates_known",
    ):
        assert code.count(criterion) == 2, criterion


# --- The cohort on the compose database ----------------------------------------------------------


@pytest.mark.db
def test_the_attrition_is_that_of_the_analysis_cohort_without_the_singleton_step(
    source: Source,
) -> None:
    assert attrition(source, MULTIPLES_DEFINITION) == [
        (step, kind, description, remaining, excluded)
        for step, (kind, description, remaining, excluded) in enumerate(ATTRITION)
    ]
    # Definition 2 is unchanged: its step 6 removes the multiples.
    assert [row[3:] for row in attrition(source, 2)] == list(ATTRITION_2)


@pytest.mark.db
def test_the_cohort_is_the_analysis_cohort_and_the_multiples_that_pass(source: Source) -> None:
    records = dict(enumerate((*RECORDS_2023, *MULTIPLE_TRAPS_2023), start=1))
    delivered = {
        row: datetime.datetime.strptime(str(record[0]), "%d/%m/%Y").date()
        for row, record in records.items()
    }
    assert [row[0] for row in cohort(source, 2)] == [pid(1), pid(2)]
    assert cohort(source, MULTIPLES_DEFINITION) == [
        (pid(row), delivered[row], delivered[row]) for row in (1, 2, 9, 10)
    ]


@pytest.mark.db
def test_its_validity_steps_are_profiled(source: Source) -> None:
    """Steps 4, 5, 7 and 8; cohorts.run already checked their counts against the attrition."""
    assert fetch(
        source.connection,
        f"SELECT DISTINCT step FROM {source.schemas.results}.excluded_profile "
        "WHERE cohort_definition_id = %s ORDER BY step",
        MULTIPLES_DEFINITION,
    ) == [(4,), (5,), (7,), (8,)]
