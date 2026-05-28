# aoyama-cemetery admin

偉人の coords 設定 + 墓参り写真アップロード用のローカル管理画面。

## 起動

```bash
./admin/run.sh
```

初回は arm64 venv を自動作成 + 依存インストール(数分)。
ブラウザで http://localhost:8501 を開く。

## 操作

- ダッシュボード: 136 名の coords 状態 + 写真枚数を一覧
- 個人詳細: 偉人を選んで coords タブ / 写真タブで編集
- 編集結果は working tree を直接更新するので、`git diff` で確認してから commit/push

## テスト

```bash
arch -arm64 admin/.venv/bin/pytest admin/tests/
```

## 設計

`docs/superpowers/specs/2026-05-28-grave-admin-design.md`
