"""admin の編集を git commit + origin/main へ push する。

設計判断:
- 1 保存 = 1 commit + 1 push(失敗時 commit はローカルに残す)
- main ブランチ以外では abort
- 指定ファイルのみを commit(他の staged 変更を巻き込まない)
- pull --rebase は行わない(競合は明示的に surface する)
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class PublishResult:
    ok: bool
    message: str
    commit_sha: str | None = None


def _run_git(*args: str, timeout: float = 60.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _current_branch() -> str:
    return _run_git("branch", "--show-current").stdout.strip()


def _has_uncommitted_change(rel_path: str) -> bool:
    """指定パスに working tree or staged の変更があるか"""
    wt = _run_git("diff", "--quiet", "--", rel_path)
    staged = _run_git("diff", "--cached", "--quiet", "--", rel_path)
    # 削除されたファイルは ls-files で追跡、status で検出
    status = _run_git("status", "--porcelain", "--", rel_path)
    return wt.returncode != 0 or staged.returncode != 0 or bool(status.stdout.strip())


def publish(file_path: Path | str, message: str) -> PublishResult:
    """指定ファイルの変更を commit して origin/main に push する。"""
    try:
        abs_path = Path(file_path).resolve()
        rel = str(abs_path.relative_to(PROJECT_ROOT))
    except ValueError:
        return PublishResult(False, f"プロジェクトルート外のパス: {file_path}")

    branch = _current_branch()
    if branch != "main":
        return PublishResult(False, f"main ブランチではありません(現在: {branch})")

    if not _has_uncommitted_change(rel):
        return PublishResult(True, "変更なし(既に commit 済 or 未変更)")

    # 新規(未追跡)ファイルは stage しないと commit -- <path> が
    # "did not match any file(s) known to git" で失敗する。
    # add は新規・変更・削除のいずれも stage できる。
    add_proc = _run_git("add", "--", rel)
    if add_proc.returncode != 0:
        return PublishResult(
            False,
            f"add 失敗:\n{add_proc.stderr or add_proc.stdout}",
        )

    commit_proc = _run_git("commit", "-m", message, "--", rel)
    if commit_proc.returncode != 0:
        return PublishResult(
            False,
            f"commit 失敗:\n{commit_proc.stderr or commit_proc.stdout}",
        )

    sha = _run_git("rev-parse", "--short", "HEAD").stdout.strip()

    push_proc = _run_git("push", "origin", "main", timeout=90.0)
    if push_proc.returncode != 0:
        return PublishResult(
            False,
            f"commit {sha} はローカルに作成済、push 失敗:\n{push_proc.stderr or push_proc.stdout}",
            commit_sha=sha,
        )

    return PublishResult(True, f"push 完了(commit {sha})。数分で本番反映。", commit_sha=sha)
