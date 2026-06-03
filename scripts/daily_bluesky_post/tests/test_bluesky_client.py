"""bluesky_client の単体テスト(atproto SDK を MagicMock で置換)"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from atproto_client.exceptions import NetworkError, UnauthorizedError
from atproto_client.models.blob_ref import BlobRef

from daily_bluesky_post import bluesky_client
from daily_bluesky_post.ogp_fetcher import OGP


def _fake_atproto_client():
    """atproto.Client のインスタンスを模した MagicMock"""
    c = MagicMock()
    c.login.return_value = None
    # pydantic strict validation 対応: 本物の BlobRef を返す
    blob_ref = BlobRef(mimeType="image/jpeg", size=4, ref=b"fakeref")
    c.upload_blob.return_value = MagicMock(blob=blob_ref)
    post_record = MagicMock()
    post_record.uri = "at://did:plc:xxx/app.bsky.feed.post/abc"
    c.send_post.return_value = post_record
    return c, blob_ref


def test_post_with_image_uploads_blob_and_creates_post(monkeypatch):
    fake, blob_ref = _fake_atproto_client()
    monkeypatch.setattr(bluesky_client, "_make_client", lambda: fake)

    monkeypatch.setattr(
        "daily_bluesky_post.bluesky_client.ogp_fetcher.download_image",
        lambda url: (b"\xff\xd8fake", "image/jpeg"),
    )

    ogp = OGP(title="大久保 利通", description="維新三傑のひとり", image_url="https://x/y.jpg")
    uri = bluesky_client.post(
        handle="aoyama-cemetery.bsky.social",
        password="xxxx-xxxx-xxxx-xxxx",
        text="【本日の命日】大久保 利通\nhttps://aoyama-cemetery.pages.dev/people/okubo-toshimichi",
        link_url="https://aoyama-cemetery.pages.dev/people/okubo-toshimichi",
        ogp=ogp,
    )
    assert uri == "at://did:plc:xxx/app.bsky.feed.post/abc"
    fake.login.assert_called_once_with("aoyama-cemetery.bsky.social", "xxxx-xxxx-xxxx-xxxx")
    fake.upload_blob.assert_called_once()
    fake.send_post.assert_called_once()
    kwargs = fake.send_post.call_args.kwargs
    assert kwargs["embed"] is not None


def test_post_without_image_skips_blob_upload(monkeypatch):
    fake, _ = _fake_atproto_client()
    monkeypatch.setattr(bluesky_client, "_make_client", lambda: fake)
    ogp = OGP(title="星 新一", description="ショートショート", image_url=None)
    bluesky_client.post(
        handle="a.bsky.social",
        password="x",
        text="...",
        link_url="https://x/y",
        ogp=ogp,
    )
    fake.upload_blob.assert_not_called()
    fake.send_post.assert_called_once()


def test_post_retries_once_on_network_error(monkeypatch):
    """NetworkError で 1 回リトライ → 成功"""
    fake, _ = _fake_atproto_client()
    post_record = MagicMock(uri="at://retry")
    fake.send_post.side_effect = [NetworkError(), post_record]
    monkeypatch.setattr(bluesky_client, "_make_client", lambda: fake)
    monkeypatch.setattr("time.sleep", lambda s: None)

    ogp = OGP(None, None, None)
    uri = bluesky_client.post(
        handle="a", password="x", text="t", link_url="https://x", ogp=ogp,
    )
    assert uri == "at://retry"
    assert fake.send_post.call_count == 2


def test_post_raises_auth_error_on_login_401(monkeypatch):
    fake, _ = _fake_atproto_client()
    fake.login.side_effect = UnauthorizedError()
    monkeypatch.setattr(bluesky_client, "_make_client", lambda: fake)
    with pytest.raises(bluesky_client.AuthError):
        bluesky_client.post(
            handle="a",
            password="bad",
            text="t",
            link_url="https://x",
            ogp=OGP(None, None, None),
        )
