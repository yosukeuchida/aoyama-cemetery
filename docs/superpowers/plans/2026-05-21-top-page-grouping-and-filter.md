# Top Page Grouping & Era Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** トップページを職業別セクション + 時代チップフィルタに再構成し、URL hash 同期と progressive enhancement(JS 無効でも全件表示)を備えた静的ページに改修する。

**Architecture:** `src/pages/index.astro` 内で完結。フロントマター側で偉人を category 順 + nameKana 昇順にグルーピングし、HTML で各 section と card grid を描画。同ファイルの `<script>` で時代チップによる `hidden` toggle + 件数更新 + URL hash 同期を実装。スタイルは同ファイルの `<style>` ブロックに収める。

**Tech Stack:** Astro 6 / TypeScript / vanilla JS(<50 行)/ CSS Grid / CSS `:has()` 不使用(JS で hidden 属性制御)。テストフレームワーク無し、手動受け入れと `npm run build` で検証。

**参考:** 設計書 `docs/superpowers/specs/2026-05-21-top-page-grouping-and-filter-design.md`

---

## File Structure

- Modify: `src/pages/index.astro`(全体書き換え。フロントマターで category 順グルーピング、HTML でチップ+セクション+card grid、`<script>` でフィルタ JS、`<style>` でカード/グリッド/チップ CSS)
- 触らない: `src/layouts/BaseLayout.astro`, `public/styles/global.css`, `src/content/people/*.md`, `src/content.config.ts`

---

## Task 1: フロントマター側でカテゴリ別グルーピング

`<article>` フラット出力を、category 固定順 + nameKana 昇順のセクション構造に置き換える。チップ UI / JS はまだ無し。各カードに `data-era` を持たせて後続タスクで使える状態にする。

**Files:**
- Modify: `src/pages/index.astro`(全置換)

- [ ] **Step 1: index.astro を以下に置き換える**

```astro
---
import { getCollection } from 'astro:content';
import BaseLayout from '../layouts/BaseLayout.astro';

const CATEGORY_ORDER = ['政治家', '軍人', '実業家', '学者', '文化人', 'その他'] as const;
type Category = (typeof CATEGORY_ORDER)[number];

const people = await getCollection('people');

const groups: Record<Category, typeof people> = {
  政治家: [],
  軍人: [],
  実業家: [],
  学者: [],
  文化人: [],
  その他: [],
};

for (const p of people) {
  groups[p.data.category as Category].push(p);
}

for (const cat of CATEGORY_ORDER) {
  groups[cat].sort((a, b) => a.data.nameKana.localeCompare(b.data.nameKana, 'ja'));
}

const totalCount = people.length;

const title = '青山霊園 偉人録';
const description = '東京・青山霊園に眠る偉人たちを紹介するサイト。明治維新を担った政治家、文学者、軍人、文化人の足跡をたどります。';
---

<BaseLayout title={title} description={description}>
  <h1>青山霊園 偉人録</h1>
  <p>東京都港区にある青山霊園は、明治以降の日本を築いた多くの偉人が眠る場所です。本サイトでは、彼らの生涯と業績を紹介します。</p>

  <p class="people-count">全 {totalCount} 名</p>

  {
    CATEGORY_ORDER.map((cat) => {
      const list = groups[cat];
      if (list.length === 0) return null;
      return (
        <section class="category-section" data-category={cat}>
          <h2>
            {cat} <span class="section-count">({list.length})</span>
          </h2>
          <div class="people-grid">
            {list.map((person) => (
              <article class="person-card" data-era={person.data.era}>
                <h3 class="person-name">
                  <a href={`/people/${person.id}/`}>{person.data.name}</a>
                </h3>
                <p class="person-kana">{person.data.nameKana}</p>
                <p class="person-meta">
                  {person.data.birthDate.slice(0, 4)} - {person.data.deathDate.slice(0, 4)}
                  <span class="era-badge">{person.data.era}</span>
                </p>
                <p class="person-desc">{person.data.shortDescription}</p>
              </article>
            ))}
          </div>
        </section>
      );
    })
  }
</BaseLayout>
```

- [ ] **Step 2: ビルドが通ることを確認**

Run: `npm run build`
Expected: エラー無し、`dist/index.html` が生成される

- [ ] **Step 3: dev サーバで目視確認**

Run: `npm run dev`
ブラウザで http://localhost:4321 を開き、以下を確認:
- カテゴリが「政治家 → 軍人 → 実業家 → 学者 → 文化人 → その他」の順
- 各セクション内が五十音順
- 各セクション見出しに `(件数)` が表示される
- 0 件のセクションは描画されない

