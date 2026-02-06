#!/usr/bin/env bash
set -euo pipefail

normalize_bool() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|on|ON) echo "1" ;;
    *) echo "0" ;;
  esac
}

AUTOMATION_REPO_ROOT="${AUTOMATION_REPO_ROOT:-/opt/orbis-test-automation}"
AUTOMATION_FEATURES_ROOT="${AUTOMATION_FEATURES_ROOT:-/opt/orbis-test-automation/apps/lokasi_intelligence/cypress}"
ORBIS_AUTOMATION_REPO="${ORBIS_AUTOMATION_REPO:-https://github.com/bvarta-tech/orbis-test-automation.git}"
ORBIS_AUTOMATION_REF="${ORBIS_AUTOMATION_REF:-main}"
AUTOMATION_GIT_SYNC="$(normalize_bool "${AUTOMATION_GIT_SYNC:-0}")"
AUTOMATION_NPM_INSTALL="$(normalize_bool "${AUTOMATION_NPM_INSTALL:-1}")"
GIT_SSH_PRIVATE_KEY="${GIT_SSH_PRIVATE_KEY:-}"
GIT_SSH_PRIVATE_KEY_B64="${GIT_SSH_PRIVATE_KEY_B64:-}"

setup_git_ssh() {
  if [ -z "$GIT_SSH_PRIVATE_KEY" ] && [ -z "$GIT_SSH_PRIVATE_KEY_B64" ]; then
    return 0
  fi

  mkdir -p /root/.ssh
  chmod 700 /root/.ssh

  local key_file="/root/.ssh/id_ed25519"
  if [ -n "$GIT_SSH_PRIVATE_KEY_B64" ]; then
    echo "$GIT_SSH_PRIVATE_KEY_B64" | base64 -d > "$key_file"
  else
    printf "%s\n" "$GIT_SSH_PRIVATE_KEY" > "$key_file"
  fi

  chmod 600 "$key_file"
  ssh-keyscan github.com >> /root/.ssh/known_hosts 2>/dev/null || true
  export GIT_SSH_COMMAND="ssh -i $key_file -o StrictHostKeyChecking=yes"
}

if [ -z "${AUTOMATION_APP_PATH:-}" ]; then
  if [ -n "$AUTOMATION_FEATURES_ROOT" ]; then
    AUTOMATION_APP_PATH="$(dirname "$AUTOMATION_FEATURES_ROOT")"
  else
    AUTOMATION_APP_PATH="${AUTOMATION_REPO_ROOT}/apps/lokasi_intelligence"
  fi
fi

setup_git_ssh

if [ ! -d "$AUTOMATION_REPO_ROOT/.git" ]; then
  if [ -n "$ORBIS_AUTOMATION_REPO" ]; then
    echo "[startup] Cloning orbis-test-automation (${ORBIS_AUTOMATION_REF})..."
    git clone --depth=1 --branch "$ORBIS_AUTOMATION_REF" --single-branch "$ORBIS_AUTOMATION_REPO" "$AUTOMATION_REPO_ROOT" || true
  fi
elif [ "$AUTOMATION_GIT_SYNC" = "1" ]; then
  echo "[startup] Syncing orbis-test-automation (${ORBIS_AUTOMATION_REF})..."
  git -C "$AUTOMATION_REPO_ROOT" fetch --depth=1 origin "$ORBIS_AUTOMATION_REF" || true
  git -C "$AUTOMATION_REPO_ROOT" checkout -q "$ORBIS_AUTOMATION_REF" || git -C "$AUTOMATION_REPO_ROOT" checkout -q -b "$ORBIS_AUTOMATION_REF" FETCH_HEAD || true
  git -C "$AUTOMATION_REPO_ROOT" reset --hard FETCH_HEAD || true
fi

if [ "$AUTOMATION_NPM_INSTALL" = "1" ] && [ -d "$AUTOMATION_APP_PATH" ]; then
  if [ ! -d "$AUTOMATION_APP_PATH/node_modules" ]; then
    echo "[startup] Installing automation dependencies..."
    if [ -f "$AUTOMATION_APP_PATH/package-lock.json" ]; then
      (cd "$AUTOMATION_APP_PATH" && npm ci)
    else
      (cd "$AUTOMATION_APP_PATH" && npm install)
    fi
  fi
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}" --workers 1 --timeout-keep-alive 120
