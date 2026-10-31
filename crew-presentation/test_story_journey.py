"""crew-presentation's story-journey root page: story links.

The story-journey root page (no card argument) shows a list of story links,
one per card in the package. Each link's text is 'repo#number — title' (the
full string, not truncated).

These tests verify:
- The root page shows one li per card in the package, with the full link
  text matching the package's cards (mqucifer/crew-presentation#227 AC2).

The tests read the built page (QA_BASE_URL/story-journey.html) and the
package (QA_PACKAGE) to determine expected links.
"""

from __future__ import annotations

import html
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


def _load_cards() -> list[dict]:
    """The cards array from the package's delivery-history.json."""
    index = json.loads((Path(PACKAGE) / "delivery-history.json").read_text())
    return index.get("cards", [])


def test_story_journey_root_shows_all_cards_as_links():
    """AC2: the story-journey root page shows one li per card, with the full link text.

    Given the story-journey root page built from a package whose cards array
    contains N cards, the page's section contains exactly N li elements, each
    with one a child whose textContent equals 'repo#number — title'.
    """
    cards = _load_cards()
    assert cards, (
        "the package has no cards: the story-journey page's list would be empty, "
        "and this test can't verify the link structure"
    )

    page_html = page("/story-journey.html")

    # The root story-journey page (no card argument) renders a section with a ul
    # of story links.
    section_match = re.search(r"<h2>Stories</h2>\s*<ul>(.*?)</ul>", page_html, re.DOTALL)
    assert section_match, (
        "story-journey.html has no <section> with a 'Stories' heading and <ul>: "
        "the root page's story list is missing"
    )
    list_html = section_match.group(1)

    # Extract all <li><a ...>text</a></li> elements.
    items = re.findall(r"<li>\s*<a[^>]*>(.*?)</a>\s*</li>", list_html, re.DOTALL)
    assert len(items) == len(cards), (
        f"story-journey.html shows {len(items)} story links, but the package "
        f"records {len(cards)} cards"
    )

    # Each link's text must be 'repo#number — title' (the full string, not truncated).
    # Jinja2's autoescape converts characters like ' to &#39;, so decode
    # entities before comparing to the package's plain-text title.
    for i, (card, link_text) in enumerate(zip(cards, items)):
        expected = f"{card['repo']}#{card['number']} — {card['title']}"
        actual = html.unescape(link_text)
        assert actual == expected, (
            f"story link {i + 1} is {actual!r}, expected {expected!r} "
            f"(card: repo={card['repo']!r}, number={card['number']}, "
            f"title={card['title']!r})"
        )
