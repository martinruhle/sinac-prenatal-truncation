"""Measure (b): the Adequacy of Prenatal Care Utilization index, approximated from SINAC.

The algorithm is that of Kotelchuck's APNCU SAS computational program, version 3 (September 1994):
the range edits of part 3a and parts 5 to 7 (docs/protocol.md §APNCU, D-091). Two changes fit it
to SINAC (D-092):

- SINAC records the trimester of the first visit, not the month, so a rule turns the trimester
  into a month. The main analysis uses the middle month, and the other two months of each
  trimester are a sensitivity axis (D-127).
- Part 3a sets a start month above weeks ÷ 4 to missing. That check is not applied: the analysis
  cohort checks the trimester instead (rule 4 of the common set), which this module also refuses.

The index has four variants (:func:`apncu_variants`), each a row of the column variant of the
output tables: the ACOG schedule of the program with each of the three month rules, and the
NOM-007 calendar with the middle month. On another calendar the algorithm is the same and only
its first two steps read the calendar instead of the program's tables (:func:`_calendar_visits`,
:func:`_calendar_missed`), under the two rules of docs/protocol.md §APNCU (D-128, D-129).

APNCU is derived from gestational age, so it is an exposure and never a predictor of a model
(CLAUDE.md rule 3). There is no I/O here (rule 6): records reach the index as combinations of
count, trimester and weeks (D-110).
"""

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import NamedTuple

__all__ = [
    "ACOG_MIDPOINT",
    "FIRST_MONTH_RULE",
    "LAST_MONTH_RULE",
    "MIDDLE_MONTH_RULE",
    "ApncuInputError",
    "ApncuLevel",
    "ApncuResult",
    "ApncuVariant",
    "apncu_variants",
    "compute_apncu",
]

#: The month that trimesters 1, 2 and 3 of the first visit become: the middle month, the rule of
#: the main analysis (D-092). Trimester 0, "NO RECIBIÓ", becomes month 0, the program's code for
#: no care.
MIDDLE_MONTH_RULE: tuple[int, int, int] = (2, 5, 8)

#: The first month of each trimester, one side of the sensitivity axis of D-127. It is also the
#: rule that turns trimester 2 into month 4, the start month of the article's worked example.
FIRST_MONTH_RULE: tuple[int, int, int] = (1, 4, 7)

#: The last month of each trimester, the other side of that axis (D-127).
LAST_MONTH_RULE: tuple[int, int, int] = (3, 6, 9)

#: The completed weeks of a month, as part 3a of the program reads them: its check sets a start
#: month above weeks ÷ 4 to missing, so month m runs from week 4 (m - 1) to week 4 m. Only the
#: variants on another calendar use it (:func:`_calendar_missed`, D-129).
_WEEKS_IN_MONTH = 4

#: The range edits of SAS part 3a: 0 to 90 visits and 18 to 50 weeks.
_VISITS = range(0, 91)
_WEEKS = range(18, 51)

#: Rule 4 of the common set (D-092): a first visit in the third trimester needs 28
#: completed weeks or more at delivery. The step "prenatal care data known and coherent" of the
#: analysis cohort applies the same bound.
_THIRD_TRIMESTER_FIRST_WEEK = 28

#: Visits missed before the start month, SAS part 6 (second step). Month 0 is no care and
#: deducts nothing. The program also lists month 10, which no trimester becomes.
_MISSED_VISITS: Mapping[int, int] = {0: 0, 1: 0, 2: 1, 3: 2, 4: 3, 5: 5, 6: 6, 7: 7, 8: 9, 9: 13}


class ApncuInputError(ValueError):
    """A record, or a month rule, the index is not computed for."""


class ApncuLevel(StrEnum):
    """The four levels of each dimension and of the summary index (the program's codes 1 to 4)."""

    INADEQUATE = "Inadequate"
    INTERMEDIATE = "Intermediate"
    ADEQUATE = "Adequate"
    ADEQUATE_PLUS = "Adequate Plus"


class ApncuResult(NamedTuple):
    """The index and each step that leads to it; the program's variable name is in brackets."""

    #: The month care began, from the trimester through the month rule; 0 is no care (MPCBBC).
    start_month: int
    #: The ACOG visits for the completed weeks at delivery (UEXPVIS).
    recommended_visits: int
    #: The recommended visits minus those missed before the start month, at least 1 (EXPVIS).
    expected_visits: int
    #: Observed over expected visits, in percent (EVRATIO).
    ratio_percent: float
    #: Adequacy of initiation of prenatal care (MOINDEX4).
    initiation: ApncuLevel
    #: Adequacy of received prenatal care services (EVINDEX).
    received_services: ApncuLevel
    #: The two factor summary index: measure (b) (INDEXSUM).
    level: ApncuLevel


