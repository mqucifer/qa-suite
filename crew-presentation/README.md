# crew-presentation

QA's functional tests for `mqucifer/crew-presentation`, the crew's public site.

**The surface:** the site's pages, as its `build.py` writes them, served over
HTTP at `QA_BASE_URL`. The tests read the pages and the package the site was
built from (its input), never the site's code.

**What it reads:** the crew's `delivery-history` package (its record's `uses`).
So a crew pull request runs these tests too (ADR 0008 in mqucifer/project-print),
with the package that pull request's code builds.

**How the build is started:** `start.sh <checkout>` does what the site's own
checks do (its `.crew/project.yaml`): it puts the package under `.package/<tag>`
and runs `python build.py` from the checkout's `uv.lock`. Then it serves `build/`.
The package is:
- on a crew pull request (`QA_PRODUCER=crew`), that pull request's
  `contracts/delivery-history/mock/` and the schemas beside it. crew's own tests
  keep the mock current with the code that builds a real package;
- otherwise, the release `delivery-history.tag` names, as the site's setup
  fetches it.

The site also reads mqucifer/design-system, but from jsDelivr at the tag it
pins, not from a build. So a design-system pull request runs these tests on the
released package, and says so.

build.py refusing the package doesn't stop the start: that's the first test.
`stop.sh` prints build.py's log and stops the server.

| Test | What it proves |
|---|---|
| `test_reads_crew.py::test_the_site_accepts_the_package` | build.py accepts the package: its schema's major is one the site displays (mqucifer/crew#905's case), and it validates |
| `test_reads_crew.py::test_a_sprints_page_shows_its_throughput` | Each sprint's page shows sprint-metrics' `throughput` from the package as "stories delivered" |

## Running it locally
```sh
QA_PRODUCER=crew QA_PRODUCER_CHECKOUT=~/path/to/crew-worktree \
  crew-presentation/start.sh ~/path/to/crew-presentation   # prints the three variables
QA_BASE_URL=... QA_SITE_STATE=... QA_PACKAGE=... uv run pytest crew-presentation
crew-presentation/stop.sh
```
Leave out `QA_PRODUCER` to build from the release the site names.
