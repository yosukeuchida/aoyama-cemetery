#!/usr/bin/env python3
"""
Wikimedia Commons から偉人の肖像画像を一括ダウンロード。

Special:FilePath はレート制限が厳しいので、
MediaWiki API 経由でサムネイル URL を取得し、CDN (upload.wikimedia.org) から取得する。

保存先: src/assets/portraits/<slug>.jpg
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

PAIRS = [
    ("akiyama-yoshifuru", "Akiyama_Yoshifuru.jpg"),
    ("goto-shinpei", "Shimpei_Gotō.jpg"),
    ("hamaguchi-osachi", "HAMAGUCHI_Osachi.jpg"),
    ("hirose-takeo", "Hirose_Takeo.jpg"),
    ("inoue-junnosuke", "Junnosuke_Inoue.jpg"),
    ("inukai-tsuyoshi", "Inukai_Tsuyoshi.jpg"),
    ("kato-takaaki", "Takaaki_Kato_suit.jpg"),
    ("kato-tomosaburo", "Admiral_Kato_Tomosaburo.jpg"),
    ("kitasato-shibasaburo", "Shibasaburō_Kitasato_1910.jpg"),
    ("komura-jutaro", "Portrait_of_Komura_Jutaro.jpg"),
    ("kunikida-doppo", "Doppo_Kunikida.jpg"),
    ("kuroda-kiyotaka", "Kiyotaka_Kuroda_formal.jpg"),
    ("makino-nobuaki", "Nobuaki_Makino_in_later_years.jpg"),
    ("matsukata-masayoshi", "4_MatsukataM.jpg"),
    ("matsuoka-yosuke", "Yohsuke_matsuoka1932.jpg"),
    ("mikimoto-kokichi", "MIKIMOTO_Kokichi.jpg"),
    ("mori-arinori", "Arinori_Mori_2.jpg"),
    ("nakae-chomin", "Nakae_Chomin_2.JPG"),
    ("nishi-amane", "Nishi_Amane,_supervisor_of_the_Tokyo_Normal_School.jpg"),
    ("nogi-maresuke", "Maresuke_Nogi,_近世名士写真_其1_-_Photo_only.jpg"),
    ("otori-keisuke", "Otori_Keisuke.jpg"),
    ("ozaki-koyo", "Koyo_Ozaki.jpg"),
    ("saito-mokichi", "Mokichi_Saito.1892.jpg"),
    ("sano-tsunetami", "Sano_Tsunetami.jpg"),
    ("shiga-naoya", "Shiga_Naoya_1938.jpg"),
    ("tanaka-hisashige", "TanakaHisashige.jpg"),
    ("ueki-emori", "Emori_Ueki.JPG"),
    ("yamamoto-gonbee", "Gonbee_Yamamoto.jpg"),
]

OUT_DIR = "src/assets/portraits"
API = "https://commons.wikimedia.org/w/api.php"
THUMB_WIDTH = 600  # 表示は max 280px、retina 用に 600px 取得
UA = "aoyama-cemetery-portrait-fetcher/1.1 (https://github.com/yosukeuchida/aoyama-cemetery; educational use)"

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
        "iiprop": "url",
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
print(f"\ndone: portraits in {OUT_DIR}/")
