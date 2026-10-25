#!/usr/bin/env bash
# Stop what start.sh started, printing the service's log first so a failed test
# can be read against it. Safe to run when start.sh failed part-way.
set -uo pipefail

here=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=names.sh
. "$here/names.sh"

if docker inspect "$APP" > /dev/null 2>&1; then
  echo "::group::the service's log"
  docker logs "$APP" 2>&1 | tail -200
  echo "::endgroup::"
fi
docker rm -f "$APP" "$DB" > /dev/null 2>&1
docker network rm "$NET" > /dev/null 2>&1
exit 0
