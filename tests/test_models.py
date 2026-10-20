"""Tests for the crude and adjusted odds ratios (task 1.6.4, docs/protocol.md §Model, D-093).

The aggregated table is checked against the individual records it aggregates: a logistic
regression on one synthetic row per birth must give the estimates of the binomial GLM on the
table. The other expected values are written by hand. Nothing here reads real data.
"""

import warnings
from collections import Counter
from math import exp

import numpy as np
import numpy.typing as npt
import pytest
import statsmodels.api as sm
from statsmodels.tools.sm_exceptions import ConvergenceWarning

from sinac_truncation.measures import (
    APNCU_VARIANT,
    FIRST_TRIMESTER,
    LATER_OR_NO_CARE,
    LevelCount,
    VisitCuts,
    crude,
    level_counts,
    reached,
)
from sinac_truncation.models import (
    ADJUSTED,
    CRUDE,
    OBSERVED,
    SENSITIVITY_MEASURES,
    Cell,
    DistributionRow,
    EstimateRow,
    ModelError,
    ModelRow,
    adjusted,
    definition_measures,
    format_estimates,
    model_table,
    observed_estimates,
    sensitivity_models,
    simulated_estimates,
    simulated_source,
    summed,
)
from sinac_truncation.simulation import Combination

CUTS = VisitCuts(minimum=5, calendar=8)

#: The covariates of a row that only the exposure and the age group tell apart.
PLAIN = ("20-24", 1, "09", 2023)
OLDER = ("35-39", 1, "09", 2023)


# --- A table that follows the model -------------------------------------------------------------

#: Within each age group the odds ratio of no visits against eight or more is exactly 2, and
#: older mothers have both more preterm births and more mothers without visits:
#:   20-24, 8+: 90 preterm of 900 (odds 1/9)    20-24, 0: 40 of 220 (odds 2/9)
#:   35-39, 8+: 25 of 100 (odds 1/3)            35-39, 0: 400 of 1,000 (odds 2/3)
CONFOUNDED = [
    ModelRow("8+", PLAIN, 900, 90),
    ModelRow("0", PLAIN, 220, 40),
    ModelRow("8+", OLDER, 100, 25),
    ModelRow("0", OLDER, 1000, 400),
]


def test_the_adjusted_model_recovers_the_odds_ratio_within_each_age_group() -> None:
    """Age confounds the crude comparison: 440 preterm of 1,220 births without visits against
    115 of 1,000 with eight or more gives (440 × 885) / (780 × 115) = 4.34. Within each age
    group the odds ratio is 2, and a model with the exposure and the age group fits the table
    exactly, so its estimate is 2."""
    estimate = crude(LevelCount(1220, 440), LevelCount(1000, 115))
    assert estimate.odds_ratio == pytest.approx(440 * 885 / (780 * 115))
    fit = adjusted(CONFOUNDED, "8+")
    assert fit.set_aside == 0
    assert fit.odds_ratios["0"].odds_ratio == pytest.approx(2.0, rel=1e-9)
    lower, upper = fit.odds_ratios["0"].lower, fit.odds_ratios["0"].upper
    assert lower is not None and upper is not None
    assert lower < 2.0 < upper


# --- The aggregated table against the individual records -----------------------------------------


def _individuals() -> list[tuple[int, int, int, str, int, str, int]]:
    """3,000 synthetic births: weeks, trimester, visits and the four covariates. Older mothers
    and state 14 have fewer visits and more preterm births, so the covariates confound."""
    rng = np.random.default_rng(2026)
    births = []
    for _ in range(3000):
        age = str(rng.choice(["15-19", "20-24", "30-34"]))
        education = int(rng.choice([1, 2, 3]))
        state = str(rng.choice(["09", "14"]))
        year = int(rng.choice([2022, 2023]))
        late = 0.35 * (age == "30-34") + 0.2 * (state == "14")
        visits = int(rng.choice([0, 3, 6, 9], p=[0.1 + late / 4, 0.2, 0.3, 0.4 - late / 4]))
        logit = -2.4 + 0.8 * (visits < 8) + 0.5 * (age == "30-34") + 0.3 * (state == "14")
        logit += 0.2 * (education == 1) - 0.1 * (year == 2022)
        preterm = rng.random() < 1 / (1 + exp(-logit))
        births.append((35 if preterm else 39, 0 if visits == 0 else 1, visits, age, education,
                       state, year))  # fmt: skip
    return births


