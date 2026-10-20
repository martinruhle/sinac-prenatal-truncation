"""The exposure measures and their crude comparison with preterm birth, from the births per
combination of completed weeks, first-visit trimester and visits (docs/protocol.md §The measures,
§Null simulation, D-113).

The records of an observed definition and the pregnancies of a simulated scenario both reduce to
that table (:class:`~sinac_truncation.simulation.Combination`). Every measure is a function of
its three values and the outcome is a function of the weeks, so the same code gives the levels
and the crude estimates of both (D-097).

Only crude estimates live here. A crude model has the exposure alone, and with one categorical
exposure the binomial GLM of D-093 has a closed form: the odds ratio of each level against the
reference, with its Wald interval. The adjusted models are in :mod:`sinac_truncation.models`.
There is no I/O here (CLAUDE.md rule 6).
"""

from collections.abc import Iterable, Mapping, Sequence
from functools import cache
from math import exp, log, sqrt
from statistics import NormalDist
from typing import Any, NamedTuple

from sinac_truncation.apncu import ApncuLevel, compute_apncu
from sinac_truncation.simulation import Combination

__all__ = [
    "APNCU_VARIANT",
    "FIRST_TRIMESTER",
    "LATER_OR_NO_CARE",
    "MEASURES",
    "PRETERM_WEEKS",
    "SENSITIVITY_CUTOFFS",
    "Crude",
    "LevelCount",
    "Share",
    "ShareRow",
    "VisitCuts",
    "compare",
    "crude",
    "excludes_one",
    "format_shares",
    "largest_share_difference",
    "level_counts",
    "measure_level",
    "ordered_levels",
    "reached",
    "reference_level",
    "truncation_shares",
    "visits_level",
]

#: A birth under 37 completed weeks is preterm: NOM-007-SSA2-2016 §3.25 (docs/protocol.md
#: §Outcome, D-053). The cut-offs of 34 and 32 weeks are a sensitivity axis (D-003).
PRETERM_WEEKS = 37

#: The other side of the axis "preterm cut-off": under 34 and under 32 completed weeks, from
#: proposal v2 §Sensitivity of the definition (docs/protocol.md §Sensitivity of the definition).
#: Only the outcome moves; the cohort and its attrition do not.
SENSITIVITY_CUTOFFS: tuple[int, ...] = (34, 32)

#: The measures of docs/protocol.md §Output tables: (a), (a) per count, (b), (c) and (d).
MEASURES: tuple[str, ...] = ("a", "a_count", "b", "c", "d")

#: Measure (b) on the ACOG schedule with the middle month of the trimester (D-092, D-098).
APNCU_VARIANT = "acog_midpoint"

#: The two levels of measure (c), D-089. "NO RECIBIÓ" belongs to the second.
FIRST_TRIMESTER = "trimester 1"
LATER_OR_NO_CARE = "trimester 0, 2 or 3"

#: The 97.5th percentile of the standard normal, for the 95 % Wald intervals of D-093.
_Z = NormalDist().inv_cdf(0.975)


class VisitCuts(NamedTuple):
    """The cut points of measures (a) and (d), from NOM-007-SSA2-2016 §5.2.1.15 (D-088)."""

    #: The minimum of five visits the norm asks for (``minimum_visits``).
    minimum: int
    #: The eight visits of its full calendar, which are also the reference of (a) per count.
    calendar: int

    @classmethod
    def from_schedule(cls, schedule: Mapping[str, Any]) -> "VisitCuts":
        """The cut points of ``config/nom007_schedule.yml``."""
        return cls(minimum=int(schedule["minimum_visits"]), calendar=len(schedule["visits"]))


class LevelCount(NamedTuple):
    """The births of one level of a measure, and the preterm ones among them: whole counts, or
    means for an exact expectation (:func:`~sinac_truncation.simulation.expected`)."""

    births: float
    preterm: float


