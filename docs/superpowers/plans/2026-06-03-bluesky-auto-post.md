# Bluesky 自動投稿 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (推奨) または superpowers:executing-plans を使って task-by-task に実装する。Steps は checkbox (`- [ ]`) で進捗管理。

**Goal:** 偉人の命日 / events の該当日に毎朝 Bluesky へ自動投稿する仕組みを、ローカル launchd + `claude -p` Max plan 経路で構築する。

**Architecture:** `scripts/daily-bluesky-post/` 配下に Python orchestrator を置き、launchd が 8:05 JST に発火する。orchestrator は match → 既投稿チェック → `claude -p` で post-writer / fact-checker subagent を呼んで投稿文を生成・検証 → Bluesky API へ投稿 → ログ追記 + git commit。失敗時は Discord webhook。

**Tech Stack:**
- Python 3.13 + arm64 venv(L0 知見、admin と同じパターン)
- `atproto` SDK(Bluesky 公式 Python、facet / embed の UTF-16 byte offset 問題を抽象化してくれる)
- `httpx`(OGP 取得 / Discord webhook)
- `beautifulsoup4`(OGP メタタグ抽出)
- `PyYAML`(frontmatter の読み取り専用なので ruamel.yaml ではなく軽量な safe_load を使う)
- `pytest` + `respx`(httpx の HTTP モック)
- subprocess で `claude -p` を起動(L0 の env strip / variadic flag 位置の知見適用)

**Spec:** `docs/superpowers/specs/2026-06-03-bluesky-auto-post-design.md`

**実装サブエージェント分担(subagent-driven-development 時):**
- spec compliance reviewer と code quality reviewer を **別 subagent で 2 段** に分離する(L0 知見)。50 行以内の軽微 task では 1 段でも可。

---

## File Structure

新規 / 変更ファイルの責務マップ:

```
aoyama-cemetery/
├── scripts/daily-bluesky-post/                ← 新規
│   ├── run.sh                                 # launchd entry。arm64 venv 起動 + env source
│   ├── orchestrator.py                        # CLI entry, match→ループ→投稿→ログ→通知
│   ├── match.py                               # date → 人物/events リスト + 上限/並び
│   ├── post_log.py                            # logs/posted.jsonl read/append + idempotency
│   ├── bluesky_client.py                      # atproto SDK ラッパー(session, post, blob)
│   ├── ogp_fetcher.py                         # サイトから og:title / desc / image を取得
│   ├── claude_runner.py                       # claude -p subprocess(env strip 込み)
│   ├── notifier.py                            # Discord webhook 送信
│   ├── git_commit.py                          # logs/posted.jsonl の単独 commit
│   ├── config.py                              # 環境変数読み込み + パス定数
│   ├── requirements.txt
│   ├── README.md
│   └── tests/
│       ├── conftest.py
│       ├── fixtures/
│       │   ├── person_okubo.md
│       │   ├── person_no_portrait.md
│       │   ├── event_with_persons.md
│       │   └── event_empty_persons.md
│       ├── test_match.py
│       ├── test_post_log.py
│       ├── test_bluesky_client.py
│       ├── test_ogp_fetcher.py
│       ├── test_claude_runner.py
│       ├── test_notifier.py
│       └── test_orchestrator.py
├── .claude/agents/                            ← 新規 2 ファイル
│   ├── aoyama-post-writer.md
│   └── aoyama-fact-checker.md
├── logs/                                      ← 新規ディレクトリ + 空ファイル
│   ├── posted.jsonl
│   ├── errors.jsonl
│   └── .gitkeep
├── src/pages/events/[slug].astro              ← 1 行修正(BaseLayout に ogImage 追加)
├── ~/Library/LaunchAgents/jp.aoyama-cemetery.daily-post.plist  ← Phase 3 で手動配置
└── ~/.config/aoyama-cemetery/                 ← Phase 2 で手動配置
    ├── bluesky.env
    └── discord.env
```

責務分離の方針:
- I/O 境界(Bluesky API / OGP HTTP / Discord HTTP / claude subprocess / git / file system)をすべて個別モジュールに分離 → orchestrator はそれらを mock したテストで全シナリオを網羅できる
- match.py は純関数(入力 = date + content dir, 出力 = list[Match])
- post_log.py も純粋に JSONL の read/append のみ、git commit は別モジュール

---

## Task 1: プロジェクトスケルトン作成

**Files:**
- Create: `scripts/daily-bluesky-post/requirements.txt`
- Create: `scripts/daily-bluesky-post/run.sh`
- Create: `scripts/daily-bluesky-post/README.md`
- Create: `scripts/daily-bluesky-post/__init__.py`(空)
- Create: `scripts/daily-bluesky-post/tests/__init__.py`(空)
- Create: `logs/.gitkeep`
- Modify: `.gitignore`(logs/posted.jsonl は track、`scripts/daily-bluesky-post/.venv/` は ignore)

- [ ] **Step 1: `scripts/daily-bluesky-post/requirements.txt` を作る**

```
atproto>=0.0.50
httpx>=0.27
beautifulsoup4>=4.12
PyYAML>=6.0
pytest>=8.0
respx>=0.21
pytest-mock>=3.12
```

- [ ] **Step 2: `scripts/daily-bluesky-post/run.sh` を作る**(admin/run.sh をモデル)

```bash
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
  arch -arm64 /usr/bin/python3 -m venv "$VENV"
  arch -arm64 "$VENV/bin/pip" install --upgrade pip
  arch -arm64 "$VENV/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
fi

ACTUAL_ARCH=$(arch -arm64 "$VENV/bin/python3" -c 'import platform; print(platform.machine())')
if [[ "$ACTUAL_ARCH" != "arm64" ]]; then
  echo "❌ venv が arm64 ではありません: $ACTUAL_ARCH" >&2
  echo "   rm -rf $VENV && $0" >&2
  exit 1
fi

# シークレット読み込み(なければ警告のみ、CI / dry-run 用)
if [[ -f "$CONFIG_DIR/bluesky.env" ]]; then
  set -a; source "$CONFIG_DIR/bluesky.env"; set +a
fi
if [[ -f "$CONFIG_DIR/discord.env" ]]; then
  set -a; source "$CONFIG_DIR/discord.env"; set +a
fi

# L0 知見: claude -p 子プロセスに API key を継承させない
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN

exec arch -arm64 "$VENV/bin/python" -m daily_bluesky_post.orchestrator "$@"
```

(`exec` の `-m` 形式で動かすため、scripts/daily-bluesky-post/ を Python パッケージとして扱う。`PYTHONPATH=scripts` で解決させる構成は次 Step で。)

- [ ] **Step 3: `chmod +x scripts/daily-bluesky-post/run.sh`**

```bash
chmod +x scripts/daily-bluesky-post/run.sh
```

- [ ] **Step 4: パッケージ名のための symlink / 構造を整える**

`scripts/daily-bluesky-post/` ディレクトリ名はハイフンが入って `import` できないので、`scripts/daily_bluesky_post/` にリネーム。run.sh / requirements.txt / README.md は中に配置のままで OK。File Structure 表のパスもすべて `scripts/daily_bluesky_post/` に読み替える(以降の Task でもこのパスを使う)。

```bash
mv scripts/daily-bluesky-post scripts/daily_bluesky_post
```

run.sh の最後の行を更新:

```bash
# PYTHONPATH=scripts を渡して daily_bluesky_post パッケージを認識させる
exec arch -arm64 \
  env PYTHONPATH="$PROJECT_ROOT/scripts" \
  "$VENV/bin/python" -m daily_bluesky_post.orchestrator "$@"
```

- [ ] **Step 5: `logs/.gitkeep` と空の JSONL を作る**

```bash
mkdir -p logs
touch logs/.gitkeep logs/posted.jsonl logs/errors.jsonl
```

- [ ] **Step 6: `.gitignore` を更新**

`.gitignore` に追記:

```
scripts/daily_bluesky_post/.venv/
scripts/daily_bluesky_post/__pycache__/
scripts/daily_bluesky_post/**/__pycache__/
scripts/daily_bluesky_post/.pytest_cache/
```

`logs/posted.jsonl` と `logs/errors.jsonl` は **commit する** ので ignore しない。

- [ ] **Step 7: README.md(scripts/daily_bluesky_post/README.md)を作る**

最小限のセットアップ + 使い方:

```markdown
# 青山霊園 Bluesky 自動投稿

毎朝 8:05 JST に launchd が発火し、本日が命日の偉人・該当日 events を Bluesky に投稿する。

## セットアップ

1. シークレット配置:
   ```
   mkdir -p ~/.config/aoyama-cemetery && chmod 700 ~/.config/aoyama-cemetery
   cat > ~/.config/aoyama-cemetery/bluesky.env <<'EOF'
   BLUESKY_HANDLE=aoyama-cemetery.bsky.social
   BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
   EOF
   chmod 600 ~/.config/aoyama-cemetery/bluesky.env
   ```
2. dry-run で動作確認:
   ```
   scripts/daily_bluesky_post/run.sh --dry-run --today 2026-05-14
   ```
3. launchd 登録: `infra/jp.aoyama-cemetery.daily-post.plist` を `~/Library/LaunchAgents/` にコピーして `launchctl load`

## テスト

```
scripts/daily_bluesky_post/run.sh --self-test       # 内部で pytest を起動
# あるいは:
arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/
```

仕様: `docs/superpowers/specs/2026-06-03-bluesky-auto-post-design.md`
```

- [ ] **Step 8: 初回 commit**

```bash
git add scripts/daily_bluesky_post .gitignore logs
git commit -m "feat(bluesky-post): プロジェクトスケルトン + venv runner + logs ディレクトリ"
```

---

## Task 2: config.py(環境変数とパス定数)

**Files:**
- Create: `scripts/daily_bluesky_post/config.py`
- Create: `scripts/daily_bluesky_post/tests/test_config.py`

