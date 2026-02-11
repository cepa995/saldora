#!/usr/bin/env bash
# Wrapper to run ruff from the project venv.
# Used by lint-staged pre-commit hook.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_RUFF="$PROJECT_ROOT/.venv/bin/ruff"

if [ ! -f "$VENV_RUFF" ]; then
  echo "Error: ruff not found at $VENV_RUFF"
  echo "Run: pip install ruff  (or: pip install -e 'apps/api[dev]')"
  exit 1
fi

COMMAND="$1"
shift

case "$COMMAND" in
  check)
    "$VENV_RUFF" check --fix "$@"
    ;;
  format)
    "$VENV_RUFF" format "$@"
    ;;
  *)
    "$VENV_RUFF" "$COMMAND" "$@"
    ;;
esac
