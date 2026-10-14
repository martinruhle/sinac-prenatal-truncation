"""Running the null simulation on the analysis cohort (task 1.7.1, docs/protocol.md §Null
simulation).

The I/O of the simulation lives here (rule 6). It reads ``config/null_simulation.yml`` and
``config/nom007_schedule.yml``, and the births of the analysis and landmark cohorts per
combination of weeks, trimester and visits with ``sql/analysis/combinations.sql``. It writes the
run to the tables of ``sql/analysis/simulation_tables.sql``. The simulation is
:mod:`sinac_truncation.simulation`. The measures and their crude comparison are
:mod:`sinac_truncation.measures`, the same code for the observed records and the simulated
pregnancies (D-097, D-113).

A run checks the cohorts before anything else. It writes everything in one transaction, and only
once the built-in check of measure (c) holds, so a failed run keeps the previous one.
"""

import time
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
import yaml
from psycopg import sql

import etl
import sql_runner
from sinac_truncation.cohorts import LANDMARK_WEEKS
from sinac_truncation.measures import (
    FIRST_TRIMESTER,
    ShareRow,
    VisitCuts,
    compare,
    excludes_one,
    format_shares,
)
from sinac_truncation.simulation import (
    Calibration,
    Combination,
    Scenario,
    SimulationError,
    calendar_first_weeks,
    calibrate,
    first_visits,
    simulate,
)
from sinac_truncation.sqltext import render_sql

#: Repository root, reached from this file so no absolute path is written down (rule 12).
REPO_ROOT = Path(__file__).resolve().parents[1]

CONFIG = REPO_ROOT / "config" / "null_simulation.yml"
SCHEDULE = REPO_ROOT / "config" / "nom007_schedule.yml"
SQL_DIR = REPO_ROOT / "sql" / "analysis"

#: The analysis cohort, whose records the simulation copies (D-097).
ANALYSIS_DEFINITION = 2


class SimulateError(RuntimeError):
    """The simulation could not run for a reason the user has to act on."""


@dataclass(frozen=True)
class Settings:
    """What a run reads from the configuration, checked before any query."""

    seed: int
    scenarios: tuple[Scenario, ...]
    first_weeks: tuple[int, ...]
    first_visit: Mapping[int, int]
    cuts: VisitCuts


def _yaml(path: Path) -> dict[str, Any]:
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise SimulateError(f"cannot read {path.name}: {error}") from error
    if not isinstance(document, dict):
        raise SimulateError(f"{path.name} is not a mapping")
    return document


def read_settings(config: Path = CONFIG, schedule: Path = SCHEDULE) -> Settings:
    """The seed, the scenarios and the calendar of a run.

    Raises:
        SimulateError: a file is missing or malformed, a seed is not a non-negative integer, or
            two scenarios share an id or a stream.
    """
    settings = _yaml(config)
    calendar = _yaml(schedule)
    try:
        seed = settings["seed"]
        scenarios = tuple(
            Scenario(
                id=str(entry["id"]),
                name=str(entry["name"]),
                stream=int(entry["stream"]),
                misses=entry["misses"],
            )
            for entry in settings["scenarios"]
        )
        trimesters = {
            int(key): int(value) for key, value in settings["trimester_first_weeks"].items()
        }
        first_weeks = calendar_first_weeks(calendar)
        first_visit = first_visits(first_weeks, trimesters)
        cuts = VisitCuts.from_schedule(calendar)
    except (KeyError, TypeError, ValueError) as error:
        raise SimulateError(f"{config.name} or {schedule.name} is malformed: {error}") from error
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise SimulateError(f"the seed {seed!r} of {config.name} is not a non-negative integer")
    if not scenarios:
        raise SimulateError(f"{config.name} declares no scenario")
    for field in ("id", "stream"):
        values = [getattr(scenario, field) for scenario in scenarios]
        if len(set(values)) != len(values):
            raise SimulateError(f"two scenarios of {config.name} share a {field}: {values}")
    if any(not isinstance(scenario.misses, bool) for scenario in scenarios):
        raise SimulateError(f"`misses` of every scenario of {config.name} is true or false")
    return Settings(seed, scenarios, first_weeks, first_visit, cuts)


