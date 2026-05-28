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
from admin.lib import audit_log, publish  # noqa: E402


def _publish(file_path: Path, message: str) -> None:
    """保存後の自動 push を実行して結果を UI に表示する共通ヘルパー。

    st.rerun() で画面が即再描画されても結果が見えるよう、永続するメッセージは
    session_state に積んでヘッダ直後で表示する。
    """
    result = publish.publish(file_path, message)
    icon = "✅" if result.ok else "❌"
    st.toast(f"{icon} {result.message}", icon=icon)
    # rerun を生き残らせるためにバナー用 session_state にも積む
    banner = st.session_state.setdefault("publish_banner", [])
    banner.append((result.ok, result.message))


def _thumb_data_uri(path: Path, max_px: int = 300) -> str:
    """ローカル画像を縮小して base64 data URI 化する。

    st.image にローカルパスを渡すと Streamlit の media file 配信経由になり、
    環境によってサムネイルが表示されないことがあるため、HTML img に直接埋め込む。
    """
    from io import BytesIO
    import base64
    from PIL import Image, ImageOps

    img = Image.open(path)
    # iPhone 等の EXIF orientation を適用(ブラウザ/Astro は尊重するが PIL は無視するため)
    img = ImageOps.exif_transpose(img)
    img.thumbnail((max_px, max_px))
    buf = BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=80)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


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

# 直前の publish 結果(rerun を超えて表示するためのバナー)
banner = st.session_state.pop("publish_banner", [])
for ok, msg in banner:
    (st.success if ok else st.error)(msg)

# ---- タブ ----
tab_coords, tab_photos, tab_fm = st.tabs(["📍 coords", "📸 写真", "📝 frontmatter"])

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
            _publish(md_path, f"feat(people): {slug} coords 削除")
            st.rerun()
        st.divider()

    st.subheader("座標を入力")
    st.caption(
        "Google Maps で右クリック→「ここは何?」で表示される URL をそのまま貼るか、"
        "`lat, lng` 形式で直接入力してください。"
    )

    st.link_button(
        "🛰️ 青山霊園を Google Maps で開く(別タブ・航空写真)",
        "https://www.google.com/maps/place/%E9%9D%92%E5%B1%B1%E9%9C%8A%E5%9C%92/@35.6685,139.7220,18z/data=!3m1!1e3",
    )

    raw = st.text_input(
        "lat, lng または Google Maps URL",
        value="",
        key=f"coords_input_{slug}",
        placeholder="例: 35.667123, 139.722456",
    )

    parsed = parse_coords_input(raw)
    new_lat = new_lng = None
    if raw and parsed is None:
        st.error("入力から lat/lng を抽出できませんでした。形式を確認してください。")
    elif parsed:
        new_lat, new_lng = round(parsed[0], 6), round(parsed[1], 6)
        st.info(f"📍 解析結果: lat={new_lat}, lng={new_lng}")
        st.markdown(
            f"[Google Maps で位置を確認](https://www.google.com/maps?q={new_lat},{new_lng})"
        )

    if st.button("💾 保存する", type="primary", key=f"save_{slug}"):
        if new_lat is None or new_lng is None:
            st.error("有効な lat, lng を入力してから保存してください。")
        else:
            try:
                content_io.set_coords(data, lat=new_lat, lng=new_lng)
                content_io.save(md_path, data)
                audit_log.log(
                    op="set_coords", slug=slug,
                    details={"lat": new_lat, "lng": new_lng},
                )
                st.success(f"保存しました: lat={new_lat}, lng={new_lng}")
                _publish(md_path, f"feat(people): {slug} coords 更新 ({new_lat}, {new_lng})")
                st.cache_data.clear()
                st.rerun()
            except ValueError as e:
                st.error(f"保存失敗: {e}")


# ---- 写真タブ ----
with tab_photos:
    photos = photo_ops.list_photos(slug)
    st.subheader(f"既存写真: {len(photos)} 枚")

    if photos:
        for photo in photos:
            cols = st.columns([1, 2, 1])
            with cols[0]:
                st.markdown(
                    f'<img src="{_thumb_data_uri(photo)}" width="150" style="border-radius:4px;">',
                    unsafe_allow_html=True,
                )
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
                        deleted_path = photo  # publish 用に path を保存
                        photo_ops.delete_photo(photo)
                        audit_log.log(op="delete_photo", slug=slug, details={"file": photo.name})
                        del st.session_state[f"confirm_del_{photo.name}"]
                        st.success(f"削除しました: {photo.name}")
                        _publish(deleted_path, f"feat(people): {slug} 墓写真削除 ({deleted_path.name})")
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
        # 成功した写真を 1 枚ずつ commit + push
        for placed in results:
            _publish(placed, f"feat(people): {slug} 墓写真追加 ({placed.name})")
        if results and not errors:
            st.cache_data.clear()
            st.rerun()


# ---- frontmatter タブ ----
with tab_fm:
    st.subheader("frontmatter を YAML で編集")
    st.caption(
        "ファイル全体の frontmatter(--- で囲まれた YAML 部分)を直接編集できます。"
        "本文は変更されません。保存後は `npm run build` で zod schema 整合を確認してください。"
    )
    st.warning(
        "⚠️ raw YAML 編集です。インデント・引用符・コロンに気をつけて。"
        "壊れた YAML を保存しようとすると拒否されます。"
    )

    current_yaml = content_io.dump_frontmatter(data)
    edited_yaml = st.text_area(
        "frontmatter (YAML)",
        value=current_yaml,
        height=600,
        key=f"fm_text_{slug}",
    )

    col_save_fm, col_reset = st.columns([1, 3])
    if col_save_fm.button("✅ frontmatter を保存", type="primary", key=f"save_fm_{slug}"):
        if edited_yaml == current_yaml:
            st.info("変更がありません。")
        else:
            try:
                content_io.replace_frontmatter(data, edited_yaml)
                content_io.save(md_path, data)
                audit_log.log(op="replace_frontmatter", slug=slug)
                st.success("保存しました。")
                _publish(md_path, f"feat(people): {slug} frontmatter 更新")
                st.cache_data.clear()
                st.rerun()
            except ValueError as e:
                st.error(f"保存失敗: {e}")
    if col_reset.button("🔄 現在の内容に戻す", key=f"reset_fm_{slug}"):
        st.rerun()
