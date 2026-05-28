# 偉人 coords + 墓写真管理 admin 設計

- 作成日: 2026-05-28
- ステータス: 設計案(ユーザーレビュー前)
- スコープ: 既存 aoyama-cemetery リポ内に Streamlit ベースのローカル admin UI を新設する

## 1. 背景と目的

aoyama-cemetery は Astro 6 製の静的サイト(136 名、本番 `https://aoyama-cemetery.pages.dev`)。コンテンツは `src/content/people/<slug>.md` の frontmatter + 本文で管理されており、新規偉人追加は `/add-person` スラッシュコマンドで完結する。一方、運用フェーズで頻度高く発生する以下 2 つの作業は claude code を起動しての md 編集に依存しており、面倒さがボトルネックになっている:

1. coords(緯度経度)の取得 — 現状 119/136 名取得済、17 名未取得。今後追加される偉人にも継続的に必要
2. 墓参り写真のアップロード — `scripts/add-grave-photo.sh` は整備されているが、CLI を叩く + caption を考える + 複数人分を順に振り分ける作業のトリガーが重い

特に「今どの偉人が coords 未取得か」「誰の墓写真がゼロ枚か」という進捗が一覧で見えない点が、作業の不連続性を生んでいる。

本 admin はこの 2 機能 + 進捗ダッシュボードを提供する PC ローカル UI。

## 2. スコープ

### In scope

- ローカル PC (macOS Apple Silicon) で `streamlit run` で起動
- 偉人ごとの進捗ダッシュボード(coords 状態 + 写真枚数)
- 個人詳細画面で coords を Leaflet 地図クリックで設定
- 個人詳細画面で写真をアップロード / 削除
- frontmatter の round-trip 書き換え(コメント・順序保持)
- 既存 `scripts/add-grave-photo.sh` への非対話フラグ追加

### Out of scope

- 認証(localhost only)
- 新規偉人追加 (`/add-person` で完結)
- routes / works / events / relatedPeople の編集
- iPhone からのアクセス
- git commit / push の自動化(working tree を更新するのみ、commit は手動)
- デプロイ(ローカル限定)

## 3. アーキテクチャ

```
ブラウザ (localhost:8501)
    │ HTTP
Streamlit app
    ├ admin/Dashboard.py       ← 進捗一覧 (entry point)
    ├ admin/pages/Person_Edit.py ← 個人詳細
    └ admin/lib/
        ├ content_io.py        ← frontmatter 読み書き (ruamel.yaml)
        ├ photo_ops.py         ← add-grave-photo.sh 呼び出し
        └ git_ops.py           ← git log 取得 (read-only)
    │ ファイル I/O
既存リポジトリ
    ├ src/content/people/*.md (136 件)
    ├ src/assets/grave-photos/<slug>/*.jpg
    └ scripts/add-grave-photo.sh (--date / --caption フラグ追加)
```

- **配置先**: aoyama-cemetery リポ内 `admin/` ディレクトリ
- **ビルド除外**: `astro.config.mjs` の `srcDir` は `src/` のみなので何もしなくても build から除外される
- **起動**: `arch -arm64 .venv/bin/streamlit run admin/Dashboard.py --server.address localhost`
  - CLAUDE.md L0 ルール: arm64 venv で起動ラッパー `admin/run.sh` を用意
- **git 連携**: admin は working tree を更新するだけ。コミット前に必ず `git diff` でレビュー可能

## 4. 画面構成

### 4.1 ダッシュボード (`Dashboard.py`)

上部サマリ:

- coords 未取得: N 名
- 墓写真ゼロ: N 名
- 未 commit のファイル: N 件(任意の警告表示)

テーブル:

| 列 | 内容 | ソート | フィルタ |
|---|---|---|---|
| slug | `okubo-toshimichi` | ✓ | ✓(部分一致) |
| 名前 | `大久保 利通` | ✓ | |
| coords | `✅` / `❌` / `(hideMap)` | ✓ | ✓(状態) |
| graveSection | `1種イ8号8側` | | |
| 写真枚数 | `3` / `0`(0 は赤太字) | ✓ | ✓(0 only) |
| 最終更新 | git log の last commit 日時 | ✓ | |

