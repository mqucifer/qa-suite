"""crew-presentation's sprint overview: a sprint's story list holds only that sprint's stories.

Which stories a sprint lists depends on the package: delivered dates or the card's
sprint. Either way, a story is delivered once, so it's on one sprint's list. The
site's own tests don't hold this: with the sprint's filter removed, they all pass.

The package says only which sprints there are; the rest is read from the pages.
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


def _sprint_pages() -> list[str]:
    """The sprint pages the site builds: one per sprint with sprint-metrics' answers."""
    index = json.loads((Path(PACKAGE) / "delivery-history.json").read_text())
    answers = index.get("sprint_metrics", {}).get("answers", {})
    return [
        s["name"].lower().replace(" ", "-") + ".html"
        for s in index.get("sprints", [])
        if s["name"] in answers
    ]


def _stories_listed(html: str) -> list[str]:
    """The story pages linked from 'The Architect's split, story by story' on a sprint's page."""
    section = re.search(r'<section[^>]*aria-labelledby="split-h".*?</section>', html, re.DOTALL)
    return re.findall(r'href="(stories/[^"]+)"', section.group(0)) if section else []


def test_a_story_is_listed_under_one_sprint_only():
    """No story is on more than one sprint's list, and at least one list has a story."""
    pages = _sprint_pages()
    assert pages, "the package has no sprint with sprint-metrics' answers"

    listed_on: dict[str, list[str]] = {}
    for slug in pages:
        for story in _stories_listed(page("/" + slug)):
            listed_on.setdefault(story, []).append(slug)

    assert listed_on, "no sprint's page lists a story, so nothing was checked"
    repeated = {story: slugs for story, slugs in listed_on.items() if len(slugs) > 1}
    assert not repeated, (
        f"{len(repeated)} of {len(listed_on)} stories are on more than one sprint's list, "
        f"so a list isn't limited to its own sprint: {dict(list(repeated.items())[:3])}"
    )
