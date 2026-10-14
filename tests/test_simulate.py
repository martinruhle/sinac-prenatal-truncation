"""Tests for ``pipeline.py simulate`` (task 1.7.1): the null simulation on the cohorts in the
database.

The records are the eight traps of ``tests/synthetic.py`` and the eight below, which all pass the
analysis cohort, with records 1 and 2 (39 weeks, eight visits from the first trimester). The
expected rows are written by hand from the records, never measured on the database.

Tests marked ``db`` load the synthetic source through the ETL into schemas of this module's own,
dropped after it, build the cohorts there and run the simulation on them.
"""

from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import pytest

import cohorts
import etl
import simulate as script
import sql_runner
from sinac_truncation.cohorts import LANDMARK_WEEKS
from sinac_truncation.measures import (
    FIRST_TRIMESTER,
    LATER_OR_NO_CARE,
    Crude,
    Share,
    ShareRow,
    level_counts,
    reached,
)
from sinac_truncation.simulation import Combination
from synthetic import RECORDS_2023, Source, fetch, module_schemas, prepare_source

#: Records 9 to 16 of the 2023 file, in the order of SOURCE_COLUMNS: FECHANACIMIENTO,
#: FECHANACIMIENTOMADRE, EDAD, RESIDEEXTRANJERO, ENTIDADRESIDENCIA, EDADGESTACIONAL,
#: PRODUCTOEMBARAZO, TOTALCONSULTAS, TRIMESTREPRIMERCONSULTA, ESCOLARIDAD, SEXO, PESO. Each is the
#: normal case of record 1 but for its weeks, its visits and its first-visit trimester.
SIMULATION_RECORDS_2023: tuple[tuple[str | None, ...], ...] = (
    # 9. 40 weeks, 6 visits from the first trimester.
    ("09/01/2023", "01/01/1990", "33", "2", "09", "40", "1", "6", "1", "51", "1", "3200"),
    # 10. 41 weeks, 12 visits from the first trimester.
    ("10/01/2023", "01/01/1990", "33", "2", "09", "41", "1", "12", "1", "51", "1", "3200"),
    # 11. 36 weeks, 5 visits from the second trimester.
    ("11/01/2023", "01/01/1990", "33", "2", "09", "36", "1", "5", "2", "51", "1", "3200"),
    # 12. 30 weeks, 2 visits from the third trimester.
    ("12/01/2023", "01/01/1990", "33", "2", "09", "30", "1", "2", "3", "51", "1", "3200"),
    # 13. 28 weeks, no care.
    ("13/01/2023", "01/01/1990", "33", "2", "09", "28", "1", "0", "0", "51", "1", "3200"),
    # 14. 33 weeks, 6 visits from the first trimester.
    ("14/01/2023", "01/01/1990", "33", "2", "09", "33", "1", "6", "1", "51", "1", "3200"),
    # 15. 35 weeks, 4 visits from the second trimester.
    ("15/01/2023", "01/01/1990", "33", "2", "09", "35", "1", "4", "2", "51", "1", "3200"),
    # 16. 38 weeks, 9 visits from the first trimester.
    ("16/01/2023", "01/01/1990", "33", "2", "09", "38", "1", "9", "1", "51", "1", "3200"),
)

#: The analysis cohort per combination: records 1 and 2, and 9 to 16.
ANALYSIS = [
    Combination(28, 0, 0, 1),
    Combination(30, 3, 2, 1),
    Combination(33, 1, 6, 1),
    Combination(35, 2, 4, 1),
    Combination(36, 2, 5, 1),
    Combination(38, 1, 9, 1),
    Combination(39, 1, 8, 2),
    Combination(40, 1, 6, 1),
    Combination(41, 1, 12, 1),
]


@pytest.fixture(scope="module")
def schemas(
    db_connection: sql_runner.Connection, ddl_files: Sequence[Path]
) -> Iterator[etl.Schemas]:
    with module_schemas(db_connection, ddl_files, "test_simulate") as names:
        yield names


@pytest.fixture
def source(db_connection: sql_runner.Connection, schemas: etl.Schemas, tmp_path: Path) -> Source:
    """The synthetic source with the records above staged as rows 9 to 16 of the 2023 file."""
    prepared = prepare_source(db_connection, schemas, tmp_path)
    prepared.stage(2023, (*RECORDS_2023, *SIMULATION_RECORDS_2023))
    results = schemas.results
    with db_connection.cursor() as cursor:
        cursor.execute(
            f"DROP TABLE IF EXISTS {results}.cohort, {results}.attrition, {results}.exposure, "
            f"{results}.simulation, {results}.simulated_combination, {results}.truncation_share"
        )
    return prepared


def built(source: Source) -> Source:
    source.run((2023,))
    cohorts.run(source.connection, (2023,), schemas=source.schemas)
    return source


