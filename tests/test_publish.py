"""Tests for publishing the results of a run under ``results/`` (task 1.5.2, D-014, D-080).

The pure tests build the text of the files from small hand-written tables. Tests marked ``db`` load
the synthetic source of ``tests/synthetic.py`` through the ETL into schemas of this module's own,
dropped after it, and publish into a temporary folder, never into ``results/``.
"""

import hashlib
import json
import re
import subprocess
from collections.abc import Iterator, Sequence
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

import etl
import pipeline
import publish
import sql_runner
from sinac_truncation.cohorts import AttritionStep
from sinac_truncation.publish import (
    ATTRITION_COLUMNS,
    Code,
    PublishedFile,
    PublishedSource,
    attrition_csv,
    manifest_json,
    read_attrition_csv,
)
from synthetic import SHA256, VERSION, Source, fetch, module_schemas, prepare_source

NOW = datetime(2026, 9, 29, 12, 0, 5, tzinfo=UTC)

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


def test_the_csv_holds_the_columns_of_the_table() -> None:
    assert ATTRITION_COLUMNS == (
        "cohort_definition_id",
        "source_year",
        "step",
        "kind",
        "description",
        "remaining",
        "excluded",
    )


def test_the_csv_has_one_row_per_step_in_order_with_lf_line_ends() -> None:
    assert attrition_csv(list(reversed(STEPS))) == CSV_TEXT


def test_the_csv_reads_back_to_the_same_steps() -> None:
    assert read_attrition_csv(attrition_csv(STEPS)) == list(STEPS)


def test_a_csv_with_another_header_is_refused() -> None:
    with pytest.raises(ValueError, match="header"):
        read_attrition_csv(CSV_TEXT.replace("remaining", "kept", 1))


MANIFEST_ARGS = {
    "code": Code(repository="https://github.com/o/r", commit="abc123"),
    "years": (2023, 2022),
    "sources": (
        PublishedSource(id="dgis_sinac_2022", version="2023.05.23", sha256="b" * 64),
        PublishedSource(id="dgis_sinac_2023", version="2024.05.14", sha256="a" * 64),
    ),
    "vocabulary_version": "v5.0 29-AUG-26",
    "vocabulary_sha256": "c" * 64,
    "files": (PublishedFile(name="attrition_base.csv", sha256="d" * 64),),
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
        "files": [{"name": "attrition_base.csv", "sha256": "d" * 64}],
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
    (repo / "results" / "attrition_base.csv").write_text("new\n", encoding="utf-8")
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

ATTRITION_QUERY = (
    "SELECT cohort_definition_id, source_year, step, kind, description, remaining, excluded "
    "FROM {}.attrition WHERE cohort_definition_id = 1 ORDER BY source_year, step"
)


@pytest.fixture(scope="module")
def schemas(
    db_connection: sql_runner.Connection, ddl_files: Sequence[Path]
) -> Iterator[etl.Schemas]:
    with module_schemas(db_connection, ddl_files, "test_publish") as names:
        yield names


@pytest.fixture
def source(db_connection: sql_runner.Connection, schemas: etl.Schemas, tmp_path: Path) -> Source:
    """The synthetic source, loaded into the CDM for 2023, with no cohort built yet."""
    prepared = prepare_source(db_connection, schemas, tmp_path)
    results = schemas.results
    with db_connection.cursor() as cursor:
        cursor.execute(f"DROP TABLE IF EXISTS {results}.cohort, {results}.attrition")
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
def test_the_csv_is_the_attrition_of_the_base_cohort_of_the_run(
    source: Source, tmp_path: Path
) -> None:
    results_dir = tmp_path / "results"
    publish_run(source, results_dir)
    rows = fetch(source.connection, ATTRITION_QUERY.format(source.schemas.results))
    published = read_attrition_csv((results_dir / "attrition_base.csv").read_text("utf-8"))
    assert len(rows) == 8
    assert published == [AttritionStep(*row) for row in rows]


@pytest.mark.db
def test_the_manifest_names_the_commit_the_sources_and_the_hash_of_the_csv(
    source: Source, tmp_path: Path
) -> None:
    results_dir = tmp_path / "results"
    assert publish_run(source, results_dir) == results_dir / "manifest.json"
    csv_sha256 = hashlib.sha256((results_dir / "attrition_base.csv").read_bytes()).hexdigest()
    assert json.loads((results_dir / "manifest.json").read_text("utf-8")) == {
        "generated_at": "2026-09-29T12:00:05Z",
        "code": {"repository": "https://example.test/repo", "commit": "synthetic"},
        "period": [2023],
        "sources": [{"id": "dgis_sinac_2023", "version": "2024.05.14", "sha256": SHA256[2023]}],
        "vocabulary": {"version": VERSION, "sha256": "c" * 64},
        "files": [{"name": "attrition_base.csv", "sha256": csv_sha256}],
    }


@pytest.mark.db
def test_two_publications_write_the_same_files(source: Source, tmp_path: Path) -> None:
    publish_run(source, tmp_path / "first")
    publish_run(source, tmp_path / "second")
    for name in ("attrition_base.csv", "manifest.json"):
        assert (tmp_path / "first" / name).read_bytes() == (tmp_path / "second" / name).read_bytes()


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
