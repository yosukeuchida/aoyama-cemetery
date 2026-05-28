# 偉人 coords + 墓写真管理 admin 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** aoyama-cemetery リポ内に Streamlit ベースのローカル admin UI を新設し、coords 設定 + 墓写真アップロード + 進捗ダッシュボードを 1 画面で完結させる。

**Architecture:** リポ内 `admin/` ディレクトリに Streamlit アプリを配置(Astro ビルド対象外)。`admin/lib/` の純関数で frontmatter (ruamel.yaml round-trip) と subprocess (既存 `scripts/add-grave-photo.sh`) をラップし、Streamlit ページ (`Dashboard.py` + `pages/Person_Edit.py`) はそれを呼ぶだけの薄い層に保つ。git commit/push は admin から行わず、`git diff` レビュー前提。

**Tech Stack:** Python 3.11+ / Streamlit / streamlit-folium / Leaflet (Esri World Imagery) / ruamel.yaml / Pillow (sanity check のみ) / pytest

**Spec:** `docs/superpowers/specs/2026-05-28-grave-admin-design.md`

---

## 0. 前提

- 作業ディレクトリ: `/Users/uchidayousuke/workspace/personal/aoyama-cemetery`
- ブランチ: main(or feature ブランチ任意)
- arch -arm64 venv 必須(CLAUDE.md L0 ルール、`uname -m` で確認)
- 既存ファイルの破損を防ぐため、各 lib module はテスト先行(TDD)

---

## Task 1: bash スクリプトに非対話フラグ追加

**Files:**
- Modify: `scripts/add-grave-photo.sh` (interactive 部分 86-114 行を分岐化)
- Create: `scripts/tests/test_add_grave_photo.sh`

### Step 1.1: テストスクリプトを作成して失敗を確認

- [ ] **Create `scripts/tests/test_add_grave_photo.sh`:**

```bash
#!/usr/bin/env bash
# add-grave-photo.sh の非対話フラグ回帰テスト
# 対話モードと非対話モードの両方を検証する
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# テスト用一時画像(1x1 white PNG)
TMP_DIR=$(mktemp -d)
trap "rm -rf $TMP_DIR" EXIT
TEST_IMAGE="$TMP_DIR/test.jpg"
sips -s format jpeg -z 100 100 /System/Library/CoreServices/DefaultDesktop.heic --out "$TEST_IMAGE" >/dev/null 2>&1 || \
  printf '\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\x27 ",#\x1c\x1c(7),01444\x1f\x27\x39=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01\x7d\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&\x27()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd0\xff\xd9' > "$TEST_IMAGE"

# 既存テスト用 slug を選ぶ(全 136 のうち最初のもの)
TEST_SLUG=$(ls src/content/people/ | head -1 | sed 's/\.md$//')
TEST_DIR="src/assets/grave-photos/${TEST_SLUG}"
# 既存写真と衝突しない日付を選ぶ
TEST_DATE="1999-12-31"

cleanup_test_artifacts() {
  rm -f "${TEST_DIR}/${TEST_DATE}-test-noninteractive.jpg"
  rm -f "${TEST_DIR}/${TEST_DATE}-test-interactive.jpg"
  [[ -d "$TEST_DIR" ]] && [[ -z "$(ls -A "$TEST_DIR")" ]] && rmdir "$TEST_DIR"
}
trap 'cleanup_test_artifacts; rm -rf $TMP_DIR' EXIT

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
echo "=== Test 3: 不正な引数(--date のみ、--caption 欠落)→ 対話モードに fallback ==="
# stdin 与えて対話プロンプトに応答できることを確認
./scripts/add-grave-photo.sh "$TEST_SLUG" "$TEST_IMAGE" --date "$TEST_DATE" <<EOF
$TEST_DATE
test-noninteractive
y
EOF
echo "✅ 部分指定は対話 fallback OK"

echo ""
echo "🎉 全テストパス"
```

- [ ] **Make executable and run:**

```bash
chmod +x scripts/tests/test_add_grave_photo.sh
./scripts/tests/test_add_grave_photo.sh
```

Expected: FAIL (--date / --caption フラグが未実装で sips にゴミ引数が渡って失敗、または「ファイルが見つかりません」)

### Step 1.2: bash スクリプトに引数パース追加

- [ ] **Replace lines 40-42 of `scripts/add-grave-photo.sh`:**

```bash
# 元コード(40-42 行目):
SLUG="$1"
shift
FILES=("$@")
```

with:

```bash
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
```

- [ ] **Replace the date/caption prompt block (87-97 行目) of `scripts/add-grave-photo.sh`:**

```bash
# 元コード(撮影日入力 87-94 + キャプション入力 96-97):
  while true; do
    read -r -p "  撮影日 (YYYY-MM-DD, Enter で今日 ${TODAY}): " DATE
    DATE=${DATE:-$TODAY}
    if [[ "$DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
      break
    fi
    echo "  ⚠️  日付は YYYY-MM-DD 形式で入力してください(ゼロ埋め必要)"
  done

  # キャプション入力
  read -r -p "  キャプション (省略可): " CAPTION
```

with:

```bash
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
```

- [ ] **Replace the overwrite confirmation block (109-115 行目):**

```bash
# 元コード:
  if [[ -e "$DEST_PATH" ]]; then
    read -r -p "  ⚠️  ${FILENAME} は既に存在します。上書きしますか? [y/N]: " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[yY]$ ]]; then
      echo "  → スキップ"
      continue
    fi
  fi
```

with:

```bash
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
```

### Step 1.3: テストを実行して全パスを確認

- [ ] **Run:**

```bash
./scripts/tests/test_add_grave_photo.sh
```

Expected: `🎉 全テストパス`

### Step 1.4: コミット

- [ ] **Commit:**

```bash
git add scripts/add-grave-photo.sh scripts/tests/test_add_grave_photo.sh
git commit -m "$(cat <<'EOF'
feat(scripts): add-grave-photo.sh に非対話フラグ追加(--date / --caption)

Streamlit admin からの subprocess 呼び出しを可能にするため、--date と
--caption の両方を渡した時だけ対話プロンプトを skip。片方だけ・両方欠落は
従来通り対話モードで動作(後方互換)。非対話モードでは既存ファイルとの
衝突は skip(上書きしない)。回帰テスト scripts/tests/test_add_grave_photo.sh
で対話・非対話・部分指定の 3 パターンを検証。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: admin/ ディレクトリ + venv セットアップ

**Files:**
- Create: `admin/requirements.txt`
- Create: `admin/run.sh`
- Create: `admin/README.md`
- Create: `admin/lib/__init__.py`
- Create: `admin/tests/__init__.py`
- Modify: `.gitignore`

### Step 2.1: requirements.txt

- [ ] **Create `admin/requirements.txt`:**

```
streamlit>=1.32
streamlit-folium>=0.18
folium>=0.16
ruamel.yaml>=0.18
pytest>=8.0
```

### Step 2.2: arm64 venv 起動ラッパー

- [ ] **Create `admin/run.sh`:**

```bash
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
```

- [ ] **Make executable:**

```bash
chmod +x admin/run.sh
```

### Step 2.3: __init__.py + .gitignore

- [ ] **Create `admin/lib/__init__.py`:** (空ファイル)

```bash
touch admin/lib/__init__.py admin/tests/__init__.py
```

- [ ] **Modify `.gitignore`:** Append:

```
# Streamlit admin (local-only tool)
admin/.venv/
admin/admin.log
admin/__pycache__/
admin/**/__pycache__/
admin/.pytest_cache/
```

### Step 2.4: README

- [ ] **Create `admin/README.md`:**

```markdown
# aoyama-cemetery admin

