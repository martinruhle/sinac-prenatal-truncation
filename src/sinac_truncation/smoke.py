"""Pure builders of the synthetic source of the smoke run: records, vocabulary and manifest.

``pipeline.py all --source fixtures`` runs every step of the pipeline on what these functions
build, so CI exercises the whole chain without downloading anything (task 1.9.4, D-136). There
is no file or database I/O here (CLAUDE.md rule 6): ``scripts/smoke_source.py`` zips, hashes and
writes.

The records are invented and few. Each one only uses codes the real configuration maps, so every
cohort, every measure and every stratum of the models gets some births; the fixture exercises the
code, it says nothing about SINAC. The vocabulary holds one ``CONCEPT`` row per ``concept_id`` of
``config/concept_sets.yml`` and ``config/source_to_concept_map.csv``, with the fields that
configuration records for it, so no ``concept_id`` is written here (rule 8). Whatever the
configuration does not record (the name and code of a target of the map, the concept class) is
marked as synthetic.
"""

import csv
import io
from collections.abc import Mapping, Sequence
from typing import Any

from sinac_truncation.etl import SOURCE_COLUMNS
from sinac_truncation.vocabulary import (
    DELIMITER,
    LOADED_TABLES,
    NO_MATCHING_VOCABULARY,
    member_name,
)

__all__ = [
    "CONCEPT_CLASS",
    "RECORDS_PER_YEAR",
    "VOCABULARY_COLUMNS",
    "VOCABULARY_VERSION",
    "manifest",
    "record_csv",
    "records",
    "vocabulary_members",
    "vocabulary_rows",
]

#: The births of each year. Enough for every level of the models to meet every other a few
#: times, few enough for the run to take seconds.
RECORDS_PER_YEAR = 600

#: ``vocabulary_version`` of the ``'None'`` row, which the manifest declares and the ETL checks.
VOCABULARY_VERSION = "v5.0 SMOKE FIXTURE"

#: The class of every synthetic concept. ``validate-concepts`` does not read it.
CONCEPT_CLASS = "Smoke fixture"

#: A valid concept's dates, as Athena writes them (YYYYMMDD).
VALID_START = "19700101"
VALID_END = "20991231"

#: The CDM v5.4 columns of each loaded vocabulary table, in the order of the vendored DDL
#: (sql/ddl/ohdsi/OMOPCDM_postgresql_5.4_ddl.sql). ``vocab`` checks each header against the table.
VOCABULARY_COLUMNS: Mapping[str, tuple[str, ...]] = {
    "vocabulary": (
        "vocabulary_id", "vocabulary_name", "vocabulary_reference", "vocabulary_version",
        "vocabulary_concept_id",
    ),
    "domain": ("domain_id", "domain_name", "domain_concept_id"),
    "concept_class": ("concept_class_id", "concept_class_name", "concept_class_concept_id"),
    "relationship": (
        "relationship_id", "relationship_name", "is_hierarchical", "defines_ancestry",
        "reverse_relationship_id", "relationship_concept_id",
    ),
    "concept": (
        "concept_id", "concept_name", "domain_id", "vocabulary_id", "concept_class_id",
        "standard_concept", "concept_code", "valid_start_date", "valid_end_date", "invalid_reason",
    ),
    "concept_relationship": (
        "concept_id_1", "concept_id_2", "relationship_id", "valid_start_date", "valid_end_date",
        "invalid_reason",
    ),
    "concept_ancestor": (
        "ancestor_concept_id", "descendant_concept_id", "min_levels_of_separation",
        "max_levels_of_separation",
    ),
}  # fmt: skip