- [ ] **Step 1: 失敗テストを書く**

`scripts/daily_bluesky_post/tests/test_config.py`:

```python
import os
import pytest
from pathlib import Path
from daily_bluesky_post import config


def test_project_root_points_to_repo():
    # repo root に astro.config.mjs があるはず
    assert (config.PROJECT_ROOT / "astro.config.mjs").is_file()


def test_site_url_constant():
    assert config.SITE_URL == "https://aoyama-cemetery.pages.dev"


def test_posted_log_path():
    assert config.POSTED_LOG == config.PROJECT_ROOT / "logs" / "posted.jsonl"


def test_load_secrets_from_env(monkeypatch):
    monkeypatch.setenv("BLUESKY_HANDLE", "test.bsky.social")
    monkeypatch.setenv("BLUESKY_APP_PASSWORD", "abcd-efgh-ijkl-mnop")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/x")
    s = config.load_secrets()
    assert s.bluesky_handle == "test.bsky.social"
    assert s.bluesky_app_password == "abcd-efgh-ijkl-mnop"
    assert s.discord_webhook_url == "https://discord.com/api/webhooks/x"


def test_load_secrets_missing_required(monkeypatch):
    monkeypatch.delenv("BLUESKY_HANDLE", raising=False)
    monkeypatch.delenv("BLUESKY_APP_PASSWORD", raising=False)
    with pytest.raises(config.MissingSecretError):
        config.load_secrets()
```

- [ ] **Step 2: テストを fail させる**

```bash
PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_config.py -v
```

Expected: `ModuleNotFoundError` または config 属性なしで fail。

- [ ] **Step 3: `config.py` を実装**

```python
"""環境変数とパス定数。

scripts/daily_bluesky_post/run.sh が ~/.config/aoyama-cemetery/*.env を
source した上で本プロセスを起動する想定。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# scripts/daily_bluesky_post/config.py から見て 2 階層上が repo root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SITE_URL = "https://aoyama-cemetery.pages.dev"

PEOPLE_DIR = PROJECT_ROOT / "src" / "content" / "people"
EVENTS_DIR = PROJECT_ROOT / "src" / "content" / "events"
POSTED_LOG = PROJECT_ROOT / "logs" / "posted.jsonl"
ERRORS_LOG = PROJECT_ROOT / "logs" / "errors.jsonl"

MAX_POSTS_PER_DAY = 5


class MissingSecretError(RuntimeError):
    pass


@dataclass(frozen=True)
class Secrets:
    bluesky_handle: str
    bluesky_app_password: str
    discord_webhook_url: str | None  # 通知無しでも動作はする


def load_secrets() -> Secrets:
    handle = os.environ.get("BLUESKY_HANDLE")
    pw = os.environ.get("BLUESKY_APP_PASSWORD")
    if not handle or not pw:
        raise MissingSecretError(
            "BLUESKY_HANDLE / BLUESKY_APP_PASSWORD が未設定です。"
            " ~/.config/aoyama-cemetery/bluesky.env を確認してください。"
        )
    return Secrets(
        bluesky_handle=handle,
        bluesky_app_password=pw,
        discord_webhook_url=os.environ.get("DISCORD_WEBHOOK_URL"),
    )
```

- [ ] **Step 4: テスト pass を確認**

```bash
PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_config.py -v
```

Expected: 5 passed.

- [ ] **Step 5: commit**

```bash
git add scripts/daily_bluesky_post/config.py scripts/daily_bluesky_post/tests/test_config.py
git commit -m "feat(bluesky-post): config モジュール(環境変数とパス定数)"
```

---

## Task 3: post_log.py(投稿ログと idempotency)

**Files:**
- Create: `scripts/daily_bluesky_post/post_log.py`
- Create: `scripts/daily_bluesky_post/tests/test_post_log.py`

- [ ] **Step 1: 失敗テストを書く**

`scripts/daily_bluesky_post/tests/test_post_log.py`:

```python
import json
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
import pytest
from daily_bluesky_post import post_log

JST = timezone(timedelta(hours=9))


@pytest.fixture
def empty_log(tmp_path):
    p = tmp_path / "posted.jsonl"
    p.touch()
    return p


def test_load_empty(empty_log):
    assert post_log.load(empty_log) == []


def test_load_skips_blank_lines(empty_log):
    empty_log.write_text('{"date":"2026-05-14","slug":"okubo-toshimichi","kind":"person","post_uri":"at://x","at":"2026-05-14T08:05:23+09:00"}\n\n')
    entries = post_log.load(empty_log)
    assert len(entries) == 1
    assert entries[0].slug == "okubo-toshimichi"


def test_already_posted_true_when_match(empty_log):
    empty_log.write_text('{"date":"2026-05-14","slug":"okubo-toshimichi","kind":"person","post_uri":"at://x","at":"2026-05-14T08:05:23+09:00"}\n')
    entries = post_log.load(empty_log)
    assert post_log.already_posted(entries, date(2026, 5, 14), "okubo-toshimichi") is True


def test_already_posted_false_when_different_date(empty_log):
    empty_log.write_text('{"date":"2026-05-14","slug":"okubo-toshimichi","kind":"person","post_uri":"at://x","at":"2026-05-14T08:05:23+09:00"}\n')
    entries = post_log.load(empty_log)
    assert post_log.already_posted(entries, date(2026, 5, 15), "okubo-toshimichi") is False


def test_append_writes_jsonl_line(empty_log):
    e = post_log.Entry(
        date=date(2026, 5, 14),
        slug="okubo-toshimichi",
        kind="person",
        post_uri="at://did:plc:xxx/app.bsky.feed.post/abc",
        at=datetime(2026, 5, 14, 8, 5, 23, tzinfo=JST),
    )
    post_log.append(empty_log, e)
    lines = empty_log.read_text().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["slug"] == "okubo-toshimichi"
    assert parsed["date"] == "2026-05-14"
    assert parsed["at"] == "2026-05-14T08:05:23+09:00"


def test_append_uses_flock_for_concurrency(empty_log):
    # 同じファイルに 10 件並列 append しても全部残ること
    import threading

    def writer(i):
        post_log.append(empty_log, post_log.Entry(
            date=date(2026, 5, 14),
            slug=f"slug-{i}",
            kind="person",
            post_uri=f"at://x/{i}",
            at=datetime(2026, 5, 14, 8, 5, i, tzinfo=JST),
        ))

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert len(empty_log.read_text().splitlines()) == 10
```

- [ ] **Step 2: テストを fail させる**

```bash
PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_post_log.py -v
```

Expected: ModuleNotFoundError or AttributeError.

- [ ] **Step 3: `post_log.py` を実装**

```python
"""投稿ログ(idempotency 用)。

logs/posted.jsonl に 1 投稿 = 1 行 JSON で append。
launchd の catch-up や手動再実行で同じ (date, slug) を投稿しないために load して check する。
"""
from __future__ import annotations

import fcntl
import json
from dataclasses import dataclass, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Literal


Kind = Literal["person", "event"]


@dataclass(frozen=True)
class Entry:
    date: date
    slug: str
    kind: Kind
    post_uri: str
    at: datetime  # JST aware

    def to_json_line(self) -> str:
        return json.dumps({
            "date": self.date.isoformat(),
            "slug": self.slug,
            "kind": self.kind,
            "post_uri": self.post_uri,
            "at": self.at.isoformat(timespec="seconds"),
        }, ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: dict) -> "Entry":
        return cls(
            date=date.fromisoformat(d["date"]),
            slug=d["slug"],
            kind=d["kind"],
            post_uri=d["post_uri"],
            at=datetime.fromisoformat(d["at"]),
        )


def load(path: Path) -> list[Entry]:
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        entries.append(Entry.from_dict(json.loads(line)))
    return entries


def already_posted(entries: Iterable[Entry], d: date, slug: str) -> bool:
    return any(e.date == d and e.slug == slug for e in entries)


def append(path: Path, entry: Entry) -> None:
    """ファイルロックを取って 1 行 append。

    launchd は通常 singleton 起動だが、手動実行と重なる可能性を排除するため flock を使う。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    line = entry.to_json_line() + "\n"
    with open(path, "ab") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.write(line.encode("utf-8"))
            f.flush()
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

- [ ] **Step 4: テスト pass を確認**

```bash
PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_post_log.py -v
```

Expected: 6 passed.

- [ ] **Step 5: commit**

```bash
git add scripts/daily_bluesky_post/post_log.py scripts/daily_bluesky_post/tests/test_post_log.py
git commit -m "feat(bluesky-post): post_log(JSONL + flock + idempotency 判定)"
```

---

## Task 4: match.py(命日マッチ + events マッチ + 上限・並び)

**Files:**
- Create: `scripts/daily_bluesky_post/match.py`
- Create: `scripts/daily_bluesky_post/tests/fixtures/` 配下 4 ファイル(人物 / event 各 2 件)
- Create: `scripts/daily_bluesky_post/tests/test_match.py`

- [ ] **Step 1: フィクスチャ作成**

`scripts/daily_bluesky_post/tests/fixtures/person_okubo.md`:

```markdown
---
name: 大久保 利通
nameKana: おおくぼ としみち
birthDate: "1830-09-26"
deathDate: "1878-05-14"
era: [江戸, 明治]
category: 政治家
graveSection: 1種イ2号15側
shortDescription: 明治維新三傑の一人。初代内務卿として近代日本の基礎を築いた薩摩出身の政治家。
deathPlace: "東京・紀尾井坂(暗殺)"
portrait: ../../assets/portraits/okubo-toshimichi.jpg
---

本文
```

`scripts/daily_bluesky_post/tests/fixtures/person_no_portrait.md`:

```markdown
---
name: 星 新一
nameKana: ほし しんいち
birthDate: "1926-09-06"
deathDate: "1997-12-30"
era: [昭和, 平成]
category: 文学者
shortDescription: ショートショート小説の名手。
---

