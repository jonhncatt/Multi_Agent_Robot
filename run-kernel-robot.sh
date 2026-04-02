#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

export MULTI_AGENT_TEAM_APP_PROFILE="${MULTI_AGENT_TEAM_APP_PROFILE:-kernel_robot}"
export MULTI_AGENT_TEAM_APP_MODULE="${MULTI_AGENT_TEAM_APP_MODULE:-app.kernel_robot_main:app}"
export MULTI_AGENT_TEAM_APP_PORT="${MULTI_AGENT_TEAM_APP_PORT:-8080}"

exec ./run.sh
