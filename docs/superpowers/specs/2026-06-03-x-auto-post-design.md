# 青山霊園 SNS 自動投稿(X 展開)設計

- 起票日: 2026-06-03
- 対象 L2: `personal/aoyama-cemetery/`
- 前提設計: `2026-06-03-bluesky-auto-post-design.md`(Bluesky MVP、稼働中)
- 関連 L0 知見:
  - launchd + `claude -p` + Max plan(`ANTHROPIC_API_KEY` strip 等)
  - arm64 venv ラッパー
  - `--allowed-tools` は `-p` より前
  - cockpit ダッシュボードでの launchd 稼働監視

## 1. 背景と目的

Bluesky bot は毎朝 8:05 JST で稼働中(2026-06-03 launch、subagent 2 段で事実誤認ゼロ生成、5 回反復で文面トーン確立済)。同じ命日マッチ素材を **X(旧 Twitter)にも並走配信** し、日本国内の主流 SNS にもリーチする。

Bluesky 用の post-writer / fact-checker subagent と確立した重厚常体トーンは貴重資産のため壊さず、X は **別 surface として独立並走** させる。Bluesky 運用に対する回帰リスクをゼロに保ち、X だけ feature flag で段階リリースする。

期待効果:
- 日本国内の主流 SNS(X)でのフィード露出による偉人ページ流入増
- 命日 + 元号表記 + 1-2 個のハッシュタグで歴史クラスタへの拡散
- 既存 frontmatter + portrait/heroImage 資産の活用、追加コンテンツ作成負荷ゼロ

## 2. スコープ

### 含む

- Bluesky と同じ命日マッチ素材(people の deathDate、events の date)を投稿対象とする
- X 用 short 版(日本語 80-110 字 + URL、ハッシュタグ 1-2 個許容、常体ベース)を **別 subagent prompt** で生成
- portrait / heroImage を **media 添付**(Astro `src/assets/` から解決、X API で upload)
- Bluesky と **完全独立運用**: 片方失敗してももう片方は継続、posted log も platform 別ファイル
- X API v2 Free tier(1,500 posts/月)で運用 — 現在の発生頻度なら十分
- `X_ENABLED` env フラグで段階リリース(Phase 1 = 実装と merge を `0` で、Phase 3 = `1` 切替)

### 含まない(意図的)

- X Premium 課金($8/月、4,000 char 投稿可)
- スレッド分割投稿(1/n 2/n 形式)
- Bluesky / X 間の cross-mention
- リプライ・いいね・RT・インプレッション集計ダッシュボード
- 投稿時間の最適化(朝のゴールデンタイム vs 夜)— Bluesky と同時 08:05 JST 固定
- 絵文字使用(重厚トーン維持、X 文化に染めすぎない)

### 投稿対象の補足

- portrait なし偉人(PD 未経過の星新一・橋本龍太郎など)も投稿対象に含める。media なしで text + URL のみ投稿
- events で personSlugs が空配列のものは投稿対象から外す(Bluesky と同じ基準)

## 3. 全体アーキテクチャ

```
launchd cron(毎朝 8:05 JST、catch-up 有効、Bluesky と共通)
   │
   ▼
[1] match: 既存ロジックそのまま(今日が deathDate/event date の対象を上限 5 件集める)
   │
   ▼
[2] for match in matches:
   │   ├ for platform in ["bluesky", "x"]:
   │   │     ├ X_ENABLED=0 なら x をスキップ
   │   │     ├ posted_<platform>.jsonl で (date, slug) 既出ならスキップ
   │   │     ├ claude_runner.generate_post(match, agent_name)
   │   │     │   ├ Bluesky → post-writer + fact-checker
   │   │     │   └ X       → post-writer-x + fact-checker-x
   │   │     ├ image_resolver.resolve(slug, kind)(X のみ呼ぶ)
   │   │     ├ platform_client.post(text, url, image_path)
   │   │     ├ posted_<platform>.jsonl 追記
   │   │     └ 失敗時 → Discord 通知、もう一方の platform 処理は継続
   │   └ 両 platform 完了後にまとめて 1 commit
```