# The values each record cycles through. Every code is one config/source_to_concept_map.csv maps,
# or a value the descriptor defines (weeks, visits, age); none is a "no especificado" code, so
# the records reach the analysis cohort (sql/cohorts/02_analysis.sql). The lengths are pairwise
# coprime, so no field repeats another and the adjusted models are not collinear by construction.
#: One age in each group of docs/protocol.md §Covariates. 7 values.
_AGES = (14, 17, 22, 27, 33, 38, 42)
#: Term and preterm births, some under 32 and 34 weeks, all past the landmark of 28. 11 values.
_WEEKS = (39, 38, 40, 36, 39, 33, 41, 31, 39, 29, 37)
#: TRIMESTREPRIMERCONSULTA: first, second, third trimester; 0 is no care. 5 values.
_TRIMESTERS = ("1", "2", "3", "1", "0")
#: ENTIDADRESIDENCIA. 3 values.
_STATES = ("09", "14", "31")
#: ESCOLARIDAD: primary, junior high, senior high, higher. 4 values.
_EDUCATION = ("31", "51", "71", "81")
#: AFILIACION: every code of the catalogue AFILIACION_CERTIFICADOS (D-133). 13 values.
_INSURANCE = ("00", "01", "02", "03", "04", "05", "06", "07", "08", "10", "11", "88", "99")
#: Visits of a mother who had care cycle over 1 to 17.
_VISIT_PERIOD = 17


def _record(year: int, index: int) -> tuple[str, ...]:
    """One birth, in the order of SOURCE_COLUMNS. Each field cycles at its own period, so the
    combinations spread over the year's records."""
    age = _AGES[index % len(_AGES)]
    weeks = _WEEKS[index % len(_WEEKS)]
    trimester = _TRIMESTERS[index % len(_TRIMESTERS)]
    visits = "0" if trimester == "0" else str(1 + index % _VISIT_PERIOD)
    # One birth in twelve is a twin, so the cohort with multiple pregnancies has some.
    plurality = "2" if index % 12 == 11 else "1"
    delivery = f"{1 + index % 28:02d}/{1 + index % 12:02d}/{year}"
    # Born on 1 January, so the age at any delivery of that year is exactly ``age``.
    mother_birth = f"01/01/{year - age}"
    return (
        delivery,
        mother_birth,
        str(age),
        "2",
        _STATES[index % len(_STATES)],
        str(weeks),
        plurality,
        visits,
        trimester,
        _EDUCATION[index % len(_EDUCATION)],
        "1" if index % 2 else "2",
        "3200" if weeks >= 37 else "2100",
        _INSURANCE[index % len(_INSURANCE)],
    )


def records(year: int, count: int = RECORDS_PER_YEAR) -> list[tuple[str, ...]]:
    """The synthetic births of one year, in the order of SOURCE_COLUMNS."""
    return [_record(year, index) for index in range(count)]


def record_csv(rows: Sequence[Sequence[str]]) -> bytes:
    """A record file as DGIS publishes it: a header, comma-separated, UTF-8."""
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\r\n")
    writer.writerow(SOURCE_COLUMNS)
    writer.writerows(rows)
    return out.getvalue().encode("utf-8")


def _expected_rows(
    config: Mapping[str, Any], map_rows: Sequence[Mapping[str, str]]
) -> dict[int, tuple[str, ...]]:
    """One CONCEPT row per concept_id the configuration uses, with the fields it records."""
    concepts: dict[int, tuple[str, ...]] = {
        0: ("0", "No matching concept", "Metadata", NO_MATCHING_VOCABULARY, "Undefined", "",
            "No matching concept", VALID_START, VALID_END, ""),
    }  # fmt: skip
    for entry in (config.get("concepts") or {}).values():
        concept_id = int(entry["concept_id"])
        concepts[concept_id] = (
            str(concept_id),
            str(entry["concept_name"]),
            str(entry["domain_id"]),
            str(entry["vocabulary_id"]),
            CONCEPT_CLASS,
            "S",
            str(entry["concept_code"]),
            VALID_START,
            VALID_END,
            "",
        )
    vocabularies = config.get("source_vocabularies") or {}
    for row in map_rows:
        concept_id = int(row["target_concept_id"])
        if concept_id in concepts:
            continue
        declared = vocabularies.get(row["source_vocabulary_id"]) or {}
        domain = declared.get("target_domain_id") or "Metadata"
        concepts[concept_id] = (
            str(concept_id),
            f"Synthetic smoke-run concept {concept_id}",
            str(domain),
            row["target_vocabulary_id"],
            CONCEPT_CLASS,
            "S",
            "SMOKE",
            VALID_START,
            VALID_END,
            "",
        )
    return dict(sorted(concepts.items()))


