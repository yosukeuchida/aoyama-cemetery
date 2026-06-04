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


def _build_prompt(
    *,
    kind: str,
    url: str,
    anniversary_year: int,
    frontmatter: Dict[str, Any],
    body: str,
    agent_name: str = "aoyama-post-writer",
    fact_checker_name: str = "aoyama-fact-checker",
) -> str:
    fm_yaml = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)
    # body は literal block scalar として安全に埋め込み(各行 2 スペースインデント)
    body_indented = "\n".join("  " + line for line in body.splitlines()) if body else "  (なし)"
    return f"""次の Match を投稿する文を作って、最後に必ず JSON だけを出力してください。

## 入力
kind: {kind}
url: {url}
anniversary_year: {anniversary_year}
frontmatter:
{fm_yaml}
body: |
{body_indented}

## 手順
1. {agent_name} subagent に上記を渡して投稿文を生成する
2. {fact_checker_name} subagent に生成文と frontmatter + body を渡して critique する
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


def _build_regenerate_prompt(
    *,
    kind: str,
    url: str,
    anniversary_year: int,
    frontmatter: Dict[str, Any],
    body: str,
    previous_text: str,
    previous_length: int,
    target_length: int,
    agent_name: str = "aoyama-post-writer",
) -> str:
    fm_yaml = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)
    body_indented = "\n".join("  " + line for line in body.splitlines()) if body else "  (なし)"
    return f"""前回生成した投稿文が {previous_length} graphemes と長すぎた(目標は {target_length} grapheme 以内、Bluesky 300 制限の安全マージン)。
**構成は維持したまま本文を圧縮して再生成**してほしい。

維持すべき構成(削除禁止):
- 1 行目のタイトル行(「【今日この日】◯◯(西暦)」または「【本日の命日】◯◯(西暦-西暦)」)
- 最終行の URL

圧縮対象は本文段落のみ。事実は frontmatter と body の範囲内のみ、トーンは {agent_name} subagent の指示書通り(常体・ストーリー性・現代接続)。

## 前回生成した文(長すぎたもの)
{previous_text}

## 入力
kind: {kind}
url: {url}
anniversary_year: {anniversary_year}
frontmatter:
{fm_yaml}
body: |
{body_indented}

## 手順
1. {agent_name} subagent に上記情報 + 「{target_length} grapheme 以内に圧縮」指示で再生成
2. aoyama-fact-checker subagent で critique
3. critique fail → 再生成 1 回まで
4. それでも fail → status="failed"

## 出力
{{"status": "ok", "post_text": "<再生成された投稿本文>", "attempts": <1または2>}}
または
{{"status": "failed", "attempts": 2, "violations": ["..."], "last_text": "<最後の生成文>"}}
"""


def _run_claude(prompt: str, timeout_sec: int) -> GenerateResult:
    """claude -p subprocess 実行 + JSON 抽出。generate_post / regenerate_shorter 共通。"""
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


def generate_post(
    *,
    kind: str,
    url: str,
    anniversary_year: int,
    frontmatter: Dict[str, Any],
    body: str = "",
    timeout_sec: int = 300,
    agent_name: str = "aoyama-post-writer",
    fact_checker_name: str = "aoyama-fact-checker",
) -> GenerateResult:
    prompt = _build_prompt(
        kind=kind, url=url, anniversary_year=anniversary_year, frontmatter=frontmatter, body=body,
        agent_name=agent_name, fact_checker_name=fact_checker_name,
    )
    return _run_claude(prompt, timeout_sec=timeout_sec)


def regenerate_shorter(
    *,
    kind: str,
    url: str,
    anniversary_year: int,
    frontmatter: Dict[str, Any],
    body: str,
    previous_text: str,
    previous_length: int,
    target_length: int = 280,
    timeout_sec: int = 300,
    agent_name: str = "aoyama-post-writer",
) -> GenerateResult:
    """previous_text が長すぎたので短く再生成。

    previous_text と previous_length を post-writer に feedback して、
    target_length 以内で再生成させる。
    """
    prompt = _build_regenerate_prompt(
        kind=kind, url=url, anniversary_year=anniversary_year,
        frontmatter=frontmatter, body=body,
        previous_text=previous_text, previous_length=previous_length,
        target_length=target_length, agent_name=agent_name,
    )
    return _run_claude(prompt, timeout_sec=timeout_sec)


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
