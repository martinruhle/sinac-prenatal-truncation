"""Structural checks of the concept configuration.

Every concept_id the ETL and the cohort SQL use lives in ``config/concept_sets.yml`` or in
``config/source_to_concept_map.csv``, never in SQL (CLAUDE.md rule 8, D-023). There is no I/O
here (CLAUDE.md rule 6): the caller parses the two files and passes what it read.

These checks need no vocabulary tables, so they run in CI. They verify that every concept carries
the vocabulary, code and domain it was looked up with, that its domain is one the CDM allows in
the fields it is written to, and that every row of the map has the columns of the CDM table and a
declared source vocabulary. Whether a concept exists, is valid and is standard in the bundle that
was actually loaded is checked against the database by ``pipeline.py validate-concepts``
(task 1.4.3).
"""

import re
from collections.abc import Mapping, Sequence
from datetime import date

__all__ = [
    "FIELD_DOMAINS",
    "OWN_TABLE_DOMAINS",
    "STCM_COLUMNS",
    "check_concept_sets",
    "check_source_to_concept_map",
]

#: The columns of SOURCE_TO_CONCEPT_MAP, in the order of the vendored OMOP CDM v5.4 DDL.
STCM_COLUMNS: tuple[str, ...] = (
    "source_code",
    "source_concept_id",
    "source_vocabulary_id",
    "source_code_description",
    "target_concept_id",
    "target_vocabulary_id",
    "valid_start_date",
    "valid_end_date",
    "invalid_reason",
)

#: The domain the CDM requires of each concept field this project writes: the ``fkDomain`` column
#: of ``inst/csv/OMOP_CDMv5.4_Field_Level.csv`` at the vendored commit (sql/ddl/ohdsi/SOURCE.md).
#: Every ``*_type_concept_id`` field requires ``Type Concept`` as well.
FIELD_DOMAINS: Mapping[str, str] = {
    "person.gender_concept_id": "Gender",
    "person.race_concept_id": "Race",
    "person.ethnicity_concept_id": "Ethnicity",
    "measurement.measurement_concept_id": "Measurement",
    "measurement.unit_concept_id": "Unit",
}

#: Domains that have a table of their own. The CDM sends to OBSERVATION the records whose source
#: values map to "any domain besides Condition, Procedure, Drug, Specimen, Measurement or Device"
#: (ETL conventions of the OBSERVATION table), so ``observation_concept_id`` takes none of these.
OWN_TABLE_DOMAINS: frozenset[str] = frozenset(
    {"Condition", "Procedure", "Drug", "Specimen", "Measurement", "Device"}
)

#: A CDM field as the configuration names it: ``table.field``, lower case.
_FIELD = re.compile(r"\A[a-z_]+\.[a-z_]+\Z")

#: The keys every concept entry must carry, copied from Athena when the concept was looked up.
_CONCEPT_TEXT_KEYS = ("concept_name", "vocabulary_id", "concept_code", "domain_id")

#: VOCABULARY.vocabulary_id and SOURCE_TO_CONCEPT_MAP.source_vocabulary_id are varchar(20).
_VOCABULARY_ID_LENGTH = 20

#: SOURCE_TO_CONCEPT_MAP.source_code is varchar(50), source_code_description varchar(255).
_SOURCE_CODE_LENGTH = 50
_DESCRIPTION_LENGTH = 255

#: The vocabulary_id of concept 0, "No matching concept".
_NO_MATCHING_VOCABULARY = "None"


def _required_domain(field: str) -> str | None:
    if field.endswith("_type_concept_id"):
        return "Type Concept"
    return FIELD_DOMAINS.get(field)


def _check_concept(key: str, entry: object) -> list[str]:
    if not isinstance(entry, Mapping):
        return [f"concept {key!r} is not a mapping"]
    problems: list[str] = []
    concept_id = entry.get("concept_id")
    if not isinstance(concept_id, int) or isinstance(concept_id, bool) or concept_id <= 0:
        problems.append(f"concept {key!r}: concept_id must be a positive integer")
    for name in _CONCEPT_TEXT_KEYS:
        value = entry.get(name)
        if not isinstance(value, str) or not value.strip():
            problems.append(f"concept {key!r}: {name} is missing")
    if entry.get("standard_concept") != "S":
        problems.append(f"concept {key!r}: standard_concept must be 'S'")
    fields = entry.get("cdm_fields")
    if not isinstance(fields, list) or not fields:
        problems.append(f"concept {key!r}: cdm_fields must list at least one table.field")
        return problems
    domain = entry.get("domain_id")
    for field in fields:
        if not isinstance(field, str) or not _FIELD.match(field):
            problems.append(f"concept {key!r}: {field!r} is not a table.field name")
            continue
        required = _required_domain(field)
        if required is not None and domain != required:
            problems.append(
                f"concept {key!r}: {field} takes {required} concepts, and this one is {domain}"
            )
        if field == "observation.observation_concept_id" and domain in OWN_TABLE_DOMAINS:
            problems.append(
                f"concept {key!r}: a {domain} concept belongs in its own table, not in OBSERVATION"
            )
    return problems


