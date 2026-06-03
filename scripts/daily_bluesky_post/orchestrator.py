"""エンドツーエンド orchestrator + CLI entry。

usage:
  python -m daily_bluesky_post.orchestrator                  # 通常実行(launchd 用)
  python -m daily_bluesky_post.orchestrator --dry-run         # 投稿せず生成文を stdout
  python -m daily_bluesky_post.orchestrator --today 2026-05-14 --dry-run
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime, timezone, timedelta

from daily_bluesky_post import (
    bluesky_client,
    claude_runner,
    config,
    git_commit,
    match,
    notifier,
    ogp_fetcher,
    post_log,
)

logger = logging.getLogger("bluesky-post")
JST = timezone(timedelta(hours=9))


def run(*, today: date, dry_run: bool = False) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    secrets = config.load_secrets()

    matches = match.match_today(today, config.PEOPLE_DIR, config.EVENTS_DIR)
    logger.info("matches=%d for %s", len(matches), today.isoformat())
    if not matches:
        return 0

    entries = post_log.load(config.POSTED_LOG)
    auth_failed = False

    for m in matches:
        if post_log.already_posted(entries, today, m.slug):
            logger.info("skip already posted: %s", m.slug)
            continue
        if auth_failed:
            logger.info("skip (prior auth failure): %s", m.slug)
            continue

        result = claude_runner.generate_post(
            kind=m.kind,
            url=m.url,
            anniversary_year=m.anniversary_year,
            frontmatter=m.frontmatter,
        )
        if result.status != "ok":
            _notify_generation_failure(secrets.discord_webhook_url, m, result)
            continue

        if dry_run:
            print(f"--- DRY RUN: {m.slug} ---")
            print(result.post_text)
            print()
            continue

        ogp = ogp_fetcher.fetch(m.url)
        try:
            uri = bluesky_client.post(
                handle=secrets.bluesky_handle,
                password=secrets.bluesky_app_password,
                text=result.post_text,
                link_url=m.url,
                ogp=ogp,
            )
        except bluesky_client.AuthError as e:
            notifier.notify(
                webhook_url=secrets.discord_webhook_url,
                title="Bluesky 認証失敗",
                body=(
                    f"{e}\n"
                    "App Password を再発行して "
                    "~/.config/aoyama-cemetery/bluesky.env を更新してください。"
                ),
            )
            auth_failed = True
            continue
        except Exception as e:  # noqa: BLE001
            notifier.notify(
                webhook_url=secrets.discord_webhook_url,
                title="Bluesky 投稿失敗",
                body=f"slug={m.slug}\nerror={e}\ntext=\n{result.post_text}",
            )
            continue

        now = datetime.now(JST).replace(microsecond=0)
        entry = post_log.Entry(
            date=today, slug=m.slug, kind=m.kind, post_uri=uri, at=now,
        )
        post_log.append(config.POSTED_LOG, entry)
        entries.append(entry)
        git_commit.commit_posted_log(f"post: {today.isoformat()} {m.slug}")
        logger.info("posted: %s -> %s", m.slug, uri)

    return 0


def _notify_generation_failure(webhook, m: match.Match, result: claude_runner.GenerateResult) -> None:
    if result.status == "failed":
        title = "LLM critique 2 連続 fail"
        body = (
            f"slug={m.slug} ({m.kind})\n"
            f"violations: {result.violations}\n"
            f"last_text:\n{result.last_text}"
        )
    else:
        title = "LLM 生成エラー"
        body = f"slug={m.slug} ({m.kind})\nerror: {result.error}"
    notifier.notify(webhook_url=webhook, title=title, body=body)


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--today", help="YYYY-MM-DD(未指定なら JST 今日)")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    today = date.fromisoformat(args.today) if args.today else datetime.now(JST).date()
    return run(today=today, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
