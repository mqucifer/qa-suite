# crew-presentation

QA's functional tests for `mqucifer/crew-presentation`, the crew's public site.

**The surface:** the site's pages, as its `build.py` writes them, served over
HTTP at `QA_BASE_URL`. The tests read the pages and the package the site was
built from (its input), never the site's code.

**What it reads:** the crew's `delivery-history` package (its record's `uses`),
at the release its `delivery-history.tag` names. These tests run on
crew-presentation's own pull requests, never on the crew's (ADR 0008 in
mqucifer/project-print).

**How the build is started:** `start.sh <checkout>` does what the site's own
checks do (its `.crew/project.yaml`): it puts the package under `.package/<tag>`
and runs `python build.py` from the checkout's `uv.lock`. Then it serves `build/`.
The package is the release `delivery-history.tag` names, as the site's setup
fetches it.

build.py refusing the package doesn't stop the start: that's the first test.
`stop.sh` prints build.py's log and stops the server.

| Test | What it proves |
|---|---|
| `test_reads_crew.py::test_the_site_accepts_the_package` | build.py accepts the package: its schema's major is one the site displays (mqucifer/crew#905's case), and it validates |
| `test_reads_crew.py::test_a_sprints_page_shows_its_throughput` | Each sprint's page shows sprint-metrics' `throughput` from the package as "stories delivered" |
| `test_sprint_overview.py::test_retried_story_shows_retried_not_first_try` | A story whose pattern is not 'first_try' (e.g. 'retried') shows its own pattern as its status badge, not 'first try' (mqucifer/crew-presentation#206: the old code assigned 'first try' by position to match the total) |
| `test_sprint_overview.py::test_attempt_row_count_matches_package_stories` | The attempt chart shows one row per story the package records for that sprint; no rows are cut to match sprint-metrics' denominator (mqucifer/crew-presentation#206) |
| `test_sprint_overview.py::test_first_try_story_shows_first_try_regardless_of_position` | A story whose pattern is 'first_try' shows 'first try' as its badge regardless of its position in the list (mqucifer/crew-presentation#206: the old code would label it 'merged' if its position exceeded the numerator) |

## Running it locally
```sh
crew-presentation/start.sh ~/path/to/crew-presentation   # prints the three variables
QA_BASE_URL=... QA_SITE_STATE=... QA_PACKAGE=... uv run pytest crew-presentation
crew-presentation/stop.sh
```