def read_sql(sql_dir: Path = SQL_DIR) -> dict[str, str]:
    """The SQL files of the simulation, by name."""
    names = ("simulation_tables.sql", "combinations.sql")
    return {name: (sql_dir / name).read_text(encoding="utf-8") for name in names}


def read_combinations(
    conn: sql_runner.Connection, schemas: etl.Schemas, sql_texts: Mapping[str, str]
) -> dict[int, list[Combination]]:
    """The births of the analysis and landmark cohorts per combination of weeks, trimester and
    visits.

    Raises:
        SimulateError: the cohorts were not built, or the births of a definition do not add up
            to its cohort.
    """
    definitions = [ANALYSIS_DEFINITION, *LANDMARK_WEEKS]
    query = render_sql(sql_texts["combinations.sql"], schemas.markers)
    found: dict[int, list[Combination]] = defaultdict(list)
    try:
        with conn.transaction(), conn.cursor() as cur:
            cur.execute(query, {"definitions": definitions})
            for definition, weeks, trimester, visits, births in cur.fetchall():
                found[int(definition)].append(
                    Combination(int(weeks), int(trimester), int(visits), int(births))
                )
            cur.execute(
                sql.SQL(
                    "SELECT cohort_definition_id, count(*) FROM {} "
                    "WHERE cohort_definition_id = ANY(%s) GROUP BY 1"
                ).format(sql.Identifier(schemas.results, "cohort")),
                (definitions,),
            )
            cohort = {int(definition): int(count) for definition, count in cur.fetchall()}
    except psycopg.errors.UndefinedTable as error:
        raise SimulateError(f"{str(error).strip()}. Run `pipeline.py cohorts` first.") from error
    for definition in definitions:
        if not cohort.get(definition):
            raise SimulateError(
                f"{schemas.results}.cohort holds no subject of definition {definition}: run "
                "`pipeline.py cohorts` first"
            )
        births = sum(combination.births for combination in found[definition])
        if births != cohort[definition]:
            raise SimulateError(
                f"the combinations of definition {definition} hold {births:,} births and its "
                f"cohort {cohort[definition]:,}: a subject lacks its weeks or its visits, or has "
                "more than one gestational age"
            )
    return dict(found)


@dataclass(frozen=True)
class Run:
    """What one run computes, before it is written."""

    calibration: Calibration
    simulated: Mapping[str, list[Combination]]
    rows: list[ShareRow]


def compute(settings: Settings, observed: Mapping[int, Sequence[Combination]]) -> Run:
    """Calibrate p, simulate each scenario and compare it with the observed definitions.

    Raises:
        SimulateError: the built-in check fails: the simulated odds ratio of (c) excludes 1,
            which a trimester drawn independently of the weeks cannot produce but by chance.
    """
    analysis = observed[ANALYSIS_DEFINITION]
    calibration = calibrate(analysis, settings.first_weeks, settings.first_visit)
    simulated = {
        scenario.id: simulate(
            analysis,
            scenario,
            first_weeks=settings.first_weeks,
            first_visit=settings.first_visit,
            visit_probability=calibration.visit_probability,
            seed=settings.seed,
        )
        for scenario in settings.scenarios
    }
    rows = compare(
        observed,
        simulated,
        settings.cuts,
        analysis_definition=ANALYSIS_DEFINITION,
        landmarks=LANDMARK_WEEKS,
    )
    for row in rows:
        if row.measure == "c" and excludes_one(row.share.simulated):
            estimate = row.share.simulated
            raise SimulateError(
                f"the built-in check failed in scenario {row.scenario}: the simulated odds ratio "
                f"of (c) is {estimate.odds_ratio:.4f} ({estimate.lower:.4f} to "
                f"{estimate.upper:.4f}), and the first trimester is drawn independently of the "
                "weeks. Nothing was written."
            )
    return Run(calibration, simulated, rows)


