"""偉人 / event ページから OGP メタを抜き取る。

Bluesky の link card 用に title / description / og:image を返す。
画像は別関数 download_image で bytes を取得(blob upload は bluesky_client 側)。
"""
from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from typing import Optional, Tuple

import httpx
from bs4 import BeautifulSoup

USER_AGENT = "aoyama-cemetery-bluesky-bot/1.0 (+https://aoyama-cemetery.pages.dev)"
TIMEOUT = httpx.Timeout(15.0, connect=5.0)


@dataclass
class OGP:
    title: Optional[str]
    description: Optional[str]
    image_url: Optional[str]


def fetch(url: str) -> OGP:
    try:
        resp = httpx.get(url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
    except httpx.HTTPError:
        return OGP(None, None, None)
    if resp.status_code != 200:
        return OGP(None, None, None)
    return _parse(resp.text)


def _parse(html: str) -> OGP:
    soup = BeautifulSoup(html, "html.parser")

    def meta(prop: str) -> Optional[str]:
        tag = soup.find("meta", property=prop)
        return tag.get("content") if tag else None

    return OGP(
        title=meta("og:title"),
        description=meta("og:description"),
        image_url=meta("og:image"),
    )


def download_image(url: str) -> Tuple[bytes, str]:
    """画像 URL から bytes と推定 MIME を返す。"""
    resp = httpx.get(url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
    resp.raise_for_status()
    mime = resp.headers.get("content-type", "").split(";")[0].strip()
    if not mime:
        mime = mimetypes.guess_type(url)[0] or "application/octet-stream"
    return resp.content, mime
