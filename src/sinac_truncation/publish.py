"""Pure helpers for publishing the results of a run under ``results/`` (task 1.5.2).

There is no file, database or git I/O here (CLAUDE.md rule 6): ``scripts/publish.py`` reads the
attrition from the database and writes the files. What lives here is their text: the CSV of an
attrition table, read back to check it against the run, and the manifest that says which code and
which data produced each file (D-014).

Every count is published as the run gives it, with no small-cell suppression (D-040).
"""

import csv
import io
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from sinac_truncation.cohorts import AttritionStep

__all__ = [
    "ATTRITION_COLUMNS",
    "Code",
    "PublishedFile",
    "PublishedSource",
    "attrition_csv",
    "manifest_json",
    "read_attrition_csv",
]

#: The columns of ``results.attrition``, which the CSV keeps with the same names and order.
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


def attrition_csv(steps: Sequence[AttritionStep]) -> str:
    """The CSV of an attrition table: a header, then one row per step in order.

    Rows are ordered by definition, year and step, whatever the order of ``steps``. Lines end in
    LF on every system, so the same table gives the same bytes and the same sha256. A kind or an
    ``excluded`` count that is missing (step 0) is an empty field.
    """
    ordered = sorted(
        steps, key=lambda step: (step.cohort_definition_id, step.source_year, step.step)
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(ATTRITION_COLUMNS)
    for step in ordered:
        writer.writerow(["" if value is None else value for value in step])
    return buffer.getvalue()


def _count(value: str) -> int | None:
    return None if value == "" else int(value)


def read_attrition_csv(text: str) -> list[AttritionStep]:
    """The steps of a CSV that :func:`attrition_csv` wrote, in the order of its rows.

    Raises:
        ValueError: the header is not :data:`ATTRITION_COLUMNS`, or a count is not an integer.
    """
    rows = list(csv.reader(io.StringIO(text, newline="")))
    if not rows or tuple(rows[0]) != ATTRITION_COLUMNS:
        found = ",".join(rows[0]) if rows else "nothing"
        raise ValueError(f"the header is {found}, not {','.join(ATTRITION_COLUMNS)}")
    return [
        AttritionStep(
            cohort_definition_id=int(definition),
            source_year=int(year),
            step=int(step),
            kind=kind or None,
            description=description,
            remaining=int(remaining),
            excluded=_count(excluded),
        )
        for definition, year, step, kind, description, remaining, excluded in rows[1:]
    ]


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
