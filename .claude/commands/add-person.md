---
description: 青山霊園偉人サイトに新規偉人 1 名を追加する(7 工程)
argument-hint: <偉人名(日本語フルネーム)>
---

# 新規偉人追加: $ARGUMENTS

以下の 7 工程を順に実施せよ。各工程の判断は CLAUDE.md(L0/L1/L2)と本コマンド本文のルールに従う。

---

## 全工程に共通する大原則(CLAUDE.md より抜粋・厳守)

- **埋葬確認ファースト**: 青山霊園への埋葬を一次資料で確認。優先順位 (1) ユーザー提供 `~/Desktop/青山霊園.pptx` → (2) Wikipedia 本人記事の冒頭 infobox「墓所: 青山霊園」明記 → (3) 青山霊園 Wikipedia 著名人リスト。確認できない場合は工程 0 で打ち切ってユーザーに報告
- **bold 禁止**: 本文に `**bold**` 記法を使わない。LLM 生成時の強調衝動を抑える
- **直接関与ファースト**: events の `personSlugs` には「その事件に直接関与した青山霊園埋葬者」のみ。同時代人・分野近接者は入れない
- **PD 判定**: 没後 70 年経過(`今年 - 没年 ≥ 71`)なら肖像取得可、未経過なら portrait なしで作成
- **frontmatter コロン引用**: 値に `:` を含む文字列はダブルクオートで囲む(YAML エラー回避)
- **era 最大 2 値**: 主要活動期 1-2 個。生没年の元号を全部入れない
- **shortDescription**: 20-100 文字以内、概要 1 文

---

## 工程 0: 埋葬確認

1. ユーザーが提供している青山霊園パンフレット情報・既存ファイル群を確認
2. Wikipedia 本人記事の infobox で「墓所: 青山霊園」を確認
3. 確認できない場合は **ここで停止しユーザーに報告**(以降の工程は実施しない)
4. 墓所番地(例: `1種イ31号1番甲`)を記録

## 工程 1: 一次資料調査

Wikipedia 本人記事を WebFetch で取得し、以下を抽出する:

- 生年月日・没年月日(西暦 YYYY-MM-DD 形式)
- 出生地・死去地
- 主要業績(肩書・在任期間・代表作)
- 受賞・栄典(文化勲章・男爵叙爵等)
- 同時代の重要関係者(既存サイトに登録済かは工程 3 で照合)
- 親族関係(配偶者・子・親 — 既存サイト人物との接続候補)
- Wikimedia Commons の肖像画像ファイル名(infobox の `Image=` フィールド)
- 出典 URL

**抽出失敗時の対応**: Wikipedia 記事に情報が不足する場合は、関連人物の Wikipedia 記事を追加 WebFetch して補完する。推測で書かない。

## 工程 2: PD 判定 + 肖像取得

1. 没年から `(今年) - (没年) ≥ 71` を判定
   - PD 経過 → 工程 2-A
   - PD 未経過 → portrait なしで md 作成、工程 3 へスキップ
2. **工程 2-A: PD 経過済の場合**
   - `scripts/download-portraits.py` の `PAIRS` リスト末尾に `("<slug>", "<Wikimedia ファイル名>"),` を追加
   - スクリプト本体は **触らない**(レート制限対策の実装は完成済)
   - `python3 scripts/download-portraits.py` を実行
   - `src/assets/portraits/<slug>.jpg` が生成されたことを確認

## 工程 3: md ファイル作成

`src/content/people/<slug>.md` を作成。slug はローマ字ハイフン区切り(例: `fujishima-takeji`)。

### frontmatter 必須項目

```yaml
---
name: <漢字フルネーム>
nameKana: <ふりがな>
nameRomaji: <Romaji>
birthDate: "YYYY-MM-DD"
deathDate: "YYYY-MM-DD"
era: [明治, 昭和]  # 最大 2 個、主要活動期
category: 政治家 | 文化人 | 軍人 | 実業家 | 学者 | その他
graveSection: <墓所番地>
shortDescription: <20-100 文字の概要>
tags: [..., ...]
birthPlace: "<出生地(現在地名併記)>"
deathPlace: "<死去地>"
jobTitle: <肩書>
knowsAbout: [専門 1, 専門 2]
nationality: JP
portrait: ../../assets/portraits/<slug>.jpg  # PD 未経過なら省略
portraitCaption: <名前>の肖像
portraitCredit: Wikimedia Commons / Public Domain
references:
  - title: Wikipedia「<名前>」
    url: <URL>
relatedPeople:
  - slug: <既存 slug>
    relation: <60 文字以内の関係説明>
---
```

### era 判定ルール

- 維新志士・幕末活動者は **江戸末期の活動も含める**(例: 大久保利通 → `[江戸, 明治]`)
- お雇い外国人は **来日後の活動を基準**
- 主要活動期が明確に 1 つなら 1 値、2 つにまたがれば 2 値

### 本文構成(5 章型ストーリー)

CLAUDE.md `project_person_page_story_structure.md` に従う:

1. **オープニング**: その人物が成し遂げた最大の業績で打ち出す(2-3 段落)
2. **来歴・前史**: 生い立ち〜出世の道(2-3 段落)
3. **代表的業績・伝説的シーン**: 中心となる事績を具体的場面として描く(3-5 段落)
4. **晩年・最期**: 退任・死去の情景(1-2 段落)
5. **青山霊園に眠る**: 墓所情報 + 同区画・同霊園の関係者への内部リンク(`[名前](/people/<slug>/)` 形式)

