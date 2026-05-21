# aoyama-cemetery サイト Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 青山霊園の偉人(初期は大久保利通 1 名)を紹介する Astro 静的サイトを構築し、Cloudflare Pages に public 公開する。

**Architecture:** Astro Content Collections で `.md` 1 ファイル = 偉人 1 ページ。GitHub (public) → Cloudflare Pages 自動デプロイ。

**Tech Stack:** Astro 5.x、TypeScript strict、`@astrojs/sitemap`、zod、Cloudflare Pages、GitHub Actions(不要、Cloudflare 側で完結)

**Spec:** `docs/superpowers/specs/2026-05-21-aoyama-cemetery-site-design.md`

**Note on TDD:** 本プロジェクトは静的サイトのため厳密な unit test は適用しない。代わりに各タスクで「ビルド成功」「ファイル生成確認」「ブラウザ目視」を verification gate とする。Astro Content Collection の zod スキーマがビルド時バリデーションの役割を果たす。

---

## File Structure

新規 L2 として `~/workspace/personal/aoyama-cemetery/` に配置。

```
aoyama-cemetery/
├── .gitignore
├── README.md                            # L2 README
├── CLAUDE.md                            # L2 規約(L0/L1 参照)
├── astro.config.mjs                     # site URL + sitemap integration
├── package.json
├── tsconfig.json
├── public/
│   ├── favicon.svg
│   └── robots.txt
├── src/
│   ├── pages/
│   │   ├── index.astro                  # トップ(偉人一覧)
│   │   ├── about.astro                  # 青山霊園の概要
│   │   └── people/[slug].astro          # 動的ルート(1 偉人 1 ページ)
│   ├── layouts/BaseLayout.astro         # 共通レイアウト + OGP
│   ├── content/
│   │   ├── config.ts                    # zod スキーマ
│   │   └── people/okubo-toshimichi.md   # 大久保利通
│   └── styles/global.css
└── docs/
    ├── project-logs/
    └── superpowers/
        ├── specs/                       # spec を L0 から移動
        └── plans/                       # plan を L0 から移動
```

---

## Task 1: L2 ディレクトリ作成と git init

**Files:**
- Create: `~/workspace/personal/aoyama-cemetery/.gitignore`
- Create: `~/workspace/personal/aoyama-cemetery/README.md`

- [ ] **Step 1: ディレクトリ作成**

Run:
```bash
mkdir -p ~/workspace/personal/aoyama-cemetery
cd ~/workspace/personal/aoyama-cemetery
```

- [ ] **Step 2: git init**

Run:
```bash
git init -b main
```

Expected: `Initialized empty Git repository in /Users/uchidayousuke/workspace/personal/aoyama-cemetery/.git/`

- [ ] **Step 3: .gitignore 作成**

Create `~/workspace/personal/aoyama-cemetery/.gitignore`:

```gitignore
# build output
dist/
.astro/

# dependencies
node_modules/

# logs
npm-debug.log*
yarn-debug.log*
yarn-error.log*
pnpm-debug.log*

# environment variables
.env
.env.production

# macOS
.DS_Store

# editor
.vscode/*
!.vscode/extensions.json
.idea/
```

- [ ] **Step 4: README.md 作成**

Create `~/workspace/personal/aoyama-cemetery/README.md`:

```markdown
# aoyama-cemetery

青山霊園に眠る偉人を紹介する静的サイト。

- **公開 URL**: https://aoyama-cemetery.pages.dev
- **スタック**: Astro + Cloudflare Pages
- **規約**: `CLAUDE.md` 参照(L0/L1/L2 階層)

## 開発

```bash
npm install
npm run dev      # http://localhost:4321
npm run build    # dist/ 生成
npm run preview  # 本番相当を確認
```

## 偉人追加方法

`src/content/people/<slug>.md` を 1 ファイル追加するだけで `/people/<slug>/` が生成されます。frontmatter スキーマは `src/content/config.ts` 参照。
```

- [ ] **Step 5: 初回コミット**

Run:
```bash
git add .gitignore README.md
git commit -m "chore: initialize aoyama-cemetery L2"
```

Expected: `[main (root-commit) ...] chore: initialize aoyama-cemetery L2`

---

## Task 2: Astro プロジェクト雛形作成

**Files:**
- Create: `package.json`, `tsconfig.json`, `astro.config.mjs`, `src/pages/index.astro`(Astro 雛形が自動生成)

- [ ] **Step 1: Astro minimal テンプレートで雛形作成**

