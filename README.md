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
