"""Tests for the synthetic source of the smoke run (task 1.9.4): ``sinac_truncation.smoke`` builds
it and ``scripts/smoke_source.py`` writes it.

None of them needs a database: the smoke run itself, ``pipeline.py all --source fixtures``, is a
step of CI. These check that what it loads is what each step expects, so a failure there points at
the pipeline and not at the fixture. The real configuration is read; ``data/`` is never touched.
"""

import csv
import io
import math
import zipfile
from itertools import combinations
from pathlib import Path

import pytest

import download
import load_vocab
import smoke_source
import stage
import validate_concepts
from sinac_truncation import smoke
from sinac_truncation.concepts import LoadedConcept, concept_problems, expected_concepts
from sinac_truncation.etl import SOURCE_COLUMNS
from sinac_truncation.vocabulary import LOADED_TABLES, member_name, version_from_lines

#: The coded columns of a record and the local vocabulary config/source_to_concept_map.csv maps
#: them with.
CODED = {
    "TRIMESTREPRIMERCONSULTA": "SINAC20_TRIMCONS",
    "RESIDEEXTRANJERO": "SINAC20_RESEXT",
    "ESCOLARIDAD": "SINAC20_ESCOL",
    "SEXO": "SINAC20_SEXO",
    "AFILIACION": "SINAC20_AFIL",
}

#: Codes the map lists with target 0 because they mean "not specified" (docs/omop_mapping.md),
#: which would take a record out of the analysis cohort.
UNKNOWN = {"SINAC20_TRIMCONS": {"8", "9"}, "SINAC20_ESCOL": {"0", "88", "99"}}


@pytest.fixture(scope="module")
def config() -> tuple[dict[str, object], list[dict[str, str]]]:
    loaded, rows, problems = validate_concepts.read_config(validate_concepts.CONFIG_DIR)
    assert problems == []
    return dict(loaded), [dict(row) for row in rows]


def test_each_year_has_its_records_with_every_source_column() -> None:
    rows = smoke.records(2021)
    assert len(rows) == smoke.RECORDS_PER_YEAR
    assert all(len(row) == len(SOURCE_COLUMNS) for row in rows)
    assert all(row[0].endswith("/2021") for row in rows)


def test_two_builds_of_a_year_are_the_same() -> None:
    assert smoke.records(2022) == smoke.records(2022)


def test_every_coded_value_is_one_the_map_lists(
    config: tuple[dict[str, object], list[dict[str, str]]],
) -> None:
    _, map_rows = config
    listed = {(row["source_vocabulary_id"], row["source_code"]) for row in map_rows}
    for row in smoke.records(2023):
        values = dict(zip(SOURCE_COLUMNS, row, strict=True))
        for column, vocabulary in CODED.items():
            assert (vocabulary, values[column]) in listed, (column, values[column])
            assert values[column] not in UNKNOWN.get(vocabulary, set())


def test_the_fields_cycle_at_coprime_periods() -> None:
    """No field repeats another, so the adjusted models are not collinear by construction."""
    periods = [
        len(smoke._AGES),
        len(smoke._WEEKS),
        len(smoke._TRIMESTERS),
        len(smoke._STATES),
        len(smoke._EDUCATION),
        len(smoke._INSURANCE),
        smoke._VISIT_PERIOD,
    ]
    assert all(math.gcd(a, b) == 1 for a, b in combinations(periods, 2))


def test_the_records_hold_term_preterm_twins_and_no_care() -> None:
    rows = [dict(zip(SOURCE_COLUMNS, row, strict=True)) for row in smoke.records(2023)]
    weeks = {int(row["EDADGESTACIONAL"]) for row in rows}
    assert min(weeks) < 32 < 37 <= max(weeks)
    assert min(weeks) >= 28, "every record reaches the first landmark"
    assert {row["PRODUCTOEMBARAZO"] for row in rows} == {"1", "2"}
    no_care = [row for row in rows if row["TRIMESTREPRIMERCONSULTA"] == "0"]
    assert no_care and all(row["TOTALCONSULTAS"] == "0" for row in no_care)


def test_a_record_file_is_a_header_and_one_line_per_record() -> None:
    text = smoke.record_csv(smoke.records(2020)).decode("utf-8")
    parsed = list(csv.reader(io.StringIO(text)))
    assert tuple(parsed[0]) == SOURCE_COLUMNS
    assert [tuple(row) for row in parsed[1:]] == smoke.records(2020)


def test_the_vocabulary_passes_every_check_of_validate_concepts(
    config: tuple[dict[str, object], list[dict[str, str]]],
) -> None:
    loaded_config, map_rows = config
    concepts = smoke.vocabulary_rows(loaded_config, map_rows)["concept"]
    columns = smoke.VOCABULARY_COLUMNS["concept"]
    loaded = {}
    for row in concepts:
        fields = dict(zip(columns, row, strict=True))
        loaded[int(fields["concept_id"])] = LoadedConcept(
            concept_id=int(fields["concept_id"]),
            concept_name=fields["concept_name"],
            domain_id=fields["domain_id"],
            vocabulary_id=fields["vocabulary_id"],
            concept_code=fields["concept_code"],
            standard_concept=fields["standard_concept"] or None,
            invalid_reason=fields["invalid_reason"] or None,
        )
    expected = expected_concepts(loaded_config, map_rows)
    assert {concept.concept_id for concept in expected} == set(loaded)
    for concept in expected:
        assert concept_problems(concept, loaded[concept.concept_id]) == [], concept


def test_the_package_has_one_file_per_loaded_table_and_the_declared_version(
    config: tuple[dict[str, object], list[dict[str, str]]],
) -> None:
    members = smoke.vocabulary_members(smoke.vocabulary_rows(*config))
    assert list(members) == [member_name(table) for table in LOADED_TABLES]
    for table in LOADED_TABLES:
        header = members[member_name(table)].decode("utf-8").splitlines()[0]
        assert header.split("\t") == list(smoke.VOCABULARY_COLUMNS[table])
    lines = members[member_name("vocabulary")].decode("utf-8").splitlines()
    assert version_from_lines(lines) == smoke.VOCABULARY_VERSION


def test_the_written_source_matches_its_manifest(tmp_path: Path) -> None:
    written = smoke_source.write(tmp_path / "smoke", (2022, 2023))

    for year in (2022, 2023):
        entry = download.load_entry(written.sources_path, download.record_id(year))
        download.verify_file(download.target_path(entry, written.raw_dir), entry)
    zip_path, _ = stage.verify_zip(2023, raw_dir=written.raw_dir, sources_path=written.sources_path)
    with zipfile.ZipFile(zip_path) as archive:
        assert archive.namelist() == ["Nacimientos_2023.csv"]

    package = load_vocab.read_package(written.sources_path)
    load_vocab.verify_package(written.root / package.file, package)
    assert package.vocabulary_version == smoke.VOCABULARY_VERSION


def test_two_writes_give_the_same_bytes(tmp_path: Path) -> None:
    first = smoke_source.write(tmp_path / "first", (2023,))
    second = smoke_source.write(tmp_path / "second", (2023,))
    assert first.sources_path.read_bytes() == second.sources_path.read_bytes()


def test_a_directory_that_holds_something_is_refused(tmp_path: Path) -> None:
    (tmp_path / "kept.txt").write_text("not the fixture's", encoding="utf-8")
    with pytest.raises(smoke_source.FixtureError, match="not empty"):
        smoke_source.write(tmp_path, (2023,))
    assert (tmp_path / "kept.txt").read_text(encoding="utf-8") == "not the fixture's"