本文
```

`scripts/daily_bluesky_post/tests/fixtures/event_with_persons.md`:

```markdown
---
title: 桜田門外の変
date: "1860-03-24"
summary: 大老井伊直弼が江戸城桜田門外で水戸浪士に襲撃され暗殺された事件。
personSlugs:
  - arimura-jizaemon
category: 事件
heroImage: ../../assets/event-images/1860-03-24-sakuradamongai.jpg
---

本文
```

`scripts/daily_bluesky_post/tests/fixtures/event_empty_persons.md`:

```markdown
---
title: ペリー来航
date: "1853-07-08"
summary: アメリカ東インド艦隊司令長官マシュー・ペリーが浦賀に来航。
category: 事件
---

本文
```

- [ ] **Step 2: テストを書く**

`scripts/daily_bluesky_post/tests/test_match.py`:

```python
import shutil
from datetime import date
from pathlib import Path
import pytest
from daily_bluesky_post import match

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def content_dirs(tmp_path):
    people = tmp_path / "people"
    events = tmp_path / "events"
    people.mkdir(); events.mkdir()
    shutil.copy(FIXTURES / "person_okubo.md", people / "okubo-toshimichi.md")
    shutil.copy(FIXTURES / "person_no_portrait.md", people / "hoshi-shinichi.md")
    shutil.copy(FIXTURES / "event_with_persons.md", events / "1860-03-24-sakuradamongai.md")
    shutil.copy(FIXTURES / "event_empty_persons.md", events / "1853-07-08-perry-raiko.md")
    return people, events


def test_match_person_by_death_anniversary(content_dirs):
    people, events = content_dirs
    matches = match.match_today(date(2026, 5, 14), people, events)
    slugs = [m.slug for m in matches]
    assert "okubo-toshimichi" in slugs


def test_match_event_by_anniversary(content_dirs):
    people, events = content_dirs
    matches = match.match_today(date(2026, 3, 24), people, events)
    slugs = [m.slug for m in matches]
    assert "1860-03-24-sakuradamongai" in slugs


def test_event_with_empty_personslugs_is_excluded(content_dirs):
    """ペリー来航(personSlugs 未設定 = 空)は投稿対象外"""
    people, events = content_dirs
    matches = match.match_today(date(2026, 7, 8), people, events)
    assert matches == []


def test_no_match_returns_empty(content_dirs):
    people, events = content_dirs
    matches = match.match_today(date(2026, 1, 1), people, events)
    assert matches == []


def test_match_includes_url_and_frontmatter(content_dirs):
    people, events = content_dirs
    matches = match.match_today(date(2026, 5, 14), people, events)
    m = matches[0]
    assert m.kind == "person"
    assert m.url == "https://aoyama-cemetery.pages.dev/people/okubo-toshimichi"
    assert m.frontmatter["name"] == "大久保 利通"


def test_match_caps_to_max_per_day(content_dirs, tmp_path):
    """6 人同じ命日なら 5 件まで"""
    people, events = content_dirs
    template = (FIXTURES / "person_okubo.md").read_text()
    for i in range(6):
        # 全員 5/14 没にする
        (people / f"x{i}.md").write_text(
            template.replace("大久保 利通", f"テスト{i}")
        )
    matches = match.match_today(date(2026, 5, 14), people, events)
    assert len(matches) == 5


def test_event_prioritized_over_person_in_tie(content_dirs, tmp_path):
    """同周年数なら event > person 優先で並ぶ"""
    people, events = content_dirs
    matches = match.match_today(date(2026, 3, 24), people, events)
    # event だけ存在する日なので 1 件、event 優先の確認は別の混在テストで
    assert matches[0].kind == "event"
```

- [ ] **Step 3: テストを fail させる**

```bash
PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_match.py -v
```

Expected: ModuleNotFoundError。

- [ ] **Step 4: `match.py` を実装**

```python
"""今日のマッチ判定。

人物: deathDate の月日が today の月日と一致
events: date の月日が today の月日と一致 + personSlugs が非空

並び: 周年数(大きい方)→ event 優先 → slug 辞書順
上限: MAX_POSTS_PER_DAY 件
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Literal

import yaml

from daily_bluesky_post.config import MAX_POSTS_PER_DAY, SITE_URL

Kind = Literal["person", "event"]


@dataclass
class Match:
    kind: Kind
    slug: str
    frontmatter: dict[str, Any]
    url: str
    anniversary_year: int  # 周年数(today.year - origin_year)


def _parse_frontmatter(path: Path) -> dict[str, Any] | None:
    """`---` で囲まれた YAML frontmatter を返す。なければ None。"""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    return yaml.safe_load(parts[1])


def _to_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def match_today(today: date, people_dir: Path, events_dir: Path) -> list[Match]:
    matches: list[Match] = []

    # 人物: deathDate 月日一致
    for path in sorted(people_dir.glob("*.md")):
        fm = _parse_frontmatter(path)
        if not fm:
            continue
        d = _to_date(fm.get("deathDate"))
        if d and d.month == today.month and d.day == today.day:
            matches.append(Match(
                kind="person",
                slug=path.stem,
                frontmatter=fm,
                url=f"{SITE_URL}/people/{path.stem}",
                anniversary_year=today.year - d.year,
            ))

    # events: date 月日一致 + personSlugs 非空
    for path in sorted(events_dir.glob("*.md")):
        fm = _parse_frontmatter(path)
        if not fm:
            continue
        if not fm.get("personSlugs"):
            continue
        d = _to_date(fm.get("date"))
        if d and d.month == today.month and d.day == today.day:
            matches.append(Match(
                kind="event",
                slug=path.stem,
                frontmatter=fm,
                url=f"{SITE_URL}/events/{path.stem}",
                anniversary_year=today.year - d.year,
            ))

    # 並び: 周年大きい順 → event 優先 → slug 辞書順
    matches.sort(key=lambda m: (
        -m.anniversary_year,
        0 if m.kind == "event" else 1,
        m.slug,
    ))
    return matches[:MAX_POSTS_PER_DAY]
```

- [ ] **Step 5: テスト pass を確認**

```bash
PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_match.py -v
```

Expected: 7 passed.

- [ ] **Step 6: 本物データで sanity check**(read-only、commit には影響しない)

```bash
PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/python -c "
from datetime import date
from pathlib import Path
from daily_bluesky_post import match, config
matches = match.match_today(date(2026, 5, 14), config.PEOPLE_DIR, config.EVENTS_DIR)
for m in matches:
    print(m.kind, m.slug, m.anniversary_year, m.url)
"
```

Expected: `person okubo-toshimichi 148 https://aoyama-cemetery.pages.dev/people/okubo-toshimichi`(他にも 5/14 没がいれば併記)。

- [ ] **Step 7: commit**

```bash
git add scripts/daily_bluesky_post/match.py scripts/daily_bluesky_post/tests/test_match.py scripts/daily_bluesky_post/tests/fixtures/
git commit -m "feat(bluesky-post): match(命日/事件日マッチ + 上限・並び)"
```

---

## Task 5: ogp_fetcher.py(サイトから OGP メタを取得)

**Files:**
- Create: `scripts/daily_bluesky_post/ogp_fetcher.py`
- Create: `scripts/daily_bluesky_post/tests/test_ogp_fetcher.py`

- [ ] **Step 1: 失敗テストを書く(respx で httpx をモック)**

`scripts/daily_bluesky_post/tests/test_ogp_fetcher.py`:

```python
import pytest
import respx
import httpx
from daily_bluesky_post import ogp_fetcher

HTML_WITH_OG = """
<!doctype html>
<html><head>
<meta property="og:title" content="大久保 利通 | 青山霊園 偉人録">
<meta property="og:description" content="明治維新三傑のひとり。">
<meta property="og:image" content="https://aoyama-cemetery.pages.dev/_astro/okubo.jpg">
</head><body></body></html>
"""

HTML_NO_IMAGE = """
<!doctype html>
<html><head>
<meta property="og:title" content="星 新一">
<meta property="og:description" content="ショートショートの名手。">
</head></html>
"""


@respx.mock
def test_fetch_returns_all_three_fields():
    respx.get("https://aoyama-cemetery.pages.dev/people/okubo-toshimichi").mock(
        return_value=httpx.Response(200, text=HTML_WITH_OG)
    )
    ogp = ogp_fetcher.fetch("https://aoyama-cemetery.pages.dev/people/okubo-toshimichi")
    assert ogp.title == "大久保 利通 | 青山霊園 偉人録"
    assert ogp.description == "明治維新三傑のひとり。"
    assert ogp.image_url == "https://aoyama-cemetery.pages.dev/_astro/okubo.jpg"


@respx.mock
def test_fetch_handles_missing_image():
    respx.get("https://aoyama-cemetery.pages.dev/people/hoshi-shinichi").mock(
        return_value=httpx.Response(200, text=HTML_NO_IMAGE)
    )
    ogp = ogp_fetcher.fetch("https://aoyama-cemetery.pages.dev/people/hoshi-shinichi")
    assert ogp.image_url is None
    assert ogp.title == "星 新一"


@respx.mock
def test_fetch_returns_empty_on_404():
    respx.get("https://aoyama-cemetery.pages.dev/people/missing").mock(
        return_value=httpx.Response(404)
    )
    ogp = ogp_fetcher.fetch("https://aoyama-cemetery.pages.dev/people/missing")
    assert ogp.title is None
    assert ogp.description is None
    assert ogp.image_url is None


@respx.mock
def test_download_image_bytes():
    respx.get("https://aoyama-cemetery.pages.dev/_astro/okubo.jpg").mock(
        return_value=httpx.Response(200, content=b"\xff\xd8\xff\xe0fake-jpeg")
    )
    data, mime = ogp_fetcher.download_image("https://aoyama-cemetery.pages.dev/_astro/okubo.jpg")
    assert data.startswith(b"\xff\xd8")
    assert mime == "image/jpeg"
```

- [ ] **Step 2: テストを fail させる**

```bash
PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_ogp_fetcher.py -v
```

- [ ] **Step 3: `ogp_fetcher.py` を実装**

```python
"""偉人 / event ページから OGP メタを抜き取る。

