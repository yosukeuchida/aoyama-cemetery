"""環境変数とパス定数。

scripts/daily_bluesky_post/run.sh が ~/.config/aoyama-cemetery/*.env を
source した上で本プロセスを起動する想定。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# scripts/daily_bluesky_post/config.py から見て 2 階層上が repo root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SITE_URL = "https://aoyama-cemetery.pages.dev"

PEOPLE_DIR = PROJECT_ROOT / "src" / "content" / "people"
EVENTS_DIR = PROJECT_ROOT / "src" / "content" / "events"
POSTED_BLUESKY_LOG = PROJECT_ROOT / "logs" / "posted_bluesky.jsonl"
POSTED_X_LOG = PROJECT_ROOT / "logs" / "posted_x.jsonl"
ERRORS_LOG = PROJECT_ROOT / "logs" / "errors.jsonl"

MAX_POSTS_PER_DAY = 5


class MissingSecretError(RuntimeError):
    pass


@dataclass(frozen=True)
class XSecrets:
    api_key: str
    api_secret: str
    access_token: str
    access_secret: str


@dataclass(frozen=True)
class Secrets:
    bluesky_handle: str
    bluesky_app_password: str
    discord_webhook_url: Optional[str]  # 通知無しでも動作はする
    x: Optional[XSecrets]
    x_enabled: bool


def load_secrets() -> Secrets:
    handle = os.environ.get("BLUESKY_HANDLE")
    pw = os.environ.get("BLUESKY_APP_PASSWORD")
    if not handle or not pw:
        raise MissingSecretError(
            "BLUESKY_HANDLE / BLUESKY_APP_PASSWORD が未設定です。"
            " ~/.config/aoyama-cemetery/bluesky.env を確認してください。"
        )

    x_key = os.environ.get("X_API_KEY")
    x_secret = os.environ.get("X_API_SECRET")
    x_token = os.environ.get("X_ACCESS_TOKEN")
    x_token_secret = os.environ.get("X_ACCESS_SECRET")
    if x_key and x_secret and x_token and x_token_secret:
        x_secrets = XSecrets(
            api_key=x_key, api_secret=x_secret,
            access_token=x_token, access_secret=x_token_secret,
        )
    else:
        x_secrets = None
    x_flag = os.environ.get("X_ENABLED", "0") == "1"
    x_enabled = x_flag and x_secrets is not None

    return Secrets(
        bluesky_handle=handle,
        bluesky_app_password=pw,
        discord_webhook_url=os.environ.get("DISCORD_WEBHOOK_URL"),
        x=x_secrets,
        x_enabled=x_enabled,
    )
