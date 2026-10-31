"""crew-presentation stops showing sprint-metrics' escalation count and rate.

Story mqucifer/crew-presentation#217: the sprint overview no longer reports
sprint-metrics' escalation_count or escalation_rate_percent. The site's
sprint overview has no 'escalations' stat, and the 'What changed' card
surfaces no escalation entry. The crew's own escalation record (escalated
events, each story's escalations) is kept.

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


def _slug(name: str) -> str:
    return name.lower().replace(" ", "-") + ".html"


def _sprints_with_metrics(index: dict) -> list[tuple[str, dict]]:
    """Sprints that have sprint-metrics answers, as (name, answer) pairs."""
    answers = index.get("sprint_metrics", {}).get("answers", {})
    return [
        (s["name"], answers[s["name"]]) for s in index.get("sprints", []) if s["name"] in answers
    ]


def _stat_labels(html: str) -> list[str]:
    """Extract stat label texts from the sprint overview's stats section."""
    stat_section = re.search(r'<section class="stats".*?</section>', html, re.DOTALL)
    if not stat_section:
        return []
    return re.findall(r"stat__label[^>]*>\s*([^<]*?)\s*<", stat_section.group(0))


def _changed_trend_entries(html: str) -> list[dict]:
    """Extract changed-trend entries from a sprint page's HTML.

    Returns a list of {"label": str, "text": str} for each entry.
    """
    entries = []
    section = re.search(r'<section class="card changed-trend".*?</section>', html, re.DOTALL)
    if not section:
        return entries
    for match in re.finditer(
        r'<div class="changed-trend-entry">.*?</div>\s*</div>', section.group(0), re.DOTALL
    ):
        entry_html = match.group(0)
        label_match = re.search(r'class="changed-trend-values">([^<]+?)\s*:', entry_html)
        text_match = re.search(r'<div class="changed-trend-text">(.*?)</div>', entry_html)
        entries.append(
            {
                "label": label_match.group(1).strip() if label_match else "",
                "text": text_match.group(1).strip() if text_match else "",
            }
        )
    return entries


def _changed_entries_for_sprint(index: dict, sprint_name: str) -> list[dict]:
    """The package's changed-trend entries for a sprint from analysis.sprints."""
    for sprint_analysis in index.get("analysis", {}).get("sprints", []):
        if sprint_analysis.get("sprint") == sprint_name:
            return sprint_analysis.get("changed", [])
    return []


def test_sprint_overview_has_no_escalations_stat():
    """AC1: no sprint overview's stats section shows an 'escalations' stat.

    Given a package whose sprint-metrics answer carries escalation_count
    (a 1.x package) or omits it (a 2.0.0 package), when any sprint page is
    built, its stats section has no 'escalations' stat: the site no longer
    reports sprint-metrics' escalation count or rate.
    """
    index = _load_index()
    sprints = _sprints_with_metrics(index)
    assert sprints, "the package has no sprint with sprint-metrics' answers"

    for name, _answer in sprints:
        html = page("/" + _slug(name))
        labels = _stat_labels(html)
        escalation_labels = [l for l in labels if "escalation" in l.lower()]
        assert not escalation_labels, (
            f"{_slug(name)}: the stats section has an escalation stat "
            f"(labels={escalation_labels}); "
            f"sprint-metrics' escalation count/rate must not be shown"
        )


def test_changed_trend_shows_no_escalation_entry():
    """AC1+AC2: the 'What changed' card never shows an escalation entry, while
    other changed measures still are.

    Given a package whose analysis.sprints[].changed list includes an
    escalation_count entry alongside other measures, when that sprint's page
    is built, the escalation_count entry is not shown in 'What changed', while
    the other changed measures still are.
    """
    index = _load_index()
    sprints = _sprints_with_metrics(index)
    assert sprints, "the package has no sprint with sprint-metrics' answers"

    for name, _answer in sprints:
        slug = _slug(name)
        html = page("/" + slug)
        rendered = _changed_trend_entries(html)

        # No rendered entry has a label containing 'escalation'
        escalation_entries = [e for e in rendered if "escalation" in e["label"].lower()]
        assert not escalation_entries, (
            f"{slug}: the 'What changed' card shows an escalation entry "
            f"({escalation_entries}); the site must not show it"
        )

        # The number of rendered entries equals the number of non-escalation
        # entries in the package's changed list for this sprint
        package_changed = _changed_entries_for_sprint(index, name)
        non_escalation = [e for e in package_changed if e.get("measure") != "escalation_count"]
        assert len(rendered) == len(non_escalation), (
            f"{slug}: the package has {len(non_escalation)} non-escalation changed "
            f"entries, but the page shows {len(rendered)} changed-trend entries "
            f"(package total: {len(package_changed)}, "
            f"escalation entries filtered: {len(package_changed) - len(non_escalation)})"
        )


def test_replay_page_carries_escalated_events():
    """AC3: the replay page still carries the crew's own escalated events and
    the build does not fail.

    Given a package that records the crew's own escalation record (an event
    with kind 'escalated' in the last sprint's events file), when the build
    runs, the replay page still carries that sprint's escalated events and the
    build does not fail. Only sprint-metrics' escalation_count /
    escalation_rate_percent are dropped; the crew's own record stays.
    """
    # The build must have succeeded
    status = (Path(STATE) / "build.status").read_text().strip()
    assert status == "0", (
        f"the build failed with exit code {status}: "
        "the site must build even when the package carries escalated events"
    )

    # The replay page shows the last sprint's events. Find that sprint's
    # events file and check for escalated events there.
    index = _load_index()
    sprints = index.get("sprints", [])
    if not sprints:
        return  # no sprints: vacuous, but the build-doesn't-fail assertion holds

    last_sprint_name = sprints[-1]["name"]
    periods = index.get("periods", [])
    escalated_events_found = False
    for period in periods:
        if period.get("sprint") != last_sprint_name:
            continue
        events_file = Path(PACKAGE) / period["file"]
        if not events_file.is_file():
            break
        data = json.loads(events_file.read_text())
        for event in data.get("events", []):
            if event.get("kind") == "escalated":
                escalated_events_found = True
                break
        break  # only the last sprint's file matters for the replay page

    if not escalated_events_found:
        # No escalated events in the last sprint: the test is vacuous for the
        # replay-page assertion, but the build-doesn't-fail check still holds.
        return

    # The replay page's embedded JSON must carry the escalated events
    replay_html = page("/replay.html")
    match = re.search(
        r'<script type="application/json" id="replay-data">(.*?)</script>',
        replay_html,
        re.DOTALL,
    )
    assert match, "the replay page has no embedded replay-data JSON"
    replay_data = json.loads(match.group(1))
    events = replay_data.get("events", [])
    escalated_in_replay = [e for e in events if e.get("kind") == "escalated"]
    assert escalated_in_replay, (
        "the package records escalated events in the last sprint, "
        "but the replay page's JSON carries none: "
        "the crew's own escalation record must be preserved"
    )
