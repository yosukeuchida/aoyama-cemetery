# メタデータレビュー PoC で検出された真の発見 — 引き継ぎ書

**作成日**: 2026-05-28
**完了日**: 2026-05-30(全 6 件決着済)
**起点**: workspace/personal/cockpit/scripts/poc_metadata_check.py(別 L2 で実施した Anthropic SDK 学習 PoC)の派生
**目的**: PoC で検出された明確な事実誤認・矛盾 6 件を aoyama-cemetery L2 で修正する

---

## 決着サマリー(2026-05-30 追記)

| # | slug | 結果 | commit / 判断 |
|---|---|---|---|
| 1 | arimura-jizaemon | ✅ 修正 | `ca2b952` 水戸藩浪士 tag 削除 |
| 2 | nakamura-utaemon-vi | ✅ 修正 | `ee4635d` 父・五代目との師事関係を補足。PoC の「初代吉右衛門に薫陶=誤り」指摘自体は誤判定で、Wikipedia 確認の結果史実として正しいことを確認(1940 年父没後に吉右衛門劇団へ)。文脈不足を補う形で書き直し |
| 3 | katayama-tokuma | ✅ 修正(部分) | `eb9f4d6` category を学者→文化人に変更。tags の「奇兵隊」は本人が実際に 15 歳で奇兵隊入隊・戊辰従軍しているため残置(PoC の削除指示は誤判定) |
| 4 | kurusu-saburo | ✅ 修正 | `3700df7` 真珠湾攻撃 tag 削除、日米開戦に置換 |
| 5 | ogata-taketora | ✅ 修正 | `029b6f6` 「自民党結成を主導」を「自由党総裁として保守合同に関与」に修正 |
| 6 | oku-yasukata | ⏸ 保留(=結論として修正せず) | 「元帥陸軍大将」は歴史的正式名称(元帥府条例)。PoC の「正しくは陸軍元帥」指摘自体が誤りのため変更なしで決着 |

**学び**: PoC(Claude Haiku batch チェック)の指摘は 6 件中 2 件(nakamura / katayama 奇兵隊 / oku の称号)で誤判定だった。LLM の事実認識は出典確認なしで rubber-stamp してはいけない、というメタデータレビュー運用の教訓。修正前の Wikipedia 等の出典確認は必須。

---

---

## 背景

別 PoC(Anthropic SDK の学習・体験を目的とした batch メタデータレビュー)で、aoyama-cemetery 全 136 偉人の frontmatter を Claude Haiku に投げて 3 軸でチェックした:

1. tags の表記揺れ・冗長(明確な誤りのみ)
2. 不足タグ提案
3. shortDescription と category/tags の整合性

結果分布: good 41 / fair 94 / needs_review 1
コスト: $0.33 USD(49.57 円)、所要 10 分、caching 72.2% 引き

PoC 全体は close。CSV を `tmp/metadata_check_results.csv` に保存(gitignore 対象)。
ここから **「明確に修正すべき」と判断された 6 件**を本 L2 で対処する。

---

## 修正対象 6 件

### 1. arimura-jizaemon: tags に誤った「水戸藩浪士」混入

**ファイル**: `src/content/people/arimura-jizaemon.md`

**現状**:
```yaml
tags:
  - 薩摩藩
  - 桜田門外の変
  - 井伊直弼
  - 幕末志士
  - 水戸藩浪士          # ← 削除
```

**修正**: tags から `水戸藩浪士` を削除。

**理由**:
- shortDescription: 「薩摩藩士」明記
- jobTitle: 「薩摩藩士」
- birthPlace: 「薩摩国鹿児島」
- tags にも `薩摩藩` あり
- 同じファイル内で「薩摩藩士 vs 水戸藩浪士」が矛盾

**背景**: 桜田門外の変(1860 年 3 月 24 日)の実行犯は水戸藩脱藩浪士 17 名 + 薩摩藩士 1 名(=有村次左衛門)。frontmatter 作成時に「桜田門外の変 = 水戸藩浪士グループの仕事」というイメージで誤って付与した可能性。

---

### 2. nakamura-utaemon-vi: shortDescription の事実誤認(needs_review)

