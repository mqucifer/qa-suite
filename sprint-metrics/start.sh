#!/usr/bin/env bash
# Start sprint-metrics' service from a pull request's checkout, as its own CI's
# docker job does (.github/workflows/tests.yml there): the image built from the
# checkout's Dockerfile, run with no arguments (its service) against Postgres 16,
# pinned by the same digest.
#
#   start.sh <checkout>
#
# Writes QA_BASE_URL to $GITHUB_ENV when run in Actions, and prints it.
set -euo pipefail

checkout=${1:?usage: start.sh <checkout>}
here=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=names.sh
. "$here/names.sh"

POSTGRES=postgres:16@sha256:9e2cf6287f25c3151f4c9421ccce2b17f3e60061c111a29165e0d2cdd9ff0a97

fail() {
  echo "::error::$1"
  for c in "$APP" "$DB"; do
    docker logs "$c" 2>&1 | tail -50 | sed "s/^/[$c] /" || true
  done
  exit 1
}

[ -f "$checkout/Dockerfile" ] || fail "no Dockerfile in $checkout: is this a sprint-metrics checkout?"

docker network create "$NET" > /dev/null
docker run -d --name "$DB" --network "$NET" \
  -e POSTGRES_USER=sprint_metrics -e POSTGRES_PASSWORD=sprint_metrics -e POSTGRES_DB=sprint_metrics \
  --tmpfs /var/lib/postgresql/data --tmpfs /var/run/postgresql \
  "$POSTGRES" > /dev/null

docker build -q -t "$IMAGE" "$checkout" > /dev/null || fail "the pull request's image didn't build"

deadline=$((SECONDS + 30))
until docker exec "$DB" pg_isready -U sprint_metrics -q 2>/dev/null; do
  [ $SECONDS -lt $deadline ] || fail "Postgres didn't accept connections within 30s"
  sleep 1
done

docker run -d --name "$APP" --network "$NET" -p "$PORT:8080" \
  -e SPRINT_METRICS_DB="postgresql://sprint_metrics:sprint_metrics@$DB:5432/sprint_metrics" \
  "$IMAGE" > /dev/null

url="http://localhost:$PORT"
deadline=$((SECONDS + 30))
until curl -sf "$url/health" > /dev/null 2>&1; do
  [ "$(docker inspect -f '{{.State.Running}}' "$APP")" = true ] || fail "the service exited at startup"
  [ $SECONDS -lt $deadline ] || fail "GET /health didn't answer 200 within 30s"
  sleep 1
done

echo "sprint-metrics is up at $url"
[ -n "${GITHUB_ENV:-}" ] && echo "QA_BASE_URL=$url" >> "$GITHUB_ENV"
echo "QA_BASE_URL=$url"
