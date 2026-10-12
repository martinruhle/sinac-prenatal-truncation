"""Tests for measure (b), the APNCU index of Kotelchuck's SAS program (D-091, D-092)."""

import pytest

from sinac_truncation.apncu import (
    MIDDLE_MONTH_RULE,
    ApncuInputError,
    ApncuLevel,
    compute_apncu,
)

#: The first month of each trimester. Not a rule of the study (D-005): it is the rule that turns
#: trimester 2 into month 4, the start month of the article's worked example.
FIRST_MONTH_RULE: tuple[int, int, int] = (1, 4, 7)


@pytest.mark.parametrize(
    ("visits", "trimester", "weeks", "month_rule", "recommended", "expected", "ratio", "level"),
    [
        # SAS
        pytest.param(4, 1, 37, MIDDLE_MONTH_RULE, 11, 10, 40.0, ApncuLevel.INADEQUATE,
                     id="37w-t1-4-below-50pct"),
        # SAS
        pytest.param(5, 1, 37, MIDDLE_MONTH_RULE, 11, 10, 50.0, ApncuLevel.INTERMEDIATE,
                     id="37w-t1-5-exactly-50pct"),
        # SAS
        pytest.param(8, 1, 37, MIDDLE_MONTH_RULE, 11, 10, 80.0, ApncuLevel.ADEQUATE,
                     id="37w-t1-8-exactly-80pct"),
        # SAS
        pytest.param(11, 1, 37, MIDDLE_MONTH_RULE, 11, 10, 110.0, ApncuLevel.ADEQUATE_PLUS,
                     id="37w-t1-11-exactly-110pct"),
        # SAS
        pytest.param(20, 2, 39, MIDDLE_MONTH_RULE, 13, 8, 250.0, ApncuLevel.INADEQUATE,
                     id="39w-t2-20-start-after-month-4"),
        # SAS + D-092
        pytest.param(1, 3, 28, MIDDLE_MONTH_RULE, 6, 1, 100.0, ApncuLevel.INADEQUATE,
                     id="28w-t3-1-floor-of-one-no-month-check"),
        # SAS
        pytest.param(0, 0, 39, MIDDLE_MONTH_RULE, 13, 13, 0.0, ApncuLevel.INADEQUATE,
                     id="39w-t0-0-no-care"),
        # SAS
        pytest.param(3, 1, 22, MIDDLE_MONTH_RULE, 5, 4, 75.0, ApncuLevel.INTERMEDIATE,
                     id="22w-t1-3-lowest-week-of-the-cohort"),
        # SAS
        pytest.param(8, 1, 45, MIDDLE_MONTH_RULE, 19, 18, 44.44, ApncuLevel.INADEQUATE,
                     id="45w-t1-8-highest-week-of-the-data"),
        # SAS
        pytest.param(10, 1, 34, MIDDLE_MONTH_RULE, 9, 8, 125.0, ApncuLevel.ADEQUATE_PLUS,
                     id="34w-t1-10-week-34"),
        # Article + SAS
        pytest.param(11, 2, 40, FIRST_MONTH_RULE, 14, 11, 100.0, ApncuLevel.ADEQUATE,
                     id="40w-t2-11-article-example"),
    ],
)  # fmt: skip
def test_the_reference_table(
    visits: int,
    trimester: int,
    weeks: int,
    month_rule: tuple[int, int, int],
    recommended: int,
    expected: int,
    ratio: float,
    level: ApncuLevel,
) -> None:
    """Eleven records worked out by hand, one step of the algorithm per column.

    Columns: the visits declared, the trimester of the first visit (0 is "NO RECIBIÓ") and the
    completed weeks at delivery; then the ACOG visits for those weeks (step 1), the visits expected
    after the start month (step 2), observed over expected in percent (step 3), and the summary
    index (step 4). The ratio is rounded to two decimals.

    Sources, as named in the comment above each row:

    - SAS: Kotelchuck M. Adequacy of Prenatal Care Utilization Index: SAS computational program,
      version 3, September 1994, parts 5 to 7 (pages 6 to 8 of the PDF).
      <https://www.mchlibrary.org/databases/HSNRCPDFs/APNCU994_20SAS.pdf>
    - D-092 (docs/decisions.md): the trimester takes its middle month, and the program's part 3a
      check of the start month against the weeks is not applied. The program would set month 8 to
      missing at 28 weeks; here the record keeps its index.
    - Article: Kotelchuck M. Am J Public Health 1994;84(9):1414-1420, page 1417. Its worked
      example is a 40-week pregnancy whose care began in month 4: 14 visits recommended, 11
      expected. The program gives the visits and the level of the row.

    Rows 1 to 4 sit at 37 weeks, where the three cut points fall on whole visits.
    """
    result = compute_apncu(visits, trimester, weeks, month_rule=month_rule)
    assert result.recommended_visits == recommended
    assert result.expected_visits == expected
    assert result.ratio_percent == pytest.approx(ratio, abs=0.01)
    assert result.level is level


