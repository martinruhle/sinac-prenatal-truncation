"""Tests for the ETL of the vertical slice: staging → cdm (task 1.4.4).

The staging tables, the configuration, the manifest and the vocabulary are synthetic, built by
``tests/synthetic.py``: eight 2023 records that each carry a trap, and two 2022 records. The real
``config/`` is only read by the tests that check the real SQL against it, without a database;
``data/`` is never touched.

Tests marked ``db`` load into schemas created for this module and dropped after it, never into
``cdm``, ``staging`` or ``results``.
"""

import csv
import datetime
import re
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import pytest
import yaml

import etl
import pipeline
import sql_runner
from sinac_truncation.etl import (
    SQL_FILES,
    RecordFile,
    Reference,
    concept_keys,
    config_problems,
    etl_reference,
    format_counts,
    person_id,
    release_date,
    source_description,
    vocabulary_ids,
    vocabulary_rows,
    year_problems,
)
from synthetic import (
    AT_LEAST,
    CDM_VERSION,
    CONCEPTS,
    FEMALE,
    FIRST,
    MAP,
    MEXICO,
    NO_CARE,
    NOT_IN_CONCEPT,
    PLURALITY,
    RECORDS_2022,
    RECORDS_2023,
    REGISTRY,
    SHA256,
    SOURCE_VOCABULARIES,
    TRIMESTER,
    VERSION,
    VISITS,
    WEEK,
    WEEKS,
    Source,
    fetch,
    map_csv,
    module_schemas,
    pid,
    prepare_source,
)

CONFIG = Path(__file__).resolve().parents[1] / "config"

# --- The real SQL against the real configuration: no database ---------------------------------


