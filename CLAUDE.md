# aoyama-cemetery — L2 規約

## 上位ルール参照

- L0: `~/workspace/CLAUDE.md`
- L1: `~/workspace/personal/CLAUDE.md`

## プロジェクト概要

- 目的: 青山霊園に眠る偉人を紹介する静的サイト
- 公開 URL: https://aoyama-cemetery.pages.dev
- スタック: Astro 6.x + TypeScript strict + @astrojs/sitemap
- ホスティング: Cloudflare Pages(GitHub public repo を watch)
- アクセス: 完全 public
- 設計書: `docs/superpowers/specs/2026-05-21-aoyama-cemetery-site-design.md`
- 実装計画: `docs/superpowers/plans/2026-05-21-aoyama-cemetery-site.md`

## 偉人追加手順

1. **埋葬確認ファースト**: 候補人物を追加する前に必ず青山霊園への埋葬を一次資料で確認する。確認の優先順位は (1) ユーザー提供の `~/Desktop/青山霊園.pptx` → (2) Wikipedia 本人記事 infobox の「墓所: 青山霊園」明記 → (3) 青山霊園 Wikipedia 著名人リスト
   - 「○○系の有名人なので青山霊園にいるはず」というカテゴリ推測でリストアップしない
   - 複数霊園に分骨/改葬されているケースもあるため最新情報で確認
   - 反面教師: 2026-05-23 セッションで 14 名(西郷従道・山田顕義・田中光顕 他)を推測で候補入りさせ後から除外する作業が発生した。詳細: `~/Desktop/Obsidian/claude-code/2026-05-24-aoyama-cemetery-pin未取得偉人リスト.md`
2. `src/content/people/<slug>.md` を作成(slug はローマ字ハイフン区切り、例 `okubo-toshimichi`)
3. frontmatter は `src/content.config.ts` の zod スキーマに準拠、`references` の出典で事実確認(没年月日・役職・業績)
4. **墓所位置**: 区画番号を Wikipedia/港区資料で確認し `graveSection` に記入(地図は「地図機能」章参照)
5. `npm run dev` でローカル目視確認(地図が正しい墓所 POI に着地するかも確認)
6. `git commit && git push` → Cloudflare Pages が自動デプロイ
7. **墓参り写真がある場合**: `./scripts/add-grave-photo.sh <slug> <写真ファイル...>` で自動リサイズ(長辺 1600px / quality 85)+ HEIC→JPEG 変換 + 規則ファイル名で配置。frontmatter 編集不要。仕様: `docs/superpowers/specs/2026-05-21-grave-photo-gallery-design.md`

## 偉人削除手順(墓じまい対応)

青山霊園から墓所が撤去された(墓じまいされた)ことが判明した場合の手順。複数コレクションに連鎖修正が必要(2026-05-24 otori-keisuke / hayashi-tadasu の 2 例で確立)。

1. **削除前に一次資料で墓じまいを確認する(必須)**: 「埋葬確認ファースト」と同じく削除時にも適用。Wikipedia の脚注や伝聞情報だけで削除しない
   - 確認順: ユーザー現地確認(写真・座標) → 管理事務所公式 → `~/Desktop/青山霊園.pptx` → 複数の独立した二次資料
   - **1 ソースのみの情報では削除しない**
   - 反面教師: 2026-05-24 大鳥圭介・林董を未検証で削除 → 翌日ユーザー現地確認で 2 名とも墓所現存判明、復活させた(commit `d218251` 他)
2. **全参照を grep で網羅検出**: `grep -rn "<slug>\|<日本語名>" src/ scripts/` + Obsidian 進捗メモにも grep
3. **完全削除**: `src/content/people/<slug>.md` + `src/assets/portraits/<slug>.jpg`
4. **frontmatter 構造参照を削除**: 他人物の `relatedPeople` / events の `personSlugs` / routes の `stops` から該当 slug を削除
5. **本文記述の判断 — 墓所言及 vs 史実言及**:
   - 削除: 「青山霊園に眠る」「同区画に並ぶ」型(現状と矛盾)
   - 保持: 「日英同盟を調印」「戊辰戦争で旧幕府軍を指揮」型(史実は墓の有無と独立)
   - 中間: events の関係者紹介セクションは保持、末尾「本霊園 ◯◯側に眠る」は「墓所は当初... 墓じまいされ現在は霊園内に墓所はない」に書き換え