@pytest.mark.parametrize(
    ("weeks", "recommended"),
    [
        (18, 4), (21, 4), (22, 5), (25, 5), (26, 6), (29, 6), (30, 7), (31, 7),
        (32, 8), (33, 8), (34, 9), (35, 9), (36, 10), (40, 14), (50, 24),
    ],
)  # fmt: skip
def test_recommended_visits_follow_the_acog_table(weeks: int, recommended: int) -> None:
    """Each bound of the first step of SAS part 6, from 18 weeks, the lowest the program accepts.

    Without care the start month is 0, so nothing is deducted and expected equals recommended.
    """
    result = compute_apncu(0, 0, weeks)
    assert result.recommended_visits == recommended
    assert result.expected_visits == recommended


@pytest.mark.parametrize(
    ("month", "expected", "initiation"),
    [
        (1, 14, ApncuLevel.ADEQUATE_PLUS),
        (2, 13, ApncuLevel.ADEQUATE_PLUS),
        (3, 12, ApncuLevel.ADEQUATE),
        (4, 11, ApncuLevel.ADEQUATE),
        (5, 9, ApncuLevel.INTERMEDIATE),
        (6, 8, ApncuLevel.INTERMEDIATE),
        (7, 7, ApncuLevel.INADEQUATE),
        (8, 5, ApncuLevel.INADEQUATE),
        (9, 1, ApncuLevel.INADEQUATE),
    ],
)
def test_the_start_month_sets_missed_visits_and_initiation(
    month: int, expected: int, initiation: ApncuLevel
) -> None:
    """At 40 weeks (14 visits recommended), SAS part 6 deducts 0, 1, 2, 3, 5, 6, 7, 9 and 13
    visits for months 1 to 9, and SAS part 5 rates months 1-2, 3-4, 5-6 and later.

    Each month is reached through a rule that places it in its own trimester.
    """
    trimester = (month - 1) // 3 + 1
    rule = list(FIRST_MONTH_RULE)
    rule[trimester - 1] = month
    result = compute_apncu(1, trimester, 40, month_rule=(rule[0], rule[1], rule[2]))
    assert result.start_month == month
    assert result.expected_visits == expected
    assert result.initiation is initiation


def test_the_default_rule_is_the_middle_month() -> None:
    # D-092, FOR APPROVAL. A change here is a change of protocol and needs a decision entry first.
    assert MIDDLE_MONTH_RULE == (2, 5, 8)
    assert [compute_apncu(1, trimester, 40).start_month for trimester in (1, 2, 3)] == [2, 5, 8]
    assert compute_apncu(0, 0, 40).start_month == 0


def test_no_care_rates_every_dimension_inadequate() -> None:
    # SAS part 5 rates month 0 Inadequate, and 0 visits give a ratio of 0.
    result = compute_apncu(0, 0, 40)
    assert result.initiation is ApncuLevel.INADEQUATE
    assert result.received_services is ApncuLevel.INADEQUATE
    assert result.level is ApncuLevel.INADEQUATE


def test_a_late_start_overrides_received_services() -> None:
    # SAS part 7: initiation Intermediate or Inadequate makes the index Inadequate.
    result = compute_apncu(20, 2, 39)
    assert result.received_services is ApncuLevel.ADEQUATE_PLUS
    assert result.level is ApncuLevel.INADEQUATE


@pytest.mark.parametrize(
    ("visits", "trimester", "weeks"),
    [
        (-1, 1, 39),  # SAS part 3a: a count below 0
        (91, 1, 39),  # SAS part 3a: a count above 90; SINAC writes 99 for an unknown count
        (5, 8, 39),  # rule 1 of the common set: trimester 8 is "NO ESPECIFICADO"
        (5, 9, 39),  # rule 1 of the common set: trimester 9 is "SE IGNORA"
        (5, 1, 17),  # SAS part 3a: below 18 weeks
        (5, 1, 51),  # SAS part 3a: above 50 weeks
        (3, 0, 39),  # rule 3 of the common set: "NO RECIBIÓ" with visits
        (0, 2, 39),  # rule 3 of the common set: a first-visit trimester with no visits
        (2, 3, 27),  # rule 4 of the common set (D-092): a third-trimester start before 28 weeks
    ],
)
def test_records_the_common_set_removes_are_refused(
    visits: int, trimester: int, weeks: int
) -> None:
    """The step "prenatal care data known and coherent" removes these records before any index
    is computed (protocol §One set of records for the four measures), so reaching the function
    with one means a fault upstream.
    """
    with pytest.raises(ApncuInputError):
        compute_apncu(visits, trimester, weeks)


@pytest.mark.parametrize(
    "rule",
    [
        (1, 2, 3),  # months of the first trimester only
        (0, 5, 8),  # month 0 is no care, not a start month
        (2, 5, 10),  # month 10 is past the third trimester
    ],
)
def test_a_month_rule_outside_its_trimesters_is_refused(rule: tuple[int, int, int]) -> None:
    with pytest.raises(ApncuInputError, match="trimester"):
        compute_apncu(1, 1, 40, month_rule=rule)
