"""The odds ratios of preterm birth for each measure, crude and adjusted, from the aggregated
table of the models (docs/protocol.md §Model, §Covariates, D-093, D-117, D-118).

The aggregated table holds the births of a definition per combination of completed weeks,
first-visit trimester, visits and the four covariates (:class:`Cell`). The level of a measure
comes from :func:`~sinac_truncation.measures.measure_level`, the code of the crude comparison and
of the null simulation (D-113), and the outcome comes from the weeks. Collapsing the table over
everything else gives the table of one model: one row per level and combination of covariates,
with its births and preterm births. With every term categorical, a binomial GLM on that table
gives the estimates of a logistic regression on the individual records (D-093).

- **Crude.** The exposure alone: the closed form of :func:`~sinac_truncation.measures.crude`.
- **Adjusted.** The exposure, age group, education, state and year, all categorical (D-094), in a
  binomial GLM with a logit link fitted by statsmodels, with 95 % Wald intervals. The coefficients
  of the covariates are not returned: the model is built to estimate the exposure (D-093).

Each measure is the exposure of its own model and never a covariate of another. Measure (b) is
fitted to show the artefact of its construction, never read as an effect (CLAUDE.md rule 3).
There is no I/O here (CLAUDE.md rule 6).
"""

import warnings
from collections import defaultdict
from collections.abc import Callable, Hashable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from math import exp
from typing import NamedTuple

import numpy as np
import numpy.typing as npt
import statsmodels.api as sm
from statsmodels.tools.sm_exceptions import (
    ConvergenceWarning,
    PerfectSeparationWarning,
    SingularMatrixWarning,
)

from sinac_truncation.measures import (
    APNCU_VARIANT,
    PRETERM_WEEKS,
    LevelCount,
    VisitCuts,
    crude,
    level_counts,
    measure_level,
    ordered_levels,
    reached,
    reference_level,
)
from sinac_truncation.simulation import Combination

__all__ = [
    "ADJUSTED",
    "COVARIATES",
    "CRUDE",
    "OBSERVED",
    "Adjusted",
    "Cell",
    "DistributionRow",
    "EstimateRow",
    "Estimates",
    "ModelError",
    "ModelRow",
    "OddsRatio",
    "adjusted",
    "definition_measures",
    "format_estimates",
    "model_table",
    "observed_estimates",
    "simulated_estimates",
    "simulated_source",
    "summed",
]

#: The covariates of the adjusted model, in the order of :attr:`ModelRow.covariates` (D-094).
COVARIATES: tuple[str, ...] = ("age_group", "education", "state", "year")

#: The values of the columns source and model of docs/protocol.md §Output tables.
OBSERVED = "observed"
CRUDE = "crude"
ADJUSTED = "adjusted"

#: The two values of the column outcome of ``exposure_distribution.csv``.
PRETERM = "preterm"
TERM = "term"

#: The measures of the analysis cohort. Measure (d) is (a) on each landmark cohort.
_ANALYSIS_MEASURES: tuple[str, ...] = ("a", "a_count", "b", "c")


class Cell(NamedTuple):
    """One row of the aggregated table, ``sql/analysis/aggregated_count.sql``."""

    weeks: int
    trimester: int
    visits: int
    age_group: str
    #: The concept of the education level (D-101).
    education: int
    state: str
    year: int
    births: int


#: The covariates of one row of a model table, in the order of :data:`COVARIATES`.
Covariates = tuple[str, int, str, int]


class ModelRow(NamedTuple):
    """One row of the table a model is fitted on: a level of the exposure and a combination of
    the covariates."""

    level: str
    covariates: Covariates
    births: int
    preterm: int


class OddsRatio(NamedTuple):
    """The odds ratio of a level against the reference and its 95 % Wald interval; ``None`` where
    there is no estimate."""

    odds_ratio: float | None
    lower: float | None
    upper: float | None


_NO_ESTIMATE = OddsRatio(None, None, None)


class Adjusted(NamedTuple):
    """The adjusted odds ratio of every level that has one, and the births the fit set aside."""

    odds_ratios: dict[str, OddsRatio]
    #: The births of the levels whose births are all preterm or all term (:func:`adjusted`).
    set_aside: int


class ModelError(RuntimeError):
    """A model could not be fitted: it did not converge."""


class EstimateRow(NamedTuple):
    """One row of ``estimates.csv`` (docs/protocol.md §Output tables)."""

    source: str
    definition: int
    period: str
    outcome_cutoff: int
    measure: str
    variant: str
    level: str
    reference: str
    model: str
    stratum_variable: str
    stratum_value: str
    #: The births and preterm births of the level.
    births: int
    preterm: int
    odds_ratio: float | None
    lower: float | None
    upper: float | None


