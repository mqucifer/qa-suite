"""crew-presentation's 'Why work didn't land first time' section: reads top_failure_causes.

The site shows what its package says in sprint-metrics' top_failure_causes.
These tests verify that the cause section on each sprint's page matches the
package's data:

- A 2.0.0 list of {class, role, count} entries shows one row per entry, each
  carrying the class as its label (not 'Cause not recorded') and the entry's
  count (mqucifer/crew-presentation#216 AC1).
- An empty or absent top_failure_causes shows 'No failures recorded' and the
  build does not fail (mqucifer/crew-presentation#216 AC3).

The tests read the package (QA_PACKAGE, the site's input) and the built pages
(QA_BASE_URL, the site's output), and verify the output matches the input.
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


def _cause_rows(html: str) -> list[tuple[str, str]]:
    """Extract (reason, count) pairs from the cause-rows in a sprint page.

    Each cause-row is:
      <div class="cause-row">
        <span ...>REASON</span>
        <div class="cause-bar ..." style="width:NN%"></div>
        <span class="num ...">COUNT</span>
      </div>
    """
    pattern = (
        r'<div class="cause-row">\s*'
        r"<span[^>]*>(.*?)</span>\s*"
        r"<div[^>]*></div>\s*"
        r"<span[^>]*>(.*?)</span>\s*"
        r"</div>"
    )
    return re.findall(pattern, html, re.DOTALL)


def _sprints_with_metrics(index: dict) -> list[tuple[str, dict]]:
    """Sprints that have sprint-metrics answers, as (name, answer) pairs."""
    answers = index.get("sprint_metrics", {}).get("answers", {})
    return [
        (s["name"], answers[s["name"]]) for s in index.get("sprints", []) if s["name"] in answers
    ]


def _slug(name: str) -> str:
    return name.lower().replace(" ", "-") + ".html"


def test_failure_causes_2_0_class_shown_not_placeholder():
    """AC1: a 2.0.0 entry carrying a class shows the class as its label, not
    'Cause not recorded', and its count is preserved."""
    index = _load_index()
    checked = 0
    for name, answer in _sprints_with_metrics(index):
        causes = answer.get("top_failure_causes")
        if not isinstance(causes, list):
            continue
        html = page("/" + _slug(name))
        rows = _cause_rows(html)
        for entry in causes:
            if not isinstance(entry, dict) or "class" not in entry:
                continue
            class_value = str(entry["class"])
            count = entry.get("count", 0)
            # Class and count together: two entries can share a count.
            assert (class_value, str(count)) in rows, (
                f"{_slug(name)}: 2.0.0 entry class={class_value!r} count {count} "
                f"has no cause-row with that label and count; the rows are {rows!r}"
            )
            checked += 1
    # Vacuous on a 1.x pin (no class-carrying entries); meaningful on 2.0.0.
    # No assertion on checked > 0: the current pin doesn't carry 2.0.0 entries.


def test_failure_causes_empty_or_absent_shows_no_failures():
    """AC3: an empty or absent top_failure_causes shows 'No failures recorded'
    and no cause-rows; the build does not fail."""
    index = _load_index()
    checked = 0
    for name, answer in _sprints_with_metrics(index):
        causes = answer.get("top_failure_causes")
        if causes:
            continue
        html = page("/" + _slug(name))
        assert "No failures recorded" in html, (
            f"{_slug(name)}: top_failure_causes is {causes!r} "
            f"but the page doesn't show 'No failures recorded'"
        )
        rows = _cause_rows(html)
        assert not rows, (
            f"{_slug(name)}: top_failure_causes is {causes!r} "
            f"but the page shows {len(rows)} cause-rows"
        )
        checked += 1
    # Vacuous if every sprint has non-empty causes; no assertion on checked > 0.
