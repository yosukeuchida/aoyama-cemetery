"""X(旧 Twitter)の weighted length カウンタ。

仕様(2026-06 時点):
- ASCII 範囲 + ラテン文字 = 1 unit / 字
- CJK / Hiragana / Katakana / 全角 = 2 units / 字
- URL は t.co 短縮で 23 units 固定(http/https 問わず)
- 無料投稿の上限は 280 weighted units

twitter-text-python は HTML フォーマッタで weighted length を提供しないため
自前実装に統一(2026-06-04 確認)。
"""
from __future__ import annotations

import re

X_LIMIT = 280
X_SAFE_LIMIT = 270  # 安全マージン 10
URL_WEIGHT = 23  # t.co 短縮後の固定長

_URL_RE = re.compile(r"https?://\S+")


def _is_double_width(ch: str) -> bool:
    """CJK Unified Ideographs / Hiragana / Katakana / 全角記号など 2 units 扱い。"""
    code = ord(ch)
    return (
        0x1100 <= code <= 0x115F  # Hangul Jamo
        or 0x2E80 <= code <= 0x303E  # CJK Radicals / Kangxi / 句読点
        or 0x3041 <= code <= 0x33FF  # ひらがな / カタカナ / CJK 記号
        or 0x3400 <= code <= 0x4DBF  # CJK Ext A
        or 0x4E00 <= code <= 0x9FFF  # CJK Unified
        or 0xA000 <= code <= 0xA4CF  # Yi
        or 0xAC00 <= code <= 0xD7A3  # Hangul Syllables
        or 0xF900 <= code <= 0xFAFF  # CJK Compat
        or 0xFE30 <= code <= 0xFE4F  # CJK Compat Forms
        or 0xFF00 <= code <= 0xFF60  # 全角 ASCII
        or 0xFFE0 <= code <= 0xFFE6  # 全角記号
    )


def x_weighted_length(text: str) -> int:
    total = 0
    pos = 0
    for m in _URL_RE.finditer(text):
        chunk = text[pos:m.start()]
        for ch in chunk:
            total += 2 if _is_double_width(ch) else 1
        total += URL_WEIGHT
        pos = m.end()
    tail = text[pos:]
    for ch in tail:
        total += 2 if _is_double_width(ch) else 1
    return total
