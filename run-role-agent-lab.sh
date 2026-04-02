#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

export MULTI_AGENT_TEAM_APP_PROFILE="${MULTI_AGENT_TEAM_APP_PROFILE:-role_agent_lab}"
export MULTI_AGENT_TEAM_APP_MODULE="${MULTI_AGENT_TEAM_APP_MODULE:-app.role_agent_lab_main:app}"
export MULTI_AGENT_TEAM_APP_PORT="${MULTI_AGENT_TEAM_APP_PORT:-8081}"

exec ./run.sh