**ポイント**:
- match / claude_runner / post_log / notifier / orchestrator 骨格は **既存共通モジュール**
- 新規追加は `x_client.py`、`image_resolver.py`、`aoyama-post-writer-x.md` / `aoyama-fact-checker-x.md` の 4 ファイルのみ
- posted log は **platform ごとに別ファイル** で部分成功を正確に追跡

## 4. 詳細設計

### 4.1 実行環境

Bluesky 設計を踏襲。`run.sh` / launchd plist / venv / `claude -p` の `ANTHROPIC_API_KEY` strip / `--allowed-tools` 位置はそのまま。`orchestrator.py` の内部 loop だけが multi-platform 化される。

### 4.2 モジュール構成

```
scripts/daily_bluesky_post/   # ディレクトリ名は維持(rename しない)
├── orchestrator.py           # 改造: platform loop 追加
├── match.py                  # 無変更
├── post_log.py               # 改造: コンストラクタで path 引数化
├── claude_runner.py          # 改造: agent_name 引数を受ける
├── notifier.py               # 無変更
├── git_commit.py             # 無変更
├── ogp_fetcher.py            # 無変更(Bluesky link card 用に継続使用)
├── config.py                 # 改造: X 認証情報 + X_ENABLED フラグ追加
├── bluesky_client.py         # 無変更
├── x_client.py               # 新規: tweepy v2 で OAuth 1.0a User Context 投稿
├── image_resolver.py         # 新規: slug → src/assets/portraits|event-images の解決
├── run.sh                    # 無変更
└── tests/
    ├── test_x_client.py             # 新規(8 件)
    ├── test_image_resolver.py       # 新規(6 件)
    ├── test_orchestrator_x.py       # 新規(7 件)
    ├── test_post_log.py             # 既存に 2 件追加
    └── test_config.py               # 既存に 2 件追加

.claude/agents/
├── aoyama-post-writer.md        # 無変更
├── aoyama-fact-checker.md       # 無変更
├── aoyama-post-writer-x.md      # 新規
└── aoyama-fact-checker-x.md     # 新規

logs/
├── posted_bluesky.jsonl         # 既存 posted.jsonl を git mv で rename
└── posted_x.jsonl               # 新規

~/.config/aoyama-cemetery/
├── bluesky.env                  # 既存
├── discord.env                  # 既存
└── x.env                        # 新規
```

### 4.3 X 認証情報(`~/.config/aoyama-cemetery/x.env`)

```
X_API_KEY=...           # Developer Portal の Consumer Keys (API Key)
X_API_SECRET=...        # Developer Portal の Consumer Keys (API Key Secret)
X_ACCESS_TOKEN=...      # OAuth 1.0a User Access Token
X_ACCESS_SECRET=...     # OAuth 1.0a User Access Secret
X_ENABLED=0             # 段階リリース用 feature flag(Phase 3 で 1 に切替)
```

OAuth 1.0a User Context を採用する理由: Free tier で v2 endpoint `POST /2/tweets` + `POST /1.1/media/upload.json`(media は v1.1 endpoint が安定)を組み合わせる際、tweepy v4 の `Client` + `API` 併用パターンが標準。OAuth 2.0 PKCE は CLI からの再認可サイクルが煩雑で daemon 運用に不向き。

### 4.4 subagent: `aoyama-post-writer-x.md`

Bluesky 版との差分:

| 項目 | Bluesky 版 | X 版 |
|---|---|---|
| 本文字数 | 180-240 字 | **80-110 字**(URL 別) |
| 全体 weighted length | 290 字以内(grapheme) | **270 weighted units 以内**(日本語 1 字=2、URL=23 固定、安全マージン 10) |
| 1 行目 | `【偉人名 命日】` | 同左 |
| 最終行 URL | 必須 | 必須 |
| 元号 + 月日(例: 明治11年5月14日) | 必須 | 必須 |
| トーン | 常体・装飾なし | **常体ベース + 軽い問いかけ許容** |
| ハッシュタグ | 禁止 | **`#青山霊園` 必須 + 任意 1 個**(`#明治維新` `#幕末` `#文学` 等、人物に応じて) |
| 絵文字 | 禁止 | 禁止(維持) |
| 区画番号(graveSection)言及 | 禁止 | 禁止(維持) |
| 事実根拠 | frontmatter + body のみ | 同左 |
| 装飾 | 禁止 | 禁止(維持) |

