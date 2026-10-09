"""Tests for measures (a) and (c) and the analysis cohort (task 1.6.1, docs/protocol.md §Exposure
measures, §Records analysed).

The records are the eight traps of ``tests/synthetic.py`` and the seventeen below. The eight give
measures for the values a record outside the base cohort can carry; each of the seventeen passes
every criterion of the base cohort and carries one trap of the declared prenatal care or of the
covariates, so each rule of steps 8 and 9 is the only reason some record leaves. The expected rows
are written by hand from the records, never measured on the database.

Tests marked ``db`` load the synthetic source through the ETL into schemas of this module's own,
dropped after it, and run the cohort SQL there.
"""

import csv
import datetime
import re
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import pytest

import cohorts
import etl
import sql_runner
from sinac_truncation.cohorts import TRIMESTER_CODES
from synthetic import RECORDS_2023, Source, fetch, module_schemas, pid, prepare_source

CONFIG = Path(__file__).resolve().parents[1] / "config"

#: Records 9 to 25 of the 2023 file, in the order of SOURCE_COLUMNS: FECHANACIMIENTO,
#: FECHANACIMIENTOMADRE, EDAD, RESIDEEXTRANJERO, ENTIDADRESIDENCIA, EDADGESTACIONAL,
#: PRODUCTOEMBARAZO, TOTALCONSULTAS, TRIMESTREPRIMERCONSULTA, ESCOLARIDAD, SEXO, PESO. Each is the
#: normal case of record 1 (8 visits from the first trimester) but for its trap.
EXPOSURE_TRAPS_2023: tuple[tuple[str | None, ...], ...] = (
    # Kept: the levels of (a) at each cut point, (c) for each answer, and the bound of rule 4.
    # 9. Zero visits and "NO RECIBIÓ": no care, which is an answer.
    ("09/01/2023", "01/01/1990", "33", "2", "09", "39", "1", "0", "0", "51", "1", "3200"),
    # 10. Four visits from the second trimester: the last count below the minimum of five.
    ("10/01/2023", "01/01/1990", "33", "2", "09", "39", "1", "4", "2", "51", "1", "3200"),
    # 11. Five visits from the first trimester: the minimum of the norm.
    ("11/01/2023", "01/01/1990", "33", "2", "09", "39", "1", "5", "1", "51", "1", "3200"),
    # 12. Seven visits from the third trimester, born at exactly 28 weeks: the bound is inclusive.
    ("12/01/2023", "01/01/1990", "33", "2", "09", "28", "1", "7", "3", "51", "1", "3200"),
    # Step 8, rule 2: the count is not known.
    # 13. 99, "No Especificado".
    ("13/01/2023", "01/01/1990", "33", "2", "09", "39", "1", "99", "1", "51", "1", "3200"),
    # 14. A blank count.
    ("14/01/2023", "01/01/1990", "33", "2", "09", "39", "1", None, "1", "51", "1", "3200"),
    # Step 8, rule 1: the trimester is not known.
    # 15. 8, "NO ESPECIFICADO".
    ("15/01/2023", "01/01/1990", "33", "2", "09", "39", "1", "6", "8", "51", "1", "3200"),
    # 16. Zero visits with 9, "SE IGNORA": an unknown start, not no care (D-086).
    ("16/01/2023", "01/01/1990", "33", "2", "09", "39", "1", "0", "9", "51", "1", "3200"),
    # 17. A blank trimester.
    ("17/01/2023", "01/01/1990", "33", "2", "09", "39", "1", "6", None, "51", "1", "3200"),
    # Step 8, rule 3: the two items disagree.
    # 18. Zero visits, and a first visit in the first trimester.
    ("18/01/2023", "01/01/1990", "33", "2", "09", "39", "1", "0", "1", "51", "1", "3200"),
    # 19. "NO RECIBIÓ", and three visits.
    ("19/01/2023", "01/01/1990", "33", "2", "09", "39", "1", "3", "0", "51", "1", "3200"),
    # Step 8, rule 4: a first visit in the third trimester of a pregnancy that ended at 27 weeks.
    ("20/01/2023", "01/01/1990", "33", "2", "09", "27", "1", "5", "3", "51", "1", "3200"),
    # Step 9: one covariate unknown.
    # 21. Age 999, "NO ESPECIFICADO"; the mother's date of birth still loads her (D-060).
    ("21/01/2023", "01/01/1990", "999", "2", "09", "39", "1", "8", "1", "51", "1", "3200"),
    # 22. Education 99, "SE IGNORA".
    ("22/01/2023", "01/01/1990", "33", "2", "09", "39", "1", "8", "1", "99", "1", "3200"),
    # 23. A blank education.
    ("23/01/2023", "01/01/1990", "33", "2", "09", "39", "1", "8", "1", None, "1", "3200"),
    # 24. State 99, "SE IGNORA", of a mother resident in Mexico.
    ("24/01/2023", "01/01/1990", "33", "2", "99", "39", "1", "8", "1", "51", "1", "3200"),
    # 25. An unknown count and an unknown education: counted at step 8 only.
    ("25/01/2023", "01/01/1990", "33", "2", "09", "39", "1", "99", "1", "0", "1", "3200"),
)

