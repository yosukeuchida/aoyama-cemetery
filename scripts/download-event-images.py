#!/usr/bin/env python3
"""
Wikimedia Commons から event hero 画像を一括ダウンロード。

保存先: src/assets/event-images/<event-slug>.<ext>
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# 2026-05-26 追加分: A+B グループ偉人の新規 events 8 件
PAIRS = [
    ("1893-06-29-fukushima-yasumasa-tanki-oudan", "Fukushima_Yasumasa.jpg"),
    ("1900-07-04-kawaguchi-ekai-tibet", "Ekai_Kawaguchi_by_Zaida_Ben-Yusuf.jpg"),
    ("1900-07-21-takamine-adrenaline", "Epinephrine.svg"),
    ("1903-06-01-hibiya-koen-kaien", "Hibiya_Park_summer.jpg"),
    ("1909-07-04-akasaka-rikyu-shunko", "2019_Akasaka_Palace_02.jpg"),
    ("1919-03-01-sanichi-dokuritsu-undo", "March_1st_movement.jpg"),
    ("1925-07-13-jokoaishi-kanko", "Joko_Aishi,_Sanko_Library.jpg"),
    ("1940-02-02-saito-takao-hangun-enzetsu", "Saitotakao_1.jpg"),
]

OUT_DIR = "src/assets/event-images"
API = "https://commons.wikimedia.org/w/api.php"
THUMB_WIDTH = 1200
UA = "aoyama-cemetery-event-fetcher/1.0 (https://github.com/yosukeuchida/aoyama-cemetery; educational use)"

os.makedirs(OUT_DIR, exist_ok=True)


def http_get(url: str, retries: int = 5) -> bytes:
    delay = 4
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                print(f"  429, retry in {delay}s...", file=sys.stderr)
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            raise
    raise RuntimeError("retries exhausted")


def get_thumb_url(fname: str) -> str:
    params = {
        "action": "query",
        "titles": f"File:{fname}",
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": str(THUMB_WIDTH),
        "format": "json",
    }
    url = API + "?" + urllib.parse.urlencode(params)
    data = json.loads(http_get(url).decode("utf-8"))
    pages = data["query"]["pages"]
    page = next(iter(pages.values()))
    if "imageinfo" not in page:
        raise RuntimeError(f"no imageinfo for {fname}")
    info = page["imageinfo"][0]
    return info.get("thumburl") or info["url"]


errors = []
for slug, fname in PAIRS:
    ext = os.path.splitext(fname)[1].lower()
    if ext == ".jpeg":
        ext = ".jpg"
    # Wikimedia delivers SVG as PNG via thumbnail URL (iiurlwidth付与時)
    if ext == ".svg":
        ext = ".png"
    out_path = os.path.join(OUT_DIR, f"{slug}{ext}")
    if os.path.exists(out_path):
        print(f"skip (exists): {out_path}")
        continue
    try:
        thumb_url = get_thumb_url(fname)
        time.sleep(0.8)
        data = http_get(thumb_url)
        with open(out_path, "wb") as f:
            f.write(data)
        print(f"ok: {out_path} ({len(data)} bytes)")
        time.sleep(0.8)
    except Exception as e:
        errors.append((slug, fname, str(e)))
        print(f"ERROR {slug}: {e}", file=sys.stderr)
        time.sleep(2)

if errors:
    print(f"\n{len(errors)} errors occurred.", file=sys.stderr)
    for slug, fname, msg in errors:
        print(f"  - {slug} ({fname}): {msg}", file=sys.stderr)
    sys.exit(1)
print(f"\ndone: event images in {OUT_DIR}/")
