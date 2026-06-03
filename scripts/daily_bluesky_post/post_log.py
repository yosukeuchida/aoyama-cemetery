"""投稿ログ(idempotency 用)。

logs/posted.jsonl に 1 投稿 = 1 行 JSON で append。
launchd の catch-up や手動再実行で同じ (date, slug) を投稿しないために load して check する。
"""
from __future__ import annotations

import fcntl
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, List

# Python 3.9 では Literal を typing から import
from typing import Literal

Kind = Literal["person", "event"]


@dataclass(frozen=True)
class Entry:
    date: date
    slug: str
    kind: Kind
    post_uri: str
    at: datetime  # JST aware

    def to_json_line(self) -> str:
        return json.dumps({
            "date": self.date.isoformat(),
            "slug": self.slug,
            "kind": self.kind,
            "post_uri": self.post_uri,
            "at": self.at.isoformat(timespec="seconds"),
        }, ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: dict) -> "Entry":
        return cls(
            date=date.fromisoformat(d["date"]),
            slug=d["slug"],
            kind=d["kind"],
            post_uri=d["post_uri"],
            at=datetime.fromisoformat(d["at"]),
        )


def load(path: Path) -> List[Entry]:
    if not path.exists():
        return []
    entries: List[Entry] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        entries.append(Entry.from_dict(json.loads(line)))
    return entries


def already_posted(entries: Iterable[Entry], d: date, slug: str) -> bool:
    return any(e.date == d and e.slug == slug for e in entries)


def append(path: Path, entry: Entry) -> None:
    """ファイルロックを取って 1 行 append。

    launchd は通常 singleton 起動だが、手動実行と重なる可能性を排除するため flock を使う。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    line = entry.to_json_line() + "\n"
    with open(path, "ab") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.write(line.encode("utf-8"))
            f.flush()
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
