import os
import pytest
from pathlib import Path
from daily_bluesky_post import config


def test_project_root_points_to_repo():
    # repo root に astro.config.mjs があるはず
    assert (config.PROJECT_ROOT / "astro.config.mjs").is_file()


def test_site_url_constant():
    assert config.SITE_URL == "https://aoyama-cemetery.pages.dev"


def test_posted_log_path():
    assert config.POSTED_LOG == config.PROJECT_ROOT / "logs" / "posted.jsonl"


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
