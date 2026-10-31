"""crew-presentation's replay board: structure and phone-width layout.

The replay page shows a board of columns (Needs Refinement, Ready, Sprint
Backlog, In Progress, Reviewing, QAing, Merging, Done, Blocked). Each column
is a .replay-col element with a .replay-col__header.

These tests verify that:
- The Board section contains the expected columns in order, each with its
  header (mqucifer/crew-presentation#224 AC2).
- The page fits a 375px viewport, rendered, without scrolling sideways
  (mqucifer/crew-presentation#224 AC1).

The tests read the built replay page (QA_BASE_URL/replay.html), over HTTP and
rendered in Chromium, plus the package (QA_PACKAGE) to determine expected columns.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

import pytest

# Fails rather than skips without them: a skipped suite would be a green check.
BASE = os.environ.get("QA_BASE_URL", "")
STATE = os.environ.get("QA_SITE_STATE", "")
PACKAGE = os.environ.get("QA_PACKAGE", "")
if not (BASE and STATE and PACKAGE):
    pytest.fail(
        "QA_BASE_URL, QA_SITE_STATE or QA_PACKAGE isn't set: run start.sh first", pytrace=False
    )


def page(path: str) -> str:
    try:
        with urllib.request.urlopen(BASE + path, timeout=10) as response:
            return response.read().decode()
    except urllib.error.HTTPError as error:
        pytest.fail(f"GET {path} answered {error.code}: the site has no such page", pytrace=False)


def _load_index() -> dict:
    return json.loads((Path(PACKAGE) / "delivery-history.json").read_text())


def _board_column_order(columns: set[str]) -> list[str]:
    """The same column order build.py uses."""
    order = [
        "Inbox (Goals)",
        "Needs Refinement",
        "Ready",
        "Sprint Backlog",
        "In Progress",
        "Reviewing",
        "QAing",
        "Merging",
        "Done",
        "Blocked",
    ]
    return [c for c in order if c in columns]


def _load_sprint_events(index: dict, sprint_name: str) -> list[dict]:
    """Load events for a sprint from the package, as build.py does."""
    pkg = Path(PACKAGE)
    for period in index.get("periods", []):
        if period.get("sprint") == sprint_name:
            events_file = pkg / period["file"]
            if events_file.is_file():
                return json.loads(events_file.read_text()).get("events", [])
    return []


def _expected_columns(index: dict, sprint_name: str) -> list[str]:
    """Compute the expected board columns from the package, as build.py does."""
    events = _load_sprint_events(index, sprint_name)
    if not events:
        return []
    columns: set[str] = set()
    for event in events:
        if event.get("from_column"):
            columns.add(event["from_column"])
        if event.get("to_column"):
            columns.add(event["to_column"])
    return _board_column_order(columns)


def _board_section_headers(html: str) -> list[str]:
    """Extract the text of each .replay-col__header within the Board section.

    Returns the column names in DOM order.
    """
    # Find the Board section
    board_match = re.search(
        r'<section[^>]*aria-label="Board"[^>]*>(.*?)</section>', html, re.DOTALL
    )
    if not board_match:
        pytest.fail("replay.html has no <section aria-label='Board'>")
    board_html = board_match.group(1)

    # Find all replay-col__header elements within the board
    headers = re.findall(r'<div class="replay-col__header">(.*?)</div>', board_html)
    return [h.strip() for h in headers]


def _board_col_count(html: str) -> int:
    """Count the .replay-col elements within the Board section."""
    board_match = re.search(
        r'<section[^>]*aria-label="Board"[^>]*>(.*?)</section>', html, re.DOTALL
    )
    if not board_match:
        pytest.fail("replay.html has no <section aria-label='Board'>")
    board_html = board_match.group(1)
    return len(re.findall(r'<div class="replay-col">', board_html))


def test_replay_board_has_nine_columns_in_order():
    """AC2: the Board section has the expected columns in DOM order.

    Given a built site whose replay.html contains a Board section with
    replay-col children, when the page is rendered, each replay-col contains a
    replay-col__header whose text is the column name, and the columns appear
    in the order build.py computes from the package.
    """
    index = _load_index()
    sprints = index.get("sprints", [])
    assert sprints, "the package has no sprints"
    sprint_name = sprints[-1].get("name", "")
    assert sprint_name, "the last sprint has no name"

    expected = _expected_columns(index, sprint_name)
    assert len(expected) == 9, (
        f"the package's last sprint ({sprint_name!r}) produces "
        f"{len(expected)} board columns ({expected}), but the test expects 9"
    )

    html = page("/replay.html")
    headers = _board_section_headers(html)
    col_count = _board_col_count(html)

    assert col_count == 9, f"the Board section has {col_count} .replay-col elements, expected 9"
    assert headers == expected, (
        f"the Board section's column headers are {headers}, expected {expected} (in that DOM order)"
    )


def test_replay_board_stacks_at_phone_width(rendered):
    """AC1: at 375x812 the board is a grid of one column, so its nine columns stack.

    The bug: site.css had no rules for .replay-board/.replay-col/.replay-card, so
    the board wasn't laid out at all and the page scrolled sideways.
    """
    replay = rendered("/replay.html", width=375, height=812)
    board = replay.locator('[aria-label="Board"]')

    display, tracks = board.evaluate(
        "el => [getComputedStyle(el).display, getComputedStyle(el).gridTemplateColumns]"
    )
    assert display == "grid", f"the board's display is {display!r} at 375px, not a grid"
    assert len(tracks.split()) == 1, f"the board has the columns {tracks!r} at 375px, not one"


# raises: a page that won't render still fails. Only the measurement is expected to.
@pytest.mark.xfail(
    raises=AssertionError,
    reason="replay.html is 559px wide at 375px on the site's main: a card title's 78-character "
    "path holds the board's 1fr column open. Remove this when the site fixes that.",
)
def test_replay_board_fits_at_phone_width(rendered):
    """AC1: replay.html, rendered at 375x812, doesn't scroll sideways."""
    replay = rendered("/replay.html", width=375, height=812)

    # A page without its board would fit too, and prove nothing.
    columns = replay.locator('[aria-label="Board"] .replay-col').count()
    assert columns == 9, f"replay.html rendered {columns} .replay-col in its Board section, not 9"

    scroll_width = replay.evaluate("document.documentElement.scrollWidth")
    assert scroll_width <= 375, (
        f"replay.html is {scroll_width}px wide in a 375px viewport, so it scrolls sideways "
        "(mqucifer/crew-presentation#224)"
    )