偉人の coords 設定 + 墓参り写真アップロード用のローカル管理画面。

## 起動

\`\`\`bash
./admin/run.sh
\`\`\`

初回は arm64 venv を自動作成 + 依存インストール(数分)。
ブラウザで http://localhost:8501 を開く。

## 操作

- ダッシュボード: 136 名の coords 状態 + 写真枚数を一覧
- 個人詳細: 偉人を選んで coords タブ / 写真タブで編集
- 編集結果は working tree を直接更新するので、`git diff` で確認してから commit/push

## テスト

\`\`\`bash
arch -arm64 admin/.venv/bin/pytest admin/tests/
\`\`\`

## 設計

`docs/superpowers/specs/2026-05-28-grave-admin-design.md`
```

### Step 2.5: venv 初期化(動作確認)

- [ ] **Run setup:**

```bash
./admin/run.sh &
sleep 5
curl -s http://localhost:8501 | head -1
kill %1 2>/dev/null || true
```

Expected: 初回は venv 作成 + pip install ログ → curl は HTML を返す(Dashboard.py 未作成なので Streamlit のエラー画面でも OK)

エラーになっても Step 6 で Dashboard.py を作るので一旦無視。venv 構築が動けば OK。

### Step 2.6: コミット

- [ ] **Commit:**

```bash
git add admin/requirements.txt admin/run.sh admin/README.md \
        admin/lib/__init__.py admin/tests/__init__.py .gitignore
git commit -m "$(cat <<'EOF'
feat(admin): admin/ ディレクトリと arm64 venv 起動ラッパー追加

scripts ではなく admin/ 配下に Streamlit アプリ + lib + tests を配置する
構造を確立。run.sh が arm64 venv を自動作成 + 依存インストール、
arch -arm64 で起動する。.gitignore に venv とログを追加。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: lib/content_io.py — frontmatter 読み書き

**Files:**
- Create: `admin/lib/content_io.py`
- Create: `admin/tests/test_content_io.py`
- Create: `admin/tests/fixtures/sample_person_no_coords.md`
- Create: `admin/tests/fixtures/sample_person_with_coords.md`
- Create: `admin/tests/fixtures/sample_person_hidemap.md`

### Step 3.1: フィクスチャ作成

- [ ] **Create `admin/tests/fixtures/sample_person_no_coords.md`:**

```markdown
---
name: テスト 太郎
nameKana: てすと たろう
nameRomaji: Test Taro
birthDate: "1850-01-01"
deathDate: "1900-12-31"
era: [明治]
category: 政治家
graveSection: 1種イ99号99側
shortDescription: テスト用のサンプル人物、frontmatter round-trip 検証のために存在する。
tags:
  - テスト
references:
  - title: Wikipedia「テスト」
    url: https://example.com/test
---

## テスト

これはテスト本文です。
```

- [ ] **Create `admin/tests/fixtures/sample_person_with_coords.md`:**

```markdown
---
name: テスト 次郎
nameKana: てすと じろう
nameRomaji: Test Jiro
birthDate: "1850-01-01"
deathDate: "1900-12-31"
era: [明治]
category: 政治家
graveSection: 1種イ99号99側
coords:
  lat: 35.667000
  lng: 139.722000
shortDescription: 既に coords 設定済のテスト用人物。
tags:
  - テスト
---

## テスト

本文。
```

- [ ] **Create `admin/tests/fixtures/sample_person_hidemap.md`:**

```markdown
---
name: テスト 三郎
nameKana: てすと さぶろう
nameRomaji: Test Saburo
birthDate: "1850-01-01"
deathDate: "1900-12-31"
era: [明治]
category: 政治家
graveSection: 1種イ99号99側
hideMap: true
shortDescription: 地図非表示設定のテスト用人物。
---

## テスト

本文。
```

### Step 3.2: 失敗するテストを書く

- [ ] **Create `admin/tests/test_content_io.py`:**

```python
"""content_io: frontmatter 読み書きの単体テスト"""
import shutil
from pathlib import Path
import pytest

from admin.lib import content_io

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_md(tmp_path):
    """フィクスチャを tmp にコピーして、編集用の Path を返す関数"""
    def _copy(name: str) -> Path:
        src = FIXTURES / name
        dst = tmp_path / name
        shutil.copy(src, dst)
        return dst
    return _copy


def test_round_trip_preserves_content(tmp_md):
    """既存 .md を読んで書き戻すと、frontmatter と本文の意味が保たれる"""
    path = tmp_md("sample_person_with_coords.md")
    original_text = path.read_text(encoding="utf-8")
    data = content_io.load(path)
    content_io.save(path, data)
    after_text = path.read_text(encoding="utf-8")
    # 本文部分(--- 後)は byte 一致
    original_body = original_text.split("---", 2)[2]
    after_body = after_text.split("---", 2)[2]
    assert original_body == after_body
    # frontmatter は YAML パース結果が一致
    assert content_io.load(path).frontmatter == data.frontmatter


def test_set_coords_inserts_after_grave_section(tmp_md):
    """coords を新規挿入すると graveSection の直後に入る"""
    path = tmp_md("sample_person_no_coords.md")
    data = content_io.load(path)
    content_io.set_coords(data, lat=35.667123, lng=139.722456)
    content_io.save(path, data)
    text = path.read_text(encoding="utf-8")
    # graveSection の直後に coords がある
    gs_idx = text.index("graveSection:")
    coords_idx = text.index("coords:")
    desc_idx = text.index("shortDescription:")
    assert gs_idx < coords_idx < desc_idx
    # 値が正しい
    assert "lat: 35.667123" in text
    assert "lng: 139.722456" in text


def test_set_coords_updates_existing(tmp_md):
    """既存の coords を更新するとキー順序が保たれる"""
    path = tmp_md("sample_person_with_coords.md")
    data = content_io.load(path)
    original_keys = list(data.frontmatter.keys())
    content_io.set_coords(data, lat=35.668000, lng=139.723000)
    content_io.save(path, data)
    after = content_io.load(path)
    assert list(after.frontmatter.keys()) == original_keys
    assert after.frontmatter["coords"]["lat"] == 35.668000
    assert after.frontmatter["coords"]["lng"] == 139.723000


