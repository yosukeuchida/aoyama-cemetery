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

0. **埋葬確認ファースト**: 候補人物を追加する前に、必ず青山霊園への埋葬を一次資料で確認する。「○○系の有名人なので青山霊園にいるはず」というカテゴリ推測でリストアップしない。確認の優先順位は (1) ユーザー提供の `~/Desktop/青山霊園.pptx`(現地調査ベースの一次資料)→ (2) Wikipedia 本人記事の冒頭 infobox の「墓所: 青山霊園」明記 → (3) 青山霊園 Wikipedia 著名人リスト の順。複数霊園に分骨されているケース・改葬されたケースがあるため必ず最新の情報で確認する。本ルールを怠った例: 2026-05-23 セッションで西郷従道(多磨)・山田顕義(護国寺)・田中光顕(護国寺)・福地源一郎(谷中)・大久保一翁(多磨/本妙寺)・久米邦武(賢崇寺)・樺山資紀(染井)・山尾庸三(海晏寺)・浅野総一郎(總持寺)・内田康哉(多磨)・川村純義(多磨)・鳩山和夫(谷中)・中野正剛(多磨)・志賀重昂(宗源寺) の 14 名を「青山霊園にいるはず」で候補リスト入りさせ、後から除外する作業が発生した
1. `src/content/people/<slug>.md` を作成(slug はローマ字ハイフン区切り、例 `okubo-toshimichi`)
2. frontmatter は `src/content.config.ts` の zod スキーマに準拠
3. 事実確認(没年月日・役職・業績)を `references` の出典で照合
4. **墓所位置**: 区画番号を Wikipedia/港区資料で確認し `graveSection` に記入(地図は次項参照)
5. `npm run dev` でローカル目視確認(地図が正しい墓所 POI に着地するかも確認)
6. `git commit && git push` → Cloudflare Pages が自動デプロイ
7. **墓参り写真がある場合**: `./scripts/add-grave-photo.sh <slug> <写真ファイル...>` で自動的にリサイズ(長辺 1600px / quality 85)+ HEIC→JPEG 変換 + 規則ファイル名で配置される。frontmatter 編集不要、`src/assets/grave-photos/<slug>/YYYY-MM-DD-<caption>.jpg` に置けば自動でギャラリー表示。詳細: `docs/superpowers/specs/2026-05-21-grave-photo-gallery-design.md`

## 偉人削除手順(墓じまい対応)

青山霊園から墓所が撤去された(墓じまいされた)ことが判明した場合、偉人ページを削除する。単純な人物ページ削除では完結せず、複数コレクションに連鎖修正が必要(2026-05-24 に otori-keisuke / hayashi-tadasu の 2 例で確立した手順)。

0. **削除前に一次資料で墓じまいを確認する(必須)**: 「埋葬確認ファースト」ルールは追加時だけでなく削除時にも適用する。Wikipedia の脚注や伝聞情報だけで削除しないこと。確認の優先順位は (1) ユーザー現地確認(写真・座標)→ (2) 青山霊園管理事務所の公式情報 → (3) ユーザー提供 `~/Desktop/青山霊園.pptx` → (4) 複数の独立した二次資料(Wikipedia 本人記事 + 別ソース、両方が「墓じまい」を明記)。1 ソースのみの情報では削除しない。**2026-05-24 に大鳥圭介(otori-keisuke)・林董(hayashi-tadasu)を未検証の墓じまい情報で削除したが、翌日ユーザー現地確認で 2 名とも墓所現存が判明し復活させた**(commit `d218251` 等)。

1. **全参照を grep で網羅検出**: `grep -rn "<slug>\|<日本語名>" src/ scripts/` と Obsidian 進捗メモにも grep をかける
2. **完全削除**: `src/content/people/<slug>.md` + `src/assets/portraits/<slug>.jpg`
3. **frontmatter 構造参照を削除**:
   - 他人物の `relatedPeople` から該当 slug エントリ
   - events の `personSlugs` から該当 slug
   - routes の `stops` から該当 slug(該当する場合)
