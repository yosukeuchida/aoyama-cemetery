# launchd 設定: jp.aoyama-cemetery.daily-post

毎朝 8:05 JST に Bluesky 自動投稿を発火する LaunchAgent。

## 前提

- `scripts/daily_bluesky_post/.venv/` が構築済(初回 `run.sh` で自動構築)
- `~/.config/aoyama-cemetery/bluesky.env` に App Password が配置済(`chmod 600`)
- `claude` CLI が `/opt/homebrew/bin` などに install 済(Max plan セッションが有効)

## 初回登録

```bash
cp infra/launchd/jp.aoyama-cemetery.daily-post.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/jp.aoyama-cemetery.daily-post.plist
launchctl list | grep aoyama
```

## 動作確認(即時発火)

```bash
launchctl start jp.aoyama-cemetery.daily-post
tail -f logs/launchd.out.log logs/launchd.err.log
```

## 停止 / 解除

```bash
launchctl unload ~/Library/LaunchAgents/jp.aoyama-cemetery.daily-post.plist
rm ~/Library/LaunchAgents/jp.aoyama-cemetery.daily-post.plist
```

## ログ

- `logs/launchd.out.log` — stdout(orchestrator の logger.info / dry-run プレビュー)
- `logs/launchd.err.log` — stderr(claude_runner / bluesky_client の error print 出力)

両ログとも append のみ、大きくなったら手動 truncate or logrotate を別途検討。

## 注意

- `StartCalendarInterval` は Mac がスリープしていた場合、起動後に発火する(catch-up デフォルト動作)
- 二重投稿は `logs/posted.jsonl` の `(date, slug)` チェックで防止
- 失敗時は Discord webhook 経由でユーザー通知(`~/.config/aoyama-cemetery/discord.env` を配置済の場合)
- cockpit ダッシュボードで本ジョブの稼働を一覧表示(`Label` 命名規約 `jp.aoyama-cemetery.*` で拾われる)

## 仕様 / 計画

- spec: `docs/superpowers/specs/2026-06-03-bluesky-auto-post-design.md`
- plan: `docs/superpowers/plans/2026-06-03-bluesky-auto-post.md` Task 13
