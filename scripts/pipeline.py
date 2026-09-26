"""Single entry point for the project pipeline (D-034).

uv run --env-file .env python scripts/pipeline.py --help
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import httpx
import psycopg

import cohorts
import download
import etl
import load_vocab
import sql_runner
import stage
import validate_concepts
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


def stage_years(*, years: Sequence[int]) -> int:
    """Stage each year's record file into the staging schema, stopping at the first failure."""
    try:
        conninfo = sql_runner.conninfo_from_env()
    except sql_runner.MissingEnvironmentError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    try:
        with psycopg.connect(conninfo) as conn:
            for year in years:
                stage.run(year, conn=conn, schema=STAGING_SCHEMA)
    except stage.StageError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except psycopg.OperationalError as error:
        print(f"error: cannot reach the database: {error}", file=sys.stderr)
        return 2

    print(f"staged {format_years(years)}; counts in {STAGING_SCHEMA}.load_counts")
    return 0


def load_vocabulary() -> int:
    """Load the Athena package that config/sources.yml declares into the cdm schema."""
    try:
        conninfo = sql_runner.conninfo_from_env()
    except sql_runner.MissingEnvironmentError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    try:
        with psycopg.connect(conninfo) as conn:
            load_vocab.run(conn, schema=CDM_SCHEMA)
    except load_vocab.VocabError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except psycopg.OperationalError as error:
        print(f"error: cannot reach the database: {error}", file=sys.stderr)
        return 2
    return 0


def check_concepts() -> int:
    """Check every concept_id of the configuration against the loaded vocabulary."""
    try:
        conninfo = sql_runner.conninfo_from_env()
    except sql_runner.MissingEnvironmentError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    try:
        with psycopg.connect(conninfo) as conn:
            problems = validate_concepts.run(conn, schema=CDM_SCHEMA)
    except validate_concepts.NotLoadedError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except load_vocab.VocabError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except psycopg.OperationalError as error:
        print(f"error: cannot reach the database: {error}", file=sys.stderr)
        return 2
    return 1 if problems else 0


def build_cdm(*, years: Sequence[int]) -> int:
    """Populate the OMOP tables of the vertical slice from the staged years."""
    try:
        conninfo = sql_runner.conninfo_from_env()
    except sql_runner.MissingEnvironmentError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    schemas = etl.Schemas(cdm=CDM_SCHEMA, staging=STAGING_SCHEMA, results=RESULTS_SCHEMA)
    try:
        with psycopg.connect(conninfo) as conn:
            etl.run(conn, years, schemas=schemas, reference=etl.git_reference())
    except etl.EtlError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except psycopg.OperationalError as error:
        print(f"error: cannot reach the database: {error}", file=sys.stderr)
        return 2
    return 0


