"""claude -p subprocess ラッパー。

CLI 実行で Max plan 経路を使い、Anthropic API 課金を避ける。

L0 知見:
- 子プロセスに ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN を継承させない
  (継承すると API key 経路にフォールバックして課金される、biz-radar 事故)
- --allowed-tools は -p より前に置く(variadic flag が prompt を吸う問題、biz-radar 事故)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class GenerateResult:
    status: str  # "ok" | "failed" | "error"
    post_text: str = ""
    attempts: int = 0
    violations: List[str] = field(default_factory=list)
    last_text: str = ""
    error: str = ""


def _claude_bin() -> str:
    return shutil.which("claude") or "claude"


def _build_prompt(*, kind: str, url: str, anniversary_year: int, frontmatter: Dict[str, Any]) -> str:
    fm_yaml = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)
    return f"""次の Match を Bluesky に投稿する文を作って、最後に必ず JSON だけを出力してください。

## 入力
kind: {kind}
url: {url}
anniversary_year: {anniversary_year}
frontmatter:
{fm_yaml}

## 手順
1. aoyama-post-writer subagent に上記を渡して投稿文を生成する
2. aoyama-fact-checker subagent に生成文と frontmatter を渡して critique する
3. critique が fail なら、violations を post-writer に渡して再生成 → 再 critique(リトライは 1 回まで)
4. 2 回目も fail なら status="failed" として終了

## 出力(最終出力は JSON 1 行のみ。前置きやコードフェンス禁止)
成功時:
{{"status": "ok", "post_text": "<投稿本文>", "attempts": <1または2>}}

失敗時:
{{"status": "failed", "attempts": 2, "violations": ["..."], "last_text": "<最後に生成された文>"}}
"""


def _child_env() -> Dict[str, str]:
    """L0 知見: claude -p 子プロセスに Anthropic API key を渡さない"""
    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("ANTHROPIC_AUTH_TOKEN", None)
    return env


def generate_post(
    *,
    kind: str,
    url: str,
    anniversary_year: int,
    frontmatter: Dict[str, Any],
    timeout_sec: int = 180,
) -> GenerateResult:
    prompt = _build_prompt(
        kind=kind, url=url, anniversary_year=anniversary_year, frontmatter=frontmatter,
    )

    # L0 知見: --allowed-tools は -p より前(variadic flag が prompt を吸う問題)
    cmd = [
        _claude_bin(),
        "--allowed-tools", "Agent",
        "-p", prompt,
    ]

    try:
        proc = subprocess.run(
            cmd,
            env=_child_env(),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        msg = f"claude -p timed out after {timeout_sec}s"
        print(f"[claude_runner] error: {msg}", file=sys.stderr)
        return GenerateResult(status="error", error=msg)

    if proc.returncode != 0:
        msg = f"claude exit {proc.returncode}: {proc.stderr[:500]}"
        print(f"[claude_runner] error: {msg}", file=sys.stderr)
        return GenerateResult(status="error", error=msg)

    payload = _extract_json(proc.stdout)
    if payload is None:
        msg = f"JSON not found in output: {proc.stdout[-500:]}"
        print(f"[claude_runner] error: {msg}", file=sys.stderr)
        return GenerateResult(status="error", error=msg)

    status = payload.get("status")
    if status not in ("ok", "failed"):
        msg = f"unknown status in JSON payload: {status!r}"
        print(f"[claude_runner] error: {msg}", file=sys.stderr)
        return GenerateResult(status="error", error=msg)

    return GenerateResult(
        status=status,
        post_text=payload.get("post_text", ""),
        attempts=payload.get("attempts", 1),
        violations=payload.get("violations", []),
        last_text=payload.get("last_text", ""),
    )


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """stdout 末尾から greedy に JSON object を抽出。改行入り pretty-print にも対応。

    1. 末尾の `}` を探し、対応する `{` まで遡って json.loads を試す
    2. parse 失敗時は更にひとつ前の `{` まで遡って再試行
    3. 全 candidate 失敗で None
    """
    end = text.rfind("}")
    if end == -1:
        return None
    # 末尾 `}` 以降は無視
    s = text[: end + 1]
    # 候補となる `{` 位置を後ろから列挙
    starts = []
    pos = s.rfind("{")
    while pos != -1:
        starts.append(pos)
        pos = s.rfind("{", 0, pos)
    for start in starts:
        candidate = s[start : end + 1]
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    return None
