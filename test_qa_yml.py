"""Tests for qa.yml's dispute build: the disputed pull request is merged with the
project's main as it is at the run, in the job that builds it
(mqucifer/qa-suite#64)."""

from pathlib import Path

WORKFLOW = Path(".github/workflows/qa.yml")
STEP = "- name: Merge the project's main into the disputed pull request"


def _step() -> str:
    text = WORKFLOW.read_text()
    assert STEP in text
    return text.split(STEP)[1].split("\n      - name:")[0]


def test_merge_runs_only_for_a_dispute():
    assert "if: inputs.build-ref != ''" in _step()


def test_merge_comes_between_checkout_and_build():
    text = WORKFLOW.read_text()
    checkout = text.index(
        "- name: Check out the project's main, or the disputed pull request's head"
    )
    start = text.index("- name: Start the build")
    assert checkout < text.index(STEP) < start


def test_merge_takes_main_now_not_githubs_merge_ref():
    step = _step()
    assert "git fetch --quiet --no-tags origin" in step
    assert 'merge --no-edit --quiet "origin/${main_ref}"' in step
    assert "refs/pull/" not in step


def test_a_conflict_fails_before_the_build():
    step = _step()
    assert "can't merge with" in step
    assert "exit 1" in step


def test_summary_names_both_commits():
    step = _step()
    assert "at ${head} merged with ${main_ref} at ${main}" in step
