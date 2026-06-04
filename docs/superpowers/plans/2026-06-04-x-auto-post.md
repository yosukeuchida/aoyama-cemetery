# X 自動投稿展開 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bluesky bot 既存稼働を壊さず、毎朝 8:05 JST の同じマッチ素材を X(旧 Twitter)にも独立配信する pipeline を追加する。

**Architecture:** 既存 `scripts/daily_bluesky_post/` の orchestrator / claude_runner / config を multi-platform 化し、X 用 subagent 2 本 + `x_client.py` + `image_resolver.py` を増分追加。posted log は platform ごとに別ファイル(`posted_bluesky.jsonl` / `posted_x.jsonl`)、`X_ENABLED` env フラグで段階リリース。Bluesky tone と既存テスト 56 件は完全保全。

**Tech Stack:** Python 3.9 / tweepy(X API v2 + v1.1 media)/ twitter-text-python(weighted length 計測、フォールバック自前実装可)/ Pillow(画像リサイズ)/ pytest / `claude -p` headless + Max plan / launchd

---

## 参照

- Spec: `docs/superpowers/specs/2026-06-03-x-auto-post-design.md`
- 既存 Bluesky 実装: `scripts/daily_bluesky_post/`
- 既存 subagent: `.claude/agents/aoyama-post-writer.md` / `aoyama-fact-checker.md`

## ファイル構成(新規 / 改造一覧)

| ファイル | 状態 | 責務 |
|---|---|---|
| `scripts/daily_bluesky_post/config.py` | 改造 | X 認証情報 + `X_ENABLED` + `POSTED_BLUESKY_LOG` / `POSTED_X_LOG` 定数追加 |
| `scripts/daily_bluesky_post/x_client.py` | 新規 | tweepy OAuth 1.0a User Context で text + media 投稿 |
| `scripts/daily_bluesky_post/image_resolver.py` | 新規 | slug → portrait/heroImage の絶対 path 解決 + size チェック + リサイズ |
| `scripts/daily_bluesky_post/x_text.py` | 新規 | X weighted length カウント(twitter-text-python or 自前実装) |
| `scripts/daily_bluesky_post/claude_runner.py` | 改造 | `agent_name` 引数で post-writer-x ルートも走らせる |
| `scripts/daily_bluesky_post/orchestrator.py` | 改造 | platform loop + 部分失敗許容 + 字数ガード分岐 |
| `scripts/daily_bluesky_post/git_commit.py` | 改造 | 両 platform の posted log を統合 stage して 1 commit |
| `scripts/daily_bluesky_post/requirements.txt` | 改造 | `tweepy`、`Pillow`、`twitter-text-python` 追加 |
| `.claude/agents/aoyama-post-writer-x.md` | 新規 | X 用 short 版生成 |
| `.claude/agents/aoyama-fact-checker-x.md` | 新規 | X 用 critique(ハッシュタグ + 必須タグ検証含む) |
| `logs/posted.jsonl` → `logs/posted_bluesky.jsonl` | rename | git mv で履歴連続性確保 |
| `~/.config/aoyama-cemetery/x.env` | user 手動 | `X_API_KEY` 等 + `X_ENABLED` |
| `scripts/daily_bluesky_post/tests/test_*.py` | 新規 + 拡張 | 25 件追加(81 件目標) |

---

## Task 1: posted.jsonl を posted_bluesky.jsonl に rename + config 定数を分離

**Files:**
- Rename: `logs/posted.jsonl` → `logs/posted_bluesky.jsonl`(`git mv`)
- Modify: `scripts/daily_bluesky_post/config.py`(行 19: `POSTED_LOG = ...`)
- Modify: `scripts/daily_bluesky_post/orchestrator.py`(行 38, 134: `config.POSTED_LOG` 参照)
- Modify: `scripts/daily_bluesky_post/git_commit.py`(行 10, 14: `POSTED_LOG` import / 参照)
- Modify: `scripts/daily_bluesky_post/tests/test_config.py`
- Modify: `scripts/daily_bluesky_post/tests/test_git_commit.py`(`POSTED_LOG` を参照していれば)

- [ ] **Step 1: 既存テストを実行して baseline 確認**

Run: `PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/ -q`
Expected: 56 passed

- [ ] **Step 2: テストを先に追加 — config の新定数を期待**

Edit `scripts/daily_bluesky_post/tests/test_config.py`、末尾に追加:

```python
def test_posted_log_paths_split_per_platform():
    from daily_bluesky_post import config
    assert config.POSTED_BLUESKY_LOG.name == "posted_bluesky.jsonl"
    assert config.POSTED_X_LOG.name == "posted_x.jsonl"
    assert config.POSTED_BLUESKY_LOG.parent == config.POSTED_X_LOG.parent


def test_legacy_posted_log_alias_removed():
    # 後方互換 alias を残さない(明示的に platform を選ばせる)
    from daily_bluesky_post import config
    assert not hasattr(config, "POSTED_LOG")
```

- [ ] **Step 3: 新しいテストを fail 確認**

Run: `PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_config.py -q`
Expected: 2 failed (AttributeError / 旧 POSTED_LOG が残っている)

- [ ] **Step 4: config.py を改造**

Edit `scripts/daily_bluesky_post/config.py`、行 19 を置換:

```python
# 旧
POSTED_LOG = PROJECT_ROOT / "logs" / "posted.jsonl"

# 新
POSTED_BLUESKY_LOG = PROJECT_ROOT / "logs" / "posted_bluesky.jsonl"
POSTED_X_LOG = PROJECT_ROOT / "logs" / "posted_x.jsonl"
```

- [ ] **Step 5: 既存参照を一括置換**

orchestrator.py 行 38: `entries = post_log.load(config.POSTED_BLUESKY_LOG)`
orchestrator.py 行 134: `post_log.append(config.POSTED_BLUESKY_LOG, entry)`
git_commit.py 行 10: `from daily_bluesky_post.config import POSTED_BLUESKY_LOG, PROJECT_ROOT`
git_commit.py 行 14: `rel = POSTED_BLUESKY_LOG.relative_to(PROJECT_ROOT)`

(注: orchestrator は Task 6 で multi-platform 化するため、本 task では Bluesky 側だけ rename。)

- [ ] **Step 6: 既存テスト内の参照も置換**

`scripts/daily_bluesky_post/tests/` 全体で `POSTED_LOG` を grep して書き換え:

```bash
grep -rn "POSTED_LOG" scripts/daily_bluesky_post/tests/
```

該当箇所を `POSTED_BLUESKY_LOG` に置換(test_git_commit.py / test_orchestrator.py 等)。

- [ ] **Step 7: 物理ファイル rename**

```bash
cd /Users/uchidayousuke/workspace/personal/aoyama-cemetery
git mv logs/posted.jsonl logs/posted_bluesky.jsonl
```

- [ ] **Step 8: 全テスト pass 確認**

Run: `PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/ -q`
Expected: 58 passed(既存 56 + 新規 2)

- [ ] **Step 9: Commit**

```bash
git add -A scripts/daily_bluesky_post/ logs/
git commit -m "refactor(bluesky-post): posted.jsonl を posted_bluesky.jsonl に rename + config 定数分離

X 並走に備えて platform 別 log ファイルへ移行。
既存 Bluesky 運用への影響なし(挙動は同一、参照名のみ変更)。"
```

---

## Task 2: requirements.txt に X 投稿用ライブラリを追加

**Files:**
- Modify: `scripts/daily_bluesky_post/requirements.txt`

- [ ] **Step 1: 現状の requirements を確認**

```bash
cat scripts/daily_bluesky_post/requirements.txt
```

- [ ] **Step 2: tweepy + Pillow + twitter-text-python を追加**

追記:

```
tweepy>=4.14
Pillow>=10.0
twitter-text-python>=1.1
```

- [ ] **Step 3: venv に install**

```bash
arch -arm64 scripts/daily_bluesky_post/.venv/bin/pip install -r scripts/daily_bluesky_post/requirements.txt
```

- [ ] **Step 4: twitter-text-python の API を実物検証**

```bash
arch -arm64 scripts/daily_bluesky_post/.venv/bin/python -c "
from twitter_text import parse_tweet
r = parse_tweet('テスト投稿です。 https://example.com #青山霊園')
print(r.weightedLength, r.valid)
"
```

Expected: `weightedLength`(整数)+ `valid`(bool)が表示される。
失敗時(API 不一致 / メンテ停止)は Task 3 で **自前実装にフォールバック**(plan の Task 3 Step 1 で分岐判断)。

- [ ] **Step 5: 既存テスト regression なし確認**

Run: `PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/ -q`
Expected: 58 passed

- [ ] **Step 6: Commit**

```bash
git add scripts/daily_bluesky_post/requirements.txt
git commit -m "chore(bluesky-post): X 投稿用に tweepy / Pillow / twitter-text-python を追加"
```

---

## Task 3: X weighted length カウンタ(`x_text.py`)

**Files:**
- Create: `scripts/daily_bluesky_post/x_text.py`
- Create: `scripts/daily_bluesky_post/tests/test_x_text.py`