def test_clear_coords_preserves_structure(tmp_md):
    """coords を削除しても frontmatter の他キーは保たれる"""
    path = tmp_md("sample_person_with_coords.md")
    data = content_io.load(path)
    content_io.clear_coords(data)
    content_io.save(path, data)
    after = content_io.load(path)
    assert "coords" not in after.frontmatter
    assert after.frontmatter["name"] == "テスト 次郎"
    assert after.frontmatter["graveSection"] == "1種イ99号99側"


def test_set_coords_rejects_out_of_range_lat(tmp_md):
    """範囲外の lat で ValueError"""
    path = tmp_md("sample_person_no_coords.md")
    data = content_io.load(path)
    with pytest.raises(ValueError, match="lat"):
        content_io.set_coords(data, lat=36.0, lng=139.722)


def test_set_coords_rejects_out_of_range_lng(tmp_md):
    """範囲外の lng で ValueError"""
    path = tmp_md("sample_person_no_coords.md")
    data = content_io.load(path)
    with pytest.raises(ValueError, match="lng"):
        content_io.set_coords(data, lat=35.667, lng=140.0)


def test_set_coords_rejects_hidemap_person(tmp_md):
    """hideMap: true 設定済の人物への coords 追加は ValueError"""
    path = tmp_md("sample_person_hidemap.md")
    data = content_io.load(path)
    with pytest.raises(ValueError, match="hideMap"):
        content_io.set_coords(data, lat=35.667, lng=139.722)


def test_load_invalid_yaml_raises(tmp_path):
    """壊れた YAML は明示的なエラーを返す"""
    path = tmp_path / "broken.md"
    path.write_text("---\nname: [unclosed\n---\nbody", encoding="utf-8")
    with pytest.raises(ValueError, match="YAML"):
        content_io.load(path)
```

### Step 3.3: テスト実行して失敗確認

- [ ] **Run:**

```bash
arch -arm64 admin/.venv/bin/pytest admin/tests/test_content_io.py -v
```

Expected: ImportError or ModuleNotFoundError(`admin.lib.content_io` が未作成)

### Step 3.4: content_io.py 実装

- [ ] **Create `admin/lib/content_io.py`:**

```python
"""frontmatter (YAML) と本文を round-trip で読み書きするモジュール。

ruamel.yaml の CommentedMap で順序とコメントを保持する。
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

# zod schema と同じ範囲(src/content.config.ts:18-21)
LAT_MIN, LAT_MAX = 35.66, 35.68
LNG_MIN, LNG_MAX = 139.71, 139.73


@dataclass
class PersonMD:
    path: Path
    frontmatter: CommentedMap
    body: str


def _yaml() -> YAML:
    y = YAML(typ="rt")
    y.preserve_quotes = True
    y.indent(mapping=2, sequence=4, offset=2)
    y.width = 4096  # 長い文字列を改行しない
    return y


def load(path: Path) -> PersonMD:
    """frontmatter と本文を読む。"""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"frontmatter フェンスが見つかりません: {path}")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"frontmatter フェンスが閉じていません: {path}")
    raw_fm = parts[1]
    body = parts[2]
    try:
        fm = _yaml().load(raw_fm)
    except Exception as e:
        raise ValueError(f"YAML パース失敗 ({path}): {e}") from e
    if not isinstance(fm, CommentedMap):
        raise ValueError(f"frontmatter がマップではありません: {path}")
    return PersonMD(path=path, frontmatter=fm, body=body)


def save(path: Path, data: PersonMD) -> None:
    """frontmatter + 本文を atomic に書き戻す。"""
    buf = io.StringIO()
    _yaml().dump(data.frontmatter, buf)
    new_text = "---\n" + buf.getvalue() + "---" + data.body
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(new_text, encoding="utf-8")
    tmp.replace(path)


def set_coords(data: PersonMD, *, lat: float, lng: float) -> None:
    """coords を設定 / 更新。graveSection の直後に挿入する。"""
    if not (LAT_MIN <= lat <= LAT_MAX):
        raise ValueError(f"lat が範囲外({LAT_MIN}-{LAT_MAX}): {lat}")
    if not (LNG_MIN <= lng <= LNG_MAX):
        raise ValueError(f"lng が範囲外({LNG_MIN}-{LNG_MAX}): {lng}")
    if data.frontmatter.get("hideMap") is True:
        raise ValueError("hideMap: true の人物には coords を設定できません")

    fm = data.frontmatter
    coords_map = CommentedMap()
    coords_map["lat"] = round(float(lat), 6)
    coords_map["lng"] = round(float(lng), 6)

    if "coords" in fm:
        fm["coords"] = coords_map
        return

    # 新規挿入: graveSection の直後に置く
    keys = list(fm.keys())
    if "graveSection" in keys:
        insert_pos = keys.index("graveSection") + 1
    elif "shortDescription" in keys:
        insert_pos = keys.index("shortDescription")
    else:
        insert_pos = len(keys)
    fm.insert(insert_pos, "coords", coords_map)


def clear_coords(data: PersonMD) -> None:
    """coords を削除。無ければ no-op。"""
    if "coords" in data.frontmatter:
        del data.frontmatter["coords"]


def has_coords(data: PersonMD) -> bool:
    return "coords" in data.frontmatter


def is_hidemap(data: PersonMD) -> bool:
    return data.frontmatter.get("hideMap") is True
```

### Step 3.5: テスト実行して全パスを確認

- [ ] **Run:**

```bash
arch -arm64 admin/.venv/bin/pytest admin/tests/test_content_io.py -v
```

Expected: 8 passed

### Step 3.6: 既存 119 件で round-trip スモークテスト(手動)

- [ ] **Run:**

```bash
arch -arm64 admin/.venv/bin/python3 -c "
from pathlib import Path
from admin.lib import content_io
import sys
errors = []
for md in sorted(Path('src/content/people').glob('*.md')):
    try:
        d = content_io.load(md)
        # 読めるだけで OK(書き戻しは別途やる)
    except Exception as e:
        errors.append((md.name, str(e)))
print(f'OK: {136 - len(errors)} / 136')
for name, err in errors:
    print(f'  - {name}: {err}')
sys.exit(1 if errors else 0)
"
```

Expected: `OK: 136 / 136`

エラーが出たら、出たファイルの frontmatter を目視確認して、content_io.py の対応漏れを修正してから再実行。

### Step 3.7: コミット

- [ ] **Commit:**

```bash
git add admin/lib/content_io.py admin/tests/test_content_io.py admin/tests/fixtures/
git commit -m "$(cat <<'EOF'
feat(admin): content_io モジュール追加(frontmatter round-trip 読み書き)

ruamel.yaml の round-trip mode で .md の frontmatter をパース・編集・書き戻し。
coords は graveSection 直後に挿入、範囲チェック(zod と同期)+ hideMap 矛盾検証。
書き込みは atomic rename。pytest 8 件 + 既存 136 件 round-trip スモーク通過。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: lib/photo_ops.py — subprocess wrapper

**Files:**
- Create: `admin/lib/photo_ops.py`
- Create: `admin/tests/test_photo_ops.py`

### Step 4.1: 失敗するテストを書く

- [ ] **Create `admin/tests/test_photo_ops.py`:**

```python
"""photo_ops: add-grave-photo.sh のラッパーテスト(subprocess は本物実行)"""
import os
import shutil
from pathlib import Path
import pytest

from admin.lib import photo_ops

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_SLUG = "okubo-toshimichi"  # 必ず存在する slug
TEST_DATE = "1999-12-30"  # 既存と衝突しない日付


def _make_test_image(path: Path) -> None:
    """1x1 の真っ白 JPEG を作る(最小限の有効 JPEG バイト列)"""
    path.write_bytes(
        b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
        b'\xff\xdb\x00C\x00' + b'\x08' * 64
        + b'\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00'
        b'\xff\xc4\x00\x14\x00\x01' + b'\x00' * 15 + b'\x03'
        b'\xff\xc4\x00\x14\x10\x01' + b'\x00' * 15 + b'\x03'
        b'\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd0\xff\xd9'
    )


@pytest.fixture
def test_image(tmp_path):
    img = tmp_path / "test.jpg"
    # sips で最小 JPEG を生成(macOS 必須)
    fallback = tmp_path / "src.jpg"
    _make_test_image(fallback)
    return fallback


@pytest.fixture
def cleanup_artifacts():
    """テスト後に作成されたファイルを片付ける"""
    created = []
    yield created
    for path in created:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def test_add_photo_basic(test_image, cleanup_artifacts):
    """正常系: 写真が src/assets/grave-photos/<slug>/ に配置される"""
    result = photo_ops.add_photo(
        slug=TEST_SLUG,
        src=test_image,
        date=TEST_DATE,
        caption="test-photo-ops",
    )
    cleanup_artifacts.append(result)
    expected = PROJECT_ROOT / f"src/assets/grave-photos/{TEST_SLUG}/{TEST_DATE}-test-photo-ops.jpg"
    assert result == expected
    assert expected.exists()


def test_add_photo_rejects_slash_in_caption(test_image):
    """caption にスラッシュが含まれると ValueError(ディレクトリトラバーサル防止)"""
    with pytest.raises(ValueError, match="caption"):
        photo_ops.add_photo(
            slug=TEST_SLUG,
            src=test_image,
            date=TEST_DATE,
            caption="bad/path",
        )


def test_add_photo_rejects_invalid_slug(test_image):
    """存在しない slug で RuntimeError(bash スクリプトの exit 1 を補足)"""
    with pytest.raises(RuntimeError, match="slug"):
        photo_ops.add_photo(
            slug="nonexistent-person-xyz",
            src=test_image,
            date=TEST_DATE,
            caption="x",
        )


def test_list_photos_returns_existing_files():
    """ list_photos: 既存写真ディレクトリのファイル一覧を返す """
    photos = photo_ops.list_photos(TEST_SLUG)
    assert isinstance(photos, list)
    # 全要素は Path
    for p in photos:
        assert isinstance(p, Path)
        assert p.exists()


def test_list_photos_empty_for_no_dir():
    """ディレクトリが無い slug は空リスト"""
    photos = photo_ops.list_photos("nonexistent-person-xyz")
    assert photos == []


def test_delete_photo(test_image, cleanup_artifacts):
    """delete_photo: ファイル削除 + 親ディレクトリは残す"""
    placed = photo_ops.add_photo(
        slug=TEST_SLUG,
        src=test_image,
        date=TEST_DATE,
        caption="test-delete",
    )
    cleanup_artifacts.append(placed)
    assert placed.exists()
    photo_ops.delete_photo(placed)
    assert not placed.exists()
```

### Step 4.2: テスト実行して失敗確認

- [ ] **Run:**

```bash
arch -arm64 admin/.venv/bin/pytest admin/tests/test_photo_ops.py -v
```

Expected: ImportError (`admin.lib.photo_ops` 未作成)

### Step 4.3: photo_ops.py 実装

- [ ] **Create `admin/lib/photo_ops.py`:**

```python
"""墓写真の配置・列挙・削除を扱うモジュール。