6. `scripts/download-portraits.py` の PAIRS エントリ削除(再ダウンロード抑止)+ Obsidian 進捗メモも修正
7. **ビルド検証**: `npm run build` で zod 検証通過 + ページ数 -1 を確認してから commit & push

実例: 林董(hayashi-tadasu)削除では grep 25 箇所 / 7 カテゴリを順に修正、178 → 177 ページ。詳細: `~/Desktop/Obsidian/claude-code/2026-05-24-aoyama-cemetery-墓じまい対応-相楽総三-林董.md`

## 管理画面(`admin/`、2026-05-28 新規)

既存偉人の coords / 墓写真 / frontmatter 編集はローカル Streamlit 管理画面から行う。新規偉人追加は引き続き `/add-person` スラッシュコマンド。

### 起動

```bash
aoyama-ui  # ~/.zshrc alias、内部で arch -arm64 admin/.venv/bin/streamlit run
           # 初回は arm64 venv を自動構築(数分)、以降は数秒で起動
```

ブラウザで http://localhost:8501。フル形は `admin/run.sh`。

### 画面構成

- **Dashboard**: 全 136 偉人の進捗一覧。coords 状態 / 墓写真枚数 / 最終 commit 日時 + フィルタ
- **Person_Edit**: 3 タブ
  - 📍 coords: lat/lng 直接入力 or Google Maps URL ペースト(`@lat,lng` / `?q=lat,lng` 自動抽出)
  - 📸 写真: 既存サムネ + 削除 + 新規アップロード(`scripts/add-grave-photo.sh` に委譲)
  - 📝 frontmatter: raw YAML editor(zod 整合は保存後の `npm run build` 任せ)

### 自動 commit + push(重要)

保存操作ごとに **対象ファイルだけ単独 commit して `origin/main` に自動 push**。Cloudflare Pages が ~2 分で本番反映。

- 保存 = 本番反映。typo に注意。zod 失敗時は build が落ちて旧版が残る
- commit message は操作種別から自動生成(例: `feat(people): okubo-toshimichi coords 更新 (35.667, 139.722)`)
- main ブランチ以外では abort、push 失敗時は UI にエラー表示

### 設計書・実装計画

- spec: `docs/superpowers/specs/2026-05-28-grave-admin-design.md`
- plan: `docs/superpowers/plans/2026-05-28-grave-admin.md`
- 構築ログ: `~/Desktop/Obsidian/claude-code/2026-05-28-aoyama-admin-streamlit-build.md`

### admin 改修時の注意

- `admin/lib/content_io.py` の ruamel.yaml round-trip は 136 件全件 byte 一致テスト済。PyYAML には差し戻さない(コメント・順序破壊)
- `admin/lib/photo_ops.py` のパス包含チェックは `Path.relative_to` を使う(`str.startswith` は sibling 漏れバグあり)
- `@st.cache_resource` は module-level 関数のみ適用(L1 アンチパターン)
- 墓写真サムネ(PIL 処理)は `ImageOps.exif_transpose` を必ず通す。iPhone 写真は EXIF orientation 付きで PIL が無視、ブラウザ/sharp は尊重するため「本番 OK / admin だけ横向き」非対称が起きる(2026-05-29 顕在化)
- pytest は `arch -arm64 admin/.venv/bin/pytest admin/tests/`

## SNS 自動投稿(`scripts/daily_bluesky_post/`、2026-06-03 新規 / 2026-06-04 X 並走化)

毎朝 8:05 JST に本日が命日の偉人 / 該当日 events を **Bluesky と X(旧 Twitter)に独立並走で自動投稿**。launchd + `claude -p` Max plan 経路 + subagent 2 段 ×2 platform 構成(`aoyama-post-writer{,_x}` / `aoyama-fact-checker{,_x}`)。ディレクトリ名は歴史的経緯で `daily_bluesky_post` のままだが実態は multi-platform。

