from datetime import date
from unittest.mock import MagicMock

import pytest

from daily_bluesky_post import orchestrator, config
from daily_bluesky_post.claude_runner import GenerateResult
from daily_bluesky_post.match import Match
from daily_bluesky_post.ogp_fetcher import OGP


def _ok_match(slug="okubo-toshimichi", kind="person"):
    plural = "people" if kind == "person" else "events"
    return Match(
        kind=kind,
        slug=slug,
        frontmatter={"name": "x"},
        url=f"https://aoyama-cemetery.pages.dev/{plural}/{slug}",
        anniversary_year=148,
    )


@pytest.fixture
def mocked(monkeypatch, tmp_path):
    """全 I/O を mock + log file を tmp_path に差し替え"""
    log_path = tmp_path / "posted.jsonl"
    log_path.touch()
    monkeypatch.setattr(config, "POSTED_LOG", log_path)

    # load_secrets を常に成功させる
    monkeypatch.setattr(
        "daily_bluesky_post.orchestrator.config.load_secrets",
        lambda: config.Secrets("h", "p", "https://discord/x"),
    )

    # 共通の no-op を差し込めるよう dict で返す
    notify_mock = MagicMock()
    monkeypatch.setattr("daily_bluesky_post.orchestrator.notifier.notify", notify_mock)

    commit_mock = MagicMock()
    monkeypatch.setattr(
        "daily_bluesky_post.orchestrator.git_commit.commit_posted_log", commit_mock
    )

    return {
        "log_path": log_path,
        "notify": notify_mock,
        "commit": commit_mock,
    }


def _set_match(monkeypatch, matches):
    monkeypatch.setattr(
        "daily_bluesky_post.orchestrator.match.match_today",
        lambda today, p, e: matches,
    )


def test_zero_matches_does_nothing(monkeypatch, mocked):
    _set_match(monkeypatch, [])
    rc = orchestrator.run(today=date(2026, 5, 14), dry_run=False)
    assert rc == 0
    mocked["notify"].assert_not_called()


def test_one_match_posts_and_logs(monkeypatch, mocked):
    _set_match(monkeypatch, [_ok_match()])
    monkeypatch.setattr(
        "daily_bluesky_post.orchestrator.claude_runner.generate_post",
        lambda **kw: GenerateResult(status="ok", post_text="...", attempts=1),
    )
    monkeypatch.setattr(
        "daily_bluesky_post.orchestrator.ogp_fetcher.fetch",
        lambda url: OGP("T", "D", None),
    )
    posted = MagicMock(return_value="at://x/y")
    monkeypatch.setattr("daily_bluesky_post.orchestrator.bluesky_client.post", posted)

    rc = orchestrator.run(today=date(2026, 5, 14), dry_run=False)
    assert rc == 0
    posted.assert_called_once()
    assert "okubo-toshimichi" in mocked["log_path"].read_text()
    mocked["commit"].assert_called_once()


def test_skips_already_posted(monkeypatch, mocked):
    mocked["log_path"].write_text(
        '{"date":"2026-05-14","slug":"okubo-toshimichi","kind":"person",'
        '"post_uri":"at://x","at":"2026-05-14T08:05:23+09:00"}\n'
    )
    _set_match(monkeypatch, [_ok_match()])
    posted = MagicMock()
    monkeypatch.setattr("daily_bluesky_post.orchestrator.bluesky_client.post", posted)

    rc = orchestrator.run(today=date(2026, 5, 14), dry_run=False)
    assert rc == 0
    posted.assert_not_called()


def test_critique_failed_notifies_and_skips_post(monkeypatch, mocked):
    _set_match(monkeypatch, [_ok_match()])
    monkeypatch.setattr(
        "daily_bluesky_post.orchestrator.claude_runner.generate_post",
        lambda **kw: GenerateResult(
            status="failed", attempts=2,
            violations=["frontmatter にない人名"], last_text="...",
        ),
    )
    posted = MagicMock()
    monkeypatch.setattr("daily_bluesky_post.orchestrator.bluesky_client.post", posted)

    rc = orchestrator.run(today=date(2026, 5, 14), dry_run=False)
    posted.assert_not_called()
    mocked["notify"].assert_called_once()
    # 通知本文に critique と violations が含まれる
    call_kwargs = mocked["notify"].call_args.kwargs
    body = call_kwargs.get("body", "")
    title = call_kwargs.get("title", "")
    assert "critique" in title.lower() or "critique" in body.lower()
    assert "frontmatter" in body


def test_dry_run_does_not_post_or_log(monkeypatch, mocked, capsys):
    _set_match(monkeypatch, [_ok_match()])
    monkeypatch.setattr(
        "daily_bluesky_post.orchestrator.claude_runner.generate_post",
        lambda **kw: GenerateResult(status="ok", post_text="DRY", attempts=1),
    )
    monkeypatch.setattr(
        "daily_bluesky_post.orchestrator.ogp_fetcher.fetch",
        lambda url: OGP("T", "D", None),
    )
    posted = MagicMock()
    monkeypatch.setattr("daily_bluesky_post.orchestrator.bluesky_client.post", posted)

    rc = orchestrator.run(today=date(2026, 5, 14), dry_run=True)
    posted.assert_not_called()
    assert "DRY" in capsys.readouterr().out
    assert mocked["log_path"].read_text() == ""
    mocked["commit"].assert_not_called()


def test_bluesky_auth_error_notifies_and_stops_remaining(monkeypatch, mocked):
    """AuthError は再ログインしても失敗するので残りの match は skip"""
    from daily_bluesky_post.bluesky_client import AuthError

    _set_match(monkeypatch, [_ok_match("a"), _ok_match("b")])
    monkeypatch.setattr(
        "daily_bluesky_post.orchestrator.claude_runner.generate_post",
        lambda **kw: GenerateResult(status="ok", post_text="...", attempts=1),
    )
    monkeypatch.setattr(
        "daily_bluesky_post.orchestrator.ogp_fetcher.fetch",
        lambda url: OGP("T", "D", None),
    )
    posted = MagicMock(side_effect=AuthError("bad password"))
    monkeypatch.setattr("daily_bluesky_post.orchestrator.bluesky_client.post", posted)

    rc = orchestrator.run(today=date(2026, 5, 14), dry_run=False)
    # 1 件目で AuthError、2 件目以降 skip → post は 1 回だけ呼ばれる
    assert posted.call_count == 1
    # 認証失敗通知が少なくとも 1 回
    assert mocked["notify"].call_count >= 1
