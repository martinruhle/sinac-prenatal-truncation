"""Tests for the null simulation (task 1.7.1, docs/protocol.md §Null simulation).

The calendar is that of config/nom007_schedule.yml and the trimesters those of
config/null_simulation.yml, read as scripts/simulate.py reads them. The visits each pregnancy of E1
must have are written by hand from the calendar, never measured on a run. The observed births are
small synthetic tables, and the scenarios run on them with the same code as on the cohort.
"""

import random
from collections import Counter
from collections.abc import Sequence

import pytest

import simulate as script
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

SETTINGS = script.read_settings()
E1, E2 = SETTINGS.scenarios
SEED = 2026


def run(
    combinations: Sequence[Combination],
    scenario: Scenario = E1,
    *,
    p: float = 0.9,
    seed: int = SEED,
) -> list[Combination]:
    return simulate(
        combinations,
        scenario,
        first_weeks=SETTINGS.first_weeks,
        first_visit=SETTINGS.first_visit,
        visit_probability=p,
        seed=seed,
    )


def births(weeks: int, trimester: int, count: int = 1, visits: int = 0) -> Combination:
    """Observed births; the simulation reads only their weeks and their trimester."""
    return Combination(weeks=weeks, trimester=trimester, visits=visits, births=count)


# --- The calendar and the trimesters -------------------------------------------------------------


def test_the_calendar_is_read_from_the_first_week_of_each_visit() -> None:
    assert SETTINGS.first_weeks == (6, 10, 16, 22, 28, 32, 36, 38)


def test_each_trimester_starts_at_its_first_visit_of_the_calendar() -> None:
    """Visit 1 (week 6), visit 3 (week 16) and visit 5 (week 28), as indexes from 0."""
    assert SETTINGS.first_visit == {1: 0, 2: 2, 3: 4}


@pytest.mark.parametrize(
    "visits",
    [
        [{"visit": 2, "first_week": 6}, {"visit": 1, "first_week": 10}],
        [{"visit": 1, "first_week": 10}, {"visit": 2, "first_week": 10}],
    ],
    ids=["misnumbered", "not-rising"],
)
def test_a_calendar_out_of_order_is_refused(visits: list[dict[str, int]]) -> None:
    with pytest.raises(SimulationError):
        calendar_first_weeks({"visits": visits})


@pytest.mark.parametrize(
    "trimesters",
    [{1: 0, 2: 14}, {1: 0, 2: 28, 3: 14}, {1: 0, 2: 11, 3: 14}],
    ids=["missing", "not-rising", "trimester-without-a-visit"],
)
def test_trimesters_the_calendar_cannot_start_in_are_refused(trimesters: dict[int, int]) -> None:
    with pytest.raises(SimulationError):
        first_visits(SETTINGS.first_weeks, trimesters)


# --- E1: every visit of the calendar until delivery ----------------------------------------------

#: (trimester of the first visit, completed weeks at delivery, visits, recorded trimester), by
#: hand from the first weeks 6, 10, 16, 22, 28, 32, 36 and 38 (D-096): the visits from the first
#: one of the trimester whose first week the weeks reach.
E1_VISITS = [
    (1, 22, 4, 1),  # weeks 6, 10, 16 and 22
    (1, 27, 4, 1),
    (1, 28, 5, 1),  # and 28
    (1, 31, 5, 1),
    (1, 32, 6, 1),  # and 32
    (1, 35, 6, 1),
    (1, 36, 7, 1),  # and 36
    (1, 37, 7, 1),  # a range counts from its first week, so 37 weeks still has seven
    (1, 38, 8, 1),  # and 38: the full calendar
    (1, 45, 8, 1),
    (2, 22, 2, 2),  # weeks 16 and 22
    (2, 28, 3, 2),
    (2, 36, 5, 2),
    (2, 38, 6, 2),
    (3, 27, 0, 0),  # delivered before week 28, its first visit: no care, trimester 0
    (3, 28, 1, 3),  # week 28
    (3, 32, 2, 3),
    (3, 36, 3, 3),
    (3, 38, 4, 3),
    (0, 40, 0, 0),  # "NO RECIBIÓ": no visit
]


@pytest.mark.parametrize(
    ("trimester", "weeks", "visits", "recorded"),
    E1_VISITS,
    ids=[f"trimester-{t}-at-{w}" for t, w, _, _ in E1_VISITS],
)
def test_e1_has_every_visit_of_the_calendar_until_delivery(
    trimester: int, weeks: int, visits: int, recorded: int
) -> None:
    assert run([births(weeks, trimester, count=3)]) == [Combination(weeks, recorded, visits, 3)]


def test_a_pregnancy_delivered_preterm_never_has_every_visit() -> None:
    """The eighth visit starts at week 38, so no world on this calendar fills the reference of
    (a) with a preterm birth (D-112), with or without misses."""
    observed = [births(weeks, trimester) for weeks in range(22, 46) for trimester in (0, 1, 2, 3)]
    for scenario in (E1, E2):
        for row in run(observed, scenario, p=0.9):
            assert row.visits <= len(SETTINGS.first_weeks)
            if row.weeks < 37:
                assert row.visits < len(SETTINGS.first_weeks)


# --- E2: each visit after the first one with probability p ---------------------------------------


@pytest.mark.parametrize(("trimester", "weeks", "visits", "recorded"), E1_VISITS)
def test_e2_with_p_1_is_e1(trimester: int, weeks: int, visits: int, recorded: int) -> None:
    assert run([births(weeks, trimester, 5)], E2, p=1.0) == [
        Combination(weeks, recorded, visits, 5)
    ]