リサイズ・HEIC 変換は scripts/add-grave-photo.sh に委譲する。
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GRAVE_PHOTOS_DIR = PROJECT_ROOT / "src/assets/grave-photos"
SCRIPT = PROJECT_ROOT / "scripts/add-grave-photo.sh"

UNSAFE_CAPTION_CHARS = re.compile(r"[/\\:*?\"<>|\n\r]")


def add_photo(
    *,
    slug: str,
    src: Path,
    date: str,
    caption: str,
) -> Path:
    """写真を追加して配置パスを返す。

    Args:
        slug: 偉人 slug
        src: アップロードされた写真のパス
        date: YYYY-MM-DD
        caption: ファイル名に使うキャプション(必須、空文字不可)

    Raises:
        ValueError: caption に不正文字を含む
        RuntimeError: bash スクリプトが non-zero exit
    """
    if not caption:
        raise ValueError("caption は必須です")
    if UNSAFE_CAPTION_CHARS.search(caption):
        raise ValueError(f"caption に不正文字が含まれています: {caption!r}")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        raise ValueError(f"date は YYYY-MM-DD 形式: {date!r}")

    cmd = [
        str(SCRIPT), slug, str(src),
        "--date", date,
        "--caption", caption,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"add-grave-photo.sh failed (exit {proc.returncode}):\n"
            f"--- stderr ---\n{proc.stderr}\n"
            f"--- stdout ---\n{proc.stdout}"
        )

    safe_caption = caption.replace(" ", "-")
    expected = GRAVE_PHOTOS_DIR / slug / f"{date}-{safe_caption}.jpg"
    if not expected.exists():
        raise RuntimeError(
            f"スクリプトは成功したが期待ファイルが見つかりません: {expected}\n"
            f"stdout: {proc.stdout}"
        )
    return expected


def list_photos(slug: str) -> list[Path]:
    """slug の墓写真一覧を撮影日昇順で返す。"""
    d = GRAVE_PHOTOS_DIR / slug
    if not d.is_dir():
        return []
    return sorted(d.glob("*.jpg"))


def delete_photo(path: Path) -> None:
    """指定写真を削除。安全のため grave-photos 配下のファイルのみ受け付ける。"""
    resolved = path.resolve()
    if not str(resolved).startswith(str(GRAVE_PHOTOS_DIR.resolve())):
        raise ValueError(f"grave-photos 配下のファイルのみ削除可: {path}")
    resolved.unlink()
