#!/usr/bin/env bash
# add-grave-photo.sh の非対話フラグ回帰テスト
# 対話モードと非対話モードの両方を検証する
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# テスト用一時画像: macOS デフォルト壁紙(HEIC)を 100x100 JPEG に縮小して作る
TMP_DIR=$(mktemp -d)
TEST_IMAGE="$TMP_DIR/test.jpg"

# Big Sur 以降の macOS で確実にある HEIC を sips で JPEG 化
SAMPLE_HEIC=""
for candidate in \
  /System/Library/CoreServices/DefaultDesktop.heic \
  /System/Library/Desktop\ Pictures/Big\ Sur.heic ; do
  if [[ -f "$candidate" ]]; then
    SAMPLE_HEIC="$candidate"
    break
  fi
done

if [[ -n "$SAMPLE_HEIC" ]]; then
  sips -s format jpeg -z 100 100 "$SAMPLE_HEIC" --out "$TEST_IMAGE" >/dev/null
else
  # フォールバック: 既存リポ内の写真を 1 枚拾って 100x100 にリサイズ
  EXISTING=$(find src/assets/grave-photos -name '*.jpg' | head -1)
  if [[ -z "$EXISTING" ]]; then
    echo "❌ テスト用画像が見つかりません(macOS HEIC も既存 jpg も無い)" >&2
    exit 1
  fi
  sips -s format jpeg -z 100 100 "$EXISTING" --out "$TEST_IMAGE" >/dev/null
fi

# 既存テスト用 slug を選ぶ
TEST_SLUG=$(ls src/content/people/ | head -1 | sed 's/\.md$//')
TEST_DIR="src/assets/grave-photos/${TEST_SLUG}"
# 既存写真と衝突しない日付を選ぶ
TEST_DATE="1999-12-31"

cleanup_test_artifacts() {
  rm -f "${TEST_DIR}/${TEST_DATE}-test-noninteractive.jpg"
  rm -f "${TEST_DIR}/${TEST_DATE}-test-interactive.jpg"
  [[ -d "$TEST_DIR" ]] && [[ -z "$(ls -A "$TEST_DIR" 2>/dev/null)" ]] && rmdir "$TEST_DIR" 2>/dev/null || true
  rm -rf "$TMP_DIR"
}
trap cleanup_test_artifacts EXIT

echo "=== Test 1: 非対話モード(--date と --caption 両方あり) ==="
./scripts/add-grave-photo.sh "$TEST_SLUG" "$TEST_IMAGE" \
  --date "$TEST_DATE" --caption "test-noninteractive"

EXPECTED="${TEST_DIR}/${TEST_DATE}-test-noninteractive.jpg"
if [[ ! -f "$EXPECTED" ]]; then
  echo "❌ 期待ファイルが作成されませんでした: $EXPECTED" >&2
  exit 1
fi
echo "✅ 非対話モード OK: $EXPECTED"

echo ""
echo "=== Test 2: 対話モード(後方互換、stdin から流し込み) ==="
./scripts/add-grave-photo.sh "$TEST_SLUG" "$TEST_IMAGE" <<EOF
$TEST_DATE
test-interactive
EOF

EXPECTED2="${TEST_DIR}/${TEST_DATE}-test-interactive.jpg"
if [[ ! -f "$EXPECTED2" ]]; then
  echo "❌ 期待ファイルが作成されませんでした: $EXPECTED2" >&2
  exit 1
fi
echo "✅ 対話モード OK: $EXPECTED2"

echo ""
echo "🎉 全テストパス"
