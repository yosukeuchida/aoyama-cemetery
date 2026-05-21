#!/usr/bin/env python3
"""
全偉人の Google Maps embed iframe POI 着地を検証するスクリプト。

使い方:
    python3 scripts/verify-map-pois.py

検出ロジック:
- 偉人ごとに src/content/people/*.md を読み、frontmatter から query を決定
  - hideMap: true   → 検証スキップ
  - coords あり     → 検証スキップ(座標ベース)
  - mapQuery あり   → mapQuery を使う
  - 何もなし        → デフォルト "{name}の墓 青山霊園"
- embed iframe URL を fetch して以下を判定
  - spotlit パターン: 固有 POI に着地 → ✅ OK
  - categorical-search: 複数候補(POI 未着地)→ ⚠️ check
  - 着地座標が青山霊園マスター POI (35.6656277, 139.7220659) → ⚠️ generic POI
"""

import urllib.request
import urllib.parse
import re
import time
import sys
from pathlib import Path

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
AOYAMA_MASTER_LAT = 35.6656277
AOYAMA_MASTER_LNG = 139.7220659


def parse_frontmatter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" not in line or line.startswith(" "):
            continue
        k, _, v = line.partition(":")
        fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm


def check_poi(query: str) -> dict:
    qe = urllib.parse.quote(query)
    url = f"https://maps.google.com/maps?q={qe}&z=18&output=embed"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ja"})
    resp = urllib.request.urlopen(req, timeout=15)
    html = resp.read().decode("utf-8", errors="replace")
    spotlit = '"spotlit"' in html
    categorical = '"categorical-search-results-injection"' in html
    poi_match = re.search(
        r'\["0x[0-9a-f]+:0x[0-9a-f]+","([^"]+)",\[(35\.[\d.]+),(139\.[\d.]+)\]', html
    )
    poi_label, lat, lng = None, None, None
    if poi_match:
        poi_label = poi_match.group(1)
        lat = float(poi_match.group(2))
        lng = float(poi_match.group(3))
    is_master = (
        lat is not None
        and abs(lat - AOYAMA_MASTER_LAT) < 1e-6
        and abs(lng - AOYAMA_MASTER_LNG) < 1e-6
    )
    if is_master:
        verdict = "GENERIC_POI"
    elif spotlit:
        verdict = "OK"
    elif categorical:
        verdict = "CATEGORICAL"
    else:
        verdict = "UNKNOWN"
    return {
        "verdict": verdict,
        "poi": poi_label,
        "lat": lat,
        "lng": lng,
    }


def main():
    repo = Path(__file__).resolve().parent.parent
    md_dir = repo / "src" / "content" / "people"
    results = []
    for md in sorted(md_dir.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        name = fm.get("name", "").replace(" ", "")
        slug = md.stem
        if fm.get("hideMap") == "true":
            results.append((slug, name, "SKIP(hideMap)", "", "", ""))
            continue
        if "coords:" in text:
            results.append((slug, name, "SKIP(coords)", "", "", ""))
            continue
        query = fm.get("mapQuery") or f"{name}の墓 青山霊園"
        try:
            r = check_poi(query)
            results.append(
                (slug, name, r["verdict"], r["poi"] or "", r["lat"] or "", r["lng"] or "")
            )
        except Exception as e:
            results.append((slug, name, f"ERR:{e}", "", "", ""))
        time.sleep(0.3)

    print(f"{'slug':<28} {'name':<10} {'verdict':<14} {'poi':<40} {'coords'}")
    print("-" * 120)
    issues = 0
    for slug, name, verdict, poi, lat, lng in results:
        if verdict not in ("OK", "SKIP(hideMap)", "SKIP(coords)"):
            issues += 1
        coords = f"{lat},{lng}" if lat else ""
        print(f"{slug:<28} {name:<10} {verdict:<14} {str(poi)[:38]:<40} {coords}")
    print()
    if issues:
        print(f"⚠️  {issues} 件の要対応(CATEGORICAL/GENERIC_POI/UNKNOWN)があります。", file=sys.stderr)
        print("   対応: 該当偉人の md に mapQuery / coords / hideMap のいずれかを設定してください。")
        sys.exit(1)
    else:
        print("✅ 全偉人で POI が正常に着地しています。")


if __name__ == "__main__":
    main()