### 起動 / セットアップ

1. シークレット配置(`~/.config/aoyama-cemetery/` 配下、フォーマット詳細は `scripts/daily_bluesky_post/README.md`):
   - `bluesky.env`(必須): `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD`
   - `discord.env`(任意): `DISCORD_WEBHOOK_URL`
   - `x.env`(X 並走時のみ): `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_SECRET`, `X_ENABLED=0/1`
2. dry-run: `scripts/daily_bluesky_post/run.sh --dry-run --today 2026-05-14`
3. launchd 登録: `infra/launchd/README.md` 手順に従う

### アーキテクチャ概要

`launchd 08:05 JST → run.sh(env 読み込み)→ orchestrator.py → match.py(命日 + events 集約)→ for match in matches: _process_bluesky + _process_x → posted_*.jsonl 追記 → git_commit.commit_posted_logs で 1 commit → 失敗時は Discord 通知`

両 platform は**独立並走**。片方失敗してももう片方は継続。X auth_fail / rate_limit は当日以降の X 処理を bypass(Bluesky は影響なし、逆も同様)。

詳細: `docs/superpowers/specs/2026-06-03-bluesky-auto-post-design.md` / `2026-06-03-x-auto-post-design.md` / `docs/superpowers/plans/2026-06-04-x-auto-post.md`

### 注意事項(両 platform 共通)

- 子プロセスから `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` を必ず strip(L0 知見、`claude_runner._child_env` 参照)
- `--allowed-tools` は `-p` より前に置く(L0 知見、`claude_runner.generate_post` 参照)
- subagent 定義 4 本は frontmatter + body のみを根拠にする厳格ルールを保つ
- post-writer が body 外の有名な逸話・統計値を加えがちなので「**body にあるかどうかが唯一の判定軸**」を subagent prompt で繰り返し明示(2026-06-04 「死後 8000 円の借金」等で顕在化、5a として禁止条項強化済み)
- `logs/posted_bluesky.jsonl` / `posted_x.jsonl` は git commit する(idempotency)
- `gen_fail` は subagent の確率的ブレで起きる(再実行で復活が多い)。1 回 retry 後諦め Discord 通知 → 人間に handle
- **launchd plist には `<key>ProcessType</key><string>Interactive</string>` を必ず入れる**
  - 未指定だと launchd が Background QoS と判定し、`claude -p --allowed-tools Agent`(subagent)起動時の peak memory で jetsam SIGKILL(exit -9)される
  - GUI session 経由なら同 binary・同 prompt で正常動作するため切り分けが難しい
  - biz-radar が launchd + claude -p で動いていたのは subagent 未使用(`--allowed-tools "WebSearch,WebFetch"`)だったため
  - 判定: `launchctl print gui/$(id -u)/<label>` で `spawn type = interactive (4)` / `jetsam priority = 40` を確認
  - 2026-06-05 朝の自動投稿で顕在化、`logs/launchd.err.log` の `claude exit -9` が手がかり

### Bluesky 側の注意

- **facet の index は UTF-8 byte offset** で計算(grapheme/char ではない)。本文 URL を clickable にする時、日本語混在で 1 文字 = 3 byte になるため `text.encode("utf-8").rfind(...)` で byte 位置計算が必要(2026-06-03 facet 実装時に確立、`bluesky_client._build_url_facets` 参照)
- atproto SDK の embed.external.thumb は pydantic strict validation。テスト fixture には本物の `BlobRef(...)` を渡す(MagicMock は `ValidationError`)
- 本文に URL を含めて投稿(Bluesky 課金ゼロ)。300 grapheme 上限の安全マージン 290 で生成

### X 側の注意