行クリックで `st.session_state["selected_slug"]` をセットし `st.switch_page("pages/Person_Edit.py")` で遷移。

### 4.2 個人詳細 (`pages/Person_Edit.py`)

ヘッダー: `大久保 利通 (1830-1878) / 1種イ8号8側`

タブ 2 枚 + 一覧へ戻るボタン。

#### 4.2.1 coords タブ

- 現在値表示: `lat=35.6678  lng=139.7234`(未設定なら「未設定」)
- クリアボタン(`coords` キー削除)
- Leaflet 航空写真(`streamlit-folium`、青山霊園範囲 `lat 35.66-35.68 / lng 139.71-139.73`)
  - タイル: Esri World Imagery(API key 不要)
  - 既存の他偉人のピンを灰色で表示(位置確認の参考用)
  - 編集中の偉人の現在値を赤ピンで表示
  - クリック → 候補座標を画面下に表示「lat=35.66xx, lng=139.72xx [採用する]」
- 保存ボタン → バリデーション → frontmatter 書き戻し
- Google Maps で確認ボタン → `https://www.google.com/maps?q={lat},{lng}` を新タブで開く

#### 4.2.2 写真タブ

既存写真リスト:

- サムネ(max 200px) + ファイル名 + 撮影日 + caption
- 各行に削除ボタン(確認 dialog あり)

新規追加フォーム:

- ファイル選択(複数可、jpg/jpeg/png/heic)
- 撮影日: date picker、デフォルト今日
- caption: テキスト(空欄なら「墓所」連番自動)
- アップロードボタン → `add-grave-photo.sh` を非対話モードで subprocess 実行

### 4.3 Streamlit 制約への対応

- `@st.cache_resource` は **module-level の関数のみ**(CLAUDE.md L1 アンチパターン回避)
- ページ遷移は `st.switch_page()` で固定 URL
- 写真サムネは `src/assets/grave-photos/...` を `st.image()` に直接渡す

## 5. データ書き込み戦略

### 5.1 coords

ライブラリ: `ruamel.yaml`(round-trip mode、コメント・順序・引用符を保持)

手順:

1. `src/content/people/<slug>.md` を読む
2. `---` フェンスで frontmatter と本文を分離
3. ruamel.yaml で frontmatter を `CommentedMap` としてパース
4. `coords` キーを **`graveSection` の直後**(既存 .md の規約)に挿入
5. `coords:\n  lat: 35.66xxxxxx\n  lng: 139.72xxxxxx` 形式で 6 桁精度
6. frontmatter + 本文を再結合
7. 一時ファイル `<slug>.md.tmp` に書いて `os.replace()` で atomic rename

衝突対策:

- 既に `coords` がある場合は確認 dialog
- `hideMap: true` 設定済なら `ValueError`(意味矛盾)
- 範囲外座標(`lat 35.66-35.68 / lng 139.71-139.73`、zod に同期)は保存前に弾く

### 5.2 写真

方針: 既存 `scripts/add-grave-photo.sh` を subprocess 呼び出し。リサイズ・HEIC 変換ロジックは bash 側の単一真実点として温存。

bash スクリプトに非対話フラグを追加:

```bash
# 従来通り対話モード
./scripts/add-grave-photo.sh okubo-toshimichi photo.jpg

# 非対話モード(Streamlit から)
./scripts/add-grave-photo.sh okubo-toshimichi photo.jpg \
  --date 2026-05-28 \
  --caption "墓所正面"
```

改修方針:

- `--date YYYY-MM-DD` と `--caption "..."` が両方与えられたら `read` を skip
- どちらか欠けたら従来通り対話プロンプト(後方互換)
- 既存の `~/Downloads/*.jpg` を直接投げる使い方は壊さない

