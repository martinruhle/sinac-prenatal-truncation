"""Fixtures shared by the test suite."""

from collections.abc import Sequence
from pathlib import Path

import pytest

#: Repository root, reached from this file so no absolute path is written down (rule 12).
REPO_ROOT = Path(__file__).resolve().parents[1]

#: The vendored OHDSI files, in the order they have to be applied (D-032).
DDL_FILENAMES = (
    "OMOPCDM_postgresql_5.4_ddl.sql",
    "OMOPCDM_postgresql_5.4_primary_keys.sql",
    "OMOPCDM_postgresql_5.4_indices.sql",
)


@pytest.fixture(scope="session")
def ddl_dir() -> Path:
    """Directory holding the vendored OMOP CDM v5.4 DDL."""
    return REPO_ROOT / "sql" / "ddl" / "ohdsi"


@pytest.fixture(scope="session")
def ddl_files(ddl_dir: Path) -> Sequence[Path]:
    """The vendored files in application order."""
    return tuple(ddl_dir / name for name in DDL_FILENAMES)
