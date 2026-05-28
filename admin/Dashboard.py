"""進捗ダッシュボード(entry point)。

136 名の coords 状態 + 写真枚数 + 最終 commit 日時を一覧表示。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# プロジェクトルートを sys.path に追加(admin.lib をインポートするため)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from admin.lib import content_io, git_ops, photo_ops  # noqa: E402

PEOPLE_DIR = PROJECT_ROOT / "src/content/people"
SCRIPT = PROJECT_ROOT / "scripts/add-grave-photo.sh"
ASTRO_CONFIG = PROJECT_ROOT / "astro.config.mjs"


# ---- ヘルスチェック ----------
def _healthcheck() -> None:
    errors = []
    if not ASTRO_CONFIG.exists():
        errors.append(f"プロジェクトルートが正しくありません: {ASTRO_CONFIG} がない")
    if not PEOPLE_DIR.is_dir() or not list(PEOPLE_DIR.glob("*.md")):
        errors.append(f"偉人 md ファイルが見つかりません: {PEOPLE_DIR}")
    if not SCRIPT.exists() or not os.access(SCRIPT, os.X_OK):
        errors.append(f"add-grave-photo.sh が実行可能ではありません: {SCRIPT}")
    if errors:
        st.error("起動時ヘルスチェック失敗:\n" + "\n".join(f"- {e}" for e in errors))
        st.stop()


# ---- データ収集 ----------
@st.cache_data(ttl=30)
def _collect_rows() -> pd.DataFrame:
    rows = []
    for md in sorted(PEOPLE_DIR.glob("*.md")):
        slug = md.stem
        try:
            data = content_io.load(md)
            fm = data.frontmatter
        except Exception as e:
            rows.append({
                "slug": slug, "name": "(parse error)",
                "coords": "❌", "graveSection": "",
                "photos": 0, "last_commit": "", "_error": str(e),
            })
            continue
        if content_io.is_hidemap(data):
            coords_state = "(hideMap)"
        elif content_io.has_coords(data):
            coords_state = "✅"
        else:
            coords_state = "❌"
        rows.append({
            "slug": slug,
            "name": fm.get("name", ""),
            "coords": coords_state,
            "graveSection": fm.get("graveSection", ""),
            "photos": len(photo_ops.list_photos(slug)),
            "last_commit": (git_ops.last_commit_date(md) or "")[:10],
        })
    return pd.DataFrame(rows)


# ---- メイン ----------
st.set_page_config(page_title="aoyama-cemetery admin", layout="wide")
_healthcheck()

st.title("aoyama-cemetery admin")

df = _collect_rows()

# サマリー
col1, col2, col3, col4 = st.columns(4)
col1.metric("全偉人", len(df))
col2.metric("coords 未取得", int((df["coords"] == "❌").sum()))
col3.metric("写真ゼロ", int((df["photos"] == 0).sum()))
col4.metric("未 commit", git_ops.uncommitted_count())

st.divider()

# フィルタ
fcol1, fcol2, fcol3 = st.columns([2, 1, 1])
name_filter = fcol1.text_input("名前 / slug 部分一致", "")
coords_filter = fcol2.selectbox("coords 状態", ["すべて", "❌ 未取得", "✅ 設定済", "(hideMap)"])
photo_filter = fcol3.checkbox("写真ゼロのみ", value=False)

filtered = df.copy()
if name_filter:
    mask = filtered["name"].str.contains(name_filter, case=False, na=False) | \
           filtered["slug"].str.contains(name_filter, case=False, na=False)
    filtered = filtered[mask]
if coords_filter == "❌ 未取得":
    filtered = filtered[filtered["coords"] == "❌"]
elif coords_filter == "✅ 設定済":
    filtered = filtered[filtered["coords"] == "✅"]
elif coords_filter == "(hideMap)":
    filtered = filtered[filtered["coords"] == "(hideMap)"]
if photo_filter:
    filtered = filtered[filtered["photos"] == 0]

st.caption(f"{len(filtered)} / {len(df)} 件表示")

# 行選択
event = st.dataframe(
    filtered,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
)

if event and event.selection and event.selection.rows:
    selected_idx = event.selection.rows[0]
    selected_slug = filtered.iloc[selected_idx]["slug"]
    st.session_state["selected_slug"] = selected_slug
    st.switch_page("pages/Person_Edit.py")
