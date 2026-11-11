"""Tests for suite.yml's dispute handling: it builds at the disputed pull request
merged with main, not at a stale GitHub merge ref (mqucifer/crew#945)."""

from pathlib import Path

WORKFLOW = Path(".github/workflows/suite.yml")


def _text() -> str:
    return WORKFLOW.read_text()


def _disputed_step() -> str:
    return _text().split("id: disputed")[1]


def test_dispute_merges_head_with_main_not_merge_ref():
    """Criterion 1: the dispute's build is produced by merging the PR head with
    the project's main in the workflow; it is not read from
    refs/pull/<n>/merge."""
    text = _text()
    # The workflow must NOT use the merge ref API endpoint.
    assert "commits/refs/pull/${pull}/merge" not in text
    # The step must check out the PR head and merge origin/main.
    step = _disputed_step()
    assert "checkout" in step
    assert "merge origin/main" in step
    # The merge result is output as `head` for the qa job's build-ref.
    assert 'echo "head=$merge_sha"' in step


def test_dispute_merge_commit_reachable_by_qa_job():
    """The merge commit must be pushed to a ref on the project's repository,
    so the qa job's checkout can fetch it (a local commit is unreachable
    across jobs)."""
    step = _disputed_step()
    # The step pushes the merge commit to a ref on the target repo.
    assert "push --quiet" in step
    # The ref names the dispute, so it's unique per pull request.
    assert "refs/qa-dispute" in step


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


def test_dispute_uses_app_token_not_github_token():
    """The clone and push to the target repo use the minted App token, not
    GITHUB_TOKEN (which is scoped to qa-suite and can't write to other repos)."""
    step = _disputed_step()
    assert "GITHUB_TOKEN" not in step
    # The disputed step references the token step's output.
    assert "steps.token.outputs.token" in _text()


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
