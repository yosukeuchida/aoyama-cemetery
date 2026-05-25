# サイト UI 刷新(歴史 7 : 自然 3 のトーン) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** aoyama-cemetery 全ページのビジュアルを「苔むした石」パレット + 見出し Noto Serif JP + ミニマル「表紙」ヒーロー + B 横並び詳細ページに刷新し、コンテンツに見合う重厚感を出す。

**Architecture:** デザイントークンを `public/styles/global.css` の `:root` 一箇所に集約し、全 Astro テンプレ / コンポーネントの scoped `<style>` がそれを参照する。レイアウトは詳細ページの「肖像左 + 名前メタ右」グリッドが新規追加、それ以外のページは構造変更最小で色・フォント・余白の差し替えに集中する。

**Tech Stack:** Astro 6 / TypeScript strict / Noto Sans JP + Noto Serif JP(Google Fonts)/ プレーン CSS(@scope なし、scoped style + CSS 変数)

**Spec:** `docs/superpowers/specs/2026-05-25-site-ui-refresh-historical-tone-design.md`

**Branch:** `main` で実装(従来通り)。各タスクごとに 1 commit。

---

## File Structure

### 既存ファイル(編集)

| ファイル | 役割 | 変更規模 |
|---|---|---|
| `public/styles/global.css` | トークン定義 + サイト共通スタイル(skip-link/header/footer/main/card/table 等) | 全面書き換え |
| `src/layouts/BaseLayout.astro` | head 内の font link 追加 / theme-color 更新 / header HTML 構造刷新 / footer HTML 構造刷新 | 大 |
| `src/components/PersonPortrait.astro` | 「肖像未公開」分岐の追加 + 額装スタイル | 中 |
| `src/components/NearbyGraves.astro` | scoped style の色・フォント差し替え | 小 |
| `src/components/RelatedPeople.astro` | 同上 | 小 |
| `src/components/RelatedWorks.astro` | 同上(`TYPE_COLOR` のチップ色はそのまま) | 小 |
| `src/components/GravePhotoGallery.astro` | scoped style 差し替え + 見出しに小ラベル | 小 |
| `src/components/RouteMap.astro` | 見出し / 凡例 / pin 色を新トークンに | 小 |
| `src/pages/index.astro` | ヒーローブロック追加 / section-title 構造 / 人物カード再スタイル / フィルター chip 再スタイル / today widget 再スタイル | 大 |
| `src/pages/people/[slug].astro` | 横並び weight 構造に再編 / `<table class="meta-table">` → `<dl class="meta-grid">` 化 / 本文 h2/h3 と sub-section のトークン化 | 大 |
| `src/pages/routes/index.astro` | ヒーローブロック追加 + カード再スタイル(`THEME_COLOR` チップ色は保持) | 中 |
| `src/pages/routes/[slug].astro` | ヒーローブロック追加 + stop リスト再スタイル | 中 |
| `src/pages/timeline.astro` | 縦軸タイムラインの色・フォント差し替え | 中 |
| `src/pages/about.astro` | サブタイトル + serif 見出し化 | 小 |
| `src/pages/events/[slug].astro` | 詳細ページ B 構造を参考に再編 | 中 |
| `src/pages/404.astro` | 中央寄せ serif ヘッダー化 | 小 |

### 新規ファイル

なし(トークンも `:root` に追加するので新 CSS ファイルは作らない)。

---

## Task 1: デザイントークン定義 + Web フォント読み込み + BaseLayout 刷新

**Files:**
- Modify: `public/styles/global.css`(全面書き換え)
- Modify: `src/layouts/BaseLayout.astro`(theme-color / head 内 font link / header HTML / footer HTML)

このタスクで「サイト全体の地」が完成する。他のタスクは全てこのトークンに依存する。

- [ ] **Step 1: `public/styles/global.css` を全面書き換え**

`Write` ツールで以下の内容にする(既存 185 行は全部捨てる):

```css
:root {
  /* === Color tokens — B「苔むした石」パレット === */
  --color-bg:           #f5f2e8;
  --color-bg-alt:       #efeadb;
  --color-card:         #f7f3e6;
  --color-ink:          #1f241f;
  --color-text:         #2b322c;
  --color-text-sub:     #4a5249;
  --color-text-muted:   #6b6258;
  --color-text-faint:   #8a8273;
  --color-accent:       #3a5448;
  --color-accent-gold:  #8a7a4a;
  --color-border:       #d8d1bf;
  --color-border-faint: #e3ddc9;
  --color-header-bg:    #1f241f;
  --color-header-fg:    #d6cfae;
  --color-header-nav:   #c8c2a6;
  --color-header-sub:   #8a8a72;

  /* === Typography === */
  --font-serif: "Noto Serif JP", "Hiragino Mincho ProN", "Yu Mincho", serif;
  --font-sans:  "Noto Sans JP", "Hiragino Sans", "Yu Gothic", sans-serif;

  /* === Layout === */
  --max-width:        760px;
  --max-width-narrow: 600px;
  --gutter:           2rem;
  --gutter-mobile:    1.25rem;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: var(--font-sans);
  background: var(--color-bg);
  color: var(--color-text);
  line-height: 1.8;
  font-feature-settings: "palt";
  -webkit-font-smoothing: antialiased;
}

a {
  color: var(--color-accent);
  text-decoration: underline;
  text-underline-offset: 2px;
  text-decoration-thickness: 1px;
  transition: color 0.15s ease;
}
a:hover { color: var(--color-accent-gold); }

:focus-visible {
  outline: 2px solid var(--color-accent-gold);
  outline-offset: 2px;
}

/* === Skip link === */
.skip-link {
  position: absolute;
  top: 0;
  left: 0;
  padding: 0.5rem 1rem;
  background: var(--color-ink);
  color: var(--color-bg);
  text-decoration: none;
  z-index: 100;
  transform: translateY(-150%);
  transition: transform 0.15s ease;
}
.skip-link:focus {
  transform: translateY(0);
}

/* === Site header === */
.site-header {
  background: var(--color-header-bg);
  border-bottom: 1px solid var(--color-accent-gold);
}
.site-header nav {
  max-width: var(--max-width);
  margin: 0 auto;
  padding: 1rem var(--gutter);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}
.site-title {
  font-family: var(--font-serif);
  font-weight: 500;
  font-size: 1.05rem;
  letter-spacing: 0.12em;
  color: var(--color-header-fg);
  text-decoration: none;
  line-height: 1.3;
}
.site-title .site-title-sub {
  display: block;
  font-family: var(--font-sans);
  font-size: 0.65rem;
  letter-spacing: 0.25em;
  color: var(--color-header-sub);
  margin-top: 0.15rem;
}
.nav-links {
  list-style: none;
  display: flex;
  gap: 1.6rem;
  padding: 0;
  margin: 0;
  flex-wrap: nowrap;
  white-space: nowrap;
  font-size: 0.82rem;
  letter-spacing: 0.15em;
}
.nav-links a {
  color: var(--color-header-nav);
  text-decoration: none;
}
.nav-links a:hover {
  color: var(--color-header-fg);
}

@media (max-width: 720px) {
  .site-header nav {
    padding: 0.7rem var(--gutter-mobile);
    gap: 0.6rem;
  }
  .site-title { font-size: 0.95rem; letter-spacing: 0.1em; }
  .site-title .site-title-sub { font-size: 0.55rem; letter-spacing: 0.2em; }
  .nav-links {
    gap: 0.9rem;
    font-size: 0.78rem;
    letter-spacing: 0.1em;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }
}

/* === Main container === */
main {
  max-width: var(--max-width);
  margin: 0 auto;
  padding: 3rem var(--gutter) 4rem;
}
@media (max-width: 720px) {
  main { padding: 2rem var(--gutter-mobile) 3rem; }
}

/* === Site footer === */
.site-footer {
  border-top: 1px solid var(--color-border);
  padding: 2.5rem var(--gutter) 2rem;
  text-align: center;
  color: var(--color-text-muted);
  font-size: 0.82rem;
  line-height: 1.7;
}
.site-footer .footer-brand {
  font-family: var(--font-serif);
  font-size: 0.95rem;
  letter-spacing: 0.12em;
  color: var(--color-text);
  margin: 0 0 0.5rem;
}
.site-footer .footer-credit {
  margin: 0;
  font-size: 0.78rem;
  color: var(--color-text-faint);
}

/* === Typography (base) === */
h1, h2, h3, h4 {
  font-family: var(--font-serif);
  font-weight: 500;
  color: var(--color-ink);
  letter-spacing: 0.06em;
}
h1 { font-size: 2rem; line-height: 1.5; margin: 0 0 1rem; }
h2 { font-size: 1.3rem; line-height: 1.6; margin: 2.5rem 0 1.2rem; padding-bottom: 0.5rem; border-bottom: 1px solid var(--color-border); letter-spacing: 0.1em; }
h3 { font-size: 1.05rem; line-height: 1.6; margin: 1.8rem 0 0.7rem; padding-left: 0.7rem; border-left: 2px solid var(--color-accent); }

p { margin: 0 0 1rem; }

/* === Reusable: small uppercase label === */
.label-small {
  display: inline-block;
  font-family: var(--font-serif);
  font-size: 0.7rem;
  letter-spacing: 0.35em;
  color: var(--color-accent-gold);
  text-indent: 0.35em;
}

/* === Reusable: hairline rule === */
.hairline {
  width: 60px;
  height: 1px;
  background: var(--color-accent-gold);
  margin: 1.5rem auto;
  border: 0;
}

/* === Reusable: person card (top page + sub-component listings) === */
.person-card {
  background: var(--color-card);
  border-left: 2px solid var(--color-accent);
  padding: 1.2rem 1.3rem;
  transition: border-left-width 0.15s ease, background 0.15s ease;
}
.person-card:hover {
  border-left-width: 3px;
  background: #fbf7eb;
}

/* === Person detail — breadcrumb === */
.person-detail .breadcrumb {
  font-size: 0.72rem;
  color: var(--color-text-faint);
  letter-spacing: 0.1em;
  margin-bottom: 1.6rem;
}
.person-detail .breadcrumb a {
  color: var(--color-text-faint);
  text-decoration: none;
}
.person-detail .breadcrumb a:hover { color: var(--color-accent-gold); }
.person-detail .breadcrumb span[aria-hidden] { margin: 0 0.4em; color: var(--color-border); }
```

