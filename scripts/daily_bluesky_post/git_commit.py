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

    bluesky_status / x_status に実際に渡される値(orchestrator 由来):
      "ok"              … 投稿成功 + posted_<platform>.jsonl に追記済
      "already"         … 既に同 (date, slug) 投稿済で skip
      "gen_fail"        … claude_runner が status="failed" or error を返した
      "length_fail"     … 字数超過、再生成後も超過で skip
      "auth_fail"       … 認証失敗(以降同 platform は当日 bypass)
      "rate_limit"      … X 月制限到達(以降 X は当日 bypass、X のみ)
      "fail"            … 上記以外の投稿失敗
      "skipped_auth"    … 先行 auth_fail を受けて以降の match を skip(Bluesky)
      "skipped_after_fail" … 先行 auth/rate を受けて以降の match を skip(X)
      "disabled"        … X_ENABLED=0 or X 認証情報未配置で X 全 skip(X のみ)
      "dry"             … --dry-run、投稿せず生成文 print のみ

    両 file を stage して diff があれば 1 commit、両方差分なしなら skip。
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
