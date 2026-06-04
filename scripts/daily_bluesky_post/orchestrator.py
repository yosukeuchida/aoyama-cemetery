"""エンドツーエンド orchestrator + CLI entry。

usage:
  python -m daily_bluesky_post.orchestrator
  python -m daily_bluesky_post.orchestrator --dry-run
  python -m daily_bluesky_post.orchestrator --today 2026-05-14 --dry-run
"""
from __future__ import annotations

import argparse
import logging
import sys
import tempfile
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from daily_bluesky_post import (
    bluesky_client, claude_runner, config, git_commit, image_resolver,
    match, notifier, ogp_fetcher, post_log, x_text,
)
from daily_bluesky_post.x_client import (
    XAuthError, XClient, XPostError, XRateLimitError,
)

logger = logging.getLogger("aoyama-post")
JST = timezone(timedelta(hours=9))

BLUESKY_LIMIT = 300
BLUESKY_SAFE = 290


def _build_x_client(x_secrets) -> XClient:
    """テスト fixture から差し替えるための薄いファクトリ。"""
    return XClient(x_secrets)


def _resolve_image(slug: str, kind: str) -> Optional[Path]:
    return image_resolver.resolve(
        slug, kind=kind,
        people_dir=config.PEOPLE_DIR, events_dir=config.EVENTS_DIR,
    )


def run(*, today: date, dry_run: bool = False) -> int:
    secrets = config.load_secrets()
    matches = match.match_today(today, config.PEOPLE_DIR, config.EVENTS_DIR)
    logger.info("matches=%d for %s", len(matches), today.isoformat())
    if not matches:
        return 0

    entries_b = post_log.load(config.POSTED_BLUESKY_LOG)
    entries_x = post_log.load(config.POSTED_X_LOG)
    bluesky_auth_failed = False
    x_disabled_after_fail = False
    x_client_instance: Optional[XClient] = None

    for m in matches:
        bluesky_status = _process_bluesky(
            m, today, secrets, entries_b, dry_run,
            auth_failed=bluesky_auth_failed,
        )
        if bluesky_status == "auth_fail":
            bluesky_auth_failed = True

        if not secrets.x_enabled:
            x_status = "disabled"
        elif x_disabled_after_fail:
            x_status = "skipped_after_fail"
        else:
            if x_client_instance is None:
                x_client_instance = _build_x_client(secrets.x)
            x_status = _process_x(
                m, today, secrets, entries_x, dry_run, x_client_instance,
            )
            if x_status in ("auth_fail", "rate_limit"):
                x_disabled_after_fail = True

        if not dry_run:
            git_commit.commit_posted_logs(
                date=today.isoformat(), slug=m.slug,
                bluesky_status=bluesky_status, x_status=x_status,
            )

    return 0


def _process_bluesky(m, today, secrets, entries, dry_run, *, auth_failed) -> str:
    if auth_failed:
        return "skipped_auth"
    if post_log.already_posted(entries, today, m.slug):
        return "already"

    result = claude_runner.generate_post(
        kind=m.kind, url=m.url, anniversary_year=m.anniversary_year,
        frontmatter=m.frontmatter, body=m.body,
        agent_name="aoyama-post-writer",
        fact_checker_name="aoyama-fact-checker",
    )
    if result.status != "ok":
        _notify_generation_failure(secrets.discord_webhook_url, m, result, platform="bluesky")
        return "gen_fail"

    text_len = len(result.post_text)
    if text_len > BLUESKY_LIMIT:
        result = claude_runner.regenerate_shorter(
            kind=m.kind, url=m.url, anniversary_year=m.anniversary_year,
            frontmatter=m.frontmatter, body=m.body,
            previous_text=result.post_text, previous_length=text_len,
            target_length=BLUESKY_SAFE,
        )
        if result.status != "ok" or len(result.post_text) > BLUESKY_LIMIT:
            notifier.notify(
                webhook_url=secrets.discord_webhook_url,
                title="[bluesky] 字数超過",
                body=f"slug={m.slug}\ntext:\n{result.post_text}",
            )
            return "length_fail"

    if dry_run:
        print(f"--- BLUESKY DRY: {m.slug} ({len(result.post_text)} chars) ---\n{result.post_text}\n")
        return "dry"

    ogp = ogp_fetcher.fetch(m.url)
    try:
        uri = bluesky_client.post(
            handle=secrets.bluesky_handle, password=secrets.bluesky_app_password,
            text=result.post_text, link_url=m.url, ogp=ogp,
        )
    except bluesky_client.AuthError as e:
        notifier.notify(
            webhook_url=secrets.discord_webhook_url,
            title="[bluesky] 認証失敗",
            body=str(e),
        )
        return "auth_fail"
    except Exception as e:  # noqa: BLE001
        notifier.notify(
            webhook_url=secrets.discord_webhook_url,
            title="[bluesky] 投稿失敗",
            body=f"slug={m.slug}\nerror={e}\ntext=\n{result.post_text}",
        )
        return "fail"

    now = datetime.now(JST).replace(microsecond=0)
    entry = post_log.Entry(date=today, slug=m.slug, kind=m.kind, post_uri=uri, at=now)
    post_log.append(config.POSTED_BLUESKY_LOG, entry)
    entries.append(entry)
    return "ok"


