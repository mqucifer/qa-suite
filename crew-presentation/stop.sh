#!/usr/bin/env bash
# Stop what start.sh started, printing build.py's log first so a failed test
# can be read against it. Safe to run when start.sh failed part-way.
set -uo pipefail

here=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=names.sh
. "$here/names.sh"

if [ -f "$STATE/build.log" ]; then
  echo "::group::build.py's log"
  cat "$STATE/build.log"
  echo "::endgroup::"
fi
[ -f "$STATE/server.pid" ] && kill "$(cat "$STATE/server.pid")" 2> /dev/null
rm -rf "$STATE"
exit 0