def vocabulary_rows(
    config: Mapping[str, Any], map_rows: Sequence[Mapping[str, str]]
) -> dict[str, list[tuple[str, ...]]]:
    """The rows of each loaded table: the concepts the configuration uses, and one row for each
    vocabulary, domain and class they name. The relationship tables stay empty: no step reads
    them."""
    concepts = list(_expected_rows(config, map_rows).values())
    vocabularies = sorted({row[3] for row in concepts} - {NO_MATCHING_VOCABULARY})
    domains = sorted({row[2] for row in concepts})
    classes = sorted({row[4] for row in concepts})
    return {
        "vocabulary": [
            (NO_MATCHING_VOCABULARY, "OMOP Standardized Vocabularies", "Synthetic smoke fixture",
             VOCABULARY_VERSION, "0"),
            *((vocabulary, f"Synthetic {vocabulary}", "Synthetic smoke fixture", "", "0")
              for vocabulary in vocabularies),
        ],
        "domain": [(domain, domain, "0") for domain in domains],
        "concept_class": [(name, name, "0") for name in classes],
        "relationship": [],
        "concept": concepts,
        "concept_relationship": [],
        "concept_ancestor": [],
    }  # fmt: skip


def vocabulary_members(rows: Mapping[str, Sequence[Sequence[str]]]) -> dict[str, bytes]:
    """Each table as a file of the Athena package: tab-delimited, a header, no quoting."""
    members: dict[str, bytes] = {}
    for table in LOADED_TABLES:
        lines = [VOCABULARY_COLUMNS[table], *rows[table]]
        members[member_name(table)] = "".join(DELIMITER.join(line) + "\n" for line in lines).encode(
            "utf-8"
        )
    return members


def manifest(
    record_files: Mapping[str, tuple[int, str, int]],
    package: tuple[str, str, int],
    rows: Mapping[str, int],
    *,
    descriptor_id: str,
    catalogue_id: str,
) -> dict[str, Any]:
    """The ``config/sources.yml`` of the fixtures.

    Args:
        record_files: by manifest id, the year, sha256 and size of its ZIP.
        package: the vocabulary ZIP, relative to the fixture root, with its sha256 and size.
        rows: the data rows of each loaded table.
        descriptor_id, catalogue_id: the ids the ETL reads the descriptor and catalogue versions
            from.
    """
    version = "1.0"
    base = "http://smoke.example.test/nacimientos"
    downloads: list[dict[str, Any]] = [
        {
            "id": entry_id,
            "page": f"{base}.html",
            "url": f"{base}/sinac_{year}.zip?V={version}",
            "version": version,
            "retrieved_at": "2026-01-01T00:00:00Z",
            "size_bytes": size,
            "sha256": sha256,
        }
        for entry_id, (year, sha256, size) in record_files.items()
    ]
    downloads += [
        {"id": descriptor_id, "url": f"{base}/descriptores.zip?V={version}", "version": version},
        {"id": catalogue_id, "url": f"{base}/catalogos.zip?V={version}", "version": version},
    ]
    file, sha256, size = package
    return {
        "downloads": downloads,
        "vocabulary": {
            "file": file,
            "size_bytes": size,
            "sha256": sha256,
            "vocabulary_version": VOCABULARY_VERSION,
            "not_loaded": [],
            "rows": dict(rows),
        },
    }
