# qa-suite

QA's functional tests, one folder per project, run against each pull request's
build by GitHub Actions (ADR 0006 in mqucifer/project-print). A failing test
fails the pull request's `qa-suite / qa` check, which blocks the merge once the
Sponsor makes it required. A Developer who thinks a test is wrong disputes it;
they don't edit it here.

## How a pull request runs it
Every delivery repository's `.github/workflows/qa.yml`, from project-template,
calls `.github/workflows/qa.yml` here with its repository's name. That workflow:

1. checks out the pull request, and this repository's main;
2. passes, saying so, if there is no folder here for the project yet;
3. runs `<project>/start.sh <checkout>`, which builds and starts the project as
   its own CI does and writes `QA_BASE_URL` to `$GITHUB_ENV`;
4. runs `uv run pytest <project>`;
5. runs `<project>/stop.sh`, always.

Its `suite-ref` input is only for proving a change here before it merges, and
`build-repository` only for `suite.yml` below. The template sets neither.

## The projects that read it run too
A pull request also runs the folders of the projects that read its project
(ADR 0008 in mqucifer/project-print), so a producer learns it breaks a reader
before it merges, without knowing its readers:

1. `.github/qa/readers.py` reads every mqucifer repository's `.crew/project.yaml`
   at its default branch, through the GitHub API. A project whose
   `intent.scope.uses` names the caller's repository is a reader. A reader with
   no folder here, or a record that doesn't parse, is named in the summary.
2. Each reader with a folder runs as its own job, `<reader> reads <project>`:
   the reader's main is the checkout, and the pull request is what it reads,
   passed to its `start.sh` as `QA_PRODUCER` (the project's name) and
   `QA_PRODUCER_CHECKOUT`. A reader's `start.sh` builds with what it reads from
   that checkout. A failed test is an annotation naming the reader and the test.
3. The `qa` job passes only if every folder passed. It's the check a delivery
   repository requires, so its id stays `qa`.

A calling workflow passes only the project's name; `qa.yml` checks out the pull
request itself. A repository not made from project-template (the crew's) calls
`qa.yml` the same way, from a `.github/workflows/qa.yml` of its own.
`suite.yml` doesn't run readers: it builds a project's main, not a producer's
pull request.

Check a change to `readers.py` with `uv run pytest .github/qa`.

## How QA's own pull request is proven
A test here runs on every pull request of its project once it merges, so it's
proven first. `.github/workflows/suite.yml` runs each project folder a pull
request here changes through `qa.yml`, against that project's main and with the
pull request's tests. A red test comes back to QA before it can fail anyone
else's pull request. The repository's own checks (`checks.yml`, from its
record's design) lint and format the tests; only CI runs them, against a build.

## Where QA's tests come from
QA's Tasks, filed here by the crew, each changing only its project's folder
(mqucifer/crew#896):

- **A story merges** in a project with a folder here: the test of its criteria,
  through the folder's surface. After the merge, never before: a test of work
  not yet on the project's main would fail every other pull request there.
- **An escaped bug's fix merges:** the test that would have caught it.
- **A Developer disputes a test** its pull request fails: QA fixes the test, or
  says why it stands and the Developer changes the code. The story waits.

A QA session reads its project at `.project/<project>/` in its worktree, never
committed.

## A project's folder
| File | What it does |
|---|---|
| `README.md` | The surface the tests go through (API, page, CLI) and how the build is started |
| `start.sh <checkout>` | Builds and starts the pull request's build, waits until it answers, and writes `QA_BASE_URL`. For a reader, it also builds with what it reads from `QA_PRODUCER_CHECKOUT` |
| `stop.sh` | Prints the build's log and removes what `start.sh` started, even after a part-way start |
| `test_*.py` | The tests, through the surface only |

| Project | Surface |
|---|---|
| [`sprint-metrics/`](sprint-metrics/README.md) | Its HTTP service |
| [`crew-presentation/`](crew-presentation/README.md) | Its site's pages, built from the crew's `delivery-history` package |

## Who writes here
Only QA. `.github/CODEOWNERS` names QA's reviewer, the Sponsor (`@mquarters`)
for now. **At takeover it moves to the crew's account, which is the Sponsor's
step**, as is requiring code-owner review on main, since branch protection
needs admin.

## From the template

The files every crew-built project starts with (mqucifer/crew ADR 0030). A new
repository is created from this template by `scripts/new-project.sh` in the
crew's repository, and `crew onboard` proposes any of these files a repository
is missing, so older projects catch up when the template changes.

| File | What it does |
|---|---|
| `.github/workflows/checks.yml` | Runs the setup and checks the project's design names (`.crew/project.yaml`) on every pull request, in the design's image, as the crew's sandbox does. Once the project's skeleton makes it green, branch protection requires its `checks` job |
| `.github/crew/run_checks.py` | What `checks.yml` runs. Before the design is merged it has nothing to check and passes |
| `.github/crew/requirements.txt` | Its one dependency, PyYAML, locked with hashes by `uv pip compile --generate-hashes` |
| `.github/workflows/board.yml` | The crew's board automation: card moves no role performs, and an issue a person opens put on the board (a Goal in Inbox (Goals)) |
| `.github/ISSUE_TEMPLATE/goal-template.md` | The Sponsor's form for a new Goal. It arrives labelled `needs:human`, so the crew leaves it alone until the Sponsor swaps that for `goal` |
| `.gitignore` | OS files, caches, and the crew sandbox's own directories |

Nothing here depends on the project's language: that comes from its design. Stories
don't change these files; the template does, by pull request.

### The crew's since mqucifer/crew#896
This repository was a Claude-built alpha. The crew took it over with
mqucifer/crew#896: its board workflow's `issues` and `pull_request` triggers are
back, and its record, `.crew/project.yaml`, is a draft for the Sponsor to
correct and merge.
