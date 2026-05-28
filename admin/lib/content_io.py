"""frontmatter (YAML) と本文を round-trip で読み書きするモジュール。

ruamel.yaml の CommentedMap で順序とコメントを保持する。
"""
from __future__ import annotations

import io
import os
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

# zod schema と同じ範囲(src/content.config.ts:18-21)
LAT_MIN, LAT_MAX = 35.66, 35.68
LNG_MIN, LNG_MAX = 139.71, 139.73


@dataclass
class PersonMD:
    path: Path
    frontmatter: CommentedMap
    body: str


def _yaml() -> YAML:
    y = YAML(typ="rt")
    y.preserve_quotes = True
    y.indent(mapping=2, sequence=4, offset=2)
    y.width = 4096  # 長い文字列を改行しない
    return y


def load(path: Path) -> PersonMD:
    """frontmatter と本文を読む。"""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"frontmatter フェンスが見つかりません: {path}")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"frontmatter フェンスが閉じていません: {path}")
    raw_fm = parts[1]
    body = parts[2]
    try:
        fm = _yaml().load(raw_fm)
    except Exception as e:
        raise ValueError(f"YAML パース失敗 ({path}): {e}") from e
    if not isinstance(fm, CommentedMap):
        raise ValueError(f"frontmatter がマップではありません: {path}")
    return PersonMD(path=path, frontmatter=fm, body=body)


def save(path: Path, data: PersonMD) -> None:
    """frontmatter + 本文を atomic に書き戻す。"""
    buf = io.StringIO()
    _yaml().dump(data.frontmatter, buf)
    new_text = "---\n" + buf.getvalue() + "---" + data.body
    tmp = path.with_suffix(f"{path.suffix}.{os.getpid()}.tmp")
    tmp.write_text(new_text, encoding="utf-8")
    tmp.replace(path)


def set_coords(data: PersonMD, *, lat: float, lng: float) -> None:
    """coords を設定 / 更新。graveSection の直後に挿入する。"""
    try:
        lat = float(lat)
        lng = float(lng)
    except (TypeError, ValueError) as e:
        raise ValueError(f"lat/lng は数値である必要があります: lat={lat!r}, lng={lng!r}") from e
    if not (LAT_MIN <= lat <= LAT_MAX):
        raise ValueError(f"lat が範囲外({LAT_MIN}-{LAT_MAX}): {lat}")
    if not (LNG_MIN <= lng <= LNG_MAX):
        raise ValueError(f"lng が範囲外({LNG_MIN}-{LNG_MAX}): {lng}")
    if data.frontmatter.get("hideMap") is True:
        raise ValueError("hideMap: true の人物には coords を設定できません")

    fm = data.frontmatter
    coords_map = CommentedMap()
    coords_map["lat"] = round(lat, 6)
    coords_map["lng"] = round(lng, 6)

    if "coords" in fm:
        fm["coords"] = coords_map
        return

    # 新規挿入: graveSection の直後に置く
    keys = list(fm.keys())
    if "graveSection" in keys:
        insert_pos = keys.index("graveSection") + 1
    elif "shortDescription" in keys:
        insert_pos = keys.index("shortDescription")
    else:
        insert_pos = len(keys)
    fm.insert(insert_pos, "coords", coords_map)


def clear_coords(data: PersonMD) -> None:
    """coords を削除。無ければ no-op。"""
    if "coords" in data.frontmatter:
        del data.frontmatter["coords"]


def has_coords(data: PersonMD) -> bool:
    return "coords" in data.frontmatter


def is_hidemap(data: PersonMD) -> bool:
    return data.frontmatter.get("hideMap") is True
