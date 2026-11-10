"""Tests for measure (b), the APNCU index of Kotelchuck's SAS program (D-091, D-092).

Two reference tables: the ACOG schedule of the program, the calendar of the main analysis, and
the NOM-007 calendar of the variant, whose two rules are the author's criteria (D-128, D-129).
"""

import pytest

from sinac_truncation.apncu import (
    ACOG_MIDPOINT,
    FIRST_MONTH_RULE,
    LAST_MONTH_RULE,
    MIDDLE_MONTH_RULE,
    ApncuInputError,
    ApncuLevel,
    apncu_variants,
    compute_apncu,
)

#: The first week of each visit of NOM-007-SSA2-2016 §5.2.1.15, as `config/nom007_schedule.yml`
#: copies them. A range of weeks is read by its first week (D-128), so these are the weeks the
#: variant reads; `tests/test_nom007_schedule.py` ties this tuple to the file.
NOM007_CALENDAR: tuple[int, ...] = (6, 10, 16, 22, 28, 32, 36, 38)


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
        # Article + SAS. FIRST_MONTH_RULE is the rule that turns trimester 2 into month 4, the
        # start month of the article's worked example; it is also one side of the axis of D-127.
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
    # D-092. A change here is a change of protocol and needs a decision entry first.
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


@pytest.mark.parametrize(
    ("visits", "trimester", "weeks", "recommended", "expected", "ratio", "level"),
    [
        # Worked row, worked out in this docstring.
        pytest.param(8, 1, 40, 8, 8, 100.0, ApncuLevel.ADEQUATE,
                     id="nom-40w-t1-8-the-full-calendar-at-term"),
        # Trace: the seventh visit is the last one a birth at 37 weeks reached (week 36), and
        # month 2 deducts nothing, so eight visits are more than expected.
        pytest.param(8, 1, 37, 7, 7, 114.29, ApncuLevel.ADEQUATE_PLUS,
                     id="nom-37w-t1-8-above-the-seven-visits-reached"),
        # Blind row (D-128): the eighth visit, between 38 and 41 weeks, enters at 38.
        pytest.param(8, 1, 38, 8, 8, 100.0, ApncuLevel.ADEQUATE,
                     id="nom-38w-t1-8-the-eighth-visit-enters"),
        # Trace: month 5 deducts the visits of weeks 6 and 10, so six visits meet the six
        # expected; care began after month 4, which SAS part 7 rates Inadequate whatever the
        # ratio.
        pytest.param(6, 2, 40, 8, 6, 100.0, ApncuLevel.INADEQUATE,
                     id="nom-40w-t2-6-start-after-month-4"),
        # Blind row (D-129): the visits a second-trimester start misses, on a preterm birth.
        pytest.param(5, 2, 32, 6, 4, 125.0, ApncuLevel.INADEQUATE,
                     id="nom-32w-t2-5-missed-visits-of-a-later-start"),
        # Trace: at 28 weeks the calendar reached five visits and month 8 deducts four, which is
        # the floor of one of SAS part 6 reached exactly.
        pytest.param(1, 3, 28, 5, 1, 100.0, ApncuLevel.INADEQUATE,
                     id="nom-28w-t3-1-floor-of-one"),
        # Trace: no care deducts nothing (month 0) and gives a ratio of 0.
        pytest.param(0, 0, 39, 8, 8, 0.0, ApncuLevel.INADEQUATE,
                     id="nom-39w-t0-0-no-care"),
        # Trace: the lowest week of the cohort reached the four visits of weeks 6 to 22.
        pytest.param(4, 1, 22, 4, 4, 100.0, ApncuLevel.ADEQUATE,
                     id="nom-22w-t1-4-lowest-week-of-the-cohort"),
        # Trace: the calendar ends at eight visits, so a higher count raises the ratio alone.
        pytest.param(20, 1, 39, 8, 8, 250.0, ApncuLevel.ADEQUATE_PLUS,
                     id="nom-39w-t1-20-above-the-calendar"),
        # Trace: the calendar has no visit after week 38, so 45 weeks expects the same eight.
        # On the ACOG schedule the same record is Inadequate (19 recommended, 44.44 %).
        pytest.param(8, 1, 45, 8, 8, 100.0, ApncuLevel.ADEQUATE,
                     id="nom-45w-t1-8-highest-week-of-the-data"),
        # Trace: at 34 weeks the calendar reached six visits (weeks 6 to 32).
        pytest.param(6, 1, 34, 6, 6, 100.0, ApncuLevel.ADEQUATE,
                     id="nom-34w-t1-6-week-34"),
    ],
)  # fmt: skip
def test_the_nom007_reference_table(
    visits: int,
    trimester: int,
    weeks: int,
    recommended: int,
    expected: int,
    ratio: float,
    level: ApncuLevel,
) -> None:
    """Eleven records of the NOM-007 variant, one step of the algorithm per column.

    The columns are those of the ACOG table above, with the expected visits taken from
    :data:`NOM007_CALENDAR` instead of the program's table. The variant is ``nom007_midpoint``,
    so the month rule is the middle month of D-092 (D-130).

    The recipe. Every row follows from the calendar and the two rules of docs/protocol.md
    §APNCU:

    1. **Recommended** (D-128): the visits of the calendar whose first week the pregnancy
       reached, that is how many of 6, 10, 16, 22, 28, 32, 36 and 38 are at most the weeks at
       delivery.
    2. **Expected** (D-129): recommended minus the visits that fall before the month care began,
       a month being four completed weeks. The middle months 2, 5 and 8 begin at weeks 4, 16 and
       28, so they deduct 0, 2 and 4 visits; no care deducts nothing. The floor is one visit.
    3. **Ratio**: observed over expected, in percent, rounded here to two decimals.
    4. **Level**: SAS parts 5 to 7, which the calendar does not change. Care begun after month 4
       is Inadequate whatever the ratio, so every second and third trimester start is Inadequate.

    The worked row, 8 visits, first trimester, 40 weeks. The pregnancy reached all eight visits
    of the calendar (38 <= 40), so eight are recommended. The middle month of the first trimester
    is month 2, which begins at week 4 (4 x (2 - 1)); no visit of the calendar falls before week
    4, so nothing is deducted and eight are expected. The ratio is 8 / 8 = 100 %, which SAS part
    6 rates Adequate (above 79.99 and not above 109.99). Month 2 is Adequate Plus initiation, so
    part 7 keeps the level of received services: Adequate. The same record on the ACOG schedule
    is Intermediate: 14 recommended, 13 expected after month 2, a ratio of 61.54 %.

    Two rows are blind, one for each rule: ``nom-38w-t1-8-the-eighth-visit-enters`` for D-128 and
    ``nom-32w-t2-5-missed-visits-of-a-later-start`` for D-129. The rest carry the trace above each
    row.

    The author's blind computation agreed on what each of the two rows tests, the eighth visit
    entering at 38 weeks and the two visits a month 5 start misses, and differed twice after
    that. The trace settled both and the table stands (issue #66):

    - It deducted one visit for month 2, the deduction of the ACOG table. On this calendar month
      2 deducts nothing: the first visit of NOM-007 falls between weeks 6 and 8, inside month 2,
      so a start there misses no visit. That the ACOG table does not carry over is why D-129
      exists.
    - It read a ratio of 125 % at a month 5 start as Adequate Plus, which is the level of
      received services. The summary index of SAS part 7 is Inadequate whenever care began after
      month 4, whatever the ratio.
    """
    result = compute_apncu(
        visits, trimester, weeks, month_rule=MIDDLE_MONTH_RULE, calendar=NOM007_CALENDAR
    )
    assert result.recommended_visits == recommended
    assert result.expected_visits == expected
    assert result.ratio_percent == pytest.approx(ratio, abs=0.01)
    assert result.level is level


