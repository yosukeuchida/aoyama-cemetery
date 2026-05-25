#!/usr/bin/env python3
"""各 event の Wikipedia 記事から代表画像を取得し、PD 確認後にダウンロード + md frontmatter 更新。

挙動:
1. src/content/events/*.md を走査
2. heroImage 未設定で url(Wikipedia URL)を持つ event について:
   a. Wikipedia pageimages API で記事の代表画像ファイル名を取得
   b. Commons imageinfo API でライセンス確認
   c. PD / CC0 / CC-BY 系 のみ採用、それ以外は SKIP
   d. 600px サムネを src/assets/event-images/<slug>.jpg に保存
   e. event md frontmatter に heroImage / heroImageCaption / heroImageCredit を追加
3. サマリーを出力

ライセンスポリシー(白リスト):
- "Public domain", "PD-*", "PD-Japan-*" など
- "CC0", "CC-PD"
- "CC-BY-X.X", "CC-BY-SA-X.X" (artist crediting 必要)
Wikimedia 由来でも fair use / non-free / unclear は SKIP。
"""
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import yaml

UA = "aoyama-cemetery-event-image-fetcher/1.0 (https://github.com/yosukeuchida/aoyama-cemetery; educational)"
EVENTS_DIR = "src/content/events"
ASSETS_DIR = "src/assets/event-images"
THUMB_WIDTH = 800

ACCEPT_PATTERNS = [
    re.compile(r"public\s*domain", re.I),
    re.compile(r"^pd[-/]", re.I),
    re.compile(r"\bpd[-/]", re.I),
    re.compile(r"^cc0", re.I),
    re.compile(r"^cc[- ]by(-sa)?[- ]?\d", re.I),
]

REJECT_PATTERNS = [
    re.compile(r"fair\s*use", re.I),
    re.compile(r"non[- ]free", re.I),
    re.compile(r"copyright", re.I),
]


def http_get(url, retries=3):
    delay = 2
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                print(f"  429, sleeping {delay}s", file=sys.stderr)
                time.sleep(delay)
                delay *= 2
                continue
            raise
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(delay)
                continue
            raise


def get_title_from_url(url):
    m = re.match(r"https://ja\.wikipedia\.org/wiki/(.+?)(?:#.*)?$", url)
    if not m:
        return None
    return urllib.parse.unquote(m.group(1))


def get_pageimage(title):
    params = {
        "action": "query",
        "titles": title,
        "prop": "pageimages",
        "piprop": "name",
        "format": "json",
        "formatversion": "2",
    }
    url = "https://ja.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    data = json.loads(http_get(url).decode("utf-8"))
    pages = data.get("query", {}).get("pages", [])
    for p in pages:
        if p.get("pageimage"):
            return p["pageimage"]
    return None


ICON_PATTERNS = [
    re.compile(r"Commons[-_]logo", re.I),
    re.compile(r"Wiki(p|m|s)edia[-_]", re.I),
    re.compile(r"Wikisource[-_]logo", re.I),
    re.compile(r"^Flag[-_]of[-_]", re.I),
    re.compile(r"^[A-Za-z]{1,3}\.svg$"),  # 短い国旗 / icon
    re.compile(r"Ambox[-_]", re.I),
    re.compile(r"Question[-_]book", re.I),
    re.compile(r"Stub[-_]icon", re.I),
    re.compile(r"^OOjs[-_]", re.I),
    re.compile(r"^Coat[-_]of[-_]arms", re.I),
    re.compile(r"^Emblem[-_]of[-_]", re.I),
    re.compile(r"^Disambig", re.I),
    re.compile(r"^Symbol[-_]", re.I),
    re.compile(r"^P[a-z]+\.svg$"),
    re.compile(r"loudspeaker", re.I),
    re.compile(r"^Edit[-_]", re.I),
    re.compile(r"^Wiktionary[-_]", re.I),
    re.compile(r"^Crystal[-_]", re.I),
    re.compile(r"Bookend\.svg$", re.I),
    re.compile(r"^Imperial Seal of Japan\.svg$", re.I),
    re.compile(r"^Government Seal of Japan\.svg$", re.I),
    re.compile(r"^Merge", re.I),
]