4. **本文記述の判断 — 墓所言及 vs 史実言及**:
   - 削除する: 「青山霊園に眠る」「同区画に...が並ぶ」型の墓所言及(現状と矛盾するため)
   - 保持する: 「駐英公使として日英同盟を調印」「戊辰戦争で旧幕府軍を指揮」型の歴史的事実(史実は墓の有無と独立、周辺人物の文脈形成に必要)
   - 中間: events の関係者紹介セクション自体は史実なので保持、ただし末尾「本霊園 ◯◯側に眠る」は「墓所は当初... 後に墓じまいされ現在は同霊園内に墓所はない」に書き換え
5. **scripts/download-portraits.py の PAIRS エントリ削除**(再ダウンロード抑止)
6. **Obsidian 進捗メモも修正**(`~/Desktop/Obsidian/claude-code/2026-05-24-aoyama-cemetery-pin未取得偉人リスト.md` 等)
7. **ビルド検証**: `npm run build` で zod 検証通過 + ページ数 -1 を確認してから commit & push

実例: 2026-05-24 林董(hayashi-tadasu)削除では grep 25 箇所 / 7 カテゴリ(人物ファイル・portrait・relatedPeople 7 ファイル・events 1 件・本文墓所言及 6 ファイル・routes 3 ファイル・script・Obsidian)を順に修正、178 → 177 ページ。詳細: `~/Desktop/Obsidian/claude-code/2026-05-24-aoyama-cemetery-墓じまい対応-相楽総三-林董.md`

## 管理画面(`admin/`、2026-05-28 新規)

既存偉人の coords / 墓写真 / frontmatter 編集はローカル Streamlit 管理画面から行う(都度 vim + git の手作業を置換)。新規偉人追加は引き続き `/add-person` スラッシュコマンド。

### 起動

```bash
aoyama-ui  # ~/.zshrc alias、内部で arch -arm64 admin/.venv/bin/streamlit run
           # 初回は arm64 venv を自動構築(数分)、以降は数秒で起動
           # 終了は Ctrl+C
```

ブラウザで http://localhost:8501 を開く。フル形は `~/workspace/personal/aoyama-cemetery/admin/run.sh`。

### 画面構成

- **Dashboard**(`admin/Dashboard.py`): 全 136 偉人の進捗一覧。coords 状態(✅ / ❌ / hideMap)、墓写真枚数、最終 commit 日時を表示。名前 / slug 部分一致 + 状態フィルタで絞り込み、行クリックで個人詳細へ。
- **Person_Edit**(`admin/pages/Person_Edit.py`): 3 タブ構成。
  - 📍 **coords**: lat/lng 直接入力 or Google Maps URL ペースト(`@lat,lng` / `?q=lat,lng` 自動抽出)。「青山霊園を別タブで開く」ボタンで航空写真表示。
  - 📸 **写真**: 既存写真サムネ + 削除、新規アップロード(複数選択可、`scripts/add-grave-photo.sh` に subprocess 委譲)。
  - 📝 **frontmatter**: raw YAML editor。zod 整合は admin では検証せず保存後の `npm run build` 任せ(過剰検証回避)。

### 自動 commit + push(重要)

保存操作ごとに **対象ファイルだけ単独 commit して `origin/main` に自動 push** する。Cloudflare Pages が自動 build/deploy(~2 分)で本番反映される。

- 撤回した旧設計: 「admin は working tree 更新のみ、commit/push は手動」(spec §3)→ 単一ユーザー運用で摩擦過大、自動化に変更
- 影響: admin で保存 = 本番に出る。typo や誤入力に注意。zod 検証で build が落ちれば旧版が残る(Cloudflare は失敗ビルドを切り替えない)
- commit message は操作種別から自動生成(例: `feat(people): okubo-toshimichi coords 更新 (35.667, 139.722)`)
- main ブランチ以外では abort、push 失敗は UI にエラー表示

