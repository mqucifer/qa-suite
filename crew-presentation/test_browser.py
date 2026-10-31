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
- AC2 (#246): every .replay-card on the board shows its full title (wrapped, not clipped)

The real package may hold no long word, so these hold for whatever it has. The long
word itself is crew-presentation's own test_replay_page_scrollwidth_at_phone_width.
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


def test_replay_page_scrollwidth_at_phone_width_with_real_titles(rendered):
    """AC1 (#246): replay.html, built from the real package, has scrollWidth
    of 375 or less at a 375px viewport, whatever titles the package holds.
    """
    replay = rendered("/replay.html", width=375, height=812)
    scroll_width = replay.evaluate("document.documentElement.scrollWidth")
    assert scroll_width <= 375, (
        f"replay.html is {scroll_width}px wide in a 375px viewport (mqucifer/"
        f"crew-presentation#246: a long unbreakable card title overflowed the "
        f"board column)"
    )


def test_replay_cards_show_their_full_titles(rendered):
    """AC2 (#246): every .replay-card on the board renders its card's full title
    from the package, wrapped rather than clipped or ellipsized.

    A card is matched to the package by its link's href, the card's url.
    """
    index = json.loads((Path(PACKAGE) / "delivery-history.json").read_text())
    titles = {card.get("url"): card.get("title", "") for card in index.get("cards", [])}

    replay = rendered("/replay.html", width=375, height=812)
    cards = replay.evaluate(
        """() => [...document.querySelectorAll('.replay-card')].map((card) => ({
            href: card.querySelector('a')?.getAttribute('href'),
            text: card.textContent,
            clipped: card.scrollWidth > card.clientWidth,
        }))"""
    )
    for card in cards:
        assert card["href"] in titles, (
            f"a .replay-card links to {card['href']!r}, which no card in the package has"
        )
        title = titles[card["href"]]
        assert title in card["text"], (
            f"the .replay-card's text {card['text']!r} does not contain the full title {title!r}"
        )
        assert not card["clipped"], (
            f"the .replay-card for {title!r} is wider than its box at 375px: "
            "its title is clipped rather than wrapped"
        )