Streamlit 側:

1. アップロードファイルを `tempfile.NamedTemporaryFile` に書き出す
2. `subprocess.run([script, slug, tmp_path, "--date", ..., "--caption", ...], check=True, capture_output=True)` で実行(`--date` と `--caption` の両方が与えられたことが非対話の合図)
3. 成功時 → 配置パスを表示
4. 失敗時 → stderr を `st.error` の expander で全文表示

写真削除:

- 削除ボタン → 確認 dialog → `os.remove(target_path)` → `st.rerun()`

### 5.3 git 連携(read-only)

- ダッシュボードの「最終更新」列は `git log -1 --format=%ci -- <path>` を `@st.cache_data(ttl=60)` で取得
- git commit / push は admin から実行しない

## 6. エラー処理・バリデーション

### 6.1 入力バリデーション

| 対象 | チェック | 失敗時の挙動 |
|---|---|---|
| coords lat | 35.66 ≤ lat ≤ 35.68 | `st.error` + 保存 abort |
| coords lng | 139.71 ≤ lng ≤ 139.73 | 同上 |
| 写真拡張子 | jpg / jpeg / png / heic | `st.error` + skip |
| 写真サイズ | ≤ 50MB | `st.error` + skip |
| caption | スラッシュ・コロン・改行を含まない | サニタイズして警告 |
| 撮影日 | YYYY-MM-DD 形式 | date picker で構造的に防止 |
| slug | `src/content/people/<slug>.md` が実在 | dashboard 由来なので構造的に防止 |

### 6.2 ファイル I/O エラー

| エラー | 検知 | 対応 |
|---|---|---|
| frontmatter YAML パース失敗 | ruamel.yaml 例外 | `st.error` で行番号 + 元エラー表示、保存しない |
| `coords` 挿入位置不明 | ロード時にチェック | warning + frontmatter 末尾に追加(fallback) |
| ディスク書き込み失敗 | `OSError` | `st.error` + 元ファイル無傷を保証 |
| `os.replace` 失敗 | `OSError` | 同上 |
| `add-grave-photo.sh` non-zero exit | `subprocess.CalledProcessError` | stderr 全文を `st.error` expander で表示 |

### 6.3 起動時ヘルスチェック

`Dashboard.py` 冒頭で以下を検証、NG なら `st.stop()`:

1. `src/content/people/` が存在し ≥ 1 件の .md がある
2. `scripts/add-grave-photo.sh` が実行可能(`os.access(path, os.X_OK)`)
3. プロジェクトルートが正しい(`astro.config.mjs` の存在)

### 6.4 同時起動

単一ユーザー想定で排他制御なし。`os.replace` の atomic 性で破損は防げる。

### 6.5 操作ログ

- `admin/admin.log` に JSONL で追記: `{ts, op, slug, before, after, file_path}`
- ローテーションは実装しない(増え続けても運用上問題なし)
- `.gitignore` に追加

## 7. テスト戦略

PC 内部ツールなので E2E や UI スナップショットはやらない。「ファイル破損」と「データ不整合」を防ぐ純関数中心の単体テスト + 起動 smoke test に絞る。

### 7.1 pytest 対象

**`lib/content_io.py`** (frontmatter 読み書き):

- 既存 .md の round-trip(読んで書き戻し、frontmatter YAML パース結果が等価かつ本文 byte が一致)
- `coords` 新規挿入で `graveSection` 直後に入る
- `coords` 既存値の更新で順序保持
- `coords` 削除で frontmatter 構造保持
- 範囲外座標で `ValueError`
- `hideMap: true` 偉人に coords 追加で `ValueError`
- フィクスチャ: `tests/fixtures/sample_person_*.md`(3 パターン)

**`lib/photo_ops.py`** (subprocess ラッパー):