### ディレクトリ構成

```
admin/
├ Dashboard.py            # 進捗一覧 + フィルタ
├ pages/Person_Edit.py    # 3 タブ
├ lib/
│   ├ content_io.py       # frontmatter round-trip (ruamel.yaml、PID 付き tmp で race 防止)
│   ├ photo_ops.py        # add-grave-photo.sh subprocess wrapper
│   ├ git_ops.py          # read-only: last_commit_date / uncommitted_count
│   ├ audit_log.py        # JSONL 操作ログ
│   └ publish.py          # 自動 commit + push(main ブランチ限定)
├ tests/                  # pytest 33 件
├ requirements.txt
└ run.sh                  # arch -arm64 venv 起動ラッパー
```

### 設計書 / 実装計画

- spec: `docs/superpowers/specs/2026-05-28-grave-admin-design.md`
- plan: `docs/superpowers/plans/2026-05-28-grave-admin.md`
- 構築セッションログ: `~/Desktop/Obsidian/claude-code/2026-05-28-aoyama-admin-streamlit-build.md`

### admin 改修時の注意

- `admin/lib/content_io.py` の ruamel.yaml round-trip は 136 件全件で byte 一致テスト済。PyYAML には差し戻さない(コメント・順序破壊する)
- `admin/lib/photo_ops.py` のパス包含チェックは `Path.relative_to` を使う(`str.startswith` は sibling ディレクトリ漏れバグあり、code review で検出済)
- `@st.cache_resource` は **module-level 関数のみ** 適用(L1 アンチパターン)
- 墓写真サムネイルなどスマホ写真を PIL で処理する箇所は `ImageOps.exif_transpose` を必ず通す。iPhone 写真は EXIF orientation(例: 6=90°回転)付きでピクセルは横のまま保存されるため、PIL は無視して横向きになる(ブラウザ・Astro/sharp は EXIF を尊重するので「本番は正しいのに admin だけ横向き」という非対称が起きる)。2026-05-29 に Person_Edit.py の data URI サムネイルで顕在化
- pytest は `arch -arm64 admin/.venv/bin/pytest admin/tests/`

## events の personSlugs 記載基準(直接関与ファースト)

events 追加・更新時、`personSlugs` に人物を記載する基準は「**その事件に直接関与した青山霊園埋葬者**」のみに限定する。

### 記載してよい役割

- 主導者・首謀者(例: 王政復古の大久保利通)
- 指揮官・司令官(例: 沖縄戦の牛島満第三十二軍司令官)
- 当事者・参加者(例: 桜田門外の変の有村次左衛門)
- 条約・法律の調印者・責任者(例: 治安維持法の加藤高明首相)
- 殉死者など事件と一体化した行為者(例: 明治天皇崩御の乃木希典夫妻)

### 記載してはいけない人物

- 同時代に生きていただけの人物(例: ペリー来航時に幼児だった乃木希典)
- 分野・領域が近いだけの人物(例: 朝鮮戦争に対して経済政策で対応した蔵相)
- 事件の影響を後に受けた人物(例: 安保闘争鎮静化を担った後継首相)
- 弾圧された側ではあるが本人は無関係な事件(例: 桜田門外の有村を安政の大獄に紐付ける)

### スキーマと運用

- events スキーマは `personSlugs: z.array(z.string()).default([])` で**空配列を許容**する(`.min(1)` ではない)
- 全員に無理に紐付けるより、空配列のまま「青山霊園関係者が誰も関与していない歴史的背景事件」として残す方が正確
- `events/[slug].astro` は `relatedPeople.length > 0` のときのみ「関連する偉人」セクションと JSON-LD `about` を表示する

### 本文最終段との整合

