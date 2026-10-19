"""Tests for publishing the results of a run under ``results/`` (task 1.5.2, issue #59, D-014,
D-080, D-122).

The pure tests build the text of the files from small hand-written tables. Tests marked ``db`` load
the synthetic source of ``tests/synthetic.py`` through the ETL into schemas of this module's own,
dropped after it, and publish into a temporary folder, never into ``results/``. The profile of the
excluded records is checked against counts written by hand from the records, never measured on the
database.
"""

import hashlib
import json
import re
import subprocess
from collections.abc import Iterator, Sequence
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

import etl
import pipeline
import publish
import sql_runner
from sinac_truncation.cohorts import AttritionStep
from sinac_truncation.publish import (
    ATTRITION_COLUMNS,
    OUTPUT_TABLES,
    Code,
    Column,
    OutputTable,
    PublishedFile,
    PublishedSource,
    manifest_json,
    read_table_csv,
    sorted_rows,
    table_csv,
)
from synthetic import RECORDS_2023, SHA256, VERSION, Source, fetch, module_schemas, prepare_source

NOW = datetime(2026, 9, 29, 12, 0, 5, tzinfo=UTC)

TABLES = {table.file: table for table in OUTPUT_TABLES}
ATTRITION = TABLES["attrition.csv"]

#: A small attrition table in the shape of ``results.attrition``: step 0 excludes nobody, so its
#: ``excluded`` is None, and so is its kind; one description holds a comma and a double quote.
STEPS: tuple[AttritionStep, ...] = (
    AttritionStep(1, 2023, 0, None, "Records in the files of the study period", 15, None),
    AttritionStep(1, 2023, 1, "data model", "Mother's year of birth known", 15, 0),
    AttritionStep(1, 2023, 2, "coverage", 'Born, in "quotes"', 12, 3),
)

CSV_TEXT = (
    "cohort_definition_id,source_year,step,kind,description,remaining,excluded\n"
    "1,2023,0,,Records in the files of the study period,15,\n"
    "1,2023,1,data model,Mother's year of birth known,15,0\n"
    '1,2023,2,coverage,"Born, in ""quotes""",12,3\n'
)


# --- The text of the files ------------------------------------------------------------------------


def test_the_five_files_hold_the_columns_of_the_protocol() -> None:
    assert {table.file: table.header for table in OUTPUT_TABLES} == {
        "attrition.csv": (
            "cohort_definition_id",
            "source_year",
            "step",
            "kind",
            "description",
            "remaining",
            "excluded",
        ),
        "exposure_distribution.csv": (
            "source",
            "cohort_definition_id",
            "period",
            "outcome_cutoff",
            "measure",
            "variant",
            "level",
            "outcome",
            "births",
        ),
        "estimates.csv": (
            "source",
            "cohort_definition_id",
            "period",
            "outcome_cutoff",
            "measure",
            "variant",
            "level",
            "reference",
            "model",
            "stratum_variable",
            "stratum_value",
            "births",
            "preterm_births",
            "odds_ratio",
            "lower_limit",
            "upper_limit",
        ),
        "truncation_share.csv": (
            "cohort_definition_id",
            "measure",
            "variant",
            "level",
            "scenario",
            "reference",
            "observed_odds_ratio",
            "observed_lower",
            "observed_upper",
            "simulated_odds_ratio",
            "observed_risk_difference",
            "simulated_risk_difference",
            "share",
        ),
        "excluded_profile.csv": (
            "cohort_definition_id",
            "step",
            "subject_group",
            "births",
            "preterm_percent",
            "first_trimester_start_percent",
            "no_prenatal_care_percent",
        ),
    }


def test_attrition_csv_keeps_the_columns_of_the_table() -> None:
    assert ATTRITION.header == ATTRITION_COLUMNS


def test_each_key_names_columns_of_its_table() -> None:
    for table in OUTPUT_TABLES:
        assert set(table.key) <= set(table.header), table.file


def test_the_csv_has_one_row_per_step_in_order_with_lf_line_ends() -> None:
    assert table_csv(ATTRITION, list(reversed(STEPS))) == CSV_TEXT


def test_the_csv_reads_back_to_the_same_rows() -> None:
    assert read_table_csv(ATTRITION, table_csv(ATTRITION, STEPS)) == [tuple(s) for s in STEPS]


