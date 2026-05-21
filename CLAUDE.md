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

1. `src/content/people/<slug>.md` を作成(slug はローマ字ハイフン区切り、例 `okubo-toshimichi`)
2. frontmatter は `src/content.config.ts` の zod スキーマに準拠
3. 事実確認(没年月日・役職・業績)を `references` の出典で照合
4. **墓所位置**: 区画番号を Wikipedia/港区資料で確認し `graveSection` に記入(地図は次項参照)
5. `npm run dev` でローカル目視確認(地図が正しい墓所 POI に着地するかも確認)
6. `git commit && git push` → Cloudflare Pages が自動デプロイ
7. **墓参り写真がある場合**: `./scripts/add-grave-photo.sh <slug> <写真ファイル...>` で自動的にリサイズ(長辺 1600px / quality 85)+ HEIC→JPEG 変換 + 規則ファイル名で配置される。frontmatter 編集不要、`src/assets/grave-photos/<slug>/YYYY-MM-DD-<caption>.jpg` に置けば自動でギャラリー表示。詳細: `docs/superpowers/specs/2026-05-21-grave-photo-gallery-design.md`

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

## コンテンツ方針

- 出典: Wikipedia(CC BY-SA)等の公開情報をベースに Claude が要約・再構成
- 直接コピペ禁止、必ず再構成 + `references` に出典明記
- 肖像写真は public domain(没後 70 年経過済)のみ使用可
- 事実誤認は本サイトの致命傷なので、ビルド前にユーザー目視確認を必ず通す

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
