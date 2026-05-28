#!/usr/bin/env bash
# Streamlit admin の起動ラッパー
# CLAUDE.md L0 ルール: arm64 venv で起動を強制
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

VENV="$SCRIPT_DIR/.venv"

if [[ ! -d "$VENV" ]]; then
  echo "🔧 arm64 venv を作成します: $VENV"
  arch -arm64 /usr/bin/python3 -m venv "$VENV"
  arch -arm64 "$VENV/bin/pip" install --upgrade pip
  arch -arm64 "$VENV/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
fi

# arch 確認
ACTUAL_ARCH=$(arch -arm64 "$VENV/bin/python3" -c 'import platform; print(platform.machine())')
if [[ "$ACTUAL_ARCH" != "arm64" ]]; then
  echo "❌ venv が arm64 ではありません: $ACTUAL_ARCH" >&2
  echo "   .venv を削除して再生成してください: rm -rf $VENV && $0" >&2
  exit 1
fi

exec arch -arm64 "$VENV/bin/streamlit" run "$SCRIPT_DIR/Dashboard.py" \
  --server.address localhost \
  --server.port 8501 \
  --browser.gatherUsageStats false
