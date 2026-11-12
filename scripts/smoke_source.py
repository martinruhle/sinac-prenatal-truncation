"""Writing the synthetic source of the smoke run to disk (task 1.9.4, D-136).

The I/O lives here (rule 6): reading the configuration, zipping, hashing and writing. What goes
into each file is pure and lives in :mod:`sinac_truncation.smoke`.

Everything lands under one root, laid out as the real source is under the repository root, so
the steps of the pipeline read it with their usual code and only their paths change:

    <root>/sources.yml                    the manifest, in place of config/sources.yml
    <root>/data/raw/dgis/sinac_<year>.zip  one record file per year, as `download` leaves it
    <root>/data/raw/athena/package.zip     the vocabulary package, as `vocab` reads it

The configuration is the real one (config/concept_sets.yml and config/source_to_concept_map.csv),
so the smoke run checks the concepts and the map the pipeline actually uses.
"""

import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml

import download
import validate_concepts
from sinac_truncation.etl import CATALOGUE_SOURCE, DESCRIPTOR_SOURCE
from sinac_truncation.integrity import digest_chunks
from sinac_truncation.smoke import (
    manifest,
    record_csv,
    records,
    vocabulary_members,
    vocabulary_rows,
)

#: The vocabulary package, relative to the fixture root.
PACKAGE = "data/raw/athena/package.zip"

#: A fixed timestamp for every member, so two builds of the same fixture hold the same bytes.
_ZIP_DATE = (2026, 1, 1, 0, 0, 0)


class FixtureError(RuntimeError):
    """The configuration cannot be turned into a fixture."""


@dataclass(frozen=True)
class FixtureSource:
    """Where the steps of the pipeline find the synthetic source."""

    root: Path
    sources_path: Path
    raw_dir: Path
    extracted_dir: Path
    interim_dir: Path


def _write_zip(path: Path, members: Mapping[str, bytes]) -> tuple[str, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in members.items():
            archive.writestr(zipfile.ZipInfo(name, date_time=_ZIP_DATE), data)
    digest = digest_chunks([path.read_bytes()])
    return digest.sha256, digest.size_bytes


def write(
    root: Path, years: Sequence[int], *, config_dir: Path = validate_concepts.CONFIG_DIR
) -> FixtureSource:
    """Write the record files of ``years``, the vocabulary package and their manifest under
    ``root``, which must be empty or not exist.

    Raises:
        FixtureError: ``root`` holds something, or the configuration fails its own checks.
    """
    if root.exists() and any(root.iterdir()):
        raise FixtureError(f"{root} is not empty; the fixture is written to an empty directory")
    config, map_rows, problems = validate_concepts.read_config(config_dir)
    if problems:
        raise FixtureError("the configuration fails its own checks:\n  " + "\n  ".join(problems))

    raw_dir = root / "data" / "raw" / "dgis"
    record_files: dict[str, tuple[int, str, int]] = {}
    for year in years:
        entry_id = download.record_id(year)
        sha256, size = _write_zip(
            raw_dir / f"sinac_{year}.zip", {f"Nacimientos_{year}.csv": record_csv(records(year))}
        )
        record_files[entry_id] = (year, sha256, size)

    tables = vocabulary_rows(config, map_rows)
    package = _write_zip(root / PACKAGE, vocabulary_members(tables))
    document = manifest(
        record_files,
        (PACKAGE, *package),
        {table: len(rows) for table, rows in tables.items()},
        descriptor_id=DESCRIPTOR_SOURCE,
        catalogue_id=CATALOGUE_SOURCE,
    )
    sources_path = root / "sources.yml"
    sources_path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    print(
        f"wrote the synthetic source of {', '.join(map(str, years))}: "
        f"{len(tables['concept'])} concepts, under {root}"
    )
    return FixtureSource(
        root=root,
        sources_path=sources_path,
        raw_dir=raw_dir,
        extracted_dir=raw_dir / "extracted",
        interim_dir=root / "data" / "interim",
    )