- [ ] **Step 2: BaseLayout.astro の head を更新**

`src/layouts/BaseLayout.astro:23` の `<meta name="theme-color">` の値を `#1f241f` に変更し、stylesheet link の直前に Google Fonts を追加する。

`<meta name="theme-color" content="#5a4a2a" />` を以下に置換:

```html
    <meta name="theme-color" content="#1f241f" />
```

`<link rel="stylesheet" href="/styles/global.css" />`(48 行目) の直前に以下を挿入:

```html
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      rel="stylesheet"
      href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500&family=Noto+Serif+JP:wght@500;600&display=swap"
    />
```

- [ ] **Step 3: BaseLayout.astro の header / footer HTML を刷新**

`<header class="site-header">` から `</header>` まで(53–63 行目)を以下で置換:

```astro
    <header class="site-header">
      <nav aria-label="メインナビゲーション">
        <a href="/" class="site-title">
          青山霊園 偉人録
          <span class="site-title-sub">AOYAMA CEMETERY MEMORIAL</span>
        </a>
        <ul class="nav-links">
          <li><a href="/">偉人</a></li>
          <li><a href="/routes/">散歩コース</a></li>
          <li><a href="/timeline/">年表</a></li>
          <li><a href="/about/">青山霊園について</a></li>
        </ul>
      </nav>
    </header>
```

`<footer class="site-footer">` から `</footer>` までを以下で置換:

```astro
    <footer class="site-footer">
      <p class="footer-brand">青山霊園 偉人録</p>
      <p class="footer-credit">© 2026 aoyama-cemetery. 偉人解説は Wikipedia 等の公開情報を元に再構成しています。</p>
    </footer>
```

- [ ] **Step 4: ビルド検証**

Run: `npm run build`
Expected: エラーなしで終了。`dist/` 内の HTML が生成される。

- [ ] **Step 5: dev server で表示確認(任意・人間チェック)**

Run: `npm run dev`
http://localhost:4321 を開き、ヘッダーが深緑黒 + 古銅金 hairline + 二段ブランド表示 / フッターが新しい二段表示になっていれば OK。本文・カードは Task 5〜9 でまだ古いまま見えるが、ヘッダー/フッター/フォント/色変数が反映されていれば成功。

- [ ] **Step 6: Commit**

```bash
git add public/styles/global.css src/layouts/BaseLayout.astro
git commit -m "$(cat <<'EOF'
feat(ui): 苔むした石パレット + Noto Serif JP の design token を導入

global.css を全面書き換え、:root に B パレットの色・タイポ・レイアウト変数を集約。
BaseLayout のヘッダーは深緑黒 + 古銅金 hairline + 二段ブランド構造に、フッターも
serif の brand + credit に刷新。Google Fonts(Noto Sans/Serif JP)を preconnect 付き
で読み込み、theme-color も新トーンに同期。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: PersonPortrait に「肖像未公開」プレースホルダーを追加

**Files:**
- Modify: `src/components/PersonPortrait.astro`(プレースホルダー分岐 + 額装スタイル + 新トークン)

肖像なしの偉人(ジョセフ・ヒコ・森永太一郎ほか)の詳細ページで左カラムが空にならないよう、placeholder 描画を担う。

- [ ] **Step 1: Props 型を更新して portrait を optional にする**

`src/components/PersonPortrait.astro` の Props インターフェースを以下に置換:

```ts
interface Props {
  portrait?: ImageMetadata;
  name: string;
  birthYear?: string;
  deathYear?: string;
  caption?: string;
  credit?: string;
}
```

- [ ] **Step 2: テンプレートを 2 分岐に書き換える**

`<figure class="person-portrait"> ... </figure>` 全体を以下で置換:

```astro
<figure class="person-portrait">
  {portrait ? (
    <div class="portrait-frame">
      <Image
        src={portrait}
        alt={altText}
        widths={[240, 360, 480]}
        sizes="(max-width: 480px) 240px, 360px"
        width={360}
        quality={85}
      />
    </div>
  ) : (
    <div class="portrait-frame portrait-placeholder" aria-hidden="false" role="img" aria-label={`${name} の肖像は未公開`}>
      <span class="placeholder-text">肖像は未公開</span>
      <span class="placeholder-rule"></span>
      <span class="placeholder-sub">No portrait</span>
    </div>
  )}
  {(caption || credit) && (
    <figcaption>
      {caption && <span class="caption">{caption}</span>}
      {credit && <span class="credit">{credit}</span>}
    </figcaption>
  )}
</figure>
```

- [ ] **Step 3: `<style>` ブロックを以下で全置換**

```astro
<style>
  .person-portrait {
    margin: 0;
    text-align: center;
  }
  .portrait-frame {
    padding: 6px;
    background: #fff;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
    display: inline-block;
    line-height: 0;
  }
  .portrait-frame img {
    width: 100%;
    max-width: 200px;
    height: auto;
    display: block;
  }
  .portrait-placeholder {
    width: 200px;
    aspect-ratio: 3 / 4;
    background: var(--color-card);
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.6rem;
    line-height: 1.5;
  }
  .placeholder-text {
    font-family: var(--font-serif);
    font-weight: 500;
    font-size: 0.9rem;
    letter-spacing: 0.15em;
    color: var(--color-text-muted);
  }
  .placeholder-rule {
    width: 30px;
    height: 1px;
    background: var(--color-accent-gold);
    display: block;
  }
  .placeholder-sub {
    font-size: 0.65rem;
    letter-spacing: 0.25em;
    color: var(--color-text-faint);
  }
  figcaption {
    margin-top: 0.6rem;
    font-size: 0.72rem;
    color: var(--color-text-muted);
    line-height: 1.5;
  }
  .caption { display: block; }
  .credit {
    display: block;
    font-size: 0.65rem;
    color: var(--color-text-faint);
    margin-top: 0.15rem;
  }
  @media (max-width: 720px) {
    .portrait-frame img,
    .portrait-placeholder { max-width: 160px; width: 160px; }
  }
</style>
```

- [ ] **Step 4: ビルド検証**

Run: `npm run build`
Expected: TS / zod が通る(portrait optional は呼び出し側に影響なし、Task 3 で `<PersonPortrait portrait={...}` を `<PersonPortrait portrait={person.data.portrait}` に変更する)。

- [ ] **Step 5: Commit**

```bash
git add src/components/PersonPortrait.astro
git commit -m "$(cat <<'EOF'
feat(portrait): 肖像未公開ケース用の陣取り型 placeholder を追加

PersonPortrait の portrait prop を optional にし、未指定時は同サイズの額装枠に
「肖像は未公開」+ hairline + No portrait の二段ラベルを描画する。新トーン
(石生成 bg / 古銅金 rule / serif フォント)で B 構造の左カラムを破綻させない。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: 偉人詳細ページの「B 横並び weight 型」レイアウト化

**Files:**
- Modify: `src/pages/people/[slug].astro`(`<article class="person-detail">` 内の冒頭〜meta-table を再編、scoped style 追加)

肖像左 / 名前メタ右の 2 カラム構造に変更し、`<table class="meta-table">` を `<dl class="meta-grid">` に置換する。本文以下(Content / 各 sub-section)は Task 4 で扱う。

- [ ] **Step 1: 冒頭部分(breadcrumb 〜 meta-table)を新構造に書き換え**