### 文体ルール

- bold 禁止(`**...**` 記法使用禁止)
- 西暦と元号は両方明記(例: 明治 35 年(1902 年))
- 既存人物への言及は **必ず内部リンク**(`[名前](/people/<slug>/)`)
- 推測・誇張表現を避け、Wikipedia で確認できる事実のみを書く

## 工程 4: 既存偉人との relatedPeople 相互リンク

工程 3 で `relatedPeople` に登録した既存 slug について、**双方向の関係を成立させる**:

1. 新規偉人 md → 既存偉人 (工程 3 で実施済)
2. **既存偉人 md → 新規偉人** (本工程で追加)

手順:

1. 各既存ファイルを Read(Edit 前に必須)
2. 既存ファイルの `relatedPeople:` セクション末尾(`---` の直前)に新規偉人エントリを追加
3. relation は新規偉人視点の鏡像(例: 新規 → 既存「父」なら、既存 → 新規「息子」)

## 工程 5: events 連携

新規偉人が「直接関与した事件」が `src/content/events/` に存在する場合、該当 event の `personSlugs:` に新規 slug を追加する。

**「直接関与」の判定基準(CLAUDE.md より)**:

記載してよい役割:
- 主導者・首謀者
- 指揮官・司令官
- 当事者・参加者
- 条約・法律の調印者・責任者
- 殉死者など事件と一体化した行為者

記載してはいけない:
- 同時代に生きていただけの人物
- 分野・領域が近いだけの人物
- 事件の影響を後に受けた人物

該当 event がない、あるいは関与が間接的なら **何もしない**。新規 event 化は本コマンドのスコープ外(ユーザーに別途相談)。

## 工程 6: works 収集(1-3 件目安)

新規偉人を題材にした作品を 1-3 件 `src/content/works/` に追加する。

候補:
- 代表作(著者本人の主要作品 → `type: 代表作`)
- 評伝・研究本(他者による → `type: 評伝` または `研究本`)
- 小説化・ドラマ化(他者による → `type: 小説` / `ドラマ` / `NHK大河` / `映画`)

既存 works の `personSlugs:` にも新規 slug を追加すべきものがないか確認(例: 司馬遼太郎『坂の上の雲』に新規偉人が登場するなら追加)。

works frontmatter:

```yaml
---
title: <作品名>
type: 小説 | 映画 | 漫画 | ドラマ | NHK大河 | 研究本 | 評伝 | 代表作 | その他
creator: "<作者(コロン含む場合は引用符必須)>"
year: <西暦>
publisher: "<出版社(コロン含む場合は引用符必須)>"
personSlugs:
  - <slug>
url: <Wikipedia URL あれば>
---

<2-4 文の作品紹介>
```

**作品が見つからない・極めて専門的なもののみの場合は 0 件でも可**。低価値な works を無理に作らない。

## 工程 7: 地図 + ビルド検証

### 7-A: 地図設定

`graveSection` の番地から座標が推測できる場合(同区画に既存人物がいる等)、frontmatter に `coords` を追加。

```yaml
coords:
  lat: 35.66xxxx
  lng: 139.72xxxx
```

座標が不明な場合は **何も書かない**(デフォルトの `?q=<name>の墓 青山霊園` 検索方式が自動適用される)。

POI が出ない著名人(過去事例: 北里柴三郎・黒田清隆・加藤高明)では `mapQuery: "<名前>の墓"` で「青山霊園」を外すと spotlit になる場合がある。

### 7-B: ビルド検証

```bash
npm run build
```

zod 検証エラー(era 超過・コロン未引用等)を解消するまで修正。ビルドが通ったら本コマンドの工程完了。

### 7-C: POI 検証(任意)

複数名を連続追加した最後の 1 回でまとめて実施するのが効率的:

```bash
python3 scripts/verify-map-pois.py
```

`CATEGORICAL` / `GENERIC_POI` が出た偉人は `mapQuery` 上書き or `coords` 追加 or `hideMap: true` で対応。

---

## 工程完了の報告

工程 1-7 が完了したら、以下をユーザーに報告:

1. 新規偉人 slug + 墓所番地
2. PD 判定結果(肖像取得 / なし)
3. 相互リンクを追加した既存偉人の数
4. events への `personSlugs` 追加(該当があれば)
5. works 追加件数
6. ビルド結果(ページ数の変化)
7. **散歩ルートへの追加可否はユーザーが別途判断するため、本コマンドではルート編集を行わない**(代わりに「候補ルート」のみ提案)

---

## やってはいけないこと

- 推測で md を書く(事実が取れない項目は省略する)
- 散歩ルート(`src/content/routes/`)の編集 — **ユーザーの別判断スコープ**
- 既存 event 本文の改変(`personSlugs` 追加は OK、本文書き換えは NG)
- bold 記法の使用
- 「直接関与ファースト」ルールに違反する events への紐付け
- portrait 取得時の `Special:FilePath` 直接アクセス(レート制限で ban される。必ず `scripts/download-portraits.py` 経由)
- commit — 本コマンドはファイル変更とビルド検証までで停止。コミットはユーザーの明示的指示を待つ
