# 青山霊園 Bluesky 自動投稿

毎朝 8:05 JST に launchd が発火し、本日が命日の偉人・該当日 events を Bluesky に投稿する。

## セットアップ

1. シークレット配置:
   ```
   mkdir -p ~/.config/aoyama-cemetery && chmod 700 ~/.config/aoyama-cemetery
   cat > ~/.config/aoyama-cemetery/bluesky.env <<'EOF'
   BLUESKY_HANDLE=aoyama-cemetery.bsky.social
   BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
   EOF
   chmod 600 ~/.config/aoyama-cemetery/bluesky.env
   ```
2. dry-run で動作確認:
   ```
   scripts/daily_bluesky_post/run.sh --dry-run --today 2026-05-14
   ```
3. launchd 登録: `infra/launchd/jp.aoyama-cemetery.daily-post.plist` を `~/Library/LaunchAgents/` にコピーして `launchctl load`

## テスト

```
arch -arm64 scripts/daily_bluesky_post/.venv/bin/pytest scripts/daily_bluesky_post/tests/
```

仕様: `docs/superpowers/specs/2026-06-03-bluesky-auto-post-design.md`
計画: `docs/superpowers/plans/2026-06-03-bluesky-auto-post.md`