def _cells(births: list[tuple[int, int, int, str, int, str, int]]) -> list[Cell]:
    return [Cell(*key, count) for key, count in sorted(Counter(births).items())]


def _dummies(values: list[str], reference: str) -> npt.NDArray[np.float64]:
    levels = sorted(set(values) - {reference})
    return np.array([[float(value == level) for level in levels] for value in values]).reshape(
        len(values), len(levels)
    )


def _individual_fit(
    births: list[tuple[int, int, int, str, int, str, int]], *, adjust: bool
) -> dict[str, tuple[float, float, float]]:
    """A logistic regression on one row per birth, fitted by maximum likelihood (statsmodels
    Logit, not the GLM), with the first level of each covariate as its reference."""
    levels = [{0: "0", 3: "1-4", 6: "5-7", 9: "8+"}[visits] for _, _, visits, *_ in births]
    blocks = [np.ones((len(births), 1)), _dummies(levels, "8+")]
    if adjust:
        for index in range(3, 7):
            values = [str(birth[index]) for birth in births]
            blocks.append(_dummies(values, min(values)))
    design = np.hstack(blocks)
    outcome = np.array([float(weeks < 37) for weeks, *_ in births])
    result = sm.Logit(outcome, design).fit(disp=0)
    limits = np.exp(result.conf_int())
    exposed = sorted(set(levels) - {"8+"})
    return {
        level: (
            float(np.exp(result.params[column])),
            float(limits[column, 0]),
            float(limits[column, 1]),
        )
        for column, level in enumerate(exposed, start=1)
    }


def test_the_aggregated_table_gives_the_estimates_of_the_individual_records() -> None:
    births = _individuals()
    cells = _cells(births)
    assert sum(cell.births for cell in cells) == len(births)
    assert len(cells) < len(births) / 5

    found = observed_estimates(2, ("a",), cells, CUTS, period="2022-2023")
    for model, adjust in ((CRUDE, False), (ADJUSTED, True)):
        expected = _individual_fit(births, adjust=adjust)
        rows = {row.level: row for row in found.estimates if row.model == model}
        assert set(rows) == set(expected)
        for level, (odds_ratio, lower, upper) in expected.items():
            row = rows[level]
            assert (row.odds_ratio, row.lower, row.upper) == pytest.approx(
                (odds_ratio, lower, upper), rel=1e-6
            )


@pytest.mark.filterwarnings("ignore:Perfect separation", "ignore:divide by zero")
def test_the_crude_model_is_the_glm_with_the_exposure_alone() -> None:
    """The closed form of the crude odds ratio (D-113) is the binomial GLM of D-093 without
    covariates. That GLM fits each level exactly, which statsmodels reports as a separation (see
    :func:`~sinac_truncation.models.adjusted`), and stops at its tolerance, about 1e-8."""
    rows = model_table(_cells(_individuals()), "a", CUTS)
    totals = {
        level: LevelCount(
            sum(r.births for r in rows if r.level == level),
            sum(r.preterm for r in rows if r.level == level),
        )
        for level in {row.level for row in rows}
    }
    levels = ["0", "1-4", "5-7"]
    design = np.array([[1.0, *(float(level == other) for other in levels)] for level in totals])
    outcome = np.array([(count.preterm, count.births - count.preterm) for count in totals.values()])
    result = sm.GLM(outcome, design, family=sm.families.Binomial()).fit()
    limits = np.exp(result.conf_int())
    for column, level in enumerate(levels, start=1):
        estimate = crude(totals[level], totals["8+"])
        assert (estimate.odds_ratio, estimate.lower, estimate.upper) == pytest.approx(
            (exp(result.params[column]), *limits[column]), rel=1e-6
        )