class DistributionRow(NamedTuple):
    """One row of ``exposure_distribution.csv`` (docs/protocol.md §Output tables)."""

    source: str
    definition: int
    period: str
    outcome_cutoff: int
    measure: str
    variant: str
    level: str
    outcome: str
    births: int


@dataclass
class Estimates:
    """The rows one definition, or one scenario, adds to the two tables."""

    estimates: list[EstimateRow] = field(default_factory=list)
    distribution: list[DistributionRow] = field(default_factory=list)
    #: Per measure, the births the adjusted model set aside; only measures where it set some.
    set_aside: dict[str, int] = field(default_factory=dict)


def definition_measures(
    analysis_definition: int, landmarks: Iterable[int]
) -> dict[int, tuple[str, ...]]:
    """The measures estimated on each definition: (a), (a) per count, (b) and (c) on the
    analysis cohort, and (d) on each landmark cohort (docs/protocol.md §The measures)."""
    measures = {analysis_definition: _ANALYSIS_MEASURES}
    measures.update({definition: ("d",) for definition in landmarks})
    return measures


def simulated_source(scenario: str) -> str:
    """The value of the column source for a scenario of ``config/null_simulation.yml``."""
    return f"sim_{scenario}"


def summed(cells: Iterable[Cell]) -> list[Combination]:
    """The aggregated table summed over the covariates: the births per combination of weeks,
    trimester and visits, the table ``sql/analysis/combinations.sql`` reads (D-113)."""
    births: dict[tuple[int, int, int], int] = defaultdict(int)
    for cell in cells:
        births[cell.weeks, cell.trimester, cell.visits] += cell.births
    return [Combination(*key, total) for key, total in sorted(births.items())]


def model_table(
    cells: Iterable[Cell],
    measure: str,
    cuts: VisitCuts,
    *,
    preterm_weeks: int = PRETERM_WEEKS,
) -> list[ModelRow]:
    """The table of the model of one measure: the births and preterm births per level and
    combination of covariates."""
    levels: dict[tuple[int, int, int], str] = {}
    births: dict[tuple[str, Covariates], int] = defaultdict(int)
    preterm: dict[tuple[str, Covariates], int] = defaultdict(int)
    for cell in cells:
        combination = (cell.weeks, cell.trimester, cell.visits)
        level = levels.get(combination)
        if level is None:
            level = measure_level(measure, Combination(*combination, cell.births), cuts)
            levels[combination] = level
        key = (level, (cell.age_group, cell.education, cell.state, cell.year))
        births[key] += cell.births
        if cell.weeks < preterm_weeks:
            preterm[key] += cell.births
    return [
        ModelRow(level, covariates, total, preterm[level, covariates])
        for (level, covariates), total in births.items()
    ]


def _one_outcome(rows: Iterable[ModelRow], value: Callable[[ModelRow], Hashable]) -> set[Hashable]:
    """The values whose births are all preterm or all term."""
    births: dict[Hashable, int] = defaultdict(int)
    preterm: dict[Hashable, int] = defaultdict(int)
    for row in rows:
        births[value(row)] += row.births
        preterm[value(row)] += row.preterm
    return {key for key, total in births.items() if preterm[key] in (0, total)}


def _covariate(index: int) -> Callable[[ModelRow], Hashable]:
    return lambda row: row.covariates[index]


def _identified(rows: Sequence[ModelRow]) -> list[ModelRow]:
    """The rows left once every level of the exposure or of a covariate whose births are all
    preterm or all term is set aside, repeated until none is left."""
    kept = list(rows)
    while True:
        exposure = _one_outcome(kept, lambda row: row.level)
        covariates = [_one_outcome(kept, _covariate(index)) for index in range(len(COVARIATES))]
        if not exposure and not any(covariates):
            return kept
        kept = [
            row
            for row in kept
            if row.level not in exposure
            and not any(value in covariates[i] for i, value in enumerate(row.covariates))
        ]


def _covariate_reference(covariate: str, births: Mapping[Hashable, int]) -> Hashable:
    """The reference of a covariate: the latest year, and the level with the most births for the
    others (docs/protocol.md §Covariates). It does not change the odds ratio of the exposure."""
    if covariate == "year":
        return max(births, key=lambda year: int(str(year)))
    return min(births, key=lambda value: (-births[value], str(value)))


