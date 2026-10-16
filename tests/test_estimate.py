"""Tests for ``pipeline.py estimate`` (task 1.6.4): the aggregated table and the odds ratios on
the cohorts in the database.

The records are synthetic, one per birth, and go through the ETL and the cohorts. The aggregated
table they produce is checked against counts written by hand from the records, never measured
on the database.

Tests marked ``db`` load the synthetic source into schemas of this module's own, dropped after
it, build the cohorts there and run the simulation and the models on them.
"""

from collections.abc import Iterator, Sequence
from math import exp, log, sqrt
from pathlib import Path
from typing import Any

import pytest

import cohorts
import estimate as script
import etl
import simulate
import sql_runner
from sinac_truncation.cohorts import LANDMARK_WEEKS
from sinac_truncation.measures import LATER_OR_NO_CARE
from sinac_truncation.models import ADJUSTED, CRUDE, OBSERVED, summed
from synthetic import (
    JUNIOR_HIGH,
    RECORDS_2023,
    SENIOR_HIGH,
    Source,
    fetch,
    module_schemas,
    prepare_source,
)


def record(
    age: int, *, weeks: int = 39, visits: int = 8, trimester: int = 1, state: str = "09"
) -> tuple[str | None, ...]:
    """Record 1 of ``tests/synthetic.py``, the normal case, with another declared age, weeks,
    visits, first-visit trimester or state. The fields are in the order of SOURCE_COLUMNS."""
    return (
        "15/03/2023", "02/05/1995", str(age), "2", state, str(weeks), "1", str(visits),
        str(trimester), "51", "1", "3200",
    )  # fmt: skip


#: One record at each bound of the age groups of docs/protocol.md §Covariates, and one with
#: other values everywhere: upper secondary education (132), state 14, 35 weeks, 6 visits from
#: the second trimester.
AGE_RECORDS = (
    *(record(age) for age in (14, 15, 19, 20, 24, 25, 29, 30, 34, 35, 39, 40)),
    ("15/03/2023", "02/05/1995", "31", "2", "14", "35", "1", "6", "2", "132", "1", "3200"),
)

#: The aggregated table of the analysis cohort, by hand: records 1 and 2 of RECORDS_2023 (age
#: 27) and AGE_RECORDS. Records 3 to 8 leave the cohort.
AGGREGATED = [
    (35, 2, 6, "30-34", SENIOR_HIGH, "14", 2023, 1),
    (39, 1, 8, "15-19", JUNIOR_HIGH, "09", 2023, 2),
    (39, 1, 8, "20-24", JUNIOR_HIGH, "09", 2023, 2),
    (39, 1, 8, "25-29", JUNIOR_HIGH, "09", 2023, 4),
    (39, 1, 8, "30-34", JUNIOR_HIGH, "09", 2023, 2),
    (39, 1, 8, "35-39", JUNIOR_HIGH, "09", 2023, 2),
    (39, 1, 8, "40 and over", JUNIOR_HIGH, "09", 2023, 1),
    (39, 1, 8, "under 15", JUNIOR_HIGH, "09", 2023, 1),
]


def confounded(age: int, trimester: int, preterm: int, term: int) -> list[tuple[str | None, ...]]:
    return [record(age, weeks=35, trimester=trimester)] * preterm + [
        record(age, trimester=trimester)
    ] * term


#: 18 births in which age confounds measure (c). Within each age group the odds ratio of a
#: later start against the first trimester is exactly 2:
#:   25-29, trimester 1: 2 preterm, 4 term     25-29, trimester 2: 2 preterm, 2 term
#:   30-34, trimester 1: 1 preterm, 1 term     30-34, trimester 2: 4 preterm, 2 term
#: Pooled, it is (6 / 4) / (3 / 5) = 2.5.
CONFOUNDED = (
    *confounded(27, 1, 2, 4),
    *confounded(27, 2, 2, 2),
    *confounded(33, 1, 1, 1),
    *confounded(33, 2, 4, 2),
)


@pytest.fixture(scope="module")
def schemas(
    db_connection: sql_runner.Connection, ddl_files: Sequence[Path]
) -> Iterator[etl.Schemas]:
    with module_schemas(db_connection, ddl_files, "test_estimate") as names:
        yield names


def staged(
    connection: sql_runner.Connection,
    schemas: etl.Schemas,
    tmp_path: Path,
    records: Sequence[Sequence[str | None]],
) -> Source:
    """The synthetic source with ``records`` as the 2023 file, and no table of results."""
    prepared = prepare_source(connection, schemas, tmp_path)
    prepared.stage(2023, records)
    results = schemas.results
    with connection.cursor() as cursor:
        cursor.execute(
            f"DROP TABLE IF EXISTS {results}.cohort, {results}.attrition, {results}.exposure, "
            f"{results}.simulation, {results}.simulated_combination, {results}.truncation_share, "
            f"{results}.aggregated_count, {results}.estimate, {results}.exposure_distribution"
        )
    return prepared


def built(source: Source) -> Source:
    source.run((2023,))
    cohorts.run(source.connection, (2023,), schemas=source.schemas)
    return source


def tables(source: Source) -> dict[str, list[tuple[Any, ...]]]:
    results = source.schemas.results
    return {
        name: fetch(source.connection, f"SELECT * FROM {results}.{name} ORDER BY {order}")
        for name, order in (
            ("aggregated_count", "1, 2, 3, 4, 5, 6, 7, 8"),
            ("estimate", "1, 2, 3, 4, 5, 6, 7, 8, 9"),
            ("exposure_distribution", "1, 2, 3, 4, 5, 6, 7, 8"),
        )
    }


