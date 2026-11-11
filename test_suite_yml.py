"""Tests for suite.yml's dispute handling: it builds at the disputed pull request
merged with main, not at a stale GitHub merge ref (mqucifer/crew#945)."""

from pathlib import Path

WORKFLOW = Path(".github/workflows/suite.yml")
QA_WORKFLOW = Path(".github/workflows/qa.yml")


def _text() -> str:
    return WORKFLOW.read_text()


def _qa_text() -> str:
    return QA_WORKFLOW.read_text()


def _disputed_step() -> str:
    return _text().split("id: disputed")[1]


def test_dispute_merges_head_with_main_not_merge_ref():
    """Criterion 1: the dispute's build is produced by merging the PR head with
    the project's main in the workflow; it is not read from
    refs/pull/<n>/merge."""
    text = _text()
    # The workflow must NOT use the merge ref API endpoint.
    assert "commits/refs/pull/${pull}/merge" not in text
    # The step checks out the PR head and verifies it merges with origin/main.
    step = _disputed_step()
    assert "checkout" in step
    assert "merge origin/main" in step
    # The head SHA is emitted for the qa job's build-ref, not a merge SHA.
    assert 'echo "head=$head_sha"' in step
    # The build merge happens in qa.yml, after the checkout.
    qa = _qa_text()
    assert "merge origin/main" in qa


def test_dispute_build_merge_in_qa_yml():
    """The build merge is performed in qa.yml after the checkout, so no
    cross-repo push is needed."""
    qa = _qa_text()
    # qa.yml merges origin/main into the checked-out build when build-ref is set.
    assert "merge origin/main" in qa
    # The step is gated on build-ref being non-empty (a dispute).
    assert "inputs.build-ref" in qa
    # No push to the target repo in suite.yml.
    step = _disputed_step()
    assert "git push" not in step


def test_dispute_summary_names_head_and_main():
    """Criterion 2: the step summary names both the PR head commit and the main
    commit it was merged with, so a reader sees both identifiers."""
    step = _disputed_step()
    # The step captures both SHAs.
    assert "head_sha" in step
    assert "main_sha" in step
    # The summary line references both.
    summary_lines = [l for l in step.splitlines() if "GITHUB_STEP_SUMMARY" in l]
    assert any("head_sha" in l and "main_sha" in l for l in summary_lines)


def test_dispute_conflict_fails_with_cant_merge():
    """Criterion 3: a dispute whose pull request can't merge cleanly fails the
    run before any test executes, with a message containing 'can't merge'."""
    text = _text()
    # The failure message must contain the exact string "can't merge".
    assert "can't merge" in text
    # The failure exits the step (exit 1) so the qa job never runs.
    step = _disputed_step()
    # The error is emitted via an ::error:: annotation (visible in the log).
    assert "::error::" in step
    # The step exits 1 on failure, preventing the qa job from running.
    assert "exit 1" in step


def test_no_dispute_builds_default_branch():
    """A run with no dispute marker builds the project's default branch,
    unchanged from current behaviour. When the marker is absent, the
    disputed step exits 0 without setting outputs, so build-ref is empty and
    qa.yml checks out the default branch."""
    text = _text()
    # When no marker is found, the step exits 0 without setting any outputs.
    step = _disputed_step()
    assert 'if [ -z "$found" ]; then' in step
    assert "exit 0" in step
    # The qa job's build-ref expression falls through to empty string when
    # disputed-repo is unset (no dispute).
    assert "disputed-repo && needs.changed.outputs.disputed-head || ''" in text