def _identified_columns(design: npt.NDArray[np.float64]) -> npt.NDArray[np.bool_]:
    """Whether each coefficient is identified: its unit vector lies in the row space of the
    design. A level whose rows are aliased with those of others has no estimate."""
    _, singular, rows_t = np.linalg.svd(design, full_matrices=False)
    tolerance = singular.max() * max(design.shape) * np.finfo(np.float64).eps
    basis = rows_t[singular > tolerance]
    identified: npt.NDArray[np.bool_] = np.isclose((basis**2).sum(axis=0), 1.0)
    return identified


def adjusted(rows: Sequence[ModelRow], reference: str) -> Adjusted:
    """The odds ratio of each level of the exposure against the reference, adjusted for the
    covariates, from a binomial GLM with a logit link on the model table.

    A level, of the exposure or of a covariate, whose births are all preterm or all term has an
    infinite coefficient. The likelihood is highest with its births predicted exactly, and those
    births then add nothing to the other estimates, so the model is fitted without them and the
    level has no estimate (D-118). The real cohorts have no such level. A level aliased with
    others, which the design cannot tell apart, has no estimate either.

    Raises:
        ModelError: the fit did not converge.
    """
    kept = _identified(rows)
    set_aside = sum(row.births for row in rows) - sum(row.births for row in kept)
    levels = sorted({row.level for row in kept} - {reference})
    if reference not in {row.level for row in kept}:
        return Adjusted({}, set_aside)

    exposure = {level: column for column, level in enumerate(levels, start=1)}
    columns = 1 + len(levels)
    terms: list[dict[Hashable, int]] = []
    for index, covariate in enumerate(COVARIATES):
        births: dict[Hashable, int] = defaultdict(int)
        for row in kept:
            births[row.covariates[index]] += row.births
        base = _covariate_reference(covariate, births)
        term: dict[Hashable, int] = {}
        for value in sorted(births, key=str):
            if value != base:
                term[value] = columns
                columns += 1
        terms.append(term)

    design = np.zeros((len(kept), columns))
    design[:, 0] = 1.0
    for line, row in enumerate(kept):
        if row.level in exposure:
            design[line, exposure[row.level]] = 1.0
        for term, value in zip(terms, row.covariates, strict=True):
            if value in term:
                design[line, term[value]] = 1.0
    outcome = np.array([(row.preterm, row.births - row.preterm) for row in kept], dtype=float)

    with warnings.catch_warnings():
        # Three warnings of statsmodels describe cases handled here. It reports a separation
        # whenever the fitted shares equal the observed ones in every row, which a table of
        # counts that the model fits exactly does without any separation; the levels with one
        # outcome were set aside above. It reports a rank-deficient design as singular; the
        # levels it cannot identify get no estimate below. A model with as many coefficients as
        # rows divides by zero residual degrees of freedom in a scale the binomial never uses.
        warnings.simplefilter("ignore", PerfectSeparationWarning)
        warnings.simplefilter("ignore", SingularMatrixWarning)
        warnings.filterwarnings("ignore", category=RuntimeWarning, module=r"statsmodels\.")
        warnings.simplefilter("error", ConvergenceWarning)
        try:
            result = sm.GLM(outcome, design, family=sm.families.Binomial()).fit()
        except ConvergenceWarning as warning:
            raise ModelError(f"the adjusted model did not converge: {warning}") from warning
    if not result.converged:
        raise ModelError("the adjusted model did not converge")
    identified = _identified_columns(design)
    estimates = np.asarray(result.params, dtype=float)
    limits = np.asarray(result.conf_int(alpha=0.05), dtype=float)
    return Adjusted(
        {
            level: OddsRatio(exp(estimates[column]), exp(limits[column, 0]), exp(limits[column, 1]))
            for level, column in exposure.items()
            if identified[column]
        },
        set_aside,
    )


def _distribution(
    source: str,
    definition: int,
    period: str,
    cutoff: int,
    measure: str,
    counts: Mapping[str, LevelCount],
    cuts: VisitCuts,
) -> list[DistributionRow]:
    variant = APNCU_VARIANT if measure == "b" else ""
    rows = []
    for level in ordered_levels(measure, counts, cuts):
        count = counts[level]
        for outcome, births in ((PRETERM, count.preterm), (TERM, count.births - count.preterm)):
            rows.append(
                DistributionRow(
                    source, definition, period, cutoff, measure, variant, level, outcome,
                    int(births),
                )
            )  # fmt: skip
    return rows


