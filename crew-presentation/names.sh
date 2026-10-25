# shellcheck shell=bash disable=SC2034
# The names start.sh and stop.sh share.
STATE=${RUNNER_TEMP:-${TMPDIR:-/tmp}}/qa-crew-presentation
PORT=${QA_PORT:-8081}
