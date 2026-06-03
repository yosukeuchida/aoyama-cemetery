"""logs/posted.jsonl を単独 commit する。push はしない。

orchestrator が投稿成功直後に呼ぶ。差分がなければ skip(catch-up 等で既に
commit 済の場合の二重 commit を防ぐ)。
"""
from __future__ import annotations

import subprocess

from daily_bluesky_post.config import POSTED_LOG, PROJECT_ROOT


def commit_posted_log(message: str) -> None:
    rel = POSTED_LOG.relative_to(PROJECT_ROOT)
    rel_str = str(rel)

    # stage
    subprocess.run(
        ["git", "add", "--", rel_str],
        cwd=PROJECT_ROOT,
        check=True,
    )

    # 差分なしなら skip
    diff = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", rel_str],
        cwd=PROJECT_ROOT,
    )
    if diff.returncode == 0:
        return

    subprocess.run(
        ["git", "commit", "-m", message, "--", rel_str],
        cwd=PROJECT_ROOT,
        check=True,
    )