Run(対話プロンプトを `--yes` でスキップ):
```bash
cd ~/workspace/personal/aoyama-cemetery
npm create astro@latest . -- --template minimal --typescript strict --install --no-git --yes
```

Expected: `npm install` が走り `package.json`, `tsconfig.json`, `astro.config.mjs`, `src/pages/index.astro` 等が生成される。`node_modules/` 作成。

注意: ディレクトリが空でない警告が出たら `--force` ではなく中身を確認。`.gitignore` `README.md` `.git/` のみなら継続して問題ない。

- [ ] **Step 2: sitemap integration を追加**

Run:
```bash
npx astro add sitemap --yes
```

Expected: `astro.config.mjs` に `@astrojs/sitemap` integration が追加され、`package.json` に依存追加される。

- [ ] **Step 3: ビルド確認(雛形が壊れていないことを確認)**

Run:
```bash
npm run build
```

Expected: エラーなく完了。`dist/` ディレクトリと `dist/index.html` が生成される。

- [ ] **Step 4: dist/index.html 存在確認**

Run:
```bash
ls dist/index.html
```

Expected: `dist/index.html` が表示される(エラーなし)

- [ ] **Step 5: コミット**

Run:
```bash
git add -A
git commit -m "chore: scaffold Astro project with sitemap"
```

---

## Task 3: astro.config.mjs に site URL を設定

**Files:**
- Modify: `astro.config.mjs`

- [ ] **Step 1: astro.config.mjs を確認**

Run:
```bash
cat astro.config.mjs
```

現在の中身を把握する(sitemap integration が追加されているはず)。

- [ ] **Step 2: site URL を追加**

`astro.config.mjs` の `defineConfig({ ... })` 内に `site: 'https://aoyama-cemetery.pages.dev'` を追加する。

最終的に以下のような形にする:

```js
// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://aoyama-cemetery.pages.dev',
  integrations: [sitemap()],
});
```

- [ ] **Step 3: ビルドして sitemap.xml が生成されることを確認**

Run:
```bash
npm run build
ls dist/sitemap-index.xml dist/sitemap-0.xml
```

Expected: 両ファイルが存在する。

- [ ] **Step 4: コミット**

Run:
```bash
git add astro.config.mjs
git commit -m "feat: set production site URL for sitemap"
```

---

## Task 4: Content Collection スキーマ定義

**Files:**
- Create: `src/content/config.ts`

- [ ] **Step 1: src/content/ ディレクトリ作成**

Run:
```bash
mkdir -p src/content/people
```

- [ ] **Step 2: src/content/config.ts 作成**

Create `src/content/config.ts`:

```ts
import { defineCollection, z } from 'astro:content';

const people = defineCollection({
  type: 'content',
  schema: z.object({
    name: z.string(),
    nameKana: z.string(),
    nameRomaji: z.string(),
    birthDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'YYYY-MM-DD 形式で入力'),
    deathDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'YYYY-MM-DD 形式で入力'),
    era: z.enum(['江戸', '明治', '大正', '昭和']),
    category: z.enum(['政治家', '文化人', '軍人', '実業家', '学者', 'その他']),
    graveSection: z.string().optional(),
    shortDescription: z.string().min(20).max(100),
    tags: z.array(z.string()).optional(),
    references: z
      .array(
        z.object({
          title: z.string(),
          url: z.string().url(),
        })
      )
      .optional(),
    ogImage: z.string().optional(),
  }),
});

export const collections = { people };
```

- [ ] **Step 3: 型チェックが通ることを確認**

Run:
```bash
npm run build
```

Expected: エラーなし(content/people/ が空でも問題ない)。

- [ ] **Step 4: コミット**

Run:
```bash
git add src/content/config.ts
git commit -m "feat: define people content collection schema"
```

---

## Task 5: 大久保利通の Markdown コンテンツ作成

**Files:**
- Create: `src/content/people/okubo-toshimichi.md`

- [ ] **Step 1: 大久保利通の事実関係を確認**

以下を確認する(Wikipedia 等から):
- 生年月日: 1830-09-26(文政13年8月10日)
- 没年月日: 1878-05-14(明治11年、紀尾井坂の変で暗殺)
- 役職: 初代内務卿、参議
- 業績: 明治維新三傑、廃藩置県、地租改正、殖産興業
- 青山霊園の墓所区画番号: 公式の最新情報を確認(分からない場合は frontmatter から省略 = 任意項目)

- [ ] **Step 2: src/content/people/okubo-toshimichi.md 作成**