Bluesky の link card 用に title / description / og:image を返す。
画像は別関数で blob をダウンロードする(blob upload は bluesky_client 側で実施)。
"""
from __future__ import annotations

import mimetypes
from dataclasses import dataclass
import httpx
from bs4 import BeautifulSoup

USER_AGENT = "aoyama-cemetery-bluesky-bot/1.0 (+https://aoyama-cemetery.pages.dev)"
TIMEOUT = httpx.Timeout(15.0, connect=5.0)


@dataclass
class OGP:
    title: str | None
    description: str | None
    image_url: str | None


def fetch(url: str) -> OGP:
    try:
        resp = httpx.get(url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
    except httpx.HTTPError:
        return OGP(None, None, None)
    if resp.status_code != 200:
        return OGP(None, None, None)
    return _parse(resp.text)


def _parse(html: str) -> OGP:
    soup = BeautifulSoup(html, "html.parser")
    def meta(prop: str) -> str | None:
        tag = soup.find("meta", property=prop)
        return tag.get("content") if tag else None
    return OGP(
        title=meta("og:title"),
        description=meta("og:description"),
        image_url=meta("og:image"),
    )


def download_image(url: str) -> tuple[bytes, str]:
    """画像 URL から bytes と推定 MIME を返す。"""
    resp = httpx.get(url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
    resp.raise_for_status()
    mime = resp.headers.get("content-type", "").split(";")[0].strip()
    if not mime:
        mime = mimetypes.guess_type(url)[0] or "application/octet-stream"
    return resp.content, mime
```

- [ ] **Step 4: テスト pass を確認**

```bash
PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_ogp_fetcher.py -v
```

Expected: 4 passed.

- [ ] **Step 5: commit**

```bash
git add scripts/daily_bluesky_post/ogp_fetcher.py scripts/daily_bluesky_post/tests/test_ogp_fetcher.py
git commit -m "feat(bluesky-post): ogp_fetcher(httpx + BeautifulSoup で OGP メタ抽出)"
```

---

## Task 6: bluesky_client.py(atproto SDK ラッパー)

**Files:**
- Create: `scripts/daily_bluesky_post/bluesky_client.py`
- Create: `scripts/daily_bluesky_post/tests/test_bluesky_client.py`

**設計メモ**: atproto SDK の `Client.login(handle, password)` でセッション、`Client.send_post(text, embed=...)` で投稿、`Client.upload_blob(data)` で画像 blob。SDK は facet を `client.utils.TextBuilder` で組める。本ラッパーは SDK の細かい型を上位に漏らさず、`post(text, link_url, ogp)` 1 メソッドで完結させる。

- [ ] **Step 1: 失敗テストを書く**

`scripts/daily_bluesky_post/tests/test_bluesky_client.py`:

```python
from unittest.mock import MagicMock, patch
import pytest
from daily_bluesky_post import bluesky_client
from daily_bluesky_post.ogp_fetcher import OGP


def _fake_atproto_client():
    """atproto.Client のインスタンスを模した MagicMock"""
    c = MagicMock()
    c.login.return_value = None
    blob_ref = MagicMock()
    c.upload_blob.return_value = MagicMock(blob=blob_ref)
    post_record = MagicMock()
    post_record.uri = "at://did:plc:xxx/app.bsky.feed.post/abc"
    c.send_post.return_value = post_record
    return c, blob_ref


def test_post_with_image_uploads_blob_and_creates_post(monkeypatch):
    fake, blob_ref = _fake_atproto_client()
    monkeypatch.setattr(bluesky_client, "_make_client", lambda: fake)

    # download_image を mock
    monkeypatch.setattr(
        "daily_bluesky_post.bluesky_client.ogp_fetcher.download_image",
        lambda url: (b"\xff\xd8fake", "image/jpeg"),
    )

    ogp = OGP(title="大久保 利通", description="維新三傑のひとり", image_url="https://x/y.jpg")
    uri = bluesky_client.post(
        handle="aoyama-cemetery.bsky.social",
        password="xxxx-xxxx-xxxx-xxxx",
        text="【本日の命日】大久保 利通\nhttps://aoyama-cemetery.pages.dev/people/okubo-toshimichi",
        link_url="https://aoyama-cemetery.pages.dev/people/okubo-toshimichi",
        ogp=ogp,
    )
    assert uri == "at://did:plc:xxx/app.bsky.feed.post/abc"
    fake.login.assert_called_once_with("aoyama-cemetery.bsky.social", "xxxx-xxxx-xxxx-xxxx")
    fake.upload_blob.assert_called_once()
    fake.send_post.assert_called_once()
    # send_post に渡された embed が external link card になっていること
    kwargs = fake.send_post.call_args.kwargs
    assert kwargs["embed"] is not None


def test_post_without_image_skips_blob_upload(monkeypatch):
    fake, _ = _fake_atproto_client()
    monkeypatch.setattr(bluesky_client, "_make_client", lambda: fake)
    ogp = OGP(title="星 新一", description="ショートショート", image_url=None)
    bluesky_client.post(
        handle="a.bsky.social", password="x",
        text="...", link_url="https://x/y", ogp=ogp,
    )
    fake.upload_blob.assert_not_called()
    fake.send_post.assert_called_once()


def test_post_retries_on_5xx(monkeypatch):
    """5xx で 1 回リトライ → 成功"""
    from atproto_client.exceptions import NetworkError
    fake, _ = _fake_atproto_client()
    # 1 回目 NetworkError、2 回目 success
    post_record = MagicMock(uri="at://retry")
    fake.send_post.side_effect = [NetworkError(MagicMock(status_code=503)), post_record]
    monkeypatch.setattr(bluesky_client, "_make_client", lambda: fake)
    monkeypatch.setattr("time.sleep", lambda s: None)  # 待機を skip

    ogp = OGP(None, None, None)
    uri = bluesky_client.post(
        handle="a", password="x", text="t", link_url="https://x", ogp=ogp,
    )
    assert uri == "at://retry"
    assert fake.send_post.call_count == 2


def test_post_raises_on_401(monkeypatch):
    from atproto_client.exceptions import UnauthorizedError
    fake, _ = _fake_atproto_client()
    fake.login.side_effect = UnauthorizedError(MagicMock(status_code=401))
    monkeypatch.setattr(bluesky_client, "_make_client", lambda: fake)
    with pytest.raises(bluesky_client.AuthError):
        bluesky_client.post(
            handle="a", password="bad", text="t", link_url="https://x", ogp=OGP(None,None,None),
        )
```

- [ ] **Step 2: テストを fail させる**

```bash
PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_bluesky_client.py -v
```

- [ ] **Step 3: `bluesky_client.py` を実装**

```python
"""atproto SDK の薄いラッパー。

upper layer には post(handle, password, text, link_url, ogp) → post_uri だけを公開する。
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from atproto import Client, models
from atproto_client.exceptions import NetworkError, UnauthorizedError

from daily_bluesky_post import ogp_fetcher
from daily_bluesky_post.ogp_fetcher import OGP


RETRY_WAIT_SEC = 60


class AuthError(RuntimeError):
    pass


def _make_client() -> Client:
    return Client()


def post(*, handle: str, password: str, text: str, link_url: str, ogp: OGP) -> str:
    """投稿して post URI を返す。

    - 401 → AuthError(リトライしない)
    - 5xx / network → 1 回だけ 60 秒待ってリトライ
    - 画像なし(ogp.image_url=None)なら blob upload を省略、external link card には title/description のみ
    """
    client = _make_client()
    try:
        client.login(handle, password)
    except UnauthorizedError as e:
        raise AuthError(f"Bluesky 認証失敗: {e}") from e

    embed = _build_external_embed(client, link_url, ogp)

    for attempt in range(2):
        try:
            record = client.send_post(text=text, embed=embed)
            return record.uri
        except NetworkError as e:
            if attempt == 0:
                time.sleep(RETRY_WAIT_SEC)
                continue
            raise


def _build_external_embed(client: Client, link_url: str, ogp: OGP):
    thumb = None
    if ogp.image_url:
        try:
            data, _mime = ogp_fetcher.download_image(ogp.image_url)
            uploaded = client.upload_blob(data)
            thumb = uploaded.blob
        except Exception:
            # 画像取得失敗時は thumb なしで投稿継続
            thumb = None

    external = models.AppBskyEmbedExternal.External(
        uri=link_url,
        title=ogp.title or "",
        description=ogp.description or "",
        thumb=thumb,
    )
    return models.AppBskyEmbedExternal.Main(external=external)
```

- [ ] **Step 4: テスト pass を確認**

```bash
PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_bluesky_client.py -v
```

Expected: 4 passed.

注意: atproto SDK の例外クラス名(NetworkError / UnauthorizedError)が SDK バージョンで異なる可能性。実装時に `pip install atproto` 後 `python -c "import atproto_client.exceptions; print(dir(...))"` で実在クラスを確認、必要なら import 名を調整。

- [ ] **Step 5: commit**

```bash
git add scripts/daily_bluesky_post/bluesky_client.py scripts/daily_bluesky_post/tests/test_bluesky_client.py
git commit -m "feat(bluesky-post): bluesky_client(atproto SDK ラッパー + external embed + 401/5xx ハンドリング)"
```

---

## Task 7: notifier.py(Discord webhook)

**Files:**
- Create: `scripts/daily_bluesky_post/notifier.py`
- Create: `scripts/daily_bluesky_post/tests/test_notifier.py`

- [ ] **Step 1: 失敗テストを書く**

```python
import json
import respx
import httpx
from daily_bluesky_post import notifier


