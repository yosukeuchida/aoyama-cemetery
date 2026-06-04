from unittest.mock import MagicMock

from daily_bluesky_post import git_commit


def test_commit_log_runs_git_add_then_commit(monkeypatch):
    calls = []

    def fake_run(cmd, **kw):
        calls.append(list(cmd))
        # diff --cached --quiet が returncode=1(差分あり)を返す mock
        if "diff" in cmd and "--cached" in cmd:
            return MagicMock(returncode=1)
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    git_commit.commit_posted_log("post: 2026-05-14 okubo-toshimichi")

    # add → diff --cached → commit の順
    assert any("add" in c for c in calls)
    assert any("commit" in c for c in calls)
    add_call = next(c for c in calls if "add" in c)
    commit_call = next(c for c in calls if "commit" in c)
    assert "logs/posted_bluesky.jsonl" in " ".join(add_call)
    assert "post: 2026-05-14 okubo-toshimichi" in " ".join(commit_call)


def test_commit_log_skips_when_nothing_staged(monkeypatch):
    """diff --cached --quiet が returncode=0(差分なし) なら commit しない"""
    calls = []

    def fake_run(cmd, **kw):
        calls.append(list(cmd))
        if "diff" in cmd and "--cached" in cmd:
            return MagicMock(returncode=0)  # 差分なし
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)
    git_commit.commit_posted_log("noop")
    # commit は呼ばれない
    assert not any("commit" in c for c in calls)