**出力フォーマット例**:
```
【大久保利通 命日】明治11年5月14日、紀尾井坂で暗殺。中央集権を貫いた内務卿、その終わりは騎馬ひとつだった。 #青山霊園 #明治維新
https://aoyama-cemetery.pages.dev/people/okubo-toshimichi
```

### 4.5 subagent: `aoyama-fact-checker-x.md`

- Bluesky 版と同じ厳格基準(frontmatter + body 外の事実混入で fail)
- **追加検証項目**:
  - ハッシュタグが事実関係を歪めていないか(例: `#討幕の英雄` のような誇張的タグは fail、`#明治維新` のような客観カテゴリは pass)
  - `#青山霊園` の有無を必須チェック
- 出力 JSON `{verdict, violations}` 形式は Bluesky 版と統一

### 4.6 X weighted length カウント

X は日本語 1 文字 = 2 weighted units、URL は t.co 短縮で 23 units 固定(2026-06-03 時点)。`claude_runner` の字数ガードは以下のヘルパで判定:

```python
def x_weighted_length(text: str) -> int:
    # ASCII = 1, 多くの記号 = 1, CJK / 全角 = 2
    # URL は 23 units 固定(t.co 短縮、http/https 問わず)
    # 簡便実装: twitter-text-python or 自前で CJK 範囲判定
```

実装方針: 公式 `twitter-text` の Python port(`twitter-text-python` PyPI、最終更新性とライセンスを Phase 1 着手時に確認)を採用。採用不可なら自前 `re` ベース実装にフォールバック(URL を 23 単位置換 → 残りを 1 字あたり 1 or 2 で加算)。

超過時の挙動: Bluesky と同じく **1 回 regenerate(短縮指示付き)→ 再失敗で skip + Discord 通知**。

### 4.7 画像解決(`image_resolver.py`)

```python
def resolve(slug: str, kind: Literal["person", "event"]) -> Path | None:
    """
    person → src/content/people/<slug>.md の frontmatter portrait field を読み、
             ../../assets/portraits/<slug>.jpg 等を絶対 path 化。
             portrait なしは None。
    event  → src/content/events/<slug>.md の frontmatter heroImage field を読む。
             heroImage なしは None。
    """
```

X media upload は **5MB 上限**(JPEG/PNG/GIF/WebP)。投稿前に PIL で size 確認:
- portrait は管理画面で 1600px 長辺 quality 85 にリサイズ済 → 通常リサイズ不要
- heroImage は素材次第 → 必ず size チェック、超過時は長辺 1600px に縮小して tempfile に書き出す
- 一時ファイルは投稿後 `try/finally` で削除

None の場合は media 添付なしで text + URL のみ投稿(API call は成功させる)。

### 4.8 X 投稿クライアント(`x_client.py`)

```python
class XClient:
    def __init__(self, api_key, api_secret, access_token, access_secret):
        self._v2 = tweepy.Client(
            consumer_key=api_key, consumer_secret=api_secret,
            access_token=access_token, access_token_secret=access_secret,
        )
        self._v1 = tweepy.API(tweepy.OAuth1UserHandler(
            api_key, api_secret, access_token, access_secret,
        ))

    def post(self, text: str, image_path: Path | None) -> dict:
        media_ids = []
        if image_path is not None:
            media = self._v1.media_upload(filename=str(image_path))
            media_ids = [media.media_id_string]
        resp = self._v2.create_tweet(text=text, media_ids=media_ids or None)
        return {"tweet_id": resp.data["id"], "url": f"https://x.com/i/web/status/{resp.data['id']}"}
```

