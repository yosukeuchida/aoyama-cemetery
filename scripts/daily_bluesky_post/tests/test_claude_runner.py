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
    assert "--allowed-tools" in captured_cmd, "L0 知見: --allowed-tools 不在"
    assert "-p" in captured_cmd
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


def test_extract_json_handles_multiline_pretty_print(monkeypatch):
    """改行入り pretty-print JSON も取れる"""
    fake_output = '''Some prefix line
{
  "status": "ok",
  "post_text": "x",
  "attempts": 1
}
'''
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: _run_result(fake_output))
    result = claude_runner.generate_post(
        kind="person", url="https://x/y", anniversary_year=0, frontmatter={},
    )
    assert result.status == "ok"
    assert result.post_text == "x"


def test_extract_json_returns_error_on_no_json(monkeypatch):
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: _run_result("not a json at all"))
    result = claude_runner.generate_post(
        kind="person", url="https://x/y", anniversary_year=0, frontmatter={},
    )
    assert result.status == "error"
    assert "JSON not found" in result.error


def test_generate_post_includes_body_in_prompt(monkeypatch):
    """body 引数が prompt に組み込まれて claude に渡る"""
    captured_prompts = []

    def fake_run(cmd, *a, **kw):
        captured_prompts.append(cmd[-1])  # 最後の引数が prompt(--allowed-tools Agent -p <prompt>)
        return _run_result(json.dumps({"status": "ok", "post_text": "x", "attempts": 1}))

    monkeypatch.setattr("subprocess.run", fake_run)
    claude_runner.generate_post(
        kind="person", url="https://x/y", anniversary_year=0, frontmatter={"name": "X"},
        body="本文の特徴的なフレーズ ABCDEF12345",
    )
    assert "ABCDEF12345" in captured_prompts[0]


def test_regenerate_shorter_passes_previous_text_in_prompt(monkeypatch):
    """regenerate_shorter は previous_text と target_length を prompt に組み込んで claude に渡す"""
    captured_prompts = []

    def fake_run(cmd, *a, **kw):
        captured_prompts.append(cmd[-1])
        return _run_result(json.dumps({"status": "ok", "post_text": "短縮版", "attempts": 1}))

    monkeypatch.setattr("subprocess.run", fake_run)
    result = claude_runner.regenerate_shorter(
        kind="person",
        url="https://x/y",
        anniversary_year=148,
        frontmatter={"name": "X"},
        body="本文",
        previous_text="UNIQUE_PREVIOUS_PHRASE_98765",
        previous_length=350,
        target_length=285,
    )
    assert result.status == "ok"
    assert result.post_text == "短縮版"
    prompt = captured_prompts[0]
    assert "UNIQUE_PREVIOUS_PHRASE_98765" in prompt
    assert "350" in prompt
    assert "285" in prompt


def test_regenerate_prompt_instructs_to_keep_title_and_url(monkeypatch):
    """regenerate prompt が title 行と URL 行の維持を明示すること"""
    captured_prompts = []

    def fake_run(cmd, *a, **kw):
        captured_prompts.append(cmd[-1])  # 最後が prompt
        return _run_result(json.dumps({"status": "ok", "post_text": "x", "attempts": 1}))

    monkeypatch.setattr("subprocess.run", fake_run)

    claude_runner.regenerate_shorter(
        kind="event", url="https://x/y", anniversary_year=148,
        frontmatter={"title": "X"}, body="本文",
        previous_text="long text", previous_length=320, target_length=290,
    )
    prompt = captured_prompts[0]
    assert "タイトル行" in prompt
    assert "URL" in prompt
    assert "削除禁止" in prompt or "維持" in prompt


def test_extract_json_returns_error_on_unknown_status(monkeypatch):
    """旧形式互換削除: status='maybe' のような未知値は error"""
    fake_output = '{"status": "maybe", "post_text": "x"}'
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: _run_result(fake_output))
    result = claude_runner.generate_post(
        kind="person", url="https://x/y", anniversary_year=0, frontmatter={},
    )
    assert result.status == "error"
    assert "unknown status" in result.error