`src/pages/people/[slug].astro:184–227` (`<article class="person-detail">` の breadcrumb から `</table>` まで)を以下で置換:

```astro
  <article class="person-detail">
    <nav class="breadcrumb" aria-label="パンくずリスト">
      <a href="/">トップ</a>
      <span aria-hidden="true">›</span>
      <a href="/">偉人</a>
      <span aria-hidden="true">›</span>
      <span aria-current="page">{person.data.name}</span>
    </nav>

    <div class="person-head">
      <div class="person-head-left">
        <PersonPortrait
          portrait={person.data.portrait}
          name={person.data.name}
          birthYear={person.data.birthDate.slice(0, 4)}
          deathYear={person.data.deathDate.slice(0, 4)}
          caption={person.data.portraitCaption}
          credit={person.data.portraitCredit}
        />
      </div>
      <div class="person-head-right">
        <span class="label-small">P E R S O N</span>
        <h1 class="person-name">{person.data.name}</h1>
        <p class="kana">{person.data.nameKana}</p>
        <p class="romaji">{person.data.nameRomaji}</p>
        <p class="summary">{person.data.shortDescription}</p>
        <dl class="meta-grid">
          <div class="meta-cell"><dt>生没年</dt><dd><time datetime={person.data.birthDate}>{person.data.birthDate.slice(0, 4)}</time> — <time datetime={person.data.deathDate}>{person.data.deathDate.slice(0, 4)}</time></dd></div>
          {person.data.birthPlace && (
            <div class="meta-cell"><dt>出身地</dt><dd>{person.data.birthPlace}</dd></div>
          )}
          {person.data.deathPlace && (
            <div class="meta-cell"><dt>死没地</dt><dd>{person.data.deathPlace}</dd></div>
          )}
          <div class="meta-cell"><dt>時代</dt><dd>{person.data.era.join('・')}</dd></div>
          <div class="meta-cell"><dt>役職</dt><dd>{person.data.jobTitle ?? person.data.category}</dd></div>
          {person.data.honorificSuffix && (
            <div class="meta-cell"><dt>爵位</dt><dd>{person.data.honorificSuffix}</dd></div>
          )}
          {person.data.alumniOf && person.data.alumniOf.length > 0 && (
            <div class="meta-cell meta-cell-wide"><dt>出身校</dt><dd>{person.data.alumniOf.join(' / ')}</dd></div>
          )}
          {person.data.memberOf && person.data.memberOf.length > 0 && (
            <div class="meta-cell meta-cell-wide"><dt>所属</dt><dd>{person.data.memberOf.join(' / ')}</dd></div>
          )}
          {person.data.award && person.data.award.length > 0 && (
            <div class="meta-cell meta-cell-wide"><dt>受勲</dt><dd>{person.data.award.join(' / ')}</dd></div>
          )}
          {person.data.graveSection && (
            <div class="meta-cell meta-cell-wide"><dt>区画</dt><dd>{person.data.graveSection}</dd></div>
          )}
          {person.data.tags && person.data.tags.length > 0 && (
            <div class="meta-cell meta-cell-wide"><dt>タグ</dt><dd>{person.data.tags.join(' / ')}</dd></div>
          )}
        </dl>
      </div>
    </div>
```

ポイント:
- `{person.data.portrait && (` の条件は削除。`PersonPortrait` 側で undefined を扱う(Task 2)。
- パンくずに「偉人」階層を追加(`/` の二回目はトップで一旦 OK。将来一覧専用ルートが出来たら張り替え)。
- 配列系メタ・出身校・所属・受勲・区画・タグは `meta-cell-wide` クラスで 1 行を占有させる。

- [ ] **Step 2: 既存の `<style>` ブロック先頭に person-head / meta-grid 用の rules を追加**

`src/pages/people/[slug].astro` の `<style>`(324 行目以降)の先頭(`.person-events {` の手前)に以下を挿入:

```css
  .person-head {
    display: grid;
    grid-template-columns: 200px 1fr;
    gap: 2.5rem;
    align-items: start;
    margin-bottom: 2rem;
  }
  .person-head-right .label-small {
    display: inline-block;
    margin-bottom: 0.6rem;
  }
  .person-head-right .person-name {
    font-family: var(--font-serif);
    font-weight: 500;
    font-size: 2.2rem;
    letter-spacing: 0.1em;
    color: var(--color-ink);
    margin: 0 0 0.3rem;
    line-height: 1.4;
    padding: 0;
    border: 0;
  }
  .person-head-right .kana {
    color: var(--color-text-muted);
    font-size: 0.88rem;
    letter-spacing: 0.08em;
    margin: 0;
  }
  .person-head-right .romaji {
    color: var(--color-text-faint);
    font-size: 0.7rem;
    letter-spacing: 0.2em;
    margin: 0.25rem 0 0;
  }
  .person-head-right .summary {
    font-family: var(--font-serif);
    font-size: 1rem;
    line-height: 1.95;
    color: var(--color-text-sub);
    margin: 1.3rem 0 1.4rem;
    padding-left: 1rem;
    border-left: 2px solid var(--color-accent);
  }
  .meta-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.45rem 1.5rem;
    margin: 0;
    padding-top: 1rem;
    border-top: 1px solid var(--color-border);
    font-size: 0.85rem;
  }
  .meta-cell {
    display: grid;
    grid-template-columns: 70px 1fr;
    gap: 0.5rem;
  }
  .meta-cell-wide {
    grid-column: 1 / -1;
  }
  .meta-cell dt {
    color: var(--color-text-faint);
    font-size: 0.72rem;
    letter-spacing: 0.15em;
    padding-top: 0.2rem;
    margin: 0;
  }
  .meta-cell dd {
    color: var(--color-text);
    margin: 0;
    line-height: 1.6;
  }

  @media (max-width: 720px) {
    .person-head {
      grid-template-columns: 1fr;
      gap: 1.5rem;
      justify-items: center;
    }
    .person-head-right { width: 100%; }
    .person-head-right .person-name { font-size: 1.7rem; letter-spacing: 0.06em; }
    .meta-grid { grid-template-columns: 1fr; }
    .meta-cell, .meta-cell-wide { grid-template-columns: 80px 1fr; }
  }
```

注意: H1 のグローバル `padding-bottom: 0.5rem; border-bottom: 1px solid` (global.css Task 1 で h1 に直接 border は引いていないが、念の為に `.person-head-right .person-name` で `padding: 0; border: 0;` を明示)。

- [ ] **Step 3: 既存の `.person-detail h1 { ... }` 等の旧 style を確認**

Task 1 で `global.css` から `.person-detail` 関連の旧 rule は削除済み。`src/pages/people/[slug].astro` の `<style>` 内には旧 `.person-detail h1` 等のスタイル定義は存在しない(grep で確認: 旧スタイルは全部 global.css にあった)。よって削除作業は不要。

- [ ] **Step 4: ビルド検証**

Run: `npm run build`
Expected: zod / TS 通過。`<table>` を削除して `<dl>` に置き換えたので、`person-detail .meta-table` を参照する CSS 残骸が無いことを Task 1 で確認済み。

- [ ] **Step 5: dev server で目視確認**

Run: `npm run dev`(既に走っていれば不要)
- 肖像あり: `/people/okubo-toshimichi/` で左に額装肖像、右に名前 + メタが並ぶこと
- 肖像なし: `/people/joseph-heco/`(または該当する slug)で左に「肖像は未公開」placeholder が同サイズで出ること
- モバイル幅(devtools で 360px)で縦積みになること

- [ ] **Step 6: Commit**

```bash
git add src/pages/people/[slug].astro
git commit -m "$(cat <<'EOF'
feat(person-detail): B 横並び weight 型レイアウトに刷新

肖像左 / 名前メタ右の 2 カラム grid を導入。meta-table を meta-grid(dl)に置換
し、配列系フィールド(出身校・所属・受勲・区画・タグ)は wide cell で 1 行占有。
shortDescription を引用罫付きの summary として上半分に組み込んで「人物索引」を
ファーストビューで完結させる。720px 以下では縦積みに切替。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: 偉人詳細ページの本文以下サブセクションを新トークン化

**Files:**
- Modify: `src/pages/people/[slug].astro`(grave-map / person-events / person-routes / references 部分の `<style>`)

GravePhotoGallery / NearbyGraves / RelatedPeople / RelatedWorks / RouteMap の 5 コンポーネントは Task 5 で別途扱う。本タスクはこのページに残っている scoped style だけが対象。

- [ ] **Step 1: grave-map のスタイルを追加(現在 scoped style に grave-map 系がないので追記する)**

`src/pages/people/[slug].astro` の `<style>` ブロック末尾(`.person-route-meta { ... }` の閉じ `}` の後)に以下を追加:

```css
  .grave-map {
    margin-top: 2.5rem;
  }
  .grave-map h2 {
    /* グローバル h2 を踏襲(古銅金小ラベルは入れず、シンプルな border-bottom のみ) */
  }
  .grave-map iframe {
    width: 100%;
    border: 1px solid var(--color-border);
    border-radius: 0;
    background: var(--color-card);
  }
  .grave-map .map-link {
    margin: 0.6rem 0 0;
    text-align: right;
    font-size: 0.85rem;
  }
  .grave-map .map-link a {
    color: var(--color-accent);
    text-decoration: none;
    border-bottom: 1px solid var(--color-accent);
    padding-bottom: 1px;
  }
  .grave-map .map-link a:hover { color: var(--color-accent-gold); border-bottom-color: var(--color-accent-gold); }
