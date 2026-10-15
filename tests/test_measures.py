"""Tests for the measures and their crude comparison (task 1.7.1, docs/protocol.md §The measures,
§What truncation alone explains).

The levels, the odds ratios and the shares are worked out by hand from small tables. The cut points
are those of config/nom007_schedule.yml, read as scripts/simulate.py reads them.
"""

import re
from pathlib import Path

import pytest

import simulate as script
from sinac_truncation.apncu import compute_apncu
from sinac_truncation.measures import (
    APNCU_VARIANT,
    FIRST_TRIMESTER,
    LATER_OR_NO_CARE,
    Crude,
    LevelCount,
    Share,
    ShareRow,
    compare,
    crude,
    excludes_one,
    format_shares,
    largest_share_difference,
    level_counts,
    ordered_levels,
    reached,
    reference_level,
    truncation_shares,
    visits_level,
)
from sinac_truncation.simulation import Combination

CUTS = script.read_settings().cuts
EXPOSURE_SQL = Path(__file__).resolve().parents[1] / "sql" / "cohorts" / "exposure.sql"


# --- The levels ----------------------------------------------------------------------------------


def test_the_cut_points_are_the_minimum_and_the_calendar_of_the_norm() -> None:
    assert (CUTS.minimum, CUTS.calendar) == (5, 8)


@pytest.mark.parametrize(
    ("visits", "level"),
    [(0, "0"), (1, "1-4"), (4, "1-4"), (5, "5-7"), (7, "5-7"), (8, "8+"), (30, "8+")],
)
def test_measure_a_has_the_four_levels_of_d_088(visits: int, level: str) -> None:
    assert visits_level(visits, CUTS) == level


def test_measure_a_has_the_labels_of_the_sql() -> None:
    """results.exposure writes the same four labels, so the two can be compared row by row."""
    labels = set(re.findall(r"THEN '([^']+)'", EXPOSURE_SQL.read_text(encoding="utf-8")))
    assert labels == {visits_level(visits, CUTS) for visits in (0, 1, 5, 8)}


def test_a_negative_count_has_no_level() -> None:
    with pytest.raises(ValueError):
        visits_level(-1, CUTS)


#: Six combinations: 36 weeks is preterm and 37 is not.
TABLE = [
    Combination(weeks=36, trimester=1, visits=7, births=10),
    Combination(weeks=37, trimester=1, visits=7, births=30),
    Combination(weeks=40, trimester=1, visits=8, births=50),
    Combination(weeks=30, trimester=2, visits=3, births=4),
    Combination(weeks=40, trimester=3, visits=3, births=6),
    Combination(weeks=33, trimester=0, visits=0, births=2),
]


def test_measure_a_counts_births_and_preterm_births_per_level() -> None:
    assert level_counts(TABLE, "a", CUTS) == {
        "5-7": LevelCount(births=40, preterm=10),
        "8+": LevelCount(births=50, preterm=0),
        "1-4": LevelCount(births=10, preterm=4),
        "0": LevelCount(births=2, preterm=2),
    }


def test_measure_a_per_count_has_one_level_per_count() -> None:
    assert level_counts(TABLE, "a_count", CUTS) == {
        "7": LevelCount(40, 10),
        "8": LevelCount(50, 0),
        "3": LevelCount(10, 4),
        "0": LevelCount(2, 2),
    }


def test_measure_b_is_the_index_of_compute_apncu_for_each_combination() -> None:
    expected: dict[str, LevelCount] = {}
    for row in TABLE:
        level = compute_apncu(row.visits, row.trimester, row.weeks).level.value
        before = expected.get(level, LevelCount(0, 0))
        expected[level] = LevelCount(
            before.births + row.births, before.preterm + row.births * (row.weeks < 37)
        )
    assert level_counts(TABLE, "b", CUTS) == expected


def test_measure_c_sets_the_first_trimester_against_the_rest() -> None:
    assert level_counts(TABLE, "c", CUTS) == {
        FIRST_TRIMESTER: LevelCount(90, 10),
        LATER_OR_NO_CARE: LevelCount(12, 6),
    }


def test_the_preterm_cut_off_is_a_parameter() -> None:
    """At 34 weeks, the births of 36 and 33 weeks change side; 30 weeks stays preterm."""
    assert level_counts(TABLE, "c", CUTS, preterm_weeks=34) == {
        FIRST_TRIMESTER: LevelCount(90, 0),
        LATER_OR_NO_CARE: LevelCount(12, 6),
    }


