# Multi-Era Classification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `era` を単一文字列から配列(1〜2 個)に変え、全 29 名を主活動期ベースで再分類し、フロントエンドを OR フィルタ + 中黒バッジ表示に切り替える。

**Architecture:** content schema を `z.array(...).min(1).max(2)` に変更、29 .md の `era` を spec の再分類リスト通りに一括更新、`src/pages/index.astro` と `src/pages/people/[slug].astro` を配列対応にする。フィルタは `data-eras="明治,大正"` を `split(',').includes(currentEra)` で OR 判定。

**Tech Stack:** Astro 6 / TypeScript strict / zod schema / no test framework / `npm run build` で検証

**参考:** spec `docs/superpowers/specs/2026-05-21-multi-era-classification-design.md`

---

## File Structure

- Modify: `src/content.config.ts`(スキーマ era を array に)
- Modify: `src/content/people/*.md` 全 29 ファイル(era を配列形式へ + 13 名は値変更)
- Modify: `src/pages/index.astro`(data-eras、presentEras、applyFilter、badge)
- Modify: `src/pages/people/[slug].astro`(時代欄を `.join('・')` に)

---

## Task 1: Schema を array に変更 + 全 29 ファイルの era を再分類

スキーマ単独変更だと全 .md が validation 失敗してビルドが落ちる。スキーマと .md を**同一コミット**で更新する必要がある。

**Files:**
- Modify: `src/content.config.ts`
- Modify: `src/content/people/*.md`(全 29)

- [ ] **Step 1: `src/content.config.ts` の era を配列スキーマに変更**

```ts
// before
era: z.enum(['江戸', '明治', '大正', '昭和']),

// after
era: z.array(z.enum(['江戸', '明治', '大正', '昭和'])).min(1).max(2),
```

- [ ] **Step 2: 16 名の「変更なし」を配列形式に書き換え(値は同一、フォーマットだけ array に)**

以下の各ファイルで `era: 明治` を `era: [明治]` に書き換え(YAML inline array)。値は変えない。

```
src/content/people/okubo-toshimichi.md       era: [明治]
src/content/people/mori-arinori.md           era: [明治]
src/content/people/ueki-emori.md             era: [明治]
src/content/people/nishi-amane.md            era: [明治]
src/content/people/kuroda-kiyotaka.md        era: [明治]
src/content/people/nakae-chomin.md           era: [明治]
src/content/people/sano-tsunetami.md         era: [明治]
src/content/people/ozaki-koyo.md             era: [明治]
src/content/people/hirose-takeo.md           era: [明治]
src/content/people/kunikida-doppo.md         era: [明治]
src/content/people/otori-keisuke.md          era: [明治]
src/content/people/komura-jutaro.md          era: [明治]
src/content/people/nogi-maresuke.md          era: [明治]
src/content/people/kato-tomosaburo.md        era: [大正]
src/content/people/kato-takaaki.md           era: [大正]
src/content/people/matsuoka-yosuke.md        era: [昭和]
```

- [ ] **Step 3: 13 名の「変更あり」を新値で書き換え**

```
src/content/people/tanaka-hisashige.md       era: [江戸, 明治]      旧: 明治
src/content/people/matsukata-masayoshi.md    era: [明治]            旧: 大正
src/content/people/goto-shinpei.md           era: [明治, 大正]      旧: 大正
src/content/people/akiyama-yoshifuru.md      era: [明治]            旧: 昭和
src/content/people/kitasato-shibasaburo.md   era: [明治]            旧: 昭和
src/content/people/mikimoto-kokichi.md       era: [明治, 大正]      旧: 昭和
src/content/people/yamamoto-gonbee.md        era: [明治, 大正]      旧: 昭和
src/content/people/hamaguchi-osachi.md       era: [大正, 昭和]      旧: 昭和
src/content/people/inoue-junnosuke.md        era: [大正, 昭和]      旧: 昭和
src/content/people/inukai-tsuyoshi.md        era: [大正, 昭和]      旧: 昭和
src/content/people/makino-nobuaki.md         era: [大正, 昭和]      旧: 昭和
src/content/people/saito-mokichi.md          era: [大正, 昭和]      旧: 昭和
src/content/people/shiga-naoya.md            era: [大正, 昭和]      旧: 昭和
```

- [ ] **Step 4: 検証**

```bash
cd /Users/uchidayousuke/workspace/personal/aoyama-cemetery
npm run build
```

ビルド成功 + 31 ページ生成を確認。zod validation でいずれかの .md が失敗すると build error になる。各 era 値の出現を数えて spec と一致するか確認:

```bash
# 江戸: 1, 明治: 20, 大正: 11, 昭和: 7 を期待
for era in 江戸 明治 大正 昭和; do
  printf "%s: " "$era"
  grep -lE "^era:.*$era" src/content/people/*.md | wc -l | tr -d ' '
  echo
done
```

- [ ] **Step 5: commit**

```bash
git add src/content.config.ts src/content/people/
git commit -m "$(cat <<'EOF'
refactor: migrate era field to array (1-2 values) and reclassify 13 figures

Based on primary-activity-era rule defined in
docs/superpowers/specs/2026-05-21-multi-era-classification-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: トップページの配列対応(data-eras + applyFilter + presentEras + badge)

`src/pages/index.astro` を 4 箇所更新。

**Files:**
- Modify: `src/pages/index.astro`

- [ ] **Step 1: presentEras を array.includes 判定に変更**

```ts
// before
const presentEras = ERA_ORDER.filter((era) => people.some((p) => p.data.era === era));