def real_config() -> dict[str, Any]:
    document = yaml.safe_load((CONFIG / "concept_sets.yml").read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def test_the_sql_cites_every_configured_concept_and_vocabulary_and_nothing_else() -> None:
    config = real_config()
    texts = etl.read_sql()
    assert config_problems(texts, config["concepts"], config["source_vocabularies"]) == []
    assert set().union(*(concept_keys(text) for text in texts.values())) == set(config["concepts"])
    assert set().union(*(vocabulary_ids(text) for text in texts.values())) == set(
        config["source_vocabularies"]
    )


def test_no_configured_concept_id_is_written_in_the_sql() -> None:
    """Rule 8: only concept 0, OMOP's "No matching concept", may be written (D-074)."""
    config = real_config()
    ids = {int(entry["concept_id"]) for entry in config["concepts"].values()}
    with (CONFIG / "source_to_concept_map.csv").open(encoding="utf-8", newline="") as handle:
        ids |= {int(row["target_concept_id"]) for row in csv.DictReader(handle)}
    ids.discard(0)
    for name, text in etl.read_sql().items():
        written = [concept for concept in ids if re.search(rf"\b{concept}\b", text)]
        assert written == [], f"sql/etl/{name} writes {written}"


def test_a_concept_or_vocabulary_the_configuration_lacks_is_named() -> None:
    text = "SELECT concept_key = 'absent' WHERE m.source_vocabulary_id = 'SINAC20_NOPE'"
    assert config_problems({"x.sql": text}, {"present": {}}, {"SINAC20_OTHER": {}}) == [
        "sql/etl/x.sql cites the concept 'absent', which config/concept_sets.yml lacks",
        "sql/etl/x.sql joins the vocabulary 'SINAC20_NOPE', which config/concept_sets.yml "
        "does not declare",
    ]


def test_person_id_is_the_record_s_position_in_its_year() -> None:
    """The example of docs/omop_mapping.md rule 7, and the bounds of D-059."""
    assert person_id(2023, 1_234_567) == 231_234_567
    assert person_id(2099, 9_999_999) < 2**31
    for year, row in ((1999, 1), (2100, 1), (2023, 0), (2023, 10_000_000)):
        with pytest.raises(ValueError):
            person_id(year, row)
    assert year_problems([2023, 1999]) == [
        "1999 is outside 2000-2099, the years person_id can hold (D-059)"
    ]


def test_each_local_vocabulary_refers_to_the_file_that_publishes_its_codes() -> None:
    descriptor = Reference(url="http://example.test/descriptores.zip?V=2", version="2")
    catalogues = Reference(url="http://example.test/catalogos.zip?V=1.1", version="1.1")
    rows = vocabulary_rows(
        {
            "SINAC20_EDADGEST": {"source_column": "EDADGESTACIONAL", "defined_in": "descriptor"},
            "SINAC20_PRODEMB": {"source_column": "PRODUCTOEMBARAZO", "defined_in": "CATALOGUE"},
        },
        descriptor=descriptor,
        catalogues=catalogues,
    )
    assert rows == [
        (
            "SINAC20_EDADGEST",
            "SINAC local codes of EDADGESTACIONAL, defined in descriptor",
            descriptor.url,
            "2",
            0,
        ),
        (
            "SINAC20_PRODEMB",
            "SINAC local codes of PRODUCTOEMBARAZO, defined in CATALOGUE",
            catalogues.url,
            "1.1",
            0,
        ),
    ]


def test_cdm_source_names_each_file_and_the_latest_retrieval() -> None:
    files = [
        RecordFile(2023, "http://x.test/n/sinac_2023.zip?V=2024.05.14", "2024.05.14", "a" * 64,
                   "2026-09-20T12:44:57Z"),
        RecordFile(2022, "http://x.test/n/sinac_2022.zip?V=2023.05.23", "2023.05.23", "b" * 64,
                   "2026-09-21T01:00:00Z"),
    ]  # fmt: skip
    assert source_description(files) == (
        f"SINAC record files loaded: 2022: sinac_2022.zip?V=2023.05.23, sha256 {'b' * 64}; "
        f"2023: sinac_2023.zip?V=2024.05.14, sha256 {'a' * 64}"
    )
    assert release_date(files) == datetime.date(2026, 9, 21)
    with pytest.raises(ValueError):
        release_date([])


def test_the_etl_reference_never_carries_credentials() -> None:
    assert (
        etl_reference("https://user:token@github.com/o/r.git\n", "abc123\n", dirty=False)
        == "https://github.com/o/r at commit abc123"
    )
    assert (
        etl_reference("git@github.com:o/r.git", "abc123", dirty=True)
        == "git@github.com:o/r at commit abc123, with uncommitted changes"
    )


def test_the_report_lists_tables_in_load_order_and_rows_first() -> None:
    lines = format_counts(
        [
            (None, "check", "visit_occurrence_rows", 0),
            (2023, "person", "year_of_birth:age", 1),
            (None, "location", "rows", 35),
            (2023, "person", "rows", 1_521_280),
            (2023, "staging", "rows", 1_521_280),
        ]
    )
    assert [line.split()[:3] for line in lines[1:]] == [
        ["2023", "staging", "rows"],
        ["2023", "person", "rows"],
        ["2023", "person", "year_of_birth:age"],
        ["all", "location", "rows"],
        ["all", "check", "visit_occurrence_rows"],
    ]
    assert lines[2].endswith("1,521,280")


def test_pipeline_cdm_takes_years() -> None:
    args = pipeline.build_parser().parse_args(["cdm", "--years", "2022,2023"])
    assert (args.command, args.years) == ("cdm", (2022, 2023))


# --- The synthetic source (tests/synthetic.py) -------------------------------------------------


@pytest.fixture(scope="module")
def schemas(
    db_connection: sql_runner.Connection, ddl_files: Sequence[Path]
) -> Iterator[etl.Schemas]:
    """Schemas of this module's own, with the vendored DDL applied, dropped after the module."""
    with module_schemas(db_connection, ddl_files, "test_etl") as names:
        yield names


@pytest.fixture
def source(db_connection: sql_runner.Connection, schemas: etl.Schemas, tmp_path: Path) -> Source:
    return prepare_source(db_connection, schemas, tmp_path)


# --- Loading: the compose database --------------------------------------------------------------


@pytest.mark.db
def test_each_trap_lands_as_the_mapping_says(source: Source) -> None:
    source.run()

    assert source.table("person", "person_id") == [
        # person_id, gender, year, month, day, birth_datetime, race, ethnicity, location_id,
        # provider, care_site, person_source_value, then the six gender/race/ethnicity sources.
        (pid(1), FEMALE, 1995, 5, 2, None, 0, 0, 3, None, None, "2023:1", *[None] * 6),
        (pid(2), FEMALE, 1995, 5, 2, None, 0, 0, 3, None, None, "2023:2", *[None] * 6),
        (pid(3), FEMALE, 2000, 11, 11, None, 0, 0, 2, None, None, "2023:3", *[None] * 6),
        (pid(4), FEMALE, 1993, None, None, None, 0, 0, 6, None, None, "2023:4", *[None] * 6),
        (pid(5), FEMALE, 1990, None, None, None, 0, 0, 1, None, None, "2023:5", *[None] * 6),
        (pid(7), FEMALE, 1998, None, None, None, 0, 0, 5, None, None, "2023:7", *[None] * 6),
        (pid(8), FEMALE, 1996, 2, 29, None, 0, 0, 4, None, None, "2023:8", *[None] * 6),
    ]

    assert fetch(
        source.connection,
        f"SELECT location_id, state, location_source_value, country_concept_id, "
        f"country_source_value FROM {source.schemas.cdm}.location ORDER BY location_id",
    ) == [
        (1, None, "1|88", 0, "1"),
        (2, None, "2|00", MEXICO, "2"),
        (3, "09", "2|09", MEXICO, "2"),
        (4, "31", "2|31", MEXICO, "2"),
        (5, None, "3|9", 0, "3"),
        (6, None, "88|00", 0, "88"),
    ]

    d = datetime.date
    weeks, plural = "EDADGESTACIONAL", "PRODUCTOEMBARAZO"
    assert fetch(
        source.connection,
        f"SELECT measurement_id, person_id, measurement_concept_id, measurement_date, "
        f"measurement_type_concept_id, operator_concept_id, value_as_number, unit_concept_id, "
        f"measurement_source_value, measurement_source_concept_id, value_source_value "
        f"FROM {source.schemas.cdm}.measurement ORDER BY measurement_id",
    ) == [
        (1, pid(1), WEEKS, d(2023, 3, 15), REGISTRY, None, 39, WEEK, weeks, 0, "39"),
        (2, pid(1), PLURALITY, d(2023, 3, 15), REGISTRY, None, 1, None, plural, 0, "1"),
        (3, pid(2), WEEKS, d(2023, 3, 15), REGISTRY, None, 39, WEEK, weeks, 0, "39"),
        (4, pid(2), PLURALITY, d(2023, 3, 15), REGISTRY, None, 1, None, plural, 0, "1"),
        (5, pid(3), WEEKS, d(2023, 6, 20), REGISTRY, None, 12, WEEK, weeks, 0, "12"),
        (6, pid(3), PLURALITY, d(2023, 6, 20), REGISTRY, AT_LEAST, 3, None, plural, 0, "3"),
        (7, pid(4), WEEKS, d(2023, 1, 1), REGISTRY, None, None, WEEK, weeks, 0, "99"),
        (8, pid(4), PLURALITY, d(2023, 1, 1), REGISTRY, None, None, None, plural, 0, "0"),
        (9, pid(5), WEEKS, d(2023, 12, 31), REGISTRY, None, None, WEEK, weeks, 0, None),
        (10, pid(5), PLURALITY, d(2023, 12, 31), REGISTRY, None, 1, None, plural, 0, "1"),
        (11, pid(7), WEEKS, d(2023, 5, 5), REGISTRY, None, None, WEEK, weeks, 0, "ab"),
        (12, pid(7), PLURALITY, d(2023, 5, 5), REGISTRY, None, None, None, plural, 0, "7"),
        (13, pid(8), WEEKS, d(2023, 2, 28), REGISTRY, None, 34, WEEK, weeks, 0, "34"),
        (14, pid(8), PLURALITY, d(2023, 2, 28), REGISTRY, None, 2, None, plural, 0, "2"),
    ]

    visits, trim = "TOTALCONSULTAS", "TRIMESTREPRIMERCONSULTA"
    assert fetch(
        source.connection,
        f"SELECT observation_id, person_id, observation_concept_id, observation_date, "
        f"observation_type_concept_id, value_as_number, value_as_concept_id, "
        f"observation_source_value, observation_source_concept_id, value_source_value "
        f"FROM {source.schemas.cdm}.observation ORDER BY observation_id",
    ) == [
        (1, pid(1), VISITS, d(2023, 3, 15), REGISTRY, 8, None, visits, 0, "8"),
        (2, pid(1), TRIMESTER, d(2023, 3, 15), REGISTRY, None, FIRST, trim, 0, "1"),
        (3, pid(2), VISITS, d(2023, 3, 15), REGISTRY, 8, None, visits, 0, "8"),
        (4, pid(2), TRIMESTER, d(2023, 3, 15), REGISTRY, None, FIRST, trim, 0, "1"),
        (5, pid(3), VISITS, d(2023, 6, 20), REGISTRY, 45, None, visits, 0, "45"),
        (6, pid(3), TRIMESTER, d(2023, 6, 20), REGISTRY, None, NO_CARE, trim, 0, "0"),
        (7, pid(4), VISITS, d(2023, 1, 1), REGISTRY, None, None, visits, 0, "99"),
        (8, pid(4), TRIMESTER, d(2023, 1, 1), REGISTRY, None, 0, trim, 0, "8"),
        (9, pid(5), VISITS, d(2023, 12, 31), REGISTRY, None, None, visits, 0, None),
        (10, pid(5), TRIMESTER, d(2023, 12, 31), REGISTRY, None, None, trim, 0, None),
        (11, pid(7), VISITS, d(2023, 5, 5), REGISTRY, None, None, visits, 0, " 7"),
        (12, pid(7), TRIMESTER, d(2023, 5, 5), REGISTRY, None, 0, trim, 0, "5"),
        (13, pid(8), VISITS, d(2023, 2, 28), REGISTRY, 0, None, visits, 0, "0"),
        (14, pid(8), TRIMESTER, d(2023, 2, 28), REGISTRY, None, FIRST, trim, 0, "1"),
    ]

    vocabularies = fetch(
        source.connection,
        f"SELECT vocabulary_id, vocabulary_reference, vocabulary_version, vocabulary_concept_id "
        f"FROM {source.schemas.cdm}.vocabulary WHERE vocabulary_id LIKE 'SINAC20%%' "
        "ORDER BY vocabulary_id",
    )
    descriptor = ("http://example.test/nacimientos/descriptores.zip?V=2026.07.09", "2026.07.09")
    catalogues = ("http://example.test/nacimientos/catalogos.zip?V=1.1", "1.1")
    assert vocabularies == [
        ("SINAC20_EDAD", *descriptor, 0),
        ("SINAC20_EDADGEST", *descriptor, 0),
        ("SINAC20_ENTRES", *catalogues, 0),
        ("SINAC20_FECHANACMAD", *descriptor, 0),
        ("SINAC20_PRODEMB", *catalogues, 0),
        ("SINAC20_RESEXT", *catalogues, 0),
        ("SINAC20_TOTCONS", *descriptor, 0),
        ("SINAC20_TRIMCONS", *catalogues, 0),
    ]

    assert fetch(
        source.connection,
        f"SELECT source_description, source_documentation_reference, cdm_etl_reference, "
        f"source_release_date, cdm_release_date, cdm_version, cdm_version_concept_id, "
        f"vocabulary_version FROM {source.schemas.cdm}.cdm_source",
    ) == [
        (
            f"SINAC record files loaded: 2023: sinac_2023.zip?V=2024.05.14, sha256 {SHA256[2023]}",
            "http://example.test/nacimientos.html",
            "https://example.test/repo at commit synthetic",
            d(2026, 9, 20),
            datetime.date.today(),
            "v5.4.3",
            CDM_VERSION,
            VERSION,
        )
    ]


@pytest.mark.db
def test_the_observation_period_is_the_delivery_day(source: Source) -> None:
    """D-062: one day, the delivery, whatever the gestational age; every event on it (D-063)."""
    source.run()
    deliveries = {
        pid(row): datetime.datetime.strptime(str(values[0]), "%d/%m/%Y").date()
        for row, values in enumerate(RECORDS_2023, start=1)
        if row != 6
    }
    assert source.table("observation_period", "observation_period_id") == [
        (person, person, day, day, REGISTRY) for person, day in sorted(deliveries.items())
    ]
    events = fetch(
        source.connection,
        f"SELECT person_id, measurement_date FROM {source.schemas.cdm}.measurement "
        f"UNION ALL SELECT person_id, observation_date FROM {source.schemas.cdm}.observation",
    )
    assert len(events) == 4 * len(deliveries)
    assert all(day == deliveries[person] for person, day in events)


EXPECTED_2023_COUNTS: dict[tuple[str, str], int] = {
    ("staging", "rows"): 8,
    ("person", "rows"): 7,
    ("person", "not_loaded:no_year_of_birth"): 1,
    ("person", "year_of_birth:mother_date"): 4,
    ("person", "year_of_birth:age"): 3,
    ("observation_period", "rows"): 7,
    ("measurement", "rows"): 14,
    ("measurement", "gestational_age_at_birth:value"): 4,
    ("measurement", "gestational_age_at_birth:code_to_null"): 1,
    ("measurement", "gestational_age_at_birth:not_integer"): 1,
    ("measurement", "gestational_age_at_birth:blank"): 1,
    ("measurement", "birth_plurality:value"): 5,
    ("measurement", "birth_plurality:code_to_null"): 1,
    ("measurement", "birth_plurality:not_in_catalogue"): 1,
    ("measurement", "birth_plurality:blank"): 0,
    ("measurement", "birth_plurality:at_least"): 1,
    ("observation", "rows"): 14,
    ("observation", "prenatal_visits_count:value"): 4,
    ("observation", "prenatal_visits_count:code_to_null"): 1,
    ("observation", "prenatal_visits_count:not_integer"): 1,
    ("observation", "prenatal_visits_count:blank"): 1,
    ("observation", "first_prenatal_visit_trimester:code_to_concept"): 4,
    ("observation", "first_prenatal_visit_trimester:code_to_0"): 1,
    ("observation", "first_prenatal_visit_trimester:not_in_catalogue"): 1,
    ("observation", "first_prenatal_visit_trimester:blank"): 1,
    ("location", "country_concept_id:code_to_concept"): 4,
    ("location", "country_concept_id:code_to_0"): 2,
    ("location", "country_concept_id:not_in_catalogue"): 1,
    ("location", "country_concept_id:blank"): 0,
    ("location", "state:value"): 3,
    ("location", "state:code_to_null"): 3,
    ("location", "state:not_two_digits"): 1,
    ("location", "state:blank"): 0,
}

CHECKS = (
    "concept_not_in_vocabulary:person",
    "concept_not_in_vocabulary:observation_period",
    "concept_not_in_vocabulary:measurement",
    "concept_not_in_vocabulary:observation",
    "concept_not_in_vocabulary:location",
    "concept_not_in_vocabulary:cdm_source",
    "concept_not_in_vocabulary:source_to_concept_map",
    "orphan_person:observation_period",
    "orphan_person:measurement",
    "orphan_person:observation",
    "orphan_location:person",
    "person_without_one_observation_period",
    "person_without_two_measurements",
    "person_without_two_observations",
    "observation_period_not_the_delivery_day",
    "event_outside_observation_period:measurement",
    "event_outside_observation_period:observation",
    "visit_occurrence_rows",
    "vocabulary_not_registered",
    "person_not_matched_to_staging",
    "staging_rows_not_load_counts",
    "cdm_source_rows_not_one",
)


@pytest.mark.db
def test_counts_per_step_are_recorded(source: Source) -> None:
    returned = source.run()
    expected: dict[tuple[int | None, str, str], int] = {
        (2023, table, rule): count for (table, rule), count in EXPECTED_2023_COUNTS.items()
    }
    expected |= {
        (None, "location", "rows"): 6,
        (None, "vocabulary", "rows"): len(SOURCE_VOCABULARIES),
        (None, "source_to_concept_map", "rows"): len(MAP),
        (None, "cdm_source", "rows"): 1,
    }
    expected |= {(None, "check", name): 0 for name in CHECKS}
    recorded = {(year, table, rule): count for year, table, rule, count in source.counts()}
    assert recorded == expected
    assert sorted(returned, key=str) == sorted(source.counts(), key=str)


@pytest.mark.db
def test_person_plus_not_loaded_equals_staged(source: Source) -> None:
    """The unit of analysis (D-051): one PERSON per staged record, less those without a year of
    birth for the mother (D-060)."""
    source.run((2022, 2023))
    counts = {(year, table, rule): count for year, table, rule, count in source.counts()}
    for year, records in ((2022, RECORDS_2022), (2023, RECORDS_2023)):
        staged = counts[(year, "staging", "rows")]
        assert staged == len(records)
        assert (
            counts[(year, "person", "rows")]
            + counts[(year, "person", "not_loaded:no_year_of_birth")]
            == staged
        )


@pytest.mark.db
def test_two_runs_leave_identical_tables_and_counts(source: Source) -> None:
    source.run()
    first = source.snapshot()
    source.run()
    assert source.snapshot() == first


@pytest.mark.db
def test_an_invalid_delivery_date_stops_and_keeps_the_previous_load(source: Source) -> None:
    source.run()
    before = source.snapshot()

    source.stage(2023, (*RECORDS_2023, ("31/02/2023", *RECORDS_2023[0][1:])))
    with pytest.raises(etl.EtlError, match="the previous load was kept") as raised:
        source.run()
    assert "1 record(s) cannot be loaded" in str(raised.value)
    assert "2023 source_row 9: FECHANACIMIENTO '31/02/2023' is not a valid dd/mm/yyyy date" in str(
        raised.value
    )
    assert source.snapshot() == before


def _map_with_a_target_not_in_concept(source: Source) -> None:
    rows = [(v, c, NOT_IN_CONCEPT if (v, c) == ("SINAC20_TRIMCONS", "3") else t) for v, c, t in MAP]
    (source.config_dir / "source_to_concept_map.csv").write_text(map_csv(rows), encoding="utf-8")


def _a_visit(source: Source) -> None:
    with source.connection.cursor() as cursor:
        cursor.execute(
            f"INSERT INTO {source.schemas.cdm}.visit_occurrence (visit_occurrence_id, person_id, "
            "visit_concept_id, visit_start_date, visit_end_date, visit_type_concept_id) "
            "VALUES (1, %s, 0, '2023-03-15', '2023-03-15', %s)",
            (pid(1), REGISTRY),
        )


@pytest.mark.db
@pytest.mark.parametrize(
    ("damage", "check"),
    [
        (_map_with_a_target_not_in_concept, "concept_not_in_vocabulary:source_to_concept_map: 1"),
        (_a_visit, "visit_occurrence_rows: 1"),
    ],
    ids=["target-not-in-concept", "a-visit"],
)
def test_a_failing_check_keeps_the_previous_load(source: Source, damage: Any, check: str) -> None:
    source.run()
    before = source.snapshot()

    damage(source)
    with pytest.raises(etl.EtlError, match="the previous load was kept") as raised:
        source.run()
    assert check in str(raised.value)
    assert source.snapshot() == before


@pytest.mark.db
def test_years_select_what_the_cdm_holds(source: Source) -> None:
    source.run((2022, 2023))
    persons = [row[0] for row in source.table("person", "person_id")]
    assert persons[:2] == [pid(1, 2022), pid(2, 2022)] == [220_000_001, 220_000_002]
    assert len(persons) == 2 + 7
    assert len(source.table("location", "location_id")) == 7

    source.run((2023,))
    persons = [row[0] for row in source.table("person", "person_id")]
    assert persons[0] == pid(1) and len(persons) == 7
    assert {year for year, *_ in source.counts()} == {None, 2023}


def _drop_staging(source: Source) -> None:
    with source.connection.cursor() as cursor:
        cursor.execute(f"DROP TABLE {source.schemas.staging}.sinac_2023")


def _another_file_staged(source: Source) -> None:
    with source.connection.cursor() as cursor:
        cursor.execute(
            f"UPDATE {source.schemas.staging}.load_counts SET source_sha256 = %s "
            "WHERE source_year = 2023",
            ("d" * 64,),
        )


def _another_vocabulary(source: Source) -> None:
    with source.connection.cursor() as cursor:
        cursor.execute(
            f"UPDATE {source.schemas.cdm}.vocabulary SET vocabulary_version = 'v5.0 OTHER' "
            "WHERE vocabulary_id = 'None'"
        )


@pytest.mark.db
@pytest.mark.parametrize(
    ("damage", "message"),
    [
        (_drop_staging, "run `pipeline.py stage --years 2023` first"),
        (_another_file_staged, "was not staged from the file config/sources.yml records"),
        (_another_vocabulary, "run `pipeline.py vocab` first"),
    ],
    ids=["no-staging", "other-sha256", "other-vocabulary"],
)
def test_what_the_load_needs_is_checked_before_anything_is_touched(
    source: Source, damage: Any, message: str
) -> None:
    source.run()
    damage(source)
    before = source.snapshot()
    with pytest.raises(etl.EtlError, match=re.escape(message)):
        source.run()
    assert source.snapshot() == before


def test_a_configuration_without_a_concept_the_sql_cites_is_refused(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    concepts = {key: entry for key, entry in CONCEPTS.items() if key != "week"}
    (config_dir / "concept_sets.yml").write_text(
        yaml.safe_dump({"concepts": concepts, "source_vocabularies": SOURCE_VOCABULARIES}),
        encoding="utf-8",
    )
    (config_dir / "source_to_concept_map.csv").write_text(map_csv(MAP), encoding="utf-8")
    with pytest.raises(etl.EtlError, match="cites the concept 'week'"):
        etl.read_inputs(
            (2023,), etl.read_sql(), config_dir=config_dir, sources_path=tmp_path / "none.yml"
        )


def test_every_sql_file_of_the_etl_exists() -> None:
    assert set(etl.read_sql()) == set(SQL_FILES)
    assert sorted(path.name for path in etl.SQL_DIR.glob("*.sql")) == sorted(SQL_FILES)