- personSlugs に人物を残した場合: 本文末尾の「本霊園に眠る◯◯は...」段落も残す
- personSlugs から外した場合: 該当人物への本文言及も削除し、史実の俯瞰文に書き換える(矛盾を避ける)
- 完全に空配列にした場合: 「本霊園に眠る」段落自体を削除し、事件の歴史的位置付けで段落を締める

### 違反した実例(2026-05-26)

2026-05-26 に 19 件の event を追加した際、旧スキーマ `min(1)` 制約下で「同時代に生きていた人物」「分野が近い人物」を 19 件すべてに紐付け、ユーザーから「ペリー来航に大久保達が関与している人物というのは無理がありすぎる」と指摘を受けた。schema を `.default([])` に変更し、10 件を空配列化・3 件を縮減・6 件のみ維持する大規模再評価を実施(commit `6f12d63`)。本ルールの不在が原因の事故。

## 地図機能

地図は **デフォルト ON**。偉人ページ(`src/pages/people/[slug].astro`)で本文下に Google Maps の iframe を表示する。frontmatter で挙動を 4 通りに制御:

| frontmatter | 地図 URL | 用途 |
|---|---|---|
| 何も書かない(デフォルト) | `?q={name}の墓 青山霊園` の **名称検索方式** | Google Maps が POI を持っている著名な偉人。最も多いパターン |
| `mapQuery: "..."` | 指定文字列で検索 | デフォルトクエリで POI に着地しない場合の上書き(例: `北里柴三郎の墓` のように「青山霊園」を外すと spotlit になる偉人がいる) |
| `coords: { lat, lng }` | `?q={lat},{lng}` の **座標方式** | POI 未登録だが正確な座標がわかる場合(座標ピンが立つだけで POI ラベルは出ない) |
| `hideMap: true` | 地図セクション非表示 | どのクエリでも POI が出ない、または出したくない場合 |

優先順位: `hideMap` > `coords` > `mapQuery` > デフォルト

- iframe・「Google マップで開く」リンクとも keyless(API key 不要)
- `coords` のスキーマ範囲は青山霊園内に限定(範囲外だと zod が build を弾く)
- トップページに複数ピンの overview 地図は持たない(個別偉人ページで完結する設計)

### 新規偉人で地図を確認する手順

1. ローカル(`npm run dev`)で偉人ページを開く、または `https://www.google.com/maps?q={偉人名}の墓+青山霊園` を直接ブラウザで検索
2. **正しい墓所 POI に着地する** → 何もしなくて OK(デフォルトで地図表示)
3. **POI が出ない / 違う場所が出る** → 以下を順に試す
   - `mapQuery: "{偉人名}の墓"`(「青山霊園」を外す)で spotlit になる偉人がいる(例: 北里柴三郎・黒田清隆・加藤高明)
   - 別の表記(`{偉人名}先生の墓` 等)を `mapQuery` に試す
   - Google Maps 航空写真で正確な lat/lng を取得して `coords: { lat, lng }` を frontmatter に追加(座標ピン)
   - どれも駄目なら `hideMap: true`(例: 御木本幸吉)

### POI 自動判定スクリプト

`scripts/verify-map-pois.py` で全偉人の地図 POI 着地を一括検証できる。新規偉人追加後や push 前のチェック用:

```bash
python3 scripts/verify-map-pois.py
```

判定基準:
- ✅ **OK**: spotlit パターン(固有 POI 着地)
- ⚠️ **CATEGORICAL**: 複数候補のみ(具体的 POI 未着地)→ `mapQuery` で別表記を試す
- ⚠️ **GENERIC_POI**: 着地座標が青山霊園マスター POI (35.6656277, 139.7220659) → `hideMap: true` 推奨(個別の墓ではなく霊園そのものを指している)
- **SKIP**: `hideMap` または `coords` 設定済

要対応件数が出たら exit code 1 を返すので CI にも組み込み可能。

### coords 取得手順(Google Maps 航空写真)

