"""crew-presentation's replay board: structure and phone-width layout.

The replay page shows a board of columns (Needs Refinement, Ready, Sprint
Backlog, In Progress, Reviewing, QAing, Merging, Done, Blocked). Each column
is a .replay-col element with a .replay-col__header.

These tests verify that:
- The Board section contains the expected columns in order, each with its
  header (mqucifer/crew-presentation#224 AC2).
- The CSS constrains the board at phone width so it does not overflow a
  375px viewport (mqucifer/crew-presentation#224 AC1).

The tests read the built replay page (QA_BASE_URL/replay.html) and the site's
CSS (QA_BASE_URL/css/site.css), plus the package (QA_PACKAGE) to determine
expected columns.
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


def _extract_block_content(text: str, open_brace_pos: int) -> str:
    """Given the position of an opening brace, return the content of that block
    by matching braces (handles nested blocks)."""
    depth = 0
    for i in range(open_brace_pos, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[open_brace_pos + 1 : i]
    return text[open_brace_pos + 1 :]


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


def _media_block_contents_at_least_width(css: str, min_width: int) -> list[str]:
    """Return the content of all @media (max-width: Npx) blocks where N >= min_width."""
    blocks = []
    for match in re.finditer(r"@media\s*\(\s*max-width:\s*(\d+)px\s*\)\s*\{", css):
        width = int(match.group(1))
        if width >= min_width:
            open_brace = match.end() - 1  # position of the opening {
            blocks.append(_extract_block_content(css, open_brace))
    return blocks


def _rules_for_selector_in_block(block: str, selector: str) -> list[str]:
    """Find rule bodies within a CSS block whose selector includes the given string.

    Handles simple rules (no nested braces in the body), which is the structure
    of rules within a media query.
    """
    rules = []
    # Match: selector { body } where body has no nested braces
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", block):
        selector_text = match.group(1).strip()
        if selector in selector_text:
            rules.append(match.group(2))
    return rules


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


def test_replay_board_css_prevents_overflow_at_phone_width():
    """AC1: the CSS constrains the board at phone width so it fits within 375px.

    The bug: site.css had no rules for .replay-board/.replay-col/.replay-card,
    so the nine columns rendered at their natural width (591px) in a 375px
    viewport and the page scrolled sideways.

    The fix: .replay-board is laid out as a grid, and a phone-width media query
    constrains it to a single column so it reflows to fit the viewport.
    """
    css = page("/css/site.css")

    # The board must have CSS rules at all (the bug: no rules existed).
    assert ".replay-board" in css, (
        "site.css has no rules for .replay-board: "
        "the board columns will not be laid out and will overflow at phone width"
    )

    # The board must be laid out as a grid (the design mock uses grid).
    board_rules = re.findall(r"\.replay-board\s*\{([^}]*)\}", css)
    assert board_rules, (
        "site.css has no .replay-board rule block: the board columns will not be laid out"
    )
    # At least one .replay-board rule must set display: grid
    has_display_grid = any("display: grid" in r or "display:grid" in r for r in board_rules)
    assert has_display_grid, (
        f".replay-board does not set display: grid in any rule; "
        f"the columns will not be laid out as a grid. "
        f"Rules found: {board_rules}"
    )

    # A phone-width media query (max-width >= 375px) must constrain the board
    # to a single column so the nine columns stack and fit within 375px.
    media_blocks = _media_block_contents_at_least_width(css, min_width=375)
    assert media_blocks, (
        "site.css has no @media (max-width: Npx) with N >= 375: "
        "the board will not reflow at phone width"
    )

    constrained = False
    for block in media_blocks:
        board_rules_in_media = _rules_for_selector_in_block(block, ".replay-board")
        for rule_body in board_rules_in_media:
            gtc_match = re.search(r"grid-template-columns:\s*([^;]+)", rule_body)
            if not gtc_match:
                continue
            value = gtc_match.group(1).strip().rstrip(";").strip()
            # A single column: 1fr, 1, minmax(0,1fr), 100%, auto, etc.
            # NOT repeat(N, ...) where N > 1.
            repeat_match = re.match(r"repeat\(\s*(\d+)", value)
            if repeat_match and int(repeat_match.group(1)) > 1:
                continue
            constrained = True
            break
        if constrained:
            break

    assert constrained, (
        "site.css has no phone-width media query (max-width >= 375px) that "
        "constrains .replay-board's grid-template-columns to a single column. "
        "The nine board columns will overflow a 375px viewport. "
        "(mqucifer/crew-presentation#224: the board rendered 591px wide "
        "in a 375px viewport because no CSS rules laid it out.)"
    )