#: One row of results.exposure per mother PERSON, as (row of the file, visits, trimester of the
#: first visit, level of (a), (c)). Record 6 is not loaded (D-060), so it has none.
EXPECTED_EXPOSURE: tuple[tuple[int, int | None, int | None, str | None, bool | None], ...] = (
    (1, 8, 1, "8+", True),
    (2, 8, 1, "8+", True),
    # 45 visits, out of any plausible range, is a count as it is (D-058).
    (3, 45, 0, "8+", False),
    # 99 and code 8; blanks; a count that does not cast and a trimester the catalogue lacks.
    (4, None, None, None, None),
    (5, None, None, None, None),
    (7, None, None, None, None),
    # Incoherent, so it would leave at step 8, but the measures are the values declared.
    (8, 0, 1, "0", True),
    (9, 0, 0, "0", False),
    (10, 4, 2, "1-4", False),
    (11, 5, 1, "5-7", True),
    (12, 7, 3, "5-7", False),
    (13, None, 1, None, True),
    (14, None, 1, None, True),
    (15, 6, None, "5-7", None),
    (16, 0, None, "0", None),
    (17, 6, None, "5-7", None),
    (18, 0, 1, "0", True),
    (19, 3, 0, "1-4", False),
    (20, 5, 3, "5-7", False),
    (21, 8, 1, "8+", True),
    (22, 8, 1, "8+", True),
    (23, 8, 1, "8+", True),
    (24, 8, 1, "8+", True),
    (25, None, 1, None, True),
)

#: The kind and description of each step of definition 2: those of the base cohort, then two.
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

#: (remaining, excluded) per step of the 2023 file, with --years 2023.
EXPECTED_ATTRITION: tuple[tuple[int, int | None], ...] = (
    (25, None),  # 0. The 8 records of RECORDS_2023 and the 17 above.
    (24, 1),  # 1. Record 6.
    (24, 0),  # 2. Every delivery is of 2023.
    (21, 3),  # 3. Records 4, 5 and 7.
    (21, 0),  # 4. Records 4, 5 and 7 carry the unknown weeks, and left at step 3.
    (21, 0),  # 5. Record 4, the same.
    (19, 2),  # 6. Records 3 and 8.
    (19, 0),  # 7. Record 3 is the one under 22 weeks, and left at step 6.
    (10, 9),  # 8. Records 13 to 20, and 25.
    (6, 4),  # 9. Records 21 to 24. Left: records 1, 2 and 9 to 12.
)


@pytest.fixture(scope="module")
def schemas(
    db_connection: sql_runner.Connection, ddl_files: Sequence[Path]
) -> Iterator[etl.Schemas]:
    with module_schemas(db_connection, ddl_files, "test_exposure") as names:
        yield names


@pytest.fixture
def source(db_connection: sql_runner.Connection, schemas: etl.Schemas, tmp_path: Path) -> Source:
    """The synthetic source with the traps above staged as rows 9 to 25 of the 2023 file."""
    prepared = prepare_source(db_connection, schemas, tmp_path)
    prepared.stage(2023, (*RECORDS_2023, *EXPOSURE_TRAPS_2023))
    results = schemas.results
    with db_connection.cursor() as cursor:
        cursor.execute(
            f"DROP TABLE IF EXISTS {results}.cohort, {results}.attrition, {results}.exposure"
        )
    return prepared