Create `src/content/people/okubo-toshimichi.md`(frontmatter は spec のスキーマに準拠):

```markdown
---
name: 大久保 利通
nameKana: おおくぼ としみち
nameRomaji: Okubo Toshimichi
birthDate: "1830-09-26"
deathDate: "1878-05-14"
era: 明治
category: 政治家
shortDescription: 明治維新三傑の一人。初代内務卿として近代日本の基礎を築いた。
tags:
  - 明治維新
  - 薩摩藩
  - 内務省
references:
  - title: Wikipedia
    url: https://ja.wikipedia.org/wiki/大久保利通
---

## 生涯

(Claude が Wikipedia を要約・再構成して 300-500 字程度で記述。生まれ・西郷隆盛との関係・倒幕運動・明治政府での役割・紀尾井坂の変まで)

## 主な業績

- 廃藩置県(1871)
- 地租改正(1873)
- 殖産興業政策の推進
- 内務省の創設と初代内務卿就任(1873)
- 岩倉使節団の副使として欧米視察

## 青山霊園での墓所

(青山霊園内のどこに墓所があるか。区画番号と簡単な説明。情報源 = Wikipedia / 青山霊園公式 / 現地確認 のいずれか)
```

注意: 本文の事実関係は **必ず Wikipedia 等で照合**し、不確実な記述は書かない。スキーマ違反(必須項目欠落、enum 不一致)があるとビルドエラーになる。

- [ ] **Step 3: ビルドしてスキーマバリデーションを通過することを確認**

Run:
```bash
npm run build
```

Expected: エラーなく完了。

- [ ] **Step 4: 内容の事実確認**

`src/content/people/okubo-toshimichi.md` を読み返し、以下を再チェック:
- 没年月日が正確か
- 業績の年号が正確か
- 役職名が正確か
- 出典(references)が正しい URL か

問題があれば修正。

- [ ] **Step 5: コミット**

Run:
```bash
git add src/content/people/okubo-toshimichi.md
git commit -m "feat: add Okubo Toshimichi profile"
```

---

## Task 6: BaseLayout 作成(共通レイアウト + OGP)

**Files:**
- Create: `src/layouts/BaseLayout.astro`

- [ ] **Step 1: src/layouts/ ディレクトリ作成**

Run:
```bash
mkdir -p src/layouts
```

- [ ] **Step 2: BaseLayout.astro 作成**

Create `src/layouts/BaseLayout.astro`:

```astro
---
export interface Props {
  title: string;
  description: string;
  ogImage?: string;
}

const { title, description, ogImage } = Astro.props;
const canonicalURL = new URL(Astro.url.pathname, Astro.site);
const ogImageURL = ogImage
  ? new URL(ogImage, Astro.site).toString()
  : undefined;
---

<!DOCTYPE html>
<html lang="ja">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <title>{title}</title>
    <meta name="description" content={description} />
    <link rel="canonical" href={canonicalURL} />

    <!-- OGP -->
    <meta property="og:type" content="website" />
    <meta property="og:title" content={title} />
    <meta property="og:description" content={description} />
    <meta property="og:url" content={canonicalURL} />
    {ogImageURL && <meta property="og:image" content={ogImageURL} />}

    <!-- Twitter -->
    <meta name="twitter:card" content={ogImageURL ? 'summary_large_image' : 'summary'} />
    <meta name="twitter:title" content={title} />
    <meta name="twitter:description" content={description} />
    {ogImageURL && <meta name="twitter:image" content={ogImageURL} />}

    <link rel="stylesheet" href="/styles/global.css" />
  </head>
  <body>
    <header class="site-header">
      <nav>
        <a href="/" class="site-title">青山霊園 偉人録</a>
        <ul class="nav-links">
          <li><a href="/">トップ</a></li>
          <li><a href="/about/">青山霊園について</a></li>
        </ul>
      </nav>
    </header>

    <main>
      <slot />
    </main>

    <footer class="site-footer">
      <p>© 2026 aoyama-cemetery. 本サイトの偉人解説は Wikipedia 等の公開情報を元に再構成しています。</p>
    </footer>
  </body>
</html>
```

- [ ] **Step 3: グローバル CSS 作成**

Run:
```bash
mkdir -p public/styles
```

Create `public/styles/global.css`:

```css
:root {
  --color-text: #222;
  --color-text-muted: #666;
  --color-bg: #fafaf7;
  --color-accent: #6b4423;
  --color-border: #ddd;
  --max-width: 720px;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", "Yu Gothic", sans-serif;
  background: var(--color-bg);
  color: var(--color-text);
  line-height: 1.7;
}

.site-header {
  border-bottom: 1px solid var(--color-border);
  background: white;
}

.site-header nav {
  max-width: var(--max-width);
  margin: 0 auto;
  padding: 1rem;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
}

.site-title {
  font-weight: bold;
  font-size: 1.2rem;
  color: var(--color-accent);
  text-decoration: none;
}

.nav-links {
  list-style: none;
  display: flex;
  gap: 1.5rem;
  padding: 0;
  margin: 0;
}

.nav-links a {
  color: var(--color-text);
  text-decoration: none;
}

.nav-links a:hover {
  color: var(--color-accent);
}

main {
  max-width: var(--max-width);
  margin: 0 auto;
  padding: 2rem 1rem;
}

.site-footer {
  border-top: 1px solid var(--color-border);
  padding: 2rem 1rem;
  text-align: center;
  color: var(--color-text-muted);
  font-size: 0.85rem;
}

/* 偉人カード(トップ) */
.person-card {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1rem;
  background: white;
}

.person-card a {
  color: var(--color-accent);
  text-decoration: none;
  font-size: 1.3rem;
  font-weight: bold;
}

.person-card .meta {
  color: var(--color-text-muted);
  font-size: 0.9rem;
  margin: 0.3rem 0 0.7rem;
}

.person-card .description {
  margin: 0;
}

/* 偉人詳細ページ */
.person-detail h1 {
  margin-bottom: 0.2rem;
}

.person-detail .kana {
  color: var(--color-text-muted);
  font-size: 1rem;
  margin: 0 0 1rem;
}

.person-detail .meta-table {
  border-collapse: collapse;
  margin: 1rem 0 2rem;
  width: 100%;
}

.person-detail .meta-table th,
.person-detail .meta-table td {
  border-bottom: 1px solid var(--color-border);
  padding: 0.5rem;
  text-align: left;
}

.person-detail .meta-table th {
  background: #f5f3ee;
  width: 30%;
}
```

- [ ] **Step 4: ビルド確認**

Run:
```bash
npm run build
```

Expected: エラーなし。

- [ ] **Step 5: コミット**

Run:
```bash
git add src/layouts/BaseLayout.astro public/styles/global.css
git commit -m "feat: add BaseLayout with OGP meta and global styles"
```

---

## Task 7: トップページ作成(偉人一覧)

**Files:**
- Modify: `src/pages/index.astro`(雛形を上書き)

- [ ] **Step 1: src/pages/index.astro を上書き**

Overwrite `src/pages/index.astro`:

```astro
---
import { getCollection } from 'astro:content';
import BaseLayout from '../layouts/BaseLayout.astro';

const people = await getCollection('people');
people.sort((a, b) => a.data.deathDate.localeCompare(b.data.deathDate));

const title = '青山霊園 偉人録';
const description = '東京・青山霊園に眠る偉人たちを紹介するサイト。明治維新を担った政治家、文学者、軍人、文化人の足跡をたどります。';
---

<BaseLayout title={title} description={description}>
  <h1>青山霊園 偉人録</h1>
  <p>東京都港区にある青山霊園は、明治以降の日本を築いた多くの偉人が眠る場所です。本サイトでは、彼らの生涯と業績を紹介します。</p>

  <h2>掲載されている偉人</h2>
  <div class="people-list">
    {
      people.map((person) => (
        <article class="person-card">
          <a href={`/people/${person.slug}/`}>{person.data.name}</a>
          <p class="meta">
            {person.data.nameKana}({person.data.birthDate.slice(0, 4)} - {person.data.deathDate.slice(0, 4)})・{person.data.category}
          </p>
          <p class="description">{person.data.shortDescription}</p>
        </article>
      ))
    }
  </div>
</BaseLayout>
```

- [ ] **Step 2: ビルドして dist/index.html が大久保利通のリンクを含むことを確認**

Run:
```bash
npm run build
grep -c 'okubo-toshimichi' dist/index.html
```

Expected: `1` 以上(リンクが含まれている)。

- [ ] **Step 3: コミット**

Run:
```bash
git add src/pages/index.astro
git commit -m "feat: build homepage listing people"
```

---

## Task 8: About ページ作成

**Files:**
- Create: `src/pages/about.astro`

- [ ] **Step 1: src/pages/about.astro 作成**

Create `src/pages/about.astro`:

```astro
---
import BaseLayout from '../layouts/BaseLayout.astro';

const title = '青山霊園について - 青山霊園 偉人録';
const description = '青山霊園の歴史、所在地、アクセス方法。明治以降の日本を築いた偉人が眠る都立霊園。';
---

<BaseLayout title={title} description={description}>
  <h1>青山霊園について</h1>

  <h2>概要</h2>
  <p>青山霊園は東京都港区南青山にある、東京都が管理する都立霊園です。1872 年(明治 5 年)に開設され、日本初の公営墓地として知られます。総面積は約 26 万平方メートル。</p>

  <h2>所在地</h2>
  <p>東京都港区南青山 2-32-2</p>

  <h2>アクセス</h2>
  <ul>
    <li>東京メトロ銀座線・千代田線・半蔵門線「表参道」駅 徒歩 5 分</li>
    <li>都営大江戸線「青山一丁目」駅 徒歩 5 分</li>
  </ul>

  <h2>特徴</h2>
  <p>明治期に活躍した政治家、軍人、文人、実業家など、近代日本の礎を築いた多くの著名人が埋葬されています。春には桜の名所としても親しまれています。</p>

  <p class="note"><small>本ページの情報は変更される可能性があります。最新情報は<a href="https://www.tokyo-park.or.jp/reien/park/index076.html" target="_blank" rel="noopener">東京都公園協会公式サイト</a>でご確認ください。</small></p>
</BaseLayout>
```

注意: 所在地・アクセスは事前に最新情報を確認してから書き込む。不確実な部分は省略可。

- [ ] **Step 2: ビルド確認**

Run:
```bash
npm run build
ls dist/about/index.html
```

Expected: ファイルが存在する。

- [ ] **Step 3: コミット**

Run:
```bash
git add src/pages/about.astro
git commit -m "feat: add about page for Aoyama Cemetery"
```

---

## Task 9: 偉人詳細ページ(動的ルート)作成

**Files:**
- Create: `src/pages/people/[slug].astro`

- [ ] **Step 1: ディレクトリ作成**

Run:
```bash
mkdir -p src/pages/people
```

- [ ] **Step 2: src/pages/people/[slug].astro 作成**

Create `src/pages/people/[slug].astro`:

```astro
---
import { getCollection, type CollectionEntry } from 'astro:content';
import BaseLayout from '../../layouts/BaseLayout.astro';

export async function getStaticPaths() {
  const people = await getCollection('people');
  return people.map((person) => ({
    params: { slug: person.slug },
    props: { person },
  }));
}

interface Props {
  person: CollectionEntry<'people'>;
}

const { person } = Astro.props;
const { Content } = await person.render();

const title = `${person.data.name} - 青山霊園 偉人録`;
const description = person.data.shortDescription;
---

<BaseLayout title={title} description={description} ogImage={person.data.ogImage}>
  <article class="person-detail">
    <h1>{person.data.name}</h1>
    <p class="kana">{person.data.nameKana}({person.data.nameRomaji})</p>

    <table class="meta-table">
      <tbody>
        <tr><th>生没年</th><td>{person.data.birthDate} 〜 {person.data.deathDate}</td></tr>
        <tr><th>時代</th><td>{person.data.era}</td></tr>
        <tr><th>分野</th><td>{person.data.category}</td></tr>
        {person.data.graveSection && <tr><th>墓所区画</th><td>{person.data.graveSection}</td></tr>}
        {person.data.tags && person.data.tags.length > 0 && (
          <tr><th>タグ</th><td>{person.data.tags.join(' / ')}</td></tr>
        )}
      </tbody>
    </table>

    <Content />

    {person.data.references && person.data.references.length > 0 && (
      <section class="references">
        <h2>参考資料</h2>
        <ul>
          {person.data.references.map((ref) => (
            <li><a href={ref.url} target="_blank" rel="noopener">{ref.title}</a></li>
          ))}
        </ul>
      </section>
    )}

    <p><a href="/">← 偉人一覧に戻る</a></p>
  </article>
</BaseLayout>
```

- [ ] **Step 3: ビルドして大久保利通の個別ページが生成されることを確認**

Run:
```bash
npm run build
ls dist/people/okubo-toshimichi/index.html
```

Expected: ファイルが存在する。

- [ ] **Step 4: 生成 HTML に大久保利通の名前と本文が含まれることを確認**

Run:
```bash
grep -c '大久保 利通' dist/people/okubo-toshimichi/index.html
```

Expected: `1` 以上。

- [ ] **Step 5: コミット**

Run:
```bash
git add src/pages/people/[slug].astro
git commit -m "feat: add dynamic person detail page"
```

---

