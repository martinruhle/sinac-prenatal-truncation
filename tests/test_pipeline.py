"""Tests for ``pipeline.py all``, which chains the steps that rebuild the cohorts (D-082).

Every step is replaced by a stub that records its call, so nothing here touches the network, the
files or the database.
"""

from collections.abc import Callable

import pytest

import download
import pipeline
from sinac_truncation.period import STUDY_YEARS

#: The steps of `all`, in the order they have to run, by the name of their subcommand.
STEPS = ("download", "stage", "vocab", "validate-concepts", "cdm", "cohorts")

#: The function of pipeline.py behind each subcommand.
FUNCTIONS = {
    "db-init": "db_init",
    "download": "download_sources",
    "stage": "stage_years",
    "vocab": "load_vocabulary",
    "validate-concepts": "check_concepts",
    "cdm": "build_cdm",
    "cohorts": "build_cohorts",
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
            },
        ),
        ("stage", {"years": (2022, 2023)}),
        ("vocab", {}),
        ("validate-concepts", {}),
        ("cdm", {"years": (2022, 2023)}),
        ("cohorts", {"years": (2022, 2023)}),
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
