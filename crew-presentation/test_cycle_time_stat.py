"""crew-presentation's sprint overview: the cycle-time stat renders a missing value as an em dash.

When sprint-metrics' answer for a sprint has cycle_time_minutes null, the
cycle-time stat's value element must contain the em dash '—', the same mark
_stat_value uses for other missing stats (mqucifer/crew-presentation#233: the
old _format_minutes returned '' for None, so the stat rendered a blank value
while the other four stats on the row showed '—').

The test reads the package (QA_PACKAGE, the site's input) and the built pages
(QA_BASE_URL, the site's output), and verifies the cycle-time stat matches.
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


def _expected_cycle_time(minutes) -> str:
    """The display text build.py's _format_minutes produces for a cycle_time_minutes value.

    A missing value (JSON null) renders '—', the same mark _stat_value uses
    for other missing stats. A present value renders in the canonical
    vocabulary (mqucifer/crew-presentation#340): below a day, hours and
    minutes with 'h' and 'min'; at a day and up, days and hours with 'd'
    and 'h', minutes dropped. Zero units are omitted, so 60 is '1 h',
    92 is '1 h 32 min', and 1500 is '1 d 1 h'.
    """
    if minutes is None:
        return "\u2014"
    total_minutes = int(minutes)
    if total_minutes < 60:
        return f"{total_minutes} min"
    if total_minutes < 1440:
        hours, mins = divmod(total_minutes, 60)
        if mins == 0:
            return f"{hours} h"
        return f"{hours} h {mins} min"
    days, remainder = divmod(total_minutes, 1440)
    hours = remainder // 60
    if hours == 0:
        return f"{days} d"
    return f"{days} d {hours} h"


def test_cycle_time_stat_matches_package_value():
    """The cycle-time stat's value matches the package's cycle_time_minutes.

    For each sprint with sprint-metrics' answers, the cycle-time stat's value
    element (the <span class="stat__value num"> inside the stat labelled
    "cycle time") contains the em dash '—' when cycle_time_minutes is null,
    the same mark the other stat value elements on that .stats row show
    for their missing values, or the formatted hours-and-minutes value
    otherwise.
    """
    index = json.loads((Path(PACKAGE) / "delivery-history.json").read_text())
    answers = index.get("sprint_metrics", {}).get("answers", {})
    sprints = [s for s in index.get("sprints", []) if s["name"] in answers]
    assert sprints, "the package has no sprint with sprint-metrics' answers"

    for sprint in sprints:
        name = sprint["name"]
        metrics = answers[name]
        cycle_time = metrics.get("cycle_time_minutes")

        slug = name.lower().replace(" ", "-") + ".html"
        html_content = page("/" + slug)
        match = re.search(
            r'<span class="stat__value[^"]*">\s*([^<]*?)\s*</span>\s*<span class="stat__label">cycle time</span>',
            html_content,
        )
        assert match, f"{slug} shows no 'cycle time' stat"
        shown = html.unescape(match.group(1)).strip()
        expected = _expected_cycle_time(cycle_time)
        assert shown == expected, (
            f"{slug}: cycle_time_minutes is {cycle_time!r} in the package, "
            f"expected {expected!r} in the cycle-time stat, got {shown!r}"
        )
