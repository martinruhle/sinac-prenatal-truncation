"""Pure text editing of the source manifest, ``config/sources.yml``.

There is no file I/O here (CLAUDE.md rule 6): callers in ``scripts/`` read the file, pass its
text through these functions and write the result back.

The manifest is written by hand, with a header comment and a ``notes`` field per entry, and it is
read by a person reviewing a diff. Re-emitting it with a YAML dumper would reformat the whole
file on every download, so the three fields the downloader records are patched as text instead:
only those value lines change, every other byte is preserved (D-045).

The contract this relies on is visible in the file: ``id`` is the first key of an entry, and the
keys that get recorded already exist there with an empty value. Anything else raises, because a
manifest that silently failed to record a hash would be worse than no manifest at all.
"""

import json
import re
from collections.abc import Mapping, Sequence

__all__ = ["ManifestError", "record_fields"]

#: The first line of a sequence item, which must carry the ``id``.
ENTRY_START = re.compile(r"\A(?P<indent>[ ]*)-[ ]+id:[ ]*(?P<id>\S.*?)[ ]*\Z")

INDENT = re.compile(r"\A(?P<indent>[ ]*)(?P<rest>.*)\Z")


class ManifestError(ValueError):
    """The manifest does not have the shape the recorder needs."""


def _entry_id(line: str) -> tuple[int, str] | None:
    """The indentation and id of an entry's first line, or ``None`` for any other line."""
    match = ENTRY_START.match(line.rstrip("\r\n"))
    if match is None:
        return None
    return len(match.group("indent")), match.group("id").strip().strip("\"'")


def _entry_block(lines: Sequence[str], entry_id: str) -> tuple[int, int, int]:
    """Locate the entry: its first line, the line after its last, and its key indentation.

    An entry runs from its ``- id:`` line to the next non-blank line indented no further than the
    dash, which is either the next entry or the end of the block.
    """
    starts = [(number, found) for number, line in enumerate(lines) if (found := _entry_id(line))]
    matching = [(number, indent) for number, (indent, found) in starts if found == entry_id]

    if not matching:
        known = ", ".join(found for _, (_, found) in starts) or "none"
        raise ManifestError(f"no entry with id {entry_id!r} in the manifest (ids present: {known})")
    if len(matching) > 1:
        at = ", ".join(str(number + 1) for number, _ in matching)
        raise ManifestError(f"id {entry_id!r} appears more than once in the manifest (lines {at})")

    start, dash_indent = matching[0]
    end = len(lines)
    for number in range(start + 1, len(lines)):
        match = INDENT.match(lines[number].rstrip("\r\n"))
        assert match is not None  # the pattern matches every line
        if match.group("rest") and len(match.group("indent")) <= dash_indent:
            end = number
            break
    # In `  - id: x`, the key `id` starts two characters after the dash, and so does every other
    # key of the entry.
    return start, end, dash_indent + 2


def _format(value: str | int) -> str:
    """Render a value as an unambiguous YAML scalar.

    Strings are quoted: an ISO timestamp or an all-digit digest would otherwise come back from
    the parser as a datetime or an int, and the caller checks what it wrote by re-parsing.
    """
    return str(value) if isinstance(value, int) else json.dumps(value)


def record_fields(text: str, entry_id: str, values: Mapping[str, str | int]) -> str:
    """Write ``values`` into the entry ``entry_id``, leaving every other byte untouched.

    Raises:
        ManifestError: the entry is missing or duplicated, a key is not already present in the
            entry, or a key already holds a value. A recorded value is never overwritten: the
            hash is what detects a republished file, so replacing it is a deliberate manual edit.
    """
    lines = text.splitlines(keepends=True)
    start, end, key_indent = _entry_block(lines, entry_id)
    patched = list(lines)

    for key, value in values.items():
        pattern = re.compile(rf"\A[ ]{{{key_indent}}}{re.escape(key)}:(?P<value>.*)\Z")
        found = [
            (number, match)
            for number in range(start, end)
            if (match := pattern.match(lines[number].rstrip("\r\n")))
        ]
        if not found:
            raise ManifestError(f"entry {entry_id!r} has no key {key!r} to record into")
        if len(found) > 1:
            raise ManifestError(f"entry {entry_id!r} has key {key!r} more than once")

        number, match = found[0]
        if match.group("value").strip():
            current = match.group("value").strip()
            raise ManifestError(
                f"entry {entry_id!r} already has {key}: {current}. "
                "Recorded values are not overwritten; clear the field by hand to record again."
            )
        ending = lines[number][len(lines[number].rstrip("\r\n")) :]
        patched[number] = f"{' ' * key_indent}{key}: {_format(value)}{ending}"

    return "".join(patched)