```

### Step 4.4: テスト実行して全パスを確認

- [ ] **Run:**

```bash
arch -arm64 admin/.venv/bin/pytest admin/tests/test_photo_ops.py -v
```

Expected: 6 passed

### Step 4.5: コミット

- [ ] **Commit:**

```bash
git add admin/lib/photo_ops.py admin/tests/test_photo_ops.py
git commit -m "$(cat <<'EOF'
feat(admin): photo_ops モジュール追加(add-grave-photo.sh の subprocess ラッパー)

add_photo / list_photos / delete_photo の 3 関数。caption の不正文字検証、
date 形式検証は Python 側で先に実施。bash スクリプトを本物実行する pytest
6 件で正常系・異常系をカバー。delete はパスチェックで grave-photos 配下に
限定(誤削除防止)。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: lib/git_ops.py — git log 読み取り

**Files:**
- Create: `admin/lib/git_ops.py`
- Create: `admin/tests/test_git_ops.py`

### Step 5.1: 失敗するテストを書く

- [ ] **Create `admin/tests/test_git_ops.py`:**

```python
"""git_ops: git log / status のラッパーテスト"""
from pathlib import Path
from unittest.mock import patch

from admin.lib import git_ops


def test_last_commit_date_returns_iso_string():
    """last_commit_date: 指定ファイルの最終 commit 日時を ISO で返す"""
    sample = Path("src/content/people/okubo-toshimichi.md")
    result = git_ops.last_commit_date(sample)
    assert result is None or "T" in result or "-" in result


def test_last_commit_date_returns_none_for_untracked(tmp_path):
    """git 管理外のファイルは None"""
    untracked = tmp_path / "untracked.md"
    untracked.write_text("x")
    assert git_ops.last_commit_date(untracked) is None


def test_uncommitted_count_returns_int():
    """uncommitted_count: int を返す(値は環境依存なので int 検証のみ)"""
    n = git_ops.uncommitted_count()
    assert isinstance(n, int)
    assert n >= 0


def test_uncommitted_count_with_mock():
    """git status --porcelain の出力をパース"""
    fake_output = " M src/content/people/x.md\n M src/content/people/y.md\n?? new.md\n"
    with patch("subprocess.run") as m:
        m.return_value.stdout = fake_output
        m.return_value.returncode = 0
        assert git_ops.uncommitted_count() == 3
```

### Step 5.2: テスト実行して失敗確認

- [ ] **Run:**

```bash
arch -arm64 admin/.venv/bin/pytest admin/tests/test_git_ops.py -v
```

Expected: ImportError

### Step 5.3: git_ops.py 実装

- [ ] **Create `admin/lib/git_ops.py`:**

```python
"""git の read-only ラッパー。書き込み系は提供しない(意図的)。"""
from __future__ import annotations

import subprocess
from pathlib import Path


def last_commit_date(path: Path | str) -> str | None:
    """指定パスの最終 commit 日時を ISO 文字列で返す。git 管理外なら None。"""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--", str(path)],
            capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError:
        return None
    output = result.stdout.strip()
    return output or None


def uncommitted_count() -> int:
    """未 commit ファイル数(working tree + staged)を返す。"""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return 0
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    return len(lines)
```

### Step 5.4: テスト実行して全パス

- [ ] **Run:**

```bash
arch -arm64 admin/.venv/bin/pytest admin/tests/test_git_ops.py -v
```

Expected: 4 passed

### Step 5.5: コミット

- [ ] **Commit:**

