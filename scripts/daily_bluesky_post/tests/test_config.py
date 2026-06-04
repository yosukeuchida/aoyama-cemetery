import os
import pytest
from pathlib import Path
from daily_bluesky_post import config


def test_project_root_points_to_repo():
    # repo root に astro.config.mjs があるはず
    assert (config.PROJECT_ROOT / "astro.config.mjs").is_file()


def test_site_url_constant():
    assert config.SITE_URL == "https://aoyama-cemetery.pages.dev"


def test_posted_log_paths_split_per_platform():
    from daily_bluesky_post import config
    assert config.POSTED_BLUESKY_LOG.name == "posted_bluesky.jsonl"
    assert config.POSTED_X_LOG.name == "posted_x.jsonl"
    assert config.POSTED_BLUESKY_LOG.parent == config.POSTED_X_LOG.parent


def test_legacy_posted_log_alias_removed():
    # 後方互換 alias を残さない(明示的に platform を選ばせる)
    from daily_bluesky_post import config
    assert not hasattr(config, "POSTED_LOG")


def test_load_secrets_from_env(monkeypatch):
    monkeypatch.setenv("BLUESKY_HANDLE", "test.bsky.social")
    monkeypatch.setenv("BLUESKY_APP_PASSWORD", "abcd-efgh-ijkl-mnop")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/x")
    s = config.load_secrets()
    assert s.bluesky_handle == "test.bsky.social"
    assert s.bluesky_app_password == "abcd-efgh-ijkl-mnop"
    assert s.discord_webhook_url == "https://discord.com/api/webhooks/x"


def test_load_secrets_missing_required(monkeypatch):
    monkeypatch.delenv("BLUESKY_HANDLE", raising=False)
    monkeypatch.delenv("BLUESKY_APP_PASSWORD", raising=False)
    with pytest.raises(config.MissingSecretError):
        config.load_secrets()
