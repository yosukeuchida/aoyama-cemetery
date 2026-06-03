"""atproto SDK の薄いラッパー。

upper layer には post(handle, password, text, link_url, ogp) → post_uri だけを公開。

- 401(login 失敗)→ AuthError(リトライしない)
- network / 5xx → 60 秒待って 1 回リトライ、それでも失敗なら raise
- 画像なし(ogp.image_url=None)なら blob upload を省略、external link card は title/description のみ
- 画像取得失敗時は thumb なしで投稿継続(except 内 swallow)
"""
from __future__ import annotations

import time

from atproto import Client, models
from atproto_client.exceptions import NetworkError, UnauthorizedError

from daily_bluesky_post import ogp_fetcher
from daily_bluesky_post.ogp_fetcher import OGP

RETRY_WAIT_SEC = 60


class AuthError(RuntimeError):
    pass


def _make_client() -> Client:
    return Client()


def post(*, handle: str, password: str, text: str, link_url: str, ogp: OGP) -> str:
    """投稿して post URI を返す。"""
    client = _make_client()
    try:
        client.login(handle, password)
    except UnauthorizedError as e:
        raise AuthError(f"Bluesky 認証失敗: {e}") from e

    embed = _build_external_embed(client, link_url, ogp)

    for attempt in range(2):
        try:
            record = client.send_post(text=text, embed=embed)
            return record.uri
        except NetworkError:
            if attempt == 0:
                time.sleep(RETRY_WAIT_SEC)
                continue
            raise

    # ループを抜けるのは raise されるパスのみ、ここには到達しない
    raise RuntimeError("unreachable")


def _build_external_embed(client: Client, link_url: str, ogp: OGP):
    thumb = None
    if ogp.image_url:
        try:
            data, _mime = ogp_fetcher.download_image(ogp.image_url)
            uploaded = client.upload_blob(data)
            thumb = uploaded.blob
        except Exception:
            # 画像取得失敗時は thumb なしで投稿継続
            thumb = None

    external = models.AppBskyEmbedExternal.External(
        uri=link_url,
        title=ogp.title or "",
        description=ogp.description or "",
        thumb=thumb,
    )
    return models.AppBskyEmbedExternal.Main(external=external)