def combinations(source: Source) -> dict[int, list[Combination]]:
    return script.read_combinations(source.connection, source.schemas, script.read_sql())


def tables(source: Source) -> dict[str, list[tuple[Any, ...]]]:
    results = source.schemas.results
    return {
        "simulation": fetch(source.connection, f"SELECT * FROM {results}.simulation ORDER BY 1"),
        "simulated_combination": fetch(
            source.connection,
            f"SELECT * FROM {results}.simulated_combination ORDER BY 1, 2, 3, 4",
        ),
        "truncation_share": fetch(
            source.connection,
            f"SELECT * FROM {results}.truncation_share ORDER BY 1, 2, 3, 4, 5",
        ),
    }


# --- The built-in check: no database --------------------------------------------------------------


def test_a_simulated_association_of_measure_c_stops_the_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A trimester drawn independently of the weeks cannot start care later in the preterm
    births but by chance, so a simulation that does has a fault."""
    # 10 % preterm among first-trimester starts and 50 % among the rest: an odds ratio of 9.
    tied = [
        Combination(39, 1, 8, 450),
        Combination(30, 1, 5, 50),
        Combination(39, 2, 6, 250),
        Combination(30, 2, 3, 250),
    ]
    monkeypatch.setattr(script, "simulate", lambda *args, **kwargs: tied)
    observed = {definition: ANALYSIS for definition in (2, 3, 4, 5)}
    with pytest.raises(script.SimulateError, match="built-in check failed"):
        script.compute(script.read_settings(), observed)


def test_the_report_states_the_check_with_or_without_an_odds_ratio() -> None:
    """A small table can leave a cell of (c) empty, as the synthetic records of this module do."""
    empty = Crude(None, None, None, 0.1)
    row = ShareRow(2, "c", "", "e1", FIRST_TRIMESTER, Share(LATER_OR_NO_CARE, empty, empty, None))
    assert script.check_line(row).endswith("does not exist: a cell is empty")
    estimate = Crude(1.0042, 0.9968, 1.0115, 0.0003)
    row = row._replace(share=row.share._replace(simulated=estimate))
    assert script.check_line(row).endswith("is 1.0042 (0.9968 to 1.0115)")


# --- The simulation on the compose database ------------------------------------------------------


@pytest.mark.db
def test_the_births_of_each_definition_are_read_per_combination(source: Source) -> None:
    found = combinations(built(source))
    assert found[2] == ANALYSIS
    # The landmark cohorts are the analysis cohort with the weeks of step 10 or more, which is
    # the filter the simulated pregnancies go through.
    for definition, week in LANDMARK_WEEKS.items():
        assert found[definition] == reached(ANALYSIS, week)


@pytest.mark.db
def test_measure_a_has_the_levels_results_exposure_holds(source: Source) -> None:
    built(source)
    results = source.schemas.results
    in_sql = fetch(
        source.connection,
        f"SELECT x.visits_level, count(*) FROM {results}.exposure AS x "
        f"INNER JOIN {results}.cohort AS c ON x.subject_id = c.subject_id "
        "WHERE c.cohort_definition_id = 2 GROUP BY 1 ORDER BY 1",
    )
    in_python = level_counts(combinations(source)[2], "a", script.read_settings().cuts)
    assert in_sql == [("0", 1), ("1-4", 2), ("5-7", 3), ("8+", 4)]
    assert in_sql == sorted((level, count.births) for level, count in in_python.items())


@pytest.mark.db
def test_two_runs_with_the_same_seed_write_the_same_tables(source: Source) -> None:
    built(source)
    script.run(source.connection, schemas=source.schemas)
    first = tables(source)
    script.run(source.connection, schemas=source.schemas)
    assert tables(source) == first

    # p: 4 of the 5 first-trimester starts delivered at 38 weeks or more had 8 visits or more.
    assert first["simulation"] == [
        ("e1", "Perfect calendar", 43, 1, False, 10, None, None, None, None),
        ("e2", "Calendar with misses", 43, 2, True, 10, pytest.approx(0.8 ** (1 / 7)), 38, 5, 0.8),
    ]
    for scenario in ("e1", "e2"):
        assert sum(row[4] for row in first["simulated_combination"] if row[0] == scenario) == 10
    measures = {(row[0], row[1]) for row in first["truncation_share"]}
    assert measures == {(2, "a"), (2, "a_count"), (2, "b"), (2, "c"), (3, "d"), (4, "d"), (5, "d")}


@pytest.mark.db
def test_the_simulation_needs_the_cohorts(source: Source) -> None:
    source.run((2023,))
    with pytest.raises(script.SimulateError, match="pipeline.py cohorts"):
        script.run(source.connection, schemas=source.schemas)