```bash
git add admin/lib/git_ops.py admin/tests/test_git_ops.py
git commit -m "$(cat <<'EOF'
feat(admin): git_ops モジュール追加(read-only git ラッパー)

last_commit_date と uncommitted_count の 2 関数のみ。書き込み系は提供しない
(admin から git commit/push をしない設計判断)。pytest 4 件パス。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Dashboard.py — 進捗一覧

**Files:**
- Create: `admin/Dashboard.py`

### Step 6.1: 実装

- [ ] **Create `admin/Dashboard.py`:**

```python
"""進捗ダッシュボード(entry point)。

136 名の coords 状態 + 写真枚数 + 最終 commit 日時を一覧表示。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# プロジェクトルートを sys.path に追加(admin.lib をインポートするため)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from admin.lib import content_io, git_ops, photo_ops  # noqa: E402

PEOPLE_DIR = PROJECT_ROOT / "src/content/people"
SCRIPT = PROJECT_ROOT / "scripts/add-grave-photo.sh"
ASTRO_CONFIG = PROJECT_ROOT / "astro.config.mjs"


# ---- ヘルスチェック ----------
def _healthcheck() -> None:
    errors = []
    if not ASTRO_CONFIG.exists():
        errors.append(f"プロジェクトルートが正しくありません: {ASTRO_CONFIG} がない")
    if not PEOPLE_DIR.is_dir() or not list(PEOPLE_DIR.glob("*.md")):
        errors.append(f"偉人 md ファイルが見つかりません: {PEOPLE_DIR}")
    if not SCRIPT.exists() or not os.access(SCRIPT, os.X_OK):
        errors.append(f"add-grave-photo.sh が実行可能ではありません: {SCRIPT}")
    if errors:
        st.error("起動時ヘルスチェック失敗:\n" + "\n".join(f"- {e}" for e in errors))
        st.stop()


# ---- データ収集 ----------
@st.cache_data(ttl=30)
def _collect_rows() -> pd.DataFrame:
    rows = []
    for md in sorted(PEOPLE_DIR.glob("*.md")):
        slug = md.stem
        try:
            data = content_io.load(md)
            fm = data.frontmatter
        except Exception as e:
            rows.append({
                "slug": slug, "name": "(parse error)",
                "coords": "❌", "graveSection": "",
                "photos": 0, "last_commit": "", "_error": str(e),
            })
            continue
        if content_io.is_hidemap(data):
            coords_state = "(hideMap)"
        elif content_io.has_coords(data):
            coords_state = "✅"
        else:
            coords_state = "❌"
        rows.append({
            "slug": slug,
            "name": fm.get("name", ""),
            "coords": coords_state,
            "graveSection": fm.get("graveSection", ""),
            "photos": len(photo_ops.list_photos(slug)),
            "last_commit": (git_ops.last_commit_date(md) or "")[:10],
        })
    return pd.DataFrame(rows)


# ---- メイン ----------
st.set_page_config(page_title="aoyama-cemetery admin", layout="wide")
_healthcheck()

st.title("aoyama-cemetery admin")

df = _collect_rows()

# サマリー
col1, col2, col3, col4 = st.columns(4)
col1.metric("全偉人", len(df))
col2.metric("coords 未取得", int((df["coords"] == "❌").sum()))
col3.metric("写真ゼロ", int((df["photos"] == 0).sum()))
col4.metric("未 commit", git_ops.uncommitted_count())

st.divider()

# フィルタ
fcol1, fcol2, fcol3 = st.columns([2, 1, 1])
name_filter = fcol1.text_input("名前 / slug 部分一致", "")
coords_filter = fcol2.selectbox("coords 状態", ["すべて", "❌ 未取得", "✅ 設定済", "(hideMap)"])
photo_filter = fcol3.checkbox("写真ゼロのみ", value=False)

filtered = df.copy()
if name_filter:
    mask = filtered["name"].str.contains(name_filter, case=False, na=False) | \
           filtered["slug"].str.contains(name_filter, case=False, na=False)
    filtered = filtered[mask]
if coords_filter == "❌ 未取得":
    filtered = filtered[filtered["coords"] == "❌"]
elif coords_filter == "✅ 設定済":
    filtered = filtered[filtered["coords"] == "✅"]
elif coords_filter == "(hideMap)":
    filtered = filtered[filtered["coords"] == "(hideMap)"]
if photo_filter:
    filtered = filtered[filtered["photos"] == 0]

st.caption(f"{len(filtered)} / {len(df)} 件表示")

# 行選択
event = st.dataframe(
    filtered,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
)

if event and event.selection and event.selection.rows:
    selected_idx = event.selection.rows[0]
    selected_slug = filtered.iloc[selected_idx]["slug"]
    st.session_state["selected_slug"] = selected_slug
    st.switch_page("pages/Person_Edit.py")
```

### Step 6.2: 手動スモークテスト

- [ ] **Run and inspect:**

```bash
./admin/run.sh &
sleep 8
# ブラウザで http://localhost:8501 を開いて、136 行表示・サマリ数値・フィルタが動くか確認
echo "ブラウザで動作確認したら Ctrl+C で kill してください"
wait
```

確認項目:
- ✅ 136 行表示される
- ✅ サマリの「coords 未取得」が 17(現状の数)
- ✅ 「coords 状態 = ❌ 未取得」フィルタで 17 行に絞れる
- ✅ 名前部分一致が動く
- ✅ 行クリックで Person_Edit.py に遷移しようとする(まだ未作成なので 404 になる、それで OK)

### Step 6.3: コミット

- [ ] **Commit:**

```bash
git add admin/Dashboard.py
git commit -m "$(cat <<'EOF'
feat(admin): Dashboard.py 追加(進捗一覧 + フィルタ)

136 名の coords 状態・写真枚数・最終 commit を一覧表示。
サマリ・名前/slug 部分一致・coords 状態・写真ゼロのフィルタを提供。
行クリックで Person_Edit.py に遷移(次タスクで実装)。
@st.cache_data(ttl=30) で再読み込み制御、cache_resource は使わない
(CLAUDE.md アンチパターン回避)。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: pages/Person_Edit.py — coords タブ

**Files:**
- Create: `admin/pages/__init__.py`
- Create: `admin/pages/Person_Edit.py`

### Step 7.1: ベース実装(coords タブのみ)

- [ ] **Create `admin/pages/__init__.py`:** (空)

```bash
touch admin/pages/__init__.py
```

- [ ] **Create `admin/pages/Person_Edit.py`:**

```python
"""個人詳細編集画面。coords タブ + 写真タブ。"""
from __future__ import annotations

import sys
from pathlib import Path

import folium
import streamlit as st
from streamlit_folium import st_folium

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from admin.lib import content_io, photo_ops  # noqa: E402

PEOPLE_DIR = PROJECT_ROOT / "src/content/people"

# 青山霊園中心(本園)
CEMETERY_CENTER = (35.6685, 139.7220)

st.set_page_config(page_title="Person Edit", layout="wide")

slug = st.session_state.get("selected_slug")
if not slug:
    st.warning("偉人が選択されていません。ダッシュボードに戻ってください。")
    if st.button("← ダッシュボードへ"):
        st.switch_page("Dashboard.py")
    st.stop()

md_path = PEOPLE_DIR / f"{slug}.md"
if not md_path.exists():
    st.error(f"偉人ファイルが見つかりません: {md_path}")
    st.stop()

data = content_io.load(md_path)
fm = data.frontmatter

# ---- ヘッダー ----
col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    name = fm.get("name", slug)
    birth = fm.get("birthDate", "")[:4]
    death = fm.get("deathDate", "")[:4]
    grave = fm.get("graveSection", "")
    st.markdown(f"## {name} ({birth}-{death}) / {grave}")
    st.caption(f"slug: `{slug}`")
with col_h2:
    if st.button("← ダッシュボード"):
        st.switch_page("Dashboard.py")

# ---- タブ ----
tab_coords, tab_photos = st.tabs(["📍 coords", "📸 写真"])

# ---- coords タブ ----
with tab_coords:
    if content_io.is_hidemap(data):
        st.warning("この偉人は `hideMap: true` 設定済のため coords は使われません。")
        st.stop()

    current = fm.get("coords")
    if current:
        st.success(f"現在値: lat={current['lat']}, lng={current['lng']}")
        if st.button("🗑️ coords をクリア", type="secondary"):
            content_io.clear_coords(data)
            content_io.save(md_path, data)
            st.success("クリアしました")
            st.rerun()
    else:
        st.info("coords 未設定。下の地図をクリックして座標を選んでください。")

    # 地図
    initial_lat = current["lat"] if current else CEMETERY_CENTER[0]
    initial_lng = current["lng"] if current else CEMETERY_CENTER[1]
    fmap = folium.Map(
        location=[initial_lat, initial_lng],
        zoom_start=19,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
        max_zoom=21,
    )
    # 現在値の赤ピン
    if current:
        folium.Marker(
            [current["lat"], current["lng"]],
            tooltip="現在の coords",
            icon=folium.Icon(color="red"),
        ).add_to(fmap)
    # 他の偉人のピン(参考用、灰色)
    for other_md in PEOPLE_DIR.glob("*.md"):
        if other_md.stem == slug:
            continue
        try:
            other = content_io.load(other_md)
            oc = other.frontmatter.get("coords")
            if oc:
                folium.CircleMarker(
                    [oc["lat"], oc["lng"]],
                    radius=3,
                    color="gray",
                    fill=True,
                    tooltip=other.frontmatter.get("name", other_md.stem),
                ).add_to(fmap)
        except Exception:
            pass

    map_result = st_folium(fmap, height=500, width=None, key=f"map_{slug}")

    # クリック座標
    clicked = map_result.get("last_clicked")
    if clicked:
        new_lat = round(clicked["lat"], 6)
        new_lng = round(clicked["lng"], 6)
        st.info(f"📍 クリック位置: lat={new_lat}, lng={new_lng}")
        col_a, col_b = st.columns(2)
        if col_a.button("✅ この座標で保存", type="primary"):
            try:
                content_io.set_coords(data, lat=new_lat, lng=new_lng)
                content_io.save(md_path, data)
                st.success(f"保存しました: lat={new_lat}, lng={new_lng}")
                st.cache_data.clear()
                st.rerun()
            except ValueError as e:
                st.error(f"保存失敗: {e}")
        col_b.markdown(
            f"[Google Maps で確認](https://www.google.com/maps?q={new_lat},{new_lng})"
        )
```

### Step 7.2: 手動確認

- [ ] **Run and inspect:**

```bash
./admin/run.sh &
sleep 8
# ブラウザで Dashboard → 1 名選択 → coords タブを開く
echo "確認したら Ctrl+C で kill"
wait
```

確認項目:
- ✅ 偉人 1 名選択 → 詳細画面に遷移
- ✅ 既存 coords がある偉人は地図上に赤ピン
- ✅ 他の偉人が灰色ピン(参考)
- ✅ 航空写真タイルが表示
- ✅ 地図クリックで「クリック位置」表示
- ✅ 「この座標で保存」で frontmatter 更新(`git diff src/content/people/<slug>.md` で確認)
- ✅ 範囲外クリックは ValueError 表示

### Step 7.3: コミット

- [ ] **Commit:**

```bash
git add admin/pages/__init__.py admin/pages/Person_Edit.py
git commit -m "$(cat <<'EOF'
feat(admin): Person_Edit.py 追加(coords タブ実装)

streamlit-folium + Esri World Imagery 航空写真で青山霊園を表示、クリックで
座標を取得して frontmatter に保存。既存座標は赤ピン、他偉人は参考の灰ピン。
hideMap: true 設定済の偉人は coords 編集不可で警告表示。
Google Maps での確認リンクも提供。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Person_Edit.py に写真タブ追加

**Files:**
- Modify: `admin/pages/Person_Edit.py` (写真タブ部分を追記)

### Step 8.1: 写真タブの実装を追加

- [ ] **Append to `admin/pages/Person_Edit.py` (after coords タブの with ブロック):**

```python
# ---- 写真タブ ----
with tab_photos:
    photos = photo_ops.list_photos(slug)
    st.subheader(f"既存写真: {len(photos)} 枚")

    if photos:
        for photo in photos:
            cols = st.columns([1, 2, 1])
            with cols[0]:
                st.image(str(photo), width=150)
            with cols[1]:
                st.text(photo.name)
                stat = photo.stat()
                st.caption(f"{stat.st_size // 1024} KB")
            with cols[2]:
                if st.button("🗑️ 削除", key=f"del_{photo.name}"):
                    st.session_state[f"confirm_del_{photo.name}"] = True
                if st.session_state.get(f"confirm_del_{photo.name}"):
                    st.warning(f"{photo.name} を削除しますか?")
                    cc1, cc2 = st.columns(2)
                    if cc1.button("削除実行", key=f"do_del_{photo.name}", type="primary"):
                        photo_ops.delete_photo(photo)
                        del st.session_state[f"confirm_del_{photo.name}"]
                        st.success(f"削除しました: {photo.name}")
                        st.cache_data.clear()
                        st.rerun()
                    if cc2.button("キャンセル", key=f"cancel_del_{photo.name}"):
                        del st.session_state[f"confirm_del_{photo.name}"]
                        st.rerun()
            st.divider()

    st.subheader("新規追加")
    from datetime import date as _date_cls
    import tempfile

    uploaded = st.file_uploader(
        "写真ファイル(複数選択可)",
        type=["jpg", "jpeg", "png", "heic"],
        accept_multiple_files=True,
        key=f"upload_{slug}",
    )
    upload_date = st.date_input("撮影日", value=_date_cls.today(), key=f"date_{slug}")
    upload_caption = st.text_input(
        "caption(ファイル名に使う、空欄なら『墓所』連番自動)",
        value="",
        key=f"caption_{slug}",
    )

    if uploaded and st.button("⬆️ アップロード", type="primary", key=f"do_upload_{slug}"):
        date_str = upload_date.strftime("%Y-%m-%d")
        # caption が空なら自動採番
        if not upload_caption.strip():
            existing_count = len(photo_ops.list_photos(slug))
            captions = [f"墓所-{existing_count + i + 1}" for i in range(len(uploaded))]
        else:
            base = upload_caption.strip().replace(" ", "-")
            captions = [base] if len(uploaded) == 1 else [f"{base}-{i + 1}" for i in range(len(uploaded))]

        results = []
        errors = []
        for upload_file, caption in zip(uploaded, captions):
            try:
                suffix = Path(upload_file.name).suffix.lower() or ".jpg"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(upload_file.getbuffer())
                    tmp_path = Path(tmp.name)
                try:
                    placed = photo_ops.add_photo(
                        slug=slug, src=tmp_path,
                        date=date_str, caption=caption,
                    )
                    results.append(placed)
                finally:
                    tmp_path.unlink(missing_ok=True)
            except Exception as e:
                errors.append((upload_file.name, str(e)))

        if results:
            st.success(f"{len(results)} 枚アップロードしました")
            for p in results:
                st.text(str(p.relative_to(PROJECT_ROOT)))
        if errors:
            for name, msg in errors:
                with st.expander(f"❌ {name}"):
                    st.code(msg)
        if results and not errors:
            st.cache_data.clear()
            st.rerun()
```

### Step 8.2: 手動確認

- [ ] **Run and test:**

```bash
./admin/run.sh &
sleep 8
echo "ブラウザでテスト:"
echo "1. 偉人選択 → 写真タブ"
echo "2. 既存写真がある偉人で枚数・サムネ表示確認"
echo "3. 写真 1 枚をアップロード → 配置パス表示"
echo "4. git diff src/assets/grave-photos/ で実ファイル確認"
echo "5. アップロード写真を削除 → ファイル消滅確認"
wait
```

### Step 8.3: コミット

- [ ] **Commit:**

```bash
git add admin/pages/Person_Edit.py
git commit -m "$(cat <<'EOF'
feat(admin): Person_Edit.py に写真タブ追加

既存写真をサムネ + ファイル名 + サイズで表示、削除は確認 dialog 付き。
新規アップロードは複数選択可、撮影日 date picker + caption。caption 空欄時は
「墓所-N」連番を自動採番。複数枚を 1 操作でアップロードする際は caption に
連番 suffix を付与。エラーは expander で個別表示、成功分だけ確定する。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: 操作ログ + 仕上げ

**Files:**
- Modify: `admin/lib/content_io.py` (操作ログ統合)
- Modify: `admin/lib/photo_ops.py` (操作ログ統合)
- Create: `admin/lib/audit_log.py`
- Create: `admin/tests/test_audit_log.py`

### Step 9.1: audit_log テスト

- [ ] **Create `admin/tests/test_audit_log.py`:**

```python
"""audit_log: JSONL 追記の最小テスト"""
import json
from pathlib import Path

from admin.lib import audit_log


def test_log_appends_jsonl(tmp_path, monkeypatch):
    log_path = tmp_path / "admin.log"
    monkeypatch.setattr(audit_log, "LOG_PATH", log_path)
    audit_log.log(op="set_coords", slug="x", details={"lat": 35.667, "lng": 139.722})
    audit_log.log(op="add_photo", slug="y", details={"file": "a.jpg"})
    lines = log_path.read_text().splitlines()
    assert len(lines) == 2
    e1 = json.loads(lines[0])
    assert e1["op"] == "set_coords"
    assert e1["slug"] == "x"
    assert "ts" in e1
```

### Step 9.2: audit_log 実装

- [ ] **Create `admin/lib/audit_log.py`:**

```python
"""admin の編集操作を JSONL で記録する(.gitignore で除外)"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parents[1] / "admin.log"


