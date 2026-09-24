"""Tests for the structural checks of the concept configuration.

The synthetic configurations below use made-up names and ids above 2,000,000,000, the OMOP range
for local concepts (D-023), so no test depends on a vocabulary bundle. The last tests run the same
checks over the two configuration files of the repository.
"""

import copy
import csv
from pathlib import Path
from typing import Any

import pytest
import yaml

from sinac_truncation.concepts import (
    STCM_COLUMNS,
    check_concept_sets,
    check_source_to_concept_map,
)

CONFIG = Path(__file__).resolve().parents[1] / "config"


def _concept(domain: str, *fields: str) -> dict[str, Any]:
    return {
        "concept_id": 2_000_000_001,
        "concept_name": "Synthetic concept",
        "vocabulary_id": "SYNTH",
        "concept_code": "S-1",
        "domain_id": domain,
        "standard_concept": "S",
        "cdm_fields": list(fields),
    }


VALID: dict[str, Any] = {
    "concepts": {
        "weeks_at_birth": _concept("Measurement", "measurement.measurement_concept_id"),
        "declared_count": _concept("Observation", "observation.observation_concept_id"),
        "provenance": _concept(
            "Type Concept",
            "measurement.measurement_type_concept_id",
            "observation.observation_type_concept_id",
        ),
    },
    "source_vocabularies": {
        "SYNTH_WEEKS": {
            "source_column": "WEEKS",
            "defined_in": "descriptor",
            "cdm_field": "measurement.value_as_number",
            "target_domain_id": None,
        },
        "SYNTH_ANSWER": {
            "source_column": "ANSWER",
            "defined_in": "CATALOGUE",
            "cdm_field": "observation.value_as_concept_id",
            "target_domain_id": "Meas Value",
        },
    },
}


def _row(vocabulary: str, code: str, target: str, target_vocabulary: str) -> dict[str, str]:
    return {
        "source_code": code,
        "source_concept_id": "0",
        "source_vocabulary_id": vocabulary,
        "source_code_description": "SYNTHETIC LABEL",
        "target_concept_id": target,
        "target_vocabulary_id": target_vocabulary,
        "valid_start_date": "2020-01-01",
        "valid_end_date": "2023-12-31",
        "invalid_reason": "",
    }


ROWS = [
    _row("SYNTH_WEEKS", "99", "0", "None"),
    _row("SYNTH_ANSWER", "0", "2000000002", "SYNTH"),
    _row("SYNTH_ANSWER", "00", "0", "None"),
]


def _with(path: tuple[str, ...], value: object) -> dict[str, Any]:
    """A copy of the valid configuration with one value replaced."""
    config = copy.deepcopy(VALID)
    node: Any = config
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    return config


def test_a_consistent_configuration_has_no_problems() -> None:
    assert check_concept_sets(VALID) == []
    assert check_source_to_concept_map(STCM_COLUMNS, ROWS, VALID["source_vocabularies"]) == []


def test_the_domain_decides_the_table() -> None:
    config = _with(("concepts", "weeks_at_birth", "domain_id"), "Observation")
    [problem] = check_concept_sets(config)
    assert "takes Measurement concepts" in problem


def test_observation_refuses_a_domain_that_has_its_own_table() -> None:
    config = _with(("concepts", "declared_count", "domain_id"), "Measurement")
    [problem] = check_concept_sets(config)
    assert "belongs in its own table" in problem


def test_type_fields_take_type_concepts_only() -> None:
    config = _with(("concepts", "provenance", "domain_id"), "Observation")
    problems = check_concept_sets(config)
    assert len(problems) == 2
    assert all("takes Type Concept concepts" in problem for problem in problems)


@pytest.mark.parametrize("key", ["concept_name", "vocabulary_id", "concept_code", "domain_id"])
def test_every_concept_carries_what_it_was_looked_up_with(key: str) -> None:
    config = _with(("concepts", "declared_count", key), "")
    assert f"{key} is missing" in " ".join(check_concept_sets(config))


@pytest.mark.parametrize("value", [0, -1, "4260747", True, None])
def test_concept_id_must_be_a_positive_integer(value: object) -> None:
    config = _with(("concepts", "declared_count", "concept_id"), value)
    [problem] = check_concept_sets(config)
    assert "concept_id must be a positive integer" in problem


def test_a_non_standard_concept_is_reported() -> None:
    config = _with(("concepts", "declared_count", "standard_concept"), None)
    [problem] = check_concept_sets(config)
    assert "standard_concept must be 'S'" in problem


@pytest.mark.parametrize("fields", [[], "measurement.measurement_concept_id", ["measurement"]])
def test_cdm_fields_must_list_table_fields(fields: object) -> None:
    config = _with(("concepts", "weeks_at_birth", "cdm_fields"), fields)
    assert check_concept_sets(config) != []


