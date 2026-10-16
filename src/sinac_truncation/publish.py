"""Pure helpers for publishing the results of a run under ``results/`` (task 1.5.2, issue #59).

There is no file, database or git I/O here (CLAUDE.md rule 6): ``scripts/publish.py`` reads the
tables from the database and writes the files. What lives here is their text: which table each
output file of D-098 copies, the CSV of its rows, read back to check it against the run, and the
manifest that says which code and which data produced each file (D-014).

Every count is published as the run gives it, with no small-cell suppression (D-040).
"""

import csv
import io
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import NamedTuple

from sinac_truncation.cohorts import AttritionStep

__all__ = [
    "ATTRITION_COLUMNS",
    "OUTPUT_TABLES",
    "Code",
    "Column",
    "OutputTable",
    "PublishedFile",
    "PublishedSource",
    "Value",
    "manifest_json",
    "read_table_csv",
    "sorted_rows",
    "table_csv",
]

#: A value of a published cell, as psycopg returns it: ``bigint`` and ``integer`` as int,
#: ``double precision`` as float, ``numeric`` as Decimal, ``text`` as str, and NULL as None.
Value = int | float | Decimal | str | None


class Column(NamedTuple):
    """A column of a published table: its name in the database and in the CSV, and its type."""

    name: str
    kind: type[int] | type[float] | type[Decimal] | type[str]
    #: Whether the column holds NULL, published as an empty field.
    nullable: bool = False


@dataclass(frozen=True)
class OutputTable:
    """An output file of D-098 and the table of the ``results`` schema it copies, row for row."""

    file: str
    table: str
    columns: tuple[Column, ...]
    #: The columns that identify a row, which order the rows of the file.
    key: tuple[str, ...]

    @property
    def header(self) -> tuple[str, ...]:
        return tuple(column.name for column in self.columns)


def _text(name: str, nullable: bool = False) -> Column:
    return Column(name, str, nullable)


def _count(name: str, nullable: bool = False) -> Column:
    return Column(name, int, nullable)


def _real(name: str) -> Column:
    return Column(name, float, nullable=True)


def _percent(name: str) -> Column:
    return Column(name, Decimal, nullable=True)


#: The columns the estimates and the exposure distribution share, in the order of the tables.
_ESTIMATE_KEY = ("source", "cohort_definition_id", "period", "outcome_cutoff", "measure")

#: The five output files of D-098, with the columns of docs/protocol.md §Output tables as the
#: tables of ``sql/cohorts/tables.sql``, ``sql/analysis/estimate_tables.sql`` and
#: ``sql/analysis/simulation_tables.sql`` name them.
OUTPUT_TABLES: tuple[OutputTable, ...] = (
    OutputTable(
        file="attrition.csv",
        table="attrition",
        columns=(
            _count("cohort_definition_id"),
            _count("source_year"),
            _count("step"),
            _text("kind", nullable=True),
            _text("description"),
            _count("remaining"),
            _count("excluded", nullable=True),
        ),
        key=("cohort_definition_id", "source_year", "step"),
    ),
    OutputTable(
        file="exposure_distribution.csv",
        table="exposure_distribution",
        columns=(
            _text("source"),
            _count("cohort_definition_id"),
            _text("period"),
            _count("outcome_cutoff"),
            _text("measure"),
            _text("variant"),
            _text("level"),
            _text("outcome"),
            _count("births"),
        ),
        key=(*_ESTIMATE_KEY, "variant", "level", "outcome"),
    ),
    OutputTable(
        file="estimates.csv",
        table="estimate",
        columns=(
            _text("source"),
            _count("cohort_definition_id"),
            _text("period"),
            _count("outcome_cutoff"),
            _text("measure"),
            _text("variant"),
            _text("level"),
            _text("reference"),
            _text("model"),
            _text("stratum_variable"),
            _text("stratum_value"),
            _count("births"),
            _count("preterm_births"),
            _real("odds_ratio"),
            _real("lower_limit"),
            _real("upper_limit"),
        ),
        key=(
            *_ESTIMATE_KEY,
            "variant",
            "level",
            "model",
            "stratum_variable",
            "stratum_value",
        ),
    ),
    OutputTable(
        file="truncation_share.csv",
        table="truncation_share",
        columns=(
            _count("cohort_definition_id"),
            _text("measure"),
            _text("variant"),
            _text("level"),
            _text("scenario"),
            _text("reference"),
            _real("observed_odds_ratio"),
            _real("observed_lower"),
            _real("observed_upper"),
            _real("simulated_odds_ratio"),
            _real("observed_risk_difference"),
            _real("simulated_risk_difference"),
            _real("share"),
        ),
        key=("cohort_definition_id", "measure", "variant", "level", "scenario"),
    ),
    OutputTable(
        file="excluded_profile.csv",
        table="excluded_profile",
        columns=(
            _count("cohort_definition_id"),
            _count("step"),
            _text("subject_group"),
            _count("births"),
            _percent("preterm_percent"),
            _percent("first_trimester_start_percent"),
            _percent("no_prenatal_care_percent"),
        ),
        key=("cohort_definition_id", "step", "subject_group"),
    ),
)