- [ ] **Step 4: commit**

```bash
git add src/pages/index.astro
git commit -m "$(cat <<'EOF'
refactor: group top page by category with kana sort

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: カード見た目とグリッドのスタイル追加

Task 1 で挿入した class に合わせて CSS を書く。グリッド、カード余白、ホバー、line-clamp、era バッジ、モバイル 1 列、prefers-reduced-motion 対応まで。

**Files:**
- Modify: `src/pages/index.astro`(末尾に `<style>` ブロック追加)

- [ ] **Step 1: index.astro の末尾(closing `</BaseLayout>` の後)に以下を追加**

```astro
<style>
  .people-count {
    color: #666;
    font-size: 0.9rem;
    margin: 0.5rem 0 1.5rem;
  }

  .category-section {
    margin-bottom: 2.5rem;
  }

  .category-section h2 {
    border-bottom: 1px solid #ddd;
    padding-bottom: 0.3rem;
    margin-bottom: 1rem;
  }

  .section-count {
    color: #888;
    font-size: 0.85rem;
    font-weight: normal;
  }

  .people-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 1rem;
  }

  .person-card {
    border: 1px solid #e5e5e5;
    border-radius: 6px;
    padding: 1rem;
    transition: box-shadow 120ms ease, transform 120ms ease;
  }

  .person-card:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    transform: translateY(-1px);
  }

  .person-name {
    margin: 0 0 0.2rem;
    font-size: 1.1rem;
  }

  .person-name a {
    color: inherit;
    text-decoration: none;
  }

  .person-name a:hover {
    text-decoration: underline;
  }

  .person-kana {
    margin: 0 0 0.4rem;
    color: #888;
    font-size: 0.85rem;
  }

  .person-meta {
    margin: 0 0 0.5rem;
    color: #555;
    font-size: 0.85rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .era-badge {
    background: #f0f0f0;
    color: #444;
    padding: 0.1rem 0.5rem;
    border-radius: 3px;
    font-size: 0.75rem;
  }

  .person-desc {
    margin: 0;
    font-size: 0.9rem;
    line-height: 1.5;
    color: #333;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  @media (max-width: 640px) {
    .people-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .person-card {
      transition: none;
    }
    .person-card:hover {
      transform: none;
    }
  }
</style>
```

- [ ] **Step 2: dev サーバで目視確認**

Run: `npm run dev`
- カードがグリッド表示される
- ホバーで影が出る
- 説明文が 2 行で truncate される
- 時代バッジが小さなチップ風に表示される
- ブラウザを 640px 未満に絞ると 1 列になる

- [ ] **Step 3: commit**

```bash
git add src/pages/index.astro
git commit -m "$(cat <<'EOF'
style: refresh top page card grid and badges

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: 時代チップバー(表示のみ・behavior なし)

該当者がいる era だけチップを描画。CSS で active 表現も先に書く。クリックしても何も起こらない状態で OK。

**Files:**
- Modify: `src/pages/index.astro`(リード文と件数表示の間にチップバーを挿入、`<style>` にチップ CSS を追加)

- [ ] **Step 1: フロントマターに era 集計を追加**

`const totalCount = people.length;` の直後に追加:

```ts
const ERA_ORDER = ['江戸', '明治', '大正', '昭和'] as const;
const presentEras = ERA_ORDER.filter((era) => people.some((p) => p.data.era === era));
```

- [ ] **Step 2: HTML 側でチップバーを追加**

リード文の `</p>` と `<p class="people-count">` の間に挿入:

```astro
<div class="era-filter" role="toolbar" aria-label="時代で絞り込み">
  <span class="era-filter-label">時代:</span>
  <button type="button" class="era-chip is-active" data-era="all" aria-pressed="true">
    すべて
  </button>
  {
    presentEras.map((era) => (
      <button type="button" class="era-chip" data-era={era} aria-pressed="false">
        {era}
      </button>
    ))
  }
</div>
```

- [ ] **Step 3: `<style>` ブロック内に以下を追加(`.people-count` ルールの前)**

```css
.era-filter {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
  margin: 1rem 0 0.5rem;
}

.era-filter-label {
  color: #555;
  font-size: 0.9rem;
  margin-right: 0.2rem;
}

.era-chip {
  background: #fff;
  border: 1px solid #ccc;
  color: #333;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.85rem;
  cursor: pointer;
  font-family: inherit;
}

.era-chip:hover {
  background: #f5f5f5;
}

.era-chip.is-active {
  background: #333;
  color: #fff;
  border-color: #333;
}
```

- [ ] **Step 4: dev サーバで目視確認**

Run: `npm run dev`
- 「時代: [すべて] [江戸] [明治] [大正] [昭和]」が表示される(該当者がいる era のみ)
- 「すべて」が黒背景・白文字で active 表示
- 他チップはホバーで薄グレー
- クリックしても何も起きない(まだ JS 無し)

- [ ] **Step 5: commit**

```bash
git add src/pages/index.astro
git commit -m "$(cat <<'EOF'
feat: add era filter chip bar (visual only)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: チップ click で絞り込み JS

`hidden` 属性で card を隠す。各セクションの件数を絞り込み後に書き換え、表示 0 件のセクションは見出しごと hidden。件数表示も更新。URL 同期は次タスク。

**Files:**
- Modify: `src/pages/index.astro`(末尾の `</style>` の後に `<script>` を追加)

- [ ] **Step 1: index.astro の末尾(`</style>` の後)に以下を追加**

```astro
<script>
  const chips = document.querySelectorAll<HTMLButtonElement>('.era-chip');
  const articles = document.querySelectorAll<HTMLElement>('.person-card');
  const sections = document.querySelectorAll<HTMLElement>('.category-section');
  const countEl = document.querySelector<HTMLElement>('.people-count');
  const totalCount = articles.length;

  function applyFilter(era: string) {
    // チップ active 切替
    chips.forEach((chip) => {
      const active = chip.dataset.era === era;
      chip.classList.toggle('is-active', active);
      chip.setAttribute('aria-pressed', active ? 'true' : 'false');
    });

    // article hidden 切替
    let visible = 0;
    articles.forEach((article) => {
      const match = era === 'all' || article.dataset.era === era;
      article.hidden = !match;
      if (match) visible += 1;
    });

    // section hidden 切替 + section count 更新
    sections.forEach((section) => {
      const cards = section.querySelectorAll<HTMLElement>('.person-card');
      const visibleInSection = Array.from(cards).filter((c) => !c.hidden).length;
      section.hidden = visibleInSection === 0;
      const countSpan = section.querySelector<HTMLElement>('.section-count');
      if (countSpan) countSpan.textContent = `(${visibleInSection})`;
    });

    // 件数表示
    if (countEl) {
      countEl.textContent =
        era === 'all' ? `全 ${totalCount} 名` : `${visible} 名を表示中 (全 ${totalCount} 名)`;
    }
  }

  chips.forEach((chip) => {
    chip.addEventListener('click', () => {
      const era = chip.dataset.era || 'all';
      applyFilter(era);
    });
  });
</script>
```

- [ ] **Step 2: dev サーバで動作確認**

Run: `npm run dev`
- 「明治」チップをクリック → 明治以外のカードが消える
- 該当 0 件のセクション(例: 江戸期に該当者がいなければ「江戸」を選んだとき全セクションが消える)が見出しごと隠れる
- 各セクション見出しの件数が更新される
- 件数表示が「◯ 名を表示中 (全 29 名)」になる
- 「すべて」に戻すと「全 29 名」と表示され、全件が戻る

- [ ] **Step 3: commit**

```bash
git add src/pages/index.astro
git commit -m "$(cat <<'EOF'
feat: filter cards by era chip with section count update

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: URL hash 同期 + hashchange リスナー

ページロード時に `#era=明治` を読み取って初期 active を復元、チップクリックで hash を書き換え、ブラウザ戻る/進むで `hashchange` から再適用する。

**Files:**
- Modify: `src/pages/index.astro`(`<script>` 内のロジック拡張)

- [ ] **Step 1: `<script>` 内の処理を以下に置き換える**

`applyFilter` 関数はそのまま残し、その下のチップイベント登録ブロックを以下に差し替える:

```ts
function parseHash(): string {
  const m = location.hash.match(/^#era=(.+)$/);
  if (!m) return 'all';
  const decoded = decodeURIComponent(m[1]);
  const valid = Array.from(chips).some((c) => c.dataset.era === decoded);
  return valid ? decoded : 'all';
}

function syncHash(era: string) {
  if (era === 'all') {
    history.replaceState(null, '', location.pathname + location.search);
  } else {
    history.replaceState(null, '', `${location.pathname}${location.search}#era=${encodeURIComponent(era)}`);
  }
}

