"""Tests for the staging layer: ZIP → CSV → Parquet → the ``staging`` schema.

The record file is synthetic and built here, in code: the published header of 2020–2023 with a
few invented records that carry the values an early cast or a careless reader would damage.
It is written as bytes rather than committed as a fixture, so the CRLF line endings of the DGIS
files survive ``.gitattributes`` (``eol=lf``). The manifest is a small synthetic file as well;
the real ``config/sources.yml`` and ``data/`` are never touched.

Tests marked ``db`` load into the throwaway schemas of ``conftest.py``, never into ``staging``.
"""

import hashlib
import textwrap
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import pytest

import sql_runner
import stage
from sinac_truncation.staging import SOURCE_ROW, staged_columns, staged_value

YEAR = 2023
MEMBER = "Nacimientos_2023.csv"

#: The 64 column names of the 2020–2023 record files, in their published order: the four headers
#: are identical (docs/source_inventory.md). Names only; no record is copied from any file.
HEADER = (
    "NACIOEXTRANJERO", "ENTIDADNACIMIENTO", "MUNICIPIONACIMIENTO", "EDAD",
    "SECONSIDERAINDIGENA", "HABLALENGUAINDIGENA", "FECHANACIMIENTOMADRE", "ESTADOCONYUGAL",
    "RESIDEEXTRANJERO", "ENTIDADRESIDENCIA", "MUNICIPIORESIDENCIA", "LOCALIDADRESIDENCIA",
    "NUMEROEMBARAZOS", "HIJOSNACIDOSMUERTOS", "HIJOSNACIDOSVIVOS", "HIJOSSOBREVIVIENTES",
    "CONDICIONHIJOANTERIOR", "VIVEHIJOANTERIOR", "ORDENNACIMIENTO", "ATENCIONPRENATAL",
    "TRIMESTREPRIMERCONSULTA", "TOTALCONSULTAS", "SOBREVIVIOPARTO", "AFILIACION",
    "ESCOLARIDAD", "INTERRUMPIOESTUDIOS", "CLAVEOCUPACIONHABITUAL", "TRABAJAACTUALMENTE",
    "EDADPADRE", "FECHANACIMIENTO", "HORANACIMIENTO", "SEXO", "EDADGESTACIONAL", "TALLA",
    "PESO", "APGAR", "SILVERMAN", "TAMIZAUDITIVO", "VACUNA_BCG", "VACUNAHEPATITIS_B",
    "VITAMINA_A", "VITAMINA_K", "PRODUCTOEMBARAZO", "ORDENPRODUCTO", "TOTALPRODUCTOS",
    "CODIGOCIEANOMALIA1", "CODIGOCIEANOMALIA2", "LUGARNACIMIENTO", "CLUES", "TIEMPOTRASLADO",
    "RESOLUCIONEMBARAZO", "UTILIZOFORCEPS", "TIPOCESAREA", "PERSONALATENDIO",
    "TIPOMEDICOATENDIO", "ENTIDADFEDERATIVAPARTO", "MUNICIPIOPARTO", "LOCALIDADPARTO",
    "CERTIFICADOPOR", "CLUESCERTIFICA", "ENTIDADFEDERATIVACERTIFICA", "MUNICIPIOCERTIFICA",
    "LOCALIDADCERTIFICA", "FECHACERTIFICADO",
)  # fmt: skip