@respx.mock
def test_notify_sends_post_to_webhook():
    route = respx.post("https://discord.com/api/webhooks/abc").mock(
        return_value=httpx.Response(204)
    )
    notifier.notify(
        webhook_url="https://discord.com/api/webhooks/abc",
        title="投稿失敗",
        body="okubo-toshimichi: critique 2 連続 fail",
    )
    assert route.called
    sent = json.loads(route.calls[0].request.content)
    assert "投稿失敗" in sent["content"]
    assert "okubo-toshimichi" in sent["content"]


def test_notify_no_op_when_webhook_url_none(caplog):
    # webhook_url=None なら HTTP リクエストを送らずに何もしない
    notifier.notify(webhook_url=None, title="t", body="b")
    # 例外を raise しない、HTTP も飛ばないことを暗黙確認(respx 未使用 = 飛んだら ConnectError)


@respx.mock
def test_notify_swallows_http_error():
    """Discord 側 5xx でも本体処理は止めない"""
    respx.post("https://discord.com/api/webhooks/abc").mock(
        return_value=httpx.Response(500)
    )
    # 例外を raise しないこと
    notifier.notify(webhook_url="https://discord.com/api/webhooks/abc", title="t", body="b")
```

- [ ] **Step 2: テスト fail 確認 → 実装 → pass**

`scripts/daily_bluesky_post/notifier.py`:

```python
"""Discord webhook 通知。

失敗時の能動通知。webhook URL が未設定なら no-op。
Discord 側エラー時に本体処理を止めないよう例外は呑む(ログのみ)。
"""
from __future__ import annotations

import logging
import httpx

logger = logging.getLogger(__name__)


def notify(*, webhook_url: str | None, title: str, body: str) -> None:
    if not webhook_url:
        return
    content = f"🚨 [aoyama-cemetery] {title}\n{body}"
    if len(content) > 1900:
        content = content[:1900] + "\n…(truncated)"
    try:
        resp = httpx.post(webhook_url, json={"content": content}, timeout=10)
        if resp.status_code >= 300:
            logger.warning("Discord webhook returned %s: %s", resp.status_code, resp.text[:200])
    except httpx.HTTPError as e:
        logger.warning("Discord webhook failed: %s", e)
```

- [ ] **Step 3: テスト pass + commit**

```bash
PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_notifier.py -v
# 3 passed

git add scripts/daily_bluesky_post/notifier.py scripts/daily_bluesky_post/tests/test_notifier.py
git commit -m "feat(bluesky-post): notifier(Discord webhook、例外は呑む)"
```

---

## Task 8: subagent 定義(2 ファイル)

**Files:**
- Create: `.claude/agents/aoyama-post-writer.md`
- Create: `.claude/agents/aoyama-fact-checker.md`

- [ ] **Step 1: `aoyama-post-writer.md` を作る**

```markdown
---
name: aoyama-post-writer
description: 青山霊園に眠る偉人または歴史的 event の Bluesky 投稿文を、与えられた frontmatter のみを根拠に生成する。事実誤認ゼロを最優先する。
model: claude-sonnet-4-6
---

あなたは青山霊園に眠る偉人と歴史的事件を紹介する Bluesky アカウントの投稿作成者です。

# 厳守ルール

1. 与えられた frontmatter 情報のみを事実として使うこと
2. frontmatter に記載のない人物関係・事件・著作・引用・地名・年号は一切追加しない
   - 例: shortDescription に「西郷との対立」が無ければ「西郷」を出してはいけない
   - 例: deathPlace が「東京・紀尾井坂(暗殺)」なら「紀尾井坂」は OK、「清水谷」は不可
3. 文字数は 300 字以内(改行 / URL を含む)
4. 文体: 重厚、プレーン、丁寧体(です・ます)
5. 装飾禁止: 太字、絵文字、記号装飾、見出し記号、ハッシュタグ
6. 構成:
   - 1 行目: person は「【本日の命日】◯◯(西暦-西暦)」、event は「【今日この日】<event 名>(西暦)」
   - 2-3 行目: shortDescription / summary を踏まえた本文(直訳ではなく自然な日本語に整える)
   - 最終行: URL を 1 行で
7. 出力は投稿本文のみ(前置き・説明・コードブロック・JSON 形式・引用符なし)

# 入力フォーマット(ユーザーメッセージ)

```yaml
kind: person | event
url: https://aoyama-cemetery.pages.dev/...
anniversary_year: <周年数>  # 例: 148
frontmatter:
  (該当 md の frontmatter 全体)
```

# 出力フォーマット

投稿本文の plain text のみ(改行込み)。
```

- [ ] **Step 2: `aoyama-fact-checker.md` を作る**

```markdown
---
name: aoyama-fact-checker
description: Bluesky 投稿文に frontmatter 外の事実が混入していないか厳格に検証する。少しでも疑わしければ fail。
model: claude-sonnet-4-6
---

あなたは事実検証担当です。

# 任務

与えられた【投稿文】が、【許可された事実(frontmatter)】の範囲だけで書かれているかチェックする。

許可された事実に書かれていない以下が登場していたら fail としてください:

- 人名(frontmatter の name / relatedPeople / 本文中の言及外)
- 事件名・条約名・戦争名・運動名
- 著作名・作品名
- 地名(birthPlace / deathPlace / 本文中の言及外)
- 年号・西暦・元号(birthDate / deathDate / 本文中の言及外)
- 関係性の主張(「◯◯の弟子」「◯◯と対立」「◯◯の養子」など)

迷ったら fail を選んでください。後段で再生成されます。

# 入力フォーマット

```yaml
post_text: |
  (投稿文)
allowed_facts:
  (frontmatter 全体)
```

# 出力フォーマット

JSON のみ(前置き・コードフェンス禁止):

```
{"verdict": "pass", "violations": []}
```

または

```
{"verdict": "fail", "violations": ["frontmatter にない人名『西郷隆盛』が登場", "frontmatter にない事件『西南戦争』が登場"]}
```
```

- [ ] **Step 3: commit**

```bash
git add .claude/agents/aoyama-post-writer.md .claude/agents/aoyama-fact-checker.md
git commit -m "feat(bluesky-post): subagent 定義(post-writer + fact-checker)"
```

---

## Task 9: claude_runner.py(claude -p subprocess ラッパー)

**Files:**
- Create: `scripts/daily_bluesky_post/claude_runner.py`
- Create: `scripts/daily_bluesky_post/tests/test_claude_runner.py`

**設計メモ**: orchestrator は match ごとに claude_runner.generate_post(match) を 1 回呼ぶ。内部で `claude -p <prompt>` を subprocess 起動し、Max plan 経路を使う。prompt は post-writer → fact-checker → 再生成ループ → JSON 出力を main claude に指示するメタプロンプト。

- [ ] **Step 1: 失敗テストを書く**

```python
import json
from unittest.mock import patch, MagicMock
from daily_bluesky_post import claude_runner


def _run_result(stdout: str, returncode: int = 0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = ""
    r.returncode = returncode
    return r


def test_generate_post_parses_json_output(monkeypatch):
    fake_output = json.dumps({"post_text": "【本日の命日】...", "attempts": 1})
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **kw: _run_result(fake_output),
    )
    result = claude_runner.generate_post(
        kind="person",
        url="https://aoyama-cemetery.pages.dev/people/okubo-toshimichi",
        anniversary_year=148,
        frontmatter={"name": "大久保 利通"},
    )
    assert result.status == "ok"
    assert result.post_text.startswith("【本日の命日】")
    assert result.attempts == 1


def test_generate_post_returns_failed_when_critique_rejects(monkeypatch):
    fake_output = json.dumps({
        "status": "failed",
        "attempts": 2,
        "violations": ["frontmatter にない人名"],
        "last_text": "...",
    })
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: _run_result(fake_output))
    result = claude_runner.generate_post(
        kind="person", url="https://x/y", anniversary_year=0, frontmatter={},
    )
    assert result.status == "failed"
    assert "frontmatter" in result.violations[0]


def test_generate_post_strips_anthropic_env(monkeypatch):
    """子プロセスに ANTHROPIC_API_KEY を渡さないこと"""
    captured_env = {}

    def fake_run(*args, **kwargs):
        captured_env.update(kwargs.get("env", {}))
        return _run_result(json.dumps({"post_text": "x", "attempts": 1}))

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-xxx")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "tok")
    monkeypatch.setattr("subprocess.run", fake_run)

    claude_runner.generate_post(
        kind="person", url="https://x/y", anniversary_year=0, frontmatter={},
    )
    assert "ANTHROPIC_API_KEY" not in captured_env
    assert "ANTHROPIC_AUTH_TOKEN" not in captured_env


def test_command_places_allowed_tools_before_p_flag(monkeypatch):
    """L0 知見: --allowed-tools は -p より前(variadic flag が prompt を吸う問題)"""
    captured_cmd = []

    def fake_run(cmd, *a, **kw):
        captured_cmd.extend(cmd)
        return _run_result(json.dumps({"post_text": "x", "attempts": 1}))

    monkeypatch.setattr("subprocess.run", fake_run)
    claude_runner.generate_post(
        kind="person", url="https://x/y", anniversary_year=0, frontmatter={},
    )
    # コマンド内で --allowed-tools の位置 < -p の位置
    if "--allowed-tools" in captured_cmd:
        assert captured_cmd.index("--allowed-tools") < captured_cmd.index("-p")