def test_a_landmark_keeps_the_pregnancies_that_reached_its_week() -> None:
    assert reached(TABLE, 37) == [TABLE[1], TABLE[2], TABLE[4]]


@pytest.mark.parametrize(
    ("measure", "reference"),
    [("a", "8+"), ("a_count", "8"), ("b", "Adequate"), ("c", FIRST_TRIMESTER), ("d", "8+")],
)
def test_the_reference_is_care_that_meets_the_norm(measure: str, reference: str) -> None:
    assert reference_level(measure, CUTS) == reference


def test_an_unknown_measure_is_refused() -> None:
    with pytest.raises(ValueError):
        reference_level("e", CUTS)
    with pytest.raises(ValueError):
        level_counts(TABLE, "e", CUTS)


def test_the_levels_are_reported_in_the_order_of_the_protocol() -> None:
    assert ordered_levels("a", {"8+", "0", "5-7"}, CUTS) == ["0", "5-7", "8+"]
    assert ordered_levels("a_count", {"10", "9", "0"}, CUTS) == ["0", "9", "10"]
    assert ordered_levels("b", {"Adequate Plus", "Inadequate"}, CUTS) == [
        "Inadequate",
        "Adequate Plus",
    ]
    assert ordered_levels("c", {LATER_OR_NO_CARE}, CUTS) == [LATER_OR_NO_CARE]


# --- The crude comparison -------------------------------------------------------------------------


def test_the_crude_odds_ratio_and_its_wald_interval() -> None:
    """30 preterm of 100 against 10 of 100: (30/70) / (10/90) = 3.857, and the interval is
    exp(log 3.857 ± 1.96 × √(1/30 + 1/70 + 1/10 + 1/90))."""
    estimate = crude(LevelCount(100, 30), LevelCount(100, 10))
    assert tuple(estimate) == pytest.approx(
        (3.8571428571428577, 1.7666027896243972, 8.421559791361659, 0.2)
    )


def test_a_reference_without_preterm_births_has_a_risk_difference_and_no_odds_ratio() -> None:
    """The separation of the null calendar (D-112): 25 % against 0 %."""
    estimate = crude(LevelCount(100, 25), LevelCount(400, 0))
    assert (estimate.odds_ratio, estimate.lower, estimate.upper) == (None, None, None)
    assert estimate.risk_difference == pytest.approx(0.25)


@pytest.mark.parametrize(
    ("level", "reference"),
    [(None, LevelCount(10, 1)), (LevelCount(10, 1), None), (LevelCount(0, 0), LevelCount(10, 1))],
    ids=["no-level", "no-reference", "empty-level"],
)
def test_a_missing_level_has_no_estimate(
    level: LevelCount | None, reference: LevelCount | None
) -> None:
    assert crude(level, reference) == Crude(None, None, None, None)


def test_an_interval_excludes_1_only_when_it_exists() -> None:
    assert excludes_one(Crude(2.0, 1.1, 3.0, 0.1))
    assert excludes_one(Crude(0.5, 0.3, 0.9, -0.1))
    assert not excludes_one(Crude(1.2, 0.5, 3.0, 0.02))
    assert not excludes_one(Crude(None, None, None, 0.25))


# --- The share (D-112) ----------------------------------------------------------------------------

#: Observed: 30 % against 10 % preterm, an interval that excludes 1; 12 % against 10 %, one that
#: includes it. Simulated: the reference has no preterm birth, as on the null calendar.
OBSERVED = {"low": LevelCount(100, 30), "mid": LevelCount(100, 12), "ref": LevelCount(100, 10)}
SIMULATED = {"low": LevelCount(100, 50), "mid": LevelCount(100, 20), "ref": LevelCount(100, 0)}


def test_the_share_is_the_simulated_over_the_observed_risk_difference() -> None:
    """(50 % - 0 %) / (30 % - 10 %) = 2.5: truncation alone produces more than is observed."""
    [low] = truncation_shares(OBSERVED, SIMULATED, "ref", ["low"])
    assert low.share == pytest.approx(2.5)
    assert low.simulated.odds_ratio is None
    assert low.observed.odds_ratio == pytest.approx(3.8571428571428577)


def test_the_share_is_not_reported_where_the_observed_interval_includes_1() -> None:
    """12 against 10 of 100: odds ratio 1.23, from 0.50 to 2.99."""
    [mid] = truncation_shares(OBSERVED, SIMULATED, "ref", ["mid"])
    assert mid.observed.lower == pytest.approx(0.5044107671116359)
    assert mid.observed.upper == pytest.approx(2.9860551068968104)
    assert mid.share is None
    assert mid.simulated.risk_difference == pytest.approx(0.2)


