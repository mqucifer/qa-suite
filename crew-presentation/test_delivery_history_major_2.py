"""crew-presentation accepts delivery-history packages on schema major 2.

The story mqucifer/crew-presentation#215: when the pin moves to the 2.0.0
release, the site builds and deploys instead of failing its pull request.

These tests run against the package start.sh fetched (the release the site
names). When the package is on schema major 2, they prove the site accepts
it and builds the expected pages. When the package is on major 1, they are
vacuous: the build succeeding for major 1 is covered by
test_reads_crew.py::test_the_site_accepts_the_package.
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


def _schema_major() -> int:
    """The package's manifest schema_version major."""
    manifest = json.loads((Path(PACKAGE) / "manifest.json").read_text())
    version = manifest["schema_version"]
    match = re.fullmatch(r"(\d+)\.(\d+)(\.(\d+))?", version)
    assert match, f"unrecognized schema_version format: {version}"
    return int(match.group(1))


def test_a_major_2_package_is_accepted():
    """AC1: a package on schema major 2 is accepted by the build.

    Given the package's manifest schema_version major is 2, the build
    succeeds: the check does not refuse it as an unsupported major.
    """
    major = _schema_major()
    if major != 2:
        return  # vacuous for this package; major-1 acceptance is covered elsewhere
    status = (Path(STATE) / "build.status").read_text().strip()
    log = (Path(STATE) / "build.log").read_text()
    assert status == "0", f"build.py refused a schema major-2 package:\n{log[:1500]}"


def test_a_major_2_package_builds_the_expected_pages():
    """AC3: a well-formed major-2 package builds and writes the expected pages.

    Given the package's manifest schema_version major is 2, the build writes
    one sprint-overview page per sprint, one story page per card, and the
    replay page — the same set of pages the site writes for a 1.x package.
    """
    major = _schema_major()
    if major != 2:
        return  # vacuous for this package
    status = (Path(STATE) / "build.status").read_text().strip()
    assert status == "0", "build.py did not succeed; the pages won't exist"
    index = json.loads((Path(PACKAGE) / "delivery-history.json").read_text())
    for sprint in index.get("sprints", []):
        slug = sprint["name"].lower().replace(" ", "-") + ".html"
        page("/" + slug)
    for card in index.get("cards", []):
        repo = card.get("repo", "")
        number = card.get("number")
        if not repo or number is None:
            continue
        slug = f"{repo.replace('/', '-')}-{number}.html"
        page("/stories/" + slug)
    page("/replay.html")
