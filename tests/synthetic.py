"""The synthetic source the database tests load: records, configuration, manifest, vocabulary.

Eight 2023 records each carry a trap: a normal case, an exact duplicate, weeks and visits out of any
plausible range, "no especificado" everywhere, empty fields, no year of birth for the mother, values
that do not cast, and twins. Two 2022 records test a load of several years. The fixture imitates
traps, not volumes.

The configuration, the manifest and the vocabulary are synthetic too, with concept ids above
2,000,000,000, the OMOP range for local concepts (D-023). ``data/`` is never touched.

It is shared by the tests of the ETL (task 1.4.4) and of the cohorts (task 1.5.1), which load the
same traps into schemas of their own.
"""

import csv
import io
import textwrap
import uuid
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from psycopg import sql

import etl
import sql_runner
import stage
from sinac_truncation.concepts import STCM_COLUMNS
from sinac_truncation.etl import SOURCE_COLUMNS, person_id

#: One record per trap, in the order of SOURCE_COLUMNS: FECHANACIMIENTO, FECHANACIMIENTOMADRE,
#: EDAD, RESIDEEXTRANJERO, ENTIDADRESIDENCIA, EDADGESTACIONAL, PRODUCTOEMBARAZO, TOTALCONSULTAS,
#: TRIMESTREPRIMERCONSULTA. ``None`` is a blank cell, which staging holds as NULL (D-069).
RECORDS_2023: tuple[tuple[str | None, ...], ...] = (
    # 1. The normal case.
    ("15/03/2023", "02/05/1995", "27", "2", "09", "39", "1", "8", "1"),
    # 2. An exact duplicate of 1: kept, as a second PERSON (D-058).
    ("15/03/2023", "02/05/1995", "27", "2", "09", "39", "1", "8", "1"),
    # 3. Out of any plausible range, kept as they are (D-053, D-058); three or more; no care.
    ("20/06/2023", "11/11/2000", "22", "2", "00", "12", "3", "45", "0"),
    # 4. "No especificado" everywhere; 88 is not in SI_NO (D-057); the mother's date is a code.
    ("01/01/2023", "09/09/9999", "30", "88", "00", "99", "0", "99", "8"),
    # 5. Empty fields; resident abroad; a mother's date that is not a day of the calendar.
    ("31/12/2023", "31/02/1990", "33", "1", "88", None, "1", None, None),
    # 6. Neither the mother's date of birth nor her age: not loaded (D-060).
    ("10/07/2023", "99/99/9999", "999", "2", "15", "38", "1", "5", "2"),
    # 7. Values that do not cast (D-075); a mother born after the delivery.
    ("05/05/2023", "01/01/2024", "25", "3", "9", "ab", "7", " 7", "5"),
    # 8. Twins; no visits, which is an answer; a mother born on a leap day.
    ("28/02/2023", "29/02/1996", "26", "2", "31", "34", "2", "0", "1"),
)

RECORDS_2022: tuple[tuple[str | None, ...], ...] = (
    ("03/03/2022", "15/08/1990", "31", "2", "09", "38", "1", "10", "1"),
    ("04/04/2022", "20/01/1985", "37", "2", "14", "36", "1", "6", "2"),
)

SHA256 = {2023: "a" * 64, 2022: "b" * 64}
VERSION = "v5.0 SYNTH"

FEMALE, REGISTRY, WEEKS, WEEK, PLURALITY, AT_LEAST, VISITS, TRIMESTER, CDM_VERSION = range(
    2_000_000_001, 2_000_000_010
)
FIRST, SECOND, THIRD, NO_CARE, MEXICO = range(2_000_000_011, 2_000_000_016)
NOT_IN_CONCEPT = 2_000_000_099


def _concept(concept_id: int, domain: str, *fields: str) -> dict[str, Any]:
    return {
        "concept_id": concept_id,
        "concept_name": f"Synthetic {concept_id}",
        "vocabulary_id": "SYNTH",
        "concept_code": str(concept_id),
        "domain_id": domain,
        "standard_concept": "S",
        "cdm_fields": list(fields),
    }