def built(source: Source, years: Sequence[int] = (2023,)) -> Source:
    source.run(years)
    cohorts.run(source.connection, years, schemas=source.schemas)
    return source


def exposure(source: Source) -> list[tuple[Any, ...]]:
    return fetch(
        source.connection,
        f"SELECT subject_id, visits, first_visit_trimester, visits_level, first_trimester_start "
        f"FROM {source.schemas.results}.exposure ORDER BY subject_id",
    )


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


def records() -> dict[int, Sequence[str | None]]:
    return dict(enumerate((*RECORDS_2023, *EXPOSURE_TRAPS_2023), start=1))


# --- The SQL against the real configuration: no database -----------------------------------------


def test_the_trimester_codes_are_the_ones_the_sql_reads() -> None:
    """exposure.sql reads codes 0 to 3 of TRIMESTRE_PRIMER_CONSULTA, each a concept of its own."""
    text = cohorts.read_sql()["exposure.sql"]
    vocabulary = TRIMESTER_CODES[0][0]
    listed = ", ".join(f"'{code}'" for _, code in TRIMESTER_CODES)
    assert f"source_vocabulary_id = '{vocabulary}'" in text
    assert f"source_code IN ({listed})" in text
    with (CONFIG / "source_to_concept_map.csv").open(encoding="utf-8", newline="") as handle:
        targets = {
            (row["source_vocabulary_id"], row["source_code"]): int(row["target_concept_id"])
            for row in csv.DictReader(handle)
        }
    concepts = [targets[code] for code in TRIMESTER_CODES]
    assert 0 not in concepts
    assert len(set(concepts)) == len(TRIMESTER_CODES)


def test_no_cohort_sql_reads_a_visit_or_its_date() -> None:
    """SINAC records no date of a visit (rule 4 of CLAUDE.md, D-066)."""
    for name, text in cohorts.read_sql().items():
        read = re.findall(r"visit_occurrence|visit_detail|observation_date", text)
        assert read == [], f"sql/cohorts/{name} reads {read}"


# --- The measures and the analysis cohort on the compose database --------------------------------


@pytest.mark.db
def test_the_measures_are_the_declared_care_of_every_mother(source: Source) -> None:
    built(source)
    assert exposure(source) == [
        (pid(row), visits, trimester, level, first)
        for row, visits, trimester, level, first in EXPECTED_EXPOSURE
    ]


@pytest.mark.db
def test_each_step_of_the_analysis_cohort_removes_the_records_its_rules_name(
    source: Source,
) -> None:
    built(source)
    expected = [
        (step, kind, description, remaining, excluded)
        for step, ((kind, description), (remaining, excluded)) in enumerate(
            zip(STEPS, EXPECTED_ATTRITION, strict=True)
        )
    ]
    assert attrition(source, 2) == expected
    # Its first steps are those of the base cohort, which the analysis cohort leaves unchanged.
    assert attrition(source, 1) == expected[:8]


@pytest.mark.db
def test_the_analysis_cohort_holds_the_records_that_pass_both_steps(source: Source) -> None:
    built(source)
    delivered = {
        row: datetime.datetime.strptime(str(record[0]), "%d/%m/%Y").date()
        for row, record in records().items()
    }
    assert cohort(source, 2) == [
        (pid(row), delivered[row], delivered[row]) for row in (1, 2, 9, 10, 11, 12)
    ]


@pytest.mark.db
def test_the_measures_are_those_of_the_files_of_the_last_run(source: Source) -> None:
    """As the cohorts, results.exposure holds the mothers of the files of --years only."""
    built(source, (2022, 2023))
    assert {pid(row, 2022) for row in (1, 2)} <= {row[0] for row in exposure(source)}
    cohorts.run(source.connection, (2023,), schemas=source.schemas)
    assert [row[0] for row in exposure(source)] == [pid(row) for row, *_ in EXPECTED_EXPOSURE]