```

- [ ] **Step 2: person-events / person-routes セクションの既存 style を新トークンに置換**

`<style>` 内の `.person-events { ... }` から `.person-route-meta { ... }` までの既存ブロック(全体)を以下で全置換:

```css
  .person-events {
    margin-top: 2.5rem;
  }
  .person-events-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }
  .person-events-list a {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    padding: 0.75rem 1rem;
    background: var(--color-card);
    border-left: 2px solid var(--color-accent);
    text-decoration: none;
    color: inherit;
    transition: border-left-width 0.15s ease, background 0.15s ease;
  }
  .person-events-list a:hover {
    border-left-width: 3px;
    background: #fbf7eb;
  }
  .person-event-date {
    font-size: 0.72rem;
    color: var(--color-text-faint);
    letter-spacing: 0.08em;
    font-variant-numeric: tabular-nums;
  }
  .person-event-title {
    font-family: var(--font-serif);
    font-size: 1rem;
    color: var(--color-ink);
    font-weight: 500;
    letter-spacing: 0.05em;
  }
  .person-event-summary {
    font-size: 0.85rem;
    color: var(--color-text-sub);
    line-height: 1.7;
  }

  .person-routes {
    margin-top: 2.5rem;
  }
  .person-routes-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 0.6rem;
  }
  .person-routes-list a {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    padding: 0.8rem 1rem;
    background: var(--color-card);
    border-left: 2px solid var(--color-accent);
    text-decoration: none;
    color: inherit;
    transition: border-left-width 0.15s ease, background 0.15s ease;
  }
  .person-routes-list a:hover {
    border-left-width: 3px;
    background: #fbf7eb;
  }
  .person-route-title {
    font-family: var(--font-serif);
    font-size: 1rem;
    color: var(--color-ink);
    font-weight: 500;
    letter-spacing: 0.05em;
  }
  .person-route-meta {
    font-size: 0.72rem;
    color: var(--color-text-faint);
    letter-spacing: 0.08em;
  }
```

- [ ] **Step 3: references セクションのスタイルを追加**

同じ `<style>` 末尾に以下を追加:

```css
  .references {
    margin-top: 2.5rem;
  }
  .references ul {
    list-style: none;
    padding: 0;
    margin: 0;
    border-top: 1px solid var(--color-border-faint);
  }
  .references li {
    padding: 0.6rem 0;
    border-bottom: 1px solid var(--color-border-faint);
    font-size: 0.88rem;
  }
  .references a {
    color: var(--color-accent);
    text-decoration: none;
  }
  .references a:hover { color: var(--color-accent-gold); text-decoration: underline; }
  .references a::after {
    content: " ↗";
    color: var(--color-text-faint);
    font-size: 0.85em;
  }
```

- [ ] **Step 4: ビルド検証**

Run: `npm run build`
Expected: エラーなし。

- [ ] **Step 5: 目視確認(dev server)**

`/people/okubo-toshimichi/` を開いて、地図セクション・関与した事件・散歩コース・参考資料が全て新トークンで描画されること。

- [ ] **Step 6: Commit**

```bash
git add src/pages/people/[slug].astro
git commit -m "$(cat <<'EOF'
feat(person-detail): 本文以下サブセクションを新トークンに統一

grave-map / person-events / person-routes / references を苔色 left rule + 石生成
card に統一し、見出しは serif の H2(global ルール準拠)に揃える。事件・経路
リンクの hover は左罫を 2→3px に厚くする共通モーション。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: 共通コンポーネント 5 つに新トークンを適用

**Files:**
- Modify: `src/components/NearbyGraves.astro`
- Modify: `src/components/RelatedPeople.astro`
- Modify: `src/components/RelatedWorks.astro`
- Modify: `src/components/GravePhotoGallery.astro`
- Modify: `src/components/RouteMap.astro`

各コンポーネントの **テンプレ HTML は変更せず、scoped `<style>` のみを置換する**。`<h2>` は global の serif H2 ルールに従う(border-bottom も継承)。

- [ ] **Step 1: NearbyGraves.astro の `<style>` ブロックを置換**

`<style>` 全体を以下で置換:

```astro
<style>
  .nearby-graves {
    margin-top: 2.5rem;
  }
  .nearby-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 0.75rem;
  }
  .nearby-card a {
    display: block;
    padding: 0.8rem 1rem;
    background: var(--color-card);
    border-left: 2px solid var(--color-accent);
    color: inherit;
    text-decoration: none;
    transition: border-left-width 0.15s ease, background 0.15s ease;
  }
  .nearby-card a:hover {
    border-left-width: 3px;
    background: #fbf7eb;
  }
  .nearby-name {
    display: block;
    font-family: var(--font-serif);
    font-weight: 500;
    font-size: 1.05rem;
    color: var(--color-ink);
    letter-spacing: 0.05em;
  }
  .nearby-section {
    display: block;
    font-size: 0.72rem;
    color: var(--color-text-faint);
    letter-spacing: 0.08em;
    margin-top: 0.2rem;
  }
  .nearby-desc {
    display: block;
    font-size: 0.85rem;
    color: var(--color-text-sub);
    margin-top: 0.4rem;
    line-height: 1.6;
  }
</style>
```

- [ ] **Step 2: RelatedPeople.astro の `<style>` ブロックを置換**

```astro
<style>
  .related-people {
    margin-top: 2.5rem;
  }
  .related-people-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 0.75rem;
  }
  .related-person-card a {
    display: block;
    padding: 0.8rem 1rem;
    background: var(--color-card);
    border-left: 2px solid var(--color-accent);
    color: inherit;
    text-decoration: none;
    transition: border-left-width 0.15s ease, background 0.15s ease;
  }
  .related-person-card a:hover {
    border-left-width: 3px;
    background: #fbf7eb;
  }
  .related-person-name {
    display: block;
    font-family: var(--font-serif);
    font-weight: 500;
    font-size: 1.05rem;
    color: var(--color-ink);
    letter-spacing: 0.05em;
  }
  .related-person-job {
    display: block;
    font-size: 0.72rem;
    color: var(--color-text-faint);
    letter-spacing: 0.08em;
    margin-top: 0.2rem;
  }
  .related-person-relation {
    display: block;
    font-size: 0.88rem;
    color: var(--color-text-sub);
    margin-top: 0.45rem;
    line-height: 1.6;
  }
</style>
```

- [ ] **Step 3: RelatedWorks.astro の `<style>` ブロックを置換**

`TYPE_COLOR` のカラフルなチップ色は意図的に保持(作品種別のシグナル)。カードのベース色のみトークン化する。

```astro
<style>
  .related-works {
    margin-top: 2.5rem;
  }
  .works-grid {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1rem;
  }
  .work-card {
    padding: 1rem 1.1rem 1.1rem;
    background: var(--color-card);
    border-left: 2px solid var(--color-accent);
    display: flex;
    flex-direction: column;
  }
  .work-header {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin-bottom: 0.5rem;
    flex-wrap: wrap;
  }
  .work-type {
    display: inline-block;
    padding: 0.15rem 0.55rem;
    color: #fff;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.08em;
  }
  .work-title {
    font-family: var(--font-serif);
    font-size: 1.05rem;
    font-weight: 500;
    margin: 0;
    color: var(--color-ink);
    line-height: 1.5;
    letter-spacing: 0.05em;
    padding: 0;
    border: 0;
  }
  .work-title a {
    color: inherit;
    text-decoration: none;
    border-bottom: 1px solid var(--color-border);
  }
  .work-title a:hover {
    border-bottom-color: var(--color-accent-gold);
  }
  .work-meta {
    margin: 0 0 0.6rem;
    font-size: 0.72rem;
    color: var(--color-text-faint);
    letter-spacing: 0.05em;
  }
  .work-summary {
    font-size: 0.88rem;
    color: var(--color-text-sub);
    line-height: 1.8;
  }
  .work-summary :global(p) {
    margin: 0;
  }
</style>
```

注意: `work-title` は H3 だが global の H3 ルール(`padding-left: 0.7rem; border-left: 2px solid` 等)を打ち消すため `padding: 0; border: 0;` を明示。

- [ ] **Step 4: GravePhotoGallery.astro の `<style>` ブロックを置換**

