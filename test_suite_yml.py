"""Tests for suite.yml's dispute handling: it builds at the disputed pull request
merged with main, not at the raw head commit (mqucifer/crew#945)."""

from pathlib import Path

WORKFLOW = Path(".github/workflows/suite.yml")


def _text() -> str:
    return WORKFLOW.read_text()


def test_dispute_resolves_merge_ref_not_head():
    """Criterion 1: a dispute whose pull request is behind main builds at the
    pull request merged with main. The workflow must resolve
    refs/pull/<n>/merge via the GitHub API, not use the marker's raw head SHA
    as the build ref."""
    text = _text()
    # The workflow resolves the merge ref via the GitHub API.
    assert "refs/pull/${" in text and "merge" in text
    # It does not pass the marker's raw head SHA as the build ref.
    # The output is the resolved merge SHA, not the marker's `head=` field.
    disputed_step = text.split("id: disputed")[1]
    # The step resolves the merge ref and outputs that SHA as `head`.
    assert "merge_sha" in disputed_step
    assert 'echo "head=$merge_sha"' in disputed_step
    # The marker's raw head is not used as the build ref.
    assert 'echo "head=$head"' not in disputed_step


def test_dispute_conflict_fails_with_cant_merge():
    """Criterion 2: a dispute whose pull request can't merge cleanly fails the
    run before any test executes, with a message containing 'can't merge'."""
    text = _text()
    # The failure message must contain the exact string "can't merge".
    assert "can't merge" in text
    # The failure exits the step (exit 1) so the qa job never runs.
    disputed_step = text.split("id: disputed")[1]
    # The error is emitted via an ::error:: annotation (visible in the log).
    assert "::error::" in disputed_step
    # The step exits 1 on failure, preventing the qa job from running.
    assert "exit 1" in disputed_step


def test_no_dispute_builds_default_branch():
    """Criterion 3: a run with no dispute marker builds the project's default
    branch, unchanged from current behaviour. When the marker is absent, the
    disputed step exits 0 without setting outputs, so build-ref is empty and
    qa.yml checks out the default branch."""
    text = _text()
    # When no marker is found, the step exits 0 without setting any outputs.
    disputed_step = text.split("id: disputed")[1]
    assert 'if [ -z "$found" ]; then' in disputed_step
    assert "exit 0" in disputed_step
    # The qa job's build-ref expression falls through to empty string when
    # disputed-repo is unset (no dispute).
    assert "disputed-repo && needs.changed.outputs.disputed-head || ''" in text
