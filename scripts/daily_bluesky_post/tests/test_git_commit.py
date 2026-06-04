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


def test_commit_posted_logs_stages_both_files(monkeypatch, tmp_path):
    from daily_bluesky_post import git_commit
    calls = []
    def fake_run(args, **kw):
        calls.append(list(args))
        class R: returncode = 1  # diff あり扱い
        return R()
    monkeypatch.setattr(git_commit.subprocess, "run", fake_run)
    git_commit.commit_posted_logs(date="2026-05-14", slug="okubo",
                                  bluesky_status="ok", x_status="ok")
    # git add で 2 ファイル分 staging
    add_calls = [c for c in calls if len(c) >= 2 and c[1] == "add"]
    assert any("posted_bluesky.jsonl" in " ".join(c) for c in add_calls)
    assert any("posted_x.jsonl" in " ".join(c) for c in add_calls)
    commit_calls = [c for c in calls if len(c) >= 2 and c[1] == "commit"]
    assert len(commit_calls) == 1
    msg = " ".join(commit_calls[0])
    assert "2026-05-14" in msg and "okubo" in msg
    assert "bluesky=ok" in msg and "x=ok" in msg


def test_commit_posted_logs_skips_when_no_diff(monkeypatch):
    from daily_bluesky_post import git_commit
    calls = []
    def fake_run(args, **kw):
        calls.append(list(args))
        class R: returncode = 0  # diff なし
        return R()
    monkeypatch.setattr(git_commit.subprocess, "run", fake_run)
    git_commit.commit_posted_logs(date="2026-05-14", slug="x",
                                  bluesky_status="skip", x_status="skip")
    commit_calls = [c for c in calls if len(c) >= 2 and c[1] == "commit"]
    assert commit_calls == []