def is_likely_content_image(filename):
    for p in ICON_PATTERNS:
        if p.search(filename):
            return False
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp"):
        return False
    return True


def get_images_list(title):
    """prop=images: 記事内全画像のリストを取得"""
    params = {
        "action": "query",
        "titles": title,
        "prop": "images",
        "imlimit": "100",
        "format": "json",
        "formatversion": "2",
    }
    url = "https://ja.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    try:
        data = json.loads(http_get(url).decode("utf-8"))
    except Exception:
        return []
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return []
    images = pages[0].get("images", [])
    result = []
    for img in images:
        name = img.get("title", "")
        # "ファイル:XXX" / "File:XXX" の prefix を除去
        for prefix in ("ファイル:", "File:"):
            if name.startswith(prefix):
                name = name[len(prefix):]
                break
        result.append(name)
    return result


def get_best_image(title):
    """pageimages 優先、ダメなら prop=images から最初の content image を選ぶ"""
    pi = get_pageimage(title)
    if pi:
        return pi
    time.sleep(0.3)
    candidates = get_images_list(title)
    for c in candidates:
        if is_likely_content_image(c):
            return c
    return None


def get_image_info(filename):
    """Commons imageinfo (+ ja.wikipedia local fallback)"""
    for endpoint in ("https://commons.wikimedia.org", "https://ja.wikipedia.org"):
        params = {
            "action": "query",
            "titles": f"File:{filename}",
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": str(THUMB_WIDTH),
            "format": "json",
            "formatversion": "2",
        }
        url = endpoint + "/w/api.php?" + urllib.parse.urlencode(params)
        try:
            data = json.loads(http_get(url).decode("utf-8"))
        except Exception as e:
            continue
        pages = data.get("query", {}).get("pages", [])
        for p in pages:
            if "imageinfo" in p:
                info = p["imageinfo"][0]
                ext = info.get("extmetadata", {})
                license_short = strip_html(ext.get("LicenseShortName", {}).get("value", ""))
                artist = strip_html(ext.get("Artist", {}).get("value", ""))
                description = strip_html(ext.get("ImageDescription", {}).get("value", ""))
                object_name = strip_html(ext.get("ObjectName", {}).get("value", ""))
                return {
                    "endpoint": endpoint,
                    "thumb": info.get("thumburl") or info.get("url"),
                    "url": info.get("url"),
                    "license": license_short,
                    "artist": artist,
                    "description": description,
                    "object_name": object_name,
                }
    return None


def strip_html(s):
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    return s.strip()


def license_ok(license_str):
    if not license_str:
        return False
    for r in REJECT_PATTERNS:
        if r.search(license_str):
            return False
    for a in ACCEPT_PATTERNS:
        if a.search(license_str):
            return True
    # 明確に Public domain 系判定できない場合は False(保守的)
    return False


def read_md(path):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", content, re.DOTALL)
    if not m:
        return None, None, content
    return yaml.safe_load(m.group(1)), m.group(2), content


def update_event_md(path, slug, ext, caption, credit):
    """frontmatter の末尾(---の直前)に heroImage 3 行を追加。既存 url 行の直後に挿入する形が望ましい。"""
    with open(path, encoding="utf-8") as f:
        content = f.read()

    # 重複防止
    if re.search(r"^heroImage:", content, re.MULTILINE):
        return False

    insert = (
        f"heroImage: ../../assets/event-images/{slug}{ext}\n"
        f"heroImageCaption: {caption}\n"
        f"heroImageCredit: {credit}\n"
    )

    # url: 行の直後に挿入
    m = re.search(r"^url:.*$", content, re.MULTILINE)
    if m:
        end = m.end()
        new_content = content[: end] + "\n" + insert.rstrip() + content[end:]
    else:
        # フォールバック: 末尾 --- の前に挿入
        parts = content.split("\n---\n", 1)
        if len(parts) == 2:
            new_content = parts[0].rstrip("\n") + "\n" + insert + "---\n" + parts[1]
        else:
            return False

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    return True


