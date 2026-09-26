"""Tests for the base cohort and its attrition (task 1.5.1, docs/protocol.md §Base cohort).

The records are the traps of ``tests/synthetic.py``, the eight the ETL tests load, plus the seven
below. Those eight leave nobody at steps 2, 4, 5 and 7: every record with an unknown gestational age
or plurality also lives abroad and leaves at step 3 first. A step that removes nobody in the fixture
would pass whether its criterion works or not, so each added record is the only one, or one of two,
that a step removes. The expected counts are written by hand from the records, never measured on the
database, and each carries the records it comes from.

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
import yaml

import cohorts
import etl
import pipeline
import sql_runner
from sinac_truncation.cohorts import (
    MEXICO_CODE,
    SQL_FILES,
    AttritionStep,
    attrition_problems,
    cited_concept_keys,
    format_attrition,
)
from sinac_truncation.etl import concept_keys, vocabulary_ids
from synthetic import (
    RECORDS_2022,
    RECORDS_2023,
    Source,
    fetch,
    module_schemas,
    pid,
    prepare_source,
)

CONFIG = Path(__file__).resolve().parents[1] / "config"

#: Records 9 to 15 of the 2023 file, in the order of SOURCE_COLUMNS: FECHANACIMIENTO,
#: FECHANACIMIENTOMADRE, EDAD, RESIDEEXTRANJERO, ENTIDADRESIDENCIA, EDADGESTACIONAL,
#: PRODUCTOEMBARAZO, TOTALCONSULTAS, TRIMESTREPRIMERCONSULTA. Each is the normal case of record 1
#: but for its trap.
COHORT_TRAPS_2023: tuple[tuple[str | None, ...], ...] = (
    # 9. A birth of 2022 in the 2023 file: leaves at step 2 when --years is 2023 (D-073).
    ("31/12/2022", "01/01/1990", "32", "2", "09", "39", "1", "8", "1"),
    # 10. RESIDEEXTRANJERO blank, so country_concept_id is NULL: unknown is not Mexico (step 3).
    ("10/10/2023", "01/01/1990", "33", None, "09", "39", "1", "8", "1"),
    # 11. Weeks 99 and plurality 0: fails criteria 3 and 4, counted only at step 4.
    ("11/11/2023", "01/01/1990", "33", "2", "09", "99", "0", "8", "1"),
    # 12. Weeks that do not cast (D-075): NULL in the CDM, so not specified (step 4).
    ("12/11/2023", "01/01/1990", "33", "2", "09", " 38", "1", "8", "1"),
    # 13. Plurality 0, "NO ESPECIFICADO": step 5.
    ("13/11/2023", "01/01/1990", "33", "2", "09", "38", "0", "8", "1"),
    # 14. A singleton born at 21 weeks: step 7.
    ("14/11/2023", "01/01/1990", "33", "2", "09", "21", "1", "8", "1"),
    # 15. A singleton born at exactly 22 weeks: the bound is inclusive (NOM-007 §3.45), it stays.
    ("15/11/2023", "01/01/1990", "33", "2", "09", "22", "1", "8", "1"),
)

#: The description and kind of each step, as docs/protocol.md §Attrition writes them.
STEPS: tuple[tuple[str | None, str], ...] = (
    (None, "Records in the files of the study period"),
    ("data model", "Mother's year of birth known"),
    ("coverage", "Born in the study period"),
    ("coverage", "Mother resident in Mexico"),
    ("validity", "Gestational age specified"),
    ("validity", "Multiplicity specified"),
    ("design", "Singleton"),
    ("design", "22 completed weeks or more"),
)

#: (remaining, excluded) per step of the 2023 file, with --years 2023.
EXPECTED_2023: tuple[tuple[int, int | None], ...] = (
    # 0. The 8 records of RECORDS_2023 and the 7 of COHORT_TRAPS_2023.
    (15, None),
    # 1. Record 6: neither the mother's date of birth nor her age (D-060).
    (14, 1),
    # 2. Record 9: born on 31/12/2022.
    (13, 1),
    # 3. Records 4 (code 88, not in SI_NO), 5 (1, resides abroad), 7 (3, not in SI_NO) and
    #    10 (blank).
    (9, 4),
    # 4. Records 11 (99) and 12 (" 38").
    (7, 2),
    # 5. Record 13 (0).
    (6, 1),
    # 6. Records 3 (three or more, and 12 weeks: it leaves here, before step 7) and 8 (twins).
    (4, 2),
    # 7. Record 14 (21 weeks). Left: records 1, 2 (the exact duplicate of 1, D-058) and 15.
    (3, 1),
)

#: With the 2022 and 2023 files and --years 2022,2023.
EXPECTED_2023_OF_2022_2023: tuple[tuple[int, int | None], ...] = (
    (15, None),  # 0. As with --years 2023.
    (14, 1),  # 1. Record 6.
    (14, 0),  # 2. Record 9 was born in 2022, which is now in the study period.
    (10, 4),  # 3. Records 4, 5, 7, 10.
    (8, 2),  # 4. Records 11, 12.
    (7, 1),  # 5. Record 13.
    (5, 2),  # 6. Records 3, 8.
    (4, 1),  # 7. Record 14. Left: records 1, 2, 9, 15.
)

#: Both 2022 records are singletons of 38 and 36 weeks whose mothers live in Mexico: nobody leaves.
EXPECTED_2022: tuple[tuple[int, int | None], ...] = ((2, None),) + ((2, 0),) * 7


def expected_rows(
    year: int, counts: Sequence[tuple[int, int | None]]
) -> list[tuple[int, int, int, str | None, str, int, int | None]]:
    return [
        (1, year, step, kind, description, remaining, excluded)
        for step, ((kind, description), (remaining, excluded)) in enumerate(
            zip(STEPS, counts, strict=True)
        )
    ]


# --- The invariants of an attrition table: no database -------------------------------------------


def table(
    counts: Sequence[tuple[int, int | None]], year: int = 2023, definition: int = 1
) -> list[AttritionStep]:
    return [
        AttritionStep(definition, year, step, None, f"step {step}", remaining, excluded)
        for step, (remaining, excluded) in enumerate(counts)
    ]


CONSISTENT = [(10, None), (9, 1), (9, 0), (5, 4)]


def test_a_consistent_attrition_has_no_problems() -> None:
    assert attrition_problems(table(CONSISTENT), {(1, 2023): 5}) == []
    two_years = table(CONSISTENT) + table([(3, None), (3, 0)], year=2022)
    assert attrition_problems(two_years, {(1, 2023): 5, (1, 2022): 3}) == []


@pytest.mark.parametrize(
    ("steps", "cohort_rows", "problem"),
    [
        (
            table([(10, None), (9, 1), (10, -1), (5, 5)]),
            {(1, 2023): 5},
            "definition 1, 2023, step 2: 10 remain after 9, and a step cannot add records",
        ),
        (
            table([(10, None), (9, 1), (9, 2), (5, 4)]),
            {(1, 2023): 5},
            "definition 1, 2023, step 2: 2 excluded, but 9 - 9 = 0",
        ),
        (
            table(CONSISTENT),
            {(1, 2023): 4},
            "definition 1, 2023: the last step leaves 5 and the cohort holds 4 rows",
        ),
        (
            table(CONSISTENT),
            {},
            "definition 1, 2023: the last step leaves 5 and the cohort holds 0 rows",
        ),
        (
            table(CONSISTENT) + table([(3, None), (3, 0)], year=2022),
            {(1, 2023): 5},
            "definition 1, 2022: the last step leaves 3 and the cohort holds 0 rows",
        ),
        (
            [step for step in table(CONSISTENT) if step.step != 2],
            {(1, 2023): 5},
            "definition 1, 2023: the steps are 0, 1, 3, not 0 to 2",
        ),
        (
            table([(10, 0), (9, 1)]),
            {(1, 2023): 9},
            "definition 1, 2023, step 0: excluded is 0, and step 0 excludes nobody",
        ),
        (
            table([(10, None), (9, None)]),
            {(1, 2023): 9},
            "definition 1, 2023, step 1: excluded is missing",
        ),
        (
            table([(10, None), (-1, 11)]),
            {(1, 2023): -1},
            "definition 1, 2023, step 1: remaining is negative",
        ),
        (
            table(CONSISTENT),
            {(1, 2023): 5, (2, 2023): 7},
            "definition 2, 2023: the cohort holds 7 rows and there is no attrition",
        ),
    ],
    ids=[
        "counts-grow",
        "excluded-inconsistent",
        "last-step-not-the-cohort",
        "no-cohort-rows",
        "one-year-without-cohort-rows",
        "a-step-missing",
        "step-0-excludes",
        "excluded-missing",
        "negative",
        "cohort-without-attrition",
    ],
)
def test_each_broken_invariant_is_named(
    steps: list[AttritionStep], cohort_rows: dict[tuple[int, int], int], problem: str
) -> None:
    assert problem in attrition_problems(steps, cohort_rows)


def test_the_report_has_one_line_per_step_in_order() -> None:
    steps = table([(1_521_280, None), (1_521_280, 0)])
    lines = format_attrition(list(reversed(steps)))
    assert len(lines) == 3
    assert lines[0].split() == [
        "definition",
        "year",
        "step",
        "kind",
        "description",
        "remaining",
        "excluded",
    ]
    assert lines[1].split()[:3] == ["1", "2023", "0"]
    assert lines[1].split()[-1] == "1,521,280"  # step 0 excludes nobody: the column is empty
    assert lines[2].split()[-2:] == ["1,521,280", "0"]


# --- The real SQL against the real configuration: no database ---------------------------------


def real_config() -> dict[str, Any]:
    document = yaml.safe_load((CONFIG / "concept_sets.yml").read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def test_every_sql_file_of_the_cohorts_exists() -> None:
    assert set(cohorts.read_sql()) == set(SQL_FILES)
    assert sorted(path.name for path in cohorts.SQL_DIR.glob("*.sql")) == sorted(SQL_FILES)


def test_the_cohort_sql_cites_configured_concepts_only() -> None:
    config = real_config()
    texts = cohorts.read_sql()
    assert cited_concept_keys(texts) == {"gestational_age_at_birth", "birth_plurality"}
    assert cited_concept_keys(texts) <= set(config["concepts"])
    cited_vocabularies = set().union(*(vocabulary_ids(text) for text in texts.values()))
    assert cited_vocabularies == {MEXICO_CODE[0]}
    assert cited_concept_keys(texts) == set().union(*(concept_keys(t) for t in texts.values()))


def test_no_configured_concept_id_is_written_in_the_cohort_sql() -> None:
    """Rule 8: the ids come from results.concept_sets or from the map (D-074)."""
    config = real_config()
    ids = {int(entry["concept_id"]) for entry in config["concepts"].values()}
    with (CONFIG / "source_to_concept_map.csv").open(encoding="utf-8", newline="") as handle:
        ids |= {int(row["target_concept_id"]) for row in csv.DictReader(handle)}
    ids.discard(0)
    for name, text in cohorts.read_sql().items():
        written = [concept for concept in ids if re.search(rf"\b{concept}\b", text)]
        assert written == [], f"sql/cohorts/{name} writes {written}"


def test_the_code_the_runner_checks_is_the_one_criterion_2_reads() -> None:
    """The map must send RESIDEEXTRANJERO 2 ("NO", catalogue SI_NO) to a concept (D-068)."""
    vocabulary, code = MEXICO_CODE
    text = cohorts.read_sql()["01_base.sql"]
    assert f"source_vocabulary_id = '{vocabulary}'" in text
    assert f"source_code = '{code}'" in text
    with (CONFIG / "source_to_concept_map.csv").open(encoding="utf-8", newline="") as handle:
        targets = [
            int(row["target_concept_id"])
            for row in csv.DictReader(handle)
            if (row["source_vocabulary_id"], row["source_code"]) == MEXICO_CODE
        ]
    assert len(targets) == 1 and targets[0] != 0


def test_pipeline_cohorts_takes_years() -> None:
    args = pipeline.build_parser().parse_args(["cohorts", "--years", "2022,2023"])
    assert (args.command, args.years) == ("cohorts", (2022, 2023))
    assert pipeline.build_parser().parse_args(["cohorts"]).years == (2020, 2021, 2022, 2023)


# --- The cohort on the compose database -----------------------------------------------------------


@pytest.fixture(scope="module")
def schemas(
    db_connection: sql_runner.Connection, ddl_files: Sequence[Path]
) -> Iterator[etl.Schemas]:
    with module_schemas(db_connection, ddl_files, "test_cohorts") as names:
        yield names


@pytest.fixture
def source(db_connection: sql_runner.Connection, schemas: etl.Schemas, tmp_path: Path) -> Source:
    """The synthetic source with the cohort traps staged as rows 9 to 15 of the 2023 file."""
    prepared = prepare_source(db_connection, schemas, tmp_path)
    prepared.stage(2023, (*RECORDS_2023, *COHORT_TRAPS_2023))
    results = schemas.results
    with db_connection.cursor() as cursor:
        cursor.execute(f"DROP TABLE IF EXISTS {results}.cohort, {results}.attrition")
    return prepared


def run_cohorts(source: Source, years: Sequence[int]) -> list[AttritionStep]:
    return cohorts.run(source.connection, years, schemas=source.schemas)


def attrition(source: Source) -> list[tuple[Any, ...]]:
    return fetch(
        source.connection,
        f"SELECT cohort_definition_id, source_year, step, kind, description, remaining, excluded "
        f"FROM {source.schemas.results}.attrition "
        "ORDER BY cohort_definition_id, source_year, step",
    )


def cohort(source: Source) -> list[tuple[Any, ...]]:
    return fetch(
        source.connection,
        f"SELECT cohort_definition_id, subject_id, cohort_start_date, cohort_end_date "
        f"FROM {source.schemas.results}.cohort ORDER BY cohort_definition_id, subject_id",
    )


def snapshot(source: Source) -> dict[str, list[tuple[Any, ...]]]:
    return {"cohort": cohort(source), "attrition": attrition(source)}


def delivery(record: Sequence[str | None]) -> datetime.date:
    return datetime.datetime.strptime(str(record[0]), "%d/%m/%Y").date()


def cohort_row(row: int, record: Sequence[str | None], year: int = 2023) -> tuple[Any, ...]:
    """A row of the base cohort (definition 1): start and end are the delivery day (D-062)."""
    return (1, pid(row, year), delivery(record), delivery(record))


@pytest.mark.db
def test_each_step_removes_the_records_its_criterion_names(source: Source) -> None:
    source.run((2023,))
    returned = run_cohorts(source, (2023,))
    assert attrition(source) == expected_rows(2023, EXPECTED_2023)
    assert [tuple(step) for step in returned] == attrition(source)


@pytest.mark.db
def test_the_cohort_holds_the_records_that_pass_every_criterion(source: Source) -> None:
    source.run((2023,))
    run_cohorts(source, (2023,))
    assert cohort(source) == [
        cohort_row(1, RECORDS_2023[0]),
        cohort_row(2, RECORDS_2023[1]),  # The exact duplicate of 1 stays (D-058).
        cohort_row(15, COHORT_TRAPS_2023[6]),  # 22 weeks.
    ]


@pytest.mark.db
@pytest.mark.parametrize("years", [(2023,), (2022, 2023)], ids=["2023", "2022-2023"])
def test_the_attrition_invariants_hold(source: Source, years: tuple[int, ...]) -> None:
    source.run(years)
    run_cohorts(source, years)
    rows = attrition(source)
    rows_per_file = range(1, len(RECORDS_2023) + len(COHORT_TRAPS_2023) + 1)
    year_of = {pid(row, year): year for year in years for row in rows_per_file}
    in_cohort: dict[int, int] = {}
    for _, subject, *_ in cohort(source):
        in_cohort[year_of[subject]] = in_cohort.get(year_of[subject], 0) + 1

    assert {row[1] for row in rows} == set(years)
    for year in years:
        steps = [row for row in rows if row[1] == year]
        assert [row[2] for row in steps] == list(range(len(STEPS)))
        remaining = [row[5] for row in steps]
        excluded = [row[6] for row in steps]
        # Counts never grow from one step to the next.
        assert remaining == sorted(remaining, reverse=True)
        # Each step excludes exactly what it removes, and step 0 excludes nobody.
        assert excluded[0] is None
        assert excluded[1:] == [
            before - after for before, after in zip(remaining[:-1], remaining[1:], strict=True)
        ]
        # The last step leaves exactly the rows of the cohort.
        assert remaining[-1] == in_cohort.get(year, 0)


@pytest.mark.db
def test_the_study_period_is_years_not_the_file(source: Source) -> None:
    """Criterion 1 reads the delivery date, and step 0 the files of --years (D-073)."""
    source.run((2022, 2023))
    run_cohorts(source, (2022, 2023))
    assert attrition(source) == expected_rows(2022, EXPECTED_2022) + expected_rows(
        2023, EXPECTED_2023_OF_2022_2023
    )
    assert cohort(source) == [
        cohort_row(1, RECORDS_2022[0], 2022),
        cohort_row(2, RECORDS_2022[1], 2022),
        cohort_row(1, RECORDS_2023[0]),
        cohort_row(2, RECORDS_2023[1]),
        cohort_row(9, COHORT_TRAPS_2023[0]),  # Born in 2022, which is now in the period.
        cohort_row(15, COHORT_TRAPS_2023[6]),
    ]

    # The same CDM with --years 2023: the 2022 file is not in step 0, and record 9 leaves again.
    run_cohorts(source, (2023,))
    assert attrition(source) == expected_rows(2023, EXPECTED_2023)


@pytest.mark.db
def test_two_runs_leave_the_same_cohort_and_attrition(source: Source) -> None:
    source.run((2022, 2023))
    run_cohorts(source, (2022, 2023))
    first = snapshot(source)
    run_cohorts(source, (2022, 2023))
    assert snapshot(source) == first


@pytest.mark.db
def test_a_year_the_cdm_does_not_hold_is_refused_before_anything_is_touched(
    source: Source,
) -> None:
    source.run((2023,))
    run_cohorts(source, (2023,))
    before = snapshot(source)
    message = "run `pipeline.py cdm --years 2022-2023` first"
    with pytest.raises(cohorts.CohortError, match=re.escape(message)):
        run_cohorts(source, (2022, 2023))
    assert snapshot(source) == before


def _more_staged_than_loaded(source: Source) -> None:
    with source.connection.cursor() as cursor:
        cursor.execute(
            f"UPDATE {source.schemas.results}.etl_counts SET row_count = row_count + 1 "
            "WHERE source_year = 2023 AND cdm_table = 'staging' AND rule = 'rows'"
        )


@pytest.mark.db
def test_a_broken_invariant_keeps_the_previous_cohort(source: Source) -> None:
    """16 staged, 1 not loaded and 14 PERSON rows: step 1 cannot be consistent."""
    source.run((2023,))
    run_cohorts(source, (2023,))
    before = snapshot(source)
    _more_staged_than_loaded(source)
    with pytest.raises(cohorts.CohortError, match="the previous cohort was kept") as raised:
        run_cohorts(source, (2023,))
    assert "definition 1, 2023, step 1: 1 excluded, but 16 - 14 = 2" in str(raised.value)
    assert snapshot(source) == before


def _no_plurality_concept(source: Source) -> None:
    with source.connection.cursor() as cursor:
        cursor.execute(
            f"DELETE FROM {source.schemas.results}.concept_sets "
            "WHERE concept_key = 'birth_plurality'"
        )


def _no_mexico_in_the_map(source: Source) -> None:
    with source.connection.cursor() as cursor:
        cursor.execute(
            f"DELETE FROM {source.schemas.cdm}.source_to_concept_map "
            "WHERE source_vocabulary_id = 'SINAC20_RESEXT' AND source_code = '2'"
        )


@pytest.mark.db
@pytest.mark.parametrize(
    ("damage", "message"),
    [
        (_no_plurality_concept, "lacks the concept 'birth_plurality'"),
        (_no_mexico_in_the_map, "maps SINAC20_RESEXT '2' to 0 concepts"),
    ],
    ids=["no-plurality-key", "no-mexico-target"],
)
def test_a_concept_the_cohort_cannot_read_is_refused(
    source: Source, damage: Any, message: str
) -> None:
    """A missing concept would be NULL, and a NULL criterion would silently exclude everyone."""
    source.run((2023,))
    run_cohorts(source, (2023,))
    before = snapshot(source)
    damage(source)
    with pytest.raises(cohorts.CohortError, match=re.escape(message)) as raised:
        run_cohorts(source, (2023,))
    assert "run `pipeline.py cdm` again" in str(raised.value)
    assert snapshot(source) == before