def _estimate_rows(
    source: str,
    definition: int,
    period: str,
    cutoff: int,
    measure: str,
    counts: Mapping[str, LevelCount],
    cuts: VisitCuts,
    odds_ratios: Mapping[str, Mapping[str, OddsRatio]],
) -> list[EstimateRow]:
    """One row per level but the reference and per model, in the order of the levels."""
    reference = reference_level(measure, cuts)
    variant = APNCU_VARIANT if measure == "b" else ""
    rows = []
    for level in ordered_levels(measure, set(counts) - {reference}, cuts):
        count = counts[level]
        for model, estimates in odds_ratios.items():
            estimate = estimates.get(level, _NO_ESTIMATE)
            rows.append(
                EstimateRow(
                    source, definition, period, cutoff, measure, variant, level, reference,
                    model, "", "", int(count.births), int(count.preterm), *estimate,
                )
            )  # fmt: skip
    return rows


def _crude(counts: Mapping[str, LevelCount], reference: str) -> dict[str, OddsRatio]:
    return {
        level: OddsRatio(*crude(count, counts.get(reference))[:3])
        for level, count in counts.items()
        if level != reference
    }


def observed_estimates(
    definition: int,
    measures: Sequence[str],
    cells: Sequence[Cell],
    cuts: VisitCuts,
    *,
    period: str,
    preterm_weeks: int = PRETERM_WEEKS,
) -> Estimates:
    """The crude and adjusted estimates and the exposure distribution of the measures of one
    observed definition, from its aggregated table.

    Raises:
        ModelError: an adjusted model cannot be fitted.
    """
    combinations = summed(cells)
    result = Estimates()
    for measure in measures:
        counts = level_counts(combinations, measure, cuts, preterm_weeks=preterm_weeks)
        reference = reference_level(measure, cuts)
        fit = adjusted(model_table(cells, measure, cuts, preterm_weeks=preterm_weeks), reference)
        if fit.set_aside:
            result.set_aside[measure] = fit.set_aside
        args = (OBSERVED, definition, period, preterm_weeks, measure, counts, cuts)
        result.estimates += _estimate_rows(
            *args, {CRUDE: _crude(counts, reference), ADJUSTED: fit.odds_ratios}
        )
        result.distribution += _distribution(*args)
    return result


def simulated_estimates(
    scenario: str,
    pregnancies: Sequence[Combination],
    cuts: VisitCuts,
    *,
    analysis_definition: int,
    landmarks: Mapping[int, int],
    period: str,
    preterm_weeks: int = PRETERM_WEEKS,
) -> Estimates:
    """The crude estimates and the exposure distribution of one scenario of the null simulation.

    The simulation has no covariates, so it has no adjusted model. Measure (d) takes the
    pregnancies that reached the week of each landmark, as :func:`~sinac_truncation.measures.
    compare` does (D-113).
    """
    source = simulated_source(scenario)
    result = Estimates()
    for definition, measures in definition_measures(analysis_definition, landmarks).items():
        week = landmarks.get(definition)
        selected = pregnancies if week is None else reached(pregnancies, week)
        for measure in measures:
            counts = level_counts(selected, measure, cuts, preterm_weeks=preterm_weeks)
            reference = reference_level(measure, cuts)
            args = (source, definition, period, preterm_weeks, measure, counts, cuts)
            result.estimates += _estimate_rows(*args, {CRUDE: _crude(counts, reference)})
            result.distribution += _distribution(*args)
    return result


def _ratio(estimate: EstimateRow | None) -> str:
    if estimate is None or estimate.odds_ratio is None:
        return ""
    return f"{estimate.odds_ratio:.3f} ({estimate.lower:.3f}-{estimate.upper:.3f})"


def format_estimates(rows: Sequence[EstimateRow]) -> list[str]:
    """The lines of the report that ``pipeline.py estimate`` prints: one per level, with its
    births, its preterm births and its crude and adjusted odds ratios."""
    lines = [
        f"{'def':<4}{'measure':<9}{'level':<21}{'births':>11}{'preterm':>10}"
        f"{'crude OR (95 % CI)':>26}{'adjusted OR (95 % CI)':>26}"
    ]
    adjusted_rows = {
        (row.definition, row.measure, row.level): row for row in rows if row.model == ADJUSTED
    }
    for row in rows:
        if row.model != CRUDE:
            continue
        other = adjusted_rows.get((row.definition, row.measure, row.level))
        lines.append(
            f"{row.definition:<4}{row.measure:<9}{row.level:<21}{row.births:>11,}"
            f"{row.preterm:>10,}{_ratio(row):>26}{_ratio(other):>26}"
        )
    return lines
