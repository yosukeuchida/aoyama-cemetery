import pytest
import respx
import httpx

from daily_bluesky_post import ogp_fetcher

HTML_WITH_OG = """
<!doctype html>
<html><head>
<meta property="og:title" content="大久保 利通 | 青山霊園 偉人録">
<meta property="og:description" content="明治維新三傑のひとり。">
<meta property="og:image" content="https://aoyama-cemetery.pages.dev/_astro/okubo.jpg">
</head><body></body></html>
"""

HTML_NO_IMAGE = """
<!doctype html>
<html><head>
<meta property="og:title" content="星 新一">
<meta property="og:description" content="ショートショートの名手。">
</head></html>
"""


@respx.mock
def test_fetch_returns_all_three_fields():
    respx.get("https://aoyama-cemetery.pages.dev/people/okubo-toshimichi").mock(
        return_value=httpx.Response(200, text=HTML_WITH_OG)
    )
    ogp = ogp_fetcher.fetch("https://aoyama-cemetery.pages.dev/people/okubo-toshimichi")
    assert ogp.title == "大久保 利通 | 青山霊園 偉人録"
    assert ogp.description == "明治維新三傑のひとり。"
    assert ogp.image_url == "https://aoyama-cemetery.pages.dev/_astro/okubo.jpg"


@respx.mock
def test_fetch_handles_missing_image():
    respx.get("https://aoyama-cemetery.pages.dev/people/hoshi-shinichi").mock(
        return_value=httpx.Response(200, text=HTML_NO_IMAGE)
    )
    ogp = ogp_fetcher.fetch("https://aoyama-cemetery.pages.dev/people/hoshi-shinichi")
    assert ogp.image_url is None
    assert ogp.title == "星 新一"


@respx.mock
def test_fetch_returns_empty_on_404():
    respx.get("https://aoyama-cemetery.pages.dev/people/missing").mock(
        return_value=httpx.Response(404)
    )
    ogp = ogp_fetcher.fetch("https://aoyama-cemetery.pages.dev/people/missing")
    assert ogp.title is None
    assert ogp.description is None
    assert ogp.image_url is None


@respx.mock
def test_download_image_bytes():
    respx.get("https://aoyama-cemetery.pages.dev/_astro/okubo.jpg").mock(
        return_value=httpx.Response(
            200,
            content=b"\xff\xd8\xff\xe0fake-jpeg",
            headers={"content-type": "image/jpeg"},
        )
    )
    data, mime = ogp_fetcher.download_image("https://aoyama-cemetery.pages.dev/_astro/okubo.jpg")
    assert data.startswith(b"\xff\xd8")
    assert mime == "image/jpeg"