twitter-text-python の API が Step 4(Task 2)で動いた場合はラッパー、動かなかった場合は自前実装。本 plan は **ラッパー実装 + 自前 fallback の 2 段** を最終形とする。

- [ ] **Step 1: テスト先行**

Create `scripts/daily_bluesky_post/tests/test_x_text.py`:

```python
from daily_bluesky_post.x_text import x_weighted_length, X_LIMIT, X_SAFE_LIMIT


def test_ascii_only_one_per_char():
    assert x_weighted_length("hello world") == len("hello world")


def test_japanese_two_per_char():
    # 日本語 1 字 = 2 weighted units
    assert x_weighted_length("青山霊園") == 8


def test_url_counted_as_23_units():
    # URL は t.co 短縮で 23 units
    text = "see https://aoyama-cemetery.pages.dev/people/okubo-toshimichi end"
    # "see " (4) + URL(23) + " end" (4) = 31
    assert x_weighted_length(text) == 31


def test_japanese_with_url_and_hashtag():
    # 「青山霊園」(8) + " " (1) + URL(23) + " " (1) + "#明治維新"(10) = 43
    text = "青山霊園 https://aoyama-cemetery.pages.dev/people/x #明治維新"
    assert x_weighted_length(text) == 43


def test_limit_constants():
    assert X_LIMIT == 280
    assert X_SAFE_LIMIT == 270  # 安全マージン 10
```

- [ ] **Step 2: fail 確認**

Run: `PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_x_text.py -q`
Expected: ModuleNotFoundError

- [ ] **Step 3: 実装(twitter-text-python ラッパー + 自前 fallback)**

Create `scripts/daily_bluesky_post/x_text.py`:

```python
"""X(旧 Twitter)の weighted length カウンタ。

仕様(2026-06 時点):
- ASCII 範囲 + ラテン文字 = 1 unit / 字
- CJK / 全角 = 2 units / 字
- URL は t.co 短縮で 23 units 固定(http/https 問わず)
- 無料投稿の上限は 280 weighted units
"""
from __future__ import annotations

import re

X_LIMIT = 280
X_SAFE_LIMIT = 270  # 安全マージン 10
URL_WEIGHT = 23  # t.co 短縮後の固定長

_URL_RE = re.compile(r"https?://\S+")

try:
    from twitter_text import parse_tweet  # type: ignore

    _USE_LIBRARY = True
except ImportError:  # pragma: no cover
    _USE_LIBRARY = False


def _is_double_width(ch: str) -> bool:
    """CJK Unified Ideographs / Hiragana / Katakana / 全角記号など 2 units 扱い。"""
    code = ord(ch)
    return (
        0x1100 <= code <= 0x115F  # Hangul Jamo
        or 0x2E80 <= code <= 0x303E  # CJK Radicals / Kangxi / 句読点
        or 0x3041 <= code <= 0x33FF  # ひらがな / カタカナ / CJK 記号
        or 0x3400 <= code <= 0x4DBF  # CJK Ext A
        or 0x4E00 <= code <= 0x9FFF  # CJK Unified
        or 0xA000 <= code <= 0xA4CF  # Yi
        or 0xAC00 <= code <= 0xD7A3  # Hangul Syllables
        or 0xF900 <= code <= 0xFAFF  # CJK Compat
        or 0xFE30 <= code <= 0xFE4F  # CJK Compat Forms
        or 0xFF00 <= code <= 0xFF60  # 全角 ASCII
        or 0xFFE0 <= code <= 0xFFE6  # 全角記号
    )


def _fallback_count(text: str) -> int:
    # URL を 23 units として一旦置換マーカーに、残りを 1/2 で加算
    total = 0
    pos = 0
    for m in _URL_RE.finditer(text):
        chunk = text[pos:m.start()]
        for ch in chunk:
            total += 2 if _is_double_width(ch) else 1
        total += URL_WEIGHT
        pos = m.end()
    tail = text[pos:]
    for ch in tail:
        total += 2 if _is_double_width(ch) else 1
    return total


def x_weighted_length(text: str) -> int:
    if _USE_LIBRARY:
        try:
            r = parse_tweet(text)
            # twitter-text-python の戻り値は object で .weightedLength を持つ
            return int(getattr(r, "weightedLength", _fallback_count(text)))
        except Exception:  # noqa: BLE001
            return _fallback_count(text)
    return _fallback_count(text)
```

- [ ] **Step 4: テスト pass 確認**

Run: `PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_x_text.py -q`
Expected: 5 passed

ライブラリと自前 fallback で結果が違う場合は、自前 fallback の方を正(spec で定義した仕様)とし、`x_weighted_length` の実装で常に fallback を使うように Step 3 を書き換える(`_USE_LIBRARY = False` 強制)。

- [ ] **Step 5: Commit**

```bash
git add scripts/daily_bluesky_post/x_text.py scripts/daily_bluesky_post/tests/test_x_text.py
git commit -m "feat(bluesky-post): X weighted length カウンタを追加

URL=23 / CJK=2 / ASCII=1 で X 投稿の文字数を計測。
twitter-text-python が使えるならラッパー、失敗時は自前 fallback。"
```

---

## Task 4: 画像解決(`image_resolver.py`)

**Files:**
- Create: `scripts/daily_bluesky_post/image_resolver.py`
- Create: `scripts/daily_bluesky_post/tests/test_image_resolver.py`
- Create: `scripts/daily_bluesky_post/tests/fixtures/image_resolver/` 配下にフィクスチャ md

- [ ] **Step 1: フィクスチャ準備**

Create `scripts/daily_bluesky_post/tests/fixtures/image_resolver/people/with_portrait.md`:

```markdown
---
name: テスト人物
portrait: ../../assets/portraits/with_portrait.jpg
deathDate: 2000-01-01
---
本文
```

Create `scripts/daily_bluesky_post/tests/fixtures/image_resolver/people/no_portrait.md`:

```markdown
---
name: 肖像なし人物
deathDate: 2000-01-01
---
本文
```

Create `scripts/daily_bluesky_post/tests/fixtures/image_resolver/events/with_hero.md`:

```markdown
---
title: テスト event
heroImage: ../../assets/event-images/with_hero.png
date: 2000-01-01
---
本文
```

Create dummy assets: `tests/fixtures/image_resolver/assets/portraits/with_portrait.jpg`(1x1 黒 JPEG)、`tests/fixtures/image_resolver/assets/event-images/with_hero.png`(1x1 黒 PNG)— Pillow で生成:

```python
# 補助スクリプト(手動 1 回実行、コミットしない)
from PIL import Image
import pathlib
base = pathlib.Path("scripts/daily_bluesky_post/tests/fixtures/image_resolver/assets")
(base / "portraits").mkdir(parents=True, exist_ok=True)
(base / "event-images").mkdir(parents=True, exist_ok=True)
Image.new("RGB", (1, 1), color="black").save(base / "portraits" / "with_portrait.jpg", quality=85)
Image.new("RGB", (1, 1), color="black").save(base / "event-images" / "with_hero.png")
```

- [ ] **Step 2: テスト先行**

Create `scripts/daily_bluesky_post/tests/test_image_resolver.py`:

```python
from pathlib import Path
import pytest
from daily_bluesky_post.image_resolver import resolve, prepare_for_upload, X_MEDIA_LIMIT_BYTES

FIXTURES = Path(__file__).parent / "fixtures" / "image_resolver"


def test_person_with_portrait_returns_absolute_path():
    path = resolve("with_portrait", kind="person",
                   people_dir=FIXTURES / "people",
                   events_dir=FIXTURES / "events")
    assert path is not None
    assert path.is_absolute()
    assert path.name == "with_portrait.jpg"
    assert path.exists()


def test_person_without_portrait_returns_none():
    path = resolve("no_portrait", kind="person",
                   people_dir=FIXTURES / "people",
                   events_dir=FIXTURES / "events")
    assert path is None


def test_event_with_hero_returns_absolute_path():
    path = resolve("with_hero", kind="event",
                   people_dir=FIXTURES / "people",
                   events_dir=FIXTURES / "events")
    assert path is not None
    assert path.name == "with_hero.png"


def test_missing_slug_returns_none():
    path = resolve("does_not_exist", kind="person",
                   people_dir=FIXTURES / "people",
                   events_dir=FIXTURES / "events")
    assert path is None


def test_prepare_for_upload_small_returns_original(tmp_path):
    src = FIXTURES / "assets" / "portraits" / "with_portrait.jpg"
    result = prepare_for_upload(src, tmp_dir=tmp_path)
    assert result == src  # 5MB 未満ならそのまま


def test_prepare_for_upload_large_resizes(tmp_path):
    from PIL import Image
    big = tmp_path / "big.jpg"
    # 6 MB を超える画像を生成(2000x2000 ランダム JPEG quality 100)
    Image.new("RGB", (4000, 4000), color="white").save(big, quality=100)
    if big.stat().st_size < X_MEDIA_LIMIT_BYTES:
        pytest.skip("test image not large enough on this platform")
    result = prepare_for_upload(big, tmp_dir=tmp_path)
    assert result != big
    assert result.stat().st_size < X_MEDIA_LIMIT_BYTES
```

- [ ] **Step 3: fail 確認**