#: The traps, one invented record each. A string is written quoted, ``""`` is a quoted empty
#: field and ``None`` an empty field without quotes; every other column holds "1", and `CLUES`
#: marks the position of the record in the file.
TRAPS: tuple[Mapping[str, str | None], ...] = (
    {"ENTIDADRESIDENCIA": "09", "ENTIDADNACIMIENTO": "00", "MUNICIPIORESIDENCIA": "001"},
    {
        "EDADGESTACIONAL": "99",
        "EDAD": "999",
        "PESO": "9999",
        "FECHANACIMIENTOMADRE": "09/09/9999",
        "HORANACIMIENTO": "99:99",
        "RESIDEEXTRANJERO": "88",
    },
    {"TOTALCONSULTAS": None, "ORDENPRODUCTO": "", "TOTALPRODUCTOS": "  "},
    {"LOCALIDADPARTO": 'EL ALTO, "BARRIO"'},
    {"LOCALIDADCERTIFICA": "SANTA MARÍA DEL ÑANDÚ"},
    {"LOCALIDADRESIDENCIA": "PRIMERA\nSEGUNDA"},
    {"FECHANACIMIENTO": "01/02/2023", "TRIMESTREPRIMERCONSULTA": "0"},
    {},
)


def record(position: int, trap: Mapping[str, str | None]) -> list[str | None]:
    cells: dict[str, str | None] = dict.fromkeys(HEADER, "1")
    cells["CLUES"] = f"SYNTH{position:05d}"
    cells.update(trap)
    return [cells[name] for name in HEADER]


RECORDS = [record(position, trap) for position, trap in enumerate(TRAPS, start=1)]

#: What staging must hold for each record, in file order: blank cells, quoted or not, are NULL.
EXPECTED = [tuple(None if cell is None else staged_value(cell) for cell in row) for row in RECORDS]


def csv_line(cells: Sequence[str | None]) -> str:
    quoted = ("" if cell is None else '"' + cell.replace('"', '""') + '"' for cell in cells)
    return ",".join(quoted) + "\r\n"


def csv_bytes(rows: Sequence[Sequence[str | None]]) -> bytes:
    return (csv_line(HEADER) + "".join(csv_line(row) for row in rows)).encode("utf-8")


def zip_bytes(members: Mapping[str, bytes], path: Path) -> bytes:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    return path.read_bytes()


def manifest_text(content: bytes) -> str:
    return textwrap.dedent(
        f"""\
        downloads:
          - id: dgis_sinac_{YEAR}
            url: http://example.test/nacimientos/sinac_{YEAR}.zip?V=2024.05.14
            version: "2024.05.14"
            retrieved_at: "2026-09-24T00:00:00Z"
            size_bytes: {len(content)}
            sha256: "{hashlib.sha256(content).hexdigest()}"
        """
    )


@dataclass(frozen=True)
class Source:
    """A synthetic source laid out as the pipeline expects it, all under ``tmp_path``."""

    raw_dir: Path
    extracted_dir: Path
    interim_dir: Path
    manifest: Path

    @property
    def zip_path(self) -> Path:
        return self.raw_dir / f"sinac_{YEAR}.zip"