```

- [ ] **Step 2: テスト fail 確認 → 実装**

`scripts/daily_bluesky_post/claude_runner.py`:

```python
"""claude -p subprocess ラッパー。

CLI 実行で Max plan 経路を使い、Anthropic API 課金を避ける。

L0 知見:
- 子プロセスに ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN を継承させない
- --allowed-tools は -p より前に置く(variadic flag 問題)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import yaml
from dataclasses import dataclass, field


@dataclass
class GenerateResult:
    status: str  # "ok" | "failed" | "error"
    post_text: str = ""
    attempts: int = 0
    violations: list[str] = field(default_factory=list)
    last_text: str = ""
    error: str = ""


CLAUDE_BIN = shutil.which("claude") or "claude"


def _build_prompt(*, kind: str, url: str, anniversary_year: int, frontmatter: dict) -> str:
    fm_yaml = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)
    return f"""次の Match を Bluesky に投稿する文を作って、最後に必ず JSON だけを出力してください。

## 入力
kind: {kind}
url: {url}
anniversary_year: {anniversary_year}
frontmatter:
{fm_yaml}

## 手順
1. aoyama-post-writer subagent に上記を渡して投稿文を生成する
2. aoyama-fact-checker subagent に生成文と frontmatter を渡して critique する
3. critique が fail なら、violations を post-writer に渡して再生成 → 再 critique(リトライは 1 回まで)
4. 2 回目も fail なら status="failed" として終了

## 出力(最終出力は JSON 1 行のみ。前置きやコードフェンス禁止)
成功時:
{{"status": "ok", "post_text": "<投稿本文>", "attempts": <1または2>}}

失敗時:
{{"status": "failed", "attempts": 2, "violations": ["..."], "last_text": "<最後に生成された文>"}}
"""


def _child_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("ANTHROPIC_AUTH_TOKEN", None)
    return env


def generate_post(*, kind: str, url: str, anniversary_year: int, frontmatter: dict, timeout_sec: int = 180) -> GenerateResult:
    prompt = _build_prompt(kind=kind, url=url, anniversary_year=anniversary_year, frontmatter=frontmatter)

    cmd = [
        CLAUDE_BIN,
        "--allowed-tools", "Agent",   # subagent dispatch のみ許可、ファイル変更は無し
        "-p", prompt,
    ]

    try:
        proc = subprocess.run(
            cmd,
            env=_child_env(),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return GenerateResult(status="error", error="claude -p timed out")

    if proc.returncode != 0:
        return GenerateResult(status="error", error=f"claude exit {proc.returncode}: {proc.stderr[:500]}")

    # stdout の最終 JSON 行を取り出す
    payload = _extract_json(proc.stdout)
    if payload is None:
        return GenerateResult(status="error", error=f"JSON not found in output: {proc.stdout[-500:]}")

    return GenerateResult(
        status=payload.get("status", "ok") if "status" in payload else ("ok" if "post_text" in payload else "error"),
        post_text=payload.get("post_text", ""),
        attempts=payload.get("attempts", 1),
        violations=payload.get("violations", []),
        last_text=payload.get("last_text", ""),
    )


def _extract_json(text: str) -> dict | None:
    """stdout の末尾に近い行から JSON object を探す"""
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None
```

- [ ] **Step 3: テスト pass を確認**

```bash
PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_claude_runner.py -v
```

Expected: 4 passed.

- [ ] **Step 4: commit**

```bash
git add scripts/daily_bluesky_post/claude_runner.py scripts/daily_bluesky_post/tests/test_claude_runner.py
git commit -m "feat(bluesky-post): claude_runner(claude -p subprocess + env strip + variadic flag 位置)"
```

---

## Task 10: git_commit.py(投稿ログの単独 commit)

**Files:**
- Create: `scripts/daily_bluesky_post/git_commit.py`
- Create: `scripts/daily_bluesky_post/tests/test_git_commit.py`

**設計メモ**: admin/lib/publish.py を参照、ただし本ラッパーは push しない(spec 8 章「push は別運用」)。

- [ ] **Step 1: 失敗テストを書く + 実装**

`scripts/daily_bluesky_post/tests/test_git_commit.py`:

```python
import subprocess
from unittest.mock import MagicMock, call
from daily_bluesky_post import git_commit


def test_commit_log_runs_git_add_then_commit(monkeypatch):
    calls = []
    def fake_run(cmd, **kw):
        calls.append(cmd)
        return MagicMock(returncode=0, stdout="", stderr="")
    monkeypatch.setattr("subprocess.run", fake_run)

    git_commit.commit_posted_log("post: 2026-05-14 okubo-toshimichi")

    # add → commit の順
    assert any("add" in c for c in calls)
    assert any("commit" in c for c in calls)
    add_call = next(c for c in calls if "add" in c)
    commit_call = next(c for c in calls if "commit" in c)
    assert "logs/posted.jsonl" in " ".join(add_call)
    assert "post: 2026-05-14 okubo-toshimichi" in " ".join(commit_call)


def test_commit_log_skips_when_nothing_staged(monkeypatch):
    """diff --cached --quiet が returncode=0(差分なし) なら commit しない"""
    def fake_run(cmd, **kw):
        if "diff" in cmd and "--cached" in cmd:
            return MagicMock(returncode=0)  # 差分なし
        return MagicMock(returncode=0)
    monkeypatch.setattr("subprocess.run", fake_run)
    # 例外を raise しないこと
    git_commit.commit_posted_log("noop")
```

`scripts/daily_bluesky_post/git_commit.py`:

```python
"""logs/posted.jsonl を単独 commit する。push はしない。"""
from __future__ import annotations

import subprocess
from pathlib import Path

from daily_bluesky_post.config import PROJECT_ROOT, POSTED_LOG


def commit_posted_log(message: str) -> None:
    rel = POSTED_LOG.relative_to(PROJECT_ROOT)
    subprocess.run(["git", "add", "--", str(rel)], cwd=PROJECT_ROOT, check=True)
    # 差分がなければ commit しない
    diff = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", str(rel)],
        cwd=PROJECT_ROOT,
    )
    if diff.returncode == 0:
        return  # 差分なし
    subprocess.run(
        ["git", "commit", "-m", message, "--", str(rel)],
        cwd=PROJECT_ROOT,
        check=True,
    )
```

- [ ] **Step 2: テスト pass + commit**

```bash
PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/test_git_commit.py -v
git add scripts/daily_bluesky_post/git_commit.py scripts/daily_bluesky_post/tests/test_git_commit.py
git commit -m "feat(bluesky-post): git_commit(posted.jsonl の単独 commit、push なし)"
```

---

## Task 11: orchestrator.py(エンドツーエンド配線 + CLI)

**Files:**
- Create: `scripts/daily_bluesky_post/orchestrator.py`
- Create: `scripts/daily_bluesky_post/tests/test_orchestrator.py`

- [ ] **Step 1: テストを書く(全 I/O モック)**

`scripts/daily_bluesky_post/tests/test_orchestrator.py`:

```python
import shutil
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from daily_bluesky_post import orchestrator, config
from daily_bluesky_post.match import Match
from daily_bluesky_post.claude_runner import GenerateResult
from daily_bluesky_post.ogp_fetcher import OGP

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def mocked(monkeypatch, tmp_path):
    """全 I/O モック + log file は tmp_path"""
    log_path = tmp_path / "posted.jsonl"
    log_path.touch()
    monkeypatch.setattr(config, "POSTED_LOG", log_path)

    monkeypatch.setattr("daily_bluesky_post.orchestrator.config.load_secrets",
        lambda: config.Secrets("h", "p", "https://discord/x"))
    return SimpleNamespace = type("NS", (), {})()


def _set_match(monkeypatch, matches):
    monkeypatch.setattr(
        "daily_bluesky_post.orchestrator.match.match_today",
        lambda today, p, e: matches,
    )


def _ok_match(slug="okubo-toshimichi", kind="person"):
    return Match(kind=kind, slug=slug,
                 frontmatter={"name": "x"},
                 url=f"https://aoyama-cemetery.pages.dev/{kind}s/{slug}",
                 anniversary_year=148)


def test_zero_matches_does_nothing(monkeypatch, mocked):
    _set_match(monkeypatch, [])
    discord = MagicMock()
    monkeypatch.setattr("daily_bluesky_post.orchestrator.notifier.notify", discord)
    rc = orchestrator.run(today=date(2026, 5, 14), dry_run=False)
    assert rc == 0
    discord.assert_not_called()


def test_one_match_posts_and_logs(monkeypatch, mocked):
    _set_match(monkeypatch, [_ok_match()])
    monkeypatch.setattr(
        "daily_bluesky_post.orchestrator.claude_runner.generate_post",
        lambda **kw: GenerateResult(status="ok", post_text="...", attempts=1),
    )
    monkeypatch.setattr(
        "daily_bluesky_post.orchestrator.ogp_fetcher.fetch",
        lambda url: OGP("T", "D", None),
    )
    posted = MagicMock(return_value="at://x/y")
    monkeypatch.setattr("daily_bluesky_post.orchestrator.bluesky_client.post", posted)
    monkeypatch.setattr("daily_bluesky_post.orchestrator.git_commit.commit_posted_log", MagicMock())

    rc = orchestrator.run(today=date(2026, 5, 14), dry_run=False)
    assert rc == 0
    posted.assert_called_once()
    # log に追記された
    assert "okubo-toshimichi" in config.POSTED_LOG.read_text()


def test_skips_already_posted(monkeypatch, mocked):
    config.POSTED_LOG.write_text(
        '{"date":"2026-05-14","slug":"okubo-toshimichi","kind":"person","post_uri":"at://x","at":"2026-05-14T08:05:23+09:00"}\n'
    )
    _set_match(monkeypatch, [_ok_match()])
    posted = MagicMock()
    monkeypatch.setattr("daily_bluesky_post.orchestrator.bluesky_client.post", posted)
    rc = orchestrator.run(today=date(2026, 5, 14), dry_run=False)
    assert rc == 0
    posted.assert_not_called()  # idempotency 効いた


def test_critique_failed_notifies_and_skips_post(monkeypatch, mocked):
    _set_match(monkeypatch, [_ok_match()])
    monkeypatch.setattr(
        "daily_bluesky_post.orchestrator.claude_runner.generate_post",
        lambda **kw: GenerateResult(status="failed", attempts=2,
                                    violations=["frontmatter にない人名"], last_text="..."),
    )
    discord = MagicMock()
    monkeypatch.setattr("daily_bluesky_post.orchestrator.notifier.notify", discord)
    posted = MagicMock()
    monkeypatch.setattr("daily_bluesky_post.orchestrator.bluesky_client.post", posted)
    rc = orchestrator.run(today=date(2026, 5, 14), dry_run=False)
    posted.assert_not_called()
    discord.assert_called_once()
    assert "critique" in discord.call_args.kwargs["title"].lower() or "critique" in discord.call_args.kwargs["body"].lower()


def test_dry_run_does_not_post_or_log(monkeypatch, mocked, capsys):
    _set_match(monkeypatch, [_ok_match()])
    monkeypatch.setattr(
        "daily_bluesky_post.orchestrator.claude_runner.generate_post",
        lambda **kw: GenerateResult(status="ok", post_text="DRY", attempts=1),
    )
    monkeypatch.setattr(
        "daily_bluesky_post.orchestrator.ogp_fetcher.fetch",
        lambda url: OGP("T", "D", None),
    )
    posted = MagicMock()
    monkeypatch.setattr("daily_bluesky_post.orchestrator.bluesky_client.post", posted)
    rc = orchestrator.run(today=date(2026, 5, 14), dry_run=True)
    posted.assert_not_called()
    assert "DRY" in capsys.readouterr().out
    assert config.POSTED_LOG.read_text() == ""


def test_bluesky_auth_error_notifies_and_continues(monkeypatch, mocked):
    """1 件目で AuthError → 残りの match も skip(再ログイン失敗が連鎖するため即終了)"""
    _set_match(monkeypatch, [_ok_match("a"), _ok_match("b")])
    monkeypatch.setattr(
        "daily_bluesky_post.orchestrator.claude_runner.generate_post",
        lambda **kw: GenerateResult(status="ok", post_text="...", attempts=1),
    )
    monkeypatch.setattr(
        "daily_bluesky_post.orchestrator.ogp_fetcher.fetch",
        lambda url: OGP("T", "D", None),
    )
    from daily_bluesky_post.bluesky_client import AuthError
    monkeypatch.setattr(
        "daily_bluesky_post.orchestrator.bluesky_client.post",
        MagicMock(side_effect=AuthError("bad password")),
    )
    discord = MagicMock()
    monkeypatch.setattr("daily_bluesky_post.orchestrator.notifier.notify", discord)
    rc = orchestrator.run(today=date(2026, 5, 14), dry_run=False)
    assert discord.call_count >= 1
```

- [ ] **Step 2: テスト fail 確認 → orchestrator 実装**

`scripts/daily_bluesky_post/orchestrator.py`:

```python
"""エンドツーエンド orchestrator + CLI entry。