CONCEPTS: dict[str, dict[str, Any]] = {
    "female": _concept(FEMALE, "Gender", "person.gender_concept_id"),
    "registry": _concept(
        REGISTRY,
        "Type Concept",
        "observation_period.period_type_concept_id",
        "measurement.measurement_type_concept_id",
        "observation.observation_type_concept_id",
    ),
    "gestational_age_at_birth": _concept(
        WEEKS, "Measurement", "measurement.measurement_concept_id"
    ),
    "week": _concept(WEEK, "Unit", "measurement.unit_concept_id"),
    "birth_plurality": _concept(PLURALITY, "Measurement", "measurement.measurement_concept_id"),
    "at_least": _concept(AT_LEAST, "Meas Value Operator", "measurement.operator_concept_id"),
    "prenatal_visits_count": _concept(VISITS, "Observation", "observation.observation_concept_id"),
    "first_prenatal_visit_trimester": _concept(
        TRIMESTER, "Observation", "observation.observation_concept_id"
    ),
    "cdm_version": _concept(CDM_VERSION, "Metadata", "cdm_source.cdm_version_concept_id"),
}


def _vocabulary(column: str, defined_in: str, field: str, domain: str | None) -> dict[str, Any]:
    return {
        "source_column": column,
        "defined_in": defined_in,
        "cdm_field": field,
        "target_domain_id": domain,
    }


SOURCE_VOCABULARIES: dict[str, dict[str, Any]] = {
    "SINAC20_EDADGEST": _vocabulary(
        "EDADGESTACIONAL", "descriptor", "measurement.value_as_number", None
    ),
    "SINAC20_PRODEMB": _vocabulary(
        "PRODUCTOEMBARAZO", "PRODUCTO_EMBARAZO", "measurement.value_as_number", None
    ),
    "SINAC20_TOTCONS": _vocabulary(
        "TOTALCONSULTAS", "descriptor", "observation.value_as_number", None
    ),
    "SINAC20_TRIMCONS": _vocabulary(
        "TRIMESTREPRIMERCONSULTA",
        "TRIMESTRE_PRIMER_CONSULTA",
        "observation.value_as_concept_id",
        "Meas Value",
    ),
    "SINAC20_RESEXT": _vocabulary(
        "RESIDEEXTRANJERO", "SI_NO", "location.country_concept_id", "Geography"
    ),
    "SINAC20_ENTRES": _vocabulary("ENTIDADRESIDENCIA", "ENTIDADES", "location.state", None),
    "SINAC20_EDAD": _vocabulary("EDAD", "descriptor", "person.year_of_birth", None),
    "SINAC20_FECHANACMAD": _vocabulary(
        "FECHANACIMIENTOMADRE", "descriptor", "person.year_of_birth", None
    ),
}

#: (vocabulary, code, target). The codes are the ones docs/omop_mapping.md lists; the targets are
#: synthetic.
MAP: tuple[tuple[str, str, int], ...] = (
    ("SINAC20_EDADGEST", "99", 0),
    ("SINAC20_PRODEMB", "0", 0),
    ("SINAC20_TOTCONS", "99", 0),
    ("SINAC20_TRIMCONS", "0", NO_CARE),
    ("SINAC20_TRIMCONS", "1", FIRST),
    ("SINAC20_TRIMCONS", "2", SECOND),
    ("SINAC20_TRIMCONS", "3", THIRD),
    ("SINAC20_TRIMCONS", "8", 0),
    ("SINAC20_TRIMCONS", "9", 0),
    ("SINAC20_RESEXT", "0", 0),
    ("SINAC20_RESEXT", "1", 0),
    ("SINAC20_RESEXT", "2", MEXICO),
    ("SINAC20_RESEXT", "8", 0),
    ("SINAC20_RESEXT", "9", 0),
    ("SINAC20_RESEXT", "88", 0),
    ("SINAC20_ENTRES", "00", 0),
    ("SINAC20_ENTRES", "88", 0),
    ("SINAC20_ENTRES", "99", 0),
    ("SINAC20_EDAD", "888", 0),
    ("SINAC20_EDAD", "999", 0),
    ("SINAC20_FECHANACMAD", "09/09/9999", 0),
)


def map_csv(rows: Sequence[tuple[str, str, int]]) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(STCM_COLUMNS)
    for vocabulary, code, target in rows:
        target_vocabulary = "None" if target == 0 else "SYNTH"
        writer.writerow(
            [code, 0, vocabulary, "synthetic", target, target_vocabulary, "2020-01-01",
             "2023-12-31", ""]
        )  # fmt: skip
    return out.getvalue()


