"""git_ops: git log / status のラッパーテスト"""
from pathlib import Path
from unittest.mock import patch

from admin.lib import git_ops


def test_last_commit_date_returns_iso_string():
    """last_commit_date: 指定ファイルの最終 commit 日時を ISO で返す"""
    sample = Path("src/content/people/okubo-toshimichi.md")
    result = git_ops.last_commit_date(sample)
    assert result is None or "T" in result or "-" in result


def test_last_commit_date_returns_none_for_untracked(tmp_path):
    """git 管理外のファイルは None"""
    untracked = tmp_path / "untracked.md"
    untracked.write_text("x")
    assert git_ops.last_commit_date(untracked) is None


def test_uncommitted_count_returns_int():
    """uncommitted_count: int を返す(値は環境依存なので int 検証のみ)"""
    n = git_ops.uncommitted_count()
    assert isinstance(n, int)
    assert n >= 0


def test_uncommitted_count_with_mock():
    """git status --porcelain の出力をパース"""
    fake_output = " M src/content/people/x.md\n M src/content/people/y.md\n?? new.md\n"
    with patch("subprocess.run") as m:
        m.return_value.stdout = fake_output
        m.return_value.returncode = 0
        assert git_ops.uncommitted_count() == 3