usage:
  python -m daily_bluesky_post.orchestrator                 # 通常実行
  python -m daily_bluesky_post.orchestrator --dry-run        # 投稿せず生成文を stdout に
  python -m daily_bluesky_post.orchestrator --today 2026-05-14 --dry-run
  python -m daily_bluesky_post.orchestrator --once <slug>    # 該当 slug を 1 件だけ投稿(マッチ判定不要、Phase 2 用)
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime, timezone, timedelta

from daily_bluesky_post import (
    bluesky_client, claude_runner, config, git_commit, match, notifier, ogp_fetcher, post_log,
)

logger = logging.getLogger("bluesky-post")
JST = timezone(timedelta(hours=9))


def run(*, today: date, dry_run: bool = False) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    secrets = config.load_secrets()

    matches = match.match_today(today, config.PEOPLE_DIR, config.EVENTS_DIR)
    logger.info("matches=%d for %s", len(matches), today.isoformat())
    if not matches:
        return 0

    entries = post_log.load(config.POSTED_LOG)
    auth_failed = False

    for m in matches:
        if post_log.already_posted(entries, today, m.slug):
            logger.info("skip already posted: %s", m.slug)
            continue
        if auth_failed:
            logger.info("skip (prior auth failure): %s", m.slug)
            continue

        result = claude_runner.generate_post(
            kind=m.kind, url=m.url, anniversary_year=m.anniversary_year, frontmatter=m.frontmatter,
        )
        if result.status != "ok":
            _notify_generation_failure(secrets.discord_webhook_url, m, result)
            continue

        if dry_run:
            print(f"--- DRY RUN: {m.slug} ---")
            print(result.post_text)
            print()
            continue

        ogp = ogp_fetcher.fetch(m.url)
        try:
            uri = bluesky_client.post(
                handle=secrets.bluesky_handle,
                password=secrets.bluesky_app_password,
                text=result.post_text,
                link_url=m.url,
                ogp=ogp,
            )
        except bluesky_client.AuthError as e:
            notifier.notify(
                webhook_url=secrets.discord_webhook_url,
                title="Bluesky 認証失敗",
                body=f"{e}\nApp Password を再発行して ~/.config/aoyama-cemetery/bluesky.env を更新してください。",
            )
            auth_failed = True
            continue
        except Exception as e:
            notifier.notify(
                webhook_url=secrets.discord_webhook_url,
                title="Bluesky 投稿失敗",
                body=f"slug={m.slug}\nerror={e}\ntext=\n{result.post_text}",
            )
            continue

        now = datetime.now(JST).replace(microsecond=0)
        entry = post_log.Entry(date=today, slug=m.slug, kind=m.kind, post_uri=uri, at=now)
        post_log.append(config.POSTED_LOG, entry)
        entries.append(entry)
        git_commit.commit_posted_log(f"post: {today.isoformat()} {m.slug}")
        logger.info("posted: %s -> %s", m.slug, uri)

    return 0


