"""Measure (b): the Adequacy of Prenatal Care Utilization index, approximated from SINAC.

The algorithm is that of Kotelchuck's APNCU SAS computational program, version 3 (September 1994):
the range edits of part 3a and parts 5 to 7 (docs/protocol.md §APNCU, D-091). Two changes fit it
to SINAC (D-092):

- SINAC records the trimester of the first visit, not the month, so a rule turns the trimester
  into a month. The study uses one rule, the middle month (D-005).
- Part 3a sets a start month above weeks ÷ 4 to missing. That check is not applied: the analysis
  cohort checks the trimester instead (rule 4 of the common set), which this module also refuses.

APNCU is derived from gestational age, so it is an exposure and never a predictor of a model
(CLAUDE.md rule 3). There is no I/O here (rule 6): records reach the index as combinations of
count, trimester and weeks (D-110).
"""

from collections.abc import Mapping
from enum import StrEnum
from typing import NamedTuple

__all__ = ["MIDDLE_MONTH_RULE", "ApncuInputError", "ApncuLevel", "ApncuResult", "compute_apncu"]

#: The month that trimesters 1, 2 and 3 of the first visit become: the middle month (D-092).
#: Trimester 0, "NO RECIBIÓ", becomes month 0, the program's code for no care.
MIDDLE_MONTH_RULE: tuple[int, int, int] = (2, 5, 8)

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


def _check(visits: int, trimester: int, weeks: int, month_rule: tuple[int, int, int]) -> None:
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
) -> ApncuResult:
    """Compute the APNCU index of one record, with the steps that lead to it.

    Args:
        visits: total prenatal visits declared (``TOTALCONSULTAS``), a count from 0 to 90.
        trimester: trimester of the first visit (``TRIMESTREPRIMERCONSULTA``): 0 "NO RECIBIÓ",
            1, 2 or 3.
        weeks: completed weeks of gestation at delivery (``EDADGESTACIONAL``), 18 to 50.
        month_rule: the month, from 1 to 9, that trimesters 1, 2 and 3 become, each inside its
            own trimester. Only the default is used by the study (D-005).

    Raises:
        ApncuInputError: a value outside the ranges above; a count and a trimester that disagree
            on whether care was received (rule 3 of the common set); a third-trimester start
            before 28 weeks (rule 4); a month rule that leaves a trimester.
    """
    _check(visits, trimester, weeks, month_rule)
    start_month = 0 if trimester == 0 else month_rule[trimester - 1]
    recommended = _recommended_visits(weeks)
    # SAS part 6: an expected count of 0 or less becomes 1.
    expected = max(recommended - _MISSED_VISITS[start_month], 1)
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