def _process_x(m, today, secrets, entries, dry_run, x_client) -> str:
    if post_log.already_posted(entries, today, m.slug):
        return "already"

    result = claude_runner.generate_post(
        kind=m.kind, url=m.url, anniversary_year=m.anniversary_year,
        frontmatter=m.frontmatter, body=m.body,
        agent_name="aoyama-post-writer-x",
        fact_checker_name="aoyama-fact-checker-x",
    )
    if result.status != "ok":
        _notify_generation_failure(secrets.discord_webhook_url, m, result, platform="x")
        return "gen_fail"

    wl = x_text.x_weighted_length(result.post_text)
    if wl > x_text.X_LIMIT:
        result = claude_runner.regenerate_shorter(
            kind=m.kind, url=m.url, anniversary_year=m.anniversary_year,
            frontmatter=m.frontmatter, body=m.body,
            previous_text=result.post_text, previous_length=wl,
            target_length=x_text.X_SAFE_LIMIT,
            agent_name="aoyama-post-writer-x",
            fact_checker_name="aoyama-fact-checker-x",
        )
        final_wl = x_text.x_weighted_length(result.post_text) if result.status == "ok" else wl
        if result.status != "ok" or final_wl > x_text.X_LIMIT:
            notifier.notify(
                webhook_url=secrets.discord_webhook_url,
                title="[x] 字数超過",
                body=f"slug={m.slug}\nweighted={final_wl}\ntext:\n{result.post_text}",
            )
            return "length_fail"
        wl = final_wl  # for downstream dry_run print

    if dry_run:
        print(f"--- X DRY: {m.slug} ({wl} units) ---\n{result.post_text}\n")
        return "dry"

    image_src = _resolve_image(m.slug, m.kind)
    image_to_send = None
    tmp_holder = None
    try:
        if image_src is not None:
            tmp_holder = tempfile.TemporaryDirectory()
            try:
                image_to_send = image_resolver.prepare_for_upload(image_src, tmp_dir=Path(tmp_holder.name))
            except Exception as e:  # noqa: BLE001
                logger.warning("image prepare failed: %s, posting text only", e)
                image_to_send = None
        try:
            resp = x_client.post(text=result.post_text, image_path=image_to_send)
        except XAuthError as e:
            notifier.notify(
                webhook_url=secrets.discord_webhook_url,
                title="[x] 認証失敗",
                body=f"{e}\n~/.config/aoyama-cemetery/x.env を確認してください。",
            )
            return "auth_fail"
        except XRateLimitError as e:
            notifier.notify(
                webhook_url=secrets.discord_webhook_url,
                title="[x] rate limit",
                body=str(e),
            )
            return "rate_limit"
        except XPostError as e:
            notifier.notify(
                webhook_url=secrets.discord_webhook_url,
                title="[x] 投稿失敗",
                body=f"slug={m.slug}\nerror={e}\ntext=\n{result.post_text}",
            )
            return "fail"
        except Exception as e:  # noqa: BLE001
            notifier.notify(
                webhook_url=secrets.discord_webhook_url,
                title="[x] 投稿失敗(想定外)",
                body=f"slug={m.slug}\nerror={type(e).__name__}: {e}\ntext=\n{result.post_text}",
            )
            return "fail"
    finally:
        if tmp_holder is not None:
            tmp_holder.cleanup()

    now = datetime.now(JST).replace(microsecond=0)
    entry = post_log.Entry(date=today, slug=m.slug, kind=m.kind,
                           post_uri=resp["url"], at=now)
    post_log.append(config.POSTED_X_LOG, entry)
    entries.append(entry)
    return "ok"


def _notify_generation_failure(webhook, m, result, *, platform: str) -> None:
    title = f"[{platform}] LLM critique 2 連続 fail" if result.status == "failed" else f"[{platform}] LLM 生成エラー"
    body = (
        f"slug={m.slug} ({m.kind})\n"
        f"violations: {result.violations}\nlast_text:\n{result.last_text}"
        if result.status == "failed"
        else f"slug={m.slug} ({m.kind})\nerror: {result.error}"
    )
    notifier.notify(webhook_url=webhook, title=title, body=body)


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--today", help="YYYY-MM-DD")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    today = date.fromisoformat(args.today) if args.today else datetime.now(JST).date()
    return run(today=today, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
