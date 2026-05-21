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
4. **墓所位置**: 区画番号を Wikipedia/港区資料で確認し `graveSection` に記入、Google Maps 航空写真で位置を特定して `coords: { lat, lng }` を frontmatter に追加(coords 未設定でも掲載可、地図にだけ出ない)
5. `npm run dev` でローカル目視確認
6. `git commit && git push` → Cloudflare Pages が自動デプロイ

### coords 取得手順(Google Maps)

1. Google Maps で「青山霊園」を開き航空写真モードに切替
2. `graveSection` の区画番号(例 `1種イ8号8側`)を区画案内図と照合して位置を絞り込む
3. 該当位置を右クリック → 緯度経度をコピー
4. frontmatter に追加: `coords:\n  lat: 35.66xx\n  lng: 139.71xx` (範囲外だと zod が build を弾く)

## 地図機能

- 偉人ページ(`src/pages/people/[slug].astro`)で coords を持つ偉人のみ、本文下に Google Maps の iframe 埋め込みを表示
- iframe URL は `https://maps.google.com/maps?q={lat},{lng}&z=18&output=embed` の keyless 形式(API key 不要・課金なし)
- 「Google マップで開く」リンクも併設し、ユーザーは新規タブで経路案内・ストリートビューに進める
- トップページに複数ピンの overview 地図は持たない(個別偉人ページで完結する設計)

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