Run: `PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_image_resolver.py -q`
Expected: ModuleNotFoundError

- [ ] **Step 4: 実装**

Create `scripts/daily_bluesky_post/image_resolver.py`:

```python
"""slug + kind から portrait / heroImage の絶対 path を解決し、X media upload 用に整形する。

frontmatter の `portrait` / `heroImage` は md ファイル基準の相対 path で書かれているため、
md の親ディレクトリ + 相対 path で resolve する。
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

import yaml
from PIL import Image

X_MEDIA_LIMIT_BYTES = 5 * 1024 * 1024  # X の image upload 上限(5 MB)
RESIZE_LONG_EDGE = 1600
RESIZE_QUALITY = 85

Kind = Literal["person", "event"]


def resolve(
    slug: str,
    *,
    kind: Kind,
    people_dir: Path,
    events_dir: Path,
) -> Optional[Path]:
    if kind == "person":
        md_path = people_dir / f"{slug}.md"
        fm_key = "portrait"
    else:
        md_path = events_dir / f"{slug}.md"
        fm_key = "heroImage"

    if not md_path.exists():
        return None

    text = md_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    fm = yaml.safe_load(parts[1]) or {}
    rel = fm.get(fm_key)
    if not rel:
        return None

    abs_path = (md_path.parent / rel).resolve()
    if not abs_path.exists():
        return None
    return abs_path


def prepare_for_upload(src: Path, *, tmp_dir: Path) -> Path:
    """5 MB 以下ならそのまま返す。超過なら長辺 1600 / quality 85 で再エンコードして tmp に書き出す。"""
    if src.stat().st_size <= X_MEDIA_LIMIT_BYTES:
        return src

    img = Image.open(src)
    img.thumbnail((RESIZE_LONG_EDGE, RESIZE_LONG_EDGE))
    out = tmp_dir / (src.stem + "_resized.jpg")
    img.convert("RGB").save(out, format="JPEG", quality=RESIZE_QUALITY)
    return out
```

- [ ] **Step 5: テスト pass 確認**

Run: `PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_image_resolver.py -q`
Expected: 6 passed(うち 1 件は platform 依存で skip 可)

- [ ] **Step 6: Commit**

```bash
git add scripts/daily_bluesky_post/image_resolver.py scripts/daily_bluesky_post/tests/test_image_resolver.py scripts/daily_bluesky_post/tests/fixtures/image_resolver
git commit -m "feat(bluesky-post): 画像解決 + X media upload 用リサイズを追加

people.portrait / events.heroImage を絶対 path に解決、
5MB 超は長辺 1600px / quality 85 で再エンコード。"
```

---

## Task 5: X 認証情報を config に追加

**Files:**
- Modify: `scripts/daily_bluesky_post/config.py`
- Modify: `scripts/daily_bluesky_post/tests/test_config.py`

- [ ] **Step 1: テスト先行**

Append to `scripts/daily_bluesky_post/tests/test_config.py`:

```python
def test_load_secrets_includes_x_when_present(monkeypatch):
    monkeypatch.setenv("BLUESKY_HANDLE", "aoyama-cemetery.bsky.social")
    monkeypatch.setenv("BLUESKY_APP_PASSWORD", "abcd-1234")
    monkeypatch.setenv("X_API_KEY", "k")
    monkeypatch.setenv("X_API_SECRET", "ks")
    monkeypatch.setenv("X_ACCESS_TOKEN", "t")
    monkeypatch.setenv("X_ACCESS_SECRET", "ts")
    monkeypatch.setenv("X_ENABLED", "1")
    from daily_bluesky_post import config
    s = config.load_secrets()
    assert s.x is not None
    assert s.x.api_key == "k"
    assert s.x.api_secret == "ks"
    assert s.x.access_token == "t"
    assert s.x.access_secret == "ts"
    assert s.x_enabled is True


def test_load_secrets_x_disabled_when_flag_zero(monkeypatch):
    monkeypatch.setenv("BLUESKY_HANDLE", "h")
    monkeypatch.setenv("BLUESKY_APP_PASSWORD", "p")
    monkeypatch.setenv("X_API_KEY", "k")
    monkeypatch.setenv("X_API_SECRET", "ks")
    monkeypatch.setenv("X_ACCESS_TOKEN", "t")
    monkeypatch.setenv("X_ACCESS_SECRET", "ts")
    monkeypatch.setenv("X_ENABLED", "0")
    from daily_bluesky_post import config
    s = config.load_secrets()
    assert s.x_enabled is False


def test_load_secrets_x_disabled_when_credentials_missing(monkeypatch):
    monkeypatch.setenv("BLUESKY_HANDLE", "h")
    monkeypatch.setenv("BLUESKY_APP_PASSWORD", "p")
    monkeypatch.delenv("X_API_KEY", raising=False)
    monkeypatch.setenv("X_ENABLED", "1")  # flag は ON でも cred 無ければ無効
    from daily_bluesky_post import config
    s = config.load_secrets()
    assert s.x_enabled is False
    assert s.x is None
```

- [ ] **Step 2: fail 確認**

Run: `PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_config.py -q`
Expected: 3 fails(AttributeError: 'Secrets' has no attribute 'x' / 'x_enabled')

- [ ] **Step 3: config.py 改造**

Replace `Secrets` dataclass + `load_secrets()` in `scripts/daily_bluesky_post/config.py`:

```python
@dataclass(frozen=True)
class XSecrets:
    api_key: str
    api_secret: str
    access_token: str
    access_secret: str


@dataclass(frozen=True)
class Secrets:
    bluesky_handle: str
    bluesky_app_password: str
    discord_webhook_url: Optional[str]
    x: Optional[XSecrets]
    x_enabled: bool


def load_secrets() -> Secrets:
    handle = os.environ.get("BLUESKY_HANDLE")
    pw = os.environ.get("BLUESKY_APP_PASSWORD")
    if not handle or not pw:
        raise MissingSecretError(
            "BLUESKY_HANDLE / BLUESKY_APP_PASSWORD が未設定です。"
            " ~/.config/aoyama-cemetery/bluesky.env を確認してください。"
        )

    x_keys = ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")
    x_vals = [os.environ.get(k) for k in x_keys]
    x_secrets = XSecrets(*x_vals) if all(x_vals) else None  # type: ignore[arg-type]
    x_flag = os.environ.get("X_ENABLED", "0") == "1"
    x_enabled = x_flag and x_secrets is not None

    return Secrets(
        bluesky_handle=handle,
        bluesky_app_password=pw,
        discord_webhook_url=os.environ.get("DISCORD_WEBHOOK_URL"),
        x=x_secrets,
        x_enabled=x_enabled,
    )
```

- [ ] **Step 4: 既存テスト互換確認**

既存 `test_config.py` の `Secrets` インスタンス化箇所(`bluesky_handle=..., bluesky_app_password=..., discord_webhook_url=...` の 3 引数)があれば、`x=None, x_enabled=False` を追加する。

```bash
grep -n "Secrets(" scripts/daily_bluesky_post/tests/test_config.py
```

該当箇所を直す。

- [ ] **Step 5: テスト pass 確認**

Run: `PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_config.py -q`
Expected: 全 pass

- [ ] **Step 6: 全テスト regression なし**

Run: `PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/ -q`
Expected: 全 pass

- [ ] **Step 7: Commit**

```bash
git add scripts/daily_bluesky_post/config.py scripts/daily_bluesky_post/tests/test_config.py
git commit -m "feat(bluesky-post): config に X 認証情報 + X_ENABLED フラグを追加"
```

---

## Task 6: X 投稿クライアント(`x_client.py`)

**Files:**
- Create: `scripts/daily_bluesky_post/x_client.py`
- Create: `scripts/daily_bluesky_post/tests/test_x_client.py`

- [ ] **Step 1: テスト先行 — tweepy を mock**

Create `scripts/daily_bluesky_post/tests/test_x_client.py`:

```python
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from daily_bluesky_post.config import XSecrets
from daily_bluesky_post.x_client import (
    XClient, XAuthError, XRateLimitError, XPostError,
)


@pytest.fixture
def secrets():
    return XSecrets(api_key="k", api_secret="ks", access_token="t", access_secret="ts")


@pytest.fixture
def mock_tweepy():
    with patch("daily_bluesky_post.x_client.tweepy") as tw:
        v2 = MagicMock()
        v1 = MagicMock()
        tw.Client.return_value = v2
        tw.API.return_value = v1
        # exception 階層を再現
        class _Unauth(Exception): ...
        class _Forbidden(Exception): ...
        class _TooMany(Exception): ...
        class _Tweepy(Exception): ...
        tw.errors.Unauthorized = _Unauth
        tw.errors.Forbidden = _Forbidden
        tw.errors.TooManyRequests = _TooMany
        tw.errors.TweepyException = _Tweepy
        yield tw, v2, v1


def test_post_text_only(secrets, mock_tweepy):
    tw, v2, v1 = mock_tweepy
    v2.create_tweet.return_value = MagicMock(data={"id": "1234567890"})
    client = XClient(secrets)
    result = client.post(text="hello", image_path=None)
    assert result["tweet_id"] == "1234567890"
    assert "1234567890" in result["url"]
    v2.create_tweet.assert_called_once_with(text="hello", media_ids=None)


def test_post_with_image_uploads_via_v1(secrets, mock_tweepy, tmp_path):
    tw, v2, v1 = mock_tweepy
    v1.media_upload.return_value = MagicMock(media_id_string="m999")
    v2.create_tweet.return_value = MagicMock(data={"id": "777"})
    img = tmp_path / "p.jpg"
    img.write_bytes(b"\xff\xd8\xff")
    client = XClient(secrets)
    result = client.post(text="t", image_path=img)
    assert result["tweet_id"] == "777"
    v1.media_upload.assert_called_once_with(filename=str(img))
    v2.create_tweet.assert_called_once_with(text="t", media_ids=["m999"])


def test_post_unauthorized_raises_xautherror(secrets, mock_tweepy):
    tw, v2, v1 = mock_tweepy
    v2.create_tweet.side_effect = tw.errors.Unauthorized("401")
    client = XClient(secrets)
    with pytest.raises(XAuthError):
        client.post(text="t", image_path=None)


def test_post_forbidden_raises_xautherror(secrets, mock_tweepy):
    tw, v2, v1 = mock_tweepy
    v2.create_tweet.side_effect = tw.errors.Forbidden("403")
    client = XClient(secrets)
    with pytest.raises(XAuthError):
        client.post(text="t", image_path=None)


def test_post_too_many_requests_raises_ratelimit(secrets, mock_tweepy):
    tw, v2, v1 = mock_tweepy
    v2.create_tweet.side_effect = tw.errors.TooManyRequests("429")
    client = XClient(secrets)
    with pytest.raises(XRateLimitError):
        client.post(text="t", image_path=None)


def test_post_generic_tweepy_error_raises_xposterror(secrets, mock_tweepy):
    tw, v2, v1 = mock_tweepy
    v2.create_tweet.side_effect = tw.errors.TweepyException("boom")
    client = XClient(secrets)
    with pytest.raises(XPostError):
        client.post(text="t", image_path=None)


def test_media_upload_failure_falls_back_to_text_only(secrets, mock_tweepy, tmp_path):
    tw, v2, v1 = mock_tweepy
    v1.media_upload.side_effect = tw.errors.TweepyException("media fail")
    v2.create_tweet.return_value = MagicMock(data={"id": "1"})
    img = tmp_path / "p.jpg"
    img.write_bytes(b"x")
    client = XClient(secrets)
    result = client.post(text="t", image_path=img)
    # 画像 upload 失敗時はテキストのみで継続
    assert result["tweet_id"] == "1"
    v2.create_tweet.assert_called_once_with(text="t", media_ids=None)


def test_client_lazy_initializes_tweepy(secrets, mock_tweepy):
    tw, v2, v1 = mock_tweepy
    XClient(secrets)
    tw.Client.assert_called_once()
    tw.API.assert_called_once()
```

- [ ] **Step 2: fail 確認**

Run: `PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_x_client.py -q`
Expected: ModuleNotFoundError

- [ ] **Step 3: 実装**

Create `scripts/daily_bluesky_post/x_client.py`:

```python
"""X (旧 Twitter) v2 投稿クライアント。

OAuth 1.0a User Context で
- v2 endpoint: POST /2/tweets(本文 + media_ids)
- v1.1 endpoint: POST /1.1/media/upload.json(画像)
の組み合わせ。

エラー区分:
- XAuthError      : 401 / 403(env 再確認、以降の X 処理 bypass)
- XRateLimitError : 429(月制限、以降の X 処理 bypass)
- XPostError      : その他 TweepyException(当該 match のみ skip)
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import tweepy

from daily_bluesky_post.config import XSecrets


class XAuthError(RuntimeError):
    pass


class XRateLimitError(RuntimeError):
    pass


class XPostError(RuntimeError):
    pass


class XClient:
    def __init__(self, secrets: XSecrets):
        self._v2 = tweepy.Client(
            consumer_key=secrets.api_key,
            consumer_secret=secrets.api_secret,
            access_token=secrets.access_token,
            access_token_secret=secrets.access_secret,
        )
        self._v1 = tweepy.API(tweepy.OAuth1UserHandler(
            secrets.api_key, secrets.api_secret,
            secrets.access_token, secrets.access_secret,
        ))

    def post(self, *, text: str, image_path: Optional[Path]) -> dict:
        media_ids = None
        if image_path is not None:
            try:
                media = self._v1.media_upload(filename=str(image_path))
                media_ids = [media.media_id_string]
            except tweepy.errors.TweepyException as e:
                # media upload は best-effort、失敗してもテキストのみで継続
                print(f"[x_client] media upload failed, falling back to text-only: {e}")
                media_ids = None

        try:
            resp = self._v2.create_tweet(text=text, media_ids=media_ids)
        except tweepy.errors.Unauthorized as e:
            raise XAuthError(f"X 認証失敗 (401): {e}") from e
        except tweepy.errors.Forbidden as e:
            raise XAuthError(f"X 認可失敗 (403): {e}") from e
        except tweepy.errors.TooManyRequests as e:
            raise XRateLimitError(f"X rate limit (429): {e}") from e
        except tweepy.errors.TweepyException as e:
            raise XPostError(f"X post failed: {e}") from e

        tweet_id = resp.data["id"]
        return {
            "tweet_id": tweet_id,
            "url": f"https://x.com/i/web/status/{tweet_id}",
        }
```

- [ ] **Step 4: テスト pass 確認**

Run: `PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_x_client.py -q`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/daily_bluesky_post/x_client.py scripts/daily_bluesky_post/tests/test_x_client.py
git commit -m "feat(bluesky-post): X 投稿クライアント(tweepy)を追加

OAuth 1.0a User Context で v2 tweet + v1.1 media upload。
Auth / RateLimit / その他を 3 種の例外で分類、
media upload 失敗時はテキストのみで継続。"
```

---

## Task 7: X 用 subagent 2 本を追加

**Files:**
- Create: `.claude/agents/aoyama-post-writer-x.md`
- Create: `.claude/agents/aoyama-fact-checker-x.md`

- [ ] **Step 1: 既存 Bluesky 版 subagent を参考に基本構造をコピー**

```bash
cat .claude/agents/aoyama-post-writer.md  # 構造把握
cat .claude/agents/aoyama-fact-checker.md  # 構造把握
```

- [ ] **Step 2: `aoyama-post-writer-x.md` を作成**

Create `.claude/agents/aoyama-post-writer-x.md`:

```markdown
---
name: aoyama-post-writer-x
description: 青山霊園に眠る偉人または歴史的 event の X(旧 Twitter)投稿文を、与えられた frontmatter と本文のみを根拠に生成する short 版。常体ベース + ハッシュタグ 1-2 個許容、事実誤認ゼロを最優先する。
model: claude-sonnet-4-6
---

あなたは青山霊園に眠る偉人と歴史的事件を紹介する X(旧 Twitter)アカウントの投稿作成者です。

# 厳守ルール(事実)

1. 与えられた frontmatter と本文(body)に書かれている事実のみを使うこと
2. それ以外の人物関係・事件・著作・引用・地名・年号は一切追加しない
3. 出典に書かれていることを再構成・要約・接続するのは OK、解釈の飛躍や演出のための創作は NG

# 厳守ルール(形式)

4. 文字数(厳守): **全体で 270 weighted units 以内**(X 280 の安全マージン 10)
   - URL は 23 units 固定(t.co 短縮)
   - 日本語 1 文字 = 2 units、ASCII 1 文字 = 1 unit
   - タイトル行は約 20-25 字(40-50 units)
   - 本文 80-110 字(160-220 units)
   - ハッシュタグ `#青山霊園` (10) + 任意 1 個(8-12)
   - 改行 + URL(23)
   - → 出力前に必ず weighted unit を自分で計算し、270 を超えないこと
5. 文体: **常体(だ・である・た止め)** を基本に、軽い問いかけや余韻は許容
   - OK: 「凶刃に倒れた」「47 歳の生涯を閉じた」「150 年前の今日のことだ」
   - NG: 「凶刃に倒れました」(です・ます禁止)、「衝撃の最期…!」(感嘆装飾禁止)
6. ハッシュタグ:
   - **`#青山霊園` を必ず最後に 1 個** 入れる
   - 加えて、人物・event に応じた客観カテゴリタグを任意で 1 個追加可(例: `#明治維新` `#幕末` `#文学` `#陸軍` `#政治家`)
   - **誇張的・主観タグは禁止**(NG: `#討幕の英雄` `#最強の総理` 等)
7. 絵文字禁止、太字・装飾記号・見出し記号も禁止
8. **墓所区画(graveSection)への言及禁止**
9. **構成(必須・1 要素でも欠けたら NG)**:
   - 1 行目: person は「【◯◯ 命日】」、event は「【◯◯◯◯(event 名)】」
   - 2-3 行目に本文(80-110 字)
   - ハッシュタグ行(`#青山霊園` 必須、任意で `#xxx` を 1 個)
   - **最終行: URL を 1 行で必ず置く**(省略禁止)