@pytest.mark.parametrize(("trimester", "weeks", "visits", "recorded"), E1_VISITS)
def test_e2_with_p_0_keeps_only_the_first_visit(
    trimester: int, weeks: int, visits: int, recorded: int
) -> None:
    assert run([births(weeks, trimester, 5)], E2, p=0.0) == [
        Combination(weeks, recorded, min(visits, 1), 5)
    ]


def test_e2_keeps_the_first_visit_and_misses_later_ones_at_rate_1_minus_p() -> None:
    """Delivered at 40 weeks from the first trimester: 1 + Binomial(7, p) visits, mean 7.3."""
    simulated = run([births(40, 1, count=20_000)], E2, p=0.9)
    assert {row.visits for row in simulated} <= set(range(1, 9))
    mean = sum(row.visits * row.births for row in simulated) / 20_000
    assert mean == pytest.approx(1 + 7 * 0.9, abs=0.03)


def test_p_outside_0_to_1_is_refused() -> None:
    with pytest.raises(SimulationError):
        run([births(40, 1)], E2, p=1.5)


# --- The pregnancies ------------------------------------------------------------------------------

#: An observed table where the trimester is tied to the weeks: every first-trimester start was
#: delivered at 40 weeks and every third-trimester start at 30.
TIED = [births(40, 1, count=6_000), births(30, 3, count=4_000)]


@pytest.mark.parametrize("scenario", [E1, E2], ids=["e1", "e2"])
def test_every_record_keeps_its_weeks(scenario: Scenario) -> None:
    observed = [*TIED, births(22, 0, count=50), births(37, 2, count=700)]
    simulated = run(observed, scenario)
    by_weeks = Counter[int]()
    for row in simulated:
        by_weeks[row.weeks] += row.births
    assert by_weeks == {40: 6_000, 30: 4_000, 22: 50, 37: 700}


def test_the_trimester_is_drawn_from_its_distribution_independently_of_the_weeks() -> None:
    """60 % of the records start in the first trimester; in the simulation, about 60 % of the
    pregnancies delivered at 30 weeks do too, though no observed one did."""
    simulated = run(TIED)
    for weeks in (30, 40):
        at = [row for row in simulated if row.weeks == weeks]
        first = sum(row.births for row in at if row.trimester == 1)
        assert first / sum(row.births for row in at) == pytest.approx(0.6, abs=0.03)


# --- Reproducibility ------------------------------------------------------------------------------

#: A larger table with every trimester and many weeks, so a change of stream changes the output.
MANY = [
    births(weeks, trimester, count=10 + weeks + 7 * trimester)
    for weeks in range(22, 43)
    for trimester in (0, 1, 2, 3)
]


@pytest.mark.parametrize("scenario", [E1, E2], ids=["e1", "e2"])
def test_two_runs_with_the_same_seed_give_the_same_output(scenario: Scenario) -> None:
    assert run(MANY, scenario) == run(MANY, scenario)


def test_the_output_does_not_depend_on_the_order_of_the_query() -> None:
    shuffled = list(MANY)
    random.Random(1).shuffle(shuffled)
    assert run(shuffled, E2) == run(MANY, E2)


def test_another_seed_gives_another_output() -> None:
    assert run(MANY, E2, seed=SEED + 1) != run(MANY, E2)


def test_a_scenario_draws_from_its_own_stream() -> None:
    """Only the seed and the stream set the draws, so adding a scenario changes no other one."""
    renamed = E2._replace(id="e9", name="Another name")
    assert run(MANY, renamed) == run(MANY, E2)
    assert run(MANY, E2._replace(stream=E2.stream + 1)) != run(MANY, E2)


def test_the_scenarios_of_the_configuration_have_their_own_streams() -> None:
    assert [(s.id, s.misses) for s in SETTINGS.scenarios] == [("e1", False), ("e2", True)]
    assert len({s.stream for s in SETTINGS.scenarios}) == len(SETTINGS.scenarios)


@pytest.mark.parametrize(
    "observed",
    [[], [births(40, 1, count=0)], [births(40, 4)], [births(40, 1, count=-1)]],
    ids=["empty", "no-birth", "unknown-trimester", "negative-births"],
)
def test_a_table_the_simulation_cannot_run_on_is_refused(observed: list[Combination]) -> None:
    with pytest.raises(SimulationError):
        run(observed)


# --- p (D-096) ------------------------------------------------------------------------------------


def test_p_makes_the_share_with_every_visit_that_of_the_observed_term_births() -> None:
    """64 of the 100 first-trimester starts delivered at 38 weeks or more had 8 visits or more,
    so p ** 7 = 0.64. The other records do not count: a first-trimester start at 37 weeks, which
    cannot reach eight visits, and a second-trimester start at 40."""
    observed = [
        births(38, 1, count=30, visits=8),
        births(40, 1, count=24, visits=10),
        births(41, 1, count=10, visits=9),
        births(39, 1, count=36, visits=7),
        births(37, 1, count=500, visits=3),
        births(40, 2, count=500, visits=12),
    ]
    calibration = calibrate(observed, SETTINGS.first_weeks, SETTINGS.first_visit)
    assert calibration._replace(visit_probability=0.0) == Calibration(
        from_week=38, births=100, full_calendar_share=0.64, visit_probability=0.0
    )
    assert calibration.visit_probability == pytest.approx(0.938234557087083)
    assert calibration.visit_probability**7 == pytest.approx(0.64)


def test_p_cannot_be_set_without_a_first_trimester_start_at_term() -> None:
    with pytest.raises(SimulationError):
        calibrate([births(37, 1, visits=7)], SETTINGS.first_weeks, SETTINGS.first_visit)
