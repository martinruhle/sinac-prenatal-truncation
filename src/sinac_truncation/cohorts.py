"""Pure helpers for the cohorts and their attrition (task 1.5.1).

There is no file or database I/O here (CLAUDE.md rule 6): ``scripts/cohorts.py`` reads the SQL of
``sql/cohorts/`` and runs it. What lives here is what can be decided from text and numbers alone:
the files and the codes the SQL cites, the invariants every attrition table must meet, and the
report.

Every criterion is SQL, in ``sql/cohorts/`` (CLAUDE.md rule 5, docs/protocol.md §Base cohort).
"""

from collections.abc import Mapping, Sequence
from itertools import groupby
from typing import NamedTuple

from sinac_truncation.etl import concept_keys

__all__ = [
    "MEXICO_CODE",
    "SQL_FILES",
    "AttritionStep",
    "attrition_problems",
    "cited_concept_keys",
    "format_attrition",
]

#: ``tables.sql`` creates the tables; each definition file writes its cohort and the step at which
#: each subject leaves it; ``attrition.sql`` counts them. They run in this order.
SQL_FILES: tuple[str, ...] = ("tables.sql", "01_base.sql", "attrition.sql")

#: The source code whose target in ``source_to_concept_map`` criterion 2 reads: RESIDEEXTRANJERO 2,
#: "NO" (does not reside abroad) in the catalogue SI_NO, mapped to Mexico (docs/omop_mapping.md
#: §LOCATION, D-068).
MEXICO_CODE: tuple[str, str] = ("SINAC20_RESEXT", "2")


class AttritionStep(NamedTuple):
    """A row of ``results.attrition``."""

    cohort_definition_id: int
    source_year: int
    step: int
    kind: str | None
    description: str
    remaining: int
    #: ``None`` at step 0, which starts from the files and excludes nobody.
    excluded: int | None


def cited_concept_keys(sql_texts: Mapping[str, str]) -> frozenset[str]:
    """The keys of ``config/concept_sets.yml`` that the cohort SQL cites."""
    return frozenset().union(*(concept_keys(text) for text in sql_texts.values()))


def _key(step: AttritionStep) -> tuple[int, int]:
    return (step.cohort_definition_id, step.source_year)


def _table_problems(steps: Sequence[AttritionStep], cohort_rows: int) -> list[str]:
    """The invariants of one attrition table: one definition, one year of the record files."""
    where = f"definition {steps[0].cohort_definition_id}, {steps[0].source_year}"
    numbers = [step.step for step in steps]
    if numbers != list(range(len(steps))):
        listed = ", ".join(str(number) for number in numbers)
        return [f"{where}: the steps are {listed}, not 0 to {len(steps) - 1}"]

    problems: list[str] = []
    for previous, step in zip([None, *steps[:-1]], steps, strict=True):
        at = f"{where}, step {step.step}"
        if step.remaining < 0:
            problems.append(f"{at}: remaining is negative")
        if previous is None:
            if step.excluded is not None:
                problems.append(f"{at}: excluded is {step.excluded}, and step 0 excludes nobody")
            continue
        if step.excluded is None:
            problems.append(f"{at}: excluded is missing")
            continue
        if step.excluded < 0:
            problems.append(f"{at}: excluded is negative")
        if step.remaining > previous.remaining:
            problems.append(
                f"{at}: {step.remaining:,} remain after {previous.remaining:,}, and a step "
                "cannot add records"
            )
        removed = previous.remaining - step.remaining
        if step.excluded != removed:
            problems.append(
                f"{at}: {step.excluded:,} excluded, but {previous.remaining:,} - "
                f"{step.remaining:,} = {removed:,}"
            )
    last = steps[-1].remaining
    if last != cohort_rows:
        problems.append(
            f"{where}: the last step leaves {last:,} and the cohort holds {cohort_rows:,} rows"
        )
    return problems


def attrition_problems(
    steps: Sequence[AttritionStep], cohort_rows: Mapping[tuple[int, int], int]
) -> list[str]:
    """Every invariant the attrition breaks, per definition and year of the record files.

    In each table the steps run from 0 without a gap; step 0 excludes nobody and every other step
    says how many it excludes; no count is negative; the counts never grow from one step to the
    next; each step excludes exactly the difference between the step before and itself; and the
    last step leaves exactly the rows the cohort holds for that definition and year.

    Args:
        steps: the rows of ``results.attrition``, in any order.
        cohort_rows: the rows of ``results.cohort`` per (definition, year of the record files).

    Returns:
        One message per broken invariant; an empty list when the attrition is consistent.
    """
    ordered = sorted(steps, key=lambda step: (*_key(step), step.step))
    problems: list[str] = []
    tables = {key: list(group) for key, group in groupby(ordered, key=_key)}
    for key, table in tables.items():
        problems += _table_problems(table, cohort_rows.get(key, 0))
    for (definition, year), count in sorted(cohort_rows.items()):
        if (definition, year) not in tables:
            problems.append(
                f"definition {definition}, {year}: the cohort holds {count:,} rows and there is no "
                "attrition"
            )
    return problems


def format_attrition(steps: Sequence[AttritionStep]) -> list[str]:
    """The lines of the report that ``pipeline.py cohorts`` prints: one per step, in order."""
    ordered = sorted(steps, key=lambda step: (*_key(step), step.step))
    kind = max([len(step.kind or "") for step in ordered] + [len("kind")])
    described = max([len(step.description) for step in ordered] + [len("description")])
    lines = [
        f"{'definition':<12}{'year':<6}{'step':<6}{'kind':<{kind}}  {'description':<{described}}"
        f"  {'remaining':>13}  {'excluded':>13}"
    ]
    for step in ordered:
        excluded = "" if step.excluded is None else f"{step.excluded:,}"
        lines.append(
            f"{step.cohort_definition_id:<12}{step.source_year:<6}{step.step:<6}"
            f"{step.kind or '':<{kind}}  {step.description:<{described}}"
            f"  {step.remaining:>13,}  {excluded:>13}"
        )
    return lines
