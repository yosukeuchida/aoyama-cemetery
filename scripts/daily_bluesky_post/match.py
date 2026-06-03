"""今日のマッチ判定。

人物: deathDate の月日が today の月日と一致
events: date の月日が today の月日と一致 + personSlugs が非空

並び: 周年数(大きい方)→ event 優先 → slug 辞書順
上限: MAX_POSTS_PER_DAY 件
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml

from daily_bluesky_post.config import MAX_POSTS_PER_DAY, SITE_URL

Kind = Literal["person", "event"]


@dataclass
class Match:
    kind: Kind
    slug: str
    frontmatter: Dict[str, Any]
    url: str
    anniversary_year: int  # 周年数(today.year - origin_year)


def _parse_frontmatter(path: Path) -> Optional[Dict[str, Any]]:
    """`---` で囲まれた YAML frontmatter を返す。なければ None。"""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    return yaml.safe_load(parts[1])


def _to_date(value: Any) -> Optional[date]:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def match_today(today: date, people_dir: Path, events_dir: Path) -> List[Match]:
    matches: List[Match] = []

    # 人物: deathDate 月日一致
    for path in sorted(people_dir.glob("*.md")):
        fm = _parse_frontmatter(path)
        if not fm:
            continue
        d = _to_date(fm.get("deathDate"))
        if d and d.month == today.month and d.day == today.day:
            matches.append(Match(
                kind="person",
                slug=path.stem,
                frontmatter=fm,
                url=f"{SITE_URL}/people/{path.stem}",
                anniversary_year=today.year - d.year,
            ))

    # events: date 月日一致 + personSlugs 非空
    for path in sorted(events_dir.glob("*.md")):
        fm = _parse_frontmatter(path)
        if not fm:
            continue
        if not fm.get("personSlugs"):
            continue
        d = _to_date(fm.get("date"))
        if d and d.month == today.month and d.day == today.day:
            matches.append(Match(
                kind="event",
                slug=path.stem,
                frontmatter=fm,
                url=f"{SITE_URL}/events/{path.stem}",
                anniversary_year=today.year - d.year,
            ))

    # 並び: 周年大きい順 → event 優先 → slug 辞書順
    matches.sort(key=lambda m: (
        -m.anniversary_year,
        0 if m.kind == "event" else 1,
        m.slug,
    ))
    return matches[:MAX_POSTS_PER_DAY]