def manifest_text() -> str:
    tables = ("vocabulary", "domain", "concept_class", "relationship", "concept",
              "concept_relationship", "concept_ancestor")  # fmt: skip
    head = textwrap.dedent(
        f"""\
        downloads:
          - id: dgis_sinac_2023
            page: http://example.test/nacimientos.html
            url: http://example.test/nacimientos/sinac_2023.zip?V=2024.05.14
            version: "2024.05.14"
            retrieved_at: "2026-09-20T12:44:57Z"
            size_bytes: 100
            sha256: "{SHA256[2023]}"
          - id: dgis_sinac_2022
            page: http://example.test/nacimientos.html
            url: http://example.test/nacimientos/sinac_2022.zip?V=2023.05.23
            version: "2023.05.23"
            retrieved_at: "2026-09-21T10:00:00Z"
            size_bytes: 100
            sha256: "{SHA256[2022]}"
          - id: dgis_sinac_descriptores_2020_2025
            url: http://example.test/nacimientos/descriptores.zip?V=2026.07.09
            version: "2026.07.09"
          - id: dgis_sinac_catalogos_2020_2023
            url: http://example.test/nacimientos/catalogos.zip?V=1.1
            version: "1.1"
        vocabulary:
          file: "athena/package.zip"
          size_bytes: 1
          sha256: "{"c" * 64}"
          vocabulary_version: "{VERSION}"
          not_loaded: []
          rows:
        """
    )
    return head + "".join(f"    {table}: 1\n" for table in tables)


#: The CONCEPT rows the anti-joins look up: every synthetic id, and 0.
CONCEPT_ROWS: tuple[tuple[object, ...], ...] = (
    (0, "No matching concept", "Metadata", "None", "Undefined", None, "No matching concept"),
    *(
        (concept_id, f"Synthetic {concept_id}", "Metadata", "SYNTH", "Undefined", "S",
         str(concept_id))
        for concept_id in range(2_000_000_001, 2_000_000_016)
    ),
)  # fmt: skip


def fetch(connection: sql_runner.Connection, query: str, *params: object) -> list[tuple[Any, ...]]:
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()


def copy_rows(
    connection: sql_runner.Connection,
    table: sql.Identifier,
    columns: Sequence[str],
    rows: Sequence[Sequence[object]],
) -> None:
    statement = sql.SQL("COPY {} ({}) FROM STDIN").format(
        table, sql.SQL(", ").join(sql.Identifier(column) for column in columns)
    )
    with connection.cursor() as cursor, cursor.copy(statement) as copy:
        for row in rows:
            copy.write_row(row)


@contextmanager
def module_schemas(
    connection: sql_runner.Connection, ddl_files: Sequence[Path], prefix: str
) -> Iterator[etl.Schemas]:
    """Schemas of one test module, with the vendored DDL applied, dropped when it ends."""
    suffix = uuid.uuid4().hex[:8]
    names = etl.Schemas(
        cdm=f"{prefix}_cdm_{suffix}",
        staging=f"{prefix}_staging_{suffix}",
        results=f"{prefix}_results_{suffix}",
    )
    listed = (names.cdm, names.staging, names.results)
    sql_runner.ensure_schemas(connection, listed)
    try:
        sql_runner.run_sql_files(connection, ddl_files, names.markers)
        yield names
    finally:
        sql_runner.drop_schemas(connection, listed)


