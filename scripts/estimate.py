"""Estimating the crude and adjusted odds ratios on the cohorts (task 1.6.4, docs/protocol.md
§Model).

The I/O of the models lives here (rule 6). It rebuilds the aggregated table of the analysis,
landmark and multiples cohorts with ``sql/analysis/aggregated_count.sql``, reads it one definition
at a time, and reads the simulated pregnancies of ``results.simulated_combination``. Measures (a)
and (c) are also estimated on each alternative definition of the sensitivity analysis (task 1.8.1,
D-099): the analysis cohort at the cut-offs of 34 and 32 weeks, and the definition with multiples.
It writes the estimates
and the exposure distribution to the tables of ``sql/analysis/estimate_tables.sql``. The models
are :mod:`sinac_truncation.models`, with the measures of :mod:`sinac_truncation.measures` (D-113).

A run checks that the aggregated table holds every birth of each cohort before it fits anything,
and writes everything in one transaction, so a failed run keeps the previous one.
"""

import time
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psycopg
import yaml
from psycopg import sql

import etl
import sql_runner
from sinac_truncation.cohorts import LANDMARK_WEEKS, MULTIPLES_DEFINITION
from sinac_truncation.measures import PRETERM_WEEKS, VisitCuts
from sinac_truncation.models import (
    OBSERVED,
    SENSITIVITY_MEASURES,
    Cell,
    DistributionRow,
    EstimateRow,
    Estimates,
    ModelError,
    definition_measures,
    format_estimates,
    observed_estimates,
    sensitivity_models,
    simulated_estimates,
)
from sinac_truncation.period import format_years
from sinac_truncation.simulation import Combination
from sinac_truncation.sqltext import render_sql

#: Repository root, reached from this file so no absolute path is written down (rule 12).
REPO_ROOT = Path(__file__).resolve().parents[1]

SCHEDULE = REPO_ROOT / "config" / "nom007_schedule.yml"
SQL_DIR = REPO_ROOT / "sql" / "analysis"

#: The analysis cohort, whose measures (a), (a) per count, (b) and (c) are estimated, and the
#: one the null simulation copies (D-097).
ANALYSIS_DEFINITION = 2


class EstimateError(RuntimeError):
    """The models could not run for a reason the user has to act on."""


@dataclass
class Run:
    """What one run writes."""

    period: str
    estimates: list[EstimateRow] = field(default_factory=list)
    distribution: list[DistributionRow] = field(default_factory=list)
    #: Per definition, outcome cut-off and measure, the births an adjusted model set aside
    #: (D-118).
    set_aside: dict[tuple[int, int, str], int] = field(default_factory=dict)

    def add(self, found: Estimates, definition: int, cutoff: int) -> None:
        """Add the rows of one definition at one cut-off, or of one scenario."""
        self.estimates += found.estimates
        self.distribution += found.distribution
        for measure, births in found.set_aside.items():
            self.set_aside[definition, cutoff, measure] = births


def read_cuts(schedule: Path = SCHEDULE) -> VisitCuts:
    """The cut points of measures (a) and (d), from the NOM-007 calendar.

    Raises:
        EstimateError: the file is missing or malformed.
    """
    try:
        document = yaml.safe_load(schedule.read_text(encoding="utf-8"))
        return VisitCuts.from_schedule(document)
    except (OSError, yaml.YAMLError, KeyError, TypeError, ValueError) as error:
        raise EstimateError(f"cannot read the cut points of {schedule.name}: {error}") from error


def read_sql(sql_dir: Path = SQL_DIR) -> dict[str, str]:
    """The SQL files of the models, by name."""
    names = ("estimate_tables.sql", "aggregated_count.sql")
    return {name: (sql_dir / name).read_text(encoding="utf-8") for name in names}


def _table(schemas: etl.Schemas, name: str) -> sql.Identifier:
    return sql.Identifier(schemas.results, name)


def build_aggregated(
    cur: psycopg.Cursor[Any],
    schemas: etl.Schemas,
    sql_texts: Mapping[str, str],
    definitions: Sequence[int],
) -> None:
    """Rebuild the tables of the models and fill the aggregated table of ``definitions``.

    Raises:
        EstimateError: the cohorts were not built, or the births of a definition in the
            aggregated table do not add up to its cohort.
    """
    try:
        cur.execute(render_sql(sql_texts["estimate_tables.sql"], schemas.markers))
        cur.execute(
            render_sql(sql_texts["aggregated_count.sql"], schemas.markers),
            {"definitions": list(definitions)},
        )
        cur.execute(
            sql.SQL(
                "SELECT c.cohort_definition_id, count(*), "
                "(SELECT sum(a.births) FROM {} AS a "
                "WHERE a.cohort_definition_id = c.cohort_definition_id) "
                "FROM {} AS c WHERE c.cohort_definition_id = ANY(%s) GROUP BY 1"
            ).format(_table(schemas, "aggregated_count"), _table(schemas, "cohort")),
            (list(definitions),),
        )
        found = {int(row[0]): (int(row[1]), int(row[2] or 0)) for row in cur.fetchall()}
    except psycopg.errors.UndefinedTable as error:
        raise EstimateError(f"{str(error).strip()}. Run `pipeline.py cohorts` first.") from error
    for definition in definitions:
        cohort, births = found.get(definition, (0, 0))
        if not cohort:
            raise EstimateError(
                f"{schemas.results}.cohort holds no subject of definition {definition}: run "
                "`pipeline.py cohorts` first"
            )
        if births != cohort:
            raise EstimateError(
                f"the aggregated table of definition {definition} holds {births:,} births and "
                f"its cohort {cohort:,}: a subject lacks a value of the table, or has more than "
                "one"
            )


