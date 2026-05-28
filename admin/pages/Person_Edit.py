"""個人詳細編集画面。coords タブ + 写真タブ。"""
from __future__ import annotations

import sys
from pathlib import Path

import folium
import streamlit as st
from streamlit_folium import st_folium

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from admin.lib import content_io, photo_ops  # noqa: E402

PEOPLE_DIR = PROJECT_ROOT / "src/content/people"

# 青山霊園中心(本園)
CEMETERY_CENTER = (35.6685, 139.7220)

st.set_page_config(page_title="Person Edit", layout="wide")

slug = st.session_state.get("selected_slug")
if not slug:
    st.warning("偉人が選択されていません。ダッシュボードに戻ってください。")
    if st.button("← ダッシュボードへ"):
        st.switch_page("Dashboard.py")
    st.stop()

md_path = PEOPLE_DIR / f"{slug}.md"
if not md_path.exists():
    st.error(f"偉人ファイルが見つかりません: {md_path}")
    st.stop()

data = content_io.load(md_path)
fm = data.frontmatter

# ---- ヘッダー ----
col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    name = fm.get("name", slug)
    birth = fm.get("birthDate", "")[:4]
    death = fm.get("deathDate", "")[:4]
    grave = fm.get("graveSection", "")
    st.markdown(f"## {name} ({birth}-{death}) / {grave}")
    st.caption(f"slug: `{slug}`")
with col_h2:
    if st.button("← ダッシュボード"):
        st.switch_page("Dashboard.py")

# ---- タブ ----
tab_coords, tab_photos = st.tabs(["📍 coords", "📸 写真"])

# ---- coords タブ ----
with tab_coords:
    if content_io.is_hidemap(data):
        st.warning("この偉人は `hideMap: true` 設定済のため coords は使われません。")
        st.stop()

    current = fm.get("coords")
    if current:
        st.success(f"現在値: lat={current['lat']}, lng={current['lng']}")
        if st.button("🗑️ coords をクリア", type="secondary"):
            content_io.clear_coords(data)
            content_io.save(md_path, data)
            st.success("クリアしました")
            st.rerun()
    else:
        st.info("coords 未設定。下の地図をクリックして座標を選んでください。")

    # 地図
    initial_lat = current["lat"] if current else CEMETERY_CENTER[0]
    initial_lng = current["lng"] if current else CEMETERY_CENTER[1]
    fmap = folium.Map(
        location=[initial_lat, initial_lng],
        zoom_start=19,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
        max_zoom=21,
    )
    # 現在値の赤ピン
    if current:
        folium.Marker(
            [current["lat"], current["lng"]],
            tooltip="現在の coords",
            icon=folium.Icon(color="red"),
        ).add_to(fmap)
    # 他の偉人のピン(参考用、灰色)
    for other_md in PEOPLE_DIR.glob("*.md"):
        if other_md.stem == slug:
            continue
        try:
            other = content_io.load(other_md)
            oc = other.frontmatter.get("coords")
            if oc:
                folium.CircleMarker(
                    [oc["lat"], oc["lng"]],
                    radius=3,
                    color="gray",
                    fill=True,
                    tooltip=other.frontmatter.get("name", other_md.stem),
                ).add_to(fmap)
        except Exception:
            pass

    map_result = st_folium(fmap, height=500, width=None, key=f"map_{slug}")

    # クリック座標
    clicked = map_result.get("last_clicked")
    if clicked:
        new_lat = round(clicked["lat"], 6)
        new_lng = round(clicked["lng"], 6)
        st.info(f"📍 クリック位置: lat={new_lat}, lng={new_lng}")
        col_a, col_b = st.columns(2)
        if col_a.button("✅ この座標で保存", type="primary"):
            try:
                content_io.set_coords(data, lat=new_lat, lng=new_lng)
                content_io.save(md_path, data)
                st.success(f"保存しました: lat={new_lat}, lng={new_lng}")
                st.cache_data.clear()
                st.rerun()
            except ValueError as e:
                st.error(f"保存失敗: {e}")
        col_b.markdown(
            f"[Google Maps で確認](https://www.google.com/maps?q={new_lat},{new_lng})"
        )