@pytest.mark.parametrize(
    ("weeks", "recommended"),
    [
        (18, 3), (21, 3), (22, 4), (27, 4), (28, 5), (31, 5), (32, 6), (35, 6),
        (36, 7), (37, 7), (38, 8), (41, 8), (50, 8),
    ],
)  # fmt: skip
def test_recommended_visits_follow_the_nom007_calendar(weeks: int, recommended: int) -> None:
    """Each bound of the calendar read by the first week of every visit (D-128).

    The eighth visit enters at 38 weeks, the first week of its range of 38 to 41, and the
    calendar asks for nothing after it: a post-term birth expects the same eight visits.
    """
    result = compute_apncu(0, 0, weeks, calendar=NOM007_CALENDAR)
    assert result.recommended_visits == recommended
    assert result.expected_visits == recommended


@pytest.mark.parametrize(
    ("month", "expected"),
    [(1, 8), (2, 8), (3, 7), (4, 6), (5, 6), (6, 5), (7, 4), (8, 4), (9, 3)],
)
def test_the_start_month_deducts_the_calendar_visits_before_it(month: int, expected: int) -> None:
    """At 40 weeks the calendar recommends eight visits, and a start in month m deducts those
    before week 4 (m - 1): 0, 0, 1, 2, 2, 3, 4, 4 and 5 visits for months 1 to 9 (D-129).

    Each month is reached through a rule that places it in its own trimester, as the ACOG test
    above does.
    """
    trimester = (month - 1) // 3 + 1
    rule = list(FIRST_MONTH_RULE)
    rule[trimester - 1] = month
    result = compute_apncu(
        1, trimester, 40, month_rule=(rule[0], rule[1], rule[2]), calendar=NOM007_CALENDAR
    )
    assert result.start_month == month
    assert result.expected_visits == expected


