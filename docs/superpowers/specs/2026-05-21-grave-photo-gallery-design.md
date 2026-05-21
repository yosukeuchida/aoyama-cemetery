# 墓参り写真ギャラリー機能 設計書

作成日: 2026-05-21

## 背景・目的

偉人ページに「実際の墓所の写真」を載せて、Wikipedia 由来の伝記情報だけでは得られない「現地感」をサイトの差別化要素にする。墓参りの記録としても機能する。

当初は訪問者が誰でも投稿できるライトな投稿機能を検討したが、認証無しの public サイトでスパム・不適切画像・モデレーション運用が重くなるリスクを踏まえ、**管理者(陽介さん)のみが git commit 経由で追加する**スタイルに方針転換した。

## コンセプト

「フォルダに画像を置けば自動でギャラリー表示される」ファイル名規則ベースのゼロ設定ギャラリー。frontmatter 編集も schema 変更も不要。

## ファイル配置規則

```
src/assets/grave-photos/<slug>/YYYY-MM-DD-<caption>.<ext>
```

- `<slug>` = Content Collection の id(例 `okubo-toshimichi`)
- `YYYY-MM-DD` = 撮影日(表示用にパース)
- `<caption>` = 任意のキャプション(日本語・ハイフン区切り、省略可)
- `<ext>` = `.jpg` / `.jpeg` / `.png` / `.webp`

例:
- `src/assets/grave-photos/okubo-toshimichi/2026-05-21-雨上がりの墓所.jpg`
- `src/assets/grave-photos/okubo-toshimichi/2025-11-03.jpg`(キャプション省略)

## ファイル名パース仕様

正規表現: `^(\d{4}-\d{2}-\d{2})(?:-(.+))?\.(jpg|jpeg|png|webp)$`

- マッチしないファイルは無視 + build ログに warning(`IMG_4321.jpg` 放置事故を検知)
- caption に追加のハイフンが含まれても OK(2 個目以降は caption の一部)
- 日付フォーマット崩れ(`2026-5-21` 等)は warning して無視

## 読み込み機構

`src/utils/grave-photos.ts` を新設:
- `import.meta.glob('/src/assets/grave-photos/*/*.{jpg,jpeg,png,webp}', { eager: true })` で全画像を build 時に取得
- パスから slug を抽出 → slug ごとに groupBy
- ファイル名から `{ date, caption, image }` をパース
- `getGravePhotos(slug)` を export(撮影日 desc でソート)

## 表示

偉人ページ(`src/pages/people/[slug].astro`)の本文と地図の間に「墓参り写真」セクション。
- 0 枚 → セクション非表示(既存ページに差分なし)
- 1 枚以上 → サムネ grid + キャプション + 撮影日
- Astro の `<Image />`(`astro:assets`)で WebP 変換 + lazy load + 自動 srcset
- サムネクリック → 同タブで拡大画像(`<a href={img.src}>`、lightbox は YAGNI)

## 画像最適化(運用ルール)

コミット前に手動で長辺 1600px / quality 85% にリサイズ。
- macOS Preview の「サイズを調整」or `sips -Z 1600 *.jpg` 一発
- 自動化スクリプトは 3 回続けて面倒に感じたら作る(YAGNI)
- CLAUDE.md に運用ルールを追記

## スコープ外(YAGNI)

- ユーザー投稿フォーム(本セッションで方針転換、明示的に除外)
- lightbox / モーダルギャラリー
- EXIF 撮影日自動抽出
- 投稿者クレジット
- 画像リサイズ自動化スクリプト

## 影響するファイル

### 新規
- `src/utils/grave-photos.ts` — 画像ロード + パース + slug ごと groupBy
- `src/components/GravePhotoGallery.astro` — gallery セクションのコンポーネント
- `src/assets/grave-photos/.gitkeep` — 空ディレクトリ確保

### 修正
- `src/pages/people/[slug].astro` — 本文と地図の間に `<GravePhotoGallery slug={...} />` を追加
- `CLAUDE.md` — 「偉人追加手順」に項目 7「墓参り写真がある場合」を追加

## 検証

- 偉人ページ `/people/okubo-toshimichi` を `npm run dev` で開きギャラリー表示確認
- 写真 0 件の他偉人ページに余白・セクションが出ないこと確認
- `npm run build` がエラーなく完了し `dist/` に最適化済み画像が出ること
- ビルドログに不正ファイル名 warning が出ること
- CLAUDE.md の手順に従って他人(将来の自分)が再現できる粒度であること
