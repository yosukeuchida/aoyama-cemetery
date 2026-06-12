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

## デプロイ前提(Cloudflare Pages)

- 環境変数: `NODE_VERSION=22` 必須(Astro 6 は >=22.12.0 要求、デフォルト Node 20 ではビルド失敗)
- Build command: `npm run build`
- Build output: `dist`
- Framework preset: Astro

## 偉人追加方法

`src/content/people/<slug>.md` を 1 ファイル追加するだけで `/people/<slug>/` が生成されます。frontmatter スキーマは `src/content.config.ts` 参照。

## 地図 coords の取得手順(Google Maps 航空写真)

新規偉人の墓所座標を取得する標準手順:

1. Google Maps で「青山霊園」を開き航空写真モードに切替
2. `graveSection`(例 `1種イ8号8側`)を区画案内図と照合して位置を絞り込む
3. 該当位置を右クリック → 緯度経度をコピー
4. frontmatter に `coords:\n  lat: 35.66xx\n  lng: 139.71xx`(範囲外は zod が build を弾く)

### 新規偉人で地図 POI 確認の流れ

1. `npm run dev` で偉人ページを開く、または `https://www.google.com/maps?q={偉人名}の墓+青山霊園` を直接検索
2. 正しい墓所 POI に着地 → OK
3. POI が出ない / 違う場所 → 順に試す:
   - `mapQuery: "{偉人名}の墓"`(「青山霊園」を外す、例: 北里柴三郎・黒田清隆・加藤高明で有効)
   - 別の表記(`{偉人名}先生の墓` 等)を `mapQuery` に
   - Google Maps 航空写真で正確な lat/lng → `coords: { lat, lng }`
   - どれも駄目なら `hideMap: true`(例: 御木本幸吉)

### POI 自動判定スクリプト

`scripts/verify-map-pois.py` で全偉人の地図 POI 着地を一括検証(`exit code 1` で CI 組込可)。判定基準:

- ✅ **OK**: spotlit(固有 POI 着地)
- ⚠️ **CATEGORICAL**: 複数候補のみ → `mapQuery` で別表記を試す
- ⚠️ **GENERIC_POI**: 青山霊園マスター POI (35.6656277, 139.7220659) → `hideMap: true` 推奨
- **SKIP**: `hideMap` または `coords` 設定済

frontmatter スキーマの判断軸(4 通りの地図制御)・立山墓地と本園の番地重複警告は `CLAUDE.md`「地図機能」参照。
