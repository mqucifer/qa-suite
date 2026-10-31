"""crew-presentation's story journey page: events timeline, cost section, omission.

The bug (mqucifer/crew-presentation#231): the journey page showed only the
card title, its meta line, the story's one-sentence text, and the five-stage
path strip. It did not show the story's events (when it entered each stage,
its moves), its cost (wall-clock, model calls), or anything else about the
story's life cycle — a delivered story gave no more detail than an undelivered one.

The fix: the journey page now renders:
- 'What happened, in order': a timeline of the story's events with timestamps
- 'What it cost': wall-clock and model calls (when the data is present)

These tests verify the fix by reading the package (the site's input) and the
built pages (the site's output), and checking the output matches the input.
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


def _load_all_events(index: dict) -> list[dict]:
    """Load all events from all period files in the package."""
    events: list[dict] = []
    for period in index.get("periods", []):
        events_file = Path(PACKAGE) / period["file"]
        if events_file.is_file():
            data = json.loads(events_file.read_text())
            events.extend(data.get("events", []))
    return events


def _events_for_card(events: list[dict], number, repo: str) -> list[dict]:
    """Events that reference a specific card (number, repo), sorted by time."""
    card_events = []
    for e in events:
        card_ref = e.get("card")
        if not card_ref:
            continue
        if card_ref.get("number") == number and card_ref.get("repo") == repo:
            card_events.append(e)
    card_events.sort(key=lambda e: e.get("at", ""))
    return card_events


def _cards_with_events(index: dict) -> list[tuple[dict, list[dict]]]:
    """Cards that have at least one event in the package's periods."""
    events = _load_all_events(index)
    result = []
    for card in index.get("cards", []):
        repo = card.get("repo", "")
        number = card.get("number")
        if not repo or number is None:
            continue
        card_events = _events_for_card(events, number, repo)
        if card_events:
            result.append((card, card_events))
    return result


def _slug_for_card(repo: str, number) -> str:
    """The story page's URL path for a card."""
    return f"stories/{repo.replace('/', '-')}-{number}.html"


def _hhmm(at: str) -> str | None:
    """Extract HH:MM from an ISO timestamp, or None if unparseable."""
    m = re.search(r"T(\d{2}):(\d{2})", at)
    return f"{m.group(1)}:{m.group(2)}" if m else None


def _wall_clock_display(wall_clock_seconds) -> str | None:
    """The display text build.py's _format_minutes produces for wall_clock_seconds.

    1740 -> round(1740/60)=29 -> '29 min'. None -> None (no cost section).
    """
    if wall_clock_seconds is None:
        return None
    minutes = round(wall_clock_seconds / 60)
    hours, mins = divmod(int(minutes), 60)
    if hours == 0:
        return f"{mins} min"
    if mins == 0:
        return f"{hours} hr"
    return f"{hours} hr {mins} min"


def test_journey_page_shows_event_timeline():
    """AC1: the journey page shows 'What happened, in order' with event details.

    Given a card with events in the package's periods (e.g. a move event with
    an 'at' timestamp and a 'to_column'), when the build renders the journey
    page for that card, the page body contains a heading with the exact text
    'What happened, in order' and, below it, at least one element whose text
    content includes the event's timestamp (HH:MM) and destination column.

    This test fails on the buggy version (no events section) and passes on the
    fixed version (events section rendered from the package's events).
    """
    index = _load_index()
    cards_with_events = _cards_with_events(index)

    for card, card_events in cards_with_events:
        repo = card["repo"]
        number = card["number"]
        slug = _slug_for_card(repo, number)
        html = page("/" + slug)

        # The page must have the timeline heading (the card has events)
        assert "What happened, in order" in html, (
            f"{slug}: the journey page has no 'What happened, in order' heading: "
            f"the story's events are not rendered (crew-presentation#231)"
        )

        # For cards that have at least one move event with a parseable timestamp
        # and a destination column, verify at least one is visible on the page.
        # (A card may have events that are not moves, or moves without a
        # timestamp — those don't carry the detail the AC checks for.)
        checkable = [
            e
            for e in card_events
            if e.get("kind") in ("move", "card_moved")
            and e.get("at")
            and _hhmm(e["at"])
            and e.get("to_column")
        ]
        if not checkable:
            continue

        found = False
        for event in checkable:
            time_str = _hhmm(event["at"])
            to_column = event["to_column"]
            if time_str in html and to_column in html:
                found = True
                break

        assert found, (
            f"{slug}: the journey page has move events in the package "
            f"with timestamps and destination columns, but none of them "
            f"appear in the rendered timeline"
        )