chips.forEach((chip) => {
  chip.addEventListener('click', () => {
    const era = chip.dataset.era || 'all';
    applyFilter(era);
    syncHash(era);
  });
});

window.addEventListener('hashchange', () => {
  applyFilter(parseHash());
});

applyFilter(parseHash());
```

- [ ] **Step 2: dev サーバで動作確認**

Run: `npm run dev`
- 「大正」をクリック → URL が `http://localhost:4321/#era=大正` になる
- そのままページ再読込 → 「大正」が active のまま、大正以外が hidden
- 「すべて」をクリック → hash が消える
- 別タブで `http://localhost:4321/#era=明治` を直接開く → 明治 active で開く
- ブラウザの戻るで 1 つ前のフィルタ状態に戻る(replaceState なので履歴は伸びないが、外部から hash 変更されたケースで `hashchange` が拾える)

- [ ] **Step 3: 不正な hash でクラッシュしないこと**

ブラウザで `http://localhost:4321/#era=invalid_xxx` を開く
- 全件表示(`all` にフォールバック)になり、エラーが console に出ないことを確認

- [ ] **Step 4: commit**

```bash
git add src/pages/index.astro
git commit -m "$(cat <<'EOF'
feat: sync era filter state with URL hash

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: noscript フォールバック + aria-live + 件数表示への aria 属性付与

JS 無効環境でチップバーと件数表示を隠す。件数表示は `aria-live="polite"` で動的更新を読み上げる。

**Files:**
- Modify: `src/pages/index.astro`

- [ ] **Step 1: `<p class="people-count">` を `aria-live="polite"` 付きに変更**

```astro
<p class="people-count" aria-live="polite">全 {totalCount} 名</p>
```

- [ ] **Step 2: `BaseLayout` の `<slot />` で噛む形になっているため、`<noscript>` は body 内 = ページの先頭(`<h1>` の前)に挿入**

```astro
<BaseLayout title={title} description={description}>
  <noscript>
    <style>
      .era-filter,
      .people-count {
        display: none;
      }
    </style>
  </noscript>

  <h1>青山霊園 偉人録</h1>
  ...