- **X API は完全 Pay-Per-Use(2025 移行)、Free tier は実質廃止**。新規アカウントは無料クレジットなしで起動 → 運用前に「クレジットを購入」($5 最小)で先払い
- 単価(2026-06-04 docs.x.com で確認):
  - POST /2/tweets(通常)= **$0.015 / request**
  - POST /2/tweets(**URL 含み**)= **$0.200 / request**(13 倍ジャンプ、最大の罠)
  - POST /1.1/media/upload(metadata)≒ $0.005 / request
- **本案件は URL を本文に含めない方針**(月 60-90 投稿 × $0.20 = ¥1,800-2,700/月を回避)。サイト誘導は X profile bio の website 欄に 1 回固定設置で代替。post-writer-x.md §5a で URL 混入を禁止、fact-checker-x.md でも検査
- 構成 3 行(タイトル / 本文 100-130 字 / `#青山霊園` + 任意 1 ハッシュタグ)、URL 行なし
- 字数カウントは **X weighted units**(CJK=2, ASCII=1)、safe limit 270 で `x_text.x_weighted_length` 計測
- 支出上限は Developer Console → 請求書 → クレジット → 支出上限 で **月 $5 or $10 推奨**
- OAuth 1.0a User Context(`tweepy.Client` v2 + `tweepy.API` v1.1)、Settings で **Read and write** + **Web App, Automated App or Bot** を Token 生成 **前** に設定(順序逆だと Read-only token → 403)
- env 命名: コンシューマーキー=`X_API_KEY` / コンシューマーキーシークレット=`X_API_SECRET` / アクセストークン=`X_ACCESS_TOKEN` / アクセストークンシークレット=`X_ACCESS_SECRET`。OAuth 2.0 のクライアント ID/シークレットは未使用

### テスト

`PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/`(2026-06-04 時点 91 件 pass)

## events の personSlugs 記載基準(直接関与ファースト)

events 追加・更新時、`personSlugs` に人物を記載する基準は「**その事件に直接関与した青山霊園埋葬者**」のみに限定。

### 記載してよい役割

- 主導者・首謀者(王政復古の大久保利通)
- 指揮官・司令官(沖縄戦の牛島満第三十二軍司令官)
- 当事者・参加者(桜田門外の変の有村次左衛門)
- 条約・法律の調印者・責任者(治安維持法の加藤高明首相)
- 殉死者など事件と一体化した行為者(明治天皇崩御の乃木希典夫妻)

### 記載してはいけない人物

- 同時代に生きていただけ(ペリー来航時に幼児だった乃木希典)
- 分野・領域が近いだけ(朝鮮戦争に経済政策で対応した蔵相)
- 事件の影響を後に受けた(安保闘争鎮静化を担った後継首相)
- 弾圧された側だが本人は無関係(桜田門外の有村を安政の大獄に紐付け)

### スキーマと運用

- スキーマは `personSlugs: z.array(z.string()).default([])` で**空配列を許容**(`.min(1)` ではない)
- 全員に無理に紐付けるより、空配列のまま「青山霊園関係者が誰も関与していない歴史的背景事件」として残す方が正確
- `events/[slug].astro` は `relatedPeople.length > 0` のときのみ「関連する偉人」セクションと JSON-LD `about` を表示

### 本文最終段との整合

- personSlugs に人物が残っている: 「本霊園に眠る◯◯は...」段落も残す
- personSlugs から外した: 該当人物への本文言及も削除し史実の俯瞰文に書き換える
- 完全に空配列: 「本霊園に眠る」段落自体を削除し事件の歴史的位置付けで段落を締める

### 違反した実例(2026-05-26)

19 件の event 追加時に旧 `.min(1)` 制約下で無理紐付け → ユーザーから「ペリー来航に大久保達が関与は無理がある」と指摘。schema を `.default([])` に変更し、10 件空配列化・3 件縮減・6 件のみ維持で大規模再評価実施(commit `6f12d63`)。本ルールの不在が原因。

## 地図機能

地図は **デフォルト ON**。`src/pages/people/[slug].astro` で本文下に Google Maps の iframe を表示。frontmatter で 4 通りに制御:

| frontmatter | 地図 URL | 用途 |
|---|---|---|
| 何も書かない(デフォルト) | `?q={name}の墓 青山霊園` 名称検索 | Google Maps が POI を持つ著名な偉人(最多) |
| `mapQuery: "..."` | 指定文字列で検索 | デフォルトクエリで POI に着地しない時の上書き |
| `coords: { lat, lng }` | `?q={lat},{lng}` 座標方式 | POI 未登録だが正確な座標がわかる場合 |
| `hideMap: true` | 非表示 | どのクエリでも POI が出ない |

優先順位: `hideMap` > `coords` > `mapQuery` > デフォルト。iframe・リンクとも keyless。`coords` のスキーマ範囲は青山霊園内に限定(範囲外だと zod が build を弾く)。トップページ overview 地図は持たない設計。

### 新規偉人で地図を確認する手順

1. `npm run dev` で偉人ページを開く、または `https://www.google.com/maps?q={偉人名}の墓+青山霊園` を直接検索
2. **正しい墓所 POI に着地** → 何もしなくて OK
3. **POI が出ない / 違う場所** → 以下を順に試す
   - `mapQuery: "{偉人名}の墓"`(「青山霊園」を外す、例: 北里柴三郎・黒田清隆・加藤高明で有効)
   - 別の表記(`{偉人名}先生の墓` 等)を `mapQuery`
   - Google Maps 航空写真で正確な lat/lng → `coords: { lat, lng }`
   - どれも駄目なら `hideMap: true`(例: 御木本幸吉)

### POI 自動判定スクリプト

`scripts/verify-map-pois.py` で全偉人の地図 POI 着地を一括検証。

```bash
python3 scripts/verify-map-pois.py
```

判定:
- ✅ **OK**: spotlit(固有 POI 着地)
- ⚠️ **CATEGORICAL**: 複数候補のみ → `mapQuery` で別表記
- ⚠️ **GENERIC_POI**: 青山霊園マスター POI (35.6656277, 139.7220659) → `hideMap: true` 推奨
- **SKIP**: `hideMap` または `coords` 設定済

要対応件数で exit code 1 を返すので CI 組込可能。

### coords 取得手順(Google Maps 航空写真)

1. Google Maps で「青山霊園」を開き航空写真モード
2. `graveSection` の区画番号(例 `1種イ8号8側`)を区画案内図と照合
3. 該当位置を右クリック → 緯度経度をコピー
4. frontmatter に `coords:\n  lat: 35.66xx\n  lng: 139.71xx`

**注意: 立山墓地と本園で同じ番地表記が独立に存在する**。番地表記だけで位置を断定せず、必ず coords(または現地確認)と合わせて見る。立山墓地側は `graveSection` 末尾に「(立山墓地)」と注記する慣習を推奨(2026-05-25 立見尚文「1種イ1号3側」は立山墓地内で本園 1種イ1号 と別物、ユーザー現地確認済)。

### 散歩ルートマップの walkOrder(マーカー番号 ≠ 歩行順)

各 route の `RouteMap.astro` は Leaflet で経路 polyline を描画。デフォルトは stops 配列順(物語順・時系列順)で結ぶが、物理的歩行効率とは別。`walkOrder` で polyline 描画順を上書き可能。

| frontmatter | polyline の結ばれ方 |
|---|---|
| `walkOrder` 未指定 | stops 配列順(=マーカー番号順、=物語順) |
| `walkOrder: [3, 1, 2, 5, 4]` 等の 1-indexed 配列 | 指定順で結ぶ。マーカー番号は stops 順のまま変化なし、線だけ効率順 |

凡例(地図直下)で「マーカー番号 = 人物紹介の順番、経路ライン = 効率順」を自動表示。

**重要: stops 変更時は walkOrder を必ず再生成**:
- walkOrder は 1-indexed 絶対インデックスで、stops 増減でずれる
- stops 長 ≠ walkOrder 長 なら RouteMap が自動的に stops 順 fallback(zod は通る、一時的に動くが意図と違う表示)
- 一時無効化は frontmatter で `# walkOrder: [...]` とコメントアウト
- 実例: 2026-05-25 sakanoue-no-kumo に林董を 3 番目に追加 → 旧 walkOrder 一時無効化 → 新 walkOrder に再生成

