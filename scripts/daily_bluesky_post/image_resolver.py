"""slug + kind から portrait / heroImage の絶対 path を解決し、X media upload 用に整形する。

frontmatter の `portrait` / `heroImage` は md ファイル基準の相対 path で書かれているため、
md の親ディレクトリ + 相対 path で resolve する。
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

import yaml
from PIL import Image

X_MEDIA_LIMIT_BYTES = 5 * 1024 * 1024  # X の image upload 上限(5 MB)
RESIZE_LONG_EDGE = 1600
RESIZE_QUALITY = 85

Kind = Literal["person", "event"]


def resolve(
    slug: str,
    *,
    kind: Kind,
    people_dir: Path,
    events_dir: Path,
) -> Optional[Path]:
    if kind == "person":
        md_path = people_dir / f"{slug}.md"
        fm_key = "portrait"
    else:
        md_path = events_dir / f"{slug}.md"
        fm_key = "heroImage"

    if not md_path.exists():
        return None

    text = md_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    fm = yaml.safe_load(parts[1]) or {}
    rel = fm.get(fm_key)
    if not rel:
        return None

    abs_path = (md_path.parent / rel).resolve()
    if not abs_path.exists():
        return None
    return abs_path


def prepare_for_upload(src: Path, *, tmp_dir: Path) -> Path:
    """5 MB 以下ならそのまま返す。超過なら長辺 1600 / quality 85 で再エンコードして tmp に書き出す。"""
    if src.stat().st_size <= X_MEDIA_LIMIT_BYTES:
        return src

    img = Image.open(src)
    img.thumbnail((RESIZE_LONG_EDGE, RESIZE_LONG_EDGE))
    out = tmp_dir / (src.stem + "_resized.jpg")
    img.convert("RGB").save(out, format="JPEG", quality=RESIZE_QUALITY)
    return out
