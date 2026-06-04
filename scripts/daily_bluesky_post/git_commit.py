"""両 platform の posted log をまとめて commit する。push はしない。

orchestrator が match ごとに呼ぶ。差分がなければ skip(既に commit 済の場合の
二重 commit を防ぐ)。
"""
from __future__ import annotations

import subprocess

from daily_bluesky_post.config import PROJECT_ROOT


def commit_posted_logs(
    *,
    date: str, slug: str,
    bluesky_status: str, x_status: str,
) -> None:
    """両 platform の posted log をまとめて stage + commit。

    bluesky_status / x_status は "ok" / "fail" / "auth_fail" / "rate_limit" / "skip" / "disabled" 等。
    両方 stage して diff があれば 1 commit。
    """
    from daily_bluesky_post.config import POSTED_BLUESKY_LOG, POSTED_X_LOG

    rel_b = str(POSTED_BLUESKY_LOG.relative_to(PROJECT_ROOT))
    rel_x = str(POSTED_X_LOG.relative_to(PROJECT_ROOT))

    for rel in (rel_b, rel_x):
        subprocess.run(["git", "add", "--", rel], cwd=PROJECT_ROOT)

    diff_b = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", rel_b], cwd=PROJECT_ROOT,
    )
    diff_x = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", rel_x], cwd=PROJECT_ROOT,
    )
    if diff_b.returncode == 0 and diff_x.returncode == 0:
        return  # どちらも差分なし

    msg = f"post: {date} {slug} bluesky={bluesky_status} x={x_status}"
    subprocess.run(
        ["git", "commit", "-m", msg, "--", rel_b, rel_x],
        cwd=PROJECT_ROOT, check=True,
    )