1. Google Maps で「青山霊園」を開き航空写真モードに切替
2. `graveSection` の区画番号(例 `1種イ8号8側`)を区画案内図と照合して位置を絞り込む
3. 該当位置を右クリック → 緯度経度をコピー
4. frontmatter に追加: `coords:\n  lat: 35.66xx\n  lng: 139.71xx`(範囲外だと zod が build を弾く)

**注意: 立山墓地と本園で同じ番地表記が独立に存在する**。「1種イ1号3側」など本園(本園北側、lat ~35.667-35.668 帯)に存在する番地と同名の区画が、附属の立山墓地(本園南側、lat ~35.663-35.664 帯)にも存在する。番地表記だけで位置を断定せず、必ず coords(または現地確認)と合わせて見ること。立山墓地側は `graveSection` 末尾に「(立山墓地)」と注記する慣習を推奨するが、注記なしの既存エントリも実在する(2026-05-25 立見尚文「1種イ1号3側」は立山墓地内で正確、本園の1種イ1号 区画とは別物 — ユーザー現地確認済)。

### 散歩ルートマップの walkOrder(マーカー番号 ≠ 歩行順)

各 route の `RouteMap.astro` は Leaflet で経路 polyline を描画する。デフォルトは stops 配列順(=物語順・時系列順)で結ぶが、物理的に効率の良い歩行順とは別のことが多い。`walkOrder` フィールドで polyline 描画順を上書きできる。

| frontmatter | polyline の結ばれ方 |
|---|---|
| `walkOrder` 未指定(デフォルト) | stops 配列順(=マーカー番号順、=物語順)で結ぶ |
| `walkOrder: [3, 1, 2, 5, 4]` 等の 1-indexed 配列 | 指定された順番で stops を結ぶ。マーカー番号は stops 順のままで変化なし(物語順)、線だけが効率順 |

```yaml
# routes/*.md の frontmatter 例
stops:
  - slug: a
  - slug: b
  - slug: c
walkOrder: [2, 3, 1]   # マーカー番号は 1=a, 2=b, 3=c のまま、線は b→c→a の順で結ぶ
```

凡例(地図直下)で「マーカー番号 = 人物紹介の順番、経路ライン = 効率よく歩ける順番」を自動表示。

**重要: stops 変更時は walkOrder を必ず再生成すること**。walkOrder は 1-indexed の絶対インデックスなので、stops に追加・削除があるとインデックスがずれる。
- stops の長さ ≠ walkOrder の長さ なら RouteMap は自動的に stops 順 fallback(zod は通る)
- stops を増やしたまま walkOrder を更新しないと「12 要素の walkOrder で 13 要素の stops を結ぼうとして fallback」となる。一時的に動くが意図と違う表示になる
- 一時無効化したい場合は frontmatter で `# walkOrder: [...]` とコメントアウト(YAML として未設定扱い)
- 実例: 2026-05-25 sakanoue-no-kumo に林董を 3 番目に追加した際、旧 walkOrder `[7,4,2,3,5,1,10,9,12,11,6,8]` を一時無効化 → 新 walkOrder `[8,5,2,4,6,1,11,10,13,12,3,7,9]` に再生成

## 散歩ルートに偉人を追加する手順

既存ルート(`src/content/routes/<route>.md`)に新規偉人を追加する場合、5 箇所の連動更新が定型化されている(2026-05-25 林董を sakanoue-no-kumo と boshin-hokuetsu に追加した際に確立)。

0. **追加偉人の coords が設定済か確認(必須)**: 追加する偉人の `src/content/people/<slug>.md` に `coords` が設定されていることを確認する。coords も `hideMap: true` も未設定の偉人を stops に含めると、`src/pages/routes/[slug].astro` の `showRouteMap` 条件で **ルート全体の経路マップが非表示になる**。2026-05-25 に山下源太郎・牛島満を coords 未取得状態で stops に追加して、それぞれ sakanoue-no-kumo・taiheiyo-senso のマップが消えた事例あり(commit `37ef39f` / `dbe7c44` で除外して復旧)。coords を先に取得するか、hideMap を設定するか、stops に追加しないかのいずれかを選ぶ。

