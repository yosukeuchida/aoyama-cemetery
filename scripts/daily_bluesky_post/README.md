# 青山霊園 SNS 自動投稿(Bluesky + X 並走)

毎朝 8:05 JST に launchd が発火し、本日が命日の偉人・該当日 events を Bluesky と X(旧 Twitter)に **独立並走** で投稿する。ディレクトリ名は歴史的経緯で `daily_bluesky_post` のままだが multi-platform 化済(2026-06-04 〜)。

## セットアップ

### 1. シークレット配置

```
mkdir -p ~/.config/aoyama-cemetery && chmod 700 ~/.config/aoyama-cemetery
```

#### bluesky.env(必須)
```
cat > ~/.config/aoyama-cemetery/bluesky.env <<'EOF'
BLUESKY_HANDLE=aoyama-cemetery.bsky.social
BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
EOF
chmod 600 ~/.config/aoyama-cemetery/bluesky.env
```

#### discord.env(任意、失敗通知用)
```
cat > ~/.config/aoyama-cemetery/discord.env <<'EOF'
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
EOF
chmod 600 ~/.config/aoyama-cemetery/discord.env
```

#### x.env(X 並走時のみ)
```
cat > ~/.config/aoyama-cemetery/x.env <<'EOF'
X_API_KEY=<コンシューマーキー>
X_API_SECRET=<コンシューマーキーシークレット>
X_ACCESS_TOKEN=<アクセストークン>
X_ACCESS_SECRET=<アクセストークンシークレット>
X_ENABLED=0
EOF
chmod 600 ~/.config/aoyama-cemetery/x.env
```

4 つのキーは X Developer Portal → アプリ → Keys and tokens の **OAuth 1.0 キー** セクションから取得(2025 移行後の用語: コンシューマーキー / コンシューマーキーシークレット / アクセストークン / アクセストークンシークレット = それぞれ env の 4 つに対応)。OAuth 2.0 のクライアント ID / シークレットは使わない。

`X_ENABLED=0` の状態で X 用 subagent の dry-run チューニングをしてから、納得したら `1` に書き換える(launchd 経由でも読まれる)。

### 2. dry-run 動作確認

```
scripts/daily_bluesky_post/run.sh --dry-run --today 2026-05-14
```

両 platform の生成文が標準出力に流れる(`--- BLUESKY DRY: ... ---` / `--- X DRY: ... ---`)。X の dry-run を見るには `X_ENABLED=1`(env or x.env 経由)が必要。

### 3. launchd 登録

`infra/launchd/jp.aoyama-cemetery.daily-post.plist` を `~/Library/LaunchAgents/` にコピーして `launchctl load`。plist は Bluesky / X 共通(orchestrator が両 platform 担当)。

## X API 料金の注意

X は **完全 Pay-Per-Use(2025 移行)、Free tier は実質廃止**。新規アカウントはクレジット先払い($5 最小)必須。

### 単価(2026-06 時点、docs.x.com で随時要確認)

- POST /2/tweets(URL なし)= **$0.015 / request**
- POST /2/tweets(**URL 含み**)= **$0.200 / request** ← 13 倍ジャンプ
- POST /1.1/media/upload(metadata)≒ $0.005 / request

本案件は **本文に URL を含めない方針** で運用(月 60-90 投稿 × $0.20 ≒ ¥2,700/月を回避、URL なしなら $0.02/件 = ¥3/件で年 ¥2,200-3,200)。サイト誘導は X profile の bio + website 欄で代替。post-writer-x.md の項目 5a と fact-checker-x.md の 5a で URL 混入を厳格禁止。

支出上限は Developer Console → 請求書作成 → クレジット → 支出上限を管理 で **月 $5-10 推奨**(暴走時の保険)。自動チャージは OFF 維持。

## 運用

- **本物実行(launchd 経由 = 自動)**: `scripts/daily_bluesky_post/run.sh`
- **本物実行(手動再投稿)**: `PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/python -m daily_bluesky_post.orchestrator --today YYYY-MM-DD`
- **dry-run**: 上記に `--dry-run` を追加
- **既投稿の重複防止**: `logs/posted_bluesky.jsonl` / `logs/posted_x.jsonl` の `(date, slug)` で idempotent
- **失敗時**: Discord 通知が飛ぶ(設定してあれば)。`gen_fail` は subagent ブレの可能性高、同じコマンドで再実行すると復活することが多い

## テスト

```
PYTHONPATH=scripts arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/
```

(2026-06-04 時点で 91 件 pass)

## 仕様 / 計画

- spec(Bluesky): `docs/superpowers/specs/2026-06-03-bluesky-auto-post-design.md`
- spec(X 並走): `docs/superpowers/specs/2026-06-03-x-auto-post-design.md`
- plan(X 並走): `docs/superpowers/plans/2026-06-04-x-auto-post.md`
