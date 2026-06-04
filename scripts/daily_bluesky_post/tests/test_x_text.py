from daily_bluesky_post.x_text import x_weighted_length, X_LIMIT, X_SAFE_LIMIT


def test_ascii_only_one_per_char():
    assert x_weighted_length("hello world") == len("hello world")


def test_japanese_two_per_char():
    # 日本語 1 字 = 2 weighted units
    assert x_weighted_length("青山霊園") == 8


def test_url_counted_as_23_units():
    # URL は t.co 短縮で 23 units
    text = "see https://aoyama-cemetery.pages.dev/people/okubo-toshimichi end"
    # "see " (4) + URL(23) + " end" (4) = 31
    assert x_weighted_length(text) == 31


def test_japanese_with_url_and_hashtag():
    # 手カウント:
    # 青(2)+山(2)+霊(2)+園(2) = 8
    # " " (1)
    # URL → 23
    # " " (1)
    # "#"(1) + 明(2) + 治(2) + 維(2) + 新(2) = 9
    # 合計: 8 + 1 + 23 + 1 + 9 = 42
    # (計画書コメントの 43 は誤カウント: "#明治維新" は # が ASCII 1unit + 漢字 4 字×2 = 9 unit)
    text = "青山霊園 https://aoyama-cemetery.pages.dev/people/x #明治維新"
    assert x_weighted_length(text) == 42


def test_limit_constants():
    assert X_LIMIT == 280
    assert X_SAFE_LIMIT == 270  # 安全マージン 10