**エラー区分**:
- `tweepy.errors.Unauthorized` (401) → AuthError(env 確認を促す Discord 通知 + 以降の X 処理 bypass)
- `tweepy.errors.Forbidden` (403) → AuthError 扱い(write 権限なし等)
- `tweepy.errors.TooManyRequests` (429) → RateLimit(月制限到達、以降の X 処理 bypass)
- その他 `tweepy.errors.TweepyException` → 通常失敗(当該 match のみ skip)

### 4.9 orchestrator 改造

```python
log_bluesky = PostLog(LOGS_DIR / "posted_bluesky.jsonl")
log_x       = PostLog(LOGS_DIR / "posted_x.jsonl")
x_auth_failed = False

for match in matches:
    bluesky_result = None
    x_result = None
    for platform, client, log, agent in [
        ("bluesky", bluesky_client, log_bluesky, "aoyama-post-writer"),
        ("x",       x_client,       log_x,       "aoyama-post-writer-x"),
    ]:
        if platform == "x" and not config.X_ENABLED:
            continue
        if platform == "x" and x_auth_failed:
            continue
        if log.is_posted(today, match.slug):
            continue
        try:
            text = claude_runner.generate_post(match, agent_name=agent)
            image = image_resolver.resolve(match.slug, match.kind) if platform == "x" else None
            result = client.post(text, url=match.url, image_path=image)
            log.record(today, match.slug, result)
            if platform == "x": x_result = "ok"
            else:               bluesky_result = "ok"
        except (XAuthError,) as e:
            x_auth_failed = True
            notifier.notify(f"[x] AuthError: {e}")
            x_result = "auth_fail"
        except Exception as e:
            notifier.notify(f"[{platform}] {match.slug}: {e}", generated_text=text if "text" in locals() else None)
            if platform == "x": x_result = "fail"
            else:               bluesky_result = "fail"
    git_commit.commit_posted_logs(date=today, slug=match.slug,
                                   bluesky=bluesky_result, x=x_result)
```

`git_commit.commit_posted_logs`: 両 platform の jsonl を `git add` してまとめて 1 commit。message は `chore(posts): {date} {slug} bluesky={status} x={status}`。何も追記されなかった(両方 skip / disabled)場合は commit しない。

### 4.10 エラー処理マトリクス

| 失敗箇所 | 影響範囲 | 復旧 |
|---|---|---|
| match.py 例外 | 全体停止 | Discord 通知、launchd 次回再実行 |
| claude_runner timeout(300s) | 当該 match の当該 platform のみ skip | Discord 通知、もう一方の platform は継続 |
| post-writer 字数超過(regen 後も) | 当該 platform のみ skip | Discord 通知 |
| fact-checker fail × 2 | 当該 platform のみ skip | Discord 通知(violations 全文) |
| image_resolver で portrait なし | media なしで投稿継続 | 通知なし(仕様内) |
| image > 5MB | PIL リサイズ → 投稿継続、リサイズ失敗時は image なしで投稿継続 | リサイズ失敗時のみ Discord 通知 |
| x_client AuthError(401/403) | 残り全 X match を skip + `x_auth_failed` フラグで bypass | Discord 通知(env 再確認を促す) |
| x_client RateLimit(429) | 残り全 X match を skip | Discord 通知 |
| x_client その他 TweepyException | 当該 match の X のみ skip | Discord 通知 |
| Bluesky AuthError | 既存挙動と同じ(残り Bluesky match を skip)、X 側は影響なし | Discord 通知 |
| posted_*.jsonl 書き込み失敗 | flock 失敗で全停止(現状維持) | 手動 unlock or 翌日再実行 |

## 5. テスト方針

`pytest` で **新規 25 件追加**(既存 56 件 + 25 件 = 81 件目標)。

