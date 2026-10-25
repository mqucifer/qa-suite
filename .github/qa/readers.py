"""The projects that read a producer, and the folders here a producer's pull request runs.

A producer doesn't know its readers (ADR 0008 in mqucifer/project-print). Each
project says what it reads in its own record, `.crew/project.yaml`'s
`intent.scope.uses`, so this reads every record in the owner's repositories,
from each one's default branch, through the GitHub API. Nothing here or in the
producer lists them.

    readers.py <owner> <producer> <suite>

Prints the run matrix as JSON, and writes it to $GITHUB_OUTPUT as `matrix` when
run in Actions: the producer's own folder first, then each reader that has a
folder in <suite>. A reader without one, or a record that can't be parsed, is
named in the step summary and doesn't fail the run. A failed API call does: a
reader missed would be a green check.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

API = "https://api.github.com"
RECORD = ".crew/project.yaml"


class NotARecord(Exception):
    """A record that can't be read as one."""


def reads(record: str, owner: str, producer: str) -> bool:
    """Whether a record's `uses` names the producer. Raises NotARecord if it isn't a record."""
    try:
        data = yaml.safe_load(record)
    except yaml.YAMLError as error:
        raise NotARecord(f"isn't YAML: {error}") from error
    uses = data
    for key in ("intent", "scope", "uses"):
        if not isinstance(uses, dict):
            raise NotARecord(f"has no mapping where {key} should be")
        uses = uses.get(key) or ({} if key != "uses" else [])
    if not isinstance(uses, list):
        raise NotARecord("has an intent.scope.uses that isn't a list")
    wanted = f"{owner}/{producer}".lower()
    return any(isinstance(u, dict) and str(u.get("repo", "")).lower() == wanted for u in uses)


def matrix(
    owner: str, producer: str, records: dict[str, str], folders: set[str]
) -> tuple[list[dict], list[str]]:
    """The run matrix, and a note for each reader or record it leaves out."""
    runs = [{"folder": producer, "reads": ""}]
    notes = []
    for repo, record in sorted(records.items()):
        if repo == producer:
            continue
        try:
            if not reads(record, owner, producer):
                continue
        except NotARecord as error:
            notes.append(
                f"{owner}/{repo}'s {RECORD} {error}, so whether it reads {producer} is unknown"
            )
            continue
        if repo in folders:
            runs.append({"folder": repo, "reads": producer})
        else:
            notes.append(f"{repo} reads {producer}, but qa-suite has no tests for it yet")
    return runs, notes


def _get(path: str, raw: bool = False) -> bytes | None:
    """GET from the API, or None on a 404. Any other failure raises."""
    headers = {"Accept": "application/vnd.github.raw" if raw else "application/vnd.github+json"}
    token = os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(API + path, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def records(owner: str) -> dict[str, str]:
    """Each repository's record at its default branch, by repository name."""
    repos: list[dict] = []
    page = 1
    while True:
        body = _get(f"/users/{owner}/repos?per_page=100&type=owner&page={page}")
        if body is None:
            raise SystemExit(f"::error::{owner} has no repositories the API can list")
        batch = json.loads(body)
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    found = {}
    for repo in repos:
        if repo.get("archived"):
            continue
        name = repo["name"]
        record = _get(
            f"/repos/{owner}/{name}/contents/{RECORD}?ref={repo['default_branch']}", raw=True
        )
        if record is not None:
            found[name] = record.decode()
    return found


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__, file=sys.stderr)
        return 2
    owner, producer, suite = argv[1:]
    folders = {p.name for p in Path(suite).iterdir() if p.is_dir() and not p.name.startswith(".")}
    try:
        runs, notes = matrix(owner, producer, records(owner), folders)
    except urllib.error.URLError as error:
        print(f"::error::couldn't read the projects' records through the GitHub API: {error}")
        return 1
    readers = [r["folder"] for r in runs if r["reads"]]
    lines = [
        f"Projects whose tests run because they read {producer}: {', '.join(readers) or 'none'}"
    ]
    lines += [f"- {note}" for note in notes]
    for note in notes:
        print(f"::notice::{note}")
    print("\n".join(lines))
    print(json.dumps(runs))
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a") as f:
            f.write("\n".join(lines) + "\n")
    if output := os.environ.get("GITHUB_OUTPUT"):
        with open(output, "a") as f:
            f.write(f"matrix={json.dumps(runs)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
