import json

import httpx
import respx

from daily_bluesky_post import notifier


@respx.mock
def test_notify_sends_post_to_webhook():
    route = respx.post("https://discord.com/api/webhooks/abc").mock(
        return_value=httpx.Response(204)
    )
    notifier.notify(
        webhook_url="https://discord.com/api/webhooks/abc",
        title="投稿失敗",
        body="okubo-toshimichi: critique 2 連続 fail",
    )
    assert route.called
    sent = json.loads(route.calls[0].request.content)
    assert "投稿失敗" in sent["content"]
    assert "okubo-toshimichi" in sent["content"]


def test_notify_no_op_when_webhook_url_none():
    """webhook_url=None なら HTTP リクエストを送らずに何もしない (respx 未使用なので実際 HTTP 飛ばない)"""
    notifier.notify(webhook_url=None, title="t", body="b")
    # 例外を raise しないことが assertion


@respx.mock
def test_notify_swallows_http_error():
    """Discord 側 5xx でも本体処理は止めない"""
    respx.post("https://discord.com/api/webhooks/abc").mock(
        return_value=httpx.Response(500)
    )
    notifier.notify(webhook_url="https://discord.com/api/webhooks/abc", title="t", body="b")
    # 例外を raise しないこと


@respx.mock
def test_notify_truncates_long_content():
    """Discord は 2000 文字制限あり、長文は truncate される"""
    route = respx.post("https://discord.com/api/webhooks/abc").mock(
        return_value=httpx.Response(204)
    )
    notifier.notify(
        webhook_url="https://discord.com/api/webhooks/abc",
        title="t",
        body="x" * 5000,
    )
    sent = json.loads(route.calls[0].request.content)
    assert len(sent["content"]) <= 2000
    assert "truncated" in sent["content"]