@dataclass(frozen=True)
class Source:
    """The synthetic vocabulary, staging, configuration and manifest of one test."""

    connection: sql_runner.Connection
    schemas: etl.Schemas
    config_dir: Path
    manifest: Path

    def run(self, years: Sequence[int] = (2023,)) -> list[tuple[int | None, str, str, int]]:
        return etl.run(
            self.connection,
            years,
            schemas=self.schemas,
            config_dir=self.config_dir,
            sources_path=self.manifest,
            reference="https://example.test/repo at commit synthetic",
        )

    def stage(self, year: int, records: Sequence[Sequence[str | None]]) -> None:
        """Rebuild a staging table and its load counts as `pipeline.py stage` leaves them."""
        table = sql.Identifier(self.schemas.staging, f"sinac_{year}")
        columns = [column.lower() for column in SOURCE_COLUMNS]
        definitions = sql.SQL(", ").join(
            sql.SQL("{} text").format(sql.Identifier(column)) for column in (*columns, "clues")
        )
        with self.connection.cursor() as cursor:
            cursor.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(table))
            cursor.execute(
                sql.SQL("CREATE TABLE {} (source_row integer PRIMARY KEY, {})").format(
                    table, definitions
                )
            )
        copy_rows(
            self.connection,
            table,
            ("source_row", *columns, "clues"),
            [(row, *values, f"SYNTH{row:05d}") for row, values in enumerate(records, start=1)],
        )
        counts = sql.Identifier(self.schemas.staging, "load_counts")
        with self.connection.cursor() as cursor:
            cursor.execute(sql.SQL("DELETE FROM {} WHERE source_year = %s").format(counts), (year,))
        copy_rows(
            self.connection,
            counts,
            ("source_year", "stage", "row_count", "source_member", "source_sha256"),
            [
                (year, name, len(records), f"Nacimientos_{year}.csv", SHA256[year])
                for name in ("csv", "parquet", "table")
            ],
        )

    def table(self, name: str, order: str) -> list[tuple[Any, ...]]:
        return fetch(self.connection, f"SELECT * FROM {self.schemas.cdm}.{name} ORDER BY {order}")

    def counts(self) -> list[tuple[Any, ...]]:
        return fetch(
            self.connection,
            "SELECT source_year, cdm_table, rule, row_count "
            f"FROM {self.schemas.results}.etl_counts "
            "ORDER BY cdm_table, rule, source_year NULLS FIRST",
        )

    def snapshot(self) -> dict[str, list[tuple[Any, ...]]]:
        """Everything a run writes, except the date of the run itself."""
        cdm, results = self.schemas.cdm, self.schemas.results
        return {
            "person": self.table("person", "person_id"),
            "observation_period": self.table("observation_period", "observation_period_id"),
            "measurement": self.table("measurement", "measurement_id"),
            "observation": self.table("observation", "observation_id"),
            "location": self.table("location", "location_id"),
            "source_to_concept_map": self.table(
                "source_to_concept_map", "source_vocabulary_id, source_code"
            ),
            "vocabulary": self.table("vocabulary", "vocabulary_id"),
            "cdm_source": fetch(
                self.connection,
                f"SELECT cdm_source_name, source_description, source_documentation_reference, "
                f"cdm_etl_reference, source_release_date, cdm_version, cdm_version_concept_id, "
                f"vocabulary_version FROM {cdm}.cdm_source",
            ),
            "etl_counts": self.counts(),
            "concept_sets": fetch(
                self.connection, f"SELECT * FROM {results}.concept_sets ORDER BY concept_key"
            ),
        }


def prepare_source(
    connection: sql_runner.Connection, schemas: etl.Schemas, tmp_path: Path
) -> Source:
    """Write the configuration and the manifest, load the vocabulary rows and stage both years."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "concept_sets.yml").write_text(
        yaml.safe_dump({"concepts": CONCEPTS, "source_vocabularies": SOURCE_VOCABULARIES}),
        encoding="utf-8",
    )
    (config_dir / "source_to_concept_map.csv").write_text(map_csv(MAP), encoding="utf-8")
    manifest = tmp_path / "sources.yml"
    manifest.write_text(manifest_text(), encoding="utf-8")

    cdm = schemas.cdm
    with connection.cursor() as cursor:
        cursor.execute(f"TRUNCATE {cdm}.concept, {cdm}.vocabulary, {cdm}.visit_occurrence")
    copy_rows(
        connection,
        sql.Identifier(cdm, "concept"),
        ("concept_id", "concept_name", "domain_id", "vocabulary_id", "concept_class_id",
         "standard_concept", "concept_code", "valid_start_date", "valid_end_date"),
        [(*row, "2020-01-01", "2099-12-31") for row in CONCEPT_ROWS],
    )  # fmt: skip
    copy_rows(
        connection,
        sql.Identifier(cdm, "vocabulary"),
        ("vocabulary_id", "vocabulary_name", "vocabulary_version", "vocabulary_concept_id"),
        [("None", "OMOP Standardized Vocabularies", VERSION, 2_000_000_100),
         ("SYNTH", "Synthetic vocabulary", None, 2_000_000_101)],
    )  # fmt: skip
    sql_runner.run_sql_file(connection, stage.LOAD_COUNTS_SQL, schemas.markers)

    prepared = Source(connection, schemas, config_dir, manifest)
    prepared.stage(2023, RECORDS_2023)
    prepared.stage(2022, RECORDS_2022)
    return prepared


def pid(row: int, year: int = 2023) -> int:
    return person_id(year, row)
