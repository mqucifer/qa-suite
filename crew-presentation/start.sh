#!/usr/bin/env bash
# Build crew-presentation's site from a checkout, as its own checks do (its
# .crew/project.yaml: setup puts the package under .package/, then
# `python build.py`), and serve build/ over HTTP.
#
#   start.sh <checkout>
#
# The package is the one the site reads from the crew (its record's `uses`): the
# release the checkout's delivery-history.tag names, as the site's setup fetches it.
#
# build.py refusing the package isn't a start failure: it's what the tests are
# for. Its exit status and log go to $STATE for test_reads_crew.py, and the
# server serves whatever it built. Writes QA_BASE_URL and QA_SITE_STATE to
# $GITHUB_ENV when run in Actions, and prints them.
set -euo pipefail

checkout=${1:?usage: start.sh <checkout>}
here=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=names.sh
. "$here/names.sh"

fail() {
  echo "::error::$1"
  [ -f "$STATE/server.log" ] && sed "s/^/[server] /" "$STATE/server.log"
  exit 1
}

[ -f "$checkout/build.py" ] && [ -f "$checkout/delivery-history.tag" ] \
  || fail "no build.py or delivery-history.tag in $checkout: is this a crew-presentation checkout?"
command -v uv > /dev/null || fail "uv isn't installed"

rm -rf "$STATE"
mkdir -p "$STATE"
tag=$(tr -d '[:space:]' < "$checkout/delivery-history.tag")
package="$checkout/.package/$tag"
rm -rf "$package" "$checkout/build"
mkdir -p "$checkout/.package"

url="https://github.com/mqucifer/crew/releases/download/$tag/$tag.tar.gz"
curl -sfL "$url" | tar -xz -C "$checkout/.package" || fail "couldn't fetch $url"
[ -f "$package/manifest.json" ] || fail "$tag's archive has no $tag/manifest.json"
echo "The package: the release $tag, which delivery-history.tag names"

uv sync -q --project "$checkout" --frozen --no-dev || fail "the site's dependencies didn't install from its uv.lock"
set +e
(cd "$checkout" && uv run -q --frozen --no-dev python build.py) > "$STATE/build.log" 2>&1
echo $? > "$STATE/build.status"
set -e
echo "build.py exited $(cat "$STATE/build.status")"
mkdir -p "$checkout/build"

python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$checkout/build" \
  > "$STATE/server.log" 2>&1 &
echo $! > "$STATE/server.pid"

url="http://127.0.0.1:$PORT"
deadline=$((SECONDS + 15))
until curl -s -o /dev/null "$url/"; do
  kill -0 "$(cat "$STATE/server.pid")" 2> /dev/null || fail "the server exited at startup"
  [ $SECONDS -lt $deadline ] || fail "the server didn't answer within 15s"
  sleep 0.5
done

echo "crew-presentation's site is up at $url"
if [ -n "${GITHUB_ENV:-}" ]; then
  { echo "QA_BASE_URL=$url"; echo "QA_SITE_STATE=$STATE"; echo "QA_PACKAGE=$package"; } >> "$GITHUB_ENV"
fi
echo "QA_BASE_URL=$url"
echo "QA_SITE_STATE=$STATE"
echo "QA_PACKAGE=$package"