# --- Levels the model cannot estimate ------------------------------------------------------------


def test_a_level_whose_births_are_all_term_has_no_estimate_and_changes_no_other() -> None:
    rows = [*CONFOUNDED, ModelRow("1-4", PLAIN, 30, 0), ModelRow("1-4", OLDER, 12, 0)]
    fit = adjusted(rows, "8+")
    assert set(fit.odds_ratios) == {"0"}
    assert fit.set_aside == 42
    assert fit.odds_ratios == adjusted(CONFOUNDED, "8+").odds_ratios


def test_a_covariate_level_whose_births_are_all_preterm_is_set_aside() -> None:
    other_state = ("20-24", 1, "14", 2023)
    rows = [*CONFOUNDED, ModelRow("8+", other_state, 3, 3), ModelRow("0", other_state, 2, 2)]
    fit = adjusted(rows, "8+")
    assert fit.set_aside == 5
    assert fit.odds_ratios == adjusted(CONFOUNDED, "8+").odds_ratios


def test_setting_a_level_aside_repeats_until_none_is_left() -> None:
    """Once state 14 leaves, the only preterm births of 1-4 are gone, so 1-4 leaves too."""
    other_state = ("20-24", 1, "14", 2023)
    rows = [
        *CONFOUNDED,
        ModelRow("1-4", other_state, 4, 4),
        ModelRow("1-4", PLAIN, 10, 0),
    ]
    fit = adjusted(rows, "8+")
    assert fit.set_aside == 14
    assert fit.odds_ratios == adjusted(CONFOUNDED, "8+").odds_ratios


def test_a_level_aliased_with_a_covariate_level_has_no_estimate() -> None:
    """Every birth with 5-7 visits is in state 31, and state 31 has no other: the design cannot
    tell the level from the state, so 5-7 has no estimate and 0 keeps its own."""
    aliased = ("20-24", 1, "31", 2023)
    rows = [*CONFOUNDED, ModelRow("5-7", aliased, 50, 10)]
    fit = adjusted(rows, "8+")
    assert set(fit.odds_ratios) == {"0"}
    assert fit.set_aside == 0
    assert fit.odds_ratios["0"] == pytest.approx(adjusted(CONFOUNDED, "8+").odds_ratios["0"])


def test_without_the_reference_no_level_has_an_estimate() -> None:
    rows = [ModelRow("0", PLAIN, 20, 4), ModelRow("1-4", PLAIN, 30, 3)]
    assert adjusted(rows, "8+").odds_ratios == {}
    # A reference whose births are all preterm is set aside, and no level is left to compare.
    all_preterm = [ModelRow("8+", PLAIN, 5, 5), ModelRow("0", PLAIN, 20, 4)]
    fit = adjusted(all_preterm, "8+")
    assert fit.odds_ratios == {}
    assert fit.set_aside == 5


@pytest.mark.parametrize("warns", [False, True])
def test_a_fit_that_does_not_converge_stops(monkeypatch: pytest.MonkeyPatch, warns: bool) -> None:
    """statsmodels can say so with its flag or with a warning; both stop the run."""

    class Unconverged:
        converged = False

    class Model:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def fit(self) -> Unconverged:
            if warns:
                warnings.warn("IRLS did not converge", ConvergenceWarning, stacklevel=1)
            return Unconverged()

    monkeypatch.setattr(sm, "GLM", Model)
    with pytest.raises(ModelError, match="did not converge"):
        adjusted(CONFOUNDED, "8+")


# --- The rows of the two tables -----------------------------------------------------------------

#: A small analysis cohort: 39 weeks is term and 35 preterm (cut-off 37).
CELLS = [
    Cell(39, 1, 8, "20-24", 1, "09", 2023, 9),
    Cell(35, 1, 8, "20-24", 1, "09", 2023, 1),
    Cell(39, 2, 6, "20-24", 1, "09", 2023, 4),
    Cell(35, 2, 6, "20-24", 1, "09", 2023, 2),
    Cell(39, 1, 9, "35-39", 1, "09", 2022, 3),
    Cell(30, 1, 9, "35-39", 1, "09", 2022, 2),
    Cell(39, 2, 6, "35-39", 1, "09", 2022, 2),
    Cell(30, 2, 6, "35-39", 1, "09", 2022, 3),
]