## 散歩ルートに偉人を追加する手順

既存ルート(`src/content/routes/<route>.md`)に新規偉人を追加する場合、5 箇所の連動更新が定型化(2026-05-25 林董の sakanoue-no-kumo / boshin-hokuetsu 追加で確立)。

0. **追加偉人の coords が設定済か確認(必須)**: coords も `hideMap: true` も未設定の偉人を stops に含めると `showRouteMap` 条件で **ルート全体の経路マップが非表示** になる。2026-05-25 山下源太郎・牛島満を coords 未取得で追加 → sakanoue-no-kumo・taiheiyo-senso のマップが消えた(commit `37ef39f` / `dbe7c44` で除外復旧)
1. **frontmatter `stops` に追加**: 適切な位置(時系列 or 物語順)に slug + note
2. **frontmatter `estimatedMinutes` を更新**: 1 名追加で 10-15 分加算が目安
3. **frontmatter `description` を更新**: 「N 名」のカウントや偉人カテゴリ列挙を再構成
4. **本文「## このコースの楽しみ方」を更新**: ルート概要・経路順リスト・対比的説明文を反映
5. **本文「Google Maps で散歩経路を開く」セクションの URL を再生成**: waypoints をパイプ `%7C` 区切りで連結
6. **`walkOrder` を自動再生成**: `python3 scripts/generate-walk-order.py` で全ルートを NN-TSP + 2-opt で書き戻し(`--dry-run` でプレビュー可)
7. **estimatedMinutes・本文の総距離/所要時間を再計算**: 公式は **実距離 = 直線距離(walkOrder順) × 1.4(曲がり道補正) / walk 15 分/km + visit 7 分/人 / 5 分単位 round**

ビルド検証: `npm run build` で zod 通過 + dev server で目視確認。

## コンテンツ方針

- 出典: Wikipedia(CC BY-SA)等の公開情報をベースに Claude が要約・再構成
- 直接コピペ禁止、必ず再構成 + `references` に出典明記
- 肖像写真は public domain(没後 70 年経過済)のみ
- 事実誤認は致命傷なのでビルド前にユーザー目視確認を必ず通す
- **本文に `**bold**` 記法を使わない**: プレーンテキストで記述。LLM 生成時に強調したくなる衝動を抑える(画面では地の文の流れが大事、structural な強調はセクション見出しで効いている)。2026-05-22 に過去 54 ファイル × 約 3,500 個の `**` を一括 strip(commit `942a704`)。works コレクションも同様
- **frontmatter `era`(元号ラベル)の判定基準**: 当人の主要な活動・功績が現れた時代を基準、schema は最大 2 値まで
  - 維新志士・幕末活動者は江戸末期の活動も含める(大久保利通・乃木希典・西周など `[江戸, 明治]`)
  - お雇い外国人は来日後の活動を基準(キヨッソーネ 1875 来日 = `[明治]`、フルベッキは 1859 来日 = `[江戸, 明治]`)
  - 外国人(本国メイン活動)で日本活動が明治以降のみは `[明治]`(金玉均 — 朝鮮政治家、亡命は明治期)
  - 2026-05-22 に 13 名を本ルールで再検証(commit `e477079`)

## 肖像写真の取得(Wikimedia Commons)

肖像写真を Wikimedia Commons から一括取得する際、**`Special:FilePath` への直接アクセスは避ける**(レート制限 HTTP 429 が厳しく、~10 件連続で ban)。代わりに MediaWiki API で `thumburl` を取得してダウンロード。

```
NG: https://commons.wikimedia.org/wiki/Special:FilePath/<filename>  → 429 連発
推奨: https://commons.wikimedia.org/w/api.php?action=query&titles=File:<filename>
        &prop=imageinfo&iiprop=url&iiurlwidth=600&format=json
      → imageinfo[0].thumburl が CDN URL、レート制限が緩い
```

