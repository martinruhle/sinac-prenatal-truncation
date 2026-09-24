"""Pure helpers for staging the SINAC record files.

There is no file or database I/O here (CLAUDE.md rule 6): ``scripts/stage.py`` opens the ZIP, the
CSV, DuckDB and Postgres, and uses these functions to name the table and its columns, to count
the records of the CSV and to compare what each stage counted.

Staging keeps every source column as text (D-033). The one column it adds is ``source_row``, the
1-based ordinal of the record in its file, header excluded, which the CDM ids are built from
(D-059).
"""

import csv
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from sinac_truncation.sqltext import is_valid_identifier

__all__ = [
    "SOURCE_ROW",
    "STAGES",
    "CsvScan",
    "Record",
    "StagingError",
    "count_mismatch",
    "sample_mismatches",
    "scan_records",
    "single_csv_member",
    "staged_columns",
    "staged_value",
    "table_name",
]

#: The column staging adds to every record (D-059).
SOURCE_ROW = "source_row"

#: The stages whose row counts must agree, in the order they run.
STAGES = ("csv", "parquet", "table")

#: A staged record: one value per source column, NULL where the cell was blank.
Record = tuple[str | None, ...]


class StagingError(ValueError):
    """A source file cannot be staged as it is."""


def table_name(year: int) -> str:
    """The staging table of one year's record file, such as ``sinac_2023`` (D-069)."""
    return f"sinac_{year}"


def staged_columns(header: Sequence[str]) -> tuple[str, ...]:
    """The staging column of each source column: its published name in lower case (D-069).

    Postgres folds unquoted identifiers to lower case, so a query can still spell a column as
    DGIS publishes it (``EDADGESTACIONAL``) without quoting it.

    Raises:
        StagingError: the header is empty, a name is not a bare SQL identifier, two names are
            the same once in lower case, or a name is the ``source_row`` staging adds.
    """
    if not header:
        raise StagingError("the file has no header")
    columns: list[str] = []
    for name in header:
        if not is_valid_identifier(name):
            raise StagingError(f"the column name {name!r} is not a bare SQL identifier")
        column = name.lower()
        if column == SOURCE_ROW:
            raise StagingError(f"the source already has a column named {SOURCE_ROW!r}")
        if column in columns:
            raise StagingError(f"the column name {name!r} appears twice, ignoring case")
        columns.append(column)
    return tuple(columns)


def single_csv_member(names: Sequence[str]) -> str:
    """The one CSV member of a record ZIP.

    The member is found, not built: its name follows no pattern across years
    (docs/source_inventory.md, observation 1).

    Raises:
        StagingError: the archive holds no CSV, or more than one.
    """
    found = [name for name in names if name.lower().endswith(".csv")]
    if len(found) != 1:
        listed = ", ".join(found) or "none"
        raise StagingError(f"expected exactly one CSV member in the ZIP, found {listed}")
    return found[0]


def staged_value(value: str) -> str | None:
    """A cell as staging stores it: blank is NULL (D-069), anything else stays as it is."""
    return None if value == "" else value


@dataclass(frozen=True)
class CsvScan:
    """What one pass of Python's own CSV parser measured over a record file."""

    header: tuple[str, ...]
    records: int
    #: Some records, keyed by their ``source_row``, as staging must hold them.
    samples: Mapping[int, Record]


def scan_records(lines: Iterable[str], *, sample_every: int) -> CsvScan:
    """Count the data records of a CSV and keep a sample of them.

    The count comes from Python's ``csv`` module, not from DuckDB, which writes the Parquet: a
    count taken by the reader that wrote the file could not catch that reader's own loss (D-070).
    ``lines`` must come from a file opened with ``newline=""``, so that a line break inside a
    quoted field stays part of its record.

    The sample holds every ``sample_every``-th record and the last one, so that the table can be
    compared with the file field by field, at positions spread over all of it.

    Raises:
        StagingError: ``sample_every`` is not positive, the file is empty, a record is malformed,
            or a record has another number of fields than the header.
    """
    if sample_every < 1:
        raise StagingError(f"sample_every must be positive, not {sample_every}")

    reader = csv.reader(lines, delimiter=",", quotechar='"', doublequote=True, strict=True)
    records = 0
    samples: dict[int, Record] = {}
    last: list[str] | None = None
    try:
        header = next(reader, None)
        if header is None:
            raise StagingError("the file is empty: it has no header")
        for row in reader:
            records += 1
            if len(row) != len(header):
                raise StagingError(
                    f"record {records} has {len(row)} fields and the header has {len(header)}"
                )
            if records % sample_every == 0:
                samples[records] = tuple(staged_value(value) for value in row)
            last = row
    except csv.Error as error:
        raise StagingError(f"record {records + 1} is not valid CSV: {error}") from error

    if last is not None:
        samples[records] = tuple(staged_value(value) for value in last)
    return CsvScan(header=tuple(header), records=records, samples=samples)


def count_mismatch(counts: Mapping[str, int]) -> str | None:
    """``None`` when every stage counted the same rows, otherwise the message that says so."""
    if len(set(counts.values())) <= 1:
        return None
    listed = ", ".join(f"{stage} {rows:,}" for stage, rows in counts.items())
    return f"the stages counted different rows: {listed}"


def sample_mismatches(
    expected: Mapping[int, Record],
    found: Mapping[int, Record],
    columns: Sequence[str],
) -> list[str]:
    """Every difference between the sampled CSV records and the rows staged for them.

    ``expected`` comes from :func:`scan_records`; ``found`` holds the staged rows keyed by
    ``source_row``. An empty list means the table holds exactly what the file holds, in the
    positions the file holds it.
    """
    problems: list[str] = []
    for row, values in sorted(expected.items()):
        staged = found.get(row)
        if staged is None:
            problems.append(f"{SOURCE_ROW} {row} is not in the table")
            continue
        if len(staged) != len(columns) or len(values) != len(columns):
            problems.append(f"{SOURCE_ROW} {row} does not have {len(columns)} columns")
            continue
        for column, want, got in zip(columns, values, staged, strict=True):
            if want != got:
                problems.append(
                    f"{SOURCE_ROW} {row}, column {column}: {want!r} in the CSV, {got!r} staged"
                )
    return problems
