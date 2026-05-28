"""個人詳細編集画面。coords タブ + 写真タブ。"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from admin.lib import content_io, photo_ops  # noqa: E402
from admin.lib import audit_log  # noqa: E402

PEOPLE_DIR = PROJECT_ROOT / "src/content/people"

# 入力テキストから lat/lng を抽出するパターン
# 1) "35.667, 139.722" / "35.667 139.722" (区切りはカンマまたは空白)
# 2) Google Maps URL の "@<lat>,<lng>,<zoom>z" (右クリック→ここは何?)
# 3) Google Maps URL の "?q=<lat>,<lng>" / "&q=<lat>,<lng>" (共有リンク)
_COORDS_PATTERNS = [
    re.compile(r"@(-?\d+\.\d+),\s*(-?\d+\.\d+)"),       # @lat,lng (URL内)
    re.compile(r"[?&]q=(-?\d+\.\d+),\s*(-?\d+\.\d+)"),  # ?q=lat,lng
    re.compile(r"^\s*(-?\d+\.?\d*)[,\s]+(-?\d+\.?\d*)\s*$"),  # bare lat,lng
]


def parse_coords_input(text: str) -> tuple[float, float] | None:
    """入力文字列から (lat, lng) を抽出する。

    対応形式:
        - "35.667123, 139.722456"
        - "35.667123 139.722456"
        - "https://www.google.com/maps/@35.667,139.722,18z/..."
        - "https://www.google.com/maps?q=35.667,139.722"
    """
    if not text:
        return None
    text = text.strip()
    for pat in _COORDS_PATTERNS:
        m = pat.search(text)
        if m:
            return float(m.group(1)), float(m.group(2))
    return None

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
        col_link, col_clear = st.columns([3, 1])
        col_link.markdown(
            f"[現在値を Google Maps で開く](https://www.google.com/maps?q={current['lat']},{current['lng']})"
        )
        if col_clear.button("🗑️ coords をクリア", type="secondary"):
            content_io.clear_coords(data)
            content_io.save(md_path, data)
            audit_log.log(op="clear_coords", slug=slug)
            st.success("クリアしました")
            st.rerun()
        st.divider()

    st.subheader("座標を入力")
    st.caption(
        "Google Maps で右クリック→「ここは何?」で表示される URL をそのまま貼るか、"
        "`lat, lng` 形式で直接入力してください。"
    )

    raw = st.text_input(
        "lat, lng または Google Maps URL",
        value="",
        key=f"coords_input_{slug}",
        placeholder="例: 35.667123, 139.722456",
    )

    parsed = parse_coords_input(raw)
    if raw and parsed is None:
        st.error("入力から lat/lng を抽出できませんでした。形式を確認してください。")
    elif parsed:
        new_lat, new_lng = round(parsed[0], 6), round(parsed[1], 6)
        st.info(f"📍 解析結果: lat={new_lat}, lng={new_lng}")
        col_save, col_preview = st.columns([1, 3])
        if col_save.button("✅ この座標で保存", type="primary", key=f"save_{slug}"):
            try:
                content_io.set_coords(data, lat=new_lat, lng=new_lng)
                content_io.save(md_path, data)
                audit_log.log(
                    op="set_coords", slug=slug,
                    details={"lat": new_lat, "lng": new_lng},
                )
                st.success(f"保存しました: lat={new_lat}, lng={new_lng}")
                st.cache_data.clear()
                st.rerun()
            except ValueError as e:
                st.error(f"保存失敗: {e}")
        col_preview.markdown(
            f"[Google Maps で位置を確認](https://www.google.com/maps?q={new_lat},{new_lng})"
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
                        audit_log.log(op="delete_photo", slug=slug, details={"file": photo.name})
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
                    audit_log.log(
                        op="add_photo", slug=slug,
                        details={"file": placed.name},
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
