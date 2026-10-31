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
| `test_failure_causes.py::test_failure_causes_2_0_class_shown_not_placeholder` | A 2.0.0 entry carrying a class shows the class as its label in the cause section, not the 'Cause not recorded' placeholder, with its count preserved (mqucifer/crew-presentation#216 AC1) |
| `test_failure_causes.py::test_failure_causes_1x_map_shows_one_row_per_entry_with_count` | A 1.x map of cause-code to count shows one row per entry with those counts, so a 1.x package builds unchanged (mqucifer/crew-presentation#216 AC2) |
| `test_failure_causes.py::test_failure_causes_empty_or_absent_shows_no_failures` | An empty or absent top_failure_causes shows 'No failures recorded' and no cause-rows; the build does not fail (mqucifer/crew-presentation#216 AC3) |
| `test_delivery_history_major_2.py::test_a_major_2_package_is_accepted` | build.py accepts a package on schema major 2: the check does not refuse it as an unsupported major (mqucifer/crew-presentation#215; vacuous while the package is on major 1) |
| `test_delivery_history_major_2.py::test_a_major_2_package_builds_the_expected_pages` | A well-formed major-2 package builds and writes one sprint-overview page per sprint, one story page per card, and the replay page (mqucifer/crew-presentation#215; vacuous while the package is on major 1) |
| `test_replay_board_cards.py::test_replay_board_cards_render_links_not_markdown` | No board card element on the replay page contains the literal markdown string '[repo#number](url)': the reference is rendered as a hyperlink, not raw syntax (mqucifer/crew-presentation#226 AC1) |
| `test_replay_board_cards.py::test_replay_board_cards_have_correct_hyperlink` | Each board card on the replay page contains an <a> element whose href equals the card's issue URL and whose visible text equals 'repo#number' (mqucifer/crew-presentation#226 AC2) |
| `test_sprint_nav_link.py::test_sprint_nav_link_on_replay_html` | replay.html's Sprint link in nav[aria-label='Views'] has a non-empty href whose value names a file that exists in the build directory (mqucifer/crew-presentation#229: the href was empty, so clicking it only reloaded the same page) |
| `test_sprint_nav_link.py::test_sprint_nav_link_on_story_pages` | Every story page under stories/ has a Sprint link in nav[aria-label='Views'] whose href, resolved relative to the story page's directory, names a file that exists in the build directory (mqucifer/crew-presentation#229) |
| `test_escalation_removed.py::test_sprint_overview_has_no_escalations_stat` | No sprint page's stats section has an 'escalations' stat: the site no longer reports sprint-metrics' escalation count or rate (mqucifer/crew-presentation#217 AC1) |
| `test_escalation_removed.py::test_changed_trend_shows_no_escalation_entry` | The 'What changed' card never shows an escalation entry, while other changed measures still are: the number of rendered entries equals the package's non-escalation changed entries (mqucifer/crew-presentation#217 AC1+AC2) |
| `test_escalation_removed.py::test_replay_page_carries_escalated_events` | The build does not fail and the replay page's JSON data still carries the crew's own escalated events (kind 'escalated'): only sprint-metrics' escalation_count / escalation_rate_percent are dropped (mqucifer/crew-presentation#217 AC3) |
| `test_replay_board.py::test_replay_board_has_nine_columns_in_order` | The Board section contains exactly nine .replay-col children in DOM order (Needs Refinement through Blocked), each with a .replay-col__header showing the column name (mqucifer/crew-presentation#224 AC2) |
| `test_replay_board.py::test_replay_board_css_prevents_overflow_at_phone_width` | site.css lays out .replay-board as a grid and a phone-width media query (max-width >= 375px) constrains it to a single column, preventing the 591px overflow the bug described (mqucifer/crew-presentation#224 AC1) |

## Running it locally
```sh
crew-presentation/start.sh ~/path/to/crew-presentation   # prints the three variables
QA_BASE_URL=... QA_SITE_STATE=... QA_PACKAGE=... uv run pytest crew-presentation
crew-presentation/stop.sh
```