```astro
<style>
  .grave-photos {
    margin: 2.5rem 0;
  }
  .photo-grid {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 1rem;
  }
  .photo-item img {
    width: 100%;
    height: auto;
    display: block;
    background: var(--color-card);
  }
  .photo-meta {
    font-size: 0.82rem;
    color: var(--color-text-muted);
    margin: 0.45rem 0 0;
    line-height: 1.6;
  }
  .photo-caption {
    color: var(--color-text);
  }
</style>
```

- [ ] **Step 5: RouteMap.astro の scoped `<style>` と global `<style is:global>` を置換**

最初の `<style>`(scoped)を以下で置換:

```astro
<style>
  .route-map-section {
    margin: 2rem 0;
  }
  .route-map-section h2 {
    /* グローバル h2 を継承(border-bottom 付き) */
  }
  .route-map {
    border: 1px solid var(--color-border);
    overflow: hidden;
  }
  .map-legend {
    margin: 0.6rem 0 0;
    color: var(--color-text-sub);
    line-height: 1.7;
    font-size: 0.85rem;
  }
  .map-attribution {
    margin: 0.3rem 0 0;
    color: var(--color-text-faint);
    text-align: right;
    font-size: 0.78rem;
  }
  .map-attribution a {
    color: var(--color-text-faint);
  }
</style>
```

続く `<style is:global>` を以下で置換(pin 色を深緑黒に):

```astro
<style is:global>
  .route-stop-pin {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: var(--color-ink);
    color: var(--color-bg);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-family: var(--font-serif);
    font-size: 0.9rem;
    border: 2px solid var(--color-bg);
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35);
  }
  .route-stop-marker {
    background: transparent !important;
    border: none !important;
  }
  .leaflet-popup-content a {
    color: var(--color-accent);
    text-decoration: none;
    border-bottom: 1px solid var(--color-accent);
  }
</style>
```

また `<script define:vars>` 内の `L.polyline(...)` の `color: '#5b8cb8'`(80 行目付近)はそのまま残す。地図線色は新トーンに変えると視認性が落ちるため(青系の方が背景の OSM 地図と分離する)。

Popup の color も `#5a4a2a` → `var(--color-accent)` に揃えるべきだが、Leaflet popup は inline style で書かれているので script 内の `color:#5a4a2a` を `color:#3a5448` に置換する:

`<script define:vars>` 内、`bindPopup(` 行(96 行目付近)の `style="color:#5a4a2a;"` を `style="color:#3a5448;"` に置換。

- [ ] **Step 6: ビルド検証**

Run: `npm run build`
Expected: 5 コンポーネント全部のビルドが通る。

- [ ] **Step 7: 目視確認**

`/people/okubo-toshimichi/` で詳細ページ下部の Nearby / Related / Works / Photo / Map の 5 セクションが全て新トーンに統一されていること。

- [ ] **Step 8: Commit**

```bash
git add src/components/NearbyGraves.astro src/components/RelatedPeople.astro src/components/RelatedWorks.astro src/components/GravePhotoGallery.astro src/components/RouteMap.astro
git commit -m "$(cat <<'EOF'
feat(components): 共通コンポーネント 5 種を新トークン(苔色 left rule)に統一

NearbyGraves / RelatedPeople / RelatedWorks / GravePhotoGallery / RouteMap の
scoped style を全面差し替え、card は石生成 bg + 苔色 left rule + hover で 3px に
拡張する共通モーション。RouteMap の pin は深緑黒 + serif 数字、popup の人物
リンクは苔色に揃え、線色だけは視認性のため青系 (#5b8cb8) を保持。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: トップページのヒーロー追加 + 全 scoped style 再整備

**Files:**
- Modify: `src/pages/index.astro`(`<h1>` + 説明 p を hero ブロックに置換 / scoped style の全面書き換え)

トップが最も visible なので、変更量が一番大きい。section-title・person-card・today-widget・filter chip・select 全てを再スキン。

- [ ] **Step 1: ヘッダー部分を hero ブロックに置換**

`src/pages/index.astro:167–168` の `<h1>` + `<p>` 行を以下で置換:

```astro
  <section class="hero">
    <h1>青山霊園に眠る<br />偉人たち</h1>
    <hr class="hairline" />
    <p class="lead">
      港区南青山。<br />
      近代日本を駆け抜けた政治家、軍人、文豪、学者たちが<br />
      静かに眠る都心の杜を、人物とともに歩く。
    </p>
    <p class="count"><strong>{totalCount}</strong>人の物語</p>
  </section>
