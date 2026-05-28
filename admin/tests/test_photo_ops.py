"""photo_ops: add-grave-photo.sh のラッパーテスト(subprocess は本物実行)"""
import shutil
from pathlib import Path
import pytest

from admin.lib import photo_ops

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_SLUG = "okubo-toshimichi"  # 必ず存在する slug
TEST_DATE = "1999-12-30"  # 既存と衝突しない日付


@pytest.fixture
def test_image(tmp_path):
    """既存リポ内の photo を 1 枚拾って tmp に複製する。
    リポに 1 枚も無い場合は最小限の有効 JPEG バイト列で代用。
    """
    existing = next(
        (PROJECT_ROOT / "src/assets/grave-photos").rglob("*.jpg"),
        None,
    )
    target = tmp_path / "src.jpg"
    if existing:
        shutil.copy(existing, target)
    else:
        # macOS HEIC からの fallback
        sample = Path("/System/Library/CoreServices/DefaultDesktop.heic")
        if sample.exists():
            import subprocess
            subprocess.run(
                ["sips", "-s", "format", "jpeg", "-z", "100", "100",
                 str(sample), "--out", str(target)],
                check=True, capture_output=True,
            )
        else:
            pytest.skip("テスト用画像が用意できない")
    return target


@pytest.fixture
def cleanup_artifacts():
    """テスト後に作成されたファイルを片付ける"""
    created = []
    yield created
    for path in created:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def test_add_photo_basic(test_image, cleanup_artifacts):
    """正常系: 写真が src/assets/grave-photos/<slug>/ に配置される"""
    result = photo_ops.add_photo(
        slug=TEST_SLUG,
        src=test_image,
        date=TEST_DATE,
        caption="test-photo-ops",
    )
    cleanup_artifacts.append(result)
    expected = PROJECT_ROOT / f"src/assets/grave-photos/{TEST_SLUG}/{TEST_DATE}-test-photo-ops.jpg"
    assert result == expected
    assert expected.exists()


def test_add_photo_rejects_slash_in_caption(test_image):
    """caption にスラッシュが含まれると ValueError(ディレクトリトラバーサル防止)"""
    with pytest.raises(ValueError, match="caption"):
        photo_ops.add_photo(
            slug=TEST_SLUG,
            src=test_image,
            date=TEST_DATE,
            caption="bad/path",
        )


def test_add_photo_rejects_invalid_slug(test_image):
    """存在しない slug で RuntimeError(bash スクリプトの exit 1 を補足)"""
    with pytest.raises(RuntimeError):
        photo_ops.add_photo(
            slug="nonexistent-person-xyz",
            src=test_image,
            date=TEST_DATE,
            caption="x",
        )


def test_list_photos_returns_existing_files():
    """list_photos: 既存写真ディレクトリのファイル一覧を返す"""
    photos = photo_ops.list_photos(TEST_SLUG)
    assert isinstance(photos, list)
    for p in photos:
        assert isinstance(p, Path)
        assert p.exists()


def test_list_photos_empty_for_no_dir():
    """ディレクトリが無い slug は空リスト"""
    photos = photo_ops.list_photos("nonexistent-person-xyz")
    assert photos == []


def test_delete_photo(test_image, cleanup_artifacts):
    """delete_photo: ファイル削除"""
    placed = photo_ops.add_photo(
        slug=TEST_SLUG,
        src=test_image,
        date=TEST_DATE,
        caption="test-delete",
    )
    cleanup_artifacts.append(placed)
    assert placed.exists()
    photo_ops.delete_photo(placed)
    assert not placed.exists()


def test_delete_photo_rejects_outside_grave_photos(tmp_path):
    """grave-photos 外のパスは ValueError(誤削除防止)"""
    outside = tmp_path / "outside.jpg"
    outside.write_bytes(b"x")
    with pytest.raises(ValueError, match="grave-photos"):
        photo_ops.delete_photo(outside)
    # ファイルは消えていない
    assert outside.exists()


def test_delete_photo_rejects_sibling_directory_prefix(tmp_path, monkeypatch):
    """旧 startswith 実装で漏れていた sibling ディレクトリ名のケースを明示的に防ぐ。
    GRAVE_PHOTOS_DIR と同名 prefix のディレクトリは別物として拒否する。
    """
    # /tmp/xxx/grave-photos と /tmp/xxx/grave-photos-evil の関係を再現
    legit = tmp_path / "grave-photos"
    legit.mkdir()
    evil = tmp_path / "grave-photos-evil"
    evil.mkdir()
    bad_file = evil / "x.jpg"
    bad_file.write_bytes(b"x")
    monkeypatch.setattr(photo_ops, "GRAVE_PHOTOS_DIR", legit)
    with pytest.raises(ValueError, match="grave-photos"):
        photo_ops.delete_photo(bad_file)
    assert bad_file.exists()