**ファイル**: `src/content/people/nakamura-utaemon-vi.md`

**現状の問題箇所**:
```yaml
shortDescription: 初代中村吉右衛門に薫陶... (以下略)
```

**修正**: shortDescription 冒頭を書き直す。出典確認のうえ、正しい師事関係に置換する。

**理由**:
- 六代目歌右衛門は **市川宗家系統(女形)**
- 初代中村吉右衛門は **立役(中村播磨屋系統)**
- 流派が異なるため師事関係は不自然
- 父・五代目歌右衛門が実質的な師であった可能性が高い(Wikipedia で要確認)

**注意**: 修正前に Wikipedia 等で正しい師事関係を確認してから書き直す。誤った修正で更に誤りを増やさない。

---

### 3. katayama-tokuma: 二重の誤り(tag + category)

**ファイル**: `src/content/people/katayama-tokuma.md`

**現状**:
```yaml
category: 学者                    # ← 文化人に変更
tags:
  - 奇兵隊                        # ← 削除
  - (...)
```

**修正**:
- tags から `奇兵隊` を削除
- category を「学者」→「文化人」に変更
- (任意で missing_tag 提案を追加検討: 「コンドル門下」「博物館建築」)

**理由**:
- 片山東熊は建築家(赤坂離宮・京都国立博物館などを設計)
- `奇兵隊` は長州藩の軍事組織で、建築家とは無関係(別人物との混同の可能性)
- category=学者 は「研究主体の人」を想定。建築家は設計・施工の実務家であり、aoyama-cemetery の慣例(辰野金吾等)では文化人として扱われている

---

### 4. kurusu-saburo: 不適切な真珠湾攻撃 tag

**ファイル**: `src/content/people/kurusu-saburo.md`

**現状**:
```yaml
tags:
  - (...)
  - 真珠湾攻撃                    # ← 削除
```

**修正**:
- tags から `真珠湾攻撃` を削除
- 代わりに `日米交渉` `ワシントン特派大使` `日独伊三国同盟` 等の正確な tag に置換(missing_tags 提案より)

**理由**:
- 来栖三郎は **攻撃直前まで野村吉三郎大使と一緒にワシントンで日米交渉中**
- 真珠湾攻撃(1941-12-08)の **実行者でも関係者でもない**
- shortDescription も「開戦直前の交渉」と述べているため矛盾

**注意**: 同様に「真珠湾攻撃」tag を持つ他の偉人がいるか grep し、それらが本当に攻撃の実行者・指揮者・関係者かも合わせて見直す(波及的な品質改善)。

---

### 5. ogata-taketora: shortDescription の歴史的事実誤認

**ファイル**: `src/content/people/ogata-taketora.md`

**現状の問題箇所**:
```yaml
shortDescription: 自由民主党結成を主導した... (以下略)
```

**修正**: 「自由民主党結成を主導」を事実に即した表現に書き直す。

**理由**:
- 1955 年 11 月の自民党結成時、緒方は **前年(1954 年 12 月)に吉田内閣退陣で公職退任済**
- 結成翌年(1956 年 1 月)に急逝
- 主導者ではなく、保守合同に関与した有力政治家の 1 人だが、結成そのものを主導したわけではない

**書き直し案**(出典確認のうえ):
- 「吉田内閣の副総理として戦後保守政治を支え、保守合同に関与した自由党総裁。自民党結成の前年に退陣、結成翌年に急逝した。」

---

### 6. oku-yasukata: 称号 tag の表記誤り(要検討事項あり)

**ファイル**: `src/content/people/oku-yasukata.md`

**現状**:
```yaml
tags:
  - 元帥陸軍大将                  # ← 検討
```

**Claude の指摘**: 「正しくは陸軍元帥」

**注意・要検討**:
- 既存 tag 一覧では `元帥陸軍大将`(4 件)が複数偉人で使われている慣用表記
- 厳密な正式称号は「元帥陸軍大将」(陸軍大将の中で元帥府に列せられた者の称号、明治31 年元帥府条例による)
- つまり **Claude の指摘自体が誤り** の可能性が高い(歴史的正式名称が「元帥陸軍大将」)
- → 本件は **修正しない** 判断が妥当だが、aoyama-cemetery 既存運用の称号 tag を一覧確認して最終判断

