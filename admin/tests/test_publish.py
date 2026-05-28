"""publish: git subprocess を mock してパス分岐をテスト"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from admin.lib import publish


def _proc(returncode: int = 0, stdout: str = "", stderr: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def test_publish_rejects_path_outside_project(tmp_path):
    """プロジェクト外のパスは ValueError 派生エラー"""
    result = publish.publish(tmp_path / "x.md", "msg")
    assert result.ok is False
    assert "プロジェクトルート外" in result.message


def test_publish_rejects_non_main_branch():
    """main 以外のブランチでは abort"""
    with patch("admin.lib.publish._run_git") as m:
        m.side_effect = [_proc(stdout="feature/x\n")]  # current_branch
        result = publish.publish(publish.PROJECT_ROOT / "README.md", "msg")
    assert result.ok is False
    assert "main" in result.message


def test_publish_skips_when_no_changes():
    """変更なしなら no-op で成功扱い"""
    with patch("admin.lib.publish._run_git") as m:
        m.side_effect = [
            _proc(stdout="main\n"),  # current_branch
            _proc(returncode=0),  # diff (no change)
            _proc(returncode=0),  # diff --cached (no change)
            _proc(stdout=""),  # status --porcelain (no change)
        ]
        result = publish.publish(publish.PROJECT_ROOT / "README.md", "msg")
    assert result.ok is True
    assert "変更なし" in result.message


def test_publish_happy_path():
    """commit + push が両方成功"""
    with patch("admin.lib.publish._run_git") as m:
        m.side_effect = [
            _proc(stdout="main\n"),  # current_branch
            _proc(returncode=1),  # diff (has change)
            _proc(returncode=0),  # diff --cached
            _proc(stdout=" M README.md\n"),  # status
            _proc(returncode=0),  # add
            _proc(returncode=0),  # commit
            _proc(stdout="abc1234\n"),  # rev-parse
            _proc(returncode=0),  # push
        ]
        result = publish.publish(publish.PROJECT_ROOT / "README.md", "feat: x")
    assert result.ok is True
    assert result.commit_sha == "abc1234"
    assert "push 完了" in result.message


def test_publish_push_failure_keeps_commit():
    """push 失敗時、commit はローカルに残るが ok=False"""
    with patch("admin.lib.publish._run_git") as m:
        m.side_effect = [
            _proc(stdout="main\n"),
            _proc(returncode=1),
            _proc(returncode=0),
            _proc(stdout=" M README.md\n"),
            _proc(returncode=0),  # add
            _proc(returncode=0),  # commit OK
            _proc(stdout="abc1234\n"),
            _proc(returncode=1, stderr="rejected (non-fast-forward)"),  # push fail
        ]
        result = publish.publish(publish.PROJECT_ROOT / "README.md", "feat: x")
    assert result.ok is False
    assert result.commit_sha == "abc1234"
    assert "push 失敗" in result.message
    assert "non-fast-forward" in result.message


def test_publish_stages_new_untracked_file():
    """新規(未追跡)ファイルは add で stage してから commit する"""
    with patch("admin.lib.publish._run_git") as m:
        m.side_effect = [
            _proc(stdout="main\n"),  # current_branch
            _proc(returncode=0),  # diff (untracked → no diff)
            _proc(returncode=0),  # diff --cached
            _proc(stdout="?? src/assets/grave-photos/x/photo.jpg\n"),  # status: untracked
            _proc(returncode=0),  # add
            _proc(returncode=0),  # commit
            _proc(stdout="abc1234\n"),  # rev-parse
            _proc(returncode=0),  # push
        ]
        result = publish.publish(
            publish.PROJECT_ROOT / "src/assets/grave-photos/x/photo.jpg", "feat: photo"
        )
    assert result.ok is True
    # add が commit より前に呼ばれている
    called = [c.args[0] for c in m.call_args_list]
    assert called.index("add") < called.index("commit")


def test_publish_commit_failure():
    """commit が失敗(hook 失敗等)した場合 ok=False"""
    with patch("admin.lib.publish._run_git") as m:
        m.side_effect = [
            _proc(stdout="main\n"),
            _proc(returncode=1),
            _proc(returncode=0),
            _proc(stdout=" M README.md\n"),
            _proc(returncode=0),  # add
            _proc(returncode=1, stderr="pre-commit hook failed"),
        ]
        result = publish.publish(publish.PROJECT_ROOT / "README.md", "feat: x")
    assert result.ok is False
    assert result.commit_sha is None
    assert "commit 失敗" in result.message
