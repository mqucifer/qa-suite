"""crew-presentation's view nav and replay board at phone width.

mqucifer/crew-presentation#230: the header's 'A story's journey' and 'Replay' nav
links in story pages used root-relative paths (story-journey.html, replay.html),
which from the stories/ subdirectory resolved to stories/story-journey.html and
stories/replay.html — files that don't exist. The build only creates root-level
versions. From the site's deepest view the reader could not navigate anywhere.

mqucifer/crew-presentation#246: a card title holding a long unbreakable word
(e.g. a 78-character test name) set the board column's min-content width past
375px. The .replay-board's 1fr column had an auto minimum, so it couldn't shrink
below that word, and .replay-card had no overflow-wrap to break it.

These tests check that:
- AC1 (#230): a story page's 'A story's journey' link resolves to a file in the build
- AC2 (#230): a story page's 'Replay' link resolves to a file in the build
- AC3 (#230): story-journey.html (root level) 'Replay' link resolves to a file in the build
- AC1 (#246): replay.html, built from the real package, has scrollWidth <= 375 at a 375px viewport
- AC2 (#246): the .replay-card holding the long title shows the full title (wrapped, not clipped)
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin

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


def _url_is_file(url: str) -> bool:
    """Check whether a URL returns HTTP 200 for a file (not a directory listing)."""
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            if response.status != 200:
                return False
            body = response.read(4096).decode(errors="replace")
            return "Directory listing for" not in body
    except (urllib.error.HTTPError, urllib.error.URLError):
        return False


def _view_nav_href(html: str, link_text: str) -> str:
    """Extract the href of the link with given text in nav[aria-label='Views']."""
    nav_match = re.search(r"<nav[^>]*aria-label=[\"']Views[\"'][^>]*>(.*?)</nav>", html, re.DOTALL)
    if not nav_match:
        pytest.fail("no nav[aria-label='Views'] found in the page", pytrace=False)
    nav_html = nav_match.group(1)
    # Match the <a> whose visible text is exactly link_text
    escaped = re.escape(link_text)
    link_match = re.search(rf"<a\s+href=[\"']([^\"']*)[\"'][^>]*>\s*{escaped}\s*</a>", nav_html)
    if not link_match:
        pytest.fail(f"no {link_text!r} link found in nav[aria-label='Views']", pytrace=False)
    return link_match.group(1)


def _story_page_paths() -> list[str]:
    """The URL paths of story pages in the build, from the package's cards."""
    index = json.loads((Path(PACKAGE) / "delivery-history.json").read_text())
    paths = []
    for card in index.get("cards", []):
        repo = card.get("repo", "")
        number = card.get("number")
        if not repo or number is None:
            continue
        slug = f"{repo.replace('/', '-')}-{number}.html"
        paths.append(f"/stories/{slug}")
    return paths


def test_story_page_journey_link_resolves():
    """AC1: a story page's 'A story's journey' nav link resolves to a file in the build.

    Given the site is built from a package containing at least one story card,
    the 'A story's journey' link in nav[aria-label='Views'] on a story page has
    an href whose value, resolved as a relative path from the stories/ directory,
    names a file that exists under the build root.
    """
    story_paths = _story_page_paths()
    assert story_paths, "the package has no story cards: the test requires at least one"

    for path in story_paths:
        html = page(path)
        href = _view_nav_href(html, "A story's journey")
        resolved = urljoin(BASE + path, href)
        assert _url_is_file(resolved), (
            f"{path}: the 'A story's journey' nav link points to {href!r}, "
            f"which resolves to {resolved} but does not name a file in the build directory"
        )


def test_story_page_replay_link_resolves():
    """AC2: a story page's 'Replay' nav link resolves to a file in the build.

    Given the site is built from a package containing at least one story card,
    the 'Replay' link in nav[aria-label='Views'] on a story page has an href
    whose value, resolved as a relative path from the stories/ directory, names
    a file that exists under the build root.
    """
    story_paths = _story_page_paths()
    assert story_paths, "the package has no story cards: the test requires at least one"

    for path in story_paths:
        html = page(path)
        href = _view_nav_href(html, "Replay")
        resolved = urljoin(BASE + path, href)
        assert _url_is_file(resolved), (
            f"{path}: the 'Replay' nav link points to {href!r}, "
            f"which resolves to {resolved} but does not name a file in the build directory"
        )