- 正常引数で `add-grave-photo.sh` を呼び、配置パスが返る
- caption に `/` を含むと `ValueError`
- スクリプト non-zero exit で `RuntimeError`(stderr 含む)
- bash モックなし、tmp ディレクトリで本物を実行(scripts 改修の後方互換も同時検証)

**`lib/git_ops.py`**:

- `git log` 出力のパース(subprocess はモック)

### 7.2 やらないもの

- Streamlit ページ自体のテスト
- Leaflet 地図クリックの自動化
- スクリーンショット比較
- bash の `bats-core`(Python 側 photo_ops テストで間接カバー)

### 7.3 手動受け入れチェックリスト

リリース前に手で 1 回:

1. `arch -arm64 .venv/bin/streamlit run admin/Dashboard.py` で起動
2. coords 未取得 17 名がフィルタで出る
3. 1 名選択 → 地図クリック → 保存 → `git diff` で意図通り
4. 別 1 名に写真 1 枚アップロード → `src/assets/grave-photos/<slug>/` に配置確認
5. 既存写真の削除 → ファイル消滅確認
6. `npm run build` が通る(zod 通過 = データ整合確認)
7. `git diff` で意図通り、`git checkout .` で全戻し可能

## 8. ディレクトリ構成

```
aoyama-cemetery/
├ admin/                           ← NEW
│   ├ Dashboard.py
│   ├ pages/
│   │   └ Person_Edit.py
│   ├ lib/
│   │   ├ __init__.py
│   │   ├ content_io.py
│   │   ├ photo_ops.py
│   │   └ git_ops.py
│   ├ tests/
│   │   ├ fixtures/
│   │   │   ├ sample_person_with_coords.md
│   │   │   ├ sample_person_no_coords.md
│   │   │   └ sample_person_hidemap.md
│   │   ├ test_content_io.py
│   │   ├ test_photo_ops.py
│   │   └ test_git_ops.py
│   ├ requirements.txt             ← streamlit, streamlit-folium, ruamel.yaml, pytest
│   ├ run.sh                       ← arch -arm64 .venv/bin/streamlit run ...
│   └ README.md
├ scripts/
│   └ add-grave-photo.sh           ← MODIFIED (--date/--caption フラグ追加)
├ .gitignore                       ← MODIFIED (admin/admin.log, admin/.venv 追加)
└ (既存ファイル群)
```

## 9. CLAUDE.md / L0-L2 ルール準拠

- L0 「Streamlit + arch -arm64」: `run.sh` で `arch -arm64 .venv/bin/streamlit` を強制
- L1 「Streamlit `@st.cache_resource` は module-level 関数のみ」: 設計時点で関数構造を限定
- L1 「外部 API は spec 前に 1 リクエスト」: 外部 API 使用なし(Leaflet タイルは Esri 公開タイル、API key 不要)
- L2 「frontmatter コロン引用」: ruamel.yaml round-trip で既存スタイルを保持
- L2 「bold 禁止」: 本文は触らない(frontmatter のみ編集)

## 10. リスク

- **bash 改修の後方互換**: `--date` `--caption` の引数追加時に既存対話モードを壊さないこと → tests で対話モードも本物実行で検証(`expect` でなく `<<<` ヒアストリングで stdin 流し込み)
- **ruamel.yaml の round-trip 精度**: 既存 119 件すべてで round-trip テストして byte 一致を確認 → CI 化しないが手動で 1 回回す
- **streamlit-folium のクリック取得安定性**: 地図クリックで lat/lng を session_state に渡す挙動は streamlit-folium の `st_folium()` の戻り値依存。動かなければ Google Maps URL ペーストへフォールバック(セクション提案時の代替案)
- **同時起動**: 単一ユーザー前提だが、誤って 2 タブ開いた場合のファイル衝突は `os.replace` で破損は防げる(片方の編集が上書きで消える程度)

## 11. 完了条件

- 7 章の手動受け入れチェックリスト 7 項目すべて通過
- pytest 全パス
- `git diff` でレビュー → `git commit && git push` → 本番 build 通過
