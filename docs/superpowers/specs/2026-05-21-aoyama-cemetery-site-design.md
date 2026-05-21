# aoyama-cemetery サイト — 設計書

- 作成日: 2026-05-21
- 目的: Claude Code を使ってシンプルな Web サイトを作成し、世界に公開する体験を完走する
- テーマ: 青山霊園に眠る偉人を紹介する静的サイト
- 初期リリーススコープ: 偉人 1 名(大久保利通)を掲載した状態で本番公開まで到達

---

## 1. 全体像

| 項目 | 内容 |
|---|---|
| プロジェクト名 | aoyama-cemetery |
| 配置 | `~/workspace/personal/aoyama-cemetery/`(新規 L2) |
| スタック | Astro(静的サイト生成、Markdown + Content Collections) |
| ホスティング | Cloudflare Pages |
| GitHub repo | `github.com/yosukeuchida/aoyama-cemetery`(public) |
| 公開 URL | `https://aoyama-cemetery.pages.dev` |
| アクセス制限 | なし(完全 public) |
| 連携方式 | GitHub push → Cloudflare Pages 自動ビルド・自動デプロイ |

**設計判断の根拠**:
- Astro: Markdown 1 ファイル = 偉人 1 ページ、で将来 20+ 名追加してもコード変更不要。ビルド成果物は純粋な静的 HTML/CSS
- Cloudflare Pages: 既存 award-flights-deploy と同パターン流用可能、無料帯域無制限、将来「身内限定公開」に切り替えたい場合に Cloudflare Access(無料)で対応可
- public repo: 偉人紹介は完全公開情報、PII を含まない

## 2. ガバナンス整合

- 新規 L2 追加につき `docs/governance/l2-onboarding.md` §2.2 に沿って同日中に以下を更新:
  - L0 `~/workspace/CLAUDE.md` の「ディレクトリ構成」「git リポ運用」章
  - L0 `~/workspace/.gitignore`(L2 ディレクトリ除外)
  - L1 `~/workspace/personal/CLAUDE.md`(存在する場合)
- ホスティング層の制限(Cloudflare Pages 無料帯域・ビルド時間)は本サイト規模では当たらないため特別な事前対策不要
- 写真・PII を扱わないため、public 化前の git 履歴監査は不要(初回から public で開始)

## 3. ファイル構成

```
aoyama-cemetery/
├── .gitignore
├── README.md
├── CLAUDE.md                    # L2 規約(L0/L1 参照)
├── astro.config.mjs             # site URL + @astrojs/sitemap
├── package.json
├── tsconfig.json
├── public/
│   ├── favicon.svg
│   └── robots.txt
├── src/
│   ├── pages/
│   │   ├── index.astro          # トップ(偉人一覧)
│   │   ├── about.astro          # 青山霊園の概要・アクセス
│   │   └── people/
│   │       └── [slug].astro     # 動的ルート(.md 1 件 = 1 ページ)
│   ├── layouts/
│   │   └── BaseLayout.astro     # 共通ヘッダ・フッタ・OGP メタ
│   ├── content/
│   │   ├── config.ts            # Content Collection スキーマ(zod)
│   │   └── people/
│   │       └── okubo-toshimichi.md   # 大久保利通(初期 1 名)
│   └── styles/
│       └── global.css
└── docs/
    ├── project-logs/
    └── superpowers/
        └── specs/
            └── 2026-05-21-aoyama-cemetery-site-design.md  # 本書(L2 確立後に移動)
```

**ポイント**:
- `src/content/people/<slug>.md` を 1 つ追加するだけで `/people/<slug>/` ページが増える
- `BaseLayout.astro` で OGP・canonical・共通 nav を一元管理
- ビルド成果物は `dist/`(`.gitignore` で除外)

## 4. データモデル

### Content Collection スキーマ(`src/content/config.ts`)

zod で frontmatter を厳密にバリデーションする。スキーマ違反はビルドエラーとして検出する。

```ts
import { defineCollection, z } from 'astro:content';

const people = defineCollection({
  type: 'content',
  schema: z.object({
    name: z.string(),                                              // 必須: 表示名
    nameKana: z.string(),                                          // 必須: ふりがな
    nameRomaji: z.string(),                                        // 必須: 英語表記
    birthDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),            // 必須: YYYY-MM-DD
    deathDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),            // 必須: YYYY-MM-DD
    era: z.enum(['江戸', '明治', '大正', '昭和']),                  // 必須
    category: z.enum(['政治家', '文化人', '軍人', '実業家', '学者', 'その他']),  // 必須
    graveSection: z.string().optional(),                           // 任意: 墓所区画
    shortDescription: z.string().min(20).max(100),                 // 必須: 一覧表示用
    tags: z.array(z.string()).optional(),
    references: z.array(z.object({
      title: z.string(),
      url: z.string().url(),
    })).optional(),
    ogImage: z.string().optional(),
  }),
});

export const collections = { people };
```

### 偉人 .md の例

```yaml
---
name: 大久保 利通
nameKana: おおくぼ としみち
nameRomaji: Okubo Toshimichi
birthDate: "1830-09-26"
deathDate: "1878-05-14"
era: 明治
category: 政治家
graveSection: "(実装時に確認)"
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
...

## 業績
...

## 青山霊園での墓所
...
```

