"""Discord webhook 通知。

失敗時の能動通知。webhook URL が未設定なら no-op。
Discord 側エラー時に本体処理を止めないよう例外は呑む(ログのみ)。
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


def notify(*, webhook_url: Optional[str], title: str, body: str) -> None:
    if not webhook_url:
        return
    content = f"🚨 [aoyama-cemetery] {title}\n{body}"
    if len(content) > 1900:
        content = content[:1900] + "\n…(truncated)"
    try:
        resp = httpx.post(webhook_url, json={"content": content}, timeout=10)
        if resp.status_code >= 300:
            logger.warning("Discord webhook returned %s: %s", resp.status_code, resp.text[:200])
    except httpx.HTTPError as e:
        logger.warning("Discord webhook failed: %s", e)