def _check_source_vocabulary(vocabulary_id: str, entry: object) -> list[str]:
    if not isinstance(entry, Mapping):
        return [f"source vocabulary {vocabulary_id!r} is not a mapping"]
    problems: list[str] = []
    if len(vocabulary_id) > _VOCABULARY_ID_LENGTH:
        problems.append(
            f"source vocabulary {vocabulary_id!r} is longer than {_VOCABULARY_ID_LENGTH} characters"
        )
    for name in ("source_column", "defined_in"):
        value = entry.get(name)
        if not isinstance(value, str) or not value.strip():
            problems.append(f"source vocabulary {vocabulary_id!r}: {name} is missing")
    field = entry.get("cdm_field")
    if not isinstance(field, str) or not _FIELD.match(field):
        problems.append(f"source vocabulary {vocabulary_id!r}: cdm_field is not a table.field name")
    target_domain = entry.get("target_domain_id")
    if target_domain is not None and not isinstance(target_domain, str):
        problems.append(f"source vocabulary {vocabulary_id!r}: target_domain_id must be text")
    return problems


def check_concept_sets(config: Mapping[str, object]) -> list[str]:
    """Check the parsed ``config/concept_sets.yml``.

    Returns:
        One message per problem found; an empty list when the configuration is consistent.
    """
    problems: list[str] = []
    concepts = config.get("concepts")
    if not isinstance(concepts, Mapping) or not concepts:
        problems.append("concepts: missing or empty")
    else:
        for key, entry in concepts.items():
            problems.extend(_check_concept(str(key), entry))
    vocabularies = config.get("source_vocabularies")
    if not isinstance(vocabularies, Mapping) or not vocabularies:
        problems.append("source_vocabularies: missing or empty")
    else:
        for vocabulary_id, entry in vocabularies.items():
            problems.extend(_check_source_vocabulary(str(vocabulary_id), entry))
    return problems


def _parse_date(text: str) -> date | None:
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _check_map_row(
    number: int, row: Mapping[str, str], vocabularies: Mapping[str, object]
) -> list[str]:
    where = f"row {number}"
    problems: list[str] = []
    vocabulary_id = row["source_vocabulary_id"]
    declared = vocabularies.get(vocabulary_id)
    if declared is None:
        problems.append(f"{where}: source vocabulary {vocabulary_id!r} is not declared")
    code = row["source_code"]
    if not code or len(code) > _SOURCE_CODE_LENGTH:
        problems.append(f"{where}: source_code must have 1 to {_SOURCE_CODE_LENGTH} characters")
    if row["source_concept_id"] != "0":
        problems.append(f"{where}: source_concept_id must be 0, SINAC codes have no source concept")
    if len(row["source_code_description"]) > _DESCRIPTION_LENGTH:
        problems.append(f"{where}: source_code_description is longer than {_DESCRIPTION_LENGTH}")
    target = row["target_concept_id"]
    if not target.isdigit():
        problems.append(f"{where}: target_concept_id {target!r} is not a concept_id")
    else:
        unmatched = int(target) == 0
        if unmatched != (row["target_vocabulary_id"] == _NO_MATCHING_VOCABULARY):
            problems.append(
                f"{where}: target_vocabulary_id must be 'None' exactly when target_concept_id is 0"
            )
        no_targets = isinstance(declared, Mapping) and declared.get("target_domain_id") is None
        if no_targets and not unmatched:
            problems.append(
                f"{where}: {vocabulary_id} declares no target domain, so its codes must map to 0"
            )
    start, end = _parse_date(row["valid_start_date"]), _parse_date(row["valid_end_date"])
    if start is None or end is None:
        problems.append(f"{where}: valid_start_date and valid_end_date must be YYYY-MM-DD")
    elif end < start:
        problems.append(f"{where}: valid_end_date precedes valid_start_date")
    if row["invalid_reason"] not in ("", "D", "U"):
        problems.append(f"{where}: invalid_reason must be empty, 'D' or 'U'")
    return problems


def check_source_to_concept_map(
    header: Sequence[str],
    rows: Sequence[Mapping[str, str]],
    source_vocabularies: Mapping[str, object],
) -> list[str]:
    """Check the rows of ``config/source_to_concept_map.csv`` against the declared vocabularies.

    Args:
        header: the column names of the file, in file order.
        rows: every data row, as read by :class:`csv.DictReader` (all values are text, so a code
            such as ``"00"`` keeps its leading zero).
        source_vocabularies: the ``source_vocabularies`` mapping of ``concept_sets.yml``.

    Returns:
        One message per problem found; an empty list when the map is consistent.
    """
    if tuple(header) != STCM_COLUMNS:
        return [f"columns must be the CDM's, in order: {', '.join(STCM_COLUMNS)}"]
    problems: list[str] = []
    seen: set[tuple[str, str]] = set()
    for number, row in enumerate(rows, start=2):
        key = (row["source_vocabulary_id"], row["source_code"])
        if key in seen:
            problems.append(f"row {number}: {key[1]!r} is mapped twice in {key[0]}")
        seen.add(key)
        problems.extend(_check_map_row(number, row, source_vocabularies))
    mapped = {vocabulary_id for vocabulary_id, _ in seen}
    for vocabulary_id in source_vocabularies:
        if vocabulary_id not in mapped:
            problems.append(f"source vocabulary {vocabulary_id!r} is declared and has no rows")
    return problems