1. **frontmatter `stops` に追加**: 適切な位置(時系列順か物語順か、ルートの編集方針に従う)に slug + note を挿入
2. **frontmatter `estimatedMinutes` を更新**: 1 名追加で 10-15 分加算が目安(墓所間距離・参拝込み)
3. **frontmatter `description` を更新**: 「N 名」のカウントや、偉人カテゴリ列挙を含む文を再構成(例: 「会津・幕府海軍・海援隊出身者 3 名」→「会津・幕府海軍・五稜郭籠城・海援隊出身者 4 名」)
4. **本文「## このコースの楽しみ方」(または相当セクション)を更新**: ルート概要・経路順リスト・対比的な説明文中の人数や偉人カテゴリを反映
5. **本文「Google Maps で散歩経路を開く」セクションの URL を再生成**: 追加偉人の coords を waypoints に含めた新しい徒歩経路 URL を生成(`https://www.google.com/maps/dir/?api=1&origin=...&destination=...&waypoints=...&travelmode=walking` 形式、waypoints はパイプ `%7C` 区切り)
6. **`walkOrder` を自動再生成**: stops を追加すると既存 walkOrder のインデックスがずれる(上記「散歩ルートマップの walkOrder」参照)。`python3 scripts/generate-walk-order.py` を実行すれば、全ルートの walkOrder を NN-TSP + 2-opt で自動計算して frontmatter に書き戻す。特定ルートだけ確認したい場合は `--dry-run` で書き込みなしプレビュー可能(2026-05-25 commit `e3f82c2` で全 11 ルート分自動生成)。手動 walkOrder を保持したいルートでは事前に bypass フラグを検討する必要があるが、現状そういうルートは無い。
7. **estimatedMinutes・本文の総距離/所要時間を再計算**: stops 数や walkOrder が変わると総距離も変わるため、`estimatedMinutes`(frontmatter)と本文「総距離 約 X km、墓所間 Y 分(参拝込み Z 分)」を更新。公式は **実距離 = 直線距離(walkOrder順) × 1.4(曲がり道補正)/ walk 15 分/km + visit 7 分/人 / 5 分単位 round**(2026-05-25 確立)。

ビルド検証: `npm run build` で zod 通過 + ページ内容を dev server で目視確認。

## コンテンツ方針

- 出典: Wikipedia(CC BY-SA)等の公開情報をベースに Claude が要約・再構成
- 直接コピペ禁止、必ず再構成 + `references` に出典明記
- 肖像写真は public domain(没後 70 年経過済)のみ使用可
- 事実誤認は本サイトの致命傷なので、ビルド前にユーザー目視確認を必ず通す
- **本文に `**bold**` 記法を使わない**。プレーンテキストで記述する。LLM 生成時に強調したくなる衝動を抑える(画面では地の文の流れの方が大事、structural な強調はセクション見出しで既に効いている)。2026-05-22 に過去 54 ファイル × 約 3,500 個の `**` を一括 strip した経緯あり(commit `942a704`)。新規偉人 md は最初から bold なしで書く。works コレクションも同様。詳細経緯: `~/Desktop/Obsidian/claude-code/2026-05-22-aoyama-cemetery-メタテーブル拡張と出身地filter.md`
- **frontmatter `era`(元号ラベル)の判定基準**: 当人の主要な活動・功績が現れた時代を基準とする。schema は最大 2 値まで。
  - **維新志士・幕末活動者は江戸末期の活動も含める**: 明治期に名を成した政治家・軍人でも、戊辰戦争・倒幕運動・幕府要職などで江戸期に活動していれば `[江戸, 明治]` とする。例: 大久保利通(明治の内務卿だが薩摩藩士として倒幕運動に深く関与)、乃木希典(明治の陸軍大将だが戊辰戦争従軍)、西周(明治の啓蒙思想家だが幕府開成所教授・徳川慶喜のブレーン)など。「明治維新を成し遂げた人物は江戸期の活動も評価する」が原則
  - **お雇い外国人は来日後の活動を基準**: 生年が江戸時代でも来日が明治以降なら `[明治]` のみとする(例: キヨッソーネ 1875 来日、フルベッキは 1859 来日のため `[江戸, 明治]`)
  - **外国人(本国メイン活動)の元号適用**: 朝鮮・中国出身者で日本での活動が明治以降のみの場合は `[明治]` のみとする(例: 金玉均 — 朝鮮の政治家、日本亡命は明治期)
  - 2026-05-22 に 13 名のラベルを本ルールで再検証・修正した経緯あり(commit `e477079`)。詳細経緯: `~/Desktop/Obsidian/claude-code/2026-05-23-aoyama-cemetery-偉人21名追加と機能群大幅拡張.md`