def build_cohorts(*, years: Sequence[int]) -> int:
    """Build the cohorts of sql/cohorts/ and their attrition on the record files of the years."""
    try:
        conninfo = sql_runner.conninfo_from_env()
    except sql_runner.MissingEnvironmentError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    schemas = etl.Schemas(cdm=CDM_SCHEMA, staging=STAGING_SCHEMA, results=RESULTS_SCHEMA)
    try:
        with psycopg.connect(conninfo) as conn:
            cohorts.run(conn, years, schemas=schemas)
    except cohorts.CohortError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except psycopg.OperationalError as error:
        print(f"error: cannot reach the database: {error}", file=sys.stderr)
        return 2
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

    stage_parser = subcommands.add_parser(
        "stage",
        help="load the record files into the staging schema, every value as text",
        description=(
            "For each year: verifies the downloaded ZIP against config/sources.yml, extracts its "
            "CSV into data/raw/dgis/extracted/, writes a Parquet copy into data/interim/ with "
            "DuckDB and loads it into staging.sinac_<year> with COPY. Every source column stays "
            "text (D-033). The rows counted in the CSV, the Parquet file and the table must "
            "agree and are recorded in staging.load_counts. Each run rebuilds the year in one "
            "transaction, so running it again gives the same result (D-069)."
        ),
    )
    add_years_option(stage_parser, what="years whose record files are staged")

    subcommands.add_parser(
        "vocab",
        help="load the Athena vocabulary package into cdm (never run in CI)",
        description=(
            "Loads VOCABULARY, DOMAIN, CONCEPT_CLASS, RELATIONSHIP, CONCEPT, "
            "CONCEPT_RELATIONSHIP and CONCEPT_ANCESTOR into cdm from the Athena package that the "
            "`vocabulary:` block of config/sources.yml declares, straight from its ZIP (D-071). "
            "CONCEPT_SYNONYM and DRUG_STRENGTH are not loaded. The package's sha256, size, "
            "members, headers and vocabulary version are checked before any table is touched; "
            "the seven tables are then emptied and loaded in one transaction that commits only "
            "when the rows recorded in the manifest, in the file and in the table agree (D-072). "
            "Needs `db-init` first. The package is downloaded by hand from Athena."
        ),
    )

    subcommands.add_parser(
        "validate-concepts",
        help="check every concept_id of the configuration against the loaded vocabulary",
        description=(
            "Checks each concept_id of config/concept_sets.yml and each target of "
            "config/source_to_concept_map.csv against cdm.concept: it exists, is valid, is "
            "standard where required (every concept but 0), and has the domain, vocabulary and "
            "code the configuration records for it. It also checks that the loaded vocabulary "
            "version is the one config/sources.yml declares. Exits 1 when a concept fails, "
            "listing each failure, and 2 when no vocabulary is loaded."
        ),
    )

    cdm_parser = subcommands.add_parser(
        "cdm",
        help="populate the OMOP tables of the vertical slice from staging",
        description=(
            "Empties and refills PERSON, OBSERVATION_PERIOD, MEASUREMENT, OBSERVATION, LOCATION, "
            "CDM_SOURCE and SOURCE_TO_CONCEPT_MAP from staging.sinac_<year>, as "
            "docs/omop_mapping.md maps them, with the SQL of sql/etl/. The concept ids come from "
            "config/concept_sets.yml and config/source_to_concept_map.csv, loaded into "
            "results.concept_sets and the map. Every value is cast here, and each rule's count "
            "goes to results.etl_counts. A record with no valid delivery date stops the run. The "
            "load is one transaction that commits only when every post-load check (anti-joins, "
            "one-day observation periods, no VISIT_OCCURRENCE, PERSON against staging) counts 0, "
            "so a failed run keeps the previous load. The CDM then holds exactly the years given "
            "(D-073). Needs `db-init`, `vocab` and `stage` first; run it again after `vocab`, "
            "which empties VOCABULARY."
        ),
    )
    add_years_option(cdm_parser, what="years whose staged records are loaded")

    cohorts_parser = subcommands.add_parser(
        "cohorts",
        help="build the cohorts of sql/cohorts/ and their attrition from the CDM",
        description=(
            "Builds every cohort defined in sql/cohorts/ (the base cohort of docs/protocol.md) "
            "on the record files of the years given, and its attrition: one row per step, per "
            "definition and per year, into results.cohort and results.attrition. Steps 0 and 1 "
            "come from results.etl_counts, the rest from the CDM; criterion 1 keeps the births "
            "of those years (D-073). The years must be loaded by `cdm` first. Each run replaces "
            "the rows of its definitions in one transaction that commits only when the attrition "
            "is consistent (counts never grow, each step excludes what it removes, the last step "
            "equals the cohort), so a failed run keeps the previous cohort."
        ),
    )
    add_years_option(cohorts_parser, what="years whose record files the cohorts are built on")
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
    if args.command == "stage":
        return stage_years(years=args.years)
    if args.command == "vocab":
        return load_vocabulary()
    if args.command == "validate-concepts":
        return check_concepts()
    if args.command == "cdm":
        return build_cdm(years=args.years)
    if args.command == "cohorts":
        return build_cohorts(years=args.years)
    raise AssertionError(f"unhandled command: {args.command}")  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())