class Crude(NamedTuple):
    """The crude comparison of one level with the reference; ``None`` where it does not exist."""

    #: ``None`` when one of the four cells is empty: the level or the reference has no birth, or
    #: no preterm or no term birth.
    odds_ratio: float | None
    lower: float | None
    upper: float | None
    #: The preterm share of the level minus that of the reference; ``None`` when either has no
    #: birth.
    risk_difference: float | None


class Share(NamedTuple):
    """One row of ``truncation_share.csv``, for one level of one measure and one scenario."""

    level: str
    observed: Crude
    simulated: Crude
    #: Simulated over observed risk difference (D-112); ``None`` when not reported.
    share: float | None


def visits_level(visits: int, cuts: VisitCuts) -> str:
    """The level of measure (a) for a count of visits: no care; below the minimum; below the
    calendar; the full calendar. The labels are those of ``sql/cohorts/exposure.sql``."""
    if visits < 0:
        raise ValueError(f"{visits} visits is not a count")
    if visits == 0:
        return "0"
    if visits < cuts.minimum:
        return f"1-{cuts.minimum - 1}"
    if visits < cuts.calendar:
        return f"{cuts.minimum}-{cuts.calendar - 1}"
    return f"{cuts.calendar}+"


@cache
def _apncu_level(visits: int, trimester: int, weeks: int) -> str:
    """Measure (b) of one combination, computed once (D-110)."""
    return compute_apncu(visits, trimester, weeks).level.value


def measure_level(measure: str, combination: Combination, cuts: VisitCuts) -> str:
    """The level of one combination in one measure. The crude comparison here and the models of
    :mod:`sinac_truncation.models` both read the levels from it, so they cannot differ."""
    if measure in ("a", "d"):
        return visits_level(combination.visits, cuts)
    if measure == "a_count":
        return str(combination.visits)
    if measure == "b":
        return _apncu_level(combination.visits, combination.trimester, combination.weeks)
    if measure == "c":
        return FIRST_TRIMESTER if combination.trimester == 1 else LATER_OR_NO_CARE
    raise ValueError(f"unknown measure {measure!r}; the measures are {', '.join(MEASURES)}")


def level_counts(
    combinations: Iterable[Combination],
    measure: str,
    cuts: VisitCuts,
    *,
    preterm_weeks: int = PRETERM_WEEKS,
) -> dict[str, LevelCount]:
    """The births and the preterm births of each level of a measure.

    Measure (d) is measure (a) on a landmark cohort, so it takes the combinations of that cohort:
    those of the definition in the database, or :func:`reached` on simulated ones.
    """
    births: dict[str, float] = {}
    preterm: dict[str, float] = {}
    for combination in combinations:
        level = measure_level(measure, combination, cuts)
        births[level] = births.get(level, 0) + combination.births
        if combination.weeks < preterm_weeks:
            preterm[level] = preterm.get(level, 0) + combination.births
    return {level: LevelCount(births[level], preterm.get(level, 0)) for level in births}


def reference_level(measure: str, cuts: VisitCuts) -> str:
    """The reference of each measure, care that meets the norm (docs/protocol.md §The measures)."""
    if measure in ("a", "d"):
        return visits_level(cuts.calendar, cuts)
    if measure == "a_count":
        return str(cuts.calendar)
    if measure == "b":
        return ApncuLevel.ADEQUATE.value
    if measure == "c":
        return FIRST_TRIMESTER
    raise ValueError(f"unknown measure {measure!r}; the measures are {', '.join(MEASURES)}")


def ordered_levels(measure: str, levels: Iterable[str], cuts: VisitCuts) -> list[str]:
    """The levels in the order of docs/protocol.md §The measures, for reports and tables."""
    if measure in ("a", "d"):
        order = [visits_level(visits, cuts) for visits in (0, 1, cuts.minimum, cuts.calendar)]
    elif measure == "b":
        order = [level.value for level in ApncuLevel]
    elif measure == "c":
        order = [FIRST_TRIMESTER, LATER_OR_NO_CARE]
    else:
        return sorted(set(levels), key=int)
    return [level for level in order if level in set(levels)]