def test_a_source_vocabulary_id_fits_the_cdm_column() -> None:
    config = copy.deepcopy(VALID)
    config["source_vocabularies"]["SYNTH_TOO_LONG_FOR_CDM"] = VALID["source_vocabularies"][
        "SYNTH_WEEKS"
    ]
    [problem] = check_concept_sets(config)
    assert "longer than 20 characters" in problem


@pytest.mark.parametrize(
    ("path", "value", "expected"),
    [
        (("concepts",), {}, "concepts: missing or empty"),
        (("source_vocabularies",), None, "source_vocabularies: missing or empty"),
        (("concepts", "declared_count"), "4260747", "is not a mapping"),
        (("source_vocabularies", "SYNTH_WEEKS"), [], "is not a mapping"),
        (("source_vocabularies", "SYNTH_WEEKS", "source_column"), "", "source_column is missing"),
        (("source_vocabularies", "SYNTH_WEEKS", "defined_in"), None, "defined_in is missing"),
        (("source_vocabularies", "SYNTH_WEEKS", "cdm_field"), "value", "not a table.field"),
        (("source_vocabularies", "SYNTH_ANSWER", "target_domain_id"), 7, "must be text"),
    ],
)
def test_each_broken_section_is_reported(
    path: tuple[str, ...], value: object, expected: str
) -> None:
    problems = check_concept_sets(_with(path, value))
    assert any(expected in problem for problem in problems), problems


def test_a_description_longer_than_the_cdm_column_is_reported() -> None:
    row = {**_row("SYNTH_ANSWER", "8", "0", "None"), "source_code_description": "X" * 256}
    problems = check_source_to_concept_map(STCM_COLUMNS, [*ROWS, row], VALID["source_vocabularies"])
    assert any("longer than 255" in problem for problem in problems), problems


def test_the_map_must_have_the_cdm_columns_in_order() -> None:
    header = list(STCM_COLUMNS)
    header[0], header[1] = header[1], header[0]
    [problem] = check_source_to_concept_map(header, ROWS, VALID["source_vocabularies"])
    assert "columns must be the CDM's" in problem


def test_leading_zeros_keep_codes_apart() -> None:
    """``0`` and ``00`` are two codes: the map is read as text, never cast (D-033)."""
    problems = check_source_to_concept_map(STCM_COLUMNS, ROWS, VALID["source_vocabularies"])
    assert not any("mapped twice" in problem for problem in problems)


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        (_row("SYNTH_UNKNOWN", "1", "0", "None"), "is not declared"),
        (_row("SYNTH_WEEKS", "99", "0", "None"), "mapped twice"),
        (_row("SYNTH_ANSWER", "8", "0", "LOINC"), "exactly when target_concept_id is 0"),
        (_row("SYNTH_ANSWER", "8", "2000000003", "None"), "exactly when target_concept_id is 0"),
        (_row("SYNTH_WEEKS", "98", "2000000003", "SYNTH"), "its codes must map to 0"),
        (_row("SYNTH_ANSWER", "8", "zero", "None"), "is not a concept_id"),
        (_row("SYNTH_ANSWER", "", "0", "None"), "source_code must have"),
        ({**_row("SYNTH_ANSWER", "8", "0", "None"), "source_concept_id": "7"}, "must be 0"),
        ({**_row("SYNTH_ANSWER", "8", "0", "None"), "valid_end_date": "31/12/2023"}, "YYYY-MM-DD"),
        ({**_row("SYNTH_ANSWER", "8", "0", "None"), "valid_end_date": "2019-12-31"}, "precedes"),
        ({**_row("SYNTH_ANSWER", "8", "0", "None"), "invalid_reason": "X"}, "invalid_reason"),
    ],
)
def test_each_broken_map_row_is_reported(row: dict[str, str], expected: str) -> None:
    problems = check_source_to_concept_map(STCM_COLUMNS, [*ROWS, row], VALID["source_vocabularies"])
    assert any(expected in problem for problem in problems), problems


def test_a_declared_vocabulary_without_rows_is_reported() -> None:
    rows = [row for row in ROWS if row["source_vocabulary_id"] != "SYNTH_WEEKS"]
    [problem] = check_source_to_concept_map(STCM_COLUMNS, rows, VALID["source_vocabularies"])
    assert "'SYNTH_WEEKS' is declared and has no rows" in problem


def test_the_repository_concept_configuration_is_consistent() -> None:
    config = yaml.safe_load((CONFIG / "concept_sets.yml").read_text(encoding="utf-8"))
    assert check_concept_sets(config) == []
    with (CONFIG / "source_to_concept_map.csv").open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        header = reader.fieldnames or []
    assert check_source_to_concept_map(header, rows, config["source_vocabularies"]) == []
