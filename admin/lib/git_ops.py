"""git の read-only ラッパー。書き込み系は提供しない(意図的)。"""
from __future__ import annotations

import subprocess
from pathlib import Path


def last_commit_date(path: Path | str) -> str | None:
    """指定パスの最終 commit 日時を ISO 文字列で返す。git 管理外なら None。"""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--", str(path)],
            capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError:
        return None
    output = result.stdout.strip()
    return output or None


def uncommitted_count() -> int:
    """未 commit ファイル数(working tree + staged)を返す。"""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return 0
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    return len(lines)
