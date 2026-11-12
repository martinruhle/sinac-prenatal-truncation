"""Tests for ``pipeline.py all``, which chains the steps that rebuild the cohorts, the null
simulation and the odds ratios (D-082).

Every step is replaced by a stub that records its call, so nothing here touches the network, the
files or the database.
"""

from collections.abc import Callable

import pytest

import download
import pipeline
from sinac_truncation.period import STUDY_YEARS

#: The steps of `all`, in the order they have to run, by the name of their subcommand.
STEPS = (
    "download",
    "stage",
    "vocab",
    "validate-concepts",
    "cdm",
    "cohorts",
    "simulate",
    "estimate",
)

#: The function of pipeline.py behind each subcommand.
FUNCTIONS = {
    "db-init": "db_init",
    "download": "download_sources",
    "stage": "stage_years",
    "vocab": "load_vocabulary",
    "validate-concepts": "check_concepts",
    "cdm": "build_cdm",
    "cohorts": "build_cohorts",
    "simulate": "run_simulation",
    "estimate": "run_estimates",
    "publish": "publish_results",
}


def _record_steps(
    monkeypatch: pytest.MonkeyPatch, *, failing: str | None = None, status: int = 1
) -> list[tuple[str, dict[str, object]]]:
    """Replace every step with a stub that records its arguments; ``failing`` returns ``status``."""
    seen: list[tuple[str, dict[str, object]]] = []

    def stub(name: str) -> Callable[..., int]:
        def run(**kwargs: object) -> int:
            seen.append((name, kwargs))
            return status if name == failing else 0

        return run

    for name, function in FUNCTIONS.items():
        monkeypatch.setattr(pipeline, function, stub(name))
    return seen


def test_all_runs_every_step_in_order_on_the_years_given(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _record_steps(monkeypatch)
    assert pipeline.main(["all", "--years", "2022,2023"]) == 0
    assert seen == [
        (
            "download",
            {
                "entry_ids": ["dgis_sinac_2022", "dgis_sinac_2023"],
                "record": False,
                "dest": download.RAW_DIR,
                "timeout": download.DEFAULT_TIMEOUT,
                "sources_path": download.SOURCES_PATH,
            },
        ),
        ("stage", {"years": (2022, 2023), "source": pipeline.DGIS}),
        ("vocab", {"source": pipeline.DGIS}),
        ("validate-concepts", {"source": pipeline.DGIS}),
        ("cdm", {"years": (2022, 2023), "source": pipeline.DGIS}),
        ("cohorts", {"years": (2022, 2023), "source": pipeline.DGIS}),
        ("simulate", {"source": pipeline.DGIS}),
        ("estimate", {"source": pipeline.DGIS}),
    ]


def test_all_neither_initialises_the_database_nor_publishes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _record_steps(monkeypatch)
    assert pipeline.main(["all", "--years", "2023"]) == 0
    assert [name for name, _ in seen] == list(STEPS)


@pytest.mark.parametrize("failing", STEPS)
def test_all_stops_at_the_first_failure_and_returns_its_status(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], failing: str
) -> None:
    seen = _record_steps(monkeypatch, failing=failing, status=2)
    assert pipeline.main(["all", "--years", "2023"]) == 2
    assert [name for name, _ in seen] == list(STEPS[: STEPS.index(failing) + 1])
    assert f"`all` stopped at `{failing}`" in capsys.readouterr().err


def test_all_defaults_to_the_study_period() -> None:
    assert pipeline.build_parser().parse_args(["all"]).years == STUDY_YEARS


def test_all_reads_the_dgis_source_by_default() -> None:
    assert pipeline.build_parser().parse_args(["all"]).source == "dgis"


def test_all_refuses_a_source_it_does_not_know(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        pipeline.build_parser().parse_args(["all", "--source", "athena"])
    assert "invalid choice" in capsys.readouterr().err


def test_the_smoke_schemas_are_not_the_schemas_of_the_real_load() -> None:
    smoke = set(pipeline.SMOKE_SCHEMAS.markers.values())
    real = set(pipeline.DGIS.schemas.markers.values())
    assert not smoke & real


def test_all_on_fixtures_rebuilds_the_smoke_schemas_and_runs_every_step_there(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _record_steps(monkeypatch)
    assert pipeline.main(["all", "--source", "fixtures", "--years", "2022,2023"]) == 0

    assert seen[0] == ("db-init", {"recreate": True, "schemas": pipeline.SMOKE_SCHEMAS})
    assert [name for name, _ in seen[1:]] == list(STEPS)
    source = dict(seen)["stage"]["source"]
    assert isinstance(source, pipeline.Source)
    assert source.schemas == pipeline.SMOKE_SCHEMAS
    # Every file comes from the fixture directory, never from config/sources.yml or data/.
    for path in (source.sources_path, source.raw_dir, source.extracted_dir, source.interim_dir):
        assert path.is_relative_to(source.vocabulary_root)
        assert not path.is_relative_to(pipeline.REPO_ROOT)
    download_call = dict(seen)["download"]
    assert download_call["dest"] == source.raw_dir
    assert download_call["sources_path"] == source.sources_path
    assert all(kwargs.get("source", source) == source for _, kwargs in seen[2:])


def test_all_on_fixtures_removes_its_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _record_steps(monkeypatch)
    assert pipeline.main(["all", "--source", "fixtures", "--years", "2023"]) == 0
    source = dict(seen)["stage"]["source"]
    assert isinstance(source, pipeline.Source)
    assert not source.vocabulary_root.exists()


def test_all_on_fixtures_stops_when_the_smoke_schemas_cannot_be_rebuilt(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen = _record_steps(monkeypatch, failing="db-init", status=2)
    assert pipeline.main(["all", "--source", "fixtures", "--years", "2023"]) == 2
    assert [name for name, _ in seen] == ["db-init"]
    assert "`all` stopped at `db-init`" in capsys.readouterr().err


@pytest.mark.parametrize("failing", STEPS)
def test_all_on_fixtures_stops_at_the_first_failure_and_returns_its_status(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], failing: str
) -> None:
    seen = _record_steps(monkeypatch, failing=failing, status=1)
    assert pipeline.main(["all", "--source", "fixtures", "--years", "2023"]) == 1
    assert [name for name, _ in seen[1:]] == list(STEPS[: STEPS.index(failing) + 1])
    assert f"`all` stopped at `{failing}`" in capsys.readouterr().err
