"""Single entry point for the project pipeline (D-034).

uv run --env-file .env python scripts/pipeline.py --help
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import psycopg

import sql_runner
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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "db-init":
        return db_init(recreate=bool(args.recreate))
    raise AssertionError(f"unhandled command: {args.command}")  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())
