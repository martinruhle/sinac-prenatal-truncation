"""Pure text handling for the SQL files this project applies to the database.

There is no file or database I/O here (CLAUDE.md rule 6): callers in ``scripts/`` read the files
and execute what these functions return.

The vendored OHDSI DDL writes its schema marker as ``@cdmDatabaseSchema``; the SQL written in
this repository uses snake_case names such as ``@staging_schema``. Both go through the same
mapping, so a file can be moved between the two conventions without touching this module.
"""

import re
from collections.abc import Mapping

__all__ = [
    "IDENTIFIER",
    "PLACEHOLDER",
    "UnknownPlaceholderError",
    "find_placeholders",
    "is_valid_identifier",
    "render_sql",
    "schema_mapping",
]

#: Every ``@word`` in a SQL file is treated as a marker. This is deliberate: an unresolved marker
#: reaching the database is a silent bug, so anything that looks like one must be mapped.
PLACEHOLDER = re.compile(r"@[A-Za-z_][A-Za-z0-9_]*")

#: A bare SQL identifier, the only thing accepted as a schema name.
IDENTIFIER = re.compile(r"\A[A-Za-z_][A-Za-z0-9_]*\Z")


class UnknownPlaceholderError(ValueError):
    """A marker in the SQL text has no value in the mapping passed to :func:`render_sql`."""


def find_placeholders(sql: str) -> frozenset[str]:
    """Return the markers present in ``sql``, without their leading ``@``."""
    return frozenset(match.group()[1:] for match in PLACEHOLDER.finditer(sql))


def is_valid_identifier(name: str) -> bool:
    """Whether ``name`` is a bare SQL identifier, safe to interpolate into a statement.

    Schema names are interpolated as text because SQL has no parameter slot for an identifier,
    so they are validated instead of bound.
    """
    return IDENTIFIER.match(name) is not None


def schema_mapping(cdm: str, staging: str, results: str) -> dict[str, str]:
    """Build the marker mapping for the three schemas of the project (D-032)."""
    return {
        "cdmDatabaseSchema": cdm,
        "cdm_schema": cdm,
        "staging_schema": staging,
        "results_schema": results,
    }


def render_sql(sql: str, schemas: Mapping[str, str]) -> str:
    """Replace the markers in ``sql`` with the schema names in ``schemas``.

    ``schemas`` is keyed by marker name without the ``@``. The substitution is a single pass, so
    a replacement is never rescanned and markers that are a prefix of another cannot corrupt
    each other.

    Raises:
        ValueError: a schema name is not a bare SQL identifier.
        UnknownPlaceholderError: ``sql`` holds a marker with no value in ``schemas``.
    """
    for marker, name in sorted(schemas.items()):
        if not is_valid_identifier(name):
            raise ValueError(f"schema name for @{marker} is not a bare SQL identifier: {name!r}")

    unknown = find_placeholders(sql) - set(schemas)
    if unknown:
        listed = ", ".join(f"@{marker}" for marker in sorted(unknown))
        raise UnknownPlaceholderError(f"no schema given for: {listed}")

    return PLACEHOLDER.sub(lambda match: schemas[match.group()[1:]], sql)