def read_period(cur: psycopg.Cursor[Any], schemas: etl.Schemas) -> str:
    """The years of the record files the cohorts were built on, as ``--years`` writes them."""
    cur.execute(
        sql.SQL(
            "SELECT DISTINCT source_year FROM {} WHERE cohort_definition_id = %s ORDER BY 1"
        ).format(_table(schemas, "attrition")),
        (ANALYSIS_DEFINITION,),
    )
    return format_years([int(year) for (year,) in cur.fetchall()])


def read_cells(cur: psycopg.Cursor[Any], schemas: etl.Schemas, definition: int) -> list[Cell]:
    """The aggregated table of one definition."""
    cur.execute(
        sql.SQL(
            "SELECT weeks, first_visit_trimester, visits, age_group, education_concept_id, "
            "state, year, births FROM {} WHERE cohort_definition_id = %s"
        ).format(_table(schemas, "aggregated_count")),
        (definition,),
    )
    return [
        Cell(int(w), int(t), int(v), str(a), int(e), str(s), int(y), int(b))
        for w, t, v, a, e, s, y, b in cur.fetchall()
    ]


def read_simulated(cur: psycopg.Cursor[Any], schemas: etl.Schemas) -> dict[str, list[Combination]]:
    """The simulated pregnancies of each scenario.

    Raises:
        EstimateError: the null simulation has not run.
    """
    try:
        cur.execute(
            sql.SQL(
                "SELECT scenario, weeks, first_visit_trimester, visits, births FROM {} "
                "ORDER BY 1, 2, 3, 4"
            ).format(_table(schemas, "simulated_combination"))
        )
    except psycopg.errors.UndefinedTable as error:
        raise EstimateError(f"{str(error).strip()}. Run `pipeline.py simulate` first.") from error
    simulated: dict[str, list[Combination]] = defaultdict(list)
    for scenario, weeks, trimester, visits, births in cur.fetchall():
        simulated[str(scenario)].append(
            Combination(int(weeks), int(trimester), int(visits), int(births))
        )
    if not simulated:
        raise EstimateError(
            f"{schemas.results}.simulated_combination is empty: run `pipeline.py simulate` first"
        )
    return dict(simulated)


def write(cur: psycopg.Cursor[Any], schemas: etl.Schemas, run: Run) -> None:
    """Insert the rows of one run into the tables :func:`build_aggregated` rebuilt."""
    cur.executemany(
        sql.SQL("INSERT INTO {} VALUES ({})").format(
            _table(schemas, "estimate"),
            sql.SQL(", ").join(sql.Placeholder() * len(EstimateRow._fields)),
        ),
        run.estimates,
    )
    cur.executemany(
        sql.SQL("INSERT INTO {} VALUES ({})").format(
            _table(schemas, "exposure_distribution"),
            sql.SQL(", ").join(sql.Placeholder() * len(DistributionRow._fields)),
        ),
        run.distribution,
    )


def run(
    conn: sql_runner.Connection,
    *,
    schemas: etl.Schemas,
    schedule: Path = SCHEDULE,
    sql_dir: Path = SQL_DIR,
) -> Run:
    """Estimate the odds ratios on the cohorts in the database. See ``pipeline.py estimate
    --help``.

    Raises:
        EstimateError: anything the user has to act on. The tables keep the previous run
            whenever it is raised.
    """
    start = time.perf_counter()
    cuts = read_cuts(schedule)
    sql_texts = read_sql(sql_dir)
    # Per definition, its models as (measures, cut-off): the main analysis, then each alternative
    # definition of the sensitivity analysis.
    models: dict[int, list[tuple[tuple[str, ...], int]]] = defaultdict(list)
    for definition, names in definition_measures(ANALYSIS_DEFINITION, LANDMARK_WEEKS).items():
        models[definition].append((names, PRETERM_WEEKS))
    for definition, cutoff in sensitivity_models(ANALYSIS_DEFINITION, MULTIPLES_DEFINITION):
        models[definition].append((SENSITIVITY_MEASURES, cutoff))
    with conn.transaction(), conn.cursor() as cur:
        build_aggregated(cur, schemas, sql_texts, list(models))
        aggregated = time.perf_counter() - start
        result = Run(period=read_period(cur, schemas))
        simulated = read_simulated(cur, schemas)
        for definition, fits in models.items():
            cells = read_cells(cur, schemas, definition)
            for names, cutoff in fits:
                try:
                    found = observed_estimates(
                        definition, names, cells, cuts, period=result.period, preterm_weeks=cutoff
                    )
                except ModelError as error:
                    raise EstimateError(
                        f"definition {definition}, cut-off {cutoff} weeks: {error}"
                    ) from error
                result.add(found, definition, cutoff)
        for scenario, pregnancies in simulated.items():
            found = simulated_estimates(
                scenario,
                pregnancies,
                cuts,
                analysis_definition=ANALYSIS_DEFINITION,
                landmarks=LANDMARK_WEEKS,
                period=result.period,
            )
            result.add(found, ANALYSIS_DEFINITION, PRETERM_WEEKS)
        write(cur, schemas, result)

    print(f"odds ratios of preterm birth, {result.period}, every term categorical (D-093)")
    for (definition, cutoff, measure), births in result.set_aside.items():
        print(
            f"definition {definition}, cut-off {cutoff} weeks, measure {measure}: the adjusted "
            f"model set aside {births:,} births of levels whose births are all preterm or all "
            "term (D-118)"
        )
    print()
    for line in format_estimates([row for row in result.estimates if row.source == OBSERVED]):
        print(line)
    print(
        f"\nwritten in {time.perf_counter() - start:.1f} s, {aggregated:.1f} s of them building "
        f"{schemas.results}.aggregated_count, to {schemas.results}.estimate and "
        f"{schemas.results}.exposure_distribution"
    )
    return result