```

- [ ] **Step 3: dev サーバで JS 無効動作確認**

Run: `npm run dev`
ブラウザの開発者ツールで JS を一時無効化(Chrome: DevTools → Settings → Debugger → Disable JavaScript)、ページを再読込:
- チップバーと「全 ◯ 名」表示が消える
- カードは全件、カテゴリ別に普通に並ぶ

JS を再有効化して通常動作も確認。

- [ ] **Step 4: commit**

```bash
git add src/pages/index.astro
git commit -m "$(cat <<'EOF'
feat: add noscript fallback and aria-live for filter

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: ビルド + 受け入れチェックリスト走査

最終ビルドが通ること、`dist/index.html` に noscript fallback と全件カードが入っていることを確認。受け入れ基準を 1 つずつ消化。

**Files:**
- 触らない(検証のみ)

- [ ] **Step 1: production build**

Run: `npm run build`
Expected: 成功、警告なし

- [ ] **Step 2: dist/index.html を grep で確認**

```bash
grep -c 'person-card' dist/index.html
```
Expected: 偉人数(現状 29)以上

```bash
grep -c 'noscript' dist/index.html
```
Expected: 1 以上(`<noscript>` ブロックが含まれる)

```bash
grep -o 'data-era="[^"]*"' dist/index.html | sort | uniq -c
```
Expected: 明治・大正・昭和(該当者がいる era)が出る

- [ ] **Step 3: preview で本番相当確認**

Run: `npm run preview`
ブラウザで http://localhost:4321 を開き、設計書 § テストと受け入れ基準 の手動チェック 8 項目を全て通す:

1. トップを開くと「すべて」が active、全件がカテゴリ別に並ぶ
2. 「明治」チップで明治以外が hidden / 各セクションカウント更新 / 0 件セクションは消える
3. URL に `#era=明治` が付き、再読込しても明治 active のまま復元される
4. ブラウザの戻るで前の状態に戻る
5. JS を無効化しても全件が普通に並ぶ
6. キーボード Tab でチップを順に focus、Space/Enter で切替できる
7. モバイル(<640px)で 1 列、カード内テキストが破綻しない
8. Lighthouse Accessibility スコアが現状から下がらない(Chrome DevTools → Lighthouse → Accessibility 単独実行)

- [ ] **Step 4: 全項目クリアしたら本タスク完了**