10. **本文中に元号 + 年 + 月 + 日の日付表記を最低 1 箇所含めること**(例:「明治 11 年 5 月 14 日」「昭和 20 年 8 月 15 日」)
11. 出力は投稿本文のみ(前置き・説明・コードブロック・JSON・引用符なし)

# トーン

12. 単なる事実列挙ではなく、その人物・事件の「重み」を 100 字前後で凝縮する
13. 「150 年前の今日」のような時間軸の問いかけ・現代接続を 1 文入れると刺さりやすい
14. 過剰な感傷・大仰な表現は避け、冷静な筆致

# 入力フォーマット

```yaml
kind: person | event
url: https://aoyama-cemetery.pages.dev/...
anniversary_year: <周年数>
frontmatter:
  (該当 md の frontmatter 全体)
body: |
  (該当 md の --- 以下の本文)
```

# 出力フォーマット

投稿本文の plain text のみ(改行込み)。

例:
```
【大久保利通 命日】明治11年5月14日、紀尾井坂で暗殺。中央集権を貫いた内務卿、その終わりは騎馬ひとつだった。今の私たちが暮らす制度の輪郭は、この日から動き始めた。
#青山霊園 #明治維新
https://aoyama-cemetery.pages.dev/people/okubo-toshimichi
```
```

- [ ] **Step 3: `aoyama-fact-checker-x.md` を作成**

Create `.claude/agents/aoyama-fact-checker-x.md`:

```markdown
---
name: aoyama-fact-checker-x
description: aoyama-post-writer-x が生成した X 投稿文を、与えられた frontmatter と本文のみを真として厳格に critique する。事実外混入・ハッシュタグ歪曲・必須要素欠落をゼロにする最終ゲート。
model: claude-sonnet-4-6
---

あなたは aoyama-post-writer-x が生成した X 投稿文の最終 critique を担うゲートキーパーです。
**疑わしきは fail**。1 つでも違反があれば verdict="fail" を返してください。

# 検証項目

1. **frontmatter + body 外の事実混入禁止**
   - 与えられた frontmatter と body に書かれていない人物・事件・著作・地名・年号・引用が混ざっていないか
   - 1 つでも見つけたら fail

2. **文体(常体)**
   - 「です・ます」「でした」「ました」が混ざっていないか
   - 1 つでもあれば fail

3. **絵文字 / 装飾記号禁止**
   - 絵文字、太字、見出し記号(`#` ハッシュタグは除く)、引用符装飾などがあれば fail

4. **元号 + 年 + 月 + 日の日付表記**
   - 本文中に「明治◯年◯月◯日」「大正◯年◯月◯日」「昭和◯年◯月◯日」のような元号付き具体日付が最低 1 箇所あるか
   - なければ fail

5. **構成完備**
   - 1 行目が `【◯◯ 命日】` or `【◯◯(event 名)】` 形式か
   - ハッシュタグ行に `#青山霊園` が含まれているか(必須)
   - 最終行が URL か(frontmatter の `url` と一致するか)
   - 1 つでも欠けたら fail

6. **ハッシュタグ歪曲検査**
   - `#青山霊園` 以外のハッシュタグ(あれば)が **客観的カテゴリ** か
   - OK: `#明治維新` `#幕末` `#文学` `#陸軍` `#政治家` `#外交`(時代・分野カテゴリ)
   - NG: `#討幕の英雄` `#最強の総理` `#神` `#泣ける` 等の主観・誇張タグ
   - 3 個以上のハッシュタグも fail(`#青山霊園` 含めて最大 2 個)
   - 違反があれば fail

7. **墓所区画(graveSection)言及禁止**
   - 「青山霊園◯側」「1 種イ◯号」等の区画表記があれば fail

8. **文字数チェック(参考、最終決定は外側でも計測)**
   - 全体 weighted length が概算 270 unit 以内か(計測根拠の概算でよい、明確に超過していそうなら fail)

# 入力フォーマット

```yaml
post_text: |
  (生成された投稿文)
frontmatter:
  (該当 md の frontmatter 全体)
body: |
  (該当 md の --- 以下の本文)
```

# 出力フォーマット(JSON のみ、前置き禁止)

```json
{"verdict": "pass" | "fail", "violations": ["項目: 違反内容", ...]}
```

`pass` の場合 `violations` は空配列。`fail` の場合は具体的な違反根拠を 1 行ずつ列挙してください。
```

- [ ] **Step 4: subagent 2 ファイル分の git 追加 + commit**

```bash
git add .claude/agents/aoyama-post-writer-x.md .claude/agents/aoyama-fact-checker-x.md
git commit -m "feat(bluesky-post): X 用 subagent 2 本を追加

post-writer-x: 80-110 字 short 版、#青山霊園 必須 + 任意カテゴリ 1 個。
fact-checker-x: 事実外混入 + 歪曲タグ + 必須要素を厳格 critique。"
```

(Step なし — subagent は md ファイル単体なのでテスト不要、実行時の orchestrator E2E で動作確認)

---

## Task 8: `claude_runner.generate_post` に agent_name 引数を追加

**Files:**
- Modify: `scripts/daily_bluesky_post/claude_runner.py`
- Modify: `scripts/daily_bluesky_post/tests/test_claude_runner.py`

- [ ] **Step 1: テスト先行**

Append to `scripts/daily_bluesky_post/tests/test_claude_runner.py`:

```python
def test_build_prompt_uses_specified_agent_name():
    from daily_bluesky_post.claude_runner import _build_prompt
    p_bluesky = _build_prompt(
        kind="person", url="https://x", anniversary_year=150,
        frontmatter={"name": "テスト"}, body="本文",
        agent_name="aoyama-post-writer",
        fact_checker_name="aoyama-fact-checker",
    )
    p_x = _build_prompt(
        kind="person", url="https://x", anniversary_year=150,
        frontmatter={"name": "テスト"}, body="本文",
        agent_name="aoyama-post-writer-x",
        fact_checker_name="aoyama-fact-checker-x",
    )
    assert "aoyama-post-writer subagent" in p_bluesky
    assert "aoyama-fact-checker subagent" in p_bluesky
    assert "aoyama-post-writer-x subagent" in p_x
    assert "aoyama-fact-checker-x subagent" in p_x


def test_generate_post_passes_agent_name_through(monkeypatch):
    from daily_bluesky_post import claude_runner
    captured = {}
    def fake_run(prompt, timeout_sec):
        captured["prompt"] = prompt
        return claude_runner.GenerateResult(status="ok", post_text="ok")
    monkeypatch.setattr(claude_runner, "_run_claude", fake_run)
    claude_runner.generate_post(
        kind="person", url="https://x", anniversary_year=1,
        frontmatter={}, body="",
        agent_name="aoyama-post-writer-x",
        fact_checker_name="aoyama-fact-checker-x",
    )
    assert "aoyama-post-writer-x" in captured["prompt"]
    assert "aoyama-fact-checker-x" in captured["prompt"]
```

- [ ] **Step 2: fail 確認**

Run: `PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_claude_runner.py -q`
Expected: 2 fails(TypeError: unexpected keyword `agent_name`)

- [ ] **Step 3: `_build_prompt` を改造**

Edit `scripts/daily_bluesky_post/claude_runner.py` 行 37-64 を:

```python
def _build_prompt(
    *,
    kind: str, url: str, anniversary_year: int,
    frontmatter: Dict[str, Any], body: str,
    agent_name: str = "aoyama-post-writer",
    fact_checker_name: str = "aoyama-fact-checker",
) -> str:
    fm_yaml = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)
    body_indented = "\n".join("  " + line for line in body.splitlines()) if body else "  (なし)"
    return f"""次の Match を投稿する文を作って、最後に必ず JSON だけを出力してください。

## 入力
kind: {kind}
url: {url}
anniversary_year: {anniversary_year}
frontmatter:
{fm_yaml}
body: |
{body_indented}

## 手順
1. {agent_name} subagent に上記を渡して投稿文を生成する
2. {fact_checker_name} subagent に生成文と frontmatter + body を渡して critique する
3. critique が fail なら、violations を post-writer に渡して再生成 → 再 critique(リトライは 1 回まで)
4. 2 回目も fail なら status="failed" として終了

## 出力(最終出力は JSON 1 行のみ。前置きやコードフェンス禁止)
成功時:
{{"status": "ok", "post_text": "<投稿本文>", "attempts": <1または2>}}

失敗時:
{{"status": "failed", "attempts": 2, "violations": ["..."], "last_text": "<最後に生成された文>"}}
"""
```

- [ ] **Step 4: `_build_regenerate_prompt` も同様に拡張**

行 75-119 の `_build_regenerate_prompt` シグネチャに `agent_name`(デフォルト `"aoyama-post-writer"`) を追加、prompt 文中の `aoyama-post-writer subagent` を `{agent_name} subagent` に置換。Bluesky 既存挙動はデフォルト引数で維持。

- [ ] **Step 5: `generate_post` / `regenerate_shorter` 公開関数にも agent_name 引数追加**

行 170-208 の `generate_post` / `regenerate_shorter` シグネチャに以下を追加:

```python
agent_name: str = "aoyama-post-writer",
fact_checker_name: str = "aoyama-fact-checker",
```

`_build_prompt` / `_build_regenerate_prompt` 呼び出しに渡す(regenerate は agent_name のみ)。

- [ ] **Step 6: テスト pass 確認**

Run: `PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_claude_runner.py -q`
Expected: 全 pass

- [ ] **Step 7: 全体 regression なし**

Run: `PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/ -q`
Expected: 全 pass

- [ ] **Step 8: Commit**

```bash
git add scripts/daily_bluesky_post/claude_runner.py scripts/daily_bluesky_post/tests/test_claude_runner.py
git commit -m "feat(bluesky-post): claude_runner に agent_name 引数を追加