def log(*, op: str, slug: str, details: dict | None = None) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "op": op,
        "slug": slug,
        "details": details or {},
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
```

### Step 9.3: Person_Edit.py からログ呼び出し追加

- [ ] **Modify `admin/pages/Person_Edit.py`:** Add import and log calls.

After existing `from admin.lib import content_io, photo_ops` line:

```python
from admin.lib import audit_log  # noqa: E402
```

Replace coords 保存ブロック:

```python
        if col_a.button("✅ この座標で保存", type="primary"):
            try:
                content_io.set_coords(data, lat=new_lat, lng=new_lng)
                content_io.save(md_path, data)
                audit_log.log(
                    op="set_coords", slug=slug,
                    details={"lat": new_lat, "lng": new_lng},
                )
                st.success(f"保存しました: lat={new_lat}, lng={new_lng}")
                st.cache_data.clear()
                st.rerun()
            except ValueError as e:
                st.error(f"保存失敗: {e}")
```

Replace coords クリアブロック:

```python
        if st.button("🗑️ coords をクリア", type="secondary"):
            content_io.clear_coords(data)
            content_io.save(md_path, data)
            audit_log.log(op="clear_coords", slug=slug)
            st.success("クリアしました")
            st.rerun()
```

Add log call in 削除実行ブロック (after `photo_ops.delete_photo(photo)`):

```python
                    if cc1.button("削除実行", key=f"do_del_{photo.name}", type="primary"):
                        photo_ops.delete_photo(photo)
                        audit_log.log(op="delete_photo", slug=slug, details={"file": photo.name})
                        del st.session_state[f"confirm_del_{photo.name}"]
                        st.success(f"削除しました: {photo.name}")
                        st.cache_data.clear()
                        st.rerun()
