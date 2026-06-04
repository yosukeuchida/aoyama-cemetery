from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from daily_bluesky_post.config import XSecrets
from daily_bluesky_post.x_client import (
    XClient, XAuthError, XRateLimitError, XPostError,
)


@pytest.fixture
def secrets():
    return XSecrets(api_key="k", api_secret="ks", access_token="t", access_secret="ts")


@pytest.fixture
def mock_tweepy():
    with patch("daily_bluesky_post.x_client.tweepy") as tw:
        v2 = MagicMock()
        v1 = MagicMock()
        tw.Client.return_value = v2
        tw.API.return_value = v1
        # exception 階層を再現
        class _Unauth(Exception): ...
        class _Forbidden(Exception): ...
        class _TooMany(Exception): ...
        class _Tweepy(Exception): ...
        tw.errors.Unauthorized = _Unauth
        tw.errors.Forbidden = _Forbidden
        tw.errors.TooManyRequests = _TooMany
        tw.errors.TweepyException = _Tweepy
        yield tw, v2, v1


def test_post_text_only(secrets, mock_tweepy):
    tw, v2, v1 = mock_tweepy
    v2.create_tweet.return_value = MagicMock(data={"id": "1234567890"})
    client = XClient(secrets)
    result = client.post(text="hello", image_path=None)
    assert result["tweet_id"] == "1234567890"
    assert "1234567890" in result["url"]
    v2.create_tweet.assert_called_once_with(text="hello", media_ids=None)


def test_post_with_image_uploads_via_v1(secrets, mock_tweepy, tmp_path):
    tw, v2, v1 = mock_tweepy
    v1.media_upload.return_value = MagicMock(media_id_string="m999")
    v2.create_tweet.return_value = MagicMock(data={"id": "777"})
    img = tmp_path / "p.jpg"
    img.write_bytes(b"\xff\xd8\xff")
    client = XClient(secrets)
    result = client.post(text="t", image_path=img)
    assert result["tweet_id"] == "777"
    v1.media_upload.assert_called_once_with(filename=str(img))
    v2.create_tweet.assert_called_once_with(text="t", media_ids=["m999"])


def test_post_unauthorized_raises_xautherror(secrets, mock_tweepy):
    tw, v2, v1 = mock_tweepy
    v2.create_tweet.side_effect = tw.errors.Unauthorized("401")
    client = XClient(secrets)
    with pytest.raises(XAuthError):
        client.post(text="t", image_path=None)


def test_post_forbidden_raises_xautherror(secrets, mock_tweepy):
    tw, v2, v1 = mock_tweepy
    v2.create_tweet.side_effect = tw.errors.Forbidden("403")
    client = XClient(secrets)
    with pytest.raises(XAuthError):
        client.post(text="t", image_path=None)


def test_post_too_many_requests_raises_ratelimit(secrets, mock_tweepy):
    tw, v2, v1 = mock_tweepy
    v2.create_tweet.side_effect = tw.errors.TooManyRequests("429")
    client = XClient(secrets)
    with pytest.raises(XRateLimitError):
        client.post(text="t", image_path=None)


def test_post_generic_tweepy_error_raises_xposterror(secrets, mock_tweepy):
    tw, v2, v1 = mock_tweepy
    v2.create_tweet.side_effect = tw.errors.TweepyException("boom")
    client = XClient(secrets)
    with pytest.raises(XPostError):
        client.post(text="t", image_path=None)


def test_media_upload_failure_falls_back_to_text_only(secrets, mock_tweepy, tmp_path):
    tw, v2, v1 = mock_tweepy
    v1.media_upload.side_effect = tw.errors.TweepyException("media fail")
    v2.create_tweet.return_value = MagicMock(data={"id": "1"})
    img = tmp_path / "p.jpg"
    img.write_bytes(b"x")
    client = XClient(secrets)
    result = client.post(text="t", image_path=img)
    # 画像 upload 失敗時はテキストのみで継続
    assert result["tweet_id"] == "1"
    v2.create_tweet.assert_called_once_with(text="t", media_ids=None)


def test_client_lazy_initializes_tweepy(secrets, mock_tweepy):
    tw, v2, v1 = mock_tweepy
    XClient(secrets)
    tw.Client.assert_called_once()
    tw.API.assert_called_once()
