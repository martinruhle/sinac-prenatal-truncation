"""The study period and the ``--years`` option that selects years inside it.

There is no I/O here (CLAUDE.md rule 6): ``scripts/pipeline.py`` reads ``--years`` with
:func:`parse_years` and shows the default with :func:`format_years`.
"""

import re
from collections.abc import Sequence

__all__ = ["STUDY_YEARS", "PeriodError", "format_years", "parse_years"]

#: The study period (D-041): 2020-2023, one catalogue period with identical headers. Development
#: runs on 2023 alone by passing ``--years 2023`` (D-009); 2019 is a conditional extension (D-050).
STUDY_YEARS: tuple[int, ...] = (2020, 2021, 2022, 2023)

#: One item of ``--years``: a year, or an inclusive range of years. ``[0-9]`` rather than ``\d``,
#: which would also accept non-ASCII digits.
_ITEM = re.compile(r"\A(?P<first>[0-9]{4})(?:-(?P<last>[0-9]{4}))?\Z")


class PeriodError(ValueError):
    """The text given for ``--years`` does not describe a set of years."""


def parse_years(text: str) -> tuple[int, ...]:
    """Read a comma-separated list of years and inclusive ranges of years.

    ``"2023"``, ``"2022,2023"``, ``"2020-2023"`` and ``"2019,2021-2023"`` are all accepted. The
    result is sorted and names each year once. Whether a year has a source file is not checked
    here: that is the manifest's business.

    Raises:
        PeriodError: an item is not a four-digit year or an ascending range of them.
    """
    years: set[int] = set()
    for raw in text.split(","):
        item = raw.strip()
        match = _ITEM.match(item)
        if match is None:
            raise PeriodError(
                f"{item!r} is not a year or a range of years; write 2023, 2022,2023 or 2020-2023"
            )
        first = int(match["first"])
        last = int(match["last"] or first)
        if last < first:
            raise PeriodError(f"the range {item!r} runs backwards")
        years.update(range(first, last + 1))
    return tuple(sorted(years))


def format_years(years: Sequence[int]) -> str:
    """Write years the way :func:`parse_years` reads them, as a range when they are contiguous.

    Raises:
        PeriodError: there are no years to write.
    """
    ordered = sorted(set(years))
    if not ordered:
        raise PeriodError("no years to write")
    first, last = ordered[0], ordered[-1]
    if len(ordered) > 1 and ordered == list(range(first, last + 1)):
        return f"{first}-{last}"
    return ",".join(str(year) for year in ordered)
