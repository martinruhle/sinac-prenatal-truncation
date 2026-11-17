"""The ignore rules keep the records and the secrets out of git (CLAUDE.md rule 1).

``git check-ignore --no-index`` answers with git's own matcher, for paths that need not exist, so
nothing is written. The analysis image holds no ``.git``, so there these tests skip.
"""

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _in_a_work_tree() -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"


pytestmark = pytest.mark.skipif(
    not _in_a_work_tree(), reason="no git work tree here (the analysis image holds none)"
)


def ignored(path: str) -> bool:
    """Whether git ignores the path, which need not exist."""
    result = subprocess.run(
        ["git", "-C", str(ROOT), "check-ignore", "--no-index", "--quiet", path],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(f"git check-ignore failed: {result.stderr.strip()}")
    return result.returncode == 0


@pytest.mark.parametrize(
    "path",
    [
        "data/raw/dgis/sinac_2023.zip",
        "data/interim/sinac_2023.parquet",
        ".env",
        ".env.local",
        "config/.env",
        "notebooks/sinac_2023.parquet",
        "results/sinac_2023.zip",
        "scripts/out/records.7z",
        ".claude/worktrees/some-branch/.env",
    ],
)
def test_records_archives_and_secrets_are_ignored_wherever_they_land(path: str) -> None:
    assert ignored(path)


@pytest.mark.parametrize(
    "path",
    [
        ".env.example",
        "results/attrition.csv",
        "results/manifest.json",
        "config/source_to_concept_map.csv",
        "tests/test_stage.py",
        "tests/data/fixture.csv",
    ],
)
def test_what_the_repository_versions_is_not_ignored(path: str) -> None:
    """``tests/data/`` stays visible: ``/data/`` is anchored to the root (D-038)."""
    assert not ignored(path)
