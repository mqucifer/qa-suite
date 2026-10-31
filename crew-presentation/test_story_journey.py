"""crew-presentation's story-journey root page: CSS prevents horizontal scroll.

The story-journey root page (no card argument) shows a list of story links,
one per card in the package. Each link's text is 'repo#number — title'.
With long titles, the anchors' intrinsic width exceeds a 375px viewport,
forcing horizontal scroll (mqucifer/crew-presentation#227).

The fix: a CSS rule sets overflow-wrap (or word-break) on the story list
links so long titles wrap within the viewport.

This test reads the site's CSS (QA_BASE_URL/css/site.css) and verifies the
rule is present. It fails on the buggy version (no overflow-wrap rule) and
passes on the fixed version.
"""

from __future__ import annotations

import os
import re
import urllib.error
import urllib.request

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


def test_story_journey_links_wrap_not_scroll():
    """AC1: the CSS prevents story links from forcing horizontal scroll at 375px.

    Given the story-journey root page built from a package whose cards array
    contains a card with a long title, when rendered at a 375px viewport,
    document.documentElement.scrollWidth must be 375 or less (WCAG 2.2 1.4.10
    Reflow). The mechanism: a CSS rule on the story list anchors sets
    overflow-wrap or word-break so long text wraps rather than extends the
    layout.

    This test checks the served CSS for that rule. It fails when the rule is
    absent (the bug) and passes when it is present (the fix).
    """
    css = page("/css/site.css")

    # The story-journey root page renders links as:
    #   <section><h2>Stories</h2><ul><li><a>...</a></li>...</ul></section>
    # A rule targeting these anchors must set overflow-wrap or word-break.
    #
    # Possible selectors: 'section ul li a', 'section li a', etc.
    # The key is that it reaches anchors inside <li> inside <section>'s <ul>.

    found = False

    # Check for overflow-wrap or word-break on a selector that targets
    # anchors within sections' lists.
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        selector = match.group(1).strip()
        body = match.group(2)

        # Must target an anchor (a) in the selector
        if not re.search(r"\ba\b", selector):
            continue

        # Must reference li, ul, or section in the selector (the story list)
        if not re.search(r"\b(li|ul|section)\b", selector):
            continue

        # Must set overflow-wrap or word-break to a wrapping value
        if re.search(
            r"(overflow-wrap|word-wrap|word-break)\s*:\s*(break-word|anywhere|auto)",
            body,
        ):
            found = True
            break

    assert found, (
        "site.css has no rule that sets overflow-wrap, word-wrap, or word-break "
        "to a wrapping value on anchors within the story list (section/ul/li). "
        "Long card titles will exceed a 375px viewport and force horizontal "
        "scroll. (mqucifer/crew-presentation#227: story links 402-631px wide "
        "in a 375px viewport.)"
    )