def test_story_journey_replay_link_resolves():
    """AC3: story-journey.html's 'Replay' nav link resolves to a file in the build.

    Given the build output includes the root-level file story-journey.html,
    the 'Replay' link in nav[aria-label='Views'] has an href whose value,
    resolved as a relative path from the build root, names a file that exists
    under the build root.
    """
    html = page("/story-journey.html")
    href = _view_nav_href(html, "Replay")
    resolved = urljoin(BASE + "/story-journey.html", href)
    assert _url_is_file(resolved), (
        f"story-journey.html: the 'Replay' nav link points to {href!r}, "
        f"which resolves to {resolved} but does not name a file in the build directory"
    )


# ---------------------------------------------------------------------------
# mqucifer/crew-presentation#246: replay page fits a phone with real titles
# ---------------------------------------------------------------------------


def _find_long_unbreakable_title() -> str | None:
    """Find a card title in the package that contains an unbreakable string of
    at least 40 characters with no whitespace.

    Returns the card's full title if found, or None if no such card exists
    among the cards that appear on the replay board.
    """
    index = json.loads((Path(PACKAGE) / "delivery-history.json").read_text())
    sprints = index.get("sprints", [])
    if not sprints:
        return None
    sprint_name = sprints[-1].get("name", "")

    # Load events for the last sprint (the replay page shows that sprint's board)
    pkg = Path(PACKAGE)
    events = []
    for period in index.get("periods", []):
        if period.get("sprint") == sprint_name:
            events_file = pkg / period["file"]
            if events_file.is_file():
                events = json.loads(events_file.read_text()).get("events", [])
            break
    if not events:
        return None

    # Find cards that appear on the board: cards with at least one event
    card_refs_on_board: set[tuple] = set()
    for event in events:
        card_ref = event.get("card")
        if card_ref:
            card_refs_on_board.add((card_ref.get("number"), card_ref.get("repo")))

    # Look for a card whose title has an unbreakable substring of >= 40 chars
    for card in index.get("cards", []):
        key = (card.get("number"), card.get("repo"))
        if key not in card_refs_on_board:
            continue
        title = card.get("title", "")
        # Split by whitespace: any piece of 40+ chars is an unbreakable string
        for word in title.split():
            if len(word) >= 40:
                return title
    return None


def test_replay_page_scrollwidth_at_phone_width_with_real_titles(rendered):
    """AC1 (#246): replay.html, built from the real package, has scrollWidth
    of 375 or less at a 375px viewport.

    The real package's card titles include long unbreakable strings (e.g.
    test names like 'crew-presentation/test_reads_crew.py::test_a_sprints_page_
    shows_its_throughput'). Without minmax(0, 1fr) on the board column and
    overflow-wrap on the card, the page overflows past 375px.
    """
    long_title = _find_long_unbreakable_title()
    assert long_title, (
        "no card on the replay board has a title with an unbreakable string "
        "of at least 40 characters: the test needs such a title to prove "
        "the fix (mqucifer/crew-presentation#246)"
    )

    replay = rendered("/replay.html", width=375, height=812)
    scroll_width = replay.evaluate("document.documentElement.scrollWidth")
    assert scroll_width <= 375, (
        f"replay.html is {scroll_width}px wide in a 375px viewport (mqucifer/"
        f"crew-presentation#246: a long unbreakable card title overflows the "
        f"board column)"
    )


def test_replay_card_shows_full_long_title(rendered):
    """AC2 (#246): the .replay-card holding a long unbreakable title renders
    the full title text (wrapped, not clipped or ellipsized).

    Given the replay page shows a .replay-card whose title contains an
    unbreakable string of at least 40 characters, when that card is inspected,
    its rendered text content contains every character of the full title.
    """
    long_title = _find_long_unbreakable_title()
    assert long_title, (
        "no card on the replay board has a title with an unbreakable string "
        "of at least 40 characters: the test needs such a title to prove "
        "the fix (mqucifer/crew-presentation#246)"
    )

    replay = rendered("/replay.html", width=375, height=812)

    # Find the .replay-card that contains the long title
    card_handle = replay.evaluate_handle(
        """(title) => {
            const cards = document.querySelectorAll('.replay-card');
            for (const c of cards) {
                if (c.textContent.includes(title)) return c;
            }
            return null;
        }""",
        long_title,
    )
    assert card_handle is not None, (
        f"no .replay-card contains the title {long_title!r}: "
        "the card is not rendered on the replay page"
    )

    # The full title must be present in the rendered text
    card_text = card_handle.evaluate("el => el.textContent")
    assert long_title in card_text, (
        f"the .replay-card's text {card_text!r} does not contain the full "
        f"title {long_title!r}: the long unbreakable word is clipped or "
        f"ellipsized rather than wrapped"
    )