何か落ちたら該当 Task に戻り、修正後に再走査する。コミットは不要(検証のみ)。

---

---

## Task 8: 職業チップフィルタ追加 + 時代フィルタと AND 合成

**追加日: 2026-05-21**(spec 改訂版に対応。Task 1-7 完了後の追加機能)

時代フィルタの下に職業フィルタを並べ、両者は AND 条件で適用。各 article に `data-category` 属性を追加、URL hash を URLSearchParams 形式(`#era=X&cat=Y`)に変更。noscript fallback も `.category-filter` を追加する。

**Files:**
- Modify: `src/pages/index.astro`(フロントマター・HTML・CSS・JS の 4 箇所同時改修)

- [ ] **Step 1: フロントマターに `presentCategories` を追加**

`const presentEras = ERA_ORDER.filter((era) => people.some((p) => p.data.era === era));` の直後に追加:

```ts
const presentCategories = CATEGORY_ORDER.filter((cat) => groups[cat].length > 0);
```

- [ ] **Step 2: 各 article に `data-category` 属性を追加**

```astro
<article class="person-card" data-era={person.data.era} data-category={person.data.category}>
```

(他は変更なし)

- [ ] **Step 3: era-filter-label を共通 `.filter-label` に rename し、職業チップバーを追加**

HTML 側:
- 既存の `<span class="era-filter-label">時代:</span>` を `<span class="filter-label">時代:</span>` に変更
- 既存の `.era-filter` `<div>` の閉じタグの直後、`<p class="people-count">` の前に職業バーを挿入:

```astro
  <div class="category-filter" role="toolbar" aria-label="職業で絞り込み">
    <span class="filter-label">職業:</span>
    <button type="button" class="category-chip is-active" data-category="all" aria-pressed="true">
      すべて
    </button>
    {
      presentCategories.map((cat) => (
        <button type="button" class="category-chip" data-category={cat} aria-pressed="false">
          {cat}
        </button>
      ))
    }
  </div>
```

- [ ] **Step 4: CSS — `.era-filter` / `.era-chip` ルールを 2 バー対応に拡張**

既存 CSS を以下に置き換える(該当 4 ルールのみ。他はそのまま):

```css
  .era-filter,
  .category-filter {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.4rem;
    margin: 1rem 0 0.5rem;
  }

  .category-filter {
    margin-top: 0.3rem;
  }

  .filter-label {
    color: #555;
    font-size: 0.9rem;
    margin-right: 0.2rem;
  }

  .era-chip,
  .category-chip {
    background: #fff;
    border: 1px solid #ccc;
    color: #333;
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
    font-size: 0.85rem;
    cursor: pointer;
    font-family: inherit;
  }

  .era-chip:hover,
  .category-chip:hover {
    background: #f5f5f5;
  }

  .era-chip.is-active,
  .category-chip.is-active {
    background: #333;
    color: #fff;
    border-color: #333;
  }
```

(旧 `.era-filter-label` ルールは削除し `.filter-label` に置き換え)

- [ ] **Step 5: noscript ブロックに `.category-filter` を追加**

```astro
  <noscript>
    <style>
      .era-filter,
      .category-filter,
      .people-count {
        display: none;
      }
    </style>
  </noscript>
```

- [ ] **Step 6: JS を AND フィルタ + URLSearchParams hash に書き換え**

`<script>` ブロック全体を以下に置き換える:

```ts
<script>
  const eraChips = document.querySelectorAll<HTMLButtonElement>('.era-chip');
  const catChips = document.querySelectorAll<HTMLButtonElement>('.category-chip');
  const articles = document.querySelectorAll<HTMLElement>('.person-card');
  const sections = document.querySelectorAll<HTMLElement>('.category-section');
  const countEl = document.querySelector<HTMLElement>('.people-count');
  const totalCount = articles.length;

  let currentEra = 'all';
  let currentCategory = 'all';

  function applyFilter() {
    eraChips.forEach((chip) => {
      const active = chip.dataset.era === currentEra;
      chip.classList.toggle('is-active', active);
      chip.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
    catChips.forEach((chip) => {
      const active = chip.dataset.category === currentCategory;
      chip.classList.toggle('is-active', active);
      chip.setAttribute('aria-pressed', active ? 'true' : 'false');
    });

    let visible = 0;
    articles.forEach((article) => {
      const matchEra = currentEra === 'all' || article.dataset.era === currentEra;
      const matchCat = currentCategory === 'all' || article.dataset.category === currentCategory;
      const match = matchEra && matchCat;
      article.hidden = !match;
      if (match) visible += 1;
    });

    sections.forEach((section) => {
      const cards = section.querySelectorAll<HTMLElement>('.person-card');
      const visibleInSection = Array.from(cards).filter((c) => !c.hidden).length;
      section.hidden = visibleInSection === 0;
      const countSpan = section.querySelector<HTMLElement>('.section-count');
      if (countSpan) countSpan.textContent = `(${visibleInSection})`;
    });

    if (countEl) {
      const filtered = currentEra !== 'all' || currentCategory !== 'all';
      countEl.textContent = filtered
        ? `${visible} 名を表示中 (全 ${totalCount} 名)`
        : `全 ${totalCount} 名`;
    }
  }

  function parseHash(): { era: string; category: string } {
    const result = { era: 'all', category: 'all' };
    const raw = location.hash.startsWith('#') ? location.hash.slice(1) : '';
    if (!raw) return result;
    let params: URLSearchParams;
    try {
      params = new URLSearchParams(raw);
    } catch {
      return result;
    }
    const era = params.get('era');
    if (era && Array.from(eraChips).some((c) => c.dataset.era === era)) {
      result.era = era;
    }
    const category = params.get('cat');
    if (category && Array.from(catChips).some((c) => c.dataset.category === category)) {
      result.category = category;
    }
    return result;
  }

  function syncHash() {
    const params = new URLSearchParams();
    if (currentEra !== 'all') params.set('era', currentEra);
    if (currentCategory !== 'all') params.set('cat', currentCategory);
    const query = params.toString();
    const url = query
      ? `${location.pathname}${location.search}#${query}`
      : location.pathname + location.search;
    history.replaceState(null, '', url);
  }

  eraChips.forEach((chip) => {
    chip.addEventListener('click', () => {
      currentEra = chip.dataset.era || 'all';
      applyFilter();
      syncHash();
    });
  });

  catChips.forEach((chip) => {
    chip.addEventListener('click', () => {
      currentCategory = chip.dataset.category || 'all';
      applyFilter();
      syncHash();
    });
  });

  window.addEventListener('hashchange', () => {
    const parsed = parseHash();
    currentEra = parsed.era;
    currentCategory = parsed.category;
    applyFilter();
  });

  const initial = parseHash();
  currentEra = initial.era;
  currentCategory = initial.category;
  applyFilter();
</script>
```

- [ ] **Step 7: 検証**

```bash
cd /Users/uchidayousuke/workspace/personal/aoyama-cemetery
npm run build
grep -c 'class="category-chip' dist/index.html       # 6 expected: 1 すべて + 5 categories (政治家/軍人/実業家/学者/文化人)
grep -c 'class="era-chip' dist/index.html            # 4 expected (unchanged: すべて+明治+大正+昭和)
grep -c 'role="toolbar"' dist/index.html             # 2 expected (era + category bars)
grep -c 'data-category=' dist/index.html             # ≥ 29 (cards) + 6 (chips) + 5 (sections) = 40-ish
grep -c 'aria-live="polite"' dist/index.html         # 1
grep -c 'noscript' dist/index.html                   # 2
```

- [ ] **Step 8: commit**

```bash
git add src/pages/index.astro docs/superpowers/specs/2026-05-21-top-page-grouping-and-filter-design.md docs/superpowers/plans/2026-05-21-top-page-grouping-and-filter.md
git commit -m "$(cat <<'EOF'
feat: add category filter combining with era filter (AND)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review

- **Spec coverage**:
  - § 情報構造 → Task 1
  - § レイアウト → Task 2
  - § チップバー UI → Task 3
  - § インタラクション(フィルタ・件数更新・section 隠し) → Task 4
  - § URL 同期 → Task 5
  - § アクセシビリティ(aria-pressed・toolbar role・aria-live・prefers-reduced-motion) → Task 3 (role/aria-pressed)、Task 2 (prefers-reduced-motion)、Task 6 (aria-live)
  - § JS 無効時 → Task 6
  - § 受け入れ基準 → Task 7
  - 全項目に対応タスクあり ✓
- **Placeholder scan**: TBD/TODO/「適宜」「後で」等なし ✓
- **Type consistency**: `data-era`, `data-category`, `.era-chip`, `.person-card`, `.category-section`, `.section-count`, `.people-count`, `.era-filter` などの class/属性名が全タスクで一貫している ✓
