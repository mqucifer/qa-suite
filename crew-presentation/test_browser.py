"""crew-presentation's view nav: 'A story's journey' and 'Replay' links resolve from stories/ subdirectory.

mqucifer/crew-presentation#230: the header's 'A story's journey' and 'Replay' nav
links in story pages used root-relative paths (story-journey.html, replay.html),
which from the stories/ subdirectory resolved to stories/story-journey.html and
stories/replay.html — files that don't exist. The build only creates root-level
versions. From the site's deepest view the reader could not navigate anywhere.

These tests check that:
- AC1: a story page's 'A story's journey' link resolves to a file in the build
- AC2: a story page's 'Replay' link resolves to a file in the build
- AC3: story-journey.html (root level) 'Replay' link resolves to a file in the build
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
