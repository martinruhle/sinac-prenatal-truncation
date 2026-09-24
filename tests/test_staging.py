"""Tests for the pure staging helpers. They touch no file and no database."""

import io

import pytest

from sinac_truncation.staging import (
    SOURCE_ROW,
    StagingError,
    count_mismatch,
    sample_mismatches,
    scan_records,
    single_csv_member,
    staged_columns,
    staged_value,
    table_name,
)


def lines(text: str) -> io.StringIO:
    """Text as a file opened with ``newline=""`` reads it: line endings left as they are."""
    return io.StringIO(text, newline="")


def test_table_name_carries_the_year() -> None:
    assert table_name(2023) == "sinac_2023"


def test_staged_columns_are_the_published_names_in_lower_case() -> None:
    assert staged_columns(["EDADGESTACIONAL", "VACUNA_BCG"]) == ("edadgestacional", "vacuna_bcg")


@pytest.mark.parametrize(
    ("header", "message"),
    [
        ([], "no header"),
        (["EDAD", "FECHA NACIMIENTO"], "not a bare SQL identifier"),
        (["EDAD", ""], "not a bare SQL identifier"),
        (["EDAD", "edad"], "appears twice"),
        (["SOURCE_ROW"], SOURCE_ROW),
    ],
)
def test_staged_columns_reject_a_header_staging_cannot_hold(
    header: list[str], message: str
) -> None:
    with pytest.raises(StagingError, match=message):
        staged_columns(header)


def test_single_csv_member_is_found_whatever_its_name() -> None:
    assert single_csv_member(["Nacimientos_2023.csv"]) == "Nacimientos_2023.csv"
    assert single_csv_member(["LEEME.txt", "sinac2019DatosAbiertos.CSV"]) == (
        "sinac2019DatosAbiertos.CSV"
    )


@pytest.mark.parametrize("names", [[], ["a.txt"], ["a.csv", "b.csv"]])
def test_single_csv_member_needs_exactly_one(names: list[str]) -> None:
    with pytest.raises(StagingError, match="exactly one CSV member"):
        single_csv_member(names)


def test_a_blank_cell_is_null_and_nothing_else_is() -> None:
    assert staged_value("") is None
    assert [staged_value(value) for value in ("09", "0", " ", "NULL", "99")] == [
        "09",
        "0",
        " ",
        "NULL",
        "99",
    ]


def test_scan_counts_records_not_lines() -> None:
    """A line break inside quotes is part of its record; CRLF ends one."""
    text = '"A","B"\r\n"1","two\r\nlines"\r\n"3",""\r\n,"4"\r\n'
    scan = scan_records(lines(text), sample_every=1)
    assert scan.header == ("A", "B")
    assert scan.records == 3
    assert scan.samples == {1: ("1", "two\r\nlines"), 2: ("3", None), 3: (None, "4")}


def test_scan_samples_every_nth_record_and_the_last() -> None:
    text = '"N"\r\n' + "".join(f'"{n}"\r\n' for n in range(1, 8))
    scan = scan_records(lines(text), sample_every=3)
    assert scan.records == 7
    assert scan.samples == {3: ("3",), 6: ("6",), 7: ("7",)}


def test_scan_of_a_header_without_records() -> None:
    scan = scan_records(lines('"A","B"\r\n'), sample_every=1)
    assert scan.records == 0
    assert scan.samples == {}


def test_scan_rejects_an_empty_file() -> None:
    with pytest.raises(StagingError, match="no header"):
        scan_records(lines(""), sample_every=1)


def test_scan_rejects_a_record_with_another_number_of_fields() -> None:
    with pytest.raises(StagingError, match="record 2 has 1 fields and the header has 2"):
        scan_records(lines('"A","B"\r\n"1","2"\r\n"3"\r\n'), sample_every=1)


def test_scan_rejects_malformed_quoting() -> None:
    with pytest.raises(StagingError, match="record 1 is not valid CSV"):
        scan_records(lines('"A","B"\r\n"1"x,"2"\r\n'), sample_every=1)


def test_scan_rejects_a_sampling_step_that_is_not_positive() -> None:
    with pytest.raises(StagingError, match="must be positive"):
        scan_records(lines('"A"\r\n'), sample_every=0)


def test_counts_that_agree_have_no_message() -> None:
    assert count_mismatch({"csv": 5, "parquet": 5, "table": 5}) is None


def test_counts_that_disagree_are_all_listed() -> None:
    message = count_mismatch({"csv": 1_521_280, "parquet": 1_521_280, "table": 1_521_279})
    assert message == (
        "the stages counted different rows: csv 1,521,280, parquet 1,521,280, table 1,521,279"
    )


def test_a_sample_found_as_it_was_read_has_no_mismatch() -> None:
    expected = {1: ("09", None), 4: ("99", "x")}
    assert sample_mismatches(expected, dict(expected), ["a", "b"]) == []


def test_sample_mismatches_name_the_row_and_the_column() -> None:
    expected = {1: ("09", None), 4: ("99", "x"), 7: ("1", "2")}
    found = {1: ("9", None), 4: ("99", "")}
    assert sample_mismatches(expected, found, ["a", "b"]) == [
        "source_row 1, column a: '09' in the CSV, '9' staged",
        "source_row 4, column b: 'x' in the CSV, '' staged",
        "source_row 7 is not in the table",
    ]


def test_a_staged_row_of_another_width_is_a_mismatch() -> None:
    assert sample_mismatches({1: ("a", "b")}, {1: ("a",)}, ["x", "y"]) == [
        "source_row 1 does not have 2 columns"
    ]