def test_summing_over_the_covariates_gives_the_births_per_combination() -> None:
    assert summed(CELLS) == [
        Combination(30, 1, 9, 2),
        Combination(30, 2, 6, 3),
        Combination(35, 1, 8, 1),
        Combination(35, 2, 6, 2),
        Combination(39, 1, 8, 9),
        Combination(39, 1, 9, 3),
        Combination(39, 2, 6, 6),
    ]


def test_the_model_table_collapses_each_level_and_combination_of_covariates() -> None:
    rows = sorted(model_table(CELLS, "a", CUTS))
    assert rows == [
        ModelRow("5-7", ("20-24", 1, "09", 2023), 6, 2),
        ModelRow("5-7", ("35-39", 1, "09", 2022), 5, 3),
        ModelRow("8+", ("20-24", 1, "09", 2023), 10, 1),
        ModelRow("8+", ("35-39", 1, "09", 2022), 5, 2),
    ]
    # Another cut-off moves the outcome only: 30 weeks is preterm at 32, 35 is not.
    assert sorted(model_table(CELLS, "a", CUTS, preterm_weeks=32))[0] == ModelRow(
        "5-7", ("20-24", 1, "09", 2023), 6, 0
    )


def test_the_model_table_does_not_depend_on_the_order_of_the_cells() -> None:
    """The database returns the aggregated table in no fixed order (D-125)."""
    rows = model_table(CELLS, "a", CUTS)
    assert rows == sorted(rows)
    assert model_table(list(reversed(CELLS)), "a", CUTS) == rows


def test_the_estimates_do_not_depend_on_the_order_of_the_cells() -> None:
    """The adjusted odds ratios are equal to the last bit whatever the order of the cells, so a
    rebuild publishes the same estimates.csv, byte for byte (D-080, D-125)."""
    cells = _cells(_individuals())
    shuffled = [cells[i] for i in np.random.default_rng(125).permutation(len(cells))]
    first = observed_estimates(2, ("a", "c"), cells, CUTS, period="2022-2023")
    second = observed_estimates(2, ("a", "c"), shuffled, CUTS, period="2022-2023")
    assert second.estimates == first.estimates


def test_a_birth_at_the_cut_off_is_term() -> None:
    """Preterm is under 37 completed weeks (NOM-007-SSA2-2016 §3.25): 36 is preterm, 37 is not."""
    cells = [Cell(36, 1, 8, *PLAIN, 3), Cell(37, 1, 8, *PLAIN, 5)]
    assert model_table(cells, "a", CUTS) == [ModelRow("8+", PLAIN, 8, 3)]


def test_each_level_but_the_reference_has_a_crude_and_an_adjusted_row_with_its_counts() -> None:
    found = observed_estimates(2, ("a", "c"), CELLS, CUTS, period="2022-2023")
    keys = [(row.measure, row.level, row.model) for row in found.estimates]
    assert keys == [
        ("a", "5-7", CRUDE),
        ("a", "5-7", ADJUSTED),
        ("c", LATER_OR_NO_CARE, CRUDE),
        ("c", LATER_OR_NO_CARE, ADJUSTED),
    ]
    first = found.estimates[0]
    assert first[:13] == (
        OBSERVED, 2, "2022-2023", 37, "a", "", "5-7", "8+", CRUDE, "", "", 11, 5
    )  # fmt: skip
    # 5 preterm of 11 against 3 of 15: (5 × 12) / (6 × 3).
    assert first.odds_ratio == pytest.approx(5 * 12 / (6 * 3))
    assert found.estimates[2].reference == FIRST_TRIMESTER
    assert found.set_aside == {}


