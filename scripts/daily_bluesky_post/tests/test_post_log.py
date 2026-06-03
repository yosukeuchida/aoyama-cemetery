import json
import threading
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

import pytest

from daily_bluesky_post import post_log

JST = timezone(timedelta(hours=9))


@pytest.fixture
def empty_log(tmp_path):
    p = tmp_path / "posted.jsonl"
    p.touch()
    return p


def test_load_empty(empty_log):
    assert post_log.load(empty_log) == []


def test_load_skips_blank_lines(empty_log):
    empty_log.write_text(
        '{"date":"2026-05-14","slug":"okubo-toshimichi","kind":"person",'
        '"post_uri":"at://x","at":"2026-05-14T08:05:23+09:00"}\n\n'
    )
    entries = post_log.load(empty_log)
    assert len(entries) == 1
    assert entries[0].slug == "okubo-toshimichi"


def test_already_posted_true_when_match(empty_log):
    empty_log.write_text(
        '{"date":"2026-05-14","slug":"okubo-toshimichi","kind":"person",'
        '"post_uri":"at://x","at":"2026-05-14T08:05:23+09:00"}\n'
    )
    entries = post_log.load(empty_log)
    assert post_log.already_posted(entries, date(2026, 5, 14), "okubo-toshimichi") is True


def test_already_posted_false_when_different_date(empty_log):
    empty_log.write_text(
        '{"date":"2026-05-14","slug":"okubo-toshimichi","kind":"person",'
        '"post_uri":"at://x","at":"2026-05-14T08:05:23+09:00"}\n'
    )
    entries = post_log.load(empty_log)
    assert post_log.already_posted(entries, date(2026, 5, 15), "okubo-toshimichi") is False


def test_append_writes_jsonl_line(empty_log):
    e = post_log.Entry(
        date=date(2026, 5, 14),
        slug="okubo-toshimichi",
        kind="person",
        post_uri="at://did:plc:xxx/app.bsky.feed.post/abc",
        at=datetime(2026, 5, 14, 8, 5, 23, tzinfo=JST),
    )
    post_log.append(empty_log, e)
    lines = empty_log.read_text().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["slug"] == "okubo-toshimichi"
    assert parsed["date"] == "2026-05-14"
    assert parsed["at"] == "2026-05-14T08:05:23+09:00"


def test_append_uses_flock_for_concurrency(empty_log):
    """同じファイルに 10 件並列 append しても全部残ること"""
    def writer(i):
        post_log.append(empty_log, post_log.Entry(
            date=date(2026, 5, 14),
            slug=f"slug-{i}",
            kind="person",
            post_uri=f"at://x/{i}",
            at=datetime(2026, 5, 14, 8, 5, i, tzinfo=JST),
        ))

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(empty_log.read_text().splitlines()) == 10
