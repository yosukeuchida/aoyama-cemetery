import json
from unittest.mock import MagicMock

from daily_bluesky_post import claude_runner


def _run_result(stdout: str, returncode: int = 0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = ""
    r.returncode = returncode
    return r


def test_generate_post_parses_json_output(monkeypatch):
    fake_output = json.dumps({"status": "ok", "post_text": "【本日の命日】...", "attempts": 1})
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: _run_result(fake_output))
    result = claude_runner.generate_post(
        kind="person",
        url="https://aoyama-cemetery.pages.dev/people/okubo-toshimichi",
        anniversary_year=148,
        frontmatter={"name": "大久保 利通"},
    )
    assert result.status == "ok"
    assert result.post_text.startswith("【本日の命日】")
    assert result.attempts == 1


def test_generate_post_returns_failed_when_critique_rejects(monkeypatch):
    fake_output = json.dumps({
        "status": "failed",
        "attempts": 2,
        "violations": ["frontmatter にない人名"],
        "last_text": "...",
    })
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: _run_result(fake_output))
    result = claude_runner.generate_post(
        kind="person", url="https://x/y", anniversary_year=0, frontmatter={},
    )
    assert result.status == "failed"
    assert "frontmatter" in result.violations[0]


def test_generate_post_strips_anthropic_env(monkeypatch):
    """L0 知見: 子プロセスに ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN を渡さない"""
    captured_env = {}

    def fake_run(*args, **kwargs):
        captured_env.update(kwargs.get("env", {}))
        return _run_result(json.dumps({"status": "ok", "post_text": "x", "attempts": 1}))

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-xxx")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "tok")
    monkeypatch.setattr("subprocess.run", fake_run)

    claude_runner.generate_post(
        kind="person", url="https://x/y", anniversary_year=0, frontmatter={},
    )
    assert "ANTHROPIC_API_KEY" not in captured_env
    assert "ANTHROPIC_AUTH_TOKEN" not in captured_env


def test_command_places_allowed_tools_before_p_flag(monkeypatch):
    """L0 知見: --allowed-tools は -p より前(variadic flag が prompt を吸う問題)"""
    captured_cmd = []

    def fake_run(cmd, *a, **kw):
        captured_cmd.extend(cmd)
        return _run_result(json.dumps({"status": "ok", "post_text": "x", "attempts": 1}))

    monkeypatch.setattr("subprocess.run", fake_run)
    claude_runner.generate_post(
        kind="person", url="https://x/y", anniversary_year=0, frontmatter={},
    )
    if "--allowed-tools" in captured_cmd:
        assert captured_cmd.index("--allowed-tools") < captured_cmd.index("-p")


def test_returncode_nonzero_returns_error_status(monkeypatch):
    """claude exit code 非 0 のときは status='error'"""
    r = MagicMock()
    r.stdout = ""
    r.stderr = "claude crashed"
    r.returncode = 1
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: r)
    result = claude_runner.generate_post(
        kind="person", url="https://x/y", anniversary_year=0, frontmatter={},
    )
    assert result.status == "error"
    assert "claude" in result.error or "exit 1" in result.error


def test_timeout_returns_error_status(monkeypatch):
    import subprocess
    def boom(*a, **kw):
        raise subprocess.TimeoutExpired(cmd="claude", timeout=180)
    monkeypatch.setattr("subprocess.run", boom)
    result = claude_runner.generate_post(
        kind="person", url="https://x/y", anniversary_year=0, frontmatter={},
    )
    assert result.status == "error"
    assert "time" in result.error.lower()
