"""sprint-metrics through its HTTP API: a card finished in a sprint is counted there.

The surface is the service's API as docs/service.md in sprint-metrics describes
it, reached at QA_BASE_URL, which start.sh sets.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid

import pytest

# Fails rather than skips without it: a skipped suite would be a green check.
BASE = os.environ.get("QA_BASE_URL", "")
if not BASE:
    pytest.fail("QA_BASE_URL isn't set: run start.sh first", pytrace=False)


def call(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        BASE + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"{}")


def event(card: str, kind: str, at: str, sprint: str) -> dict:
    return {
        "api_version": "1",
        "card_id": card,
        "type": kind,
        "timestamp": at,
        "sprint": sprint,
        "card": {"created": "2026-01-05"},
    }


def test_a_finished_card_counts_in_its_sprint():
    # A sprint of its own, so a rerun against the same database counts only this one.
    sprint = f"QA-{uuid.uuid4().hex[:8]}"
    card = f"{sprint}-card"
    status, _ = call(
        "POST",
        "/sprints",
        {"name": sprint, "start_date": "2026-01-05", "end_date": "2026-01-16", "timezone": "UTC"},
    )
    assert status == 200, "POST /sprints didn't register the sprint"
    for kind, at in (("started", "2026-01-06T10:00:00Z"), ("finished", "2026-01-08T10:00:00Z")):
        status, body = call("POST", "/events", event(card, kind, at, sprint))
        assert status == 200, f"POST /events refused the {kind} event: {body}"

    status, body = call("GET", f"/range?start={sprint}&end={sprint}")

    assert status == 200, f"GET /range answered {status}: {body}"
    metrics = body["sprints"][sprint]
    assert metrics["throughput"] == 1
    assert metrics["cycle_time_days"] == 2