def test_the_distribution_has_every_level_and_both_outcomes() -> None:
    found = observed_estimates(2, ("a",), CELLS, CUTS, period="2022-2023")
    assert found.distribution == [
        DistributionRow(OBSERVED, 2, "2022-2023", 37, "a", "", "5-7", "preterm", 5),
        DistributionRow(OBSERVED, 2, "2022-2023", 37, "a", "", "5-7", "term", 6),
        DistributionRow(OBSERVED, 2, "2022-2023", 37, "a", "", "8+", "preterm", 3),
        DistributionRow(OBSERVED, 2, "2022-2023", 37, "a", "", "8+", "term", 12),
    ]


def test_measure_b_carries_its_variant() -> None:
    found = observed_estimates(2, ("b",), CELLS, CUTS, period="2022-2023")
    assert {row.variant for row in found.estimates} == {APNCU_VARIANT}
    assert {row.variant for row in found.distribution} == {APNCU_VARIANT}


def test_the_measures_of_each_definition() -> None:
    assert definition_measures(2, (3, 4, 5)) == {
        2: ("a", "a_count", "b", "c"),
        3: ("d",),
        4: ("d",),
        5: ("d",),
    }


def test_each_alternative_definition_changes_one_side_of_the_main_analysis() -> None:
    """The analysis cohort at 34 and 32 weeks, and the definition with multiples at 37 (D-054)."""
    assert sensitivity_models(2, 6) == [(2, 34), (2, 32), (6, 37)]
    assert SENSITIVITY_MEASURES == ("a", "c")


def test_a_scenario_has_crude_rows_only_and_its_landmarks_keep_the_weeks_reached() -> None:
    pregnancies = summed(CELLS)
    found = simulated_estimates(
        "e1", pregnancies, CUTS, analysis_definition=2, landmarks={3: 32}, period="2022-2023"
    )
    assert {row.source for row in found.estimates} == {simulated_source("e1")} == {"sim_e1"}
    assert {row.model for row in found.estimates} == {CRUDE}
    landmark = [row for row in found.distribution if row.definition == 3]
    counts = level_counts(reached(pregnancies, 32), "d", CUTS)
    assert sum(row.births for row in landmark) == sum(c.births for c in counts.values()) == 21
    assert {(row.definition, row.measure) for row in found.estimates} == {
        (2, "a"),
        (2, "a_count"),
        (2, "b"),
        (2, "c"),
        (3, "d"),
    }


def test_the_report_prints_both_models_on_one_line() -> None:
    row = EstimateRow(
        OBSERVED, 2, "2023", 37, "c", "", LATER_OR_NO_CARE, FIRST_TRIMESTER, CRUDE, "", "",
        1200, 85, 1.0, 0.9, 1.1,
    )  # fmt: skip
    lines = format_estimates([row, row._replace(model=ADJUSTED, odds_ratio=1.065)])
    assert len(lines) == 2
    assert lines[1].split()[-6:] == [
        "1,200",
        "85",
        "1.000",
        "(0.900-1.100)",
        "1.065",
        "(0.900-1.100)",
    ]
    no_estimate = row._replace(odds_ratio=None, lower=None, upper=None)
    assert format_estimates([no_estimate])[1].rstrip().endswith("85")


def test_the_report_pairs_the_models_of_each_cut_off_apart() -> None:
    """One level at two cut-offs gives two lines, each with its own adjusted odds ratio."""
    row = EstimateRow(
        OBSERVED, 2, "2023", 37, "c", "", LATER_OR_NO_CARE, FIRST_TRIMESTER, CRUDE, "", "",
        1200, 85, 1.0, 0.9, 1.1,
    )  # fmt: skip
    at_34 = row._replace(outcome_cutoff=34, preterm=40)
    lines = format_estimates(
        [
            row,
            row._replace(model=ADJUSTED, odds_ratio=1.065),
            at_34,
            at_34._replace(model=ADJUSTED, odds_ratio=1.2),
        ]
    )
    assert [line.split()[:2] for line in lines[1:]] == [["2", "37"], ["2", "34"]]
    assert [line.split()[-2] for line in lines[1:]] == ["1.065", "1.200"]
