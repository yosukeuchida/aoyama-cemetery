# トップページ 分類・絞り込み再設計

- 作成日: 2026-05-21
- 対象ファイル: `src/pages/index.astro`(必要なら `src/styles/` 配下に CSS 追記)
- 関連: `docs/superpowers/specs/2026-05-21-aoyama-cemetery-site-design.md`(初期サイト設計)

## 背景

掲載偉人が 29 名まで増え、最終的に 100 名前後を想定している。現状トップは没年月日昇順のフラットな card list で、(1) 目的の人を探しにくい、(2) 並びが単調で興味を引きにくい、(3) 偉人同士の関係性(同時代・職業クラスタ)が見えない、(4) 見た目を整えたい、という 4 つの困りごとが顕在化した。本設計は職業別セクション + 時代フィルタ + 職業フィルタを軸にトップを再構成する。

## 改訂履歴

- 2026-05-21 初版
- 2026-05-21 職業チップフィルタを追加(時代フィルタの下に並ぶ第 2 のチップバー。両者は AND で適用)。URL hash スキーマを `#era=X` から `#era=X&cat=Y` の URLSearchParams 形式に変更。

## ゴール / 非ゴール

**ゴール**
- 100 名規模でも 1 ページで全件を見渡せる構造
- 職業(category)を主軸にしたグルーピングで関心起点の探索を可能にする
- 時代(era)で絞り込めるチップフィルタ
- URL hash で絞り込み状態を共有・復元できる
- JS 無効でも全件が表示される progressive enhancement
- カード見た目の改善(可読性・余白・ホバー)

**非ゴール**(将来枠)
- タグ多重選択 facet
- 文字列検索ボックス
- カテゴリ別アクセント色
- カード画像
- サブ一覧ページ(`/people/<category>/` 等)

## 情報構造

### セクション分けと並び順

`category` の固定順で 6 セクションを描画する。

1. 政治家
2. 軍人
3. 実業家
4. 学者
5. 文化人
6. その他

各セクション見出しに `(n)` で件数を併記する(例: `政治家 (12)`)。該当 0 件のセクションは描画しない。

### セクション内ソート

`nameKana` 昇順(五十音順)。同名の tie-break は不要(現実的に発生しない、発生してもファイル順で安定)。

### 時代チップ

「すべて / 江戸 / 明治 / 大正 / 昭和」の 5 種。該当する偉人が 1 名もいない時代のチップは描画しない(将来江戸期不在の状態を許容)。

### 職業チップ

「すべて / 政治家 / 軍人 / 実業家 / 学者 / 文化人 / その他」の 7 種。`CATEGORY_ORDER` の並びで描画。該当者 0 のカテゴリのチップは描画しない(現状「その他」が該当)。時代チップバーの直下に並ぶ第 2 のチップバー。両フィルタは **AND 条件** で適用される(例: 「明治」+「政治家」で明治期の政治家のみ表示)。

## レイアウト

```
青山霊園 偉人録
(リード文)

時代で絞り込む:
[すべて] [江戸] [明治] [大正] [昭和]
ℹ 全 29 名

── 政治家 (12) ──────────────────────
┌─card─┐ ┌─card─┐ ┌─card─┐ ┌─card─┐
└──────┘ └──────┘ └──────┘ └──────┘
┌─card─┐ ...

── 軍人 (3) ─────────────────────────
...
```

### カード構成

- 1 行目: 名前(リンク・やや大きめ、`color: inherit; text-decoration: none`)
- 2 行目: `nameKana`(小・薄色)
- 3 行目: `birthDate.slice(0,4) - deathDate.slice(0,4)` + 時代バッジ(小さい inline chip)
- 4 行目: `shortDescription`(`-webkit-line-clamp: 2; overflow: hidden`)
- カード全体に `<a>` を被せず、1 行目の `<a>` を `display: block` + 周囲を padding で広く取り、見出しクリックで遷移する形にする(キーボード focus を壊さない)

### Grid

- `display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 1rem;`
- モバイル(<640px)は自動で 1 列になる
- カードは `border: 1px solid #e5e5e5; border-radius: 6px; padding: 1rem;`
- ホバーで `box-shadow: 0 2px 8px rgba(0,0,0,0.08); transform: translateY(-1px); transition: 120ms`
- `@media (prefers-reduced-motion: reduce)` で transition を無効化

### チップバー