### コンテンツ出典方針

- Wikipedia(CC BY-SA)等の公開情報をベースに Claude が要約・再構成
- 引用元は `references` に必ず明記
- 肖像写真は public domain(没後 70 年経過済)があれば使用、なければ初期版は文字のみ

## 5. デプロイフロー

### 初回セットアップ(1 回だけ)

1. Astro プロジェクト雛形作成
   ```bash
   npm create astro@latest aoyama-cemetery -- --template minimal --typescript strict
   cd aoyama-cemetery
   npm install @astrojs/sitemap
   ```
2. `astro.config.mjs` に `site: 'https://aoyama-cemetery.pages.dev'` と sitemap integration を追加
3. ローカル確認
   ```bash
   npm run dev      # http://localhost:4321
   npm run build    # dist/ 生成
   npm run preview  # 本番相当を確認
   ```
4. GitHub repo (public) 作成・push
   ```bash
   gh repo create yosukeuchida/aoyama-cemetery --public --source=. --push
   ```
5. **(ブラウザ作業 = ユーザー手動)** Cloudflare dashboard → Pages → "Connect to Git"
   - Framework preset: Astro
   - Build command: `npm run build`
   - Build output dir: `dist`
   - 環境変数: `NODE_VERSION=22`(必須。Astro 6 は Node >=22.12.0 が要件)
6. `https://aoyama-cemetery.pages.dev` で公開確認

### 継続運用フロー(偉人追加時)

1. `src/content/people/<slug>.md` を新規作成
2. `npm run dev` でローカル目視確認
3. `git commit` → `git push`
4. Cloudflare Pages が push 検出 → 自動ビルド(40-80 秒)
5. 本番 URL で反映確認

### 手動介入が必要な工程(Claude Code 代行不可)

- Cloudflare ダッシュボードでの GitHub 連携承認(初回のみ)
- `gh auth login`(未認証の場合のみ)

## 6. 受け入れ基準(初回リリース完了の判定)

### 形式的妥当性(自動チェック)

- [ ] `npm run build` がエラーなく成功
- [ ] Content Collection の zod スキーマでバリデーション通過
- [ ] 生成された `dist/index.html` / `dist/about/index.html` / `dist/people/okubo-toshimichi/index.html` / `dist/sitemap-index.xml` / `dist/sitemap-0.xml` が存在

### ユーザー目線の精度チェック(L0 CLAUDE.md「MVP は『動く』だけでなく『正しい』も含める」準拠)

- [ ] `https://aoyama-cemetery.pages.dev` がブラウザで開く
- [ ] トップで大久保利通の名前・没年月日・短文紹介が表示される
- [ ] `/people/okubo-toshimichi/` で本文が読める
- [ ] `/about/` で青山霊園の概要が読める
- [ ] スマホ表示で破綻していない(陽介さんの iPhone で実物確認)
- [ ] OGP メタタグが入っており、URL シェア時にタイトル・説明(画像は ogImage 指定時のみ)が表示される
- [ ] 大久保利通の解説内容に**事実誤認がない**(没年月日・役職・主要業績を目で確認)

### UI 確認の補助輪(L0 CLAUDE.md より)

- push 前: `npm run preview` でローカル本番相当を**ブラウザで目視確認**
- デプロイ後: Cloudflare Pages 本番 URL を**ブラウザで再度目視確認**

## 7. 将来拡張(任意・スコープ外)

- 偉人 2-10 名追加(志賀直哉、北里柴三郎、斎藤茂吉、忠犬ハチ公、等)
- 一覧ページにフィルタ(時代別・ジャンル別)
- 墓所マップ(青山霊園内の区画図、Leaflet 等)
- OGP 画像の偉人ごと自動生成(Satori 等)
- カスタムドメイン取得
- Google Search Console 登録(検索流入観測)

### 将来拡張時に維持したい設計原則

- 偉人追加は `.md` 1 ファイルで完結(コード変更不要)
- 共通レイアウト・OGP 生成は `BaseLayout.astro` に一元化
- スキーマ変更時は zod 定義を更新 → ビルドエラーで既存 `.md` の追従漏れを検出

## 8. スコープ外(やらない)

- コメント機能・お問い合わせフォーム(動的機能不要)
- 多言語化(日本語のみ)
- 管理画面(`.md` 直接編集)
- 認証(public のため)
- 写真の大量掲載(著作権チェックが負担。初回は文字のみ、public domain の肖像のみ追加可)

## 9. リスクと対策

| リスク | 対策 |
|---|---|
| 偉人解説の事実誤認 | references を必ず明記、複数ソース照合、ユーザー目視確認を受け入れ基準に含める |
| Node バージョン不一致でビルド失敗 | `NODE_VERSION=22` を環境変数に明示(Astro 6 は >=22.12.0 必須、Cloudflare デフォルトは古い) |
| Cloudflare Pages プロジェクト名衝突 | `aoyama-cemetery` 先取り可否を初回作成時に確認、ダメなら `aoyama-bochi` 等の代替案で再ネゴ |
| Wikipedia コンテンツの著作権(CC BY-SA) | 直接コピペせず Claude が再構成、出典明記 |
| 将来「身内だけに見せたい」変更 | Cloudflare Access(無料)で allowlist 化に切り替え可能 |