## 肖像写真の取得(Wikimedia Commons)

肖像写真を Wikimedia Commons から一括取得する際は、**`Special:FilePath` への直接アクセスは避ける**(レート制限 HTTP 429 が厳しく、~10 件連続で ban される)。代わりに MediaWiki API で `thumburl`(`upload.wikimedia.org` の CDN URL)を取得してからダウンロードする。

```
方法 A (NG): https://commons.wikimedia.org/wiki/Special:FilePath/<filename>
                → 連続アクセスで 429 連発、長時間待機が必要に
方法 B (推奨): https://commons.wikimedia.org/w/api.php?action=query&titles=File:<filename>
                  &prop=imageinfo&iiprop=url&iiurlwidth=600&format=json
                → imageinfo[0].thumburl が CDN URL、レート制限が緩い
```

実装済み再利用スクリプト: `scripts/download-portraits.py`(slug ↔ ファイル名のリストを定義して走らせるだけ、idempotent)。ライセンスは Wikipedia の File ページで Public domain in Japan / U.S. の表記を確認してから取得。frontmatter には `portrait: ../../assets/portraits/<slug>.jpg` + `portraitCredit: Wikimedia Commons / Public Domain` を統一して付与。詳細経緯: `~/Desktop/Obsidian/claude-code/2026-05-21-aoyama-cemetery-Wikimedia-Commons-肖像取得.md`

### Public Domain 判定の事前チェック

新規偉人を追加する前に、**没年から 70 年が経過しているか**を確認する。日本国内の著作権法は **著作者の死後 70 年**で Public Domain になるルール(2018 年 12 月 30 日施行・TPP 関連法改正)。70 年未経過の人物は Wikimedia Commons にも Public Domain 画像が存在しないため、`portrait` フィールドなしで作成し、ページ上部は冒頭文の視覚的インパクトで補う方針とする。

- 例(2026 年現在で PD 経過): 後藤象二郎(1897 没)・副島種臣(1905 没)・川路利良(1879 没)・西竹一(1945 没・滑り込み)・長与専斎(1902 没)・ジョセフ・ヒコ(1897 没)・森永太一郎(1937 没)・佐藤義亮(1951 没)等
- 例(PD 未経過のため肖像なし): **星新一(1997 没 → 2068 年に PD)**・**橋本龍太郎(2006 没 → 2077 年に PD)**
- 判定式: `今年 - 没年 ≥ 71` なら PD 経過(没年当年は計算に含まない年起算ルール)。境界年は Wikipedia の File ページで `{{PD-Japan}}` テンプレートを確認してから取得

### events heroImage 取得の補完テクニック(url 一時書き換え)

