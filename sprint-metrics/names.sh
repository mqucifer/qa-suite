# shellcheck shell=bash disable=SC2034
# The names start.sh and stop.sh share.
NET=qa-sprint-metrics
DB=qa-sprint-metrics-db
APP=qa-sprint-metrics-app
IMAGE=qa-sprint-metrics:pr
PORT=${QA_PORT:-8080}