## Task 10: ローカル目視確認(push 前ゲート)

**Files:** なし(ブラウザ目視)

- [ ] **Step 1: プレビューサーバー起動**

Run(バックグラウンド):
```bash
npm run build && npm run preview
```

Expected: `http://localhost:4321` でサーバー起動。

- [ ] **Step 2: ブラウザで以下を目視確認**

ブラウザで以下を開き、内容を確認:

- [ ] `http://localhost:4321/` — タイトル・大久保利通の名前・短文紹介が見える
- [ ] `http://localhost:4321/about/` — 青山霊園の概要が読める
- [ ] `http://localhost:4321/people/okubo-toshimichi/` — 大久保利通の本文が読める、メタテーブルが表示される、参考資料リンクがある
- [ ] iPhone 等スマホ表示で破綻していない(レスポンシブ)
- [ ] ナビゲーション(トップ ⇔ About ⇔ 詳細)が動く
- [ ] ページソースを View し、`<meta property="og:title">` `<meta property="og:description">` が入っている

- [ ] **Step 3: 内容の事実確認**

大久保利通ページの内容を再読し、事実誤認がないか確認(没年月日、役職、業績)。問題があれば `src/content/people/okubo-toshimichi.md` を修正してリビルド。

- [ ] **Step 4: プレビューサーバー停止**

該当 background プロセスを停止。

- [ ] **Step 5: 修正があればコミット**

修正した場合のみ:
```bash
git add -A
git commit -m "fix: correct content based on local preview review"
```

---

## Task 11: robots.txt 作成

**Files:**
- Create: `public/robots.txt`

- [ ] **Step 1: public/robots.txt 作成**

Create `public/robots.txt`:

```
User-agent: *
Allow: /

Sitemap: https://aoyama-cemetery.pages.dev/sitemap-index.xml
```

- [ ] **Step 2: ビルドして dist/robots.txt が含まれることを確認**

Run:
```bash
npm run build
cat dist/robots.txt
```

Expected: 上記内容が表示される。

- [ ] **Step 3: コミット**

Run:
```bash
git add public/robots.txt
git commit -m "feat: add robots.txt with sitemap reference"
```

---

## Task 12: GitHub repo (public) 作成と push

**Files:** なし(リモート操作)

- [ ] **Step 1: gh CLI 認証確認**

Run:
```bash
gh auth status
```

Expected: `Logged in to github.com as yosukeuchida` のような表示。
未認証なら **ユーザーに `gh auth login` の実行を依頼**(対話必要)。

- [ ] **Step 2: GitHub に public repo 作成 + push**

Run(`~/workspace/personal/aoyama-cemetery/` で実行):
```bash
gh repo create yosukeuchida/aoyama-cemetery --public --source=. --push --description "青山霊園に眠る偉人を紹介する静的サイト"
```

Expected: `https://github.com/yosukeuchida/aoyama-cemetery` が作成され、main ブランチが push される。

- [ ] **Step 3: GitHub 上で確認**

Run:
```bash
gh repo view yosukeuchida/aoyama-cemetery --web
```

ブラウザで repo が public で表示されることを確認。

---

## Task 13: Cloudflare Pages プロジェクト作成(ユーザー手動)

**Files:** なし(ブラウザでの Cloudflare ダッシュボード操作)

- [ ] **Step 1: ユーザーに以下の手順を依頼する**

> **手動操作が必要です。Cloudflare dashboard を開いてください:**
>
> 1. https://dash.cloudflare.com/ にログイン
> 2. 左メニュー「Workers & Pages」→「Create」→「Pages」タブ→「Connect to Git」
> 3. GitHub 連携が未設定なら「Connect GitHub」で承認
> 4. リポジトリ一覧から `yosukeuchida/aoyama-cemetery` を選択 →「Begin setup」
> 5. ビルド設定:
>    - Project name: `aoyama-cemetery`(衝突したら別名で再ネゴ)
>    - Production branch: `main`
>    - Framework preset: `Astro`
>    - Build command: `npm run build`
>    - Build output directory: `dist`
> 6. 「Environment variables」を展開し以下を追加:
>    - `NODE_VERSION` = `22`(Astro 6 が >=22.12.0 を要求するため。`20` だと `Node.js v20.20.0 is not supported by Astro!` エラーで失敗)
> 7. 「Save and Deploy」をクリック
> 8. 初回ビルドが走る(1-2 分)
> 9. デプロイ完了後、表示される URL(`https://aoyama-cemetery.pages.dev`)を確認

