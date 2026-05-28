"""content_io: frontmatter 読み書きの単体テスト"""
import shutil
from pathlib import Path
import pytest

from admin.lib import content_io

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_md(tmp_path):
    """フィクスチャを tmp にコピーして、編集用の Path を返す関数"""
    def _copy(name: str) -> Path:
        src = FIXTURES / name
        dst = tmp_path / name
        shutil.copy(src, dst)
        return dst
    return _copy


def test_round_trip_preserves_content(tmp_md):
    """既存 .md を読んで書き戻すと、frontmatter と本文の意味が保たれる"""
    path = tmp_md("sample_person_with_coords.md")
    original_text = path.read_text(encoding="utf-8")
    data = content_io.load(path)
    content_io.save(path, data)
    after_text = path.read_text(encoding="utf-8")
    # 本文部分(--- 後)は byte 一致
    original_body = original_text.split("---", 2)[2]
    after_body = after_text.split("---", 2)[2]
    assert original_body == after_body
    # frontmatter は YAML パース結果が一致
    assert content_io.load(path).frontmatter == data.frontmatter


def test_set_coords_inserts_after_grave_section(tmp_md):
    """coords を新規挿入すると graveSection の直後に入る"""
    path = tmp_md("sample_person_no_coords.md")
    data = content_io.load(path)
    content_io.set_coords(data, lat=35.667123, lng=139.722456)
    content_io.save(path, data)
    text = path.read_text(encoding="utf-8")
    # graveSection の直後に coords がある
    gs_idx = text.index("graveSection:")
    coords_idx = text.index("coords:")
    desc_idx = text.index("shortDescription:")
    assert gs_idx < coords_idx < desc_idx
    # 値が正しい
    assert "lat: 35.667123" in text
    assert "lng: 139.722456" in text


def test_set_coords_updates_existing(tmp_md):
    """既存の coords を更新するとキー順序が保たれる"""
    path = tmp_md("sample_person_with_coords.md")
    data = content_io.load(path)
    original_keys = list(data.frontmatter.keys())
    content_io.set_coords(data, lat=35.668000, lng=139.723000)
    content_io.save(path, data)
    after = content_io.load(path)
    assert list(after.frontmatter.keys()) == original_keys
    assert after.frontmatter["coords"]["lat"] == 35.668000
    assert after.frontmatter["coords"]["lng"] == 139.723000


def test_clear_coords_preserves_structure(tmp_md):
    """coords を削除しても frontmatter の他キーは保たれる"""
    path = tmp_md("sample_person_with_coords.md")
    data = content_io.load(path)
    content_io.clear_coords(data)
    content_io.save(path, data)
    after = content_io.load(path)
    assert "coords" not in after.frontmatter
    assert after.frontmatter["name"] == "テスト 次郎"
    assert after.frontmatter["graveSection"] == "1種イ99号99側"


def test_set_coords_rejects_out_of_range_lat(tmp_md):
    """範囲外の lat で ValueError"""
    path = tmp_md("sample_person_no_coords.md")
    data = content_io.load(path)
    with pytest.raises(ValueError, match="lat"):
        content_io.set_coords(data, lat=36.0, lng=139.722)


def test_set_coords_rejects_out_of_range_lng(tmp_md):
    """範囲外の lng で ValueError"""
    path = tmp_md("sample_person_no_coords.md")
    data = content_io.load(path)
    with pytest.raises(ValueError, match="lng"):
        content_io.set_coords(data, lat=35.667, lng=140.0)


def test_set_coords_rejects_hidemap_person(tmp_md):
    """hideMap: true 設定済の人物への coords 追加は ValueError"""
    path = tmp_md("sample_person_hidemap.md")
    data = content_io.load(path)
    with pytest.raises(ValueError, match="hideMap"):
        content_io.set_coords(data, lat=35.667, lng=139.722)


def test_load_invalid_yaml_raises(tmp_path):
    """壊れた YAML は明示的なエラーを返す"""
    path = tmp_path / "broken.md"
    path.write_text("---\nname: [unclosed\n---\nbody", encoding="utf-8")
    with pytest.raises(ValueError, match="YAML"):
        content_io.load(path)
