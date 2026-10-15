"""The null simulation: prenatal visits on the NOM-007-SSA2-2016 calendar in a world where care
has no effect on preterm birth (docs/protocol.md §Null simulation, D-096, D-097).

Each simulated pregnancy takes the completed weeks at delivery of one record of the analysis
cohort, and a trimester of the first visit drawn independently of them. Its visits follow the
calendar from the first visit of that trimester until delivery stops it, so the only link between
visits and preterm birth is truncation.

There is no I/O here (CLAUDE.md rule 6): the calendar, the seed and the scenarios reach these
functions as values, which ``scripts/simulate.py`` reads from ``config/``. The visits are those of
the model, not of SINAC, which records no visit date (rule 4).
"""

from bisect import bisect_right
from collections.abc import Iterable, Mapping, Sequence
from math import comb
from typing import Any, NamedTuple

import numpy as np

__all__ = [
    "Calibration",
    "Combination",
    "Scenario",
    "SimulationError",
    "calendar_first_weeks",
    "calibrate",
    "expected",
    "first_visits",
    "simulate",
]

#: The trimester codes of ``TRIMESTREPRIMERCONSULTA`` the common set keeps: 0 "NO RECIBIÓ", 1, 2, 3.
_TRIMESTERS = (0, 1, 2, 3)


class SimulationError(ValueError):
    """A calendar, a parameter or a table the simulation cannot run on."""


class Combination(NamedTuple):
    """The births of one combination of completed weeks, first-visit trimester and visits.

    The observed analysis and the simulation both reduce to this table: one row per combination
    of a definition, or of a scenario (D-113).
    """

    #: Completed weeks of gestation at delivery (``EDADGESTACIONAL``).
    weeks: int
    #: Trimester of the first visit (``TRIMESTREPRIMERCONSULTA``): 0 "NO RECIBIÓ", 1, 2 or 3.
    trimester: int
    #: Total prenatal visits (``TOTALCONSULTAS``).
    visits: int
    #: A whole count for records and simulated pregnancies; a mean, with fractions, for the exact
    #: expectation of :func:`expected`.
    births: float


class Scenario(NamedTuple):
    """A scenario of ``config/null_simulation.yml``."""

    id: str
    name: str
    #: The child of the seed this scenario draws from (a SeedSequence spawn key).
    stream: int
    #: False: every visit after the first one happens (E1). True: each one with probability p (E2).
    misses: bool


class Calibration(NamedTuple):
    """How p of the scenario with misses is set from the observed records (D-096).

    The births are those of the records that started care in the first trimester and were
    delivered at the first week of the last visit or later, the only ones the calendar lets reach
    every visit. p makes the expected share of their simulated pregnancies with every visit equal
    to the observed share with as many visits or more.
    """

    #: The first week of the last visit of the calendar: 38 for NOM-007-SSA2-2016.
    from_week: int
    births: int
    #: The observed share of those births with as many visits as the calendar or more.
    full_calendar_share: float
    #: p: the probability of each visit after the first one.
    visit_probability: float


def calendar_first_weeks(schedule: Mapping[str, Any]) -> tuple[int, ...]:
    """The first week of each visit of ``config/nom007_schedule.yml``, in the order of the norm.

    A visit happens when the completed weeks at delivery reach its first week (D-096, FOR
    APPROVAL), so the first week is the only number of a visit the simulation reads.

    Raises:
        SimulationError: the visits are not numbered 1 to n, or their first weeks do not rise.
    """
    visits: Sequence[Mapping[str, Any]] = schedule["visits"]
    if [visit["visit"] for visit in visits] != list(range(1, len(visits) + 1)):
        raise SimulationError("the visits of the calendar are not numbered 1 to n in order")
    weeks = tuple(int(visit["first_week"]) for visit in visits)
    if any(later <= earlier for earlier, later in zip(weeks, weeks[1:], strict=False)):
        raise SimulationError(f"the first weeks of the calendar do not rise: {weeks}")
    return weeks