- [ ] **Step 2: デプロイ完了の確認(ユーザーから完了報告を待つ)**

ユーザーから「デプロイ完了」報告を受け取ったら次のタスクへ進む。

---

## Task 14: 本番動作確認

**Files:** なし(ブラウザ目視)

- [ ] **Step 1: 公開 URL をブラウザで開いて以下を確認**

`https://aoyama-cemetery.pages.dev` を開き、以下を確認:

- [ ] トップに大久保利通の名前・没年月日・短文紹介が表示
- [ ] `/people/okubo-toshimichi/` で本文が読める
- [ ] `/about/` で青山霊園の概要が読める
- [ ] `/sitemap-index.xml` が返る
- [ ] `/robots.txt` が返る
- [ ] スマホでアクセスしても破綻なし
- [ ] URL をスマホで LINE / Twitter 等にペーストし、プレビューにタイトル・説明が出る

- [ ] **Step 2: 問題があれば修正コミット → push → 再デプロイ確認**

問題が見つかった場合:
```bash
# 修正
git add -A
git commit -m "fix: <内容>"
git push
# Cloudflare Pages が自動再ビルド(40-80 秒)
# 本番 URL で再確認
```

---

## Task 15: spec / plan を L2 リポへ移動

**Files:**
- Move: `~/workspace/docs/superpowers/specs/2026-05-21-aoyama-cemetery-site-design.md` → `~/workspace/personal/aoyama-cemetery/docs/superpowers/specs/`
- Move: `~/workspace/docs/superpowers/plans/2026-05-21-aoyama-cemetery-site.md` → `~/workspace/personal/aoyama-cemetery/docs/superpowers/plans/`

L2 確立後、spec/plan は L2 配下で管理する方針(プロジェクト固有ドキュメントの帰属を揃える)。

- [ ] **Step 1: L2 にディレクトリ作成**

Run:
```bash
mkdir -p ~/workspace/personal/aoyama-cemetery/docs/superpowers/{specs,plans}
mkdir -p ~/workspace/personal/aoyama-cemetery/docs/project-logs
```

- [ ] **Step 2: spec / plan をコピー**

Run:
```bash
cp ~/workspace/docs/superpowers/specs/2026-05-21-aoyama-cemetery-site-design.md \
   ~/workspace/personal/aoyama-cemetery/docs/superpowers/specs/

cp ~/workspace/docs/superpowers/plans/2026-05-21-aoyama-cemetery-site.md \
   ~/workspace/personal/aoyama-cemetery/docs/superpowers/plans/
```

- [ ] **Step 3: L2 側でコミット**

Run(`~/workspace/personal/aoyama-cemetery/` で):
```bash
git add docs/
git commit -m "docs: copy spec and plan into L2"
git push
```

- [ ] **Step 4: L0 から spec / plan を削除**

Run(`~/workspace/` で):
```bash
cd ~/workspace
git rm docs/superpowers/specs/2026-05-21-aoyama-cemetery-site-design.md
git rm docs/superpowers/plans/2026-05-21-aoyama-cemetery-site.md
git commit -m "docs: move aoyama-cemetery spec/plan to L2"
```

---

## Task 16: workspace ガバナンス反映(L0 CLAUDE.md / .gitignore / L1)

**Files:**
- Modify: `~/workspace/CLAUDE.md`
- Modify: `~/workspace/.gitignore`
- Modify: `~/workspace/personal/CLAUDE.md`(存在する場合)

`docs/governance/l2-onboarding.md` §2.2 に沿って同日中に反映する。

- [ ] **Step 1: L0 CLAUDE.md の「ディレクトリ構成」章に aoyama-cemetery を追記**

`~/workspace/CLAUDE.md` の `personal/` 配下リストに以下を追加:

```
│   ├── aoyama-cemetery/         # L2: 青山霊園に眠る偉人紹介の静的サイト（Astro + Cloudflare Pages、独立gitリポ、GitHub public）
```

- [ ] **Step 2: L0 CLAUDE.md の「git リポ運用」章に運用メモを追記**

`~/workspace/CLAUDE.md` の「git リポ運用」セクションの末尾(他 L2 の説明と同じ書式)に以下を追加:

```
  - aoyama-cemetery/ は 2026-05-21 新規 L2 化。青山霊園に眠る偉人を紹介する Astro 静的サイト。初期は大久保利通 1 名で本番公開(https://aoyama-cemetery.pages.dev)、以降は Markdown 1 ファイル追加で偉人ページが増える構造。Cloudflare Pages + GitHub public で運用、Claude Code を使ったサイト公開体験が主目的
```

