"""crew-presentation's replay board cards: card references render as hyperlinks.

The replay page shows a board with cards placed in their initial column.
Each card's reference must be a real hyperlink (repo#number as the visible
label, the issue URL as the href), not literal markdown text.

These tests verify that:
- No board card element contains the literal markdown string
  '[repo#number](url)' (mqucifer/crew-presentation#226).
- Each board card contains an <a> element whose href equals the card's URL
  and whose visible text equals 'repo#number'.

The tests read the package (QA_PACKAGE, the site's input) and the built
replay page (QA_BASE_URL/replay.html, the site's output).
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


def _load_sprint_events(index: dict, sprint_name: str) -> list[dict]:
    """Load events for a sprint from the package, as build.py does."""
    pkg = Path(PACKAGE)
    for period in index.get("periods", []):
        if period.get("sprint") == sprint_name:
            events_file = pkg / period["file"]
            if events_file.is_file():
                return json.loads(events_file.read_text()).get("events", [])
    return []


def _column_order(columns: set[str]) -> list[str]:
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


def _expected_board_cards(index: dict, sprint_name: str) -> dict[str, list[dict]]:
    """Replicate build.py's _build_board_state to compute expected card placement.

    Returns a dict mapping column name to a list of expected card dicts with
    'link_text', 'link_url', and 'title'.
    """
    events = _load_sprint_events(index, sprint_name)
    cards = index.get("cards", [])

    if not events:
        return {}

    columns: set[str] = set()
    for event in events:
        if event.get("from_column"):
            columns.add(event["from_column"])
        if event.get("to_column"):
            columns.add(event["to_column"])
    ordered_columns = _column_order(columns)

    cards_by_key: dict[tuple, dict] = {}
    for card in cards:
        key = (card.get("number"), card.get("repo"))
        cards_by_key[key] = card

    # Find each card's earliest event
    earliest: dict[tuple, dict] = {}
    for event in events:
        card_ref = event.get("card")
        if not card_ref:
            continue
        key = (card_ref.get("number"), card_ref.get("repo"))
        at = event.get("at", "")
        if key not in earliest or at < earliest[key].get("at", ""):
            earliest[key] = event

    board: dict[str, list[dict]] = {col: [] for col in ordered_columns}
    for key, event in earliest.items():
        col = event.get("from_column", "")
        if col not in board:
            continue
        card = cards_by_key.get(key)
        if card is None:
            continue
        url = card.get("url", "")
        match = re.match(r"https://github\.com/([^/]+)/([^/]+)/issues/\d+", url)
        if match:
            display_repo = f"{match.group(1)}/{match.group(2)}"
        else:
            display_repo = card.get("repo", "")
        number = card.get("number", "")
        board[col].append(
            {
                "link_text": f"{display_repo}#{number}",
                "link_url": url,
                "title": card.get("title", ""),
            }
        )

    return board


def _board_cards_from_html(html: str) -> list[tuple[str, str, str, str]]:
    """Parse all board cards from the replay page HTML.

    Returns a list of (column, href, link_text, title) for each .replay-card.
    The column is determined by which .replay-col__header precedes the card.
    """
    results: list[tuple[str, str, str, str]] = []
    # Find all column sections: from a .replay-col__header to the next one
    col_starts = list(re.finditer(r'<div class="replay-col__header">(.*?)</div>', html))
    card_pattern = re.compile(
        r'<div class="replay-card">\s*<a href="([^"]*)" class="num meta">([^<]*)</a>\s*([^<]*)\s*</div>'
    )
    for i, col_match in enumerate(col_starts):
        col_name = col_match.group(1).strip()
        col_start = col_match.end()
        col_end = col_starts[i + 1].start() if i + 1 < len(col_starts) else len(html)
        col_html = html[col_start:col_end]
        for card_match in card_pattern.finditer(col_html):
            href = card_match.group(1)
            link_text = card_match.group(2).strip()
            title = card_match.group(3).strip()
            results.append((col_name, href, link_text, title))
    return results


def _all_cards_html(html: str) -> list[str]:
    """Return the raw HTML of every .replay-card element."""
    return re.findall(r'<div class="replay-card">.*?</div>', html, re.DOTALL)


def test_replay_board_cards_render_links_not_markdown():
    """AC1: no board card element contains the literal markdown link text.

    Given the replay page is built from a package with cards that have URLs,
    when the replay page HTML is rendered, no board card element contains the
    literal markdown string '[repo#number](url)'.
    """
    index = _load_index()
    sprints = index.get("sprints", [])
    assert sprints, "the package has no sprints"
    sprint_name = sprints[-1].get("name", "")
    assert sprint_name, "the last sprint has no name"

    expected = _expected_board_cards(index, sprint_name)
    all_expected_cards: list[dict] = []
    for cards in expected.values():
        all_expected_cards.extend(cards)

    if not all_expected_cards:
        # No cards on the board; nothing to check.
        return

    html = page("/replay.html")
    card_htmls = _all_cards_html(html)
    assert card_htmls, "the replay page has no .replay-card elements"

    for card in all_expected_cards:
        link_text = card["link_text"]
        link_url = card["link_url"]
        # The literal markdown form that the bug produced
        markdown_form = f"[{link_text}]({link_url})"
        for card_html in card_htmls:
            assert markdown_form not in card_html, (
                f"board card in the replay page contains the literal markdown "
                f"string {markdown_form!r} instead of a rendered hyperlink"
            )


def test_replay_board_cards_have_correct_hyperlink():
    """AC2: each board card contains an <a> element with the correct href and text.

    Given the replay page is built from a package with cards that have URLs,
    when the replay page HTML is rendered, each board card contains an <a>
    element whose href equals the card's URL and whose visible text equals
    'repo#number'.
    """
    index = _load_index()
    sprints = index.get("sprints", [])
    assert sprints, "the package has no sprints"
    sprint_name = sprints[-1].get("name", "")
    assert sprint_name, "the last sprint has no name"

    expected = _expected_board_cards(index, sprint_name)
    all_expected_cards: list[dict] = []
    for col, cards in expected.items():
        for card in cards:
            all_expected_cards.append({**card, "column": col})

    if not all_expected_cards:
        # No cards on the board; nothing to check.
        return

    html = page("/replay.html")
    rendered = _board_cards_from_html(html)
    assert rendered, (
        "the replay page has no board cards with <a> elements: "
        "the fix renders card references as hyperlinks"
    )

    # Build a lookup from (link_text) to rendered card
    rendered_by_text: dict[str, list[tuple[str, str, str, str]]] = {}
    for col, href, link_text, title in rendered:
        rendered_by_text.setdefault(link_text, []).append((col, href, link_text, title))

    for card in all_expected_cards:
        link_text = card["link_text"]
        link_url = card["link_url"]
        col = card["column"]
        matches = rendered_by_text.get(link_text, [])
        assert matches, f"no board card with link text {link_text!r} found in the replay page"
        # Find the one in the expected column
        in_column = [m for m in matches if m[0] == col]
        assert in_column, (
            f"board card with link text {link_text!r} is not in column {col!r} "
            f"(found in columns: {[m[0] for m in matches]})"
        )
        for _col, href, _text, _title in in_column:
            assert href == link_url, (
                f"board card {link_text!r} in {col!r}: href is {href!r}, expected {link_url!r}"
            )
