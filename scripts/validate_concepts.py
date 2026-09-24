"""Checking every concept_id of the configuration against the vocabulary loaded in ``cdm``.

The I/O lives here (rule 6): the two configuration files, the manifest and the vocabulary tables.
What each use of a concept requires, and whether the loaded row meets it, is decided by
:mod:`sinac_truncation.concepts`.

A concept of ``config/concept_sets.yml`` must exist, be valid and standard, and keep the domain,
vocabulary and code it was looked up with in Athena. A target of
``config/source_to_concept_map.csv`` must exist, be valid and standard, and belong to its row's
vocabulary and to the ``target_domain_id`` of its source vocabulary; target 0 must be concept 0.
The database must also hold the vocabulary version ``config/sources.yml`` declares.
"""

import csv
from collections.abc import Mapping, Sequence
from pathlib import Path

import psycopg
import yaml
from psycopg import sql

import download
import load_vocab
import sql_runner
from sinac_truncation.concepts import (
    ExpectedConcept,
    LoadedConcept,
    check_concept_sets,
    check_source_to_concept_map,
    concept_problems,
    expected_concepts,
)
from sinac_truncation.vocabulary import NO_MATCHING_VOCABULARY

#: Repository root, reached from this file so no absolute path is written down (rule 12).
REPO_ROOT = Path(__file__).resolve().parents[1]

CONFIG_DIR = REPO_ROOT / "config"
CONCEPT_SETS = "concept_sets.yml"
SOURCE_TO_CONCEPT_MAP = "source_to_concept_map.csv"

NAME_WIDTH = 44


class NotLoadedError(RuntimeError):
    """The database holds no vocabulary to check against."""


def read_config(
    config_dir: Path,
) -> tuple[Mapping[str, object], list[dict[str, str]], list[str]]:
    """Both configuration files, and the structural problems they have (checked as in CI)."""
    config = yaml.safe_load((config_dir / CONCEPT_SETS).read_text(encoding="utf-8"))
    if not isinstance(config, Mapping):
        return {}, [], [f"{CONCEPT_SETS} is not a mapping"]
    with (config_dir / SOURCE_TO_CONCEPT_MAP).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        header = reader.fieldnames or []
    vocabularies = config.get("source_vocabularies")
    declared = vocabularies if isinstance(vocabularies, Mapping) else {}
    problems = [f"{CONCEPT_SETS}: {problem}" for problem in check_concept_sets(config)]
    problems += [
        f"{SOURCE_TO_CONCEPT_MAP}: {problem}"
        for problem in check_source_to_concept_map(header, rows, declared)
    ]
    return config, rows, problems


def loaded_version(conn: sql_runner.Connection, schema: str) -> str | None:
    """The version of the loaded package, or ``None`` when no package is loaded."""
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL("SELECT vocabulary_version FROM {} WHERE vocabulary_id = %s").format(
                sql.Identifier(schema, "vocabulary")
            ),
            (NO_MATCHING_VOCABULARY,),
        )
        rows = cur.fetchall()
    return str(rows[0][0]) if len(rows) == 1 and rows[0][0] is not None else None


def loaded_concepts(
    conn: sql_runner.Connection, schema: str, concept_ids: Sequence[int]
) -> dict[int, LoadedConcept]:
    """The ``CONCEPT`` rows of the given ids that the database holds."""
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL(
                "SELECT concept_id, concept_name, domain_id, vocabulary_id, concept_code, "
                "standard_concept, invalid_reason FROM {} WHERE concept_id = ANY(%s)"
            ).format(sql.Identifier(schema, "concept")),
            (list(concept_ids),),
        )
        return {int(row[0]): LoadedConcept(int(row[0]), *row[1:]) for row in cur.fetchall()}


def _uses(expected: Sequence[ExpectedConcept]) -> str:
    if len(expected) == 1:
        return expected[0].used_by
    if all(use.used_by.startswith(SOURCE_TO_CONCEPT_MAP) for use in expected):
        return f"{len(expected)} rows of {SOURCE_TO_CONCEPT_MAP}"
    return "; ".join(use.used_by for use in expected)


def report(expected: Sequence[ExpectedConcept], loaded: Mapping[int, LoadedConcept]) -> list[str]:
    """Print one line per concept_id and return every problem found."""
    by_id: dict[int, list[ExpectedConcept]] = {}
    for use in expected:
        by_id.setdefault(use.concept_id, []).append(use)

    print(f"{'concept_id':>10}  {'result':<6}  {'name in the vocabulary':<{NAME_WIDTH}}  used by")
    problems: list[str] = []
    for concept_id, uses in by_id.items():
        found = loaded.get(concept_id)
        failed = [
            f"{concept_id} {use.used_by}: {problem}"
            for use in uses
            for problem in concept_problems(use, found)
        ]
        problems += failed
        name = "—" if found is None else found.concept_name[:NAME_WIDTH]
        result = "FAIL" if failed else "ok"
        print(f"{concept_id:>10}  {result:<6}  {name:<{NAME_WIDTH}}  {_uses(uses)}")
    print(f"\n{len(by_id)} concept_ids in {len(expected)} uses")
    return problems


def run(
    conn: sql_runner.Connection,
    *,
    schema: str,
    config_dir: Path = CONFIG_DIR,
    sources_path: Path = download.SOURCES_PATH,
) -> list[str]:
    """Check the configuration against the loaded vocabulary. See ``pipeline.py --help``.

    Returns:
        Every problem found, already printed; an empty list when every concept passes.

    Raises:
        NotLoadedError: the vocabulary tables are missing or empty.
        load_vocab.VocabError: the manifest has no valid ``vocabulary:`` block.
    """
    config, rows, problems = read_config(config_dir)
    if problems:
        print("the configuration fails its own checks, so it is not compared with the vocabulary:")
        for problem in problems:
            print(f"  {problem}")
        return problems

    package = load_vocab.read_package(sources_path)
    try:
        version = loaded_version(conn, schema)
        expected = expected_concepts(config, rows)
        loaded = loaded_concepts(conn, schema, sorted({use.concept_id for use in expected}))
    except psycopg.errors.UndefinedTable as error:
        raise NotLoadedError(
            f"{error}. Run `pipeline.py db-init` and `pipeline.py vocab` first."
        ) from error
    if version is None:
        raise NotLoadedError(f"no vocabulary is loaded in {schema!r}: run `pipeline.py vocab`")

    print(
        f"vocabulary {version!r} in {schema} (config/sources.yml declares "
        f"{package.vocabulary_version!r})\n"
    )
    problems = []
    if version != package.vocabulary_version:
        problems.append(
            f"the database holds vocabulary {version!r}, config/sources.yml declares "
            f"{package.vocabulary_version!r}: run `pipeline.py vocab`"
        )
    problems += report(expected, loaded)

    if problems:
        print(f"{len(problems)} problem(s):")
        for problem in problems:
            print(f"  {problem}")
    else:
        print("every concept exists, is valid, is standard where required and has its domain")
    return problems