def main():
    if not os.path.isdir(EVENTS_DIR):
        print(f"ERROR: {EVENTS_DIR} not found", file=sys.stderr)
        sys.exit(1)
    os.makedirs(ASSETS_DIR, exist_ok=True)

    successes = []
    skipped = []
    errors = []

    for fname in sorted(os.listdir(EVENTS_DIR)):
        if not fname.endswith(".md"):
            continue
        slug = fname[:-3]
        path = os.path.join(EVENTS_DIR, fname)
        fm, _, _ = read_md(path)
        if not fm:
            skipped.append((slug, "no frontmatter"))
            continue
        if fm.get("heroImage"):
            skipped.append((slug, "already has heroImage"))
            continue
        url = fm.get("url")
        if not url or "wikipedia.org" not in url:
            skipped.append((slug, "no Wikipedia URL"))
            continue

        title = get_title_from_url(url)
        if not title:
            skipped.append((slug, "invalid URL"))
            continue

        print(f"[{slug}] {title}")
        try:
            pageimage = get_best_image(title)
            time.sleep(0.4)
            if not pageimage:
                print(f"  no usable image in Wikipedia article")
                skipped.append((slug, "no usable image"))
                continue

            info = get_image_info(pageimage)
            time.sleep(0.4)
            if not info or not info.get("thumb"):
                print(f"  imageinfo not found for {pageimage}")
                skipped.append((slug, f"no imageinfo for {pageimage}"))
                continue

            license_str = info["license"]
            if not license_ok(license_str):
                print(f"  license SKIP: '{license_str}'")
                skipped.append((slug, f"license: {license_str}"))
                continue

            ext = os.path.splitext(pageimage)[1].lower() or ".jpg"
            if ext == ".jpeg":
                ext = ".jpg"
            # SVG は thumb URL が PNG に自動レンダされるので拡張子を .png に変換
            if ext == ".svg":
                ext = ".png"
            # webp/png/jpg/gif すべて許容
            if ext not in (".jpg", ".png", ".gif", ".webp"):
                print(f"  unsupported ext: {ext}")
                skipped.append((slug, f"unsupported ext: {ext}"))
                continue

            out_path = os.path.join(ASSETS_DIR, f"{slug}{ext}")
            data = http_get(info["thumb"])
            with open(out_path, "wb") as f:
                f.write(data)
            time.sleep(0.4)

            caption = info["object_name"] or fm.get("title", slug)
            artist = info["artist"][:80] if info["artist"] else ""
            credit_parts = []
            if artist:
                credit_parts.append(artist)
            credit_parts.append("Wikimedia Commons" if "commons" in info["endpoint"] else "Wikipedia")
            credit_parts.append(license_str)
            credit = " / ".join(credit_parts)
            # YAML 不正回避: " と " 内のコロン等を含む場合は引用が必要 — 全部引用しておく
            caption_yaml = json.dumps(caption, ensure_ascii=False)
            credit_yaml = json.dumps(credit, ensure_ascii=False)

            updated = update_event_md(path, slug, ext, caption_yaml, credit_yaml)
            if updated:
                successes.append((slug, pageimage, license_str, len(data)))
                print(f"  OK ({license_str}, {len(data)} bytes)")
            else:
                errors.append((slug, "md update failed"))
                print(f"  md update failed")
        except Exception as e:
            errors.append((slug, str(e)))
            print(f"  ERROR: {e}", file=sys.stderr)
            time.sleep(1)

    print()
    print("=== Summary ===")
    print(f"Success: {len(successes)}")
    for s, pi, lic, sz in successes:
        print(f"  {s}: {pi} ({lic})")
    print(f"\nSkipped: {len(skipped)}")
    for s, reason in skipped:
        print(f"  {s}: {reason}")
    if errors:
        print(f"\nErrors: {len(errors)}")
        for s, e in errors:
            print(f"  {s}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