def test_a_csv_with_another_header_is_refused() -> None:
    with pytest.raises(ValueError, match="header"):
        read_table_csv(ATTRITION, CSV_TEXT.replace("remaining", "kept", 1))


#: A table with one column of each type: a text that may be empty, a count, and a float and a
#: percentage that may be NULL.
SAMPLE = OutputTable(
    file="sample.csv",
    table="sample",
    columns=(
        Column("level", str),
        Column("births", int),
        Column("odds_ratio", float, nullable=True),
        Column("percent", Decimal, nullable=True),
    ),
    key=("level",),
)


def test_numbers_are_written_to_read_back_exactly() -> None:
    rows = [
        ("a", 3, 0.1 + 0.2, Decimal("55.56")),
        ("", 0, None, None),
        ("b", 1, 2.0, Decimal("0.00")),
    ]
    text = table_csv(SAMPLE, rows)
    assert text == (
        "level,births,odds_ratio,percent\n,0,,\na,3,0.30000000000000004,55.56\nb,1,2.0,0.00\n"
    )
    assert read_table_csv(SAMPLE, text) == sorted_rows(SAMPLE, rows)


def test_rows_are_ordered_by_code_point_whatever_the_collation() -> None:
    rows = [("b", 1, None, None), ("a", 1, None, None), ("Z", 1, None, None), ("8+", 1, None, None)]
    assert [row[0] for row in sorted_rows(SAMPLE, rows)] == ["8+", "Z", "a", "b"]


@pytest.mark.parametrize(
    ("row", "problem"),
    [
        ((None, 1, None, None), "NULL in a column that holds none"),
        (("a", 1, 1, None), "1 is not a float"),
        (("a", True, None, None), "True is not a int"),
        (("a", 1, float("inf"), None), "inf is not a finite number"),
        (("a", 1, None, Decimal("NaN")), "is not a finite number"),
        (("a", 1, None), "a row has 3 values, not 4"),
    ],
    ids=["null", "type", "bool", "infinite", "nan", "width"],
)
def test_a_value_the_csv_cannot_hold_exactly_is_refused(
    row: tuple[object, ...], problem: str
) -> None:
    with pytest.raises(ValueError, match=re.escape(problem)):
        table_csv(SAMPLE, [row])  # type: ignore[list-item]


def test_an_empty_text_where_null_is_allowed_is_refused() -> None:
    with pytest.raises(ValueError, match="would read back as NULL"):
        table_csv(ATTRITION, [AttritionStep(1, 2023, 1, "", "loaded", 1, 0)])


MANIFEST_ARGS = {
    "code": Code(repository="https://github.com/o/r", commit="abc123"),
    "years": (2023, 2022),
    "sources": (
        PublishedSource(id="dgis_sinac_2022", version="2023.05.23", sha256="b" * 64),
        PublishedSource(id="dgis_sinac_2023", version="2024.05.14", sha256="a" * 64),
    ),
    "vocabulary_version": "v5.0 29-AUG-26",
    "vocabulary_sha256": "c" * 64,
    "files": (PublishedFile(name="attrition.csv", sha256="d" * 64),),
}


def test_the_manifest_names_the_code_the_sources_and_each_file() -> None:
    text = manifest_json(generated_at=NOW, **MANIFEST_ARGS)  # type: ignore[arg-type]
    assert text.endswith("}\n")
    assert json.loads(text) == {
        "generated_at": "2026-09-29T12:00:05Z",
        "code": {"repository": "https://github.com/o/r", "commit": "abc123"},
        "period": [2022, 2023],
        "sources": [
            {"id": "dgis_sinac_2022", "version": "2023.05.23", "sha256": "b" * 64},
            {"id": "dgis_sinac_2023", "version": "2024.05.14", "sha256": "a" * 64},
        ],
        "vocabulary": {"version": "v5.0 29-AUG-26", "sha256": "c" * 64},
        "files": [{"name": "attrition.csv", "sha256": "d" * 64}],
    }


MEXICO_CITY = timezone(timedelta(hours=-6))


@pytest.mark.parametrize(
    "generated_at",
    [datetime(2026, 9, 29, 12, 0, 5), datetime(2026, 9, 29, 6, 0, 5, tzinfo=MEXICO_CITY)],
    ids=["naive", "not-utc"],
)
def test_a_generation_time_that_is_not_utc_is_refused(generated_at: datetime) -> None:
    with pytest.raises(ValueError, match="UTC"):
        manifest_json(generated_at=generated_at, **MANIFEST_ARGS)  # type: ignore[arg-type]