def reached(combinations: Iterable[Combination], week: int) -> list[Combination]:
    """The combinations of the pregnancies that reached ``week``: step 10 of the landmark cohorts,
    ``EDADGESTACIONAL`` ≥ the week (D-090, D-111)."""
    return [combination for combination in combinations if combination.weeks >= week]


def crude(level: LevelCount | None, reference: LevelCount | None) -> Crude:
    """The crude odds ratio of a level against the reference, its 95 % Wald interval, and the
    risk difference. A level absent from the table is ``None`` and has no estimate."""
    if level is None or reference is None or level.births == 0 or reference.births == 0:
        return Crude(None, None, None, None)
    risk_difference = level.preterm / level.births - reference.preterm / reference.births
    cells = (
        level.preterm,
        level.births - level.preterm,
        reference.preterm,
        reference.births - reference.preterm,
    )
    if min(cells) == 0:
        return Crude(None, None, None, risk_difference)
    exposed_preterm, exposed_term, reference_preterm, reference_term = cells
    log_odds_ratio = log(exposed_preterm / exposed_term) - log(reference_preterm / reference_term)
    margin = _Z * sqrt(sum(1 / cell for cell in cells))
    return Crude(
        odds_ratio=exp(log_odds_ratio),
        lower=exp(log_odds_ratio - margin),
        upper=exp(log_odds_ratio + margin),
        risk_difference=risk_difference,
    )


def excludes_one(estimate: Crude) -> bool:
    """Whether the interval of an odds ratio exists and excludes 1. The share is reported only
    where the observed one does (docs/protocol.md §What truncation alone explains), and the
    simulated odds ratio of (c) must not (§What it computes)."""
    if estimate.lower is None or estimate.upper is None:
        return False
    return estimate.lower > 1 or estimate.upper < 1


def truncation_shares(
    observed: Mapping[str, LevelCount],
    simulated: Mapping[str, LevelCount],
    reference: str,
    levels: Sequence[str],
) -> list[Share]:
    """What truncation alone produces of the observed association, level by level (D-112).

    The share is the simulated risk difference over the observed one: 1 means that truncation
    alone reproduces the observed difference in preterm births, 0 that it produces none, and more
    than 1 that it produces more. It is reported only where the observed interval excludes 1 and
    the simulated difference exists. The odds ratios are kept beside it: the simulated one is
    ``None`` where the simulated world leaves a cell empty, as the calendar does for the
    reference of (a), (b) and (d).

    Args:
        observed: :func:`level_counts` of the observed definition.
        simulated: :func:`level_counts` of the same measure in one scenario.
        reference: :func:`reference_level`.
        levels: the levels to report, the reference excluded, in order.
    """
    rows = []
    for level in levels:
        seen = crude(observed.get(level), observed.get(reference))
        model = crude(simulated.get(level), simulated.get(reference))
        share = None
        if excludes_one(seen) and seen.risk_difference and model.risk_difference is not None:
            share = model.risk_difference / seen.risk_difference
        rows.append(Share(level=level, observed=seen, simulated=model, share=share))
    return rows


class ShareRow(NamedTuple):
    """A :class:`Share` with the definition, measure, variant and scenario it belongs to."""

    definition: int
    measure: str
    #: :data:`APNCU_VARIANT` for (b), empty for the other measures.
    variant: str
    scenario: str
    reference: str
    share: Share


def _compared(
    definition: int,
    measure: str,
    scenario: str,
    observed: Sequence[Combination],
    simulated: Sequence[Combination],
    cuts: VisitCuts,
) -> list[ShareRow]:
    seen = level_counts(observed, measure, cuts)
    model = level_counts(simulated, measure, cuts)
    reference = reference_level(measure, cuts)
    levels = ordered_levels(measure, (set(seen) | set(model)) - {reference}, cuts)
    variant = APNCU_VARIANT if measure == "b" else ""
    return [
        ShareRow(definition, measure, variant, scenario, reference, share)
        for share in truncation_shares(seen, model, reference, levels)
    ]


