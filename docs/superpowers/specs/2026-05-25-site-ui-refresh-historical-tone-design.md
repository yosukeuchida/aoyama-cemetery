# 設計書: サイト UI 刷新 — 歴史 7 : 自然 3 のトーンへ

- **日付**: 2026-05-25
- **対象**: aoyama-cemetery 全ページ(トップ / 偉人詳細 / 散歩コース / 年表 / 青山霊園について / events / 404)
- **背景**: 現状は system sans-serif × 茶アクセント × cream 背景の最小構成で、情報は届くが「歴史の重み」「青山霊園らしさ」が画面に出ていない。記事数が 178 名規模に育った段階で、サイトの世界観をコンテンツに見合うものに引き上げる。

## 1. デザイン方針(ブレストで確定)

| 項目 | 決定 |
|---|---|
| トーン比重 | 歴史 7 : 自然 3(重厚さ主導) |
| カラーパレット | B. 苔むした石 — 深緑黒 × 石生成 × 古銅金 × 深緑アクセント |
| 見出しフォント | Noto Serif JP(500, 一部 600) |
| 本文フォント | Noto Sans JP(400/500) |
| トップ ヒーロー | 案 3 ミニマル(キッカーなし、表題+細罫+リード+件数のみ。画像なし) |
| 偉人詳細ヘッダー | B 横並び weight 型(肖像左 / 名前・読み・サマリ・メタグリッド右) |
| 肖像なしの偉人 | 左カラムに「肖像は未公開」陣取り型プレースホルダー(構造は崩さない) |
| モバイル | 横並びは縦積み / 2 列グリッドは 1 列 |
| 既存コンポーネント | 新トーンを全面適用してサイト全体を一貫させる |

## 2. デザイントークン

CSS 変数として `public/styles/global.css` の `:root` に定義し、全 Astro テンプレートが参照する。

```css
:root {
  /* 色 — B 苔むした石 */
  --color-bg:           #f5f2e8;  /* 石生成 — body / hero */
  --color-bg-alt:       #efeadb;  /* 一段沈んだ生成 — 偉人カード一覧の地 */
  --color-card:         #f7f3e6;  /* 偉人カード単体 */
  --color-ink:          #1f241f;  /* 主見出し・深緑黒 — header bg / h1 */
  --color-text:         #2b322c;  /* 本文 */
  --color-text-sub:     #4a5249;  /* リード文・引用 */
  --color-text-muted:   #6b6258;  /* 読み・キャプション */
  --color-text-faint:   #8a8273;  /* 件数ラベル・パンくず */
  --color-accent:       #3a5448;  /* 苔色アクセント — 罫線・引用左罫 */
  --color-accent-gold:  #8a7a4a;  /* 古銅金 — 細罫 / kicker / ラベル */
  --color-border:       #d8d1bf;  /* 主罫線 */
  --color-border-faint: #e3ddc9;  /* 副罫線 — メタリスト */
  --color-header-bg:    #1f241f;  /* ヘッダー深緑黒 */
  --color-header-fg:    #d6cfae;  /* ヘッダー上の文字 */
  --color-header-nav:   #c8c2a6;  /* ヘッダー ナビ */
  --color-header-sub:   #8a8a72;  /* ヘッダー 小文字 */

  /* タイポ */
  --font-serif: "Noto Serif JP", "Hiragino Mincho ProN", "Yu Mincho", serif;
  --font-sans:  "Noto Sans JP", "Hiragino Sans", "Yu Gothic", sans-serif;

  /* レイアウト */
  --max-width:        760px;   /* 720 → 760 に微増(B 詳細ページの肖像 200 + 余白を許容) */
  --max-width-narrow: 600px;   /* リード文・引用などの可読幅 */
  --gutter:           2rem;
  --gutter-mobile:    1.25rem;
}
```

`#5a4a2a` / `#6b4423` / `#fafaf7` 等の旧値は削除する。`<meta name="theme-color">` も `#1f241f` に差し替え。

## 3. Web フォント読み込み