- `test_x_client.py`(8 件): media upload あり / なし、リサイズ要 / 不要、AuthError、RateLimit、TweepyException、text-only、weighted_length カウント
- `test_image_resolver.py`(6 件): person portrait あり / なし、event heroImage あり / なし、相対 path 解決、ファイル不存在
- `test_orchestrator_x.py`(7 件): 両 platform 成功 / Bluesky 成功 X 失敗 / X 成功 Bluesky 失敗 / X_ENABLED=0 全 skip / X auth_failed の連鎖 bypass / 両 既投稿 skip / partial matches succeed
- `test_post_log.py` 拡張(2 件): 2 ファイル分離での重複判定
- `test_config.py` 拡張(2 件): X 認証情報読み込み、X_ENABLED フラグ デフォルト 0

実行:
```bash
PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/
```

## 6. 段階リリース

- **Phase 1**: 実装 + テスト(`X_ENABLED=0` で merge、Bluesky 影響ゼロ)
- **Phase 2**: X アカウント作成 + Developer Portal 申請 + Free tier API key 取得 + env 配置 + `--dry-run --platform=x --today=2026-05-14` で 5 回反復文面チューニング
- **Phase 3**: `X_ENABLED=1` 切替 + launchd 次回発火を待つ(plist 変更不要)
- **Phase 4**: 1 ヶ月運用後の振り返り(投稿数 / インプレッション集計 / fact-checker fail 率)

## 7. Bluesky 既存運用への影響

- **コード**: orchestrator / post_log / claude_runner / config の 4 ファイル改造、既存テスト 56 件は全 pass を維持(回帰なし)
- **データ**: `logs/posted.jsonl` → `logs/posted_bluesky.jsonl` の git mv 1 回のみ、内容は無変更
- **subagent**: 既存 2 ファイルは無変更
- **launchd**: plist 無変更、catch-up も既存挙動維持
- **env**: `bluesky.env` / `discord.env` 無変更、`x.env` 新規

## 8. リスクと留保事項

- **X Developer Portal 審査**: Free tier でも Basic 審査(用途記入)が必要。アカウント作成 → 審査通過まで数日 〜 数週間かかる可能性。Phase 2 が長期化する場合は Phase 1(コード)を先に main へ merge して塩漬けでも問題ない(X_ENABLED=0)
- **X API 価格変動**: Free tier の 1,500 posts/月 は将来縮小される可能性あり。月間投稿数(命日 + events のマッチ数)を Phase 4 で計測、限界に近づいたら Premium 課金 or 投稿頻度調整を意思決定
- **OGP リンクカード**: X は OGP カードを自動表示するが media 添付すると非表示になる。本設計は media 優先(クリック率重視)、リンクカード非表示は許容
- **twitter-text Python port のメンテ状況**: PyPI 上の `twitter-text-python` が最終更新古い場合、自前 weighted_length 実装にフォールバック。Phase 1 着手時に確認
- **t.co 短縮の仕様変更**: 23 units 固定は 2026-06-03 時点の仕様、変更時は `X_URL_WEIGHT` 定数で集中管理
- **events の personSlugs 空配列除外**: Bluesky と同じ基準(青山霊園関係者が誰も関与していない歴史背景事件は投稿しない)
- **`#青山霊園` ハッシュタグ枯渇リスク**: 同タグの daily 投稿で X 側に低品質判定される可能性。Phase 4 で頻度・拡散実績を見ながら調整

## 9. 開発スケジュール

- Phase 1(設計 + 実装 + テスト): 1 セッション完走目標(Bluesky bot と同パターン、subagent-driven-development で 12-15 task 想定)
- Phase 2(アカウント + dry-run チューニング): user 手動、別セッション
- Phase 3(launchd 反映): env 1 行書き換えのみ、即時
- Phase 4(運用振り返り): 1 ヶ月後

## 10. 参照ドキュメント

- 前提設計: `docs/superpowers/specs/2026-06-03-bluesky-auto-post-design.md`
- Bluesky 実装: `scripts/daily_bluesky_post/`
- L0 知見元: `~/workspace/CLAUDE.md`(claude -p subprocess + --allowed-tools 位置 + ANTHROPIC_API_KEY strip)
- 過去メモ: `~/Obsidian/claude-code/2026-06-03-aoyama-bluesky-bot-spec-to-launchd稼働.md`(Bluesky 完走記録、SNS 文字数比較表)