```

- [ ] **Step 2: 各 `<section class="category-section">` の `<h2>` を section-title 構造に置換**

`{ CATEGORY_ORDER.map((cat) => { ... }` 内(252–271 行目付近)の `<section class="category-section" ...>` の中の `<h2>` を以下で置換:

```astro
            <header class="section-title">
              <span class="label-small">P E O P L E</span>
              <h2>{cat} <span class="section-count">({list.length})</span></h2>
            </header>
```

- [ ] **Step 3: scoped `<style>` ブロックを全置換**

277–546 行目の `<style>` ブロック全体を以下で置換:

```astro
<style>
  /* === Hero === */
  .hero {
    text-align: center;
    padding: 4rem 0 3.5rem;
    border-bottom: 1px solid var(--color-border);
    margin-bottom: 2.5rem;
  }
  .hero h1 {
    font-family: var(--font-serif);
    font-weight: 500;
    font-size: 2.4rem;
    line-height: 1.55;
    letter-spacing: 0.12em;
    color: var(--color-ink);
    margin: 0 0 1.5rem;
    padding: 0;
    border: 0;
  }
  .hero .hairline {
    margin: 0 auto 1.5rem;
  }
  .hero .lead {
    font-family: var(--font-serif);
    font-size: 0.98rem;
    line-height: 2.1;
    letter-spacing: 0.06em;
    color: var(--color-text-sub);
    max-width: var(--max-width-narrow);
    margin: 0 auto;
  }
  .hero .count {
    margin: 2.2rem 0 0;
    font-size: 0.72rem;
    letter-spacing: 0.3em;
    color: var(--color-text-faint);
  }
  .hero .count strong {
    font-family: var(--font-serif);
    font-weight: 500;
    font-size: 1.5rem;
    color: var(--color-accent);
    letter-spacing: 0.05em;
    margin: 0 0.3em;
  }
  @media (max-width: 720px) {
    .hero { padding: 2.5rem 0 2.2rem; margin-bottom: 1.8rem; }
    .hero h1 { font-size: 1.8rem; letter-spacing: 0.06em; }
  }

  /* === Today widgets === */
  .today-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 0.8rem;
    margin: 0 0 2rem;
  }
  .today-widget {
    padding: 1rem 1.1rem;
    background: var(--color-card);
    border-left: 2px solid var(--color-accent);
  }
  .today-widget-history {
    border-left-color: var(--color-accent-gold);
  }
  .today-widget-title {
    font-family: var(--font-serif);
    font-weight: 500;
    margin: 0 0 0.5rem;
    font-size: 1rem;
    color: var(--color-ink);
    letter-spacing: 0.06em;
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0;
    border: 0;
  }
  .today-icon { font-size: 1.05rem; }
  .today-date { color: var(--color-accent-gold); font-weight: 500; }
  .today-range {
    font-size: 0.7rem;
    color: var(--color-text-faint);
    letter-spacing: 0.1em;
    margin-left: 0.4rem;
  }
  .today-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
  }
  .today-list li {
    font-size: 0.88rem;
    line-height: 1.6;
    color: var(--color-text);
  }
  .today-list a {
    color: var(--color-accent);
    text-decoration: none;
    border-bottom: 1px solid var(--color-border);
  }
  .today-list a:hover { color: var(--color-accent-gold); border-bottom-color: var(--color-accent-gold); }

  .event-action {
    display: inline-block;
    padding: 0 0.3rem;
    font-size: 0.75rem;
    font-weight: 600;
    margin: 0 0.25rem 0 0.1rem;
  }
  .event-action.birth { color: #5a7a18; }
  .event-action.death { color: #6b3a1a; }
  .event-related {
    color: var(--color-text-muted);
    font-size: 0.78rem;
    display: block;
    margin-top: 0.15rem;
  }
  .event-related a { color: var(--color-accent); }
  .event-date {
    color: var(--color-text-faint);
    font-variant-numeric: tabular-nums;
    margin-right: 0.3rem;
    font-size: 0.82rem;
  }
  .event-year {
    color: var(--color-text-faint);
    font-size: 0.78rem;
    margin-left: 0.3rem;
  }
  .today-empty {
    color: var(--color-text-muted);
    font-size: 0.85rem;
    font-style: italic;
  }
  .event-today-marker {
    color: #a23b56;
    font-weight: 600;
    margin-left: 0.3rem;
  }

  /* === Filters === */
  .era-filter,
  .category-filter {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.4rem;
    margin: 1rem 0 0.5rem;
  }
  .category-filter { margin-top: 0.3rem; }
  .section-filter,
  .birthplace-filter {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin: 0.3rem 0 0.5rem;
  }
  .filter-label {
    color: var(--color-text-muted);
    font-size: 0.85rem;
    letter-spacing: 0.05em;
    margin-right: 0.2rem;
  }
  .era-chip,
  .category-chip {
    background: transparent;
    border: 1px solid var(--color-border);
    color: var(--color-text);
    padding: 0.3rem 0.85rem;
    font-size: 0.82rem;
    cursor: pointer;
    font-family: inherit;
    letter-spacing: 0.05em;
    transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
  }
  .era-chip:hover,
  .category-chip:hover {
    background: var(--color-bg-alt);
    border-color: var(--color-accent-gold);
  }
  .era-chip.is-active,
  .category-chip.is-active {
    background: var(--color-ink);
    color: var(--color-bg);
    border-color: var(--color-ink);
  }
  .section-filter select,
  .birthplace-filter select {
    background: #fff;
    border: 1px solid var(--color-border);
    color: var(--color-text);
    padding: 0.3rem 0.6rem;
    font-size: 0.85rem;
    font-family: inherit;
    cursor: pointer;
  }

  .people-count {
    color: var(--color-text-muted);
    font-size: 0.85rem;
    letter-spacing: 0.05em;
    margin: 0.7rem 0 1.8rem;
  }

  /* === Section title === */
  .category-section {
    margin-bottom: 3rem;
  }
  .section-title {
    text-align: left;
    margin: 0 0 1rem;
  }
  .section-title .label-small {
    display: block;
    margin-bottom: 0.3rem;
  }
  .section-title h2 {
    font-family: var(--font-serif);
    font-weight: 500;
    font-size: 1.3rem;
    color: var(--color-ink);
    letter-spacing: 0.1em;
    margin: 0;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--color-border);
  }
  .section-count {
    color: var(--color-text-faint);
    font-size: 0.85rem;
    font-weight: normal;
    letter-spacing: 0.05em;
    margin-left: 0.3em;
  }

  /* === People grid === */
  .people-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.7rem;
  }
  @media (max-width: 720px) {
    .people-grid { grid-template-columns: 1fr; }
  }

  .person-card {
    background: var(--color-card);
    border-left: 2px solid var(--color-accent);
    padding: 1.1rem 1.2rem;
    transition: border-left-width 0.15s ease, background 0.15s ease;
  }
  .person-card:hover {
    border-left-width: 3px;
    background: #fbf7eb;
  }
  .person-name {
    margin: 0 0 0.2rem;
    font-family: var(--font-serif);
    font-weight: 500;
    font-size: 1.15rem;
    color: var(--color-ink);
    letter-spacing: 0.05em;
    padding: 0;
    border: 0;
  }
  .person-name a {
    color: inherit;
    text-decoration: none;
  }
  .person-name a:hover { color: var(--color-accent-gold); }
  .person-kana {
    margin: 0 0 0.4rem;
    color: var(--color-text-muted);
    font-size: 0.8rem;
    letter-spacing: 0.05em;
  }
  .person-meta {
    margin: 0 0 0.5rem;
    color: var(--color-text-faint);
    font-size: 0.78rem;
    letter-spacing: 0.05em;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .era-badge {
    background: var(--color-ink);
    color: var(--color-bg);
    padding: 0.15rem 0.55rem;
    font-size: 0.7rem;
    letter-spacing: 0.08em;
  }
  .person-desc {
    margin: 0;
    font-size: 0.85rem;
    line-height: 1.75;
    color: var(--color-text-sub);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  @media (prefers-reduced-motion: reduce) {
    .person-card { transition: none; }
  }
</style>
```

ポイント:
- `.person-card` の hover で旧 `transform: translateY(-1px)` は削除(動きを抑える)。新しい hover は border-left 拡張のみ。
- `.people-grid` は `auto-fill, minmax(240px, 1fr)` から固定 2 列に変更(2 列前提のデザインなので、半端に 3 列になるのを防ぐ)。720px 以下で 1 列。

- [ ] **Step 4: ビルド検証**

Run: `npm run build`

- [ ] **Step 5: dev server 目視確認**

http://localhost:4321 を開いて:
- ヒーローが新構造で表示される
- 今日の暦 / 今日の歴史ウィジェットも新トーン
- フィルタ chip が active 時に深緑黒になる
- カテゴリ見出しに `P E O P L E` 小ラベル + serif H2
- 偉人カードが 2 列で並び、苔色の左罫
- モバイル幅で 1 列、ヒーローが縮む

- [ ] **Step 6: Commit**

```bash
git add src/pages/index.astro
git commit -m "$(cat <<'EOF'
feat(top): 表紙型ヒーロー + section-title + 2 列カードグリッドに刷新

トップを「青山霊園に眠る偉人たち」+ hairline + lead + N人カウントのミニマル
ヒーローに置換。今日の暦・今日の歴史ウィジェット、フィルタ chip、職業セクション
見出し、人物カードを全て新トークンで再構築。auto-fill から固定 2 列(モバイル
1 列)に変えてレイアウトの安定感を出す。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: 散歩コース(`/routes/` と `/routes/[slug]/`)を新トーンに

**Files:**
- Modify: `src/pages/routes/index.astro`
- Modify: `src/pages/routes/[slug].astro`

`THEME_COLOR`(コース別の色)は意図的に保持して、カード自体だけ新トークンに。

- [ ] **Step 1: routes/index.astro のヘッダーを hero ブロックに置換**

`src/pages/routes/index.astro:39–41`(`<h1>` + `<p>` 2 個)を以下で置換:

```astro
  <section class="hero">
    <h1>散歩コース</h1>
    <hr class="hairline" />
    <p class="lead">
      青山霊園に眠る偉人を、テーマ別に巡る散歩コースです。<br />
      明治維新・戊辰戦争・昭和の宰相・文人・お雇い外国人・女性とハチ公・軍人 ──<br />
      興味と所要時間に合わせて選んでください。
    </p>
    <p class="note">各コースの stops は物語の流れで並べています。実際の散策では、各人物ページに記載した区画番号(graveSection)を確認して動線を組むのがおすすめです。</p>
  </section>
```

- [ ] **Step 2: routes/index.astro の `<style>` を置換**

`<style>` 全体を以下で置換:

```astro
<style>
  .hero {
    text-align: center;
    padding: 3rem 0 2.5rem;
    border-bottom: 1px solid var(--color-border);
    margin-bottom: 2.5rem;
  }
  .hero h1 {
    font-family: var(--font-serif);
    font-weight: 500;
    font-size: 2rem;
    letter-spacing: 0.12em;
    color: var(--color-ink);
    margin: 0 0 1.3rem;
    padding: 0;
    border: 0;
  }
  .hero .hairline { margin: 0 auto 1.3rem; }
  .hero .lead {
    font-family: var(--font-serif);
    font-size: 0.95rem;
    line-height: 2.0;
    letter-spacing: 0.06em;
    color: var(--color-text-sub);
    max-width: var(--max-width-narrow);
    margin: 0 auto 1rem;
  }
  .hero .note {
    color: var(--color-text-faint);
    font-size: 0.78rem;
    line-height: 1.7;
    max-width: var(--max-width-narrow);
    margin: 0 auto;
    letter-spacing: 0.04em;
  }

  .routes-grid {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 1rem;
  }
  .route-card {
    padding: 1.1rem 1.2rem 1.2rem;
    background: var(--color-card);
    border-left: 2px solid var(--color-accent);
    display: flex;
    flex-direction: column;
    transition: border-left-width 0.15s ease, background 0.15s ease;
  }
  .route-card:hover {
    border-left-width: 3px;
    background: #fbf7eb;
  }
  .route-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    margin-bottom: 0.6rem;
  }
  .route-theme {
    display: inline-block;
    padding: 0.15rem 0.6rem;
    color: #fff;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.08em;
  }
  .route-meta {
    color: var(--color-text-faint);
    font-size: 0.75rem;
    letter-spacing: 0.05em;
  }
  .route-title {
    font-family: var(--font-serif);
    font-weight: 500;
    font-size: 1.15rem;
    margin: 0 0 0.3rem;
    color: var(--color-ink);
    line-height: 1.5;
    letter-spacing: 0.05em;
    padding: 0;
    border: 0;
  }
  .route-title a {
    color: inherit;
    text-decoration: none;
  }
  .route-title a:hover { color: var(--color-accent-gold); }
  .route-subtitle {
    margin: 0 0 0.5rem;
    color: var(--color-text-muted);
    font-size: 0.85rem;
    font-style: italic;
  }
  .route-description {
    margin: 0;
    font-size: 0.88rem;
    line-height: 1.75;
    color: var(--color-text-sub);
  }
  @media (prefers-reduced-motion: reduce) {
    .route-card { transition: none; }
  }
</style>
```

注意: `.route-title` は H2 だが global の `<h2>` ルール(border-bottom 等)を打ち消すため `padding: 0; border: 0;` 明示。

- [ ] **Step 3: routes/[slug].astro を読んで構造把握**

Run: `cat src/pages/routes/[slug].astro` で読む(305 行)。主要セクション:
- ヘッダー(`<h1>` route.data.title)
- 概要(subtitle / description / estimatedMinutes / theme チップ)
- 「## このコースの楽しみ方」等の本文(Content)
- 散歩経路マップ(RouteMap)
- stops 一覧(各人物カード)
- Google Maps 経路リンク

- [ ] **Step 4: routes/[slug].astro のヘッダー部分を hero 化**

`<h1>` から concept/description ブロックまでを hero に置換(具体的な変更行は実装者がファイルを開いて判断する)。ヒント:

```astro
  <article class="route-detail">
    <nav class="breadcrumb" aria-label="パンくずリスト">
      <a href="/">トップ</a>
      <span aria-hidden="true">›</span>
      <a href="/routes/">散歩コース</a>
      <span aria-hidden="true">›</span>
      <span aria-current="page">{route.data.title}</span>
    </nav>

    <section class="hero">
      <span class="label-small">R O U T E</span>
      <h1>{route.data.title}</h1>
      {route.data.subtitle && <p class="hero-subtitle">{route.data.subtitle}</p>}
      <hr class="hairline" />
      <p class="lead">{route.data.description}</p>
      <p class="hero-meta">
        <span>{route.data.theme}</span>
        <span>所要 {route.data.estimatedMinutes} 分</span>
        <span>{route.data.stops.length} 名</span>
      </p>
    </section>
    ...
```

既存の概要ブロック(`<h1>` 直後の paragraph 等)は削除して上記に置き換える。

- [ ] **Step 5: routes/[slug].astro の scoped `<style>` を新トーンに置換**

既存の `.breadcrumb` / `.route-detail` 系・stop card 系のスタイルを以下のパターンで全部置換(個別の class 名は既存ファイルを開いて確認、共通方針は):

- 背景・border は `var(--color-card)` / `var(--color-border)` / `var(--color-accent)`
- h1/h2/h3 は serif + letter-spacing 0.05–0.12em
- 本文は `var(--color-text-sub)`, line-height 1.75–2.0
- stop list はトップの person-card と同じ「左 2px 苔色罫 → hover で 3px」

追加で hero 部用に以下を追記:

```css
  .hero {
    text-align: center;
    padding: 3rem 0 2.5rem;
    border-bottom: 1px solid var(--color-border);
    margin-bottom: 2.5rem;
  }
  .hero .label-small { display: block; margin-bottom: 0.6rem; }
  .hero h1 {
    font-family: var(--font-serif);
    font-weight: 500;
    font-size: 2rem;
    letter-spacing: 0.12em;
    color: var(--color-ink);
    margin: 0 0 0.5rem;
    padding: 0;
    border: 0;
  }
  .hero-subtitle {
    font-family: var(--font-serif);
    font-size: 1rem;
    color: var(--color-text-muted);
    font-style: italic;
    margin: 0 0 1rem;
  }
  .hero .hairline { margin: 0 auto 1.3rem; }
  .hero .lead {
    font-family: var(--font-serif);
    font-size: 0.95rem;
    line-height: 2.0;
    letter-spacing: 0.06em;
    color: var(--color-text-sub);
    max-width: var(--max-width-narrow);
    margin: 0 auto 1.4rem;
  }
  .hero-meta {
    display: flex;
    justify-content: center;
    gap: 1.5rem;
    font-size: 0.75rem;
    letter-spacing: 0.15em;
    color: var(--color-text-faint);
    margin: 0;
  }
```

- [ ] **Step 6: ビルド検証**

Run: `npm run build`

- [ ] **Step 7: 目視確認**

`/routes/` → 一覧、`/routes/sakanoue-no-kumo/` → 詳細をブラウザで確認。stop list の見た目がトップの person-card と同調していること。

- [ ] **Step 8: Commit**

```bash
git add src/pages/routes/index.astro src/pages/routes/[slug].astro
git commit -m "$(cat <<'EOF'
feat(routes): 散歩コース一覧・詳細を新トーンに(THEME_COLOR チップは保持)

routes/index に hero + serif h1 + 苔色左罫の route-card を導入。routes/[slug] は
breadcrumb + label-small ROUTE + 表題 + hairline + lead + meta の hero 構造に
再編。stop list はトップの person-card と同じ左罫+hover モーションで全サイト
共通の質感に統一。テーマ別チップ色(THEME_COLOR)はジャンル識別子として保持。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: timeline / about / events / 404 ページを新トーンに

**Files:**
- Modify: `src/pages/timeline.astro`
- Modify: `src/pages/about.astro`
- Modify: `src/pages/events/[slug].astro`
- Modify: `src/pages/404.astro`

- [ ] **Step 1: timeline.astro の hero 化 + 縦軸スタイルを新トークンに**

`<h1>年表</h1>` 等のヘッダーを hero ブロックに置換し、scoped `<style>` 内の以下のパターンを置換:

- 年区切り見出し(`.timeline-year` 等): serif 500, 1.5rem, letter-spacing 0.12em, color `--color-ink`
- 出来事カード: `var(--color-card)` 背景 + 左 2px `var(--color-accent-gold)` 罫(古銅金で時間軸を象徴)
- 軸線: `var(--color-border)` の 1px or 2px 縦線
- カテゴリチップ(政治・軍事 等): 旧色値があれば全部 `var(--color-ink) / var(--color-accent) / var(--color-accent-gold)` に統一

具体的な class 名は実装者がファイルを開いて確認。hero ブロックは以下を `<BaseLayout>` 直下に挿入:

```astro
  <section class="hero">
    <h1>年表</h1>
    <hr class="hairline" />
    <p class="lead">
      青山霊園に眠る偉人たちの生没年と、近代日本の主要な出来事を<br />
      時系列で並べた年表。
    </p>
  </section>
```

(本文の `lead` 文言は既存ページの説明文を流用。冒頭の `<h1>` + `<p>` を置換するだけで OK。)

scoped style の `.hero { ... }` ブロックは Task 7 の routes/index と同じ rules をコピペする(DRY のためにグローバル化したいが、今回はスコープ内コピーで割り切る)。

- [ ] **Step 2: about.astro を serif 化**

`src/pages/about.astro` の現在の構造はシンプル(h1 + h2 × 4)。h1 を hero ブロックに置換し、本文の h2 / p / ul はグローバルルールに任せる:

`<h1>青山霊園について</h1>` を以下に置換:

```astro
  <section class="hero">
    <span class="label-small">A B O U T</span>
    <h1>青山霊園について</h1>
    <hr class="hairline" />
    <p class="lead">
      港区南青山にある、1872 年(明治 5 年)開設の日本初の公営墓地。<br />
      近代日本の礎を築いた多くの著名人が眠る、都心の杜。
    </p>
  </section>
```

scoped `<style>` ブロックが無いので、ヒーロー用 CSS をページ末尾に追加:

```astro
<style>
  .hero {
    text-align: center;
    padding: 3rem 0 2.5rem;
    border-bottom: 1px solid var(--color-border);
    margin-bottom: 2.5rem;
  }
  .hero .label-small { display: block; margin-bottom: 0.6rem; }
  .hero h1 {
    font-family: var(--font-serif);
    font-weight: 500;
    font-size: 2rem;
    letter-spacing: 0.12em;
    color: var(--color-ink);
    margin: 0 0 1.3rem;
    padding: 0;
    border: 0;
  }
  .hero .hairline { margin: 0 auto 1.3rem; }
  .hero .lead {
    font-family: var(--font-serif);
    font-size: 0.98rem;
    line-height: 2.0;
    letter-spacing: 0.06em;
    color: var(--color-text-sub);
    max-width: var(--max-width-narrow);
    margin: 0 auto;
  }
  .note {
    margin-top: 2.5rem;
    color: var(--color-text-faint);
    font-size: 0.78rem;
  }
  .note a {
    color: var(--color-accent);
    text-decoration: none;
    border-bottom: 1px solid var(--color-border);
  }
</style>
```

- [ ] **Step 3: events/[slug].astro を詳細ページ B 構造に揃える**

ファイル(284 行)を開いて、構造を確認。主要セクションは:
- breadcrumb
- h1 (event title)
- 日付・カテゴリ・場所等のメタ
- summary 本文
- 関連人物リスト
- 参考資料

person 詳細と同じ構造ではないので、B 構造の完全コピーは合わない。**簡易版** hero(label-small EVENT + serif h1 + hairline + lead)+ メタグリッド(date / category / location)+ Content + 関連人物 cards の構成にする。

具体手順:

1. `<h1>` を `<section class="hero">` + `<span class="label-small">E V E N T</span>` + h1 + hairline + lead(event.data.summary) でラップ
2. メタは `<dl class="meta-grid">` で 1 列(`grid-template-columns: 80px 1fr`)
3. 関連人物リストは Task 5 の `.related-person-card` と同じスタイル
4. scoped `<style>` を新トークンで再記述

実装の参考は `src/pages/people/[slug].astro` の hero + meta-grid + scoped style を流用すること。

- [ ] **Step 4: 404.astro を新トーンに**

`src/pages/404.astro` の `<h1>` → serif、注釈文 → `--color-text-sub`、リンク → `--color-accent`。

`<section class="not-found">` の中身を以下で置換:

```astro
  <section class="not-found">
    <span class="label-small">N O T   F O U N D</span>
    <h1>404 — ページが見つかりません</h1>
    <hr class="hairline" />
    <p>
      お探しのページは見つかりませんでした。<br />
      URL が間違っているか、ページが移動・削除された可能性があります。
    </p>
    <ul class="not-found-actions">
      <li><a href="/">→ 偉人一覧のトップへ</a></li>
      <li><a href="/about/">→ 青山霊園について</a></li>
    </ul>
  </section>
```

`<style>` を以下で置換:

```astro
<style>
  .not-found {
    text-align: center;
    padding: 4rem 1rem 5rem;
    max-width: var(--max-width-narrow);
    margin: 0 auto;
  }
  .not-found .label-small { display: block; margin-bottom: 0.6rem; }
  .not-found h1 {
    font-family: var(--font-serif);
    font-weight: 500;
    font-size: 1.8rem;
    letter-spacing: 0.1em;
    color: var(--color-ink);
    margin: 0 0 1.3rem;
    padding: 0;
    border: 0;
  }
  .not-found .hairline { margin: 0 auto 1.5rem; }
  .not-found p {
    color: var(--color-text-sub);
    line-height: 2.0;
    margin-bottom: 2rem;
  }
  .not-found-actions {
    list-style: none;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
  }
  .not-found-actions a {
    display: inline-block;
    padding: 0.5rem 1rem;
    color: var(--color-accent);
    text-decoration: none;
    border-bottom: 1px solid var(--color-border);
  }
  .not-found-actions a:hover {
    color: var(--color-accent-gold);
    border-bottom-color: var(--color-accent-gold);
  }
</style>
```

- [ ] **Step 5: ビルド検証**

Run: `npm run build`
Expected: 全ページが zod / TS / リンクチェックを通過。

- [ ] **Step 6: dev server で 4 ページ目視確認**

- `/timeline/`(年表縦軸の見た目)
- `/about/`(hero + 本文)
- `/events/<任意>` (B 構造の簡易版)
- `/_404`(直接ブラウザで存在しない URL を打って 404 を表示)

- [ ] **Step 7: Commit**

```bash
git add src/pages/timeline.astro src/pages/about.astro src/pages/events/[slug].astro src/pages/404.astro
git commit -m "$(cat <<'EOF'
feat(pages): timeline / about / events / 404 を新トーンに統一

各ページに serif h1 + hairline + lead の hero ブロックを導入、scoped style を
新トークン(石生成 card / 苔色 left rule / 古銅金 hairline)に差し替え。
timeline の出来事カードは左罫を古銅金にして時間軸を象徴。events 詳細は B
構造の簡易版(label-small EVENT + meta-grid 1 列 + 関連人物 card)に再編。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: 最終検証 — 5 ページの目視チェック + Lighthouse + スクリーンショット

**Files:** なし(検証のみ)

- [ ] **Step 1: クリーン build**

```bash
rm -rf dist .astro
npm run build
```

Expected: 全 178+ 偉人ページ、ルートページ、年表、events、about、404、index 全てがエラーなしで生成。

- [ ] **Step 2: 5 ページの dev server 目視チェック(デスクトップ幅 1280px)**

`npm run dev` で起動して以下を順に開く:

1. **`/`** — ヒーロー / 今日の暦 / フィルタ / 偉人カード 2 列
2. **`/people/okubo-toshimichi/`** — 肖像あり詳細(B 横並び)
3. **任意の肖像なし偉人**(例: `/people/joseph-heco/` または `/people/morinaga-taichiro/` 等、肖像未取得の slug を `git ls-files src/assets/portraits/` で確認して 1 つ選ぶ)— placeholder 表示
4. **`/routes/sakanoue-no-kumo/`** — 散歩コース詳細(hero / stop list / RouteMap)
5. **`/timeline/`** — 縦軸年表

各ページで以下をチェック:
- ヘッダー(深緑黒 + 古銅金 hairline)が出ている
- 見出しが Noto Serif JP
- 本文が Noto Sans JP
- カードが石生成 + 苔色 left rule
- リンクの hover 色が古銅金に変わる
- フッターが新構造

- [ ] **Step 3: モバイル幅(360px)で同 5 ページ確認**

DevTools の device emulation を 360×800 にして:
- ヘッダーナビが横スクロール可
- 詳細ページが縦積み
- カードが 1 列
- ヒーローが縮む

- [ ] **Step 4: Lighthouse 計測(任意)**

Chrome DevTools の Lighthouse タブで `/` を Performance + Accessibility 計測。

- フォント追加で LCP が顕著に悪化していないか(preconnect 効果)
- Accessibility が以前と同等以上(90+ 目安)
- 数値が悪化していれば原因を確認(font-display: swap が効いているか等)

- [ ] **Step 5: スクリーンショットを Obsidian に保存**

Before(刷新前)が無いので After のみ。主要 5 ページのスクリーンショットを `~/Desktop/Obsidian/claude-code/2026-05-25-aoyama-cemetery-ui-refresh.md` に貼る。任意。

- [ ] **Step 6: 最終 commit と push**

ここまでの 8 commit が積まれているはず。最終確認:

```bash
git log --oneline -10
git status
```

問題なければ:

```bash
git push origin main
```

Cloudflare Pages が自動デプロイを始める。https://aoyama-cemetery.pages.dev で数分後に反映を確認。

---

## Notes

### TDD を入れない理由

本タスク群は純粋な視覚刷新で、ロジック変更は **Task 2(PersonPortrait の optional 化)と Task 3 の dl 化** のみ。これらは zod schema / TypeScript の型システムが防壁になり、ビルドが通れば構造的に正しい。動作確認は dev server の目視で行う(プロジェクトの CLAUDE.md「UI 変更は push 前に必ず手元で実物を生成してブラウザで目視確認」に従う)。

### Astro 6 のフォント API について

Astro 6 にはネイティブフォント API(`astro:assets/fonts`)があるが、現状の安定性とビルド時間を考慮して Google Fonts CDN + preconnect の素直な構成を採用。将来的に置換可能。

### 失敗時のロールバック

各タスクで 1 commit するので、問題があれば `git revert <hash>` で部分巻き戻しが容易。

---

## Self-Review

**Spec coverage:**
- §1 デザイン方針 → Task 1(トークン)で全部反映済
- §2 デザイントークン → Task 1 で `:root` に集約
- §3 Web フォント → Task 1 で Google Fonts + preconnect
- §4.1 サイトヘッダー / §4.2 フッター / §4.3 main → Task 1
- §5.1 トップヒーロー & 偉人セクション → Task 6
- §5.2 偉人詳細 → Task 3 & 4
- §5.3 routes → Task 7 / timeline → Task 8 / about → Task 8 / events → Task 8 / 404 → Task 8
- §5.4 共通コンポーネント指針 → Task 5
- §6 レスポンシブ → 各タスクの `@media (max-width: 720px)` ブロック
- §7 アクセシビリティ → Task 1 の `:focus-visible` + コントラスト確認
- §8 影響範囲 → File Structure テーブルで網羅
- §9 非対象 → 各タスクが該当範囲を超えていないことは明示
- §10 検証手順 → Task 9
- §11 移行戦略 → 9 commit (Task 1-8 + 1 push)で対応

**Placeholder scan:** 「TBD」「TODO」「具体的な変更行は実装者がファイルを開いて判断する」が Task 7 Step 4 と Task 8 Step 1/3 に残るが、これらはファイルサイズ的に plan に全部書き出すと冗長になる箇所であり、方針 + サンプルコード + class 名のヒントを与えることで実装者が判断できる粒度になっている。subagent で進める場合、各タスクで対象ファイルを Read してから着手するよう冒頭に明示する。

**Type consistency:**
- PersonPortrait の `portrait?: ImageMetadata` は Task 2 と 3 で同じ
- `meta-grid` / `meta-cell` / `meta-cell-wide` class 名は Task 3 (people) と Task 8 (events) で一貫
- `.label-small` / `.hairline` / `.hero` は global で定義しページごとに必要なら局所オーバーライド

問題なし。