`BaseLayout.astro` の `<head>` 末尾に Google Fonts(Noto Serif JP / Noto Sans JP)を 1 つの link でロード。display=swap で FOIT を避ける。

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500&family=Noto+Serif+JP:wght@500;600&display=swap">
```

ウェイトは Sans 400/500・Serif 500/600 のみ。日本語フォントは重いので weight 数を抑える。

## 4. グローバル UI

### 4.1 サイトヘッダー(共通)

- 背景: `--color-header-bg`(深緑黒)。下に 1px の `--color-accent-gold` ヘアライン
- ブランド: 2 段組
  - 上段「青山霊園 偉人録」(serif, letter-spacing .12em)
  - 下段「AOYAMA CEMETERY MEMORIAL」(.7rem, letter-spacing .25em, `--color-header-sub`)
- ナビ: 「偉人」「散歩コース」「年表」「霊園について」 letter-spacing .15em
  - 現状の「トップ」リンクは廃止(ブランドクリックでトップへ戻る)
- モバイル: ナビは横スクロール(現行踏襲)、letter-spacing は .1em に縮小

### 4.2 サイトフッター

- 上に 1px `--color-border` の罫線
- 背景は `--color-bg`、文字は `--color-text-muted`
- 中央寄せ、`Noto Serif JP` の小見出し「青山霊園 偉人録」+ クレジット文

### 4.3 main コンテナ

- `max-width: var(--max-width)`、上下 `padding: 3rem 1.25rem 4rem`
- 既存の `padding: 2rem 1rem` から増量(行間と組合せて「文書の余白」を作る)

## 5. ページ別レイアウト

### 5.1 トップページ(`src/pages/index.astro`)

**ヒーロー(案 3 ミニマル)**

- `.hero`: padding `5rem var(--gutter) 4.5rem`、中央寄せ
- `h1` (serif 500, 2.6rem, line-height 1.55, letter-spacing .15em):
  ```
  青山霊園に眠る
  偉人たち
  ```
- `.rule`: 60×1px の `--color-accent-gold` の細罫(`margin: 0 auto 1.8rem`)
- `.lead`(serif, 0.98rem, line-height 2.1, max-width 480px, `--color-text-sub`):
  ```
  港区南青山。
  近代日本を駆け抜けた政治家、軍人、文豪、学者たちが
  静かに眠る都心の杜を、人物とともに歩く。
  ```
- `.count`: 「**N**人の物語」(N は serif 500, 1.5rem, `--color-accent`、ラベル部は letter-spacing .3em で `--color-text-faint`)
- ヒーロー下に 1px `--color-border` の罫線

**偉人セクション**

- 背景を `--color-bg-alt` に切り替え
- `.section-title`(中央寄せ): 上に小ラベル `P E O P L E`(.7rem letter-spacing .35em `--color-accent-gold`)、下に serif h2「新たに加わった偉人」など
- 偉人カード: 2 列グリッド(モバイルは 1 列)
  - 背景 `--color-card`、左 2px `--color-accent`(苔色)の縦罫
  - 名前: serif 500, 1.2rem
  - メタ: 0.72rem, letter-spacing .08em, `--color-text-muted`
  - 説明文: sans, 0.82rem, line-height 1.75
  - hover: 左罫を 3px に / 軽い背景明度変化

既存のグルーピング・フィルタ機能はそのまま維持し、見出しと罫線・色だけ新トークンに置き換える。

### 5.2 偉人詳細(`src/pages/people/[slug].astro`) — B 横並び weight 型

```
┌─ パンくず ───────────────────────────────────────┐
│                                                  │
├──────────────┬──────────────────────────────────┤
│              │ P E R S O N                      │
│              │ 大久保 利通                       │  ← serif 500 2.4rem
│  [肖像]      │ おおくぼ としみち                  │
│  3:4         │ Ōkubo Toshimichi                  │
│  shadow      │                                   │
│              │ ┃ 維新の三傑のひとり。...           │  ← serif サマリ 引用罫
│              │                                   │
│              │ ── meta-grid 2 列 ───────────────┤
│              │ 生没年│1830 — 1878                │
│              │ 出身地│薩摩国鹿児島                │
│              │ 時代  │江戸・明治                  │
│              │ 役職  │内務卿 / 大蔵卿             │
│              │ 区画  │1 種 イ 8 号 8 側           │
└──────────────┴──────────────────────────────────┘

  ── h2「維新の三傑、内務卿として…」── (本文セクション)