Bluesky 既存挙動はデフォルト維持、X 用は agent_name=aoyama-post-writer-x で
post-writer-x / fact-checker-x にルートする。"
```

---

## Task 9: `git_commit` を multi-platform 化

**Files:**
- Modify: `scripts/daily_bluesky_post/git_commit.py`
- Modify: `scripts/daily_bluesky_post/tests/test_git_commit.py`

- [ ] **Step 1: テスト先行**

Append to `scripts/daily_bluesky_post/tests/test_git_commit.py`:

```python
def test_commit_posted_logs_stages_both_files(monkeypatch, tmp_path):
    from daily_bluesky_post import git_commit
    calls = []
    def fake_run(args, **kw):
        calls.append(args)
        class R: returncode = 1
        return R()
    monkeypatch.setattr(git_commit.subprocess, "run", fake_run)
    git_commit.commit_posted_logs(date="2026-05-14", slug="okubo",
                                  bluesky_status="ok", x_status="ok")
    # git add で 2 ファイル分 staging
    add_calls = [c for c in calls if c[1] == "add"]
    assert any("posted_bluesky.jsonl" in " ".join(c) for c in add_calls)
    assert any("posted_x.jsonl" in " ".join(c) for c in add_calls)
    commit_calls = [c for c in calls if c[1] == "commit"]
    assert len(commit_calls) == 1
    msg = " ".join(commit_calls[0])
    assert "2026-05-14" in msg and "okubo" in msg
    assert "bluesky=ok" in msg and "x=ok" in msg


def test_commit_posted_logs_skips_when_no_diff(monkeypatch):
    from daily_bluesky_post import git_commit
    calls = []
    def fake_run(args, **kw):
        calls.append(args)
        class R: returncode = 0  # diff なし
        return R()
    monkeypatch.setattr(git_commit.subprocess, "run", fake_run)
    git_commit.commit_posted_logs(date="2026-05-14", slug="x",
                                  bluesky_status="skip", x_status="skip")
    commit_calls = [c for c in calls if c[1] == "commit"]
    assert commit_calls == []
```

- [ ] **Step 2: fail 確認**

Run: `PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_git_commit.py -q`
Expected: 2 fails(AttributeError: `commit_posted_logs` not found)

- [ ] **Step 3: 実装 — 既存 `commit_posted_log`(単数)を残しつつ複数版を追加**

Edit `scripts/daily_bluesky_post/git_commit.py`、末尾に追加:

```python
def commit_posted_logs(
    *,
    date: str, slug: str,
    bluesky_status: str, x_status: str,
) -> None:
    """両 platform の posted log をまとめて stage + commit。

    bluesky_status / x_status は "ok" / "fail" / "auth_fail" / "rate_limit" / "skip" / "disabled" 等。
    両方 stage して diff があれば 1 commit。
    """
    from daily_bluesky_post.config import POSTED_BLUESKY_LOG, POSTED_X_LOG

    rel_b = str(POSTED_BLUESKY_LOG.relative_to(PROJECT_ROOT))
    rel_x = str(POSTED_X_LOG.relative_to(PROJECT_ROOT))

    for rel in (rel_b, rel_x):
        subprocess.run(["git", "add", "--", rel], cwd=PROJECT_ROOT)

    diff_b = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", rel_b], cwd=PROJECT_ROOT,
    )
    diff_x = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", rel_x], cwd=PROJECT_ROOT,
    )
    if diff_b.returncode == 0 and diff_x.returncode == 0:
        return  # どちらも差分なし

    msg = f"post: {date} {slug} bluesky={bluesky_status} x={x_status}"
    subprocess.run(
        ["git", "commit", "-m", msg, "--", rel_b, rel_x],
        cwd=PROJECT_ROOT, check=True,
    )
```

注: `commit_posted_log`(単数)は backward compatibility のため残し、orchestrator は新しい `commit_posted_logs`(複数)を使う。Task 10 完了後に旧関数の使用箇所がなくなったら Task 10 の最後で削除。

- [ ] **Step 4: テスト pass 確認**

Run: `PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_git_commit.py -q`
Expected: 全 pass

- [ ] **Step 5: Commit**

```bash
git add scripts/daily_bluesky_post/git_commit.py scripts/daily_bluesky_post/tests/test_git_commit.py
git commit -m "feat(bluesky-post): git_commit に platform 統合版 commit_posted_logs を追加"
```

---

## Task 10: orchestrator を multi-platform 化

**Files:**
- Modify: `scripts/daily_bluesky_post/orchestrator.py`(ほぼ全面改造)
- Modify: `scripts/daily_bluesky_post/tests/test_orchestrator.py`(既存に追加)
- Create: `scripts/daily_bluesky_post/tests/test_orchestrator_x.py`

- [ ] **Step 1: 新規テストファイル**

Create `scripts/daily_bluesky_post/tests/test_orchestrator_x.py`:

```python
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from daily_bluesky_post import orchestrator, match, claude_runner


def _mk_match(slug="okubo", kind="person"):
    return match.Match(
        kind=kind, slug=slug, frontmatter={"name": "テスト", "url": "https://x"},
        body="本文", url="https://aoyama-cemetery.pages.dev/people/" + slug,
        anniversary_year=150,
    )


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("BLUESKY_HANDLE", "h")
    monkeypatch.setenv("BLUESKY_APP_PASSWORD", "p")
    monkeypatch.setenv("X_API_KEY", "k")
    monkeypatch.setenv("X_API_SECRET", "ks")
    monkeypatch.setenv("X_ACCESS_TOKEN", "t")
    monkeypatch.setenv("X_ACCESS_SECRET", "ts")
    monkeypatch.setenv("X_ENABLED", "1")
    # logs を tmp に逃がす
    from daily_bluesky_post import config
    monkeypatch.setattr(config, "POSTED_BLUESKY_LOG", tmp_path / "pb.jsonl")
    monkeypatch.setattr(config, "POSTED_X_LOG", tmp_path / "px.jsonl")
    return tmp_path


def _patch_all(monkeypatch, *,
               match_result=None, claude_text="本文 https://x", claude_status="ok",
               bluesky_uri="at://x", x_result=None, x_exc=None,
               x_enabled=True):
    matches = [_mk_match()] if match_result is None else match_result
    monkeypatch.setattr(orchestrator.match, "match_today", lambda *a, **k: matches)
    monkeypatch.setattr(
        orchestrator.claude_runner, "generate_post",
        lambda **k: claude_runner.GenerateResult(status=claude_status, post_text=claude_text),
    )
    monkeypatch.setattr(orchestrator.ogp_fetcher, "fetch", lambda url: MagicMock(title="t", description="d", image_url=None))
    monkeypatch.setattr(orchestrator.bluesky_client, "post", lambda **k: bluesky_uri)
    # X
    fake_x = MagicMock()
    if x_exc is not None:
        fake_x.post.side_effect = x_exc
    else:
        fake_x.post.return_value = x_result or {"tweet_id": "1", "url": "https://x.com/i/web/status/1"}
    monkeypatch.setattr(orchestrator, "_build_x_client", lambda secrets: fake_x)
    monkeypatch.setattr(orchestrator, "_resolve_image", lambda slug, kind: None)
    monkeypatch.setattr(orchestrator.git_commit, "commit_posted_logs", lambda **k: None)
    monkeypatch.setattr(orchestrator.notifier, "notify", lambda **k: None)
    return fake_x


def test_both_platforms_succeed(env, monkeypatch):
    fake_x = _patch_all(monkeypatch)
    rc = orchestrator.run(today=date(2026, 5, 14), dry_run=False)
    assert rc == 0
    fake_x.post.assert_called_once()


def test_x_disabled_skips_x(env, monkeypatch):
    monkeypatch.setenv("X_ENABLED", "0")
    fake_x = _patch_all(monkeypatch)
    orchestrator.run(today=date(2026, 5, 14), dry_run=False)
    fake_x.post.assert_not_called()


def test_x_auth_failure_disables_rest_of_x(env, monkeypatch):
    from daily_bluesky_post.x_client import XAuthError
    matches = [_mk_match("a"), _mk_match("b")]
    fake_x = _patch_all(monkeypatch, match_result=matches, x_exc=XAuthError("401"))
    orchestrator.run(today=date(2026, 5, 14), dry_run=False)
    # 1 件目で auth fail → 2 件目は X を call しない
    assert fake_x.post.call_count == 1