def test_pipeline_publish_takes_years() -> None:
    args = pipeline.build_parser().parse_args(["publish", "--years", "2023"])
    assert (args.command, args.years) == ("publish", (2023,))


# --- The commit a run publishes from --------------------------------------------------------------


def git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.test", *args],
        check=True,
        capture_output=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repository with one commit, a remote that carries credentials and a ``results/`` folder."""
    root = tmp_path / "repo"
    (root / "results").mkdir(parents=True)
    (root / "results" / ".gitkeep").write_text("", encoding="utf-8")
    (root / "code.py").write_text("x = 1\n", encoding="utf-8")
    git(root, "init", "--quiet")
    git(root, "remote", "add", "origin", "https://user:token@github.com/o/r.git")
    git(root, "add", ".")
    git(root, "commit", "--quiet", "-m", "first")
    return root


def head(repo: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()


def test_the_code_is_the_commit_and_the_remote_without_credentials(repo: Path) -> None:
    assert publish.current_code(repo) == Code(
        repository="https://github.com/o/r", commit=head(repo)
    )


def test_changes_under_results_do_not_count(repo: Path) -> None:
    (repo / "results" / "attrition.csv").write_text("new\n", encoding="utf-8")
    (repo / "results" / ".gitkeep").write_text("changed\n", encoding="utf-8")
    assert publish.current_code(repo).commit == head(repo)


@pytest.mark.parametrize("change", ["modified", "untracked"])
def test_a_change_outside_results_is_refused(repo: Path, change: str) -> None:
    name = "code.py" if change == "modified" else "notes.txt"
    (repo / name).write_text("x = 2\n", encoding="utf-8")
    with pytest.raises(publish.PublishError, match="commit them first"):
        publish.current_code(repo)


# --- Publishing a run on the compose database -----------------------------------------------------

#: The code ``Source.run`` says the synthetic CDM was loaded from.
CODE = Code(repository="https://example.test/repo", commit="synthetic")


def record(
    weeks: str, *, plurality: str = "1", visits: str, trimester: str, education: str = "51"
) -> tuple[str | None, ...]:
    """Record 1 of ``tests/synthetic.py``, the normal case, with other weeks, plurality, visits,
    first-visit trimester or education. The fields are in the order of SOURCE_COLUMNS."""
    return (
        "15/03/2023", "02/05/1995", "27", "2", "09", weeks, plurality, visits, trimester,
        education, "1", "3200",
    )  # fmt: skip


#: Records 9 to 15 of the 2023 file. Records 1 to 8 leave nobody at a validity step, so each of
#: the first four is the record one validity step removes; the last three stay in the analysis
#: cohort with records 1 and 2.
PUBLISH_RECORDS_2023 = (
    # 9. Gestational age 99 "No Especificado", no care: leaves at step 4.
    record("99", visits="0", trimester="0"),
    # 10. Multiplicity 0 "NO ESPECIFICADO", 35 weeks, from the second trimester: step 5.
    record("35", plurality="0", visits="5", trimester="2"),
    # 11. 36 weeks, trimester 8 "NO ESPECIFICADO": step 8.
    record("36", visits="3", trimester="8"),
    # 12. 37 weeks, the first term week, from the first trimester, education 99 "SE IGNORA":
    #     step 9.
    record("37", visits="9", trimester="1", education="99"),
    # 13. 30 weeks, 2 visits from the third trimester.
    record("30", visits="2", trimester="3"),
    # 14. 40 weeks, 6 visits from the first trimester.
    record("40", visits="6", trimester="1"),
    # 15. 28 weeks, no care.
    record("28", visits="0", trimester="0"),
)

#: excluded_profile.csv, by hand. Besides records 9 to 15, the records of RECORDS_2023 that reach
#: a validity step are 1 and 2 (39 weeks, trimester 1), 3 (12 weeks, below the outcome, trimester
#: 0) and 8 (34 weeks, trimester 1); 4, 5 and 7 leave at step 3 and 6 at step 1.
#: Definition 1, step 4: record 9 leaves, with no weeks; records 1 to 3, 8 and 10 to 15 stay.
#:   Preterm: 8, 10, 11, 13 and 15 of the 9 with 22 weeks or more. A trimester is known in 9 (not
#:   in 11): 1 in records 1, 2, 8, 12 and 14, and 0 in records 3 and 15.
#: Step 5: record 10 leaves; the rest stay. Preterm 4 of 8, trimester 1 in 5 of 8 and 0 in 2.
#: Definition 2 repeats steps 4 and 5, then:
#: Step 8: record 11 leaves, with no trimester; records 1, 2 and 12 to 15 stay. Preterm: 13, 15.
#: Step 9: record 12 leaves; records 1, 2 and 13 to 15 stay.
#: The landmark cohorts, definitions 3 to 5, repeat the four steps of definition 2.
#: Definition 6, with multiples, repeats steps 4 and 5; record 3 leaves at step 6, of kind design.
#: Step 7: records 8 (twins of 34 weeks with no visits and a first visit in trimester 1) and 11
#:   leave, both preterm, with trimester 1 known in record 8 alone; records 1, 2 and 12 to 15
#:   stay, as at step 8 of definition 2.
#: Step 8 is step 9 of definition 2.
PROFILE_1 = [
    "4,excluded,1,,0.00,100.00",
    "4,retained,10,55.56,55.56,22.22",
    "5,excluded,1,100.00,0.00,0.00",
    "5,retained,9,50.00,62.50,25.00",
]
PROFILE_2 = [
    *PROFILE_1,
    "8,excluded,1,100.00,,",
    "8,retained,6,33.33,66.67,16.67",
    "9,excluded,1,0.00,100.00,0.00",
    "9,retained,5,40.00,60.00,20.00",
]
PROFILE_6 = [
    *PROFILE_1,
    "7,excluded,2,100.00,100.00,0.00",
    "7,retained,6,33.33,66.67,16.67",
    "8,excluded,1,0.00,100.00,0.00",
    "8,retained,5,40.00,60.00,20.00",
]
PROFILE_CSV = [
    ",".join(TABLES["excluded_profile.csv"].header),
    *(f"1,{row}" for row in PROFILE_1),
    *(f"{definition},{row}" for definition in (2, 3, 4, 5) for row in PROFILE_2),
    *(f"6,{row}" for row in PROFILE_6),
]

FILES = (*TABLES, "manifest.json")


@pytest.fixture(scope="module")
def schemas(
    db_connection: sql_runner.Connection, ddl_files: Sequence[Path]
) -> Iterator[etl.Schemas]:
    with module_schemas(db_connection, ddl_files, "test_publish") as names:
        yield names


@pytest.fixture
def source(db_connection: sql_runner.Connection, schemas: etl.Schemas, tmp_path: Path) -> Source:
    """The synthetic source with the records above, loaded into the CDM for 2023, with no table
    of results built yet."""
    prepared = prepare_source(db_connection, schemas, tmp_path)
    prepared.stage(2023, (*RECORDS_2023, *PUBLISH_RECORDS_2023))
    results = schemas.results
    with db_connection.cursor() as cursor:
        cursor.execute(
            f"DROP TABLE IF EXISTS {results}.cohort, {results}.attrition, {results}.exposure, "
            f"{results}.excluded_profile, {results}.simulation, {results}.simulated_combination, "
            f"{results}.truncation_share, {results}.aggregated_count, {results}.estimate, "
            f"{results}.exposure_distribution"
        )
    prepared.run((2023,))
    return prepared


def publish_run(
    source: Source, results_dir: Path, *, code: Code = CODE, years: Sequence[int] = (2023,)
) -> Path:
    return publish.run(
        source.connection,
        years,
        schemas=source.schemas,
        code=code,
        results_dir=results_dir,
        sources_path=source.manifest,
        now=NOW,
    )


@pytest.mark.db
def test_each_file_is_its_table_of_the_run(source: Source, tmp_path: Path) -> None:
    results_dir = tmp_path / "results"
    publish_run(source, results_dir)
    for table in OUTPUT_TABLES:
        columns = ", ".join(column.name for column in table.columns)
        query = f"SELECT {columns} FROM {source.schemas.results}.{table.table}"
        rows = fetch(source.connection, query)
        published = read_table_csv(table, (results_dir / table.file).read_text("utf-8"))
        assert rows, table.file
        assert published == sorted_rows(table, rows), table.file

    attrition = read_table_csv(ATTRITION, (results_dir / "attrition.csv").read_text("utf-8"))
    assert {row[0] for row in attrition} == {1, 2, 3, 4, 5, 6}


@pytest.mark.db
def test_the_profile_compares_the_records_each_validity_step_removes(
    source: Source, tmp_path: Path
) -> None:
    results_dir = tmp_path / "results"
    publish_run(source, results_dir)
    assert (results_dir / "excluded_profile.csv").read_text("utf-8").splitlines() == PROFILE_CSV


@pytest.mark.db
def test_the_manifest_names_the_commit_the_sources_and_the_hash_of_each_file(
    source: Source, tmp_path: Path
) -> None:
    results_dir = tmp_path / "results"
    assert publish_run(source, results_dir) == results_dir / "manifest.json"
    hashes = [
        {"name": name, "sha256": hashlib.sha256((results_dir / name).read_bytes()).hexdigest()}
        for name in TABLES
    ]
    assert json.loads((results_dir / "manifest.json").read_text("utf-8")) == {
        "generated_at": "2026-09-29T12:00:05Z",
        "code": {"repository": "https://example.test/repo", "commit": "synthetic"},
        "period": [2023],
        "sources": [{"id": "dgis_sinac_2023", "version": "2024.05.14", "sha256": SHA256[2023]}],
        "vocabulary": {"version": VERSION, "sha256": "c" * 64},
        "files": hashes,
    }


@pytest.mark.db
def test_two_publications_write_the_same_files(source: Source, tmp_path: Path) -> None:
    publish_run(source, tmp_path / "first")
    publish_run(source, tmp_path / "second")
    for name in FILES:
        assert (tmp_path / "first" / name).read_bytes() == (tmp_path / "second" / name).read_bytes()


@pytest.mark.db
def test_a_csv_the_run_does_not_write_is_removed(source: Source, tmp_path: Path) -> None:
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    (results_dir / "attrition_base.csv").write_text("old\n", encoding="utf-8")
    (results_dir / ".gitkeep").write_text("", encoding="utf-8")
    publish_run(source, results_dir)
    assert sorted(path.name for path in results_dir.iterdir()) == sorted((*FILES, ".gitkeep"))


@pytest.mark.db
@pytest.mark.parametrize(
    "code",
    [
        Code(repository="https://example.test/repo", commit="another"),
        Code(repository="https://example.test/fork", commit="synthetic"),
    ],
    ids=["commit", "repository"],
)
def test_a_cdm_loaded_from_other_code_is_refused_and_nothing_is_written(
    source: Source, tmp_path: Path, code: Code
) -> None:
    results_dir = tmp_path / "results"
    with pytest.raises(publish.PublishError, match=re.escape("run `pipeline.py cdm --years 2023`")):
        publish_run(source, results_dir, code=code)
    assert not results_dir.exists()


@pytest.mark.db
def test_a_cdm_loaded_with_uncommitted_changes_is_refused(source: Source, tmp_path: Path) -> None:
    with source.connection.cursor() as cursor:
        cursor.execute(
            f"UPDATE {source.schemas.cdm}.cdm_source "
            "SET cdm_etl_reference = cdm_etl_reference || ', with uncommitted changes'"
        )
    with pytest.raises(publish.PublishError, match="uncommitted changes"):
        publish_run(source, tmp_path / "results")
    assert not (tmp_path / "results").exists()


@pytest.mark.db
def test_a_vocabulary_other_than_the_declared_one_is_refused(
    source: Source, tmp_path: Path
) -> None:
    with source.connection.cursor() as cursor:
        cursor.execute(
            f"UPDATE {source.schemas.cdm}.vocabulary SET vocabulary_version = 'v5.0 OTHER' "
            "WHERE vocabulary_id = 'None'"
        )
    with pytest.raises(publish.PublishError, match="v5.0 OTHER"):
        publish_run(source, tmp_path / "results")
    assert not (tmp_path / "results").exists()


@pytest.mark.db
def test_a_year_the_cdm_does_not_hold_is_refused(source: Source, tmp_path: Path) -> None:
    with pytest.raises(publish.PublishError, match=re.escape("2022")):
        publish_run(source, tmp_path / "results", years=(2022, 2023))
    assert not (tmp_path / "results").exists()
