"""Tests for the vocabulary load and for ``validate-concepts``, on a synthetic Athena package.

The package is built here, in code, with the format of the real one (tab-delimited, a header, no
quoting, YYYYMMDD dates) and a few invented rows that carry the values a careless load would
damage: a literal double quote, a backslash sequence, an empty ``standard_concept``. Every id but
0 is above 2,000,000,000, the range for local concepts (D-023). The manifest and the configuration
files are synthetic too; the real ``config/`` and ``data/`` are never touched.

Tests marked ``db`` load into the throwaway schemas of ``conftest.py``, never into ``cdm``.
"""

import datetime
import hashlib
import textwrap
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

import load_vocab
import sql_runner
import validate_concepts
from sinac_truncation.vocabulary import LOADED_TABLES, member_name

#: The CDM v5.4 columns of each loaded table, which the synthetic headers name.
COLUMNS: Mapping[str, tuple[str, ...]] = {
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

QUOTED_NAME = 'Synthetic "quoted" weeks'
"""A name with literal double quotes, as 193 real concept names have."""

BACKSLASH_NAME = "Synthetic answer \\N"
"""``\\N`` is NULL in COPY's text format; here it must stay text."""

VERSION = "v5.0 SYNTH"

ROWS: Mapping[str, tuple[tuple[str, ...], ...]] = {
    "vocabulary": (
        ("None", "OMOP Standardized Vocabularies", "OMOP generated", VERSION, "2000000100"),
        ("SYNTH", "Synthetic vocabulary", "OMOP generated", "", "2000000101"),
    ),
    "domain": (
        ("Measurement", "Measurement", "2000000110"),
        ("Meas Value", "Measurement Value", "2000000111"),
        ("Observation", "Observation", "2000000112"),
        ("Metadata", "Metadata", "2000000113"),
    ),
    "concept_class": (
        ("Answer", "Answer", "2000000120"),
        ("Survey", "Survey", "2000000121"),
        ("Undefined", "Undefined", "2000000122"),
    ),
    "relationship": (
        ("Maps to", "Non-standard to Standard map (OMOP)", "0", "0", "Mapped from", "2000000130"),
        ("Mapped from", "Standard to Non-standard map (OMOP)", "0", "0", "Maps to", "2000000131"),
    ),
    "concept": (
        ("0", "No matching concept", "Metadata", "None", "Undefined", "",
         "No matching concept", "19700101", "20991231", ""),
        ("2000000001", QUOTED_NAME, "Measurement", "SYNTH", "Survey", "S",
         "S-1", "20200101", "20991231", ""),
        ("2000000002", BACKSLASH_NAME, "Meas Value", "SYNTH", "Answer", "S",
         "A-1", "20200101", "20991231", ""),
        ("2000000003", "Synthetic count, not standard", "Observation", "SYNTH", "Survey", "",
         "C-1", "20200101", "20991231", ""),
        ("2000000004", "Synthetic answer, deprecated", "Meas Value", "SYNTH", "Answer", "",
         "A-2", "20200101", "20201231", "D"),
    ),
    "concept_relationship": (
        ("2000000001", "2000000001", "Maps to", "20200101", "20991231", ""),
        ("2000000001", "2000000001", "Mapped from", "20200101", "20991231", ""),
    ),
    "concept_ancestor": (("2000000001", "2000000001", "0", "0"),),
}  # fmt: skip

NOT_LOADED = "CONCEPT_SYNONYM.csv"
PACKAGE = "athena/package.zip"


def table_bytes(table: str, rows: tuple[tuple[str, ...], ...] | None = None) -> bytes:
    lines = [COLUMNS[table], *(ROWS[table] if rows is None else rows)]
    return "".join("\t".join(line) + "\n" for line in lines).encode("utf-8")


def package_members(**replaced: bytes) -> dict[str, bytes]:
    members = {member_name(table): table_bytes(table) for table in LOADED_TABLES}
    members[NOT_LOADED] = b"concept_id\tconcept_synonym_name\tlanguage_concept_id\n"
    members.update(replaced)
    return members


def manifest_text(content: bytes, *, rows: Mapping[str, int], version: str = VERSION) -> str:
    head = textwrap.dedent(
        f"""\
        vocabulary:
          file: "{PACKAGE}"
          size_bytes: {len(content)}
          sha256: "{hashlib.sha256(content).hexdigest()}"
          vocabulary_version: "{version}"
          not_loaded:
            - {NOT_LOADED}
          rows:
        """
    )
    return head + "".join(f"    {table}: {count}\n" for table, count in rows.items())


@dataclass(frozen=True)
class Package:
    """A synthetic package and the manifest that declares it, all under ``tmp_path``."""

    repo_root: Path
    manifest: Path

    @property
    def zip_path(self) -> Path:
        return self.repo_root / PACKAGE


def make_package(
    tmp_path: Path,
    members: Mapping[str, bytes] | None = None,
    *,
    rows: Mapping[str, int] | None = None,
    version: str = VERSION,
) -> Package:
    """Write the ZIP and a manifest that declares it, with the rows of ``ROWS`` by default."""
    zip_path = tmp_path / PACKAGE
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in (members or package_members()).items():
            archive.writestr(name, data)
    counts = {table: len(ROWS[table]) for table in LOADED_TABLES}
    counts.update(rows or {})
    manifest = tmp_path / "sources.yml"
    manifest.write_text(
        manifest_text(zip_path.read_bytes(), rows=counts, version=version), encoding="utf-8"
    )
    return Package(repo_root=tmp_path, manifest=manifest)


def preflight(package: Package) -> None:
    declared = load_vocab.read_package(package.manifest)
    with zipfile.ZipFile(package.zip_path) as archive:
        load_vocab.preflight(archive, declared, COLUMNS)


# --- Before any table is touched: no database ---------------------------------------------------


def test_the_synthetic_package_passes_every_check_that_needs_no_rows(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    load_vocab.verify_package(package.zip_path, load_vocab.read_package(package.manifest))
    preflight(package)


def test_a_package_that_is_not_the_declared_one_is_refused(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    declared = load_vocab.read_package(package.manifest)
    package.zip_path.write_bytes(package.zip_path.read_bytes() + b"\0")
    with pytest.raises(load_vocab.VocabError, match="is not the package config/sources.yml"):
        load_vocab.verify_package(package.zip_path, declared)


def test_a_package_that_is_not_on_disk_is_refused(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    package.zip_path.unlink()
    with pytest.raises(load_vocab.VocabError, match="downloaded by hand"):
        load_vocab.verify_package(package.zip_path, load_vocab.read_package(package.manifest))


def test_a_manifest_without_the_block_is_refused(tmp_path: Path) -> None:
    manifest = tmp_path / "sources.yml"
    manifest.write_text("downloads: []\n", encoding="utf-8")
    with pytest.raises(load_vocab.VocabError, match="no `vocabulary:` block"):
        load_vocab.read_package(manifest)


@pytest.mark.parametrize(
    ("members", "expected"),
    [
        (package_members(**{"NEW_TABLE.csv": b"x\n"}), "NEW_TABLE.csv is in the package"),
        (
            package_members(**{"DOMAIN.csv": b"domain_name\tdomain_id\tdomain_concept_id\n"}),
            "DOMAIN.csv has the columns",
        ),
        (
            package_members(**{"CONCEPT.csv": table_bytes("concept").replace(b"\t", b",")}),
            "CONCEPT.csv has the columns",
        ),
    ],
)
def test_a_package_that_differs_from_its_manifest_is_refused(
    tmp_path: Path, members: dict[str, bytes], expected: str
) -> None:
    with pytest.raises(load_vocab.VocabError, match="nothing was touched") as raised:
        preflight(make_package(tmp_path, members))
    assert expected in str(raised.value)


def test_a_package_of_another_vocabulary_version_is_refused(tmp_path: Path) -> None:
    with pytest.raises(load_vocab.VocabError, match="config/sources.yml declares 'v5.0 OTHER'"):
        preflight(make_package(tmp_path, version="v5.0 OTHER"))


# --- Loading into Postgres: the compose database ----------------------------------------------


def load(package: Package, connection: sql_runner.Connection, schema: str) -> None:
    load_vocab.run(
        connection, schema=schema, sources_path=package.manifest, repo_root=package.repo_root
    )


def fetch(connection: sql_runner.Connection, query: str, *params: object) -> list[tuple[Any, ...]]:
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()


def counts(connection: sql_runner.Connection, schema: str) -> dict[str, int]:
    return {
        table: fetch(connection, f"SELECT count(*) FROM {schema}.{table}")[0][0]
        for table in LOADED_TABLES
    }


EXPECTED_COUNTS = {table: len(ROWS[table]) for table in LOADED_TABLES}


@pytest.mark.db
def test_the_package_is_loaded_as_it_is(
    db_connection: sql_runner.Connection, omop_schema: str, tmp_path: Path
) -> None:
    load(make_package(tmp_path), db_connection, omop_schema)
    assert counts(db_connection, omop_schema) == EXPECTED_COUNTS

    concepts = fetch(
        db_connection,
        f"SELECT concept_id, concept_name, standard_concept, valid_start_date, invalid_reason "
        f"FROM {omop_schema}.concept WHERE concept_id IN (2000000001, 2000000002, 2000000003) "
        "ORDER BY concept_id",
    )
    assert concepts == [
        (2000000001, QUOTED_NAME, "S", datetime.date(2020, 1, 1), None),
        (2000000002, BACKSLASH_NAME, "S", datetime.date(2020, 1, 1), None),
        (2000000003, "Synthetic count, not standard", None, datetime.date(2020, 1, 1), None),
    ]
    assert fetch(
        db_connection,
        f"SELECT vocabulary_version FROM {omop_schema}.vocabulary WHERE vocabulary_id = 'SYNTH'",
    ) == [(None,)]


@pytest.mark.db
def test_two_loads_leave_the_same_tables(
    db_connection: sql_runner.Connection, omop_schema: str, tmp_path: Path
) -> None:
    package = make_package(tmp_path)
    load(package, db_connection, omop_schema)
    first = fetch(db_connection, f"SELECT * FROM {omop_schema}.concept ORDER BY concept_id")
    load(package, db_connection, omop_schema)
    assert fetch(db_connection, f"SELECT * FROM {omop_schema}.concept ORDER BY concept_id") == first
    assert counts(db_connection, omop_schema) == EXPECTED_COUNTS


def _bad_concept(**changes: str) -> tuple[tuple[str, ...], ...]:
    row = dict(zip(COLUMNS["concept"], ROWS["concept"][1], strict=True), **changes)
    return (*ROWS["concept"], tuple(row[column] for column in COLUMNS["concept"]))


@pytest.mark.db
@pytest.mark.parametrize(
    ("members", "rows", "expected"),
    [
        (None, {"concept": 6}, "config/sources.yml 6, file 5, table 5"),
        (
            package_members(
                **{"CONCEPT.csv": table_bytes("concept", _bad_concept(concept_id="2000000009"))}
            ),
            None,
            "config/sources.yml 5, file 6, table 6",
        ),
        (
            package_members(
                **{
                    "CONCEPT.csv": table_bytes(
                        "concept", _bad_concept(concept_id="2000000009", valid_end_date="20201345")
                    )
                }
            ),
            {"concept": 6},
            "COPY refused the package",
        ),
        (
            package_members(
                **{
                    "CONCEPT.csv": table_bytes(
                        "concept",
                        _bad_concept(concept_id="2000000009", concept_name="a \bquoted\b name"),
                    )
                }
            ),
            {"concept": 6},
            "2 backspace bytes",
        ),
    ],
    ids=["manifest-count", "file-count", "bad-date", "quote-byte"],
)
def test_a_failed_load_keeps_the_previous_one(
    db_connection: sql_runner.Connection,
    omop_schema: str,
    tmp_path: Path,
    members: dict[str, bytes] | None,
    rows: dict[str, int] | None,
    expected: str,
) -> None:
    """Every table is emptied inside the transaction that the failure rolls back."""
    load(make_package(tmp_path / "good"), db_connection, omop_schema)
    before = fetch(db_connection, f"SELECT * FROM {omop_schema}.concept ORDER BY concept_id")

    with pytest.raises(load_vocab.VocabError, match="previous load was kept") as raised:
        load(make_package(tmp_path / "bad", members, rows=rows), db_connection, omop_schema)
    assert expected in str(raised.value)

    assert counts(db_connection, omop_schema) == EXPECTED_COUNTS
    assert (
        fetch(db_connection, f"SELECT * FROM {omop_schema}.concept ORDER BY concept_id") == before
    )


CONCEPT_SETS = textwrap.dedent(
    """\
    concepts:
      weeks:
        concept_id: 2000000001
        concept_name: Synthetic weeks
        vocabulary_id: SYNTH
        concept_code: "S-1"
        domain_id: Measurement
        standard_concept: S
        cdm_fields: [measurement.measurement_concept_id]
      declared_count:
        concept_id: 2000000003
        concept_name: Synthetic count
        vocabulary_id: SYNTH
        concept_code: "C-1"
        domain_id: Observation
        standard_concept: S
        cdm_fields: [observation.observation_concept_id]
    source_vocabularies:
      SYNTH_WEEKS:
        source_column: WEEKS
        defined_in: descriptor
        cdm_field: measurement.value_as_number
        target_domain_id: null
      SYNTH_ANSWER:
        source_column: ANSWER
        defined_in: CATALOGUE
        cdm_field: observation.value_as_concept_id
        target_domain_id: Meas Value
    """
)

SOURCE_TO_CONCEPT_MAP = textwrap.dedent(
    """\
    source_code,source_concept_id,source_vocabulary_id,source_code_description,target_concept_id,target_vocabulary_id,valid_start_date,valid_end_date,invalid_reason
    99,0,SYNTH_WEEKS,NOT SPECIFIED,0,None,2020-01-01,2023-12-31,
    1,0,SYNTH_ANSWER,FIRST,2000000002,SYNTH,2020-01-01,2023-12-31,
    2,0,SYNTH_ANSWER,SECOND,2000000004,SYNTH,2020-01-01,2023-12-31,
    """
)


def write_config(tmp_path: Path) -> Path:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / validate_concepts.CONCEPT_SETS).write_text(CONCEPT_SETS, encoding="utf-8")
    (config_dir / validate_concepts.SOURCE_TO_CONCEPT_MAP).write_text(
        SOURCE_TO_CONCEPT_MAP, encoding="utf-8"
    )
    return config_dir


def validate(
    connection: sql_runner.Connection, schema: str, config_dir: Path, manifest: Path
) -> list[str]:
    return validate_concepts.run(
        connection, schema=schema, config_dir=config_dir, sources_path=manifest
    )


@pytest.mark.db
def test_validation_lists_exactly_the_concepts_that_fail(
    db_connection: sql_runner.Connection,
    omop_schema: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    package = make_package(tmp_path)
    load(package, db_connection, omop_schema)
    problems = validate(db_connection, omop_schema, write_config(tmp_path), package.manifest)

    assert problems == [
        "2000000003 concept_sets.yml declared_count: not standard (standard_concept None)",
        "2000000004 source_to_concept_map.csv row 4 (SYNTH_ANSWER '2'): not valid "
        "(invalid_reason 'D')",
        "2000000004 source_to_concept_map.csv row 4 (SYNTH_ANSWER '2'): not standard "
        "(standard_concept None)",
    ]
    report = capsys.readouterr().out
    assert f"vocabulary {VERSION!r}" in report
    assert "5 concept_ids in 5 uses" in report


@pytest.mark.db
def test_validation_reports_a_database_holding_another_version(
    db_connection: sql_runner.Connection, omop_schema: str, tmp_path: Path
) -> None:
    load(make_package(tmp_path / "loaded"), db_connection, omop_schema)
    other = make_package(tmp_path / "declared", version="v5.0 OTHER")
    problems = validate(db_connection, omop_schema, write_config(tmp_path), other.manifest)
    assert problems[0].startswith(f"the database holds vocabulary {VERSION!r}")


@pytest.mark.db
def test_validation_refuses_to_run_without_a_loaded_vocabulary(
    db_connection: sql_runner.Connection, omop_schema: str, tmp_path: Path
) -> None:
    package = make_package(tmp_path)
    load(package, db_connection, omop_schema)
    with db_connection.cursor() as cursor:
        cursor.execute(f"TRUNCATE {omop_schema}.vocabulary")
    with pytest.raises(validate_concepts.NotLoadedError, match="run `pipeline.py vocab`"):
        validate(db_connection, omop_schema, write_config(tmp_path), package.manifest)