class ApncuVariant(NamedTuple):
    """One variant of measure (b): a calendar of expected visits and a month rule (D-130)."""

    #: The value of the column variant of the output tables (docs/protocol.md §Output tables).
    name: str
    #: The first week of each visit of the calendar, or ``None`` for the ACOG schedule, whose
    #: expected visits the program gives week by week (:func:`_recommended_visits`).
    calendar: tuple[int, ...] | None
    #: The month that trimesters 1, 2 and 3 become.
    month_rule: tuple[int, int, int]


#: Measure (b) of the main analysis: the ACOG schedule of the program with the middle month of
#: each trimester (D-091, D-092).
ACOG_MIDPOINT = ApncuVariant("acog_midpoint", None, MIDDLE_MONTH_RULE)


def apncu_variants(nom007_first_weeks: Sequence[int]) -> tuple[ApncuVariant, ...]:
    """The four variants of docs/protocol.md §APNCU, in the order of the output tables.

    The month rule varies on the ACOG schedule alone, the schedule of the main analysis the
    sensitivity of D-127 is about; the NOM-007 variant keeps the middle month (D-130).

    Args:
        nom007_first_weeks: the first week of each visit of the NOM-007 calendar, from
            :func:`~sinac_truncation.simulation.calendar_first_weeks`.
    """
    calendar = tuple(int(week) for week in nom007_first_weeks)
    return (
        ACOG_MIDPOINT,
        ApncuVariant("acog_first", None, FIRST_MONTH_RULE),
        ApncuVariant("acog_last", None, LAST_MONTH_RULE),
        ApncuVariant("nom007_midpoint", calendar, MIDDLE_MONTH_RULE),
    )


def _check(
    visits: int,
    trimester: int,
    weeks: int,
    month_rule: tuple[int, int, int],
    calendar: Sequence[int] | None,
) -> None:
    if len(month_rule) != 3 or any(
        not 3 * index + 1 <= month <= 3 * index + 3 for index, month in enumerate(month_rule)
    ):
        raise ApncuInputError(
            f"the month rule {month_rule} must turn each trimester into one of its own months "
            "(1-3, 4-6 and 7-9)"
        )
    if visits not in _VISITS:
        raise ApncuInputError(f"{visits} visits is outside 0 to 90 (SAS part 3a)")
    if weeks not in _WEEKS:
        raise ApncuInputError(f"{weeks} weeks is outside 18 to 50 (SAS part 3a)")
    if trimester not in (0, 1, 2, 3):
        raise ApncuInputError(f"first-visit trimester {trimester} is not 0, 1, 2 or 3 (rule 1)")
    if (trimester == 0) != (visits == 0):
        raise ApncuInputError(
            f"trimester {trimester} and {visits} visits disagree on whether care was received "
            "(rule 3)"
        )
    if trimester == 3 and weeks < _THIRD_TRIMESTER_FIRST_WEEK:
        raise ApncuInputError(
            f"a first visit in the third trimester is not possible at {weeks} weeks (rule 4)"
        )
    if calendar is not None and (
        not calendar
        or any(later <= earlier for earlier, later in zip(calendar, calendar[1:], strict=False))
    ):
        raise ApncuInputError(
            f"the calendar {tuple(calendar)} must hold at least one visit, in rising weeks"
        )


def _recommended_visits(weeks: int) -> int:
    """UEXPVIS, the first step of SAS part 6, for the 18 to 50 weeks that part 3a accepts."""
    if weeks >= 35:
        return (weeks - 35) + 9
    if weeks == 34:
        return 9
    if weeks >= 32:
        return 8
    if weeks >= 30:
        return 7
    if weeks >= 26:
        return 6
    if weeks >= 22:
        return 5
    return 4


def _calendar_visits(calendar: Sequence[int], weeks: int) -> int:
    """UEXPVIS on another calendar: its visits whose first week the pregnancy reached.

    A range of weeks is read by its first week, the reading D-096 already gives the same
    calendar in the null simulation (D-128, FOR APPROVAL). In the cohort, 22 completed weeks or
    more, that reading changes one visit of NOM-007: the eighth, between 38 and 41 weeks, which
    a birth at 38 weeks is expected to have had.
    """
    return sum(1 for week in calendar if week <= weeks)


