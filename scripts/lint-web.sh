#!/usr/bin/env bash
# Wrapper to run eslint from the web workspace.
# Used by lint-staged pre-commit hook.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ESLINT="$PROJECT_ROOT/apps/web/node_modules/.bin/eslint"

if [ ! -f "$ESLINT" ]; then
  echo "Error: eslint not found at $ESLINT"
  echo "Run: npm install  (from project root)"
  exit 1
fi

# Increase Node memory limit to prevent SIGKILL during type-aware linting
export NODE_OPTIONS="--max-old-space-size=2048"

exec "$ESLINT" --config "$PROJECT_ROOT/apps/web/eslint.config.mjs" "$@"
