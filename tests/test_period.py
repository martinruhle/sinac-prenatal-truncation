"""Tests for the study period and the parsing of ``--years``."""

import pytest

from sinac_truncation.period import STUDY_YEARS, PeriodError, format_years, parse_years


def test_the_study_period_is_2020_to_2023() -> None:
    # D-041. A change here is a change of study period and needs a decision entry first.
    assert STUDY_YEARS == (2020, 2021, 2022, 2023)


@pytest.mark.parametrize(
    ("text", "years"),
    [
        ("2023", (2023,)),
        ("2022,2023", (2022, 2023)),
        ("2020-2023", (2020, 2021, 2022, 2023)),
        ("2019,2021-2023", (2019, 2021, 2022, 2023)),
        (" 2023 , 2022 ", (2022, 2023)),
        ("2023,2020-2023,2021", (2020, 2021, 2022, 2023)),
        ("2023-2023", (2023,)),
    ],
)
def test_years_are_read_sorted_and_without_repeats(text: str, years: tuple[int, ...]) -> None:
    assert parse_years(text) == years


@pytest.mark.parametrize(
    "text",
    ["", "23", "20230", "2022,,2023", "2020-", "-2023", "2020..2023", "2020 2023", "٢٠٢٣"],
)
def test_anything_but_years_and_ranges_is_refused(text: str) -> None:
    with pytest.raises(PeriodError, match="not a year"):
        parse_years(text)


def test_a_range_that_runs_backwards_is_refused() -> None:
    with pytest.raises(PeriodError, match="runs backwards"):
        parse_years("2023-2020")


@pytest.mark.parametrize(
    ("years", "text"),
    [
        ((2020, 2021, 2022, 2023), "2020-2023"),
        ((2023,), "2023"),
        ((2022, 2023), "2022-2023"),
        ((2019, 2021, 2022), "2019,2021,2022"),
        ((2023, 2021, 2022, 2021), "2021-2023"),
    ],
)
def test_years_are_written_as_a_range_when_contiguous(years: tuple[int, ...], text: str) -> None:
    assert format_years(years) == text


@pytest.mark.parametrize("years", [STUDY_YEARS, (2023,), (2019, 2021, 2023)])
def test_what_is_written_reads_back_the_same(years: tuple[int, ...]) -> None:
    assert parse_years(format_years(years)) == years


def test_writing_no_years_is_refused() -> None:
    with pytest.raises(PeriodError):
        format_years(())
