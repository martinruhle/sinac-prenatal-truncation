"""Checks of the NOM-007-SSA2-2016 visit calendar in config/nom007_schedule.yml.

The calendar is copied by hand from the DOF text, so these tests tie every number to the quoted
line it was read from and keep the visits in the order the norm gives them.
"""

from pathlib import Path
from typing import Any

import pytest
import yaml

SCHEDULE = Path(__file__).resolve().parents[1] / "config" / "nom007_schedule.yml"


def _schedule() -> dict[str, Any]:
    document: dict[str, Any] = yaml.safe_load(SCHEDULE.read_text(encoding="utf-8"))
    return document


def _visits() -> list[dict[str, Any]]:
    visits: list[dict[str, Any]] = _schedule()["visits"]
    return visits


def test_the_eight_visits_are_numbered_in_order() -> None:
    assert [visit["visit"] for visit in _visits()] == list(range(1, 9))


def test_the_minimum_fits_in_the_calendar() -> None:
    assert 0 < _schedule()["minimum_visits"] <= len(_visits())


def test_the_weeks_of_consecutive_visits_do_not_overlap() -> None:
    visits = _visits()
    for visit in visits:
        assert visit["first_week"] <= visit["last_week"]
    for earlier, later in zip(visits, visits[1:], strict=False):
        assert earlier["last_week"] < later["first_week"]


@pytest.mark.parametrize("visit", _visits(), ids=lambda visit: f"visit-{visit['visit']}")
def test_every_number_is_read_from_its_published_line(visit: dict[str, Any]) -> None:
    published: str = visit["published"]
    assert published.startswith(f"{visit['visit']} ª consulta:")
    last = str(visit["last_week"])
    if "last_week_days" in visit:
        last = f"{last}.{visit['last_week_days']}"
    weeks = published.split(":", 1)[1]
    if visit["first_week"] == visit["last_week"]:
        assert f" {last} semanas" in weeks
    else:
        assert f" {visit['first_week']} - {last}" in weeks
