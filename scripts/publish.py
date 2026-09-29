"""Publishing the results of a run under ``results/`` (task 1.5.2).

The I/O of publishing lives here (rule 6): git, the manifest of sources, Postgres and the files of
``results/``. The text of each file comes from :mod:`sinac_truncation.publish`.

A run publishes what one commit produces end to end (D-080). It refuses to start when the working
tree has changes outside ``results/``, or when the CDM was loaded from another commit or another
vocabulary. It then rebuilds the cohorts at this commit, writes the attrition of the base cohort,
reads the file back against the run, and writes the manifest last. Every count is published as the
run gives it (D-040).
"""

import subprocess
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from psycopg import sql

import cohorts
import download
import etl
import load_vocab
import sql_runner
import validate_concepts
from sinac_truncation.etl import etl_reference, repository_url
from sinac_truncation.integrity import digest_chunks
from sinac_truncation.publish import (
    Code,
    PublishedFile,
    PublishedSource,
    attrition_csv,
    manifest_json,
    read_attrition_csv,
)
from sinac_truncation.vocabulary import VocabularyPackage

#: Repository root, reached from this file so no absolute path is written down (rule 12).
REPO_ROOT = Path(__file__).resolve().parents[1]

RESULTS_DIR = REPO_ROOT / "results"

#: The base cohort: the number of ``sql/cohorts/01_base.sql`` (D-077).
BASE_DEFINITION = 1
ATTRITION_FILE = "attrition_base.csv"
MANIFEST_FILE = "manifest.json"


class PublishError(RuntimeError):
    """The results could not be published for a reason the user has to act on."""


def current_code(repo_root: Path = REPO_ROOT) -> Code:
    """The commit the working tree is at, which a run publishes from.

    Changes under ``results/`` do not count: they are what the run writes.

    Raises:
        PublishError: git cannot tell, or a file outside ``results/`` differs from the commit.
    """

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(repo_root), *args], check=True, capture_output=True, text=True
        ).stdout

    try:
        remote = git("remote", "get-url", "origin")
        commit = git("rev-parse", "HEAD").strip()
        changed = git("status", "--porcelain", "--", ".", ":(exclude)results").splitlines()
    except (OSError, subprocess.CalledProcessError) as error:
        raise PublishError(f"git cannot tell which commit this is: {error}") from error
    if changed:
        listed = "\n  ".join(changed)
        raise PublishError(
            "the working tree differs from the commit outside results/, so the results would "
            f"not be the ones of any commit; commit them first:\n  {listed}"
        )
    return Code(repository=repository_url(remote), commit=commit)


def read_sources(
    years: Sequence[int], sources_path: Path
) -> tuple[list[PublishedSource], VocabularyPackage]:
    """The record file of each year and the vocabulary package, as the manifest records them."""
    published: list[PublishedSource] = []
    try:
        for year in years:
            entry = download.load_entry(sources_path, download.record_id(year))
            if entry.sha256 is None:
                raise PublishError(
                    f"{entry.id} has no recorded sha256: run "
                    f"`pipeline.py download --years {year} --record` first"
                )
            published.append(
                PublishedSource(id=entry.id, version=entry.version, sha256=entry.sha256)
            )
        package = load_vocab.read_package(sources_path)
    except (download.DownloadError, load_vocab.VocabError) as error:
        raise PublishError(str(error)) from error
    return published, package


def check_database(
    conn: sql_runner.Connection,
    years: Sequence[int],
    schemas: etl.Schemas,
    code: Code,
    package: VocabularyPackage,
) -> None:
    """Refuse a CDM that was not loaded from ``code``, clean, with the declared vocabulary."""
    expected = etl_reference(code.repository, code.commit, dirty=False)
    try:
        with conn.transaction(), conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT cdm_etl_reference FROM {}").format(
                    sql.Identifier(schemas.cdm, "cdm_source")
                )
            )
            loaded = [row[0] for row in cur.fetchall()]
            version = validate_concepts.loaded_version(conn, schemas.cdm)
    except psycopg.errors.UndefinedTable as error:
        raise PublishError(
            f"{str(error).strip()}. Run `pipeline.py db-init`, `vocab` and `cdm` first."
        ) from error
    if loaded != [expected]:
        found = ", ".join(repr(reference) for reference in loaded) or "nothing"
        raise PublishError(
            f"the CDM was loaded from {found}, not from {expected!r}: run `pipeline.py cdm "
            f"--years {','.join(str(year) for year in years)}` again from this commit, with "
            "nothing uncommitted, then publish"
        )
    if version != package.vocabulary_version:
        raise PublishError(
            f"the database holds vocabulary {version!r} and config/sources.yml declares "
            f"{package.vocabulary_version!r}: run `pipeline.py vocab` and `cdm` again"
        )


def run(
    conn: sql_runner.Connection,
    years: Sequence[int],
    *,
    schemas: etl.Schemas,
    code: Code,
    results_dir: Path = RESULTS_DIR,
    sources_path: Path = download.SOURCES_PATH,
    now: datetime | None = None,
) -> Path:
    """Rebuild the cohorts and publish the attrition of the base cohort with its manifest.

    See ``pipeline.py publish --help``.

    Returns:
        The path of the manifest.

    Raises:
        PublishError: anything the user has to act on; nothing is written when it is raised
            before the cohorts are rebuilt.
    """
    sources, package = read_sources(years, sources_path)
    check_database(conn, years, schemas, code, package)
    try:
        steps = cohorts.run(conn, years, schemas=schemas)
    except cohorts.CohortError as error:
        raise PublishError(str(error)) from error

    base = [step for step in steps if step.cohort_definition_id == BASE_DEFINITION]
    built = sorted({step.source_year for step in base})
    if built != sorted(years):
        raise PublishError(f"the base cohort was built for {built}, not for {sorted(years)}")

    text = attrition_csv(base)
    results_dir.mkdir(parents=True, exist_ok=True)
    attrition_path = results_dir / ATTRITION_FILE
    attrition_path.write_bytes(text.encode("utf-8"))
    written = attrition_path.read_bytes()
    if read_attrition_csv(written.decode("utf-8")) != base:
        raise PublishError(f"{attrition_path} does not read back as the attrition of the run")

    manifest = manifest_json(
        generated_at=(now or datetime.now(UTC)).replace(microsecond=0),
        code=code,
        years=years,
        sources=sources,
        vocabulary_version=package.vocabulary_version,
        vocabulary_sha256=package.sha256,
        files=[PublishedFile(name=ATTRITION_FILE, sha256=digest_chunks([written]).sha256)],
    )
    manifest_path = results_dir / MANIFEST_FILE
    manifest_path.write_bytes(manifest.encode("utf-8"))
    print(
        f"\npublished {len(base)} steps of the base cohort to {attrition_path.name} and the "
        f"manifest to {manifest_path.name}, from commit {code.commit[:12]}"
    )
    return manifest_path
