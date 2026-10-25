# sprint-metrics

QA's functional tests for `mqucifer/sprint-metrics`.

**The surface:** its HTTP service, as its `docs/service.md` describes it (POST
/sprints, POST /events, GET /range and the rest). The tests reach it at
`QA_BASE_URL` and nothing else: no imports of its code, no database reads.

**How the build is started:** `start.sh <checkout>` does what sprint-metrics'
own CI docker job does (`.github/workflows/tests.yml` there). It builds the
image from the pull request's Dockerfile, starts Postgres 16 by the same
digest, runs the image with no arguments (its service, since
mqucifer/sprint-metrics#788 retired the CLI), and waits for GET /health.
`stop.sh` prints the service's log and removes it all. When sprint-metrics
changes how its CI starts the image, `start.sh` follows.

| Test | What it proves |
|---|---|
| `test_api.py` | A card started and finished in a sprint is counted there by GET /range: throughput 1, cycle time 2 days |

## Running it locally
```sh
QA_PORT=18080 sprint-metrics/start.sh ~/path/to/sprint-metrics   # prints QA_BASE_URL
QA_BASE_URL=http://localhost:18080 uv run pytest sprint-metrics
sprint-metrics/stop.sh
```
