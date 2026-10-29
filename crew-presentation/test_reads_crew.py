"""crew-presentation reads the crew's delivery-history package: what it takes from it.

The site is built from the package start.sh put in place (a crew pull request's,
or the release the site names) and reached at QA_BASE_URL. These are the reads a
crew change could break (ADR 0008 in mqucifer/project-print): that the site
accepts the package at all, and that a sprint's page shows what sprint-metrics
answered for it, as the package carries it.
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


def sprints_with_answers() -> list[tuple[str, dict]]:
    index = json.loads((Path(PACKAGE) / "delivery-history.json").read_text())
    answers = index.get("sprint_metrics", {}).get("answers", {})
    return [(s["name"], answers[s["name"]]) for s in index["sprints"] if s["name"] in answers]


def test_the_site_accepts_the_package():
    # build.py refuses a package on a schema major it can't display (mqucifer/crew#905's case),
    # or one that doesn't validate against the schemas it carries.
    status = (Path(STATE) / "build.status").read_text().strip()
    log = (Path(STATE) / "build.log").read_text()
    assert status == "0", f"crew-presentation's build.py refused the package:\n{log[:1500]}"


def test_a_sprints_page_shows_its_throughput():
    sprints = sprints_with_answers()
    assert sprints, "the package has no sprint with sprint-metrics' answers"
    for name, answer in sprints:
        assert "throughput" in answer, (
            f"the package's sprint_metrics.answers[{name!r}] has no throughput, "
            f"which the site shows as 'stories delivered': {sorted(answer)}"
        )
        slug = name.lower().replace(" ", "-") + ".html"
        shown = re.search(
            r'stat__value[^>]*>\s*([^<]*?)\s*</span>\s*<span class="stat__label">stories delivered',
            page("/" + slug),
        )
        assert shown, f"{slug} shows no 'stories delivered'"
        expected = "—" if answer["throughput"] is None else str(answer["throughput"])
        assert html.unescape(shown.group(1)) == expected, (
            f"{slug} shows {shown.group(1)!r} stories delivered; "
            f"the package says {answer['throughput']!r}"
        )