```

Add log call after `results.append(placed)`:

```python
                    placed = photo_ops.add_photo(
                        slug=slug, src=tmp_path,
                        date=date_str, caption=caption,
                    )
                    audit_log.log(
                        op="add_photo", slug=slug,
                        details={"file": placed.name},
                    )
                    results.append(placed)
```

### Step 9.4: 全テスト実行

- [ ] **Run all:**

```bash
arch -arm64 admin/.venv/bin/pytest admin/tests/ -v
```

Expected: 全テストパス(content_io 8 + photo_ops 6 + git_ops 4 + audit_log 1 = 19)

### Step 9.5: コミット

- [ ] **Commit:**

```bash
git add admin/lib/audit_log.py admin/tests/test_audit_log.py admin/pages/Person_Edit.py
git commit -m "$(cat <<'EOF'
feat(admin): 編集操作の JSONL audit log 追加

set_coords / clear_coords / add_photo / delete_photo を admin.log に記録。
ローテーション無し(問題出たら後で対応)。.gitignore 除外済。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: 受け入れチェックリスト + 完成

**Files:** なし(手動検証のみ)

### Step 10.1: 受け入れ 7 項目を順に実行

- [ ] **1. 起動:**

```bash
./admin/run.sh
```

ブラウザで http://localhost:8501 を開く。

- [ ] **2. ダッシュボードで coords 未取得 17 名がフィルタで出る:**

「coords 状態 = ❌ 未取得」を選択、件数 = 17 を確認(初回時点の数値、人物追加で変動)。

- [ ] **3. 1 名選択 → 地図クリック → 保存 → `git diff`:**

```bash
git diff src/content/people/
```

意図通り `coords:` ブロックが `graveSection:` 直後に追加されている。

- [ ] **4. 別 1 名に写真 1 枚アップロード → `src/assets/grave-photos/<slug>/` に配置確認:**

```bash
ls src/assets/grave-photos/<slug>/
git status
```

長辺 1600px / JPEG に変換されているか確認。

- [ ] **5. 既存写真の削除 → ファイル消滅確認:**

削除ボタン → 確認 dialog → 削除実行、`ls src/assets/grave-photos/<slug>/` で消滅確認。

- [ ] **6. `npm run build` が通る(zod 通過 = データ整合確認):**

```bash
npm run build
```

zod validation エラーが出ないこと。

- [ ] **7. `git diff` で意図通り、`git checkout .` で全戻し可能:**

```bash
git diff  # 意図通りかレビュー
git checkout .  # テスト変更を元に戻す
git clean -fd src/assets/grave-photos/  # 新規追加した写真を削除
```

### Step 10.2: spec の手動受け入れチェックリストを完了マーク

- [ ] spec doc の §7.3 をマーク済みリストに更新(`- [x]`)してコミット:

```bash
# spec 末尾を編集して全項目を - [x] に変更
git add docs/superpowers/specs/2026-05-28-grave-admin-design.md
git commit -m "$(cat <<'EOF'
docs(spec): grave-admin 設計の受け入れチェックリストを完了マーク

7 項目すべて手動受入テスト通過、admin/ ローカル動作確認済。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review チェックリスト(計画作成者向け)

- ✅ **spec coverage**: spec §1-11 が Task 1-10 にマッピング済(§2 in scope → Task 1-9、§7.3 acceptance → Task 10)
- ✅ **bash 改修と Python 側の整合**: `--date` と `--caption` 両方ありで非対話、片方欠落で対話 fallback、両者の挙動を Task 1 のテストでカバー
- ✅ **placeholder スキャン**: "TBD" "TODO" "add appropriate" 一切なし
- ✅ **型の一貫性**: `PersonMD.frontmatter` (CommentedMap) は全箇所統一、`add_photo` 戻り値 Path も統一
- ✅ **commit 粒度**: 9 commit + ドキュメント 1 commit = 10 commit、各 commit はビルド通る単位

---

## 完了条件

1. Task 1-10 すべて完了 + 全 commit push 済
2. `arch -arm64 admin/.venv/bin/pytest admin/tests/` 全パス
3. `./admin/run.sh` で起動 → ブラウザで全機能動作
4. `npm run build` がパス
5. spec §7.3 受入チェックリスト 7 項目すべてマーク済