```

- グリッド: `grid-template-columns: 200px 1fr; gap: 2.5rem`
- 肖像枠: `padding: 6px; background: #fff; box-shadow: 0 2px 12px rgba(0,0,0,.1)`(額装感)
- サマリ: serif 1rem, line-height 1.95, `padding-left: 1rem; border-left: 2px solid var(--color-accent)`
- メタグリッド: `grid-template-columns: 1fr 1fr`、各セルは `70px 1fr` の「ラベル|値」
- ラベル: 0.72rem, letter-spacing .15em, `--color-text-faint`
- 既存のメタテーブル(`<table class="meta-table">`)はメタグリッドに置換
- 表示対象フィールド(現行 meta-table 踏襲): `生没年` / `出身地` / `死没地` / `時代` / `役職` / `爵位` / `出身校` / `所属` / `受賞` / `区画`
  - 値が undefined のフィールドはセル自体を出さない(可変長グリッド)
  - 受賞・所属・出身校は配列なので「 / 」区切りで 1 セル内に収める
  - フィールド数が 6 を超えるときは meta-grid 単独行を 2 段組から 1 段組に切替(`grid-column: 1 / -1` を当てる)

**肖像なしの陣取り型プレースホルダー**

`PersonPortrait.astro` で `portrait` が undefined の場合、左カラムに以下を出す:

- 同じ 200×267 サイズの枠(`padding: 6px; background: var(--color-card); box-shadow: 0 2px 12px rgba(0,0,0,.05)`)
- 中央に「肖像は未公開」(serif 500, 0.9rem, `--color-text-muted`, letter-spacing .15em)、その下に細罫 + 小さく「No portrait」(0.65rem letter-spacing .25em `--color-text-faint`)
- ホバー・リンク化はしない(情報の追加投入を待つフラットな表現)

**本文 h2 / h3**

- `.body-sample` 相当のスタイルを `:global` で本文要素に適用
- h2: serif 500, 1.3rem, letter-spacing .1em, `padding-bottom: .5rem; border-bottom: 1px solid var(--color-border)`
- h3: serif 500, 1.1rem, 左 2px `--color-accent` のインデント罫
- p: sans 0.95rem, line-height 2.0

**コンポーネント群**

以下の既存セクションを 5.4 のコンポーネント節で示すトーンに置換:

1. `GravePhotoGallery`
2. `NearbyGraves`
3. `RelatedPeople`
4. `RelatedWorks`
5. RouteMap(`RouteMap.astro` は別ページでも使用)
6. references 一覧
7. events 関連リスト

### 5.3 その他ページ

| ページ | 変更 |
|---|---|
| `/routes/` 一覧 | トップと同じ section-title + カードグリッド。各ルートは `.route-card`(古銅金 left rule) |
| `/routes/[slug]` | 詳細ページと同じ「ヒーロー(キッカー+表題+rule+lead)」+ stop リスト(stop ごとに番号 + serif 名前 + 一言) |
| `/timeline/` | 縦軸タイムライン。年の見出しは serif 大、出来事は左罫 + sans 本文。色は `--color-accent` |
| `/about/` | 「霊園について」サブタイトル + serif h2 + 長文段組(リード文ブロック含む) |
| `/events/[slug]` | 詳細ページと同じ B 構造を流用(画像なし、左カラムは「催事 / EVENT」プレースホルダー) |
| `/404.astro` | 中央寄せ serif 表題「ページが見つかりません」+ rule + sans 案内文 + トップへの戻り |

### 5.4 共通コンポーネントのスタイル指針

すべて新トークンを参照、レイアウトは現行維持を基本とする。

- **セクション見出し**: serif 500, 1.3rem, 上に 0.7rem letter-spacing .35em の小ラベル(P L A C E / R E L A T E D / W O R K S 等)
- **カード**: `background: var(--color-card); border-left: 2px solid var(--color-accent)` を共通形に
- **罫線**: 主は `--color-border`, 副は `--color-border-faint`
- **タグ・チップ**: 背景 `--color-ink`, 文字 `--color-bg`, letter-spacing .1em, padding `.15rem .55rem`(era / category / 出身地など)
- **リンク**: 本文中のリンクは `--color-accent` + 下線、hover で `--color-accent-gold`
- **Map / iframe**: 枠線 1px `--color-border`, 余白を周囲に確保