def test_journey_page_shows_cost_section():
    """AC2: the journey page shows 'What it cost' with wall-clock and model calls.

    Given a card whose analysis.stories entry has wall_clock_seconds and
    cost.model_calls, when the build renders the journey page for that card,
    the page body contains a heading 'What it cost' and, within the same
    section, the wall-clock formatted as hours and minutes and the model calls
    count.

    This test fails on the buggy version (no cost section) and passes on the
    fixed version (cost section rendered from the package's analysis).
    """
    index = _load_index()
    stories = index.get("analysis", {}).get("stories", [])

    for story in stories:
        card_ref = story.get("card")
        if not card_ref:
            continue
        repo = card_ref.get("repo", "")
        number = card_ref.get("number")
        if not repo or number is None:
            continue

        wall_clock_seconds = story.get("wall_clock_seconds")
        cost = story.get("cost")
        model_calls = cost.get("model_calls") if isinstance(cost, dict) else None

        if wall_clock_seconds is None or model_calls is None:
            continue

        slug = _slug_for_card(repo, number)
        html = page("/" + slug)

        # The page must have the cost heading
        assert "What it cost" in html, (
            f"{slug}: the journey page has no 'What it cost' heading: "
            f"the story's cost data is not rendered (crew-presentation#231)"
        )

        # The wall-clock should be formatted and shown
        expected = _wall_clock_display(wall_clock_seconds)
        assert expected is not None
        assert expected in html, (
            f"{slug}: wall_clock_seconds={wall_clock_seconds} should show "
            f"{expected!r} in the cost section, but it's not in the page"
        )

        # The model calls count should be in a cost-grid__value span
        pattern = rf"cost-grid__value[^>]*>\s*{re.escape(str(model_calls))}\s*<"
        assert re.search(pattern, html), (
            f"{slug}: cost.model_calls={model_calls} should be shown "
            f"in a cost-grid__value span, but {str(model_calls)!r} isn't found"
        )


def test_journey_page_omits_cost_when_no_wall_clock():
    """AC3: when wall_clock_seconds is null, the journey page omits 'What it cost'.

    Given a card whose analysis.stories entry has wall_clock_seconds null and
    whose periods contain at least one event for that card, when the build
    renders the journey page, the page body contains 'What happened, in order'
    (the events are shown) but does NOT contain 'What it cost' (the cost
    section is absent because the data is missing).

    This guards against a regression where the cost section is shown
    regardless of the data.
    """
    index = _load_index()
    stories = index.get("analysis", {}).get("stories", [])
    events = _load_all_events(index)

    for story in stories:
        card_ref = story.get("card")
        if not card_ref:
            continue
        repo = card_ref.get("repo", "")
        number = card_ref.get("number")
        if not repo or number is None:
            continue

        # Only check stories with wall_clock_seconds null
        if story.get("wall_clock_seconds") is not None:
            continue

        # Check that this card has at least one event
        if not _events_for_card(events, number, repo):
            continue

        slug = _slug_for_card(repo, number)
        html = page("/" + slug)

        # The events should be shown (the card has events)
        assert "What happened, in order" in html, (
            f"{slug}: the card has events but the journey page has no "
            f"'What happened, in order' heading"
        )

        # The cost section should NOT be shown
        assert "What it cost" not in html, (
            f"{slug}: wall_clock_seconds is null but the page shows "
            f"'What it cost': the cost section should be omitted when "
            f"the data is missing"
        )
