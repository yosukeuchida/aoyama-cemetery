from pathlib import Path
import pytest
from daily_bluesky_post.image_resolver import resolve, prepare_for_upload, X_MEDIA_LIMIT_BYTES

FIXTURES = Path(__file__).parent / "fixtures" / "image_resolver"


def test_person_with_portrait_returns_absolute_path():
    path = resolve("with_portrait", kind="person",
                   people_dir=FIXTURES / "people",
                   events_dir=FIXTURES / "events")
    assert path is not None
    assert path.is_absolute()
    assert path.name == "with_portrait.jpg"
    assert path.exists()


def test_person_without_portrait_returns_none():
    path = resolve("no_portrait", kind="person",
                   people_dir=FIXTURES / "people",
                   events_dir=FIXTURES / "events")
    assert path is None


def test_event_with_hero_returns_absolute_path():
    path = resolve("with_hero", kind="event",
                   people_dir=FIXTURES / "people",
                   events_dir=FIXTURES / "events")
    assert path is not None
    assert path.name == "with_hero.png"


def test_missing_slug_returns_none():
    path = resolve("does_not_exist", kind="person",
                   people_dir=FIXTURES / "people",
                   events_dir=FIXTURES / "events")
    assert path is None


def test_prepare_for_upload_small_returns_original(tmp_path):
    src = FIXTURES / "assets" / "portraits" / "with_portrait.jpg"
    result = prepare_for_upload(src, tmp_dir=tmp_path)
    assert result == src  # 5MB 未満ならそのまま


def test_prepare_for_upload_large_resizes(tmp_path):
    from PIL import Image
    big = tmp_path / "big.jpg"
    # 6 MB を超える画像を生成(2000x2000 ランダム JPEG quality 100)
    Image.new("RGB", (4000, 4000), color="white").save(big, quality=100)
    if big.stat().st_size < X_MEDIA_LIMIT_BYTES:
        pytest.skip("test image not large enough on this platform")
    result = prepare_for_upload(big, tmp_dir=tmp_path)
    assert result != big
    assert result.stat().st_size < X_MEDIA_LIMIT_BYTES
