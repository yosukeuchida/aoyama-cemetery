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

## 地図機能

地図は **デフォルト ON**。偉人ページ(`src/pages/people/[slug].astro`)で本文下に Google Maps の iframe を表示する。3 通りの挙動を frontmatter で制御:

| frontmatter | 地図 URL | 用途 |
|---|---|---|
| 何も書かない(デフォルト) | `?q={name}の墓 青山霊園` の **名称検索方式** | Google Maps が POI を持っている著名な偉人。最も多いパターン |
| `hideMap: true` | 地図セクション非表示 | POI 未登録で地図を出したくない場合 |
| `coords: { lat, lng }` | `?q={lat},{lng}` の **座標方式** | POI 未登録だが正確な座標がわかる場合(座標ピンが立つだけで POI ラベルは出ない) |

- iframe・「Google マップで開く」リンクとも keyless(API key 不要)
- `coords` のスキーマ範囲は青山霊園内に限定(範囲外だと zod が build を弾く)
- トップページに複数ピンの overview 地図は持たない(個別偉人ページで完結する設計)

### 新規偉人で地図を確認する手順

1. ローカル(`npm run dev`)で偉人ページを開く、または `https://www.google.com/maps?q={偉人名}の墓+青山霊園` を直接ブラウザで検索
2. **正しい墓所 POI に着地する** → 何もしなくて OK(デフォルトで地図表示)
3. **別の場所が出る / 全く違う POI が出る** → 以下のどちらか
   - `hideMap: true` を frontmatter に追加(地図を出さない)
   - Google Maps 航空写真で正確な lat/lng を取得して `coords: { lat, lng }` を frontmatter に追加(座標ピンで表示)

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
