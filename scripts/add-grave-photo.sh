#!/usr/bin/env bash
# 墓参り写真を偉人ページに追加する補助スクリプト
#
# 使い方:
#   ./scripts/add-grave-photo.sh <slug> <写真ファイル> [<写真ファイル> ...]
#
# 例:
#   ./scripts/add-grave-photo.sh okubo-toshimichi ~/Downloads/IMG_1234.jpg
#   ./scripts/add-grave-photo.sh okubo-toshimichi ~/Downloads/*.jpg
#
# 動作:
#   - slug の存在を src/content/people/<slug>.md で検証
#   - 撮影日(デフォルト今日)とキャプション(省略可)を対話的に入力
#   - 長辺 1600px / JPEG quality 85 にリサイズ
#   - HEIC は自動で JPEG に変換
#   - src/assets/grave-photos/<slug>/YYYY-MM-DD-<caption>.jpg に配置

set -euo pipefail

# プロジェクトルートに移動(スクリプトが workspace のどこから呼ばれても動くように)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# 引数チェック
if [[ $# -lt 2 ]]; then
  cat <<EOF
使い方: $0 <slug> <写真ファイル> [<写真ファイル> ...]

例:
  $0 okubo-toshimichi ~/Downloads/IMG_1234.jpg
  $0 okubo-toshimichi ~/Downloads/*.jpg

利用可能な slug 一覧:
EOF
  ls src/content/people/ | sed 's/\.md$//' | sed 's/^/  - /'
  exit 1
fi

SLUG="$1"
shift

# オプション引数(--date YYYY-MM-DD / --caption "...")を抽出
# Streamlit admin 等から非対話で呼び出すための拡張(両方与えられた時のみ非対話モード)
CLI_DATE=""
CLI_CAPTION=""
FILES=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --date)
      CLI_DATE="$2"
      shift 2
      ;;
    --caption)
      CLI_CAPTION="$2"
      shift 2
      ;;
    *)
      FILES+=("$1")
      shift
      ;;
  esac
done

# 非対話モード判定: --date と --caption 両方与えられた時のみ
NONINTERACTIVE=false
if [[ -n "$CLI_DATE" && -n "$CLI_CAPTION" ]]; then
  NONINTERACTIVE=true
  # 非対話モードは引数の日付バリデーションも厳格に
  if [[ ! "$CLI_DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    echo "❌ --date は YYYY-MM-DD 形式で指定してください: $CLI_DATE" >&2
    exit 1
  fi
fi

# slug 検証
PERSON_MD="src/content/people/${SLUG}.md"
if [[ ! -f "$PERSON_MD" ]]; then
  echo "❌ slug '${SLUG}' に対応する偉人が見つかりません" >&2
  echo "   ${PERSON_MD} が存在する必要があります" >&2
  CANDIDATES=$(ls src/content/people/ | sed 's/\.md$//' | grep -i "${SLUG:0:5}" || true)
  if [[ -n "$CANDIDATES" ]]; then
    echo "" >&2
    echo "   候補:" >&2
    echo "$CANDIDATES" | sed 's/^/     - /' >&2
  fi
  exit 1
fi

# 偉人名抽出(frontmatter の name フィールド、クォート除去)
# awk は locale 由来のマルチバイトエラーが出るので bash 文字列操作で
NAME_LINE=$(grep -m1 '^name:' "$PERSON_MD" || echo "name: ${SLUG}")
NAME="${NAME_LINE#name:}"
NAME="${NAME# }"
NAME="${NAME#\"}"; NAME="${NAME%\"}"
NAME="${NAME#\'}"; NAME="${NAME%\'}"

echo "📸 ${NAME} (${SLUG}) の墓参り写真を追加します"
echo "   投入ファイル数: ${#FILES[@]}"
echo ""

# 出力先準備
DEST_DIR="src/assets/grave-photos/${SLUG}"
mkdir -p "$DEST_DIR"

TODAY=$(date +%Y-%m-%d)
ADDED_FILES=()

for SRC in "${FILES[@]}"; do
  # ファイル存在チェック
  if [[ ! -f "$SRC" ]]; then
    echo "⚠️  ファイルが見つかりません、スキップ: $SRC" >&2
    continue
  fi

  echo "─── $(basename "$SRC") ───"

  # 撮影日入力
  if [[ "$NONINTERACTIVE" == "true" ]]; then
    DATE="$CLI_DATE"
    CAPTION="$CLI_CAPTION"
  else
    while true; do
      read -r -p "  撮影日 (YYYY-MM-DD, Enter で今日 ${TODAY}): " DATE
      DATE=${DATE:-$TODAY}
      if [[ "$DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
        break
      fi
      echo "  ⚠️  日付は YYYY-MM-DD 形式で入力してください(ゼロ埋め必要)"
    done
    read -r -p "  キャプション (省略可): " CAPTION
  fi

  # ファイル名構築(空白 → ハイフン、ファイル名禁止文字を除外)
  if [[ -n "$CAPTION" ]]; then
    SAFE_CAPTION=$(echo "$CAPTION" | tr ' ' '-' | tr -d '/\\:*?"<>|')
    FILENAME="${DATE}-${SAFE_CAPTION}.jpg"
  else
    FILENAME="${DATE}.jpg"
  fi
  DEST_PATH="${DEST_DIR}/${FILENAME}"

  # 上書き確認
  if [[ -e "$DEST_PATH" ]]; then
    if [[ "$NONINTERACTIVE" == "true" ]]; then
      # 非対話モードでは上書きしない(明示削除してから呼ぶこと)
      echo "  ⚠️  ${FILENAME} は既に存在します(非対話モードのため skip)" >&2
      continue
    fi
    read -r -p "  ⚠️  ${FILENAME} は既に存在します。上書きしますか? [y/N]: " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[yY]$ ]]; then
      echo "  → スキップ"
      continue
    fi
  fi

  # 元サイズ取得
  SRC_SIZE=$(du -h "$SRC" | cut -f1)
  SRC_DIM=$(sips -g pixelWidth -g pixelHeight "$SRC" 2>/dev/null | awk '/pixelWidth/ {w=$2} /pixelHeight/ {h=$2} END {print w"x"h}')

  # リサイズ + JPEG 変換(HEIC も sips が自動で扱う)
  echo "  → リサイズ + JPEG 変換 中..."
  sips -Z 1600 -s formatOptions 85 -s format jpeg "$SRC" --out "$DEST_PATH" >/dev/null

  DEST_SIZE=$(du -h "$DEST_PATH" | cut -f1)
  DEST_DIM=$(sips -g pixelWidth -g pixelHeight "$DEST_PATH" 2>/dev/null | awk '/pixelWidth/ {w=$2} /pixelHeight/ {h=$2} END {print w"x"h}')

  echo "  ✅ ${DEST_PATH}"
  echo "     ${SRC_DIM}, ${SRC_SIZE} → ${DEST_DIM}, ${DEST_SIZE}"
  echo ""

  ADDED_FILES+=("$DEST_PATH")
done

if [[ ${#ADDED_FILES[@]} -eq 0 ]]; then
  echo "❌ 追加された写真はありません" >&2
  exit 1
fi

echo "✅ ${#ADDED_FILES[@]} 枚を追加しました"
echo ""
echo "次の手順:"
echo "  1. ローカル確認"
echo "     npm run dev"
echo "     → http://localhost:4321/people/${SLUG} を開いてギャラリー目視確認"
echo ""
echo "  2. 公開"
echo "     git add ${DEST_DIR}/"
echo "     git commit -m \"feat: ${NAME}の墓参り写真を追加\""
echo "     git push"
echo "     → Cloudflare Pages が自動デプロイ"
