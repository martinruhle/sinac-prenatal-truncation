"""Pure helpers for the ETL that populates the CDM tables of the vertical slice (task 1.4.4).

There is no file or database I/O here (CLAUDE.md rule 6): ``scripts/etl.py`` reads the SQL files,
the configuration and the manifest, and runs the load. What lives here is what can be decided from
text alone: the ids of D-059, the concept keys and source vocabularies the SQL cites, the rows that
register the local vocabularies, the ``CDM_SOURCE`` texts and the report of the counts.

Every rule of the mapping itself is SQL, in ``sql/etl/`` (docs/omop_mapping.md).
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import PurePosixPath
from urllib.parse import urlsplit, urlunsplit

__all__ = [
    "CATALOGUE_SOURCE",
    "COUNTED_TABLES",
    "DESCRIPTOR_SOURCE",
    "FIRST_YEAR",
    "LAST_YEAR",
    "LOAD_FILES",
    "POPULATED_TABLES",
    "ROWS_PER_YEAR",
    "SETUP_FILES",
    "SOURCE_COLUMNS",
    "SQL_FILES",
    "UNLOADABLE_FILE",
    "CountRow",
    "RecordFile",
    "Reference",
    "concept_keys",
    "config_problems",
    "etl_reference",
    "format_counts",
    "person_id",
    "release_date",
    "source_description",
    "vocabulary_ids",
    "vocabulary_rows",
    "year_problems",
]

#: The source columns the ETL reads, as DGIS publishes them. Staging holds them in lower case.
SOURCE_COLUMNS: tuple[str, ...] = (
    "FECHANACIMIENTO",
    "FECHANACIMIENTOMADRE",
    "EDAD",
    "RESIDEEXTRANJERO",
    "ENTIDADRESIDENCIA",
    "EDADGESTACIONAL",
    "PRODUCTOEMBARAZO",
    "TOTALCONSULTAS",
    "TRIMESTREPRIMERCONSULTA",
)

#: ``tables.sql`` creates the tables the ETL keeps in ``results``; ``records.sql`` casts every
#: staged value; ``unloadable.sql`` lists the records that stop the load. These run first.
SETUP_FILES: tuple[str, ...] = ("tables.sql", "records.sql")
UNLOADABLE_FILE = "unloadable.sql"

#: The files that write the CDM and the counts, in the order they run: LOCATION comes before
#: PERSON, which references it, and the checks come last.
LOAD_FILES: tuple[str, ...] = (
    "location.sql",
    "person.sql",
    "observation_period.sql",
    "measurement.sql",
    "observation.sql",
    "cdm_source.sql",
    "counts.sql",
    "checks.sql",
)

SQL_FILES: tuple[str, ...] = (*SETUP_FILES, UNLOADABLE_FILE, *LOAD_FILES)

#: The CDM tables the ETL empties and fills on every run (docs/omop_mapping.md §Scope).
POPULATED_TABLES: tuple[str, ...] = (
    "person",
    "observation_period",
    "measurement",
    "observation",
    "location",
    "cdm_source",
    "source_to_concept_map",
)

#: The order in which the report lists the tables of ``results.etl_counts``.
COUNTED_TABLES: tuple[str, ...] = (
    "staging",
    "person",
    "observation_period",
    "measurement",
    "observation",
    "location",
    "vocabulary",
    "source_to_concept_map",
    "cdm_source",
    "check",
)

#: ``person_id`` = (year − FIRST_YEAR) × ROWS_PER_YEAR + ``source_row`` (D-059). The formula fits
#: the ``integer`` column up to LAST_YEAR, and no file has as many as ROWS_PER_YEAR records.
FIRST_YEAR = 2000
LAST_YEAR = 2099
ROWS_PER_YEAR = 10_000_000

#: The manifest entries a local vocabulary points at: the descriptor, when its codes are declared
#: there, and otherwise the catalogue set of the 2020-2023 catalogue period (concept_sets.yml).
DESCRIPTOR_SOURCE = "dgis_sinac_descriptores_2020_2025"
CATALOGUE_SOURCE = "dgis_sinac_catalogos_2020_2023"

#: A concept of ``config/concept_sets.yml`` as the SQL cites it: by key, never by id (D-074).
_CONCEPT_KEY = re.compile(r"concept_key\s*=\s*'([^']*)'")

#: A local source vocabulary as the SQL cites it, in its join to ``source_to_concept_map``.
_VOCABULARY_ID = re.compile(r"source_vocabulary_id\s*=\s*'([^']*)'")

#: A row of ``results.etl_counts``: year (``None`` for the whole load), table, rule, rows.
CountRow = tuple[int | None, str, str, int]


def person_id(year: int, source_row: int) -> int:
    """The ``person_id`` of the mother of one record (D-059).

    Raises:
        ValueError: the year or the row does not fit the formula.
    """
    if not FIRST_YEAR <= year <= LAST_YEAR:
        raise ValueError(f"year {year} is outside {FIRST_YEAR}-{LAST_YEAR}")
    if not 1 <= source_row < ROWS_PER_YEAR:
        raise ValueError(f"source_row {source_row} is outside 1-{ROWS_PER_YEAR - 1:,}")
    return (year - FIRST_YEAR) * ROWS_PER_YEAR + source_row


def year_problems(years: Sequence[int]) -> list[str]:
    """The years the ids of D-059 cannot hold."""
    return [
        f"{year} is outside {FIRST_YEAR}-{LAST_YEAR}, the years person_id can hold (D-059)"
        for year in years
        if not FIRST_YEAR <= year <= LAST_YEAR
    ]


def concept_keys(sql: str) -> frozenset[str]:
    """The keys of ``config/concept_sets.yml`` that a SQL text cites."""
    return frozenset(_CONCEPT_KEY.findall(sql))


def vocabulary_ids(sql: str) -> frozenset[str]:
    """The local source vocabularies that a SQL text joins ``source_to_concept_map`` on."""
    return frozenset(_VOCABULARY_ID.findall(sql))


def config_problems(
    sql_texts: Mapping[str, str],
    concepts: Mapping[str, object],
    source_vocabularies: Mapping[str, object],
) -> list[str]:
    """Every concept key and local vocabulary the SQL cites that the configuration does not declare.

    A missing key would reach the database as a NULL concept id, which a nullable field such as
    ``unit_concept_id`` would take without complaint; so it is refused before anything runs.
    """
    problems: list[str] = []
    for name, text in sql_texts.items():
        problems += [
            f"sql/etl/{name} cites the concept {key!r}, which config/concept_sets.yml lacks"
            for key in sorted(concept_keys(text) - set(concepts))
        ]
        problems += [
            f"sql/etl/{name} joins the vocabulary {vocabulary!r}, which "
            "config/concept_sets.yml does not declare"
            for vocabulary in sorted(vocabulary_ids(text) - set(source_vocabularies))
        ]
    return problems


@dataclass(frozen=True)
class Reference:
    """A file of the manifest a local vocabulary refers to: its URL and published version."""

    url: str
    version: str


def vocabulary_rows(
    source_vocabularies: Mapping[str, object], *, descriptor: Reference, catalogues: Reference
) -> list[tuple[str, str, str, str, int]]:
    """The ``VOCABULARY`` rows of the local source vocabularies (docs/omop_mapping.md rule 6).

    Each row names the source column, and refers to the descriptor or to the catalogue set that
    publishes its codes, with that file's version. ``vocabulary_concept_id`` is 0 (D-023).

    Returns:
        ``(vocabulary_id, vocabulary_name, vocabulary_reference, vocabulary_version,
        vocabulary_concept_id)`` per vocabulary, in the order of the configuration.
    """
    rows: list[tuple[str, str, str, str, int]] = []
    for vocabulary_id, entry in source_vocabularies.items():
        if not isinstance(entry, Mapping):
            continue
        defined_in = str(entry.get("defined_in"))
        reference = descriptor if defined_in == "descriptor" else catalogues
        name = f"SINAC local codes of {entry.get('source_column')}, defined in {defined_in}"
        rows.append((vocabulary_id, name, reference.url, reference.version, 0))
    return rows


@dataclass(frozen=True)
class RecordFile:
    """One loaded record file, as ``CDM_SOURCE`` describes it."""

    year: int
    url: str
    version: str
    sha256: str
    #: ``retrieved_at`` of the manifest, an ISO 8601 UTC timestamp.
    retrieved_at: str


def source_description(files: Sequence[RecordFile]) -> str:
    """``CDM_SOURCE.source_description``: each loaded file with its version and sha256 (D-059)."""
    described = [
        f"{record.year}: {PurePosixPath(urlsplit(record.url).path).name}?V={record.version}, "
        f"sha256 {record.sha256}"
        for record in sorted(files, key=lambda record: record.year)
    ]
    return "SINAC record files loaded: " + "; ".join(described)


def release_date(files: Sequence[RecordFile]) -> date:
    """``CDM_SOURCE.source_release_date``: the latest retrieval date of the loaded files.

    DGIS publishes a dated version for 2022 and 2023 only, so the retrieval date is the one date
    every file has (docs/omop_mapping.md §CDM_SOURCE).

    Raises:
        ValueError: there are no files, or a timestamp is not ISO 8601.
    """
    if not files:
        raise ValueError("no record files were loaded")
    return max(date.fromisoformat(record.retrieved_at[:10]) for record in files)


def etl_reference(remote_url: str, commit: str, *, dirty: bool) -> str:
    """``CDM_SOURCE.cdm_etl_reference``: the repository and the commit the ETL ran from.

    Credentials a remote URL may carry (``https://user:token@host/...``) are dropped, and so is a
    trailing ``.git``, so the reference is a URL that can be opened.
    """
    parts = urlsplit(remote_url.strip())
    host = parts.hostname or ""
    netloc = host if parts.port is None else f"{host}:{parts.port}"
    url = urlunsplit((parts.scheme, netloc, parts.path, "", "")) if parts.scheme else remote_url
    url = url.removesuffix(".git")
    reference = f"{url} at commit {commit.strip()}"
    return f"{reference}, with uncommitted changes" if dirty else reference


def _order(row: CountRow) -> tuple[int, int, bool, str]:
    year, table, rule, _ = row
    position = COUNTED_TABLES.index(table) if table in COUNTED_TABLES else len(COUNTED_TABLES)
    return (position, -1 if year is None else year, rule != "rows", rule)


def format_counts(rows: Sequence[CountRow]) -> list[str]:
    """The lines of the report that ``pipeline.py cdm`` prints: one per row of ``etl_counts``.

    Rows are listed by table in load order, then by year (the rows about the whole load first),
    with each table's own row count ahead of its rules.
    """
    width = max([len(rule) for _, _, rule, _ in rows] + [len("rule")])
    lines = [f"{'year':<6}{'table':<23}{'rule':<{width}}  {'rows':>13}"]
    for year, table, rule, count in sorted(rows, key=_order):
        shown = "all" if year is None else str(year)
        lines.append(f"{shown:<6}{table:<23}{rule:<{width}}  {count:>13,}")
    return lines