events 用の自動取得スクリプト `scripts/fetch-event-images.py` は md ファイルの `url:` フィールド(Wikipedia 記事 URL)から記事を解決し、pageimage API → imageinfo API でライセンス白リスト(PD/CC0/CC-BY/CC-BY-SA)に合致する画像のみを取得して frontmatter を自動更新する。

事件記事に画像がない・ライセンス不適合・国旗や紋章しか取れない等で SKIP / 弱画像になった event は、**md ファイルの `url:` を関連 Wikipedia 記事に一時的に書き換えて再実行 → 元の url に戻す** ワークアラウンドで補完できる。スクリプト本体を改造する必要はない。

#### 書き換え先候補の優先順位

1. **当事者・主導者の人物 Wikipedia 記事**(肖像が取れる、最も汎用的)
   - 例: 安政の大獄 → `井伊直弼` / 学制発布 → `大木喬任` / 国際連盟脱退 → `松岡洋右`
2. **サブ記事・関連記事**(画像の種類が違うバリアントが取れる)
   - 例: 満州事変 → `柳条湖事件`(本記事は紋章しか pageimage がないが、サブ記事は爆破地点写真)
3. **別の関連人物**(第一候補がライセンス不適の場合のフォールバック)
   - 例: 壬午事変 → `閔妃`(韓国 KOGL Type 1 で白リスト外) → `三浦梧楼` で再試行

#### 手順

```bash
# 1. md ファイルの url を一時書き換え(Edit で 1 行)
#    旧: url: https://ja.wikipedia.org/wiki/安政の大獄
#    新: url: https://ja.wikipedia.org/wiki/井伊直弼

# 2. 弱画像の場合は既存の heroImage / heroImageCaption / heroImageCredit 3 行も削除
#    (heroImage 設定済みだとスクリプトが skip するため)
rm -f src/assets/event-images/<旧画像>.png

# 3. スクリプト再実行(取得済の他 event は自動 skip)
python3 scripts/fetch-event-images.py

# 4. 取得成功を確認したら url を元の事件名記事に戻す
#    (事件詳細ページの「参考資料」リンクは事件名記事の方が読者向けに自然)
```

#### 注意点

- url 書き換え時に heroImageCredit が複数行構造(`\n` を含む YAML scalar)の場合、Edit の old_string マッチが失敗するため Python の re.sub で multiline 削除する方が安全
- 完成した heroImage は人物肖像になるが、event の「象徴画像」として機能するため違和感は少ない(条約調印者・指揮官・主導者の肖像など)
- 紋章・国旗(`Go-shichi_no_kiri.svg` / `Flag_of_Japan.svg`)が pageimage に来る記事は、関連人物への書き換えで具体性が大幅向上する
- 実例: 2026-05-26 に新規 19 件中 4 件(SKIP)+ 3 件(弱画像)を本手法で補完し、全 19 件で適切な heroImage を取得(commit `e0453e9`)

## frontmatter 記法の注意

people / works の frontmatter で、**値にコロン `:` を含む文字列はダブルクオートで囲む**。YAML パーサが「キー: 値」の構造と誤認識して `bad indentation of a mapping entry` エラーで build が止まる。

```yaml
# ✗ NG
creator: NHK / 脚本: 大森美香
publisher: 文藝春秋(訳: 廣中和歌子)

# ✓ OK
creator: "NHK / 脚本: 大森美香"
publisher: "文藝春秋(訳: 廣中和歌子)"
```

特に works コレクションの `creator` / `publisher`(脚本家・原作者・訳者などコロンを含む表記が頻出)で踏みやすい。新規 markdown 追加後は必ず `npm run build` で YAML 検証を通す。

## 開発コマンド

```bash
npm install
npm run dev      # http://localhost:4321
npm run build    # dist/ 生成
npm run preview  # 本番相当を確認
```

## デプロイ前提

- Cloudflare Pages 環境変数: `NODE_VERSION=22`(Astro 6 は >=22.12.0 を要求)
- Build command: `npm run build`
- Build output: `dist`
- Framework preset: Astro