def test_bluesky_success_x_failure_independent(env, monkeypatch):
    from daily_bluesky_post.x_client import XPostError
    fake_x = _patch_all(monkeypatch, x_exc=XPostError("boom"))
    rc = orchestrator.run(today=date(2026, 5, 14), dry_run=False)
    assert rc == 0
    # Bluesky 側は通常 commit, X は失敗扱いだが orchestrator は完走


def test_already_posted_per_platform(env, monkeypatch, tmp_path):
    from daily_bluesky_post import post_log, config
    from datetime import datetime, timezone, timedelta
    JST = timezone(timedelta(hours=9))
    # Bluesky 側だけ既投稿
    post_log.append(config.POSTED_BLUESKY_LOG, post_log.Entry(
        date=date(2026, 5, 14), slug="okubo", kind="person",
        post_uri="at://existing", at=datetime.now(JST).replace(microsecond=0),
    ))
    fake_x = _patch_all(monkeypatch)
    fake_bsky = MagicMock(return_value="at://new")
    monkeypatch.setattr(orchestrator.bluesky_client, "post", fake_bsky)
    orchestrator.run(today=date(2026, 5, 14), dry_run=False)
    # Bluesky はスキップされ X だけ実行
    fake_bsky.assert_not_called()
    fake_x.post.assert_called_once()


def test_x_rate_limit_disables_rest(env, monkeypatch):
    from daily_bluesky_post.x_client import XRateLimitError
    matches = [_mk_match("a"), _mk_match("b")]
    fake_x = _patch_all(monkeypatch, match_result=matches, x_exc=XRateLimitError("429"))
    orchestrator.run(today=date(2026, 5, 14), dry_run=False)
    assert fake_x.post.call_count == 1  # 連鎖防止


def test_dry_run_does_not_post_either(env, monkeypatch):
    fake_x = _patch_all(monkeypatch)
    fake_bsky = MagicMock()
    monkeypatch.setattr(orchestrator.bluesky_client, "post", fake_bsky)
    orchestrator.run(today=date(2026, 5, 14), dry_run=True)
    fake_bsky.assert_not_called()
    fake_x.post.assert_not_called()
```

- [ ] **Step 2: fail 確認**

Run: `PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_orchestrator_x.py -q`
Expected: AttributeError or 失敗(orchestrator にまだ `_build_x_client` / `_resolve_image` がない)

- [ ] **Step 3: orchestrator.py 改造**

Edit `scripts/daily_bluesky_post/orchestrator.py`:

```python
"""エンドツーエンド orchestrator + CLI entry。

usage:
  python -m daily_bluesky_post.orchestrator
  python -m daily_bluesky_post.orchestrator --dry-run
  python -m daily_bluesky_post.orchestrator --today 2026-05-14 --dry-run
"""
from __future__ import annotations

import argparse
import logging
import sys
import tempfile
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from daily_bluesky_post import (
    bluesky_client, claude_runner, config, git_commit, image_resolver,
    match, notifier, ogp_fetcher, post_log, x_text,
)
from daily_bluesky_post.x_client import (
    XAuthError, XClient, XPostError, XRateLimitError,
)

logger = logging.getLogger("aoyama-post")
JST = timezone(timedelta(hours=9))

BLUESKY_LIMIT = 300
BLUESKY_SAFE = 290


def _build_x_client(x_secrets) -> XClient:
    """テスト fixture から差し替えるための薄いファクトリ。"""
    return XClient(x_secrets)


def _resolve_image(slug: str, kind: str) -> Optional[Path]:
    return image_resolver.resolve(
        slug, kind=kind,
        people_dir=config.PEOPLE_DIR, events_dir=config.EVENTS_DIR,
    )


def run(*, today: date, dry_run: bool = False) -> int:
    secrets = config.load_secrets()
    matches = match.match_today(today, config.PEOPLE_DIR, config.EVENTS_DIR)
    logger.info("matches=%d for %s", len(matches), today.isoformat())
    if not matches:
        return 0

    entries_b = post_log.load(config.POSTED_BLUESKY_LOG)
    entries_x = post_log.load(config.POSTED_X_LOG)
    bluesky_auth_failed = False
    x_disabled_after_fail = False
    x_client_instance: Optional[XClient] = None

    for m in matches:
        bluesky_status = _process_bluesky(
            m, today, secrets, entries_b, dry_run,
            auth_failed=bluesky_auth_failed,
        )
        if bluesky_status == "auth_fail":
            bluesky_auth_failed = True

        if not secrets.x_enabled:
            x_status = "disabled"
        elif x_disabled_after_fail:
            x_status = "skipped_after_fail"
        else:
            if x_client_instance is None:
                x_client_instance = _build_x_client(secrets.x)
            x_status = _process_x(
                m, today, secrets, entries_x, dry_run, x_client_instance,
            )
            if x_status in ("auth_fail", "rate_limit"):
                x_disabled_after_fail = True

        if not dry_run:
            git_commit.commit_posted_logs(
                date=today.isoformat(), slug=m.slug,
                bluesky_status=bluesky_status, x_status=x_status,
            )

    return 0


def _process_bluesky(m, today, secrets, entries, dry_run, *, auth_failed) -> str:
    if auth_failed:
        return "skipped_auth"
    if post_log.already_posted(entries, today, m.slug):
        return "already"

    result = claude_runner.generate_post(
        kind=m.kind, url=m.url, anniversary_year=m.anniversary_year,
        frontmatter=m.frontmatter, body=m.body,
        agent_name="aoyama-post-writer",
        fact_checker_name="aoyama-fact-checker",
    )
    if result.status != "ok":
        _notify_generation_failure(secrets.discord_webhook_url, m, result, platform="bluesky")
        return "gen_fail"

    text_len = len(result.post_text)
    if text_len > BLUESKY_LIMIT:
        result = claude_runner.regenerate_shorter(
            kind=m.kind, url=m.url, anniversary_year=m.anniversary_year,
            frontmatter=m.frontmatter, body=m.body,
            previous_text=result.post_text, previous_length=text_len,
            target_length=BLUESKY_SAFE,
        )
        if result.status != "ok" or len(result.post_text) > BLUESKY_LIMIT:
            notifier.notify(
                webhook_url=secrets.discord_webhook_url,
                title="[bluesky] 字数超過",
                body=f"slug={m.slug}\ntext:\n{result.post_text}",
            )
            return "length_fail"

    if dry_run:
        print(f"--- BLUESKY DRY: {m.slug} ({len(result.post_text)} chars) ---\n{result.post_text}\n")
        return "dry"

    ogp = ogp_fetcher.fetch(m.url)
    try:
        uri = bluesky_client.post(
            handle=secrets.bluesky_handle, password=secrets.bluesky_app_password,
            text=result.post_text, link_url=m.url, ogp=ogp,
        )
    except bluesky_client.AuthError as e:
        notifier.notify(
            webhook_url=secrets.discord_webhook_url,
            title="[bluesky] 認証失敗",
            body=str(e),
        )
        return "auth_fail"
    except Exception as e:  # noqa: BLE001
        notifier.notify(
            webhook_url=secrets.discord_webhook_url,
            title="[bluesky] 投稿失敗",
            body=f"slug={m.slug}\nerror={e}\ntext=\n{result.post_text}",
        )
        return "fail"

    now = datetime.now(JST).replace(microsecond=0)
    entry = post_log.Entry(date=today, slug=m.slug, kind=m.kind, post_uri=uri, at=now)
    post_log.append(config.POSTED_BLUESKY_LOG, entry)
    entries.append(entry)
    return "ok"


def _process_x(m, today, secrets, entries, dry_run, x_client) -> str:
    if post_log.already_posted(entries, today, m.slug):
        return "already"

    result = claude_runner.generate_post(
        kind=m.kind, url=m.url, anniversary_year=m.anniversary_year,
        frontmatter=m.frontmatter, body=m.body,
        agent_name="aoyama-post-writer-x",
        fact_checker_name="aoyama-fact-checker-x",
    )
    if result.status != "ok":
        _notify_generation_failure(secrets.discord_webhook_url, m, result, platform="x")
        return "gen_fail"

    # X weighted length ガード
    wl = x_text.x_weighted_length(result.post_text)
    if wl > x_text.X_LIMIT:
        result = claude_runner.regenerate_shorter(
            kind=m.kind, url=m.url, anniversary_year=m.anniversary_year,
            frontmatter=m.frontmatter, body=m.body,
            previous_text=result.post_text, previous_length=wl,
            target_length=x_text.X_SAFE_LIMIT,
            agent_name="aoyama-post-writer-x",
        )
        if result.status != "ok" or x_text.x_weighted_length(result.post_text) > x_text.X_LIMIT:
            notifier.notify(
                webhook_url=secrets.discord_webhook_url,
                title="[x] 字数超過",
                body=f"slug={m.slug}\nweighted={wl}\ntext:\n{result.post_text}",
            )
            return "length_fail"

    if dry_run:
        print(f"--- X DRY: {m.slug} ({wl} units) ---\n{result.post_text}\n")
        return "dry"

    image_src = _resolve_image(m.slug, m.kind)
    image_to_send = None
    tmp_holder = None
    try:
        if image_src is not None:
            tmp_holder = tempfile.TemporaryDirectory()
            try:
                image_to_send = image_resolver.prepare_for_upload(image_src, tmp_dir=Path(tmp_holder.name))
            except Exception as e:  # noqa: BLE001
                logger.warning("image prepare failed: %s, posting text only", e)
                image_to_send = None
        try:
            resp = x_client.post(text=result.post_text, image_path=image_to_send)
        except XAuthError as e:
            notifier.notify(
                webhook_url=secrets.discord_webhook_url,
                title="[x] 認証失敗",
                body=f"{e}\n~/.config/aoyama-cemetery/x.env を確認してください。",
            )
            return "auth_fail"
        except XRateLimitError as e:
            notifier.notify(
                webhook_url=secrets.discord_webhook_url,
                title="[x] rate limit",
                body=str(e),
            )
            return "rate_limit"
        except XPostError as e:
            notifier.notify(
                webhook_url=secrets.discord_webhook_url,
                title="[x] 投稿失敗",
                body=f"slug={m.slug}\nerror={e}\ntext=\n{result.post_text}",
            )
            return "fail"
    finally:
        if tmp_holder is not None:
            tmp_holder.cleanup()

    now = datetime.now(JST).replace(microsecond=0)
    entry = post_log.Entry(date=today, slug=m.slug, kind=m.kind,
                           post_uri=resp["url"], at=now)
    post_log.append(config.POSTED_X_LOG, entry)
    entries.append(entry)
    return "ok"


