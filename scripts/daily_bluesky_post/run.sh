#!/usr/bin/env bash
# Bluesky 自動投稿 launchd entry
# CLAUDE.md L0: arm64 venv を強制
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

VENV="$SCRIPT_DIR/.venv"
CONFIG_DIR="$HOME/.config/aoyama-cemetery"

if [[ ! -d "$VENV" ]]; then
  echo "🔧 arm64 venv を作成: $VENV"
  trap 'rm -rf "$VENV"' ERR
  arch -arm64 /usr/bin/python3 -m venv "$VENV"
  arch -arm64 "$VENV/bin/pip" install --upgrade pip
  arch -arm64 "$VENV/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
  trap - ERR
fi

ACTUAL_ARCH=$(arch -arm64 "$VENV/bin/python3" -c 'import platform; print(platform.machine())')
if [[ "$ACTUAL_ARCH" != "arm64" ]]; then
  echo "❌ venv が arm64 ではありません: $ACTUAL_ARCH" >&2
  echo "   rm -rf $VENV && $0" >&2
  exit 1
fi

if [[ -f "$CONFIG_DIR/bluesky.env" ]]; then
  set -a; source "$CONFIG_DIR/bluesky.env"; set +a
fi
if [[ -f "$CONFIG_DIR/discord.env" ]]; then
  set -a; source "$CONFIG_DIR/discord.env"; set +a
fi
if [[ -f "$CONFIG_DIR/x.env" ]]; then
  set -a; source "$CONFIG_DIR/x.env"; set +a
fi

# L0 知見: claude -p 子プロセスに API key を継承させない
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN

exec arch -arm64 \
  env PYTHONPATH="$PROJECT_ROOT/scripts" \
  "$VENV/bin/python" -m daily_bluesky_post.orchestrator "$@"