def first_visits(
    first_weeks: Sequence[int], trimester_first_weeks: Mapping[int, int]
) -> dict[int, int]:
    """The first visit of the calendar in each trimester, as an index into ``first_weeks``.

    A pregnancy that starts care in a trimester starts at the first visit whose first week falls
    in it (docs/protocol.md §Pregnancies). For NOM-007-SSA2-2016 and the trimesters of D-092 that
    is visit 1 (week 6), visit 3 (week 16) and visit 5 (week 28).

    Raises:
        SimulationError: the trimesters are not 1, 2 and 3 in rising weeks, or one holds no visit.
    """
    if sorted(trimester_first_weeks) != [1, 2, 3]:
        raise SimulationError(f"the trimesters are {sorted(trimester_first_weeks)}, not 1, 2 and 3")
    bounds = [trimester_first_weeks[trimester] for trimester in (1, 2, 3)]
    if bounds != sorted(set(bounds)):
        raise SimulationError(f"the first weeks of the trimesters do not rise: {bounds}")
    ends = [*bounds[1:], None]
    starts: dict[int, int] = {}
    for trimester, start, end in zip((1, 2, 3), bounds, ends, strict=True):
        inside = [
            index
            for index, week in enumerate(first_weeks)
            if week >= start and (end is None or week < end)
        ]
        if not inside:
            raise SimulationError(f"no visit of the calendar falls in trimester {trimester}")
        starts[trimester] = inside[0]
    return starts


def calibrate(
    combinations: Iterable[Combination],
    first_weeks: Sequence[int],
    first_visit: Mapping[int, int],
) -> Calibration:
    """Set p from the observed births of definition 2 (D-096, FOR APPROVAL).

    A pregnancy that starts in the first trimester and is delivered at the first week of the last
    visit or later can have every visit of the calendar. With each visit after the first one
    happening with probability p, it has all of them with probability p to the power of the
    visits after the first, so p is that root of the observed share.

    Raises:
        SimulationError: no observed birth meets the condition.
    """
    from_week = first_weeks[-1]
    eligible = [c for c in combinations if c.trimester == 1 and c.weeks >= from_week]
    births = sum(c.births for c in eligible)
    if births == 0:
        raise SimulationError(
            f"no birth started care in the first trimester and was delivered at {from_week} "
            "weeks or more, so p cannot be set"
        )
    full = sum(c.births for c in eligible if c.visits >= len(first_weeks))
    share = full / births
    later_visits = len(first_weeks) - 1 - first_visit[1]
    return Calibration(
        from_week=from_week,
        # The observed births are whole counts.
        births=int(births),
        full_calendar_share=share,
        visit_probability=share ** (1 / later_visits),
    )


def _checked(combinations: Iterable[Combination]) -> list[Combination]:
    """The combinations with births, sorted, so the draws never depend on the order of a query."""
    rows = sorted(combinations)
    for row in rows:
        if row.trimester not in _TRIMESTERS:
            raise SimulationError(f"trimester {row.trimester} is not 0, 1, 2 or 3")
        if row.births < 0:
            raise SimulationError(f"a combination holds {row.births} births")
    rows = [row for row in rows if row.births > 0]
    if not rows:
        raise SimulationError("there is no birth to simulate")
    return rows


def _births_by(rows: Iterable[Combination], field: str) -> dict[int, float]:
    """The births per value of one field of the combinations, by rising value."""
    births: dict[int, float] = {}
    for row in rows:
        value = getattr(row, field)
        births[value] = births.get(value, 0) + row.births
    return dict(sorted(births.items()))