// after
const presentEras = ERA_ORDER.filter((era) => people.some((p) => p.data.era.includes(era)));
```

- [ ] **Step 2: article の data 属性を data-eras(複数値カンマ区切り)に変更**

```astro
<!-- before -->
<article class="person-card" data-era={person.data.era} data-category={person.data.category}>

<!-- after -->
<article class="person-card" data-eras={person.data.era.join(',')} data-category={person.data.category}>
```

- [ ] **Step 3: バッジ表示を `.join('・')` に変更**

```astro
<!-- before -->
<span class="era-badge">{person.data.era}</span>

<!-- after -->
<span class="era-badge">{person.data.era.join('・')}</span>
```

- [ ] **Step 4: applyFilter の matchEra 判定を split + includes に変更**

```ts
// before
const matchEra = currentEra === 'all' || article.dataset.era === currentEra;

// after
const matchEra =
  currentEra === 'all' ||
  (article.dataset.eras ?? '').split(',').includes(currentEra);
```

- [ ] **Step 5: 検証**

```bash
npm run build

# data-eras 出現確認
grep -o 'data-eras="[^"]*"' dist/index.html | sort | uniq -c | head -20

# badge に中黒が含まれる人物が存在することを確認(13 - 田中久重で江戸・明治を含む 8 名が複数)
grep -o '・' dist/index.html | wc -l
```

- [ ] **Step 6: commit**

```bash
git add src/pages/index.astro
git commit -m "$(cat <<'EOF'
feat: top page filter handles multi-era figures with OR match

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: 個別ページの時代欄を `.join('・')` に変更

**Files:**
- Modify: `src/pages/people/[slug].astro`

- [ ] **Step 1: 32 行目の era 表示を変更**

```astro
<!-- before -->
<tr><th>時代</th><td>{person.data.era}</td></tr>

<!-- after -->
<tr><th>時代</th><td>{person.data.era.join('・')}</td></tr>
```

- [ ] **Step 2: 検証**

```bash
npm run build

# 個別ページ(例: 御木本幸吉)で「明治・大正」と表示されているか
grep -A1 '時代' dist/people/mikimoto-kokichi/index.html | head -5
# 期待: <td>明治・大正</td>
```

- [ ] **Step 3: commit**

```bash
git add src/pages/people/\[slug\].astro
git commit -m "$(cat <<'EOF'
feat: individual page shows multiple eras with middle dot

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: 受け入れチェック

**Files:**
- 触らない(検証のみ)

- [ ] **Step 1: production build**

```bash
npm run build
```

Expected: 成功、警告なし

- [ ] **Step 2: dist 内の era 集計**

```bash
# 各元号がいくつの person ページに含まれるか
for era in 江戸 明治 大正 昭和; do
  printf "%s: " "$era"
  grep -l "data-eras=\"[^\"]*$era[^\"]*\"" dist/index.html >/dev/null && \
    grep -o "data-eras=\"[^\"]*$era[^\"]*\"" dist/index.html | wc -l | tr -d ' '
  echo
done
```

Expected: 江戸=1、明治=20、大正=11、昭和=7

- [ ] **Step 3: 個別ページの中黒バッジ確認**

```bash
for slug in mikimoto-kokichi goto-shinpei yamamoto-gonbee hamaguchi-osachi inoue-junnosuke inukai-tsuyoshi makino-nobuaki saito-mokichi shiga-naoya tanaka-hisashige; do
  printf "%s: " "$slug"
  grep '時代' dist/people/$slug/index.html | head -1
done
```

Expected: 各人の era が中黒(・)区切りで表示される

- [ ] **Step 4: preview で手動確認**

```bash
npm run preview
```

ブラウザで http://localhost:4321 を開き、以下を確認:

1. 江戸チップが初登場(田中久重 1 名)
2. 「明治」チップで 20 名表示、その中に松方正義・北里柴三郎・秋山好古・後藤新平・御木本幸吉・山本権兵衛が含まれる
3. 「大正」チップで 11 名、「昭和」チップで 7 名
4. 「明治」+「政治家」で明治期の政治家のみ表示(後藤新平・山本権兵衛など複数 era 持ちも該当)
5. カードバッジに「明治・大正」のような中黒表記
6. 個別ページ(例 mikimoto-kokichi)で「時代: 明治・大正」表示
7. URL hash `#era=明治&cat=政治家` 復元動作
8. JS 無効でも全件表示

全項目クリアでマージ。

---

## Self-Review

- **Spec coverage**:
  - § データモデル(スキーマ array 化) → Task 1
  - § 判定ルール明文化 → spec 内で明示済み、コード変更不要
  - § 29 名再分類リスト → Task 1 Steps 2-3
  - § UI 変更(data-eras / applyFilter / presentEras / badge) → Task 2
  - § 個別ページ表示 → Task 3
  - § noscript fallback → 既存実装で対応(変更不要)
  - § 受け入れ基準 → Task 4
- **Placeholder scan**: TBD/TODO なし ✓
- **Type consistency**: `era` は `string[]` 型として全タスクで一貫 ✓