def _notify_generation_failure(webhook, m, result, *, platform: str) -> None:
    title = f"[{platform}] LLM critique 2 連続 fail" if result.status == "failed" else f"[{platform}] LLM 生成エラー"
    body = (
        f"slug={m.slug} ({m.kind})\n"
        f"violations: {result.violations}\nlast_text:\n{result.last_text}"
        if result.status == "failed"
        else f"slug={m.slug} ({m.kind})\nerror: {result.error}"
    )
    notifier.notify(webhook_url=webhook, title=title, body=body)


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--today", help="YYYY-MM-DD")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    today = date.fromisoformat(args.today) if args.today else datetime.now(JST).date()
    return run(today=today, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: claude_runner.regenerate_shorter にも agent_name 引数を渡せるよう Task 8 で対応済か確認**

Task 8 Step 5 で `regenerate_shorter` も `agent_name` を受けるはず。grep:

```bash
grep -n "def regenerate_shorter" scripts/daily_bluesky_post/claude_runner.py
```

`agent_name: str = "aoyama-post-writer"` がパラメータにあるか確認、なければ追加。

- [ ] **Step 5: 新規テスト pass 確認**

Run: `PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_orchestrator_x.py -q`
Expected: 7 passed

- [ ] **Step 6: 既存 test_orchestrator.py の調整**

既存テストは旧 `_notify_generation_failure` シグネチャ等を mock していた可能性あり。実行して failures を確認:

```bash
PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_orchestrator.py -q
```

失敗があれば、`_process_bluesky` 内部に同等の挙動を維持しているか確認しつつ既存テストの mock 対象を `orchestrator._process_bluesky` 由来のものに調整。重要: **Bluesky 側の挙動は変えない**。テストは挙動 base で書かれている前提なら通るはず。挙動が変わっていれば実装側を修正(Bluesky 既存 contract を保つ方向)。

- [ ] **Step 7: 全テスト pass 確認**

Run: `PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/ -q`
Expected: 全 pass(目標 81 件超)

- [ ] **Step 8: 旧 `commit_posted_log`(単数)を git_commit.py から削除**

orchestrator は新しい `commit_posted_logs`(複数)に移行済なので、旧関数を削除。

```bash
grep -n "commit_posted_log\b" scripts/daily_bluesky_post/
```

唯一残った定義以外に参照がないことを確認した上で、`git_commit.py` から `def commit_posted_log` を削除。test_git_commit.py の旧テスト(単数版)も該当があれば削除。

- [ ] **Step 9: 再度全テスト pass**

Run: `PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/ -q`

- [ ] **Step 10: Commit**

```bash
git add -A scripts/daily_bluesky_post/
git commit -m "feat(bluesky-post): orchestrator を multi-platform 化、X 並走を実装

match ごとに Bluesky → X の順で独立処理、片方失敗してももう一方は継続。
X_ENABLED=0 で X 全 skip、AuthError/RateLimit 時は当日の以降 X を bypass。
posted log は platform 別ファイルに分離、commit はまとめて 1 回。"
```

---

## Task 11: dry-run E2E 動作確認(`X_ENABLED=0` 既定で安全)

**Files:** なし(動作確認のみ)

- [ ] **Step 1: Bluesky dry-run で既存挙動が壊れていないか確認**

```bash
cd /Users/uchidayousuke/workspace/personal/aoyama-cemetery
unset X_ENABLED
source ~/.config/aoyama-cemetery/bluesky.env
source ~/.config/aoyama-cemetery/discord.env
PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/python -m daily_bluesky_post.orchestrator --dry-run --today 2026-05-14
```

Expected: 大久保利通の Bluesky 投稿文が dry-run で表示される(既存挙動と同じ)。

- [ ] **Step 2: X dry-run はダミー認証で skip されるか確認**

```bash
export X_ENABLED=1
export X_API_KEY=dummy
export X_API_SECRET=dummy
export X_ACCESS_TOKEN=dummy
export X_ACCESS_SECRET=dummy
PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/python -m daily_bluesky_post.orchestrator --dry-run --today 2026-05-14
```

Expected: Bluesky と X の両 dry-run 文が表示される(X は claude_runner が走るので時間かかる、subagent 動作確認も兼ねる)。

注: 本 Step は claude -p Max plan を実消費する。Bluesky bot で文面チューニング済の 2026-05-14 マッチを使う想定。コストが気になる場合は --today 2026-12-31 のような matches=0 になる日付で配線確認のみ行う。

- [ ] **Step 3: Commit**(必要な修正があれば)

修正が出なければ commit 不要。

---

## Phase 2 以降(本 plan のスコープ外、メモ)

- **Phase 2(user 作業)**: X アカウント `@aoyama_cemetery` 等の作成 → Developer Portal で Free tier API key 取得 → `~/.config/aoyama-cemetery/x.env` に値を配置 → `X_ENABLED=1` に設定 → 既存日付で 5 回反復文面チューニング
- **Phase 3**: launchd plist 無変更で次回 8:05 JST 発火を待つ。最初の 1 件で挙動確認、Discord 通知体制確認
- **Phase 4**: 1 ヶ月運用後の振り返り(投稿数 / インプレッション / fact-checker fail 率)

---

## Self-Review チェックリスト

- [x] Spec §1 背景・目的 → Task 全体で達成(独立並走)
- [x] Spec §2 含む・含まない → Task 7 subagent / Task 10 orchestrator が具体化
- [x] Spec §3 アーキテクチャ → Task 10 で実装
- [x] Spec §4.2 モジュール構成 → Task 1-10 でカバー
- [x] Spec §4.3 X 認証情報 → Task 5
- [x] Spec §4.4 / §4.5 subagent 差分 → Task 7
- [x] Spec §4.6 weighted length → Task 3
- [x] Spec §4.7 画像解決 → Task 4
- [x] Spec §4.8 X クライアント → Task 6
- [x] Spec §4.9 orchestrator → Task 10
- [x] Spec §4.10 エラー処理マトリクス → Task 6 / Task 10 で網羅
- [x] Spec §5 テスト方針(25 件) → Task 1 (2) + Task 3 (5) + Task 4 (6) + Task 5 (3) + Task 6 (8) + Task 8 (2) + Task 9 (2) + Task 10 (7) = 35 件追加(目標超過)
- [x] Spec §6 段階リリース → Task 5 で `X_ENABLED` 実装、Phase 2-4 はスコープ外注記
- [x] Spec §7 Bluesky 既存運用への影響 → Task 1 / Task 10 で互換維持確認

Type / signature consistency:
- `XSecrets` 命名 → Task 5 で定義、Task 6 / Task 10 で参照、一致
- `XClient.post` 戻り値 `{"tweet_id", "url"}` → Task 6 定義、Task 10 で `resp["url"]` 参照、一致
- `image_resolver.resolve(slug, *, kind, people_dir, events_dir)` → Task 4 定義、Task 10 `_resolve_image` で wrap、一致
- `image_resolver.prepare_for_upload(src, *, tmp_dir)` → Task 4 定義、Task 10 で参照、一致
- `x_text.x_weighted_length` / `X_LIMIT` / `X_SAFE_LIMIT` → Task 3 定義、Task 10 で参照、一致
- `git_commit.commit_posted_logs(*, date, slug, bluesky_status, x_status)` → Task 9 定義、Task 10 で参照、一致
- `claude_runner.generate_post(..., agent_name=, fact_checker_name=)` → Task 8 定義、Task 10 で参照、一致
- `claude_runner.regenerate_shorter(..., agent_name=)` → Task 8 Step 5 で対応、Task 10 Step 4 で再確認、一致
- `config.POSTED_BLUESKY_LOG` / `POSTED_X_LOG` → Task 1 定義、Task 9 / Task 10 で参照、一致
- `config.Secrets.x` / `x_enabled` → Task 5 定義、Task 10 で参照、一致
