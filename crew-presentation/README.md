# crew-presentation

QA's functional tests for `mqucifer/crew-presentation`, the crew's public site.

**The surface:** the site's pages, as its `build.py` writes them, served over
HTTP at `QA_BASE_URL`, and as Chromium renders them there. The tests read the
pages and the package the site was built from (its input), never the site's code.
A test of rendering or layout, whatever a criterion measures in a browser such as
`scrollWidth` at 375px, drives Chromium through the `rendered` fixture in
`conftest.py`, which needs nothing added, and measures the pages built from the
real package; anything the HTML or the package already says is plain HTTP. Your
sandbox has no running build and no browser, so only CI runs these tests: see
"Writing a browser test" in `crew-presentation/README.md`.

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

**The browser:** `start.sh` also installs Playwright (`playwright==1.52.0`, the
version crew-presentation's own tests use, from the root `uv.lock`'s `browser`
group) and Chromium's headless shell, so only this folder's runs pay for them.

## Writing a browser test
Use the browser when the bug or the criterion is in what the reader sees: layout,
overflow, anything computed from the CSS. A check of the CSS's text doesn't prove
the page fits, and a check of the HTML passes with or without a CSS bug. Use plain
HTTP when the page's HTML or the package already says it: it's faster and needs
no browser.

```python
def test_the_page_fits_a_phone(rendered):
    page = rendered("/replay.html", width=375, height=812)
    assert page.evaluate("document.documentElement.scrollWidth") <= 375
```

A `scrollWidth` test measures the pages `start.sh` built from the real package,
never a page built from a made-up one. The real package's long titles were what
overflowed: mqucifer/crew-presentation#224's fix passed the site's own test, built
from a fixture package, while the real `replay.html` was still 559px wide at 375px.

`rendered` gives you a loaded Playwright
[Page](https://playwright.dev/python/docs/api/class-page) at the viewport you
choose, and fails if the site doesn't serve the page or a stylesheet doesn't load.

A QA session's sandbox has no running build and no browser, and its checks only
lint and format, so a browser test can't be run there. Write it from what the site
does: `.project/crew-presentation/` has the templates and CSS to find your
selectors in, and its `tests/test_browser.py` shows what the site's own Playwright
tests measure. Then open the pull request: `suite.yml` runs the test against the
site's main, and a red one comes back with its log.

## Test files

| File | Topic |
|---|---|
| `test_browser.py` | View nav links resolve to real files, and the replay page fits a phone with real card titles (mqucifer/crew-presentation#230, #246) |
| `test_cycle_time_stat.py` | The cycle-time stat renders a missing value as an em dash (mqucifer/crew-presentation#233) |
| `test_delivery_history_major_2.py` | The site accepts and builds a package on schema major 2 (mqucifer/crew-presentation#215) |
| `test_escalation_removed.py` | The site no longer shows sprint-metrics' escalation count or rate (mqucifer/crew-presentation#217) |
| `test_failure_causes.py` | The failure-causes section reads top_failure_causes correctly (mqucifer/crew-presentation#216) |
| `test_reads_crew.py` | The site accepts the package, and a sprint's page shows sprint-metrics' answers |
| `test_replay_board.py` | The replay board's structure and phone-width layout (mqucifer/crew-presentation#224) |
| `test_replay_board_cards.py` | Board cards render their references as hyperlinks, not raw markdown (mqucifer/crew-presentation#226) |
| `test_sprint_nav_link.py` | The Sprint nav link on non-sprint pages points to a real sprint page (mqucifer/crew-presentation#229) |
| `test_sprint_overview.py` | A sprint's story list holds only that sprint's stories |
| `test_story_journey.py` | The story-journey root page fits a phone (mqucifer/crew-presentation#227) |
| `test_story_journey_details.py` | The story journey page shows its event timeline (mqucifer/crew-presentation#231) |

## Running it locally
```sh
crew-presentation/start.sh ~/path/to/crew-presentation   # prints the three variables
QA_BASE_URL=... QA_SITE_STATE=... QA_PACKAGE=... uv run pytest crew-presentation
crew-presentation/stop.sh
```

`start.sh` installs Playwright into qa-suite's `.venv` and Chromium into
Playwright's cache. Off Linux CI, install Chromium's system libraries yourself.
