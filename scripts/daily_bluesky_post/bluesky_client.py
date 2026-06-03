"""atproto SDK の薄いラッパー。

upper layer には post(handle, password, text, link_url, ogp) → post_uri だけを公開。

- 401(login 失敗)→ AuthError(リトライしない)
- network / 5xx → 60 秒待って 1 回リトライ、それでも失敗なら raise
- 画像なし(ogp.image_url=None)なら blob upload を省略、external link card は title/description のみ
- 画像取得失敗時は thumb なしで投稿継続(except 内 swallow)
"""
from __future__ import annotations

import time

import httpx
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
        raise AuthError(
            f"Bluesky 認証失敗 (handle={handle}): App Password が無効か期限切れ"
        ) from e

    embed = _build_external_embed(client, link_url, ogp)
    facets = _build_url_facets(text, link_url)

    for attempt in range(2):
        try:
            if facets:
                record = client.send_post(text=text, embed=embed, facets=facets)
            else:
                record = client.send_post(text=text, embed=embed)
            return record.uri
        except NetworkError:
            if attempt == 0:
                time.sleep(RETRY_WAIT_SEC)
                continue
            raise

    # ループを抜けるのは raise されるパスのみ、ここには到達しない
    raise RuntimeError("unreachable")


def _build_url_facets(text: str, link_url: str):
    """text 中の link_url(最後の出現)に対する facet リストを返す。

    Bluesky の facet は UTF-8 byte offset を使うため、bytes 化してから索引する。
    URL が text 中に無ければ None。
    """
    text_bytes = text.encode("utf-8")
    url_bytes = link_url.encode("utf-8")
    byte_start = text_bytes.rfind(url_bytes)
    if byte_start == -1:
        return None
    byte_end = byte_start + len(url_bytes)
    return [
        models.AppBskyRichtextFacet.Main(
            index=models.AppBskyRichtextFacet.ByteSlice(
                byte_start=byte_start,
                byte_end=byte_end,
            ),
            features=[
                models.AppBskyRichtextFacet.Link(uri=link_url),
            ],
        )
    ]


def _build_external_embed(client: Client, link_url: str, ogp: OGP):
    thumb = None
    if ogp.image_url:
        try:
            data, _mime = ogp_fetcher.download_image(ogp.image_url)
            uploaded = client.upload_blob(data)
            thumb = uploaded.blob
        except (httpx.HTTPError, NetworkError) as e:
            # 画像取得・upload 失敗時は thumb なしで投稿継続(理由をログに残す)
            print(f"[bluesky_client] thumb fallback due to {type(e).__name__}: {e}")
            thumb = None

    external = models.AppBskyEmbedExternal.External(
        uri=link_url,
        title=ogp.title or "",
        description=ogp.description or "",
        thumb=thumb,
    )
    return models.AppBskyEmbedExternal.Main(external=external)