- sticky にはしない(スクロール追従させない)
- 時代バー: `<div class="era-filter" role="toolbar" aria-label="時代で絞り込み">`
- 職業バー: `<div class="category-filter" role="toolbar" aria-label="職業で絞り込み">`(時代バーの直下)
- 各チップは `<button type="button" aria-pressed="false" data-era="明治">明治</button>` / `<button data-category="政治家">政治家</button>`
- 「すべて」は `data-era="all"` / `data-category="all"`
- active 状態は `aria-pressed="true"` + `.is-active` クラスで CSS が色反転(背景濃く・文字白)
- ラベル「時代:」「職業:」は共通の `.filter-label` クラスでスタイリング

## インタラクション仕様

### チップ操作

1. クリック時、同じバー内の他チップの `aria-pressed` を false に、自身を true に
2. 状態として `currentEra` と `currentCategory` を保持
3. 各 `<article>` について `matchEra && matchCat` で表示判定し、不一致なら `hidden` 属性付与
   - `matchEra = currentEra === 'all' || article.dataset.era === currentEra`
   - `matchCat = currentCategory === 'all' || article.dataset.category === currentCategory`
4. 各セクション見出しの `(n)` を絞り込み後件数で更新
5. セクション内可視件数が 0 になったら、そのセクション(`<section>`)ごと `hidden` 属性を付与
6. 件数表示エリアを `◯ 名を表示中 (全 ◯ 名)`(どちらかでも絞り込み中)/ `全 ◯ 名`(両方 all)に更新

### URL 同期

- hash は **URLSearchParams 形式**: `#era=明治&cat=政治家`(キー名は `era` と `cat`)
- 片方のみ絞り込み中なら片方だけ書く: `#era=明治` / `#cat=政治家`
- 両方 `all` なら hash を消す
- 書き換えは `history.replaceState` のみ(履歴を汚さない)
- ページロード時とブラウザ戻る/進む(`hashchange`)時に hash → `currentEra` / `currentCategory` を復元して再適用
- 不正値・未知の era/cat は `all` にフォールバック

### 件数表示

- チップバー直下に `<p id="people-count" aria-live="polite">全 29 名</p>`
- 絞り込み変化時にテキスト書き換え

### JS 無効時

- `<noscript><style>.era-filter, .category-filter, .people-count { display: none }</style></noscript>` で両チップバーと件数表示を隠す
- カードは全件普通に並ぶ
- 検索エンジンには全件が見える

## 実装場所と分割

- `src/pages/index.astro` 内で完結させる
  - 上部: getCollection → category 順 → nameKana 昇順でグルーピング
  - HTML 部分: チップバー + 各 category section + card grid
  - 末尾の `<script>`(type="module" 不要、Astro が処理): フィルタ JS(<50 行想定)
- スタイルは `index.astro` 内の `<style>` ブロックに収める(BaseLayout のグローバルスタイルは触らない)
- 外部 .ts への切り出しは行わない(規模が小さい、1 ファイルで完結する方が読みやすい)

## アクセシビリティ

- チップ: `<button aria-pressed>` toggle button pattern
- チップバー: `role="toolbar" aria-label="時代で絞り込み"`
- 件数表示: `aria-live="polite"`
- カード見出しリンクが focus 可能、Tab 順序が DOM 順と一致
- `prefers-reduced-motion` 対応

## テストと受け入れ基準

### 自動

- `npm run build` が成功する
- 既存ページ(`/about`, `/people/<slug>/`)に regression なし
- 自動テストの新規追加は行わない(現状もテスト無し・Astro 静的サイト・スコープ過剰)

### 手動受け入れ基準

1. トップを開くと両バーで「すべて」が active、全件がカテゴリ別に並ぶ
2. 「明治」チップで明治以外が hidden / 各セクションカウント更新 / 0 件セクションは消える
3. 「政治家」チップで政治家以外のセクションが hidden、政治家セクション内は全件表示
4. 「明治」+「政治家」で明治期の政治家のみ表示(AND)
5. URL に `#era=明治&cat=政治家` が付き、再読込しても両 active のまま復元される
6. 片方を「すべて」に戻すと hash が `#cat=政治家` のように片方だけ残る
7. JS を無効化しても全件が普通に並ぶ(両チップバー + 件数表示が消える)
8. キーボード Tab で全チップを順に focus、Space/Enter で切替できる
9. モバイル(<640px)で 1 列、カード内テキストが破綻しない
10. Lighthouse Accessibility スコアが現状から下がらない

## オープン項目

なし(本設計時点で確定)。