- [ ] **Step 3: L0 .gitignore に aoyama-cemetery を追記**

`~/workspace/.gitignore` に以下を追加:

```
personal/aoyama-cemetery/
```

(他 L2 と同じ書式に揃える。既存の personal/oya-log/ 等の周辺に配置)

- [ ] **Step 4: L1 personal/CLAUDE.md があれば更新**

Run:
```bash
ls ~/workspace/personal/CLAUDE.md
```

存在すれば、L2 一覧があるセクションに aoyama-cemetery を追記する。

- [ ] **Step 5: L0 のコミット**

Run(`~/workspace/` で):
```bash
cd ~/workspace
git add CLAUDE.md .gitignore personal/CLAUDE.md 2>/dev/null
git commit -m "chore(governance): register aoyama-cemetery as new L2"
```

(`personal/CLAUDE.md` が存在しない場合はそのファイルパス指定でエラーになるが、`-A` ではなく明示指定し未存在ならエラーで気づける形にする)

---

## Task 17: L2 内 CLAUDE.md 作成

**Files:**
- Create: `~/workspace/personal/aoyama-cemetery/CLAUDE.md`

- [ ] **Step 1: L2 CLAUDE.md 作成**

Create `~/workspace/personal/aoyama-cemetery/CLAUDE.md`:

```markdown
# aoyama-cemetery — L2 規約

## 上位ルール参照

- L0: `~/workspace/CLAUDE.md`
- L1: `~/workspace/personal/CLAUDE.md`(存在すれば)

## プロジェクト概要

- 目的: 青山霊園に眠る偉人を紹介する静的サイト
- 公開 URL: https://aoyama-cemetery.pages.dev
- スタック: Astro 5.x + TypeScript strict + @astrojs/sitemap
- ホスティング: Cloudflare Pages(GitHub public repo を watch)
- アクセス: 完全 public
- 設計書: `docs/superpowers/specs/2026-05-21-aoyama-cemetery-site-design.md`
- 実装計画: `docs/superpowers/plans/2026-05-21-aoyama-cemetery-site.md`

## 偉人追加手順

1. `src/content/people/<slug>.md` を作成(slug はローマ字ハイフン区切り)
2. frontmatter は `src/content/config.ts` の zod スキーマに準拠
3. 事実確認(没年月日・役職・業績)を `references` の出典で照合
4. `npm run dev` でローカル目視確認
5. `git commit && git push` → Cloudflare Pages が自動デプロイ

## コンテンツ方針

- 出典: Wikipedia(CC BY-SA)等の公開情報をベースに Claude が要約・再構成
- 直接コピペ禁止、必ず再構成 + `references` に出典明記
- 肖像写真は public domain(没後 70 年経過済)のみ使用可
- 事実誤認は本サイトの致命傷なので、ビルド前にユーザー目視確認を必ず通す

## 開発コマンド

```bash
npm run dev      # http://localhost:4321
npm run build    # dist/ 生成
npm run preview  # 本番相当を確認
```
```

- [ ] **Step 2: コミット + push**

Run(`~/workspace/personal/aoyama-cemetery/` で):
```bash
git add CLAUDE.md
git commit -m "docs: add L2 CLAUDE.md"
git push
```

---

## Completion Checklist

実装完了の判定は以下を全て満たすこと(spec §6 受け入れ基準より):

### 形式的妥当性
- [ ] `npm run build` がエラーなく成功
- [ ] `dist/index.html` `dist/about/index.html` `dist/people/okubo-toshimichi/index.html` `dist/sitemap-index.xml` `dist/sitemap-0.xml` `dist/robots.txt` が存在

### 本番動作
- [ ] `https://aoyama-cemetery.pages.dev` がブラウザで開く
- [ ] トップで大久保利通の名前・没年月日・短文紹介が見える
- [ ] `/people/okubo-toshimichi/` で本文が読める
- [ ] `/about/` で青山霊園の概要が読める
- [ ] スマホ表示で破綻していない
- [ ] OGP メタタグが入っており URL シェアでタイトル・説明が出る
- [ ] 大久保利通の解説に事実誤認がない

### ガバナンス反映
- [ ] L0 `~/workspace/CLAUDE.md` に aoyama-cemetery 記載
- [ ] L0 `~/workspace/.gitignore` に `personal/aoyama-cemetery/` 追加
- [ ] L2 `~/workspace/personal/aoyama-cemetery/CLAUDE.md` 作成
- [ ] spec / plan が L2 配下に移動済み