def _notify_generation_failure(webhook: str | None, m: match.Match, result: claude_runner.GenerateResult) -> None:
    if result.status == "failed":
        title = "LLM critique 2 連続 fail"
        body = (
            f"slug={m.slug} ({m.kind})\n"
            f"violations: {result.violations}\n"
            f"last_text:\n{result.last_text}"
        )
    else:
        title = "LLM 生成エラー"
        body = f"slug={m.slug} ({m.kind})\nerror: {result.error}"
    notifier.notify(webhook_url=webhook, title=title, body=body)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--today", help="YYYY-MM-DD(未指定なら JST 今日)")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    today = date.fromisoformat(args.today) if args.today else datetime.now(JST).date()
    return run(today=today, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: テスト pass を確認**

```bash
PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/ -v
```

Expected: 全テスト pass(~30 ケース)。

- [ ] **Step 4: dry-run 動作確認(本物データ、Bluesky/Claude API は呼ばない)**

```bash
# claude_runner を mock したいので、まず dry-run + generate_post を一時的に dummy 化する必要がある
# 代わりにユニットテストの pass で代用、本実行は Phase 2 でやる
```

- [ ] **Step 5: commit**

```bash
git add scripts/daily_bluesky_post/orchestrator.py scripts/daily_bluesky_post/tests/test_orchestrator.py
git commit -m "feat(bluesky-post): orchestrator(配線 + CLI + AuthError 連鎖防止)"
```

---

## Task 12: events ページの ogImage 渡し修正(spec §5.2)

**Files:**
- Modify: `src/pages/events/[slug].astro:92`

- [ ] **Step 1: 現状を確認**

```bash
grep -n "BaseLayout" src/pages/events/\[slug\].astro
```

Expected: `92:<BaseLayout title={title} description={description} jsonLd={[eventJsonLd, breadcrumbJsonLd]}>`

- [ ] **Step 2: ogImage を追加**

`src/pages/events/[slug].astro` の該当行を以下に変更:

```astro
<BaseLayout title={title} description={description} ogImage={event.data.heroImage?.src} jsonLd={[eventJsonLd, breadcrumbJsonLd]}>
```

- [ ] **Step 3: build 確認**

```bash
npm run build
```

Expected: ビルド成功(zod 通過)。

- [ ] **Step 4: 実 URL での OGP 確認(dev server)**

```bash
npm run dev &
sleep 3
curl -s http://localhost:4321/events/1860-03-24-sakuradamongai/ | grep -E '(og:image|og:title)'
kill %1
```

Expected: `og:image` の値が `/_astro/1860-03-24-sakuradamongai....jpg` 風になっている(heroImage がある event なら)。

- [ ] **Step 5: commit**

```bash
git add src/pages/events/\[slug\].astro
git commit -m "fix(events): heroImage を og:image に渡してリンクカードで表示されるようにする"
```

---

## Task 13: launchd plist + 設置手順を repo に置く(Phase 3 用)

**Files:**
- Create: `infra/launchd/jp.aoyama-cemetery.daily-post.plist`(テンプレ、実配置は手動)
- Create: `infra/launchd/README.md`

- [ ] **Step 1: plist テンプレを作成**

`infra/launchd/jp.aoyama-cemetery.daily-post.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>jp.aoyama-cemetery.daily-post</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/uchidayousuke/workspace/personal/aoyama-cemetery/scripts/daily_bluesky_post/run.sh</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>8</integer>
        <key>Minute</key>
        <integer>5</integer>
    </dict>

    <!-- スリープで時刻を逃したら起動後 catch-up 発火 -->
    <key>RunAtLoad</key>
    <false/>

    <key>StandardOutPath</key>
    <string>/Users/uchidayousuke/workspace/personal/aoyama-cemetery/logs/launchd.out.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/uchidayousuke/workspace/personal/aoyama-cemetery/logs/launchd.err.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
```

- [ ] **Step 2: README を作成**

`infra/launchd/README.md`:

```markdown
# launchd 設定: jp.aoyama-cemetery.daily-post

毎朝 8:05 JST に Bluesky 自動投稿を発火する LaunchAgent。

## 初回登録

```bash
cp infra/launchd/jp.aoyama-cemetery.daily-post.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/jp.aoyama-cemetery.daily-post.plist
launchctl list | grep aoyama
```

## 動作確認(即時発火)

```bash
launchctl start jp.aoyama-cemetery.daily-post
tail -f logs/launchd.out.log logs/launchd.err.log
```

## 停止 / 解除

```bash
launchctl unload ~/Library/LaunchAgents/jp.aoyama-cemetery.daily-post.plist
rm ~/Library/LaunchAgents/jp.aoyama-cemetery.daily-post.plist
```

## 注意

- StartCalendarInterval は Mac がスリープしていた場合、起動後に発火する(catch-up デフォルト)
- 二重投稿は logs/posted.jsonl のチェックで防止
- 失敗時は Discord webhook 経由でユーザー通知
```

- [ ] **Step 3: commit**

```bash
git add infra/
git commit -m "feat(bluesky-post): launchd plist テンプレ + 設置手順"
```

---

## Task 14: README / CLAUDE.md 更新

**Files:**
- Modify: `CLAUDE.md`(L2)
- Modify: `~/workspace/CLAUDE.md`(L0)の「ディレクトリ構成」「git リポ運用」aoyama-cemetery セクションに追記
  (L0 は CLAUDE.md のスコープ外なら本 PR では触れない、ユーザー判断)

- [ ] **Step 1: aoyama-cemetery/CLAUDE.md に「Bluesky 自動投稿」セクション追加**

`CLAUDE.md` に新セクション(管理画面セクションの後ろ):

```markdown
## Bluesky 自動投稿(`scripts/daily_bluesky_post/`、2026-06-03 新規)

毎朝 8:05 JST に本日が命日の偉人 / 該当日 events を Bluesky に自動投稿する仕組み。launchd + `claude -p` Max plan 経路 + subagent 2 段(post-writer / fact-checker)構成。

### 起動 / セットアップ

1. シークレット配置(`~/.config/aoyama-cemetery/bluesky.env` と `discord.env`)。フォーマットは `scripts/daily_bluesky_post/README.md` 参照
2. dry-run: `scripts/daily_bluesky_post/run.sh --dry-run --today 2026-05-14`
3. launchd 登録: `infra/launchd/README.md` 手順に従う

### アーキテクチャ

```
launchd 08:05 JST → run.sh → orchestrator.py
  → match.py で本日が命日の人物 + 該当日 events を集約(personSlugs 空除外、上限 5)
  → post_log で既投稿チェック
  → claude_runner が claude -p で post-writer → fact-checker subagent をループ
  → bluesky_client(atproto SDK)で external link card 付き投稿
  → logs/posted.jsonl 追記 + git commit
  → 失敗時は notifier で Discord webhook
```

詳細:
- spec: `docs/superpowers/specs/2026-06-03-bluesky-auto-post-design.md`
- plan: `docs/superpowers/plans/2026-06-03-bluesky-auto-post.md`

### 注意事項

- 子プロセスから `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` を必ず strip(claude_runner._child_env 参照、L0 知見)
- `--allowed-tools` は `-p` より前に置く(L0 知見、claude_runner._build_prompt 参照)
- subagent 定義(`.claude/agents/aoyama-post-writer.md` / `aoyama-fact-checker.md`)は frontmatter のみを根拠にする厳格ルールを保つこと。本文に「ハッシュタグ禁止」「絵文字禁止」を勝手に外さない(サイト全体の重厚トーンと一致させるため)
- `logs/posted.jsonl` は git commit する(idempotency + 履歴保存)。push は別運用
- 投稿失敗の事後対応: Discord 通知の生成文を参考に、本物の Bluesky 画面から手動投稿 or skip 判断
- pytest: `arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/`
```

- [ ] **Step 2: commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude): Bluesky 自動投稿セクションを追加"
```

---

## Task 15: 全テスト最終 pass + 動作確認(Phase 1 完了)

- [ ] **Step 1: 全テスト一括実行**

```bash
PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/ -v
```

Expected: 全 30 ケース前後が pass、エラー / xfail なし。

- [ ] **Step 2: dry-run 本物データ(claude_runner を含む完全実行で 1 件分の生成だけ確認)**

事前条件: 5/14 のような本日が命日の偉人がいる日付を指定(historical な日付で OK)。`~/.config/aoyama-cemetery/bluesky.env` は不要(dry-run なら secrets チェックを bypass する分岐を確認)。

```bash
# 5/14 = 大久保利通の命日で動作確認
scripts/daily_bluesky_post/run.sh --dry-run --today 2026-05-14
```

Expected: stdout に投稿文(`【本日の命日】大久保 利通...`)が出る、posted.jsonl は変更されない、Bluesky API は呼ばれない。

注意: dry-run 時も claude_runner は実際に `claude -p` を起動する(これが本実装の生成品質確認になる)。Anthropic Max plan の認証は別途必要。`claude` CLI が PATH にあること、Max plan セッションが生きていることを事前確認:

```bash
claude --version
```

- [ ] **Step 3: Phase 1 完了マークを commit message に残す**

```bash
git log --oneline | head -15  # Task 1-15 の commit 履歴を確認
git tag -a phase1-complete -m "Bluesky auto-post Phase 1: スクリプト + テスト + dry-run 完了"
```

(タグは push しない、ローカル参照のみ)

---

## Phase 2 以降のチェックリスト(本計画スコープ外、ユーザー手動)

- [ ] Bluesky 専用アカウント `aoyama-cemetery.bsky.social` を作成、プロフィール設定、App Password 発行
- [ ] Discord webhook を新規作成 or 既存チャンネルを流用
- [ ] `~/.config/aoyama-cemetery/{bluesky,discord}.env` を chmod 600 で配置
- [ ] `scripts/daily_bluesky_post/run.sh --once okubo-toshimichi` で 1 件本物投稿(Phase 2 用の `--once` オプションは Task 11 で実装済)→ Bluesky で OGP カードと文面を目視確認
- [ ] OK なら launchd 登録(`infra/launchd/README.md`)、翌朝発火を確認
- [ ] 1 ヶ月運用後に Phase 4 振り返り

---

## Verification

実装完了後、以下のコマンドが全て通れば Phase 1 完了:

```bash
# 1. テスト
PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/ -v

# 2. astro ビルド(events ogImage 修正の影響)
npm run build

# 3. dry-run 動作(claude -p 経由で実生成)
scripts/daily_bluesky_post/run.sh --dry-run --today 2026-05-14

# 4. git ステータス clean
git status
```

期待:
- 全 pytest ケース pass
- npm run build 成功
- dry-run で大久保利通の投稿文が stdout 表示、posted.jsonl 不変
- working tree clean

---

## Spec Compliance Map(自己 review 用)

| Spec 章 | 実装 Task |
|---|---|
| §2 スコープ(命日 / 該当日 / personSlugs 空除外 / portrait なし含む) | Task 4 match.py |
| §3 全体アーキテクチャ | Task 11 orchestrator.py |
| §4.1 launchd / Max plan / env strip / variadic flag | Task 9 claude_runner.py + Task 13 plist |
| §4.2 ディレクトリ構成 | Task 1 + 以降全て |
| §4.3 subagent 定義 | Task 8 |
| §4.4 マッチロジック(上限 5、周年順) | Task 4 |
| §4.5 投稿文生成 + critique | Task 8 + Task 9 |
| §4.6 Bluesky API(session, post, blob, embed) | Task 6 bluesky_client.py |
| §4.7 idempotency(JSONL + git commit) | Task 3 post_log.py + Task 10 git_commit.py |
| §4.8 失敗ハンドリング | Task 11 orchestrator.py(各 except 分岐) |
| §4.9 シークレット管理 | Task 2 config.py + Task 1 run.sh |
| §5.1 Bluesky アカウント | Phase 2 ユーザー手動 |
| §5.2 events ogImage 修正 | Task 12 |
| §5.3 Discord webhook | Phase 2 ユーザー手動 |
| §6 テスト方針 | Task 3-11 で各モジュールに pytest |
| §7 段階的リリース Phase 1-4 | Task 1-15 が Phase 1、Phase 2-4 は手動 |
| §8 運用 | Task 14 CLAUDE.md 追記 + Task 13 README |
| §9 将来拡張 | スコープ外、文書化のみ |
| §10 リスク | flock(Task 3)、catch-up(Task 13 plist) |

---

## Notes for the Executing Subagent

- **2 段レビュー**: L0 知見に従い、各 Task 完了時に「spec compliance」と「code quality」を別 subagent で 2 段レビューする。50 行以内の Task(Task 8, 12)は 1 段でも可。
- **frontmatter 仕様の確認**: Task 4 match.py で yaml.safe_load を使うが、本物の people md の frontmatter は portrait のように相対パス文字列を含む。yaml.safe_load は単純 string として扱うので問題ないはず。conftest を fixture で固めたので、もし本物データで挙動が変わるなら Task 4 Step 6 の sanity check で気付く。
- **atproto SDK バージョン依存**: Task 6 のテストで `atproto_client.exceptions` の NetworkError / UnauthorizedError を import している。SDK 0.0.50+ で存在することは確認済だが、最新版で名前が変わっていたら test_bluesky_client.py の import 文を修正する。
- **dry-run と claude -p**: dry-run でも claude -p は実行する(これが生成品質の事前検証になる)。claude CLI が PATH にない CI 環境では Task 15 Step 2 を skip 可。
- **Manual Phase 2**: Phase 2 以降は本計画のスコープ外。Bluesky アカウント作成・本番投稿・launchd 登録は実装完了後にユーザー側で手動実施する。
