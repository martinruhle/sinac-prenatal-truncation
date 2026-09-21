"""Single entry point for the project pipeline (D-034).

uv run --env-file .env python scripts/pipeline.py --help
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import httpx
import psycopg

import download
import sql_runner
from sinac_truncation.period import STUDY_YEARS, PeriodError, format_years, parse_years
from sinac_truncation.sqltext import schema_mapping

#: Repository root, reached from this file so no absolute path is written down (rule 12).
REPO_ROOT = Path(__file__).resolve().parents[1]

DDL_DIR = REPO_ROOT / "sql" / "ddl" / "ohdsi"

#: The vendored OHDSI files, in the order they have to be applied. Foreign keys are not
#: applied and not vendored (D-032).
DDL_FILES = (
    DDL_DIR / "OMOPCDM_postgresql_5.4_ddl.sql",
    DDL_DIR / "OMOPCDM_postgresql_5.4_primary_keys.sql",
    DDL_DIR / "OMOPCDM_postgresql_5.4_indices.sql",
)

CDM_SCHEMA = "cdm"
STAGING_SCHEMA = "staging"
RESULTS_SCHEMA = "results"
SCHEMAS = (CDM_SCHEMA, STAGING_SCHEMA, RESULTS_SCHEMA)


def db_init(*, recreate: bool) -> int:
    """Create the schemas and apply the OMOP CDM v5.4 DDL, primary keys and indices."""
    try:
        conninfo = sql_runner.conninfo_from_env()
    except sql_runner.MissingEnvironmentError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    try:
        with psycopg.connect(conninfo) as conn:
            if recreate:
                sql_runner.drop_schemas(conn, SCHEMAS)
            sql_runner.ensure_schemas(conn, SCHEMAS)

            existing = sql_runner.count_tables(conn, CDM_SCHEMA)
            if existing:
                print(
                    f"error: schema {CDM_SCHEMA!r} already holds {existing} tables. "
                    "Re-run with --recreate to drop and rebuild the schemas, "
                    "or use `docker compose down -v` to start from an empty database.",
                    file=sys.stderr,
                )
                return 1

            for path in DDL_FILES:
                sql_runner.run_sql_file(conn, path, schema_mapping(*SCHEMAS))
                print(f"applied {path.relative_to(REPO_ROOT).as_posix()}")

            created = sql_runner.count_tables(conn, CDM_SCHEMA)
    except psycopg.OperationalError as error:
        print(f"error: cannot reach the database: {error}", file=sys.stderr)
        return 2

    print(f"schemas {', '.join(SCHEMAS)} ready; {created} tables in {CDM_SCHEMA}")
    return 0


def download_source(*, entry_id: str, record: bool, dest: Path, timeout: float) -> int:
    """Download one source file, or verify the copy already on disk, against the manifest."""
    try:
        download.run(entry_id, record_digest=record, dest_dir=dest, timeout=timeout)
    except download.DownloadError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except httpx.HTTPError as error:
        print(f"error: the download failed: {error}", file=sys.stderr)
        return 2
    return 0


def download_sources(*, entry_ids: Sequence[str], record: bool, dest: Path, timeout: float) -> int:
    """Download or verify each source in turn, stopping at the first one that fails."""
    for entry_id in entry_ids:
        status = download_source(entry_id=entry_id, record=record, dest=dest, timeout=timeout)
        if status != 0:
            return status
    return 0


def years_option(text: str) -> tuple[int, ...]:
    """``--years`` as argparse reads it, so a malformed value is a usage error."""
    try:
        return parse_years(text)
    except PeriodError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def add_years_option(container: argparse._ActionsContainer, *, what: str) -> None:
    """The ``--years`` option every step that reads records takes, defaulting to D-041.

    ``_ActionsContainer`` is the base argparse gives both parsers and mutually exclusive groups,
    so the option can be added to either.
    """
    container.add_argument(
        "--years",
        type=years_option,
        default=STUDY_YEARS,
        metavar="YEARS",
        help=(
            f"{what}, as 2023, 2022,2023 or 2020-2023 (default: the study period, "
            f"{format_years(STUDY_YEARS)}, D-041; development runs on 2023, D-009)"
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipeline.py",
        description="Pipeline for the SINAC prenatal care truncation study.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    db_init_parser = subcommands.add_parser(
        "db-init",
        help="create the schemas and apply the OMOP CDM v5.4 DDL",
        description=(
            "Creates the cdm, staging and results schemas and applies the vendored OMOP CDM "
            "v5.4 DDL, primary keys and indices to cdm. Foreign keys are not applied (D-032)."
        ),
    )
    db_init_parser.add_argument(
        "--recreate",
        action="store_true",
        help="DESTRUCTIVE: drop the cdm, staging and results schemas first, losing their data",
    )

    download_parser = subcommands.add_parser(
        "download",
        help="download source files listed in config/sources.yml and check their sha256",
        description=(
            "Downloads files declared in config/sources.yml into data/raw/dgis/ and checks "
            "each sha256 against the manifest: by default the record files of the study period, "
            "with --years the record files of other years, with --id any single entry such as "
            "a descriptor or a catalogue. A file already on disk is verified, never downloaded "
            "again and never overwritten (D-044)."
        ),
    )
    selection = download_parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--id",
        dest="entry_id",
        help="id of one entry in the `downloads:` block of config/sources.yml",
    )
    add_years_option(selection, what="years whose record files are downloaded")
    download_parser.add_argument(
        "--record",
        action="store_true",
        help=(
            "write sha256, size_bytes and retrieved_at into config/sources.yml. Only for the "
            "first download of a source: a recorded hash is never overwritten"
        ),
    )
    download_parser.add_argument(
        "--dest",
        type=Path,
        default=download.RAW_DIR,
        help="directory the file is written to (default: data/raw/dgis)",
    )
    download_parser.add_argument(
        "--timeout",
        type=float,
        default=download.DEFAULT_TIMEOUT,
        help=f"read timeout in seconds (default: {download.DEFAULT_TIMEOUT:g})",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "db-init":
        return db_init(recreate=bool(args.recreate))
    if args.command == "download":
        entry_ids = (
            [str(args.entry_id)]
            if args.entry_id is not None
            else [download.record_id(year) for year in args.years]
        )
        return download_sources(
            entry_ids=entry_ids,
            record=bool(args.record),
            dest=Path(args.dest),
            timeout=float(args.timeout),
        )
    raise AssertionError(f"unhandled command: {args.command}")  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())
