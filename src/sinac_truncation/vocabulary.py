"""Pure helpers for loading the OMOP standardized vocabularies from an Athena package.

There is no file or database I/O here (CLAUDE.md rule 6): ``scripts/load_vocab.py`` opens the ZIP
and Postgres, and uses these functions to read the ``vocabulary:`` block of ``config/sources.yml``,
to check the package against it before anything is loaded, and to count what streams through.

The package format was inspected before the first load and is recorded in the manifest:
tab-delimited, a header row, no quoting (some concept names hold a literal double quote), dates as
YYYYMMDD. The files are loaded as they are, with quoting turned off (D-071).
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath

from sinac_truncation.integrity import DigestResult, IntegrityError, normalise_digest

__all__ = [
    "DELIMITER",
    "LOADED_TABLES",
    "NO_MATCHING_VOCABULARY",
    "QUOTE",
    "StreamTally",
    "VocabularyError",
    "VocabularyPackage",
    "digest_problem",
    "header_problem",
    "member_name",
    "member_problems",
    "package_from_manifest",
    "version_from_lines",
]

#: The vocabulary tables that are loaded, small reference tables first. CONCEPT_SYNONYM and
#: DRUG_STRENGTH are deliberately not among them (task 1.4.3), even though the CDM has both.
LOADED_TABLES: tuple[str, ...] = (
    "vocabulary",
    "domain",
    "concept_class",
    "relationship",
    "concept",
    "concept_relationship",
    "concept_ancestor",
)

#: The field separator of every Athena file.
DELIMITER = "\t"

#: The quote character ``COPY`` is given. Athena does not quote, so quoting is turned off by naming
#: a byte the package never holds (backspace); the load fails if one ever appears (D-071).
QUOTE = "\b"

#: The ``vocabulary_id`` whose ``VOCABULARY`` row carries the version of the whole package, and
#: the vocabulary of concept 0, "No matching concept".
NO_MATCHING_VOCABULARY = "None"

_QUOTE_BYTE = QUOTE.encode("ascii")


class VocabularyError(ValueError):
    """The package, or its entry in the manifest, is not what the loader can accept."""


def member_name(table: str) -> str:
    """The file of one table in the package, such as ``CONCEPT.csv``."""
    return f"{table.upper()}.csv"


@dataclass(frozen=True)
class VocabularyPackage:
    """The ``vocabulary:`` block of the manifest: what the loaded package must be."""

    #: The ZIP, relative to the repository root (rule 12).
    file: str
    size_bytes: int
    sha256: str
    #: ``vocabulary_version`` of the ``VOCABULARY`` row whose ``vocabulary_id`` is ``'None'``.
    vocabulary_version: str
    #: Data rows of each loaded table, header excluded.
    rows: Mapping[str, int]
    #: Members of the ZIP that are not loaded, by file name.
    not_loaded: tuple[str, ...]


def _count(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _text(block: Mapping[str, object], key: str) -> str:
    value = block.get(key)
    if not isinstance(value, str) or not value.strip():
        raise VocabularyError(f"vocabulary: {key} is missing")
    return value


def package_from_manifest(document: object) -> VocabularyPackage:
    """Read the ``vocabulary:`` block of the parsed manifest.

    Raises:
        VocabularyError: the block is missing, a field is missing or malformed, the file is given
            as an absolute path, or ``rows`` does not list exactly the loaded tables.
    """
    block = document.get("vocabulary") if isinstance(document, Mapping) else None
    if not isinstance(block, Mapping):
        raise VocabularyError("the manifest has no `vocabulary:` block")

    file = _text(block, "file")
    if PurePosixPath(file).is_absolute() or PureWindowsPath(file).is_absolute():
        raise VocabularyError("vocabulary: file must be relative to the repository root")

    size = _count(block.get("size_bytes"))
    if not size:
        raise VocabularyError("vocabulary: size_bytes must be a positive integer")

    try:
        sha256 = normalise_digest(_text(block, "sha256"))
    except IntegrityError as error:
        raise VocabularyError(f"vocabulary: {error}") from error

    rows = block.get("rows")
    if not isinstance(rows, Mapping) or set(rows) != set(LOADED_TABLES):
        raise VocabularyError(f"vocabulary: rows must list exactly {', '.join(LOADED_TABLES)}")
    counted: dict[str, int] = {}
    for table in LOADED_TABLES:
        count = _count(rows[table])
        if count is None:
            raise VocabularyError(f"vocabulary: rows of {table} must be an integer, 0 or more")
        counted[table] = count

    not_loaded = block.get("not_loaded", [])
    if not isinstance(not_loaded, list) or not all(isinstance(name, str) for name in not_loaded):
        raise VocabularyError("vocabulary: not_loaded must be a list of file names")

    return VocabularyPackage(
        file=file,
        size_bytes=size,
        sha256=sha256,
        vocabulary_version=_text(block, "vocabulary_version"),
        rows=counted,
        not_loaded=tuple(not_loaded),
    )


def digest_problem(package: VocabularyPackage, actual: DigestResult) -> str | None:
    """``None`` when the ZIP is the one the manifest declares, else the message that says so."""
    if actual.sha256 == package.sha256 and actual.size_bytes == package.size_bytes:
        return None
    return (
        f"{package.file} is not the package config/sources.yml declares:\n"
        f"  expected sha256 {package.sha256} ({package.size_bytes} bytes)\n"
        f"  actual   sha256 {actual.sha256} ({actual.size_bytes} bytes)\n"
        "A new Athena package needs its own `vocabulary:` entry; do not edit the hash to fit."
    )


def member_problems(names: Iterable[str], not_loaded: Sequence[str]) -> list[str]:
    """Every loaded table has its file, and every other file is declared as not loaded.

    A member nobody declared stops the load, so a package with a new file is looked at before it
    is used.
    """
    present = set(names)
    loaded = {member_name(table) for table in LOADED_TABLES}
    problems = [f"{name} is missing from the package" for name in sorted(loaded - present)]
    declared = set(not_loaded)
    problems += [
        f"{name} is in the package but neither loaded nor listed in not_loaded"
        for name in sorted(present - loaded - declared)
    ]
    problems += [
        f"{name} is listed in not_loaded but is not in the package"
        for name in sorted(declared - present)
    ]
    problems += [
        f"{name} is a loaded table and cannot be listed in not_loaded"
        for name in sorted(declared & loaded)
    ]
    return problems


def header_problem(table: str, header: str, columns: Sequence[str]) -> str | None:
    """``None`` when the header line names the table's columns in order, else the difference."""
    found = header.rstrip("\r\n").split(DELIMITER)
    if found == list(columns):
        return None
    return (
        f"{member_name(table)} has the columns {', '.join(map(repr, found))}; "
        f"the {table} table has {', '.join(map(repr, columns))}"
    )