def test_the_share_is_not_reported_for_a_level_the_simulation_does_not_produce() -> None:
    observed = {**OBSERVED, "high": LevelCount(100, 40)}
    [high] = truncation_shares(observed, SIMULATED, "ref", ["high"])
    assert high == Share(
        "high", crude(observed["high"], observed["ref"]), Crude(None, None, None, None), None
    )


#: Observed records of the analysis cohort (2) and of the landmark of week 37 (3), and one
#: simulated scenario.
ANALYSIS = [
    Combination(36, 1, 7, 20),
    Combination(39, 1, 9, 80),
    Combination(36, 2, 4, 15),
    Combination(39, 2, 4, 45),
]
LANDMARK = [row for row in ANALYSIS if row.weeks >= 37]
PREGNANCIES = [
    Combination(36, 1, 7, 25),
    Combination(39, 1, 8, 75),
    Combination(36, 2, 3, 20),
    Combination(39, 2, 6, 40),
]


def test_the_comparison_covers_every_measure_of_each_scenario() -> None:
    rows = compare(
        {2: ANALYSIS, 3: LANDMARK},
        {"e1": PREGNANCIES, "e2": PREGNANCIES},
        CUTS,
        analysis_definition=2,
        landmarks={3: 37},
    )
    keys = {(row.definition, row.measure, row.scenario) for row in rows}
    assert keys == {
        (definition, measure, scenario)
        for scenario in ("e1", "e2")
        for definition, measure in [(2, "a"), (2, "a_count"), (2, "b"), (2, "c"), (3, "d")]
    }
    assert {row.variant for row in rows if row.measure == "b"} == {APNCU_VARIANT}
    assert {row.variant for row in rows if row.measure != "b"} == {""}
    for row in rows:
        assert row.reference == reference_level(row.measure, CUTS)
        assert row.share.level != row.reference


def test_measure_d_compares_the_landmark_with_the_pregnancies_that_reached_it() -> None:
    rows = compare(
        {2: ANALYSIS, 3: LANDMARK},
        {"e1": PREGNANCIES},
        CUTS,
        analysis_definition=2,
        landmarks={3: 37},
    )
    shares = {row.share.level: row.share for row in rows if row.measure == "d"}
    # The levels of either side: 1-4 is observed only, 5-7 simulated only.
    assert list(shares) == ["1-4", "5-7"]
    # Observed at 37 weeks or more: 1-4 visits, 45 term births, against 80 term births at 8+.
    assert shares["1-4"].observed == Crude(None, None, None, 0.0)
    # Simulated: only the pregnancies delivered at 39 weeks reach the landmark, none with 1-4.
    assert shares["1-4"].simulated == Crude(None, None, None, None)
    assert shares["5-7"].simulated == crude(LevelCount(40, 0), LevelCount(75, 0))


def test_the_report_has_one_line_per_row_and_blanks_what_does_not_exist() -> None:
    rows = compare(
        {2: ANALYSIS, 3: LANDMARK},
        {"e1": PREGNANCIES},
        CUTS,
        analysis_definition=2,
        landmarks={3: 37},
    )
    lines = format_shares(rows)
    assert len(lines) == len(rows) + 1
    assert lines[0].split() == [
        "def", "measure", "level", "scenario", "OR", "obs", "OR", "sim", "RD", "obs", "pp", "RD",
        "sim", "pp", "share",
    ]  # fmt: skip
    [line] = [
        line
        for row, line in zip(rows, lines[1:], strict=True)
        if row.measure == "d" and row.share.level == "1-4"
    ]
    # Only the observed risk difference exists, 0 points.
    assert line.split() == ["3", "d", "1-4", "e1", "0.00"]


def test_the_largest_share_difference_is_relative_and_per_scenario() -> None:
    """Shares of 2.5 and 4.0 against exact ones of 2.0 and 4.0: 25 % in e1; none in e2."""

    def row(scenario: str, level: str, share: float | None) -> ShareRow:
        empty = Crude(None, None, None, None)
        return ShareRow(2, "a", "", scenario, "8+", Share(level, empty, empty, share))

    simulated = [row("e1", "0", 2.5), row("e1", "1-4", 4.0), row("e2", "0", None)]
    exact = [row("e1", "0", 2.0), row("e1", "1-4", 4.0), row("e2", "0", 1.5)]
    assert largest_share_difference(simulated, exact) == {"e1": pytest.approx(0.25), "e2": None}
