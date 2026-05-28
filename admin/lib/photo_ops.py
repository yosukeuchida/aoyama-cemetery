"""墓写真の配置・列挙・削除を扱うモジュール。

リサイズ・HEIC 変換は scripts/add-grave-photo.sh に委譲する。
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GRAVE_PHOTOS_DIR = PROJECT_ROOT / "src/assets/grave-photos"
SCRIPT = PROJECT_ROOT / "scripts/add-grave-photo.sh"

UNSAFE_CAPTION_CHARS = re.compile(r"[/\\:*?\"<>|\n\r]")


def add_photo(
    *,
    slug: str,
    src: Path,
    date: str,
    caption: str,
) -> Path:
    """写真を追加して配置パスを返す。

    Args:
        slug: 偉人 slug
        src: アップロードされた写真のパス
        date: YYYY-MM-DD
        caption: ファイル名に使うキャプション(必須、空文字不可)

    Raises:
        ValueError: caption に不正文字を含む or date 形式不正 or caption 空
        RuntimeError: bash スクリプトが non-zero exit
    """
    if not caption:
        raise ValueError("caption は必須です")
    if UNSAFE_CAPTION_CHARS.search(caption):
        raise ValueError(f"caption に不正文字が含まれています: {caption!r}")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        raise ValueError(f"date は YYYY-MM-DD 形式: {date!r}")

    cmd = [
        str(SCRIPT), slug, str(src),
        "--date", date,
        "--caption", caption,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"add-grave-photo.sh failed (exit {proc.returncode}):\n"
            f"--- stderr ---\n{proc.stderr}\n"
            f"--- stdout ---\n{proc.stdout}"
        )

    safe_caption = caption.replace(" ", "-")
    expected = GRAVE_PHOTOS_DIR / slug / f"{date}-{safe_caption}.jpg"
    if not expected.exists():
        raise RuntimeError(
            f"スクリプトは成功したが期待ファイルが見つかりません: {expected}\n"
            f"stdout: {proc.stdout}"
        )
    return expected


def list_photos(slug: str) -> list[Path]:
    """slug の墓写真一覧を撮影日昇順で返す。"""
    d = GRAVE_PHOTOS_DIR / slug
    if not d.is_dir():
        return []
    return sorted(d.glob("*.jpg"))


def delete_photo(path: Path) -> None:
    """指定写真を削除。安全のため grave-photos 配下のファイルのみ受け付ける。"""
    resolved = path.resolve()
    if not str(resolved).startswith(str(GRAVE_PHOTOS_DIR.resolve())):
        raise ValueError(f"grave-photos 配下のファイルのみ削除可: {path}")
    resolved.unlink()