def version_from_lines(lines: Iterable[str]) -> str:
    """The ``vocabulary_version`` of the ``'None'`` row of ``VOCABULARY.csv``.

    That row is the version of the whole package, which ``CDM_SOURCE.vocabulary_version`` records
    (docs/omop_mapping.md).

    Raises:
        VocabularyError: the file has no such column, or not exactly one ``'None'`` row with a
            version.
    """
    rows = iter(lines)
    header = next(rows, "").rstrip("\r\n").split(DELIMITER)
    if "vocabulary_id" not in header or "vocabulary_version" not in header:
        raise VocabularyError("VOCABULARY.csv has no vocabulary_id and vocabulary_version columns")
    key, version = header.index("vocabulary_id"), header.index("vocabulary_version")
    found = [
        fields[version]
        for fields in (line.rstrip("\r\n").split(DELIMITER) for line in rows)
        if len(fields) == len(header) and fields[key] == NO_MATCHING_VOCABULARY
    ]
    if len(found) != 1 or not found[0]:
        raise VocabularyError(
            f"VOCABULARY.csv must have one {NO_MATCHING_VOCABULARY!r} row with a version, "
            f"found {len(found)}"
        )
    return found[0]


@dataclass
class StreamTally:
    """What streamed through the loader: line breaks, and bytes that ``COPY`` would read as quotes.

    Chunks may split a line anywhere; the count does not depend on where.
    """

    line_breaks: int = 0
    quote_bytes: int = 0
    #: Bytes were seen after the last line break: a last line without a line break.
    open_line: bool = False

    def update(self, chunk: bytes) -> None:
        if not chunk:
            return
        self.line_breaks += chunk.count(b"\n")
        self.quote_bytes += chunk.count(_QUOTE_BYTE)
        self.open_line = not chunk.endswith(b"\n")

    @property
    def records(self) -> int:
        """Data rows, header excluded."""
        lines = self.line_breaks + (1 if self.open_line else 0)
        return max(lines - 1, 0)
