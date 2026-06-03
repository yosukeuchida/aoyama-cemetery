# 青山霊園 SNS 自動投稿(Bluesky MVP)設計

- 起票日: 2026-06-03
- 対象 L2: `personal/aoyama-cemetery/`
- 関連 L0 知見:
  - launchd + `claude -p` + Max plan(biz-radar Phase 1 で確立、`ANTHROPIC_API_KEY` strip 等)
  - arm64 venv ラッパー(award-flights / lbo-simulator / admin で確立)
  - cockpit ダッシュボードでの launchd 稼働監視

## 1. 背景と目的

青山霊園に眠る 136 名の偉人と歴史的 events を紹介する本サイト(https://aoyama-cemetery.pages.dev)は、現状では Google 検索流入と直リンク共有が主な発見導線になっている。

「今日が誰の命日か」「今日この日にどんな事件があったか」は本来 SNS との相性が良いコンテンツだが、現状は人手投稿していない。これを **毎朝 1 回、Bluesky に自動投稿** する仕組みを構築する。

期待効果:

- 命日・歴史的当日のフィード露出による偉人ページへの流入増
- 「青山霊園の偉人」アカウントとしての継続発信による認知形成
- 既存 frontmatter 資産(名前・没年月日・短い説明・URL)の活用、追加コンテンツ作成負荷ゼロ

## 2. スコープ

### 含む

- 偉人 `src/content/people/*.md` の **命日(deathDate の月日)** が今日と一致するページを投稿
- events `src/content/events/*.md` の **date(slug プレフィックスの月日)** が今日と一致するページを投稿
- 投稿先は **Bluesky のみ**(青山霊園サイト専用アカウントを新規作成)
- LLM(Claude)による投稿文生成と事実検証(critique)
- 二重投稿防止(投稿ログによる idempotency)
- 失敗時の Discord 通知

### 含まない(意図的に除外、将来検討)

- Threads / X (Twitter) / Mastodon 等の他 SNS(後から「投稿先プラガブル化」で追加可能な設計にはする)
- 節目年(没後 50 / 100 / 150 年)特別文の生成分岐
- 投稿前の人手レビュー UI(critique 独立性で代替する)
- いいね・リプライ数のダッシュボード集計
- 偉人ページの誕生日・生年マッチでの投稿(命日のみに絞る)
- events の `personSlugs` が空配列(青山霊園関係者が誰も関与していない歴史背景イベント)は投稿対象外とする — 「本霊園に眠る人物が関わっていない事件」を投稿してもサイトの趣旨に合致しない

### 投稿対象の補足

- portrait なし偉人(PD 未経過の星新一・橋本龍太郎など)も投稿対象に含める。Bluesky リンクカードの og:image が出ないだけで、text + URL での投稿は成立する
- events で personSlugs が空配列のものは投稿対象から外す(上述)。残った events のみ投稿する

## 3. 全体アーキテクチャ

```
launchd cron(毎朝 8:05 JST、catch-up 有効)
   │
   ▼
[1] match: 今日の date と一致する人物 / events を集める(上限 5 件)
   │
   ▼
[2] 既投稿ログ logs/posted.jsonl を読み、(date, slug) が既出ならスキップ
   │
   ▼ (残った対象を for-loop)
[3] claude -p 起動 → post-writer subagent → 投稿文生成
   │
   ▼
[4] 同セッション内で fact-checker subagent → critique
   │
   ├ pass → Bluesky 投稿 → posted.jsonl 追記 → git commit
   ├ fail (1回目)→ post-writer に violations を渡して再生成
   └ fail (2回目)→ skip + Discord 通知
```

## 4. 詳細設計

### 4.1 実行環境

- macOS launchd の LaunchAgent として登録
  - plist: `~/Library/LaunchAgents/jp.aoyama-cemetery.daily-post.plist`
  - 発火: `StartCalendarInterval` で 08:05 JST(0 分発火の他ジョブと CPU 競合を避ける)
  - catch-up: Mac スリープ等で時刻を逃した場合、起動後すぐ発火
- 実行は `arch -arm64` でラップした venv(L0 知見、Apple Silicon ネイティブ確保)
- `claude -p` headless を subprocess で起動し、Max plan 経路を使う(Anthropic API 課金ゼロ)
  - subprocess 起動時に `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` を env から strip(L0 知見、biz-radar Phase 1)
  - `--allowed-tools` は `-p` より前に置く(variadic flag が prompt を吸う問題、L0 知見)
- cockpit ダッシュボードに launchd ジョブとして拾われるよう、Label を `jp.aoyama-cemetery.daily-post` で命名

### 4.2 ディレクトリ構成

```
aoyama-cemetery/
├── scripts/daily-bluesky-post/
│   ├── run.sh                    # launchd entry、arch -arm64 で venv 起動 + env source
│   ├── orchestrator.py           # match + ループ + 投稿 + ログ + 通知
│   ├── bluesky_client.py         # createSession + createRecord + OGP embed
│   ├── match.py                  # date → 人物 / events 集約 + フィルタ + 上限
│   ├── post_log.py               # logs/posted.jsonl の R/W
│   ├── notifier.py               # Discord webhook 送信
│   ├── claude_runner.py          # claude -p subprocess ラッパー(env strip 込み)
│   ├── requirements.txt
│   └── tests/
│       ├── test_match.py
│       ├── test_post_log.py
│       ├── test_bluesky_client.py    # API 呼び出しは responses mock
│       └── test_orchestrator.py      # claude_runner / bluesky / notifier 全部 mock
├── .claude/agents/
│   ├── aoyama-post-writer.md     # 投稿文生成 subagent
│   └── aoyama-fact-checker.md    # critique subagent
└── logs/
    ├── posted.jsonl              # 投稿履歴 + idempotency(git commit)
    └── errors.jsonl              # 失敗履歴(git commit、参照用)
```

### 4.3 subagent 定義

#### `.claude/agents/aoyama-post-writer.md`

```markdown
---
name: aoyama-post-writer
description: 青山霊園に眠る偉人または歴史的 event の Bluesky 投稿文を、与えられた frontmatter のみを根拠に生成する。
model: claude-sonnet-4-6
---

あなたは青山霊園に眠る偉人と歴史的事件を紹介する Bluesky 投稿の作成者です。

# 厳守ルール

1. 与えられた frontmatter 情報のみを事実として使うこと
2. frontmatter に記載のない人物関係・事件・著作・引用・地名・年号は一切追加しないこと
   - 例: shortDescription に「西郷との対立」が無ければ「西郷」を出してはいけない
   - 例: deathPlace が「東京・紀尾井坂(暗殺)」とあれば紀尾井坂は OK、「清水谷」は frontmatter に無いので不可
3. 文字数は 300 字以内(改行 / URL を含む)
4. 文体: 重厚、プレーン、丁寧体(です・ます)
5. 装飾禁止: 太字、絵文字、記号装飾、見出し記号
6. 構成:
   - 冒頭: 人物は「【本日の命日】◯◯(西暦-西暦)」、event は「【今日この日】<event 名>(西暦)」
   - 中段: shortDescription を踏まえた 1〜3 文の本文
   - 末尾: URL を 1 行で
7. 出力は投稿本文のみ(前置き・説明・コードブロックなし)

# 入力フォーマット

```yaml
kind: person | event
frontmatter:
  (該当 md の frontmatter 全体)
url: https://aoyama-cemetery.pages.dev/people/<slug> | /events/<slug>
```

# 出力フォーマット

投稿本文の plain text のみ。
```

#### `.claude/agents/aoyama-fact-checker.md`

```markdown
---
name: aoyama-fact-checker
description: Bluesky 投稿文に frontmatter 外の事実が混入していないか検証する。
model: claude-sonnet-4-6
---

あなたは事実検証担当です。

# 任務

与えられた【投稿文】が、【許可された事実】に基づいて書かれているかチェックする。

許可された事実に書かれていない以下が登場していたら fail としてください:

- 人名(frontmatter の name / relatedPeople / 本文中の言及外)
- 事件名・条約名・戦争名・運動名
- 著作名・作品名
- 地名(birthPlace / deathPlace / 本文中の言及外)
- 年号・西暦・元号(birthDate / deathDate / 本文中の言及外)
- 関係性の主張(「◯◯の弟子」「◯◯と対立」など)

# 入力フォーマット

```yaml
post_text: |
  (生成された投稿文)
allowed_facts:
  (frontmatter 全体)
```

# 出力フォーマット

JSON のみ(コードブロックなし、説明文なし):

```json
{
  "verdict": "pass",
  "violations": []
}
```

または

```json
{
  "verdict": "fail",
  "violations": [
    "frontmatter にない人名『西郷隆盛』が登場",
    "frontmatter にない事件『西南戦争』が登場"
  ]
}
```
```

### 4.4 マッチロジック

```python
@dataclass
class Match:
    kind: Literal["person", "event"]
    slug: str
    frontmatter: dict
    url: str

def match_today(today: date) -> list[Match]:
    matches = []
    # 人物: deathDate の月日が today の月日と一致
    for path in glob("src/content/people/*.md"):
        fm = parse_frontmatter(path)
        if not fm.get("deathDate"):
            continue
        d = fm["deathDate"]  # date 型
        if d.month == today.month and d.day == today.day:
            matches.append(Match("person", slug=path.stem, frontmatter=fm,
                                 url=f"{SITE_URL}/people/{path.stem}"))
    # events: date の月日が today の月日と一致 + personSlugs が非空
    for path in glob("src/content/events/*.md"):
        fm = parse_frontmatter(path)
        if not fm.get("personSlugs"):  # 空配列は除外
            continue
        d = fm["date"]
        if d.month == today.month and d.day == today.day:
            matches.append(Match("event", slug=path.stem, frontmatter=fm,
                                 url=f"{SITE_URL}/events/{path.stem}"))
    # 5 件上限(超過時は周年年数が大きい順 → event 優先 → slug アルファベット順)
    matches.sort(key=lambda m: (
        -(today.year - m.frontmatter[m._date_field].year),  # 周年が大きい順
        0 if m.kind == "event" else 1,                       # event 優先
        m.slug,
    ))
    return matches[:5]
```

### 4.5 投稿文生成と critique

orchestrator から `claude_runner.run(prompt, allowed_tools=[...])` を 1 回呼び、その中で post-writer → fact-checker を順に dispatch する。Claude Code の Agent ツールを使った 2 段呼び出し。

擬似コード(orchestrator から claude_runner に渡す prompt):

```
次の Match を Bluesky に投稿する文を作って:

kind: person
url: https://aoyama-cemetery.pages.dev/people/okubo-toshimichi
frontmatter:
  name: 大久保 利通
  birthDate: 1830-09-26
  deathDate: 1878-05-14
  shortDescription: 明治維新三傑の一人。初代内務卿として近代日本の基礎を築いた薩摩出身の政治家。
  birthPlace: 薩摩国鹿児島城下加治屋町(現・鹿児島県鹿児島市)
  deathPlace: 東京・紀尾井坂(暗殺)
  ...

手順:
1. aoyama-post-writer subagent に上記を渡して投稿文を生成
2. aoyama-fact-checker subagent に生成文と frontmatter を渡して critique
3. critique が fail なら post-writer に violations を渡して再生成 → 再 critique
4. 2 回目も fail なら "FAILED: <violations>" を出力
5. pass したら投稿文を出力(JSON: {"post_text": "...", "attempts": N})
```

orchestrator は claude_runner の stdout を JSON parse し、`post_text` を受け取って Bluesky に投稿する。FAILED の場合は skip + Discord 通知。

### 4.6 Bluesky API 呼び出し

#### 認証

`POST /xrpc/com.atproto.server.createSession` に `identifier` + `password`(App Password)を送り、`accessJwt` と `did` を受け取る。セッションは数十分有効、1 回の orchestrator 実行内で使い回す。

#### 投稿

`POST /xrpc/com.atproto.repo.createRecord` に以下を送る:

```json
{
  "repo": "<did>",
  "collection": "app.bsky.feed.post",
  "record": {
    "$type": "app.bsky.feed.post",
    "text": "<生成された投稿文>",
    "createdAt": "2026-05-14T08:05:23.000Z",
    "facets": [
      {
        "index": {"byteStart": <URL の開始>, "byteEnd": <URL の終了>},
        "features": [{"$type": "app.bsky.richtext.facet#link", "uri": "<URL>"}]
      }
    ],
    "embed": {
      "$type": "app.bsky.embed.external",
      "external": {
        "uri": "<URL>",
        "title": "<OGP の og:title 値>",
        "description": "<OGP の og:description 値>",
        "thumb": <blob upload した CID>  // og:image があれば
      }
    }
  }
}
```

#### OGP 取得とサムネ blob upload

1. orchestrator が偉人ページ URL を `requests.get` で取得 → BeautifulSoup で `og:title` / `og:description` / `og:image` を抽出
2. og:image があれば画像 URL を再度 `requests.get` で取得し、`POST /xrpc/com.atproto.repo.uploadBlob` でアップロード → 返ってきた `blob` を embed.external.thumb に入れる
3. og:image が無い場合は thumb 抜きで投稿(text + URL のみのカード)

### 4.7 idempotency と投稿ログ

#### `logs/posted.jsonl` の構造

1 投稿 = 1 行 JSON:

```json
{"date":"2026-05-14","slug":"okubo-toshimichi","kind":"person","post_uri":"at://did:plc:.../app.bsky.feed.post/3k...","at":"2026-05-14T08:05:23+09:00"}
```

#### 動作

- orchestrator は起動時に posted.jsonl を全件メモリ読み込み
- 各 Match に対して `(today.isoformat(), slug)` が既存ログに含まれていたら skip
- 投稿成功時に append、ファイル fsync、`git add logs/posted.jsonl && git commit -m "post: <date> <slug>"`

#### git commit する理由

- 投稿履歴が repo 内に永久残存(後から「2026 年 5 月の命日投稿一覧を出して」が `grep '"2026-05-' logs/posted.jsonl` で出る)
- Mac を新調 / リストアしても投稿状況が完全再現できる(launchd 再登録 + git pull で完了)
- push はしない(本 spec 内では git commit のみ、push は別途手動 or 別 cron で対応)

### 4.8 失敗ハンドリングと通知

| 失敗パターン | 検知方法 | 対応 |
|---|---|---|
| Bluesky 5xx / 429 | response status | 60 秒待って 1 回リトライ → なお失敗なら skip + Discord |
| Bluesky 401(認証失敗) | response status | リトライせず Discord 通知(App Password 更新が必要) |
| OGP 取得失敗(サイト 404 / network) | requests exception | thumb なしで投稿継続 |
| critique 2 連続 fail | claude_runner の出力 | skip + Discord(生成文 + violations を含める) |
| claude_runner 自体が exit code 非 0 | subprocess returncode | skip + Discord(stderr を含める) |
| matches 0 件 | orchestrator | 何もしない、通知も出さない(平時) |
| launchd 未発火 | cockpit | cockpit が「最終発火 > 2 日」のジョブを赤表示 |

#### Discord 通知メッセージ例

```
🚨 [aoyama-cemetery] Bluesky 投稿失敗
日付: 2026-05-14
対象: okubo-toshimichi (person)
理由: LLM critique 2 回連続 fail
violations: ["frontmatter にない人名『西郷隆盛』が登場"]
最終生成文:
  【本日の命日】大久保 利通(1830-1878)
  維新三傑のひとり、西郷隆盛と袂を分かちながら...
  https://aoyama-cemetery.pages.dev/people/okubo-toshimichi
対応: 手動投稿 or skip を判断してください
```

成功時は通知しない(沈黙 = 正常、Bluesky フィード自体が確認できる場所のため)。

### 4.9 シークレット管理

git 管理外のディレクトリに置く(L0 ルール、`~/.config/` 配下):

```
~/.config/aoyama-cemetery/
├── bluesky.env       # chmod 600
│   BLUESKY_HANDLE=aoyama-cemetery.bsky.social
│   BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
└── discord.env       # chmod 600
    DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

`run.sh` が起動時に source して環境変数として子プロセスに渡す。

## 5. 前提条件(別 PR or 同 PR 内で対応)

### 5.1 Bluesky アカウント新規作成

- Handle: `aoyama-cemetery.bsky.social`(候補、空きがあれば確保)
- プロフィール: 「青山霊園に眠る明治・大正・昭和の偉人を、命日に紹介します。」+ サイト URL
- アバター: サイトの favicon / ロゴと統一
- App Password: 設定画面で 1 個発行、`~/.config/aoyama-cemetery/bluesky.env` に保存
- 本実装着手前にユーザーが手動で完了させる

### 5.2 events ページの ogImage 渡し(現状調査で発見)

`src/pages/events/[slug].astro` の BaseLayout 呼び出しに `ogImage` を渡していないため、events の `heroImage` が OGP に出ない。本 spec の Bluesky 投稿が events を含むため、リンクカードを充実させるために 1 行修正する:

```diff
- <BaseLayout title={title} description={description} jsonLd={[eventJsonLd, breadcrumbJsonLd]}>
+ <BaseLayout title={title} description={description} ogImage={event.data.heroImage?.src} jsonLd={[eventJsonLd, breadcrumbJsonLd]}>
```

これは本 spec の plan 内で同時対応する(切り出して別 PR にする必要はない小修正)。

### 5.3 Discord webhook の作成

- 投稿失敗通知用 Discord webhook を 1 個作成(既存 award-flights / biz-radar チャンネルと別、または同じ専用チャンネルにまとめる)
- URL を `~/.config/aoyama-cemetery/discord.env` に保存

## 6. テスト方針

### unit test(pytest、`admin/.venv` と同じ arm64 venv で実行)

- `test_match.py`: 命日マッチ / events マッチ / personSlugs 空配列除外 / 5 件上限 / 周年順並び
- `test_post_log.py`: JSONL append / 重複検出 / 空ファイル対応
- `test_bluesky_client.py`: `responses` または `httpx_mock` で API mock、createSession / createRecord / uploadBlob / 401・429 リトライ
- `test_orchestrator.py`: claude_runner / bluesky_client / notifier を全部 mock、以下のシナリオ網羅:
  - 0 件マッチ → 何もしない
  - 1 件マッチ → 投稿 → ログ追加
  - 2 件マッチ → 2 件とも投稿
  - critique 1 回目 fail → 再生成 → 2 回目 pass → 投稿
  - critique 2 連続 fail → skip + Discord 通知
  - Bluesky 429 → リトライ → 成功
  - Bluesky 401 → リトライせず Discord 通知
  - 既存ログにある → skip(idempotency)

### 統合テスト(手動、Phase 2 で実施)

- Bluesky 専用アカウントで 1 件の本物投稿 → フィードで OGP カード表示確認 → 削除可能

## 7. 段階的リリース

### Phase 1: スクリプト + テスト(投稿は dry-run)

- 上記ディレクトリ構成・スクリプト・subagent md を作成
- pytest が全 pass
- orchestrator に `--dry-run` フラグを実装、Bluesky API は叩かず生成文を stdout に出すだけで動作確認できる状態にする
- events ページの ogImage 修正(5.2)も同 PR に含める

### Phase 2: 手動 1 件投稿で本番動作確認

- Bluesky 専用アカウントを作成し、シークレットを `~/.config/aoyama-cemetery/` に配置
- `--dry-run` を外して `--once <slug>` で 1 偉人を本物投稿 → フィードで OGP カードと文面を目視確認
- 問題なければそのまま残す、違和感あれば削除して文面調整

### Phase 3: launchd 登録、毎朝 8:05 発火開始

- LaunchAgent plist を `~/Library/LaunchAgents/` に配置
- `launchctl load` で登録、cockpit に拾われることを確認
- 翌朝 8:05 の発火で当日命日マッチがあるか確認(無い日は無投稿で正常)

### Phase 4: 1 ヶ月運用後の振り返り

- 投稿数 / critique fail 率 / Discord 通知回数を `logs/posted.jsonl` と `logs/errors.jsonl` から集計
- 文面品質をフィード遡って目視レビュー
- 必要に応じて post-writer prompt 調整 / 投稿先 SNS 追加 / 節目年対応など次フェーズへ

## 8. 運用

- 投稿アカウント: 青山霊園サイト専用の Bluesky アカウント
- 投稿時刻: 毎朝 8:05 JST(catch-up 有効、Mac スリープ時は起動後すぐ発火)
- マッチなしの日: 無投稿(沈黙)
- 失敗時: Discord 通知 → ユーザーが手動投稿 or skip を判断
- 投稿ログ: `logs/posted.jsonl` に git commit、push は別運用
- 投稿の事後編集: 必要時は手動(Bluesky アプリから直接編集 / 削除)
- App Password 失効: Bluesky 側で再発行 → `~/.config/aoyama-cemetery/bluesky.env` を更新

## 9. 将来の拡張(本 spec のスコープ外)

- 投稿先プラガブル化 → Threads / Mastodon / X 追加
- 節目年(没後 50 / 100 / 150 年)の特別テンプレ
- 誕生日マッチ(命日と別頻度)
- routes(散歩ルート)を週次で 1 本紹介する企画投稿
- works(関連書籍・映像作品)の紹介投稿
- いいね・リプライ集計 → cockpit に統合

## 10. リスクと対応

| リスク | 影響 | 対応 |
|---|---|---|
| Bluesky の API 仕様変更 | 投稿が突然失敗 | bluesky_client.py を局所修正、Discord 通知で気付ける |
| Claude のアップデートで生成品質が変動 | 投稿文のトーンが変わる | post-writer prompt のルール強化、定期目視 |
| Mac が長期間オフ | 当日の命日投稿を逃す | catch-up でカバー、cockpit で稼働監視 |
| 投稿文が事実誤認 | サイトの信頼毀損 | critique + 事後編集可能性で許容範囲、繰り返し起きたら prompt 強化 |
| Bluesky アカウントの BAN / ロック | 投稿停止 | 投稿頻度が月 ~10 件と低いので通常運用では起こりにくい、起きたら手動対応 |
| logs/posted.jsonl が壊れる(同時書き込み等) | 重複投稿リスク | orchestrator は singleton(launchd で多重起動しない)、flock で追記時にロック |

## 11. オープン項目

- Bluesky の handle 候補が利用可能か(`aoyama-cemetery.bsky.social` 等)→ Phase 2 入りで確認
- 投稿のリンクカード見た目の最終調整(og:description の文面が刺さるかは実投稿で見ないと分からない)→ Phase 2 の目視で確認
- Discord 通知チャンネルを既存と統合するか分けるか → Phase 2 入りで判断