def make_source(
    tmp_path: Path,
    members: Mapping[str, bytes] | None = None,
    recorded: bytes | None = None,
) -> Source:
    """Write the ZIP and a manifest that records it (or records ``recorded`` instead)."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    content = zip_bytes(members or {MEMBER: csv_bytes(RECORDS)}, raw_dir / f"sinac_{YEAR}.zip")
    manifest = tmp_path / "sources.yml"
    manifest.write_text(manifest_text(content if recorded is None else recorded), "utf-8")
    return Source(
        raw_dir=raw_dir,
        extracted_dir=raw_dir / "extracted",
        interim_dir=tmp_path / "interim",
        manifest=manifest,
    )


@pytest.fixture
def source(tmp_path: Path) -> Source:
    return make_source(tmp_path)


def prepare(source: Source) -> stage.Prepared:
    return stage.prepare(
        YEAR,
        raw_dir=source.raw_dir,
        extracted_dir=source.extracted_dir,
        interim_dir=source.interim_dir,
        sources_path=source.manifest,
    )


def parquet_rows(path: Path) -> list[tuple[Any, ...]]:
    with duckdb.connect() as duck:
        return duck.execute(
            "SELECT * EXCLUDE (file_row_number) FROM read_parquet($1, file_row_number = true) "
            "ORDER BY file_row_number",
            [str(path)],
        ).fetchall()


# --- File stages: no database -------------------------------------------------------------------


def test_every_stage_counts_every_record(source: Source) -> None:
    prepared = prepare(source)
    assert prepared.scan.records == prepared.parquet_rows == len(RECORDS)
    assert prepared.columns == staged_columns(HEADER)
    assert prepared.parquet_path == source.interim_dir / f"sinac_{YEAR}.parquet"


def test_the_parquet_copy_keeps_every_value_as_text(source: Source) -> None:
    prepared = prepare(source)
    with duckdb.connect() as duck:
        types = duck.execute(
            "SELECT column_type FROM (DESCRIBE SELECT * FROM read_parquet($1))",
            [str(prepared.parquet_path)],
        ).fetchall()
    assert types == [("VARCHAR",)] * len(HEADER)
    assert parquet_rows(prepared.parquet_path) == EXPECTED


def test_the_sample_holds_the_last_record_as_staging_must_hold_it(source: Source) -> None:
    prepared = prepare(source)
    assert prepared.scan.samples == {len(RECORDS): EXPECTED[-1]}


def test_a_second_run_writes_the_same_parquet_and_reuses_the_csv(
    source: Source, capsys: pytest.CaptureFixture[str]
) -> None:
    first = prepare(source)
    content = parquet_rows(first.parquet_path)
    assert "(reused)" not in capsys.readouterr().out

    second = prepare(source)
    assert "(reused)" in capsys.readouterr().out
    assert parquet_rows(second.parquet_path) == content
    assert not list(source.interim_dir.glob("*.part"))


def test_a_damaged_extracted_copy_is_replaced(source: Source) -> None:
    csv_path, reused = stage.extract(source.zip_path, source.extracted_dir)
    assert not reused
    whole = csv_path.read_bytes()

    csv_path.write_bytes(whole[:-10])
    _, reused = stage.extract(source.zip_path, source.extracted_dir)
    assert not reused
    assert csv_path.read_bytes() == whole

    _, reused = stage.extract(source.zip_path, source.extracted_dir)
    assert reused


def test_a_zip_with_two_csv_members_is_refused(tmp_path: Path) -> None:
    source = make_source(tmp_path, members={MEMBER: csv_bytes(RECORDS), "other.csv": b"A\r\n"})
    with pytest.raises(stage.StageError, match="exactly one CSV member"):
        prepare(source)


def test_a_zip_that_is_not_the_recorded_one_is_refused(tmp_path: Path) -> None:
    source = make_source(tmp_path, recorded=b"the file that was recorded")
    with pytest.raises(stage.StageError, match="sha256 mismatch"):
        prepare(source)
    assert not source.extracted_dir.exists()


def test_a_zip_that_was_never_downloaded_is_refused(source: Source) -> None:
    source.zip_path.unlink()
    with pytest.raises(stage.StageError, match="download --years 2023"):
        prepare(source)


def test_a_short_record_stops_the_run_before_the_parquet(tmp_path: Path) -> None:
    short = csv_bytes(RECORDS) + b'"1","2"\r\n'
    source = make_source(tmp_path, members={MEMBER: short})
    with pytest.raises(stage.StageError, match="record 9 has 2 fields"):
        prepare(source)
    assert not source.interim_dir.exists()


def test_duckdb_refuses_a_short_record_too_and_leaves_no_file(tmp_path: Path) -> None:
    """The Python count catches it first; DuckDB must not drop it silently either."""
    csv_path = tmp_path / MEMBER
    csv_path.write_bytes(csv_bytes(RECORDS) + b'"1","2"\r\n')
    parquet_path = tmp_path / "interim" / "out.parquet"
    with (
        stage.duckdb_connection(tmp_path / "interim") as duck,
        pytest.raises(stage.StageError, match="DuckDB could not read"),
    ):
        stage.write_parquet(duck, csv_path, parquet_path)
    assert not list((tmp_path / "interim").glob("out.parquet*"))


# --- Loading into Postgres: the compose database ----------------------------------------------


def run(source: Source, connection: sql_runner.Connection, schema: str) -> None:
    stage.run(
        YEAR,
        conn=connection,
        schema=schema,
        raw_dir=source.raw_dir,
        extracted_dir=source.extracted_dir,
        interim_dir=source.interim_dir,
        sources_path=source.manifest,
    )


def fetch(connection: sql_runner.Connection, query: str, *params: object) -> list[tuple[Any, ...]]:
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()


def load_counts(connection: sql_runner.Connection, schema: str) -> list[tuple[Any, ...]]:
    return fetch(
        connection,
        f"SELECT source_year, stage, row_count, source_member, source_sha256 "
        f"FROM {schema}.load_counts ORDER BY source_year, stage",
    )


@pytest.mark.db
def test_two_runs_leave_the_same_counts_and_the_three_agree(
    db_connection: sql_runner.Connection, temp_schemas: Mapping[str, str], source: Source
) -> None:
    schema = temp_schemas["staging"]
    run(source, db_connection, schema)
    first = load_counts(db_connection, schema)
    run(source, db_connection, schema)
    assert load_counts(db_connection, schema) == first

    sha256 = hashlib.sha256(source.zip_path.read_bytes()).hexdigest()
    assert first == [
        (YEAR, stage_name, len(RECORDS), MEMBER, sha256)
        for stage_name in ("csv", "parquet", "table")
    ]


@pytest.mark.db
def test_the_table_holds_every_source_column_as_text(
    db_connection: sql_runner.Connection, temp_schemas: Mapping[str, str], source: Source
) -> None:
    schema = temp_schemas["staging"]
    run(source, db_connection, schema)
    columns = fetch(
        db_connection,
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
        schema,
        f"sinac_{YEAR}",
    )
    assert columns == [(SOURCE_ROW, "integer")] + [
        (name, "text") for name in staged_columns(HEADER)
    ]
    primary_key = fetch(
        db_connection,
        "SELECT a.attname FROM pg_index i "
        "JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
        "WHERE i.indrelid = %s::regclass AND i.indisprimary",
        f"{schema}.sinac_{YEAR}",
    )
    assert primary_key == [(SOURCE_ROW,)]


@pytest.mark.db
def test_the_table_holds_the_file_in_file_order(
    db_connection: sql_runner.Connection, temp_schemas: Mapping[str, str], source: Source
) -> None:
    """The same ordinals on every load, in file order (docs/omop_mapping.md, rule 7)."""
    schema = temp_schemas["staging"]
    for _ in range(2):
        run(source, db_connection, schema)
        rows = fetch(db_connection, f"SELECT * FROM {schema}.sinac_{YEAR} ORDER BY source_row")
        assert rows == [(position, *values) for position, values in enumerate(EXPECTED, start=1)]


@pytest.mark.db
def test_a_failed_load_keeps_the_previous_one(
    db_connection: sql_runner.Connection,
    temp_schemas: Mapping[str, str],
    source: Source,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The table is dropped and refilled inside the transaction the failed check rolls back."""
    schema = temp_schemas["staging"]
    run(source, db_connection, schema)
    counts = load_counts(db_connection, schema)

    def copy_nothing(*args: object, **kwargs: object) -> None:
        """A COPY that loses every row, after the table has been dropped and created again."""

    monkeypatch.setattr(stage, "_copy_rows", copy_nothing)
    with pytest.raises(stage.StageError, match="table 0. The previous load was kept"):
        run(source, db_connection, schema)

    assert load_counts(db_connection, schema) == counts
    rows = fetch(db_connection, f"SELECT count(*) FROM {schema}.sinac_{YEAR}")
    assert rows == [(len(RECORDS),)]