def write(
    conn: sql_runner.Connection,
    schemas: etl.Schemas,
    settings: Settings,
    run: Run,
    sql_texts: Mapping[str, str],
) -> None:
    """Replace the rows of the three tables of the simulation, in one transaction."""

    def table(name: str) -> sql.Identifier:
        return sql.Identifier(schemas.results, name)

    with conn.transaction(), conn.cursor() as cur:
        cur.execute(render_sql(sql_texts["simulation_tables.sql"], schemas.markers))
        for name in ("simulation", "simulated_combination", "truncation_share"):
            cur.execute(sql.SQL("DELETE FROM {}").format(table(name)))
        calibration = run.calibration
        cur.executemany(
            sql.SQL("INSERT INTO {} VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)").format(
                table("simulation")
            ),
            [
                (
                    scenario.id,
                    scenario.name,
                    settings.seed,
                    scenario.stream,
                    scenario.misses,
                    sum(c.births for c in run.simulated[scenario.id]),
                    *(
                        (
                            calibration.visit_probability,
                            calibration.from_week,
                            calibration.births,
                            calibration.full_calendar_share,
                        )
                        if scenario.misses
                        else (None, None, None, None)
                    ),
                )
                for scenario in settings.scenarios
            ],
        )
        cur.executemany(
            sql.SQL("INSERT INTO {} VALUES (%s, %s, %s, %s, %s)").format(
                table("simulated_combination")
            ),
            [
                (scenario, c.weeks, c.trimester, c.visits, c.births)
                for scenario, combinations in run.simulated.items()
                for c in combinations
            ],
        )
        cur.executemany(
            sql.SQL(
                "INSERT INTO {} VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            ).format(table("truncation_share")),
            [
                (
                    row.definition,
                    row.measure,
                    row.variant,
                    row.share.level,
                    row.scenario,
                    row.reference,
                    row.share.observed.odds_ratio,
                    row.share.observed.lower,
                    row.share.observed.upper,
                    row.share.simulated.odds_ratio,
                    row.share.observed.risk_difference,
                    row.share.simulated.risk_difference,
                    row.share.share,
                )
                for row in run.rows
            ],
        )


def check_line(row: ShareRow) -> str:
    """The line of the report that states the built-in check of one scenario."""
    estimate = row.share.simulated
    what = (
        f"built-in check, scenario {row.scenario}: the odds ratio of (c), {row.share.level} "
        f"against {FIRST_TRIMESTER},"
    )
    if estimate.odds_ratio is None or estimate.lower is None or estimate.upper is None:
        # A small table can leave a cell empty; there is then no interval that could exclude 1.
        return f"{what} does not exist: a cell is empty"
    return f"{what} is {estimate.odds_ratio:.4f} ({estimate.lower:.4f} to {estimate.upper:.4f})"


def run(
    conn: sql_runner.Connection,
    *,
    schemas: etl.Schemas,
    config: Path = CONFIG,
    schedule: Path = SCHEDULE,
    sql_dir: Path = SQL_DIR,
) -> Run:
    """Run the null simulation on the cohorts in the database. See ``pipeline.py simulate --help``.

    Raises:
        SimulateError: anything the user has to act on. The tables keep the previous run
            whenever it is raised.
    """
    start = time.perf_counter()
    settings = read_settings(config, schedule)
    sql_texts = read_sql(sql_dir)
    observed = read_combinations(conn, schemas, sql_texts)
    try:
        result = compute(settings, observed)
    except SimulationError as error:
        raise SimulateError(str(error)) from error
    write(conn, schemas, settings, result, sql_texts)

    calibration = result.calibration
    pregnancies = sum(c.births for c in observed[ANALYSIS_DEFINITION])
    print(f"null simulation, seed {settings.seed}: {pregnancies:,} pregnancies per scenario")
    print(
        f"p = {calibration.visit_probability:.4f}: {calibration.full_calendar_share:.2%} of the "
        f"{calibration.births:,} births that started in the first trimester and were delivered "
        f"at {calibration.from_week} weeks or more had {settings.cuts.calendar} visits or more"
    )
    for row in result.rows:
        if row.measure == "c":
            print(check_line(row))
    print()
    for line in format_shares(result.rows):
        print(line)
    print(
        f"\nwritten in {time.perf_counter() - start:.1f} s to {schemas.results}.simulation, "
        f"{schemas.results}.simulated_combination and {schemas.results}.truncation_share"
    )
    return result
