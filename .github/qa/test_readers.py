"""readers.py's choice of folders, from records as the repositories hold them."""

from __future__ import annotations

import pytest
from readers import NotARecord, matrix, reads

PRESENTATION = """
version: 3
intent:
  scope:
    uses:
    - repo: mqucifer/crew
      file: README.md
    - repo: mqucifer/design-system
"""


def test_a_record_naming_the_producer_reads_it():
    assert reads(PRESENTATION, "mqucifer", "crew")
    assert reads(PRESENTATION, "mqucifer", "Design-System")
    assert not reads(PRESENTATION, "mqucifer", "sprint-metrics")
    assert not reads(PRESENTATION, "someone-else", "crew")


def test_a_record_without_uses_reads_nothing():
    assert not reads("version: 3\nintent:\n  scope:\n    purpose: x\n", "mqucifer", "crew")


@pytest.mark.parametrize("record", ["- a list", "intent: {scope: {uses: crew}}", "a: [b"])
def test_what_isnt_a_record_says_so(record):
    with pytest.raises(NotARecord):
        reads(record, "mqucifer", "crew")


def test_the_producer_runs_first_then_readers_with_folders():
    records = {
        "crew-presentation": PRESENTATION,
        "other-reader": PRESENTATION,
        "sprint-metrics": "version: 3\n",
        "broken": "a: [b",
        "crew": PRESENTATION,
    }
    runs, notes = matrix("mqucifer", "crew", records, {"crew-presentation", "sprint-metrics"})
    assert runs == [
        {"folder": "crew", "reads": ""},
        {"folder": "crew-presentation", "reads": "crew"},
    ]
    assert notes == [
        "mqucifer/broken's .crew/project.yaml isn't YAML: " + notes[0].split("isn't YAML: ")[1],
        "other-reader reads crew, but qa-suite has no tests for it yet",
    ]