def simulate(
    combinations: Iterable[Combination],
    scenario: Scenario,
    *,
    first_weeks: Sequence[int],
    first_visit: Mapping[int, int],
    visit_probability: float,
    seed: int,
) -> list[Combination]:
    """Simulate one pregnancy per observed birth under one scenario (docs/protocol.md §Null
    simulation).

    Each pregnancy keeps the completed weeks of its record. Its trimester of the first visit is
    drawn from the observed distribution, independently of the weeks. It starts at the first
    visit of the calendar in that trimester, and a visit happens when the weeks reach its first
    week. In E1 every visit after the first one happens; in E2 each one happens independently
    with probability ``visit_probability``. A pregnancy delivered before its first visit has none,
    and is recorded as no care, trimester 0.

    Args:
        combinations: the observed births of definition 2 per combination; only their weeks and
            the distribution of their trimesters are read.
        scenario: the scenario, whose stream of ``seed`` it draws from.
        first_weeks: :func:`calendar_first_weeks`.
        first_visit: :func:`first_visits`.
        visit_probability: p (:func:`calibrate`); E1 does not read it.
        seed: the seed of ``config/null_simulation.yml``.

    Returns:
        The simulated births per combination, as many as the observed ones, sorted.

    Raises:
        SimulationError: p outside 0 to 1, or a table with no birth or an unknown trimester.
    """
    if not 0 <= visit_probability <= 1:
        raise SimulationError(f"p = {visit_probability} is not a probability")
    rows = _checked(combinations)
    weeks = np.repeat(
        np.array([row.weeks for row in rows], dtype=np.int64),
        np.array([row.births for row in rows], dtype=np.int64),
    )
    observed = _births_by(rows, "trimester")
    codes = np.array(sorted(observed), dtype=np.int64)
    shares = np.array([observed[code] for code in sorted(observed)], dtype=np.float64)

    rng = np.random.default_rng(np.random.SeedSequence(seed, spawn_key=(scenario.stream,)))
    trimester = rng.choice(codes, size=weeks.size, p=shares / shares.sum())

    # The index of the first visit of each pregnancy; -1 for trimester 0, which has no visit.
    start_of = np.full(len(_TRIMESTERS), -1, dtype=np.int64)
    for code, index in first_visit.items():
        start_of[code] = index
    start = start_of[trimester]
    # The visits of the calendar whose first week the pregnancy reached, counted from visit 1.
    reached = np.searchsorted(np.array(first_weeks, dtype=np.int64), weeks, side="right")
    possible = np.where(start >= 0, np.maximum(reached - start, 0), 0)
    if scenario.misses:
        later = rng.binomial(np.maximum(possible - 1, 0), visit_probability)
        visits = np.where(possible > 0, 1 + later, 0)
    else:
        visits = possible
    recorded = np.where(visits == 0, 0, trimester)

    # One key per combination, so counting the pregnancies is a single sort.
    width = len(first_weeks) + 1
    keys = (weeks * len(_TRIMESTERS) + recorded) * width + visits
    unique, counts = np.unique(keys, return_counts=True)
    return [
        Combination(
            weeks=int(key // (len(_TRIMESTERS) * width)),
            trimester=int(key // width % len(_TRIMESTERS)),
            visits=int(key % width),
            births=int(count),
        )
        for key, count in zip(unique.tolist(), counts.tolist(), strict=True)
    ]


def expected(
    combinations: Iterable[Combination],
    scenario: Scenario,
    *,
    first_weeks: Sequence[int],
    first_visit: Mapping[int, int],
    visit_probability: float,
) -> list[Combination]:
    """The births :func:`simulate` gives on average: the exact expectation of a scenario, with no
    draw (D-115).

    The births of each observed week are split across the trimesters in their observed shares.
    The visits of a pregnancy then follow from the calendar: all of them in E1, and in E2 the
    first one plus a binomial count of the later ones. The births are means, with fractions.

    Both scenarios are simple enough to have this closed form, so it checks the simulation: two
    computations of the same model have to agree, up to the noise of the draws. A scenario with
    no closed form would have only the simulation.

    Raises:
        SimulationError: as :func:`simulate`.
    """
    if not 0 <= visit_probability <= 1:
        raise SimulationError(f"p = {visit_probability} is not a probability")
    rows = _checked(combinations)
    by_weeks = _births_by(rows, "weeks")
    by_trimester = _births_by(rows, "trimester")
    total = sum(by_trimester.values())

    births: dict[tuple[int, int, int], float] = {}

    def add(key: tuple[int, int, int], mass: float) -> None:
        births[key] = births.get(key, 0) + mass

    for weeks, delivered in by_weeks.items():
        reached = bisect_right(first_weeks, weeks)
        for trimester, started in by_trimester.items():
            mass = delivered * started / total
            possible = 0 if trimester == 0 else max(reached - first_visit[trimester], 0)
            if possible == 0:
                add((weeks, 0, 0), mass)
            elif not scenario.misses:
                add((weeks, trimester, possible), mass)
            else:
                later = possible - 1
                for kept in range(later + 1):
                    chance = (
                        comb(later, kept)
                        * visit_probability**kept
                        * (1 - visit_probability) ** (later - kept)
                    )
                    add((weeks, trimester, 1 + kept), mass * chance)
    return [Combination(*key, births=mass) for key, mass in sorted(births.items()) if mass > 0]
