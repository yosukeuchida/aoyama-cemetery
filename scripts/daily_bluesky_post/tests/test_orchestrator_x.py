from datetime import date
from unittest.mock import MagicMock

import pytest

from daily_bluesky_post import orchestrator, match, claude_runner


def _mk_match(slug="okubo", kind="person"):
    return match.Match(
        kind=kind, slug=slug, frontmatter={"name": "テスト", "url": "https://x"},
        body="本文", url="https://aoyama-cemetery.pages.dev/people/" + slug,
        anniversary_year=150,
    )


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("BLUESKY_HANDLE", "h")
    monkeypatch.setenv("BLUESKY_APP_PASSWORD", "p")
    monkeypatch.setenv("X_API_KEY", "k")
    monkeypatch.setenv("X_API_SECRET", "ks")
    monkeypatch.setenv("X_ACCESS_TOKEN", "t")
    monkeypatch.setenv("X_ACCESS_SECRET", "ts")
    monkeypatch.setenv("X_ENABLED", "1")
    from daily_bluesky_post import config
    monkeypatch.setattr(config, "POSTED_BLUESKY_LOG", tmp_path / "pb.jsonl")
    monkeypatch.setattr(config, "POSTED_X_LOG", tmp_path / "px.jsonl")
    return tmp_path


def _patch_all(monkeypatch, *,
               match_result=None, claude_text="本文 https://x", claude_status="ok",
               bluesky_uri="at://x", x_result=None, x_exc=None):
    matches = [_mk_match()] if match_result is None else match_result
    monkeypatch.setattr(orchestrator.match, "match_today", lambda *a, **k: matches)
    monkeypatch.setattr(
        orchestrator.claude_runner, "generate_post",
        lambda **k: claude_runner.GenerateResult(status=claude_status, post_text=claude_text),
    )
    monkeypatch.setattr(orchestrator.ogp_fetcher, "fetch",
                        lambda url: MagicMock(title="t", description="d", image_url=None))
    monkeypatch.setattr(orchestrator.bluesky_client, "post", lambda **k: bluesky_uri)
    fake_x = MagicMock()
    if x_exc is not None:
        fake_x.post.side_effect = x_exc
    else:
        fake_x.post.return_value = x_result or {"tweet_id": "1", "url": "https://x.com/i/web/status/1"}
    monkeypatch.setattr(orchestrator, "_build_x_client", lambda secrets: fake_x)
    monkeypatch.setattr(orchestrator, "_resolve_image", lambda slug, kind: None)
    monkeypatch.setattr(orchestrator.git_commit, "commit_posted_logs", lambda **k: None)
    monkeypatch.setattr(orchestrator.notifier, "notify", lambda **k: None)
    return fake_x


def test_both_platforms_succeed(env, monkeypatch):
    fake_x = _patch_all(monkeypatch)
    rc = orchestrator.run(today=date(2026, 5, 14), dry_run=False)
    assert rc == 0
    fake_x.post.assert_called_once()


def test_x_disabled_skips_x(env, monkeypatch):
    monkeypatch.setenv("X_ENABLED", "0")
    fake_x = _patch_all(monkeypatch)
    orchestrator.run(today=date(2026, 5, 14), dry_run=False)
    fake_x.post.assert_not_called()


def test_x_auth_failure_disables_rest_of_x(env, monkeypatch):
    from daily_bluesky_post.x_client import XAuthError
    matches = [_mk_match("a"), _mk_match("b")]
    fake_x = _patch_all(monkeypatch, match_result=matches, x_exc=XAuthError("401"))
    orchestrator.run(today=date(2026, 5, 14), dry_run=False)
    assert fake_x.post.call_count == 1  # 連鎖防止


def test_bluesky_success_x_failure_independent(env, monkeypatch):
    from daily_bluesky_post.x_client import XPostError
    fake_x = _patch_all(monkeypatch, x_exc=XPostError("boom"))
    rc = orchestrator.run(today=date(2026, 5, 14), dry_run=False)
    assert rc == 0  # 完走


def test_already_posted_per_platform(env, monkeypatch):
    from daily_bluesky_post import post_log, config
    from datetime import datetime, timezone, timedelta
    JST = timezone(timedelta(hours=9))
    # Bluesky 側だけ既投稿
    post_log.append(config.POSTED_BLUESKY_LOG, post_log.Entry(
        date=date(2026, 5, 14), slug="okubo", kind="person",
        post_uri="at://existing", at=datetime.now(JST).replace(microsecond=0),
    ))
    fake_x = _patch_all(monkeypatch)
    fake_bsky = MagicMock(return_value="at://new")
    monkeypatch.setattr(orchestrator.bluesky_client, "post", fake_bsky)
    orchestrator.run(today=date(2026, 5, 14), dry_run=False)
    # Bluesky はスキップされ X だけ実行
    fake_bsky.assert_not_called()
    fake_x.post.assert_called_once()


def test_x_rate_limit_disables_rest(env, monkeypatch):
    from daily_bluesky_post.x_client import XRateLimitError
    matches = [_mk_match("a"), _mk_match("b")]
    fake_x = _patch_all(monkeypatch, match_result=matches, x_exc=XRateLimitError("429"))
    orchestrator.run(today=date(2026, 5, 14), dry_run=False)
    assert fake_x.post.call_count == 1


def test_dry_run_does_not_post_either(env, monkeypatch):
    fake_x = _patch_all(monkeypatch)
    fake_bsky = MagicMock()
    monkeypatch.setattr(orchestrator.bluesky_client, "post", fake_bsky)
    orchestrator.run(today=date(2026, 5, 14), dry_run=True)
    fake_bsky.assert_not_called()
    fake_x.post.assert_not_called()