def test_the_middle_month_deducts_what_the_trimester_boundaries_would() -> None:
    """The rejected alternative of D-129 deducts the visits before the first week of the
    trimester: before weeks 0, 14 and 28 of D-092, that is 0, 2 and 4 visits.

    Those are the three counts the middle month gives, so the variant of the main analysis does
    not depend on which of the two rules was chosen. The axis of D-127 does: the last month of
    each trimester deducts 1, 3 and 5 instead.
    """
    boundaries = [sum(1 for week in NOM007_CALENDAR if week < start) for start in (0, 14, 28)]
    middle = [
        compute_apncu(1, trimester, 40, calendar=NOM007_CALENDAR).expected_visits
        for trimester in (1, 2, 3)
    ]
    assert boundaries == [0, 2, 4]
    assert middle == [8 - 0, 8 - 2, 8 - 4]


def test_the_four_variants_are_the_two_calendars_and_the_month_rules() -> None:
    """D-130: the month rule varies on the ACOG schedule alone, and the NOM-007 variant keeps
    the middle month. The names are the values of the column variant of D-098.
    """
    variants = apncu_variants(NOM007_CALENDAR)
    assert [variant.name for variant in variants] == [
        "acog_midpoint",
        "acog_first",
        "acog_last",
        "nom007_midpoint",
    ]
    assert variants[0] == ACOG_MIDPOINT
    assert [variant.calendar for variant in variants] == [None, None, None, NOM007_CALENDAR]
    assert [variant.month_rule for variant in variants] == [
        MIDDLE_MONTH_RULE,
        FIRST_MONTH_RULE,
        LAST_MONTH_RULE,
        MIDDLE_MONTH_RULE,
    ]


@pytest.mark.parametrize("calendar", [(), (6, 10, 10), (10, 6)])
def test_a_calendar_without_rising_weeks_is_refused(calendar: tuple[int, ...]) -> None:
    with pytest.raises(ApncuInputError, match="calendar"):
        compute_apncu(1, 1, 40, calendar=calendar)