# --- The aggregated table -------------------------------------------------------------------------


@pytest.mark.db
def test_the_aggregated_table_holds_each_birth_of_the_cohorts_with_its_covariates(
    db_connection: sql_runner.Connection, schemas: etl.Schemas, tmp_path: Path
) -> None:
    source = built(staged(db_connection, schemas, tmp_path, (*RECORDS_2023, *AGE_RECORDS)))
    definitions = [2, *LANDMARK_WEEKS]
    with source.connection.transaction(), source.connection.cursor() as cur:
        script.build_aggregated(cur, source.schemas, script.read_sql(), definitions)
        cells = {
            definition: script.read_cells(cur, schemas, definition) for definition in definitions
        }

    # Every record of the analysis cohort reached week 35, so each landmark cohort holds them all.
    for definition in definitions:
        assert sorted((*cell,) for cell in cells[definition]) == AGGREGATED
    # Summed over the covariates, the table is the one the null simulation reads (D-113).
    found = simulate.read_combinations(source.connection, source.schemas, simulate.read_sql())
    for definition in definitions:
        assert summed(cells[definition]) == found[definition]


@pytest.mark.db
def test_the_models_need_the_cohorts(
    db_connection: sql_runner.Connection, schemas: etl.Schemas, tmp_path: Path
) -> None:
    source = staged(db_connection, schemas, tmp_path, CONFOUNDED)
    source.run((2023,))
    with pytest.raises(script.EstimateError, match="pipeline.py cohorts"):
        script.run(source.connection, schemas=source.schemas)


@pytest.mark.db
def test_the_models_need_the_simulation(
    db_connection: sql_runner.Connection, schemas: etl.Schemas, tmp_path: Path
) -> None:
    source = built(staged(db_connection, schemas, tmp_path, CONFOUNDED))
    with pytest.raises(script.EstimateError, match="pipeline.py simulate"):
        script.run(source.connection, schemas=source.schemas)


# --- The estimates -------------------------------------------------------------------------------


@pytest.mark.db
def test_a_run_estimates_the_crude_and_adjusted_odds_ratios_of_the_records(
    db_connection: sql_runner.Connection, schemas: etl.Schemas, tmp_path: Path
) -> None:
    source = built(staged(db_connection, schemas, tmp_path, CONFOUNDED))
    simulate.run(source.connection, schemas=source.schemas)
    run = script.run(source.connection, schemas=source.schemas)
    first = tables(source)
    script.run(source.connection, schemas=source.schemas)
    assert tables(source) == first

    assert run.period == "2023"
    observed = {
        (row.measure, row.level, row.model): row for row in run.estimates if row.source == OBSERVED
    }
    # Measure (c): 6 preterm of 10 later starts against 3 of 8 first-trimester starts.
    crude = observed["c", LATER_OR_NO_CARE, CRUDE]
    margin = 1.959964 * sqrt(1 / 6 + 1 / 4 + 1 / 3 + 1 / 5)
    assert (crude.births, crude.preterm) == (10, 6)
    assert (crude.odds_ratio, crude.lower, crude.upper) == pytest.approx(
        (2.5, exp(log(2.5) - margin), exp(log(2.5) + margin)), rel=1e-6
    )
    assert observed["c", LATER_OR_NO_CARE, ADJUSTED].odds_ratio == pytest.approx(2.0, rel=1e-8)

    # Every record has 8 visits, so (a), (a) per count and (d) have the reference alone. In (b)
    # the reference, Adequate, holds the 3 preterm first-trimester starts at 35 weeks and no term
    # birth, so no level has an estimate, and the adjusted model sets aside Adequate and
    # Intermediate, the 5 term first-trimester starts.
    assert sorted(observed) == [
        ("b", "Inadequate", ADJUSTED),
        ("b", "Inadequate", CRUDE),
        ("b", "Intermediate", ADJUSTED),
        ("b", "Intermediate", CRUDE),
        ("c", LATER_OR_NO_CARE, ADJUSTED),
        ("c", LATER_OR_NO_CARE, CRUDE),
    ]
    assert all(observed[key].odds_ratio is None for key in observed if key[0] == "b")
    assert run.set_aside == {(2, "b"): 8}

    # The distribution splits the 18 births of each measure and definition by outcome.
    observed_distribution = [row for row in run.distribution if row.source == OBSERVED]
    assert {(row.definition, row.measure) for row in observed_distribution} == {
        (2, "a"),
        (2, "a_count"),
        (2, "b"),
        (2, "c"),
        (3, "d"),
        (4, "d"),
        (5, "d"),
    }
    for definition, measure in {(row.definition, row.measure) for row in observed_distribution}:
        rows = [
            row
            for row in observed_distribution
            if (row.definition, row.measure) == (definition, measure)
        ]
        assert sum(row.births for row in rows) == 18
        assert sum(row.births for row in rows if row.outcome == "preterm") == 9

    # Each scenario adds its crude rows, and no adjusted one.
    simulated = {row.source for row in run.estimates if row.source != OBSERVED}
    assert simulated == {"sim_e1", "sim_e2"}
    assert {row.model for row in run.estimates if row.source in simulated} == {CRUDE}
    assert len(first["estimate"]) == len(run.estimates)
    assert len(first["exposure_distribution"]) == len(run.distribution)