## 6. レスポンシブ

ブレイクポイント `max-width: 720px`(既存準拠)で:

- 詳細ページの `head-b` を `grid-template-columns: 1fr` に変更、肖像幅 160px に縮小・中央寄せ
- メタグリッドを `grid-template-columns: 1fr` に
- トップの偉人カード 2 列 → 1 列
- ヒーロー h1 を 2.0rem に、letter-spacing を .08em に
- ヘッダーのブランド小文字下段は引き続き表示(letter-spacing は .15em に短縮)
- main の padding を `var(--gutter-mobile)` に

## 7. アクセシビリティ

- 背景 `--color-bg` (#f5f2e8) × 本文 `--color-text` (#2b322c) のコントラスト比 ≥ 12:1(WCAG AAA 確認済)
- `--color-text-muted` (#6b6258) × `--color-bg` のコントラスト比 ≥ 4.7:1(AA 通過)
- `--color-text-faint` (#8a8273) は 12px 以上のラベル限定使用(AA 大文字基準 3:1 を満たす)
- skip-link は現行維持(色だけ新トークン化)
- フォーカスリングは `outline: 2px solid var(--color-accent-gold); outline-offset: 2px` で統一

## 8. 影響範囲(変更ファイル)

| ファイル | 変更内容 |
|---|---|
| `public/styles/global.css` | 全面書き換え(185行 → 概算 400行) |
| `src/layouts/BaseLayout.astro` | フォント link 追加 / ヘッダー HTML 構造刷新 / `theme-color` 更新 |
| `src/pages/index.astro` | ヒーロー追加、section-title 構造、カードグリッド見直し |
| `src/pages/people/[slug].astro` | `<table class="meta-table">` → meta-grid に置換、横並びレイアウトラッパ追加 |
| `src/pages/routes/index.astro` | section-title / route-card 化 |
| `src/pages/routes/[slug].astro` | ヒーローブロック追加、stop リスト刷新 |
| `src/pages/timeline.astro` | 縦軸タイムラインの見た目刷新 |
| `src/pages/about.astro` | サブタイトル + serif 段組 |
| `src/pages/events/[slug].astro` | 詳細ページ B 構造の流用 |
| `src/pages/404.astro` | 中央寄せ serif 表題 |
| `src/components/PersonPortrait.astro` | 「肖像未公開」プレースホルダー分岐追加 |
| `src/components/RelatedPeople.astro` | 見出し・罫・トークンを差し替え |
| `src/components/RelatedWorks.astro` | 同上 |
| `src/components/NearbyGraves.astro` | 同上 |
| `src/components/GravePhotoGallery.astro` | 同上 |
| `src/components/RouteMap.astro` | 凡例・罫線のみトークン化(地図そのものは触らない) |

## 9. 非対象(やらないこと)

- コンテンツ(各 md ファイルの本文)の書き換え
- 既存 era / category / job タクソノミーの変更
- 散歩ルート機能(walkOrder / Leaflet)のロジック変更
- 肖像写真の新規取得・新規偉人の追加
- JSON-LD / SEO 構造化データの変更
- ダークモード対応(現状の単一ライト調で完成と見なす)
- アニメーション類(hover の細部のみ、ページ遷移アニメは入れない)

## 10. 検証手順

1. `npm run dev` でローカル起動
2. 以下 5 ページをブラウザで目視確認(デスクトップ・スマホ両方)
   - トップ(`/`)
   - 偉人詳細 肖像あり(`/people/okubo-toshimichi/`)
   - 偉人詳細 肖像なし(`/people/joseph-heco/` などプレースホルダー検証)
   - 散歩ルート詳細(`/routes/sakanoue-no-kumo/`)
   - 年表(`/timeline/`)
3. `npm run build` で型 / zod / リンクが通ることを確認
4. Lighthouse でフォント表示遅延(LCP)に致命的な悪化がないことを確認(font preconnect 効果)
5. 最終目視チェック後、commit & push

## 11. 移行戦略

- フェーズ分けせず単一 PR で実施(`global.css` の変数化を先にやれば各テンプレ修正は機械的に進む)
- 既存のページ単位テストは無いため、目視のスナップショット記録(主要 5 ページのスクリーンショット before/after)を Obsidian 進捗メモに保存
