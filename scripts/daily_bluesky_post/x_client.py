"""X (旧 Twitter) v2 投稿クライアント。

OAuth 1.0a User Context で
- v2 endpoint: POST /2/tweets(本文 + media_ids)
- v1.1 endpoint: POST /1.1/media/upload.json(画像)
の組み合わせ。

エラー区分:
- XAuthError      : 401 / 403(env 再確認、以降の X 処理 bypass)
- XRateLimitError : 429(月制限、以降の X 処理 bypass)
- XPostError      : その他 TweepyException(当該 match のみ skip)
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import tweepy

from daily_bluesky_post.config import XSecrets


class XAuthError(RuntimeError):
    pass


class XRateLimitError(RuntimeError):
    pass


class XPostError(RuntimeError):
    pass


class XClient:
    def __init__(self, secrets: XSecrets):
        self._v2 = tweepy.Client(
            consumer_key=secrets.api_key,
            consumer_secret=secrets.api_secret,
            access_token=secrets.access_token,
            access_token_secret=secrets.access_secret,
        )
        self._v1 = tweepy.API(tweepy.OAuth1UserHandler(
            secrets.api_key, secrets.api_secret,
            secrets.access_token, secrets.access_secret,
        ))

    def post(self, *, text: str, image_path: Optional[Path]) -> dict:
        media_ids = None
        if image_path is not None:
            try:
                media = self._v1.media_upload(filename=str(image_path))
                media_ids = [media.media_id_string]
            except tweepy.errors.TweepyException as e:
                # media upload は best-effort、失敗してもテキストのみで継続
                print(f"[x_client] media upload failed, falling back to text-only: {e}")
                media_ids = None

        try:
            resp = self._v2.create_tweet(text=text, media_ids=media_ids)
        except tweepy.errors.Unauthorized as e:
            raise XAuthError(f"X 認証失敗 (401): {e}") from e
        except tweepy.errors.Forbidden as e:
            raise XAuthError(f"X 認可失敗 (403): {e}") from e
        except tweepy.errors.TooManyRequests as e:
            raise XRateLimitError(f"X rate limit (429): {e}") from e
        except tweepy.errors.TweepyException as e:
            raise XPostError(f"X post failed: {e}") from e

        tweet_id = resp.data["id"]
        return {
            "tweet_id": tweet_id,
            "url": f"https://x.com/i/web/status/{tweet_id}",
        }