**確認方法**:
```bash
grep -rn "元帥陸軍大将\|陸軍元帥" src/content/people/
```

---

## 修正フロー(標準)

各偉人について:

```bash
cd /Users/uchidayousuke/workspace/personal/aoyama-cemetery

# 1. 該当ファイル編集
$EDITOR src/content/people/<slug>.md

# 2. ローカル build 検証(zod schema 通過確認)
npm run build

# 3. dev サーバーで目視確認
npm run dev
# → http://localhost:4321/people/<slug>

# 4. commit & push
git add src/content/people/<slug>.md
git commit -m "fix(<slug>): <修正内容>"
git push origin main

# Cloudflare Pages が自動 deploy(数分)
```

## まとめての修正案(個別 commit vs 一括 commit)

選択肢:
- **個別 commit**(6 件 → 6 commits): 各修正の意図が明確、後から差分追跡しやすい
- **一括 commit**(1 件にまとめる): メタデータ品質改善 PoC の結果を一回でまとめる、git log が見やすい

推奨は **個別 commit**(aoyama-cemetery の既存 commit 慣例に合わせる)。commit message 例:

```
fix(arimura-jizaemon): 誤った「水戸藩浪士」tag を削除(薩摩藩士)
fix(katayama-tokuma): category を学者→文化人に変更、誤った奇兵隊 tag を削除
fix(kurusu-saburo): 真珠湾攻撃 tag を削除(攻撃時は交渉中)
fix(nakamura-utaemon-vi): shortDescription の師事関係を修正
fix(ogata-taketora): shortDescription の自民党結成主導記述を修正
```

(6 番目の oku-yasukata は要検討で保留)

---

## 関連リソース

| リソース | 場所 |
|---|---|
| PoC スクリプト | `~/workspace/personal/cockpit/scripts/poc_metadata_check.py` |
| PoC 結果 CSV | `~/workspace/personal/aoyama-cemetery/tmp/metadata_check_results.csv`(gitignore 対象) |
| 関連 Obsidian メモ | (未作成。学習総括は別途検討) |
| aoyama-cemetery 偉人追加・修正ルール | `~/workspace/personal/aoyama-cemetery/CLAUDE.md` |

---

## 完了チェックリスト

- [x] arimura-jizaemon: 水戸藩浪士 tag 削除(`ca2b952`)
- [x] nakamura-utaemon-vi: shortDescription 師事関係修正(`ee4635d`、2026-05-30)
- [x] katayama-tokuma: category を文化人に変更(`eb9f4d6`)。奇兵隊 tag は実関与のため残置
- [x] kurusu-saburo: 真珠湾攻撃 tag 削除 + 日米開戦に置換(`3700df7`)
- [x] ogata-taketora: shortDescription 自民党結成記述修正(`029b6f6`)
- [x] oku-yasukata: 称号 tag 統一性検討 → 「元帥陸軍大将」は歴史的正式名称につき保留(=変更なしで決着)
- [x] 全件で npm run build 通過確認
- [x] 個別 commit & push 完了

---

## 検討事項(将来の派生作業)

1. **「真珠湾攻撃」tag を持つ他偉人の妥当性確認**: kurusu-saburo の修正と同時に、他の同 tag 保有者(山本五十六等?)が真の関係者か grep + 検証
2. **称号 tag の統一運用ルール策定**: 「元帥陸軍大将」「元帥海軍大将」「陸軍大将」「海軍大将」等の称号 tag を CLAUDE.md に明文化(命名 convention)
3. **missing_tags 提案の採用判断**: PoC CSV の missing_tags 列に 100 件以上の提案がある。一律採用ではなく、各偉人ごとに本当に必要なものだけ採用する(全件 spreadsheet レビュー)
4. **本 PoC スクリプトの定期実行化**: 新規偉人追加時の品質チェックとして launchd で月次自動実行 + Discord 通知も検討可能(ただし運用コストとのバランス)