def test_build_prompt_uses_specified_agent_name():
    from daily_bluesky_post.claude_runner import _build_prompt
    p_bluesky = _build_prompt(
        kind="person", url="https://x", anniversary_year=150,
        frontmatter={"name": "テスト"}, body="本文",
        agent_name="aoyama-post-writer",
        fact_checker_name="aoyama-fact-checker",
    )
    p_x = _build_prompt(
        kind="person", url="https://x", anniversary_year=150,
        frontmatter={"name": "テスト"}, body="本文",
        agent_name="aoyama-post-writer-x",
        fact_checker_name="aoyama-fact-checker-x",
    )
    assert "aoyama-post-writer subagent" in p_bluesky
    assert "aoyama-fact-checker subagent" in p_bluesky
    assert "aoyama-post-writer-x subagent" in p_x
    assert "aoyama-fact-checker-x subagent" in p_x


def test_generate_post_passes_agent_name_through(monkeypatch):
    from daily_bluesky_post import claude_runner
    captured = {}
    def fake_run(prompt, timeout_sec):
        captured["prompt"] = prompt
        return claude_runner.GenerateResult(status="ok", post_text="ok")
    monkeypatch.setattr(claude_runner, "_run_claude", fake_run)
    claude_runner.generate_post(
        kind="person", url="https://x", anniversary_year=1,
        frontmatter={}, body="",
        agent_name="aoyama-post-writer-x",
        fact_checker_name="aoyama-fact-checker-x",
    )
    assert "aoyama-post-writer-x" in captured["prompt"]
    assert "aoyama-fact-checker-x" in captured["prompt"]


def test_build_regenerate_prompt_uses_specified_fact_checker():
    from daily_bluesky_post.claude_runner import _build_regenerate_prompt
    p_bluesky = _build_regenerate_prompt(
        kind="person", url="https://x", anniversary_year=1,
        frontmatter={}, body="b",
        previous_text="...", previous_length=320, target_length=290,
    )
    p_x = _build_regenerate_prompt(
        kind="person", url="https://x", anniversary_year=1,
        frontmatter={}, body="b",
        previous_text="...", previous_length=320, target_length=270,
        agent_name="aoyama-post-writer-x",
        fact_checker_name="aoyama-fact-checker-x",
    )
    assert "aoyama-fact-checker subagent" in p_bluesky
    assert "aoyama-fact-checker-x subagent" in p_x
    # Make sure the X variant did NOT leak the bluesky name
    assert "aoyama-fact-checker subagent" not in p_x or "aoyama-fact-checker-x subagent" in p_x  # tolerate substring nesting
    # Stronger: bluesky name should not appear as a standalone token in X variant
    # i.e. no "aoyama-fact-checker " (with trailing space) without -x
    import re
    assert not re.search(r"aoyama-fact-checker(?!-x)", p_x), f"Bluesky fact-checker name leaked in X prompt: {p_x}"


def test_regenerate_shorter_passes_fact_checker_through(monkeypatch):
    from daily_bluesky_post import claude_runner
    captured = {}
    def fake_run(prompt, timeout_sec):
        captured["prompt"] = prompt
        return claude_runner.GenerateResult(status="ok", post_text="ok")
    monkeypatch.setattr(claude_runner, "_run_claude", fake_run)
    claude_runner.regenerate_shorter(
        kind="person", url="https://x", anniversary_year=1,
        frontmatter={}, body="",
        previous_text="...", previous_length=320, target_length=270,
        agent_name="aoyama-post-writer-x",
        fact_checker_name="aoyama-fact-checker-x",
    )
    assert "aoyama-post-writer-x subagent" in captured["prompt"]
    assert "aoyama-fact-checker-x subagent" in captured["prompt"]