def _calendar_missed(calendar: Sequence[int], start_month: int) -> int:
    """The second step of part 6 on another calendar: its visits that fall before the month care
    began, a month being :data:`_WEEKS_IN_MONTH` completed weeks (D-129, FOR APPROVAL).

    Month 0, no care, deducts nothing, as the program's table does. On NOM-007 the middle month
    of each trimester misses 0, 2 and 4 visits, which is also what the trimester boundaries of
    D-092 give; the first month of each trimester misses 0, 2 and 4, and the last 1, 3 and 5.
    """
    if start_month == 0:
        return 0
    start_week = _WEEKS_IN_MONTH * (start_month - 1)
    return sum(1 for week in calendar if week < start_week)


def _initiation(start_month: int) -> ApncuLevel:
    """MOINDEX4, SAS part 5. Month 0, no care, falls in the last branch with months 7 to 9."""
    if 1 <= start_month <= 2:
        return ApncuLevel.ADEQUATE_PLUS
    if 3 <= start_month <= 4:
        return ApncuLevel.ADEQUATE
    if 5 <= start_month <= 6:
        return ApncuLevel.INTERMEDIATE
    return ApncuLevel.INADEQUATE


def _received_services(ratio_percent: float) -> ApncuLevel:
    """EVINDEX, SAS part 6, with the cut points written as the program writes them.

    With whole visits and at most 24 expected, no ratio falls between 49.99 and 50, 79.99 and 80,
    or 109.99 and 110, so these are the 50, 80 and 110 % of the article.
    """
    if ratio_percent > 109.99:
        return ApncuLevel.ADEQUATE_PLUS
    if ratio_percent > 79.99:
        return ApncuLevel.ADEQUATE
    if ratio_percent > 49.99:
        return ApncuLevel.INTERMEDIATE
    return ApncuLevel.INADEQUATE


def _summary(initiation: ApncuLevel, received_services: ApncuLevel) -> ApncuLevel:
    """INDEXSUM, SAS part 7: Inadequate when care began after month 4 or received services are
    Inadequate; otherwise the level of received services, as the program's last three branches
    give it."""
    late_start = initiation in (ApncuLevel.INADEQUATE, ApncuLevel.INTERMEDIATE)
    if late_start or received_services is ApncuLevel.INADEQUATE:
        return ApncuLevel.INADEQUATE
    return received_services


def compute_apncu(
    visits: int,
    trimester: int,
    weeks: int,
    *,
    month_rule: tuple[int, int, int] = MIDDLE_MONTH_RULE,
    calendar: Sequence[int] | None = None,
) -> ApncuResult:
    """Compute the APNCU index of one record, with the steps that lead to it.

    Args:
        visits: total prenatal visits declared (``TOTALCONSULTAS``), a count from 0 to 90.
        trimester: trimester of the first visit (``TRIMESTREPRIMERCONSULTA``): 0 "NO RECIBIÓ",
            1, 2 or 3.
        weeks: completed weeks of gestation at delivery (``EDADGESTACIONAL``), 18 to 50.
        month_rule: the month, from 1 to 9, that trimesters 1, 2 and 3 become, each inside its
            own trimester. The main analysis uses :data:`MIDDLE_MONTH_RULE` and the sensitivity
            axis the other two (D-127).
        calendar: the first week of each visit of another calendar, which then gives the
            expected visits and the ones a later start misses (D-128, D-129). The default, the
            ACOG schedule of the program, is the calendar of the main analysis.

    Raises:
        ApncuInputError: a value outside the ranges above; a count and a trimester that disagree
            on whether care was received (rule 3 of the common set); a third-trimester start
            before 28 weeks (rule 4); a month rule that leaves a trimester; a calendar with no
            visit or with weeks that do not rise.
    """
    _check(visits, trimester, weeks, month_rule, calendar)
    start_month = 0 if trimester == 0 else month_rule[trimester - 1]
    if calendar is None:
        recommended = _recommended_visits(weeks)
        missed = _MISSED_VISITS[start_month]
    else:
        recommended = _calendar_visits(calendar, weeks)
        missed = _calendar_missed(calendar, start_month)
    # SAS part 6: an expected count of 0 or less becomes 1.
    expected = max(recommended - missed, 1)
    ratio_percent = visits / expected * 100
    initiation = _initiation(start_month)
    received_services = _received_services(ratio_percent)
    return ApncuResult(
        start_month=start_month,
        recommended_visits=recommended,
        expected_visits=expected,
        ratio_percent=ratio_percent,
        initiation=initiation,
        received_services=received_services,
        level=_summary(initiation, received_services),
    )