def compare(
    observed: Mapping[int, Sequence[Combination]],
    simulated: Mapping[str, Sequence[Combination]],
    cuts: VisitCuts,
    *,
    analysis_definition: int,
    landmarks: Mapping[int, int],
) -> list[ShareRow]:
    """Every row of ``truncation_share.csv`` (docs/protocol.md §Output tables).

    Measures (a), (a) per count, (b) and (c) compare the analysis cohort with each scenario.
    Measure (d) compares each landmark cohort with the pregnancies of the scenario that reached
    its week, the filter that builds the landmark cohort from the analysis cohort.

    Args:
        observed: the combinations of each definition, from the database.
        simulated: the combinations of each scenario, from :func:`~sinac_truncation.simulation.
            simulate` on the analysis cohort.
        cuts: :meth:`VisitCuts.from_schedule`.
        analysis_definition: the definition the scenarios were simulated from.
        landmarks: the week of each landmark definition
            (:data:`~sinac_truncation.cohorts.LANDMARK_WEEKS`).
    """
    rows: list[ShareRow] = []
    for scenario, pregnancies in simulated.items():
        for measure in ("a", "a_count", "b", "c"):
            rows += _compared(
                analysis_definition,
                measure,
                scenario,
                observed[analysis_definition],
                pregnancies,
                cuts,
            )
        for definition, week in landmarks.items():
            rows += _compared(
                definition, "d", scenario, observed[definition], reached(pregnancies, week), cuts
            )
    return rows


def largest_share_difference(
    rows: Sequence[ShareRow], exact: Sequence[ShareRow]
) -> dict[str, float | None]:
    """Per scenario, the largest relative difference between a simulated share and the share of
    the exact expectation for the same definition, measure, variant and level (D-115).

    It is the noise the draws add to the shares. ``None`` for a scenario with no share reported
    in both.
    """

    def key(row: ShareRow) -> tuple[int, str, str, str, str]:
        return (row.definition, row.measure, row.variant, row.share.level, row.scenario)

    reference = {key(row): row.share.share for row in exact}
    largest: dict[str, float | None] = {}
    for row in rows:
        largest.setdefault(row.scenario, None)
        simulated, computed = row.share.share, reference.get(key(row))
        if simulated is None or not computed:
            continue
        difference = abs(simulated - computed) / abs(computed)
        current = largest[row.scenario]
        largest[row.scenario] = difference if current is None else max(current, difference)
    return largest


def _number(value: float | None, digits: int) -> str:
    return "" if value is None else f"{value:.{digits}f}"


def format_shares(rows: Sequence[ShareRow]) -> list[str]:
    """The lines of the report that ``pipeline.py simulate`` prints: one per row, the risk
    differences in percentage points."""
    lines = [
        f"{'def':<4}{'measure':<9}{'level':<21}{'scenario':<9}{'OR obs':>8}{'OR sim':>8}"
        f"{'RD obs pp':>11}{'RD sim pp':>11}{'share':>8}"
    ]
    for row in rows:
        share = row.share
        observed_rd = share.observed.risk_difference
        simulated_rd = share.simulated.risk_difference
        lines.append(
            f"{row.definition:<4}{row.measure:<9}{share.level:<21}{row.scenario:<9}"
            f"{_number(share.observed.odds_ratio, 2):>8}"
            f"{_number(share.simulated.odds_ratio, 2):>8}"
            f"{_number(None if observed_rd is None else 100 * observed_rd, 2):>11}"
            f"{_number(None if simulated_rd is None else 100 * simulated_rd, 2):>11}"
            f"{_number(share.share, 1):>8}"
        )
    return lines