再利用スクリプト: `scripts/download-portraits.py`(slug ↔ ファイル名のリストを定義、idempotent)。frontmatter には `portrait: ../../assets/portraits/<slug>.jpg` + `portraitCredit: Wikimedia Commons / Public Domain` を統一して付与。

### Public Domain 判定の事前チェック

新規偉人追加前に**没年から 70 年経過しているか**を確認。日本国内の著作権法は **著作者の死後 70 年**で Public Domain(2018 年 12 月 30 日施行・TPP 関連法改正)。

- 判定式: `今年 - 没年 ≥ 71` で PD 経過(没年当年は計算に含まない年起算)
- 70 年未経過の人物は `portrait` フィールドなしで作成、ページ上部は冒頭文の視覚的インパクトで補う
- 境界年は Wikipedia の File ページで `{{PD-Japan}}` テンプレートで確認
- 例(PD 未経過): 星新一(1997 没 → 2068 年)、橋本龍太郎(2006 没 → 2077 年)

### events heroImage 取得の補完テクニック(url 一時書き換え)

`scripts/fetch-event-images.py` は md の `url:` フィールドから記事を解決し、pageimage API + imageinfo API でライセンス白リスト(PD/CC0/CC-BY/CC-BY-SA)合致の画像のみ取得して frontmatter 自動更新。

事件記事に画像がない・ライセンス不適合・国旗や紋章しか取れない等で SKIP / 弱画像になった event は、**md の `url:` を関連 Wikipedia 記事に一時書き換え → 再実行 → 元の url に戻す** ワークアラウンドで補完できる(スクリプト本体は触らない)。

書き換え先候補の優先順位:
1. **当事者・主導者の人物 Wikipedia 記事**(肖像が取れる、最も汎用的): 安政の大獄 → `井伊直弼` / 学制発布 → `大木喬任` / 国際連盟脱退 → `松岡洋右`
2. **サブ記事・関連記事**(画像のバリアントが取れる): 満州事変 → `柳条湖事件`(本記事は紋章のみ、サブ記事は爆破地点写真)
3. **別の関連人物**(第一候補がライセンス不適のフォールバック): 壬午事変 → `閔妃`(韓国 KOGL Type 1 で白リスト外) → `三浦梧楼`

手順:
1. md の `url:` を一時書き換え(Edit で 1 行)
2. 弱画像時は既存の `heroImage` / `heroImageCaption` / `heroImageCredit` 3 行削除 + 画像ファイルも削除
3. `python3 scripts/fetch-event-images.py` 再実行(取得済 event は自動 skip)
4. 取得成功後、url を元の事件名記事に戻す

注意: heroImageCredit が複数行 YAML scalar の場合 Edit が失敗するため Python の `re.sub` で multiline 削除が安全。実例: 2026-05-26 新規 19 件中 4 件 SKIP + 3 件弱画像を本手法で補完、全 19 件で適切な heroImage 取得(commit `e0453e9`)。

## frontmatter 記法の注意

people / works の frontmatter で、**値にコロン `:` を含む文字列はダブルクオートで囲む**。YAML パーサが「キー: 値」構造と誤認識して `bad indentation of a mapping entry` エラーで build が止まる。

```yaml
# ✗ NG
creator: NHK / 脚本: 大森美香
publisher: 文藝春秋(訳: 廣中和歌子)

# ✓ OK
creator: "NHK / 脚本: 大森美香"
publisher: "文藝春秋(訳: 廣中和歌子)"
```

特に works コレクションの `creator` / `publisher`(脚本家・原作者・訳者などコロン頻出)で踏みやすい。新規 markdown 追加後は `npm run build` で YAML 検証を通す。

## 開発コマンド

```bash
npm install
npm run dev      # http://localhost:4321
npm run build    # dist/ 生成
npm run preview  # 本番相当を確認
```

## デプロイ前提

- Cloudflare Pages 環境変数: `NODE_VERSION=22`(Astro 6 は >=22.12.0 要求)
- Build command: `npm run build`
- Build output: `dist`
- Framework preset: Astro
