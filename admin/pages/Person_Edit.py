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


# ---- 写真タブ ----
with tab_photos:
    photos = photo_ops.list_photos(slug)
    st.subheader(f"既存写真: {len(photos)} 枚")

    if photos:
        for photo in photos:
            cols = st.columns([1, 2, 1])
            with cols[0]:
                st.image(str(photo), width=150)
            with cols[1]:
                st.text(photo.name)
                stat = photo.stat()
                st.caption(f"{stat.st_size // 1024} KB")
            with cols[2]:
                if st.button("🗑️ 削除", key=f"del_{photo.name}"):
                    st.session_state[f"confirm_del_{photo.name}"] = True
                if st.session_state.get(f"confirm_del_{photo.name}"):
                    st.warning(f"{photo.name} を削除しますか?")
                    cc1, cc2 = st.columns(2)
                    if cc1.button("削除実行", key=f"do_del_{photo.name}", type="primary"):
                        photo_ops.delete_photo(photo)
                        del st.session_state[f"confirm_del_{photo.name}"]
                        st.success(f"削除しました: {photo.name}")
                        st.cache_data.clear()
                        st.rerun()
                    if cc2.button("キャンセル", key=f"cancel_del_{photo.name}"):
                        del st.session_state[f"confirm_del_{photo.name}"]
                        st.rerun()
            st.divider()

    st.subheader("新規追加")
    from datetime import date as _date_cls
    import tempfile

    uploaded = st.file_uploader(
        "写真ファイル(複数選択可)",
        type=["jpg", "jpeg", "png", "heic"],
        accept_multiple_files=True,
        key=f"upload_{slug}",
    )
    upload_date = st.date_input("撮影日", value=_date_cls.today(), key=f"date_{slug}")
    upload_caption = st.text_input(
        "caption(ファイル名に使う、空欄なら『墓所』連番自動)",
        value="",
        key=f"caption_{slug}",
    )

    if uploaded and st.button("⬆️ アップロード", type="primary", key=f"do_upload_{slug}"):
        date_str = upload_date.strftime("%Y-%m-%d")
        # caption が空なら自動採番
        if not upload_caption.strip():
            existing_count = len(photo_ops.list_photos(slug))
            captions = [f"墓所-{existing_count + i + 1}" for i in range(len(uploaded))]
        else:
            base = upload_caption.strip().replace(" ", "-")
            captions = [base] if len(uploaded) == 1 else [f"{base}-{i + 1}" for i in range(len(uploaded))]

        results = []
        errors = []
        for upload_file, caption in zip(uploaded, captions):
            try:
                suffix = Path(upload_file.name).suffix.lower() or ".jpg"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(upload_file.getbuffer())
                    tmp_path = Path(tmp.name)
                try:
                    placed = photo_ops.add_photo(
                        slug=slug, src=tmp_path,
                        date=date_str, caption=caption,
                    )
                    results.append(placed)
                finally:
                    tmp_path.unlink(missing_ok=True)
            except Exception as e:
                errors.append((upload_file.name, str(e)))

        if results:
            st.success(f"{len(results)} 枚アップロードしました")
            for p in results:
                st.text(str(p.relative_to(PROJECT_ROOT)))
        if errors:
            for name, msg in errors:
                with st.expander(f"❌ {name}"):
                    st.code(msg)
        if results and not errors:
            st.cache_data.clear()
            st.rerun()