#: The columns of ``results.attrition``, which ``attrition.csv`` keeps with the same names and
#: order; a test ties them to :data:`OUTPUT_TABLES`.
ATTRITION_COLUMNS: tuple[str, ...] = AttritionStep._fields


@dataclass(frozen=True)
class Code:
    """The commit a run publishes from, and the repository that holds it."""

    #: As :func:`sinac_truncation.etl.repository_url` writes it: no credentials, no ``.git``.
    repository: str
    commit: str


@dataclass(frozen=True)
class PublishedSource:
    """A file of ``config/sources.yml`` the published results were computed from."""

    id: str
    version: str
    sha256: str


@dataclass(frozen=True)
class PublishedFile:
    """A file written next to the manifest, by name."""

    name: str
    sha256: str


def sorted_rows(table: OutputTable, rows: Sequence[Sequence[Value]]) -> list[tuple[Value, ...]]:
    """The rows in the order of the file: by the columns of the key, compared in Python.

    Python compares text by code point on every system, where an ``ORDER BY`` would follow the
    collation of the database, so the same rows give the same bytes anywhere.

    Raises:
        ValueError: a row has another number of values than the table has columns.
    """
    positions = [table.header.index(name) for name in table.key]
    width = len(table.columns)
    for row in rows:
        if len(row) != width:
            raise ValueError(f"{table.file}: a row has {len(row)} values, not {width}: {row!r}")
    return sorted((tuple(row) for row in rows), key=lambda row: [row[i] for i in positions])


def _field(value: Value, column: Column, file: str) -> str:
    """One cell of the CSV. A float is written as the shortest text that reads back to the same
    float, and a Decimal as the database holds it, so the read-back is exact."""
    where = f"{file}, column {column.name}"
    if value is None:
        if not column.nullable:
            raise ValueError(f"{where}: NULL in a column that holds none")
        return ""
    if isinstance(value, bool) or not isinstance(value, column.kind):
        raise ValueError(f"{where}: {value!r} is not a {column.kind.__name__}")
    if isinstance(value, float | Decimal) and not math.isfinite(value):
        raise ValueError(f"{where}: {value!r} is not a finite number")
    if isinstance(value, str) and value == "" and column.nullable:
        raise ValueError(f"{where}: an empty text would read back as NULL")
    return repr(value) if isinstance(value, float) else str(value)


def table_csv(table: OutputTable, rows: Sequence[Sequence[Value]]) -> str:
    """The CSV of an output table: its header, then one row per row of the table, in the order
    of :func:`sorted_rows`.

    Lines end in LF on every system, so the same rows give the same bytes and the same sha256. A
    NULL is an empty field, and an empty text in a column without NULL stays empty.

    Raises:
        ValueError: a value is not of the type of its column, a NULL is in a column that holds
            none, or a number is not finite.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(table.header)
    for row in sorted_rows(table, rows):
        writer.writerow(
            [
                _field(value, column, table.file)
                for value, column in zip(row, table.columns, strict=True)
            ]
        )
    return buffer.getvalue()


def _value(text: str, column: Column) -> Value:
    if text == "" and column.nullable:
        return None
    return column.kind(text)


def read_table_csv(table: OutputTable, text: str) -> list[tuple[Value, ...]]:
    """The rows of a CSV that :func:`table_csv` wrote, typed as the database returns them.

    Raises:
        ValueError: the header is not that of the table, a row has another number of fields, or
            a field does not read as the type of its column.
    """
    rows = list(csv.reader(io.StringIO(text, newline="")))
    if not rows or tuple(rows[0]) != table.header:
        found = ",".join(rows[0]) if rows else "nothing"
        raise ValueError(f"{table.file}: the header is {found}, not {','.join(table.header)}")
    width = len(table.columns)
    read: list[tuple[Value, ...]] = []
    for number, row in enumerate(rows[1:], start=2):
        if len(row) != width:
            raise ValueError(f"{table.file}, line {number}: {len(row)} fields, not {width}")
        read.append(
            tuple(_value(field, column) for field, column in zip(row, table.columns, strict=True))
        )
    return read


def manifest_json(
    *,
    generated_at: datetime,
    code: Code,
    years: Sequence[int],
    sources: Sequence[PublishedSource],
    vocabulary_version: str,
    vocabulary_sha256: str,
    files: Sequence[PublishedFile],
) -> str:
    """``results/manifest.json``: what produced the files published next to it (D-014, D-080).

    It names the commit, the period, each record file of ``config/sources.yml`` with its sha256,
    the vocabulary, and the sha256 of each published file, so a clean clone can check that it
    reproduces them (D-020). The keys keep this order and the text ends in a newline.

    Raises:
        ValueError: ``generated_at`` is not a UTC time.
    """
    if generated_at.utcoffset() != timedelta(0):
        raise ValueError(f"the generation time must be UTC, not {generated_at.isoformat()}")
    document = {
        "generated_at": generated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "code": {"repository": code.repository, "commit": code.commit},
        "period": sorted(years),
        "sources": [
            {"id": source.id, "version": source.version, "sha256": source.sha256}
            for source in sources
        ],
        "vocabulary": {"version": vocabulary_version, "sha256": vocabulary_sha256},
        "files": [{"name": file.name, "sha256": file.sha256} for file in files],
    }
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"
