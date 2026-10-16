"""Publishing the results of a run under ``results/`` (task 1.5.2, issue #59).

The I/O of publishing lives here (rule 6): git, the manifest of sources, Postgres and the files of
``results/``. The text of each file comes from :mod:`sinac_truncation.publish`.

A run publishes what one commit produces end to end (D-080, D-122). It refuses to start when the
working tree has changes outside ``results/``, or when the CDM was loaded from another commit or
another vocabulary. It then rebuilds the cohorts, the null simulation and the odds ratios at this
commit, writes the five output files of D-098, reads each back against the run, removes any other
CSV of ``results/``, and writes the manifest last. Every count is published as the run gives it
(D-040).
"""

import subprocess
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from psycopg import sql

import cohorts
import download
import estimate
import etl
import load_vocab
import simulate
import sql_runner
import validate_concepts
from sinac_truncation.etl import etl_reference, repository_url
from sinac_truncation.integrity import digest_chunks
from sinac_truncation.publish import (
    OUTPUT_TABLES,
    Code,
    OutputTable,
    PublishedFile,
    PublishedSource,
    Value,
    manifest_json,
    read_table_csv,
    sorted_rows,
    table_csv,
)
from sinac_truncation.vocabulary import VocabularyPackage

#: Repository root, reached from this file so no absolute path is written down (rule 12).
REPO_ROOT = Path(__file__).resolve().parents[1]

RESULTS_DIR = REPO_ROOT / "results"

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


def read_table(
    conn: sql_runner.Connection, schemas: etl.Schemas, table: OutputTable
) -> list[tuple[Value, ...]]:
    """Every row of the table an output file copies, with the columns of the file."""
    query = sql.SQL("SELECT {} FROM {}").format(
        sql.SQL(", ").join(sql.Identifier(column.name) for column in table.columns),
        sql.Identifier(schemas.results, table.table),
    )
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(query)
        return [tuple(row) for row in cur.fetchall()]


def rebuild(conn: sql_runner.Connection, years: Sequence[int], schemas: etl.Schemas) -> None:
    """Rebuild every table the output files copy, at this commit: the cohorts, the null
    simulation and the odds ratios, in the order of `pipeline.py all` (D-122)."""
    try:
        steps = cohorts.run(conn, years, schemas=schemas)
        built = sorted({step.source_year for step in steps})
        if built != sorted(years):
            raise PublishError(f"the cohorts were built for {built}, not for {sorted(years)}")
        print()
        simulate.run(conn, schemas=schemas)
        print()
        estimate.run(conn, schemas=schemas)
    except (cohorts.CohortError, simulate.SimulateError, estimate.EstimateError) as error:
        raise PublishError(str(error)) from error


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
    """Rebuild the results at this commit and publish the five output files with their manifest.

    See ``pipeline.py publish --help``.

    Returns:
        The path of the manifest.

    Raises:
        PublishError: anything the user has to act on; nothing is written when it is raised
            before the results are rebuilt.
    """
    sources, package = read_sources(years, sources_path)
    check_database(conn, years, schemas, code, package)
    rebuild(conn, years, schemas)

    results_dir.mkdir(parents=True, exist_ok=True)
    published: list[PublishedFile] = []
    lines: list[str] = []
    for table in OUTPUT_TABLES:
        rows = sorted_rows(table, read_table(conn, schemas, table))
        path = results_dir / table.file
        path.write_bytes(table_csv(table, rows).encode("utf-8"))
        written = path.read_bytes()
        if read_table_csv(table, written.decode("utf-8")) != rows:
            raise PublishError(f"{path} does not read back as {schemas.results}.{table.table}")
        published.append(PublishedFile(name=table.file, sha256=digest_chunks([written]).sha256))
        lines.append(f"  {table.file:<28}{len(rows):>8,} rows")

    # results/ holds what one run publishes and nothing else (D-014): a CSV of an earlier layout,
    # such as attrition_base.csv before v0.2-progress, would outlive the manifest that names it.
    names = {table.file for table in OUTPUT_TABLES}
    for stale in sorted(path for path in results_dir.glob("*.csv") if path.name not in names):
        stale.unlink()
        lines.append(f"  removed {stale.name}, which this run does not write")

    manifest = manifest_json(
        generated_at=(now or datetime.now(UTC)).replace(microsecond=0),
        code=code,
        years=years,
        sources=sources,
        vocabulary_version=package.vocabulary_version,
        vocabulary_sha256=package.sha256,
        files=published,
    )
    manifest_path = results_dir / MANIFEST_FILE
    manifest_path.write_bytes(manifest.encode("utf-8"))
    print(f"\npublished to {results_dir.name}/, from commit {code.commit[:12]}:")
    for line in lines:
        print(line)
    print(f"  {MANIFEST_FILE}")
    return manifest_path
