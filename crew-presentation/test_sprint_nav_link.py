"""crew-presentation's nav: the Sprint link on non-sprint pages points to a real sprint page.

mqucifer/crew-presentation#229: the header's 'Sprint' nav link had an empty href
(sprint_slug was '' on non-sprint pages), so clicking it only reloaded the same
page. The link must point to a file that exists in the build output.

These tests check the Sprint link in nav[aria-label='Views'] on:
- replay.html (AC1)
- every story page under stories/ (AC2)

and verify its href names a file that exists in the build directory.
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


def _sprint_nav_href(html: str) -> str:
    """Extract the href of the Sprint link in nav[aria-label='Views']."""
    nav_match = re.search(r"<nav[^>]*aria-label=[\"']Views[\"'][^>]*>(.*?)</nav>", html, re.DOTALL)
    if not nav_match:
        pytest.fail("no nav[aria-label='Views'] found in the page", pytrace=False)
    nav_html = nav_match.group(1)
    link_match = re.search(r"<a\s+href=[\"']([^\"']*)[\"'][^>]*>\s*Sprint\s*</a>", nav_html)
    if not link_match:
        pytest.fail("no Sprint link found in nav[aria-label='Views']", pytrace=False)
    return link_match.group(1)


def _url_exists(url: str) -> bool:
    """Check whether a URL returns HTTP 200."""
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.status == 200
    except (urllib.error.HTTPError, urllib.error.URLError):
        return False


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


def test_sprint_nav_link_on_replay_html():
    """AC1: replay.html's Sprint nav link has a non-empty href naming an existing file.

    Given a built site with at least one sprint in the delivery-history package,
    the Sprint link in nav[aria-label='Views'] on replay.html has a non-empty
    href whose value names a file that exists in the build directory.
    """
    index = json.loads((Path(PACKAGE) / "delivery-history.json").read_text())
    sprints = index.get("sprints", [])
    assert sprints, "the package has no sprints: the test requires at least one"

    html = page("/replay.html")
    href = _sprint_nav_href(html)
    assert href, "the Sprint nav link on replay.html has an empty href"

    resolved = urljoin(BASE + "/replay.html", href)
    assert _url_exists(resolved), (
        f"replay.html's Sprint nav link points to {href!r}, "
        f"which resolves to {resolved} but does not exist in the build directory"
    )


def test_sprint_nav_link_on_story_pages():
    """AC2: every story page's Sprint nav link has a non-empty href naming an existing file.

    Given a built site with at least one sprint and at least one story card in
    the delivery-history package, every story page under stories/ has a Sprint
    link in nav[aria-label='Views'] whose href, resolved relative to the story
    page's directory, names a file that exists in the build directory.
    """
    index = json.loads((Path(PACKAGE) / "delivery-history.json").read_text())
    sprints = index.get("sprints", [])
    assert sprints, "the package has no sprints: the test requires at least one"

    story_paths = _story_page_paths()
    assert story_paths, "the package has no story cards: the test requires at least one"

    for path in story_paths:
        html = page(path)
        href = _sprint_nav_href(html)
        assert href, f"{path}: the Sprint nav link has an empty href"

        resolved = urljoin(BASE + path, href)
        assert _url_exists(resolved), (
            f"{path}: the Sprint nav link points to {href!r}, "
            f"which resolves to {resolved} but does not exist in the build directory"
        )
