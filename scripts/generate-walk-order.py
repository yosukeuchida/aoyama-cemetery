#!/usr/bin/env python3
"""
各散歩ルートの walkOrder を NN-TSP + 2-opt で生成して frontmatter に書き戻す。

stops 順 = 物語順、walkOrder = 歩行効率順 という設計(CLAUDE.md「散歩ルートマップ
の walkOrder」セクション参照)に基づき、map polyline が物語順だと「ぐちゃぐちゃ」に
なる問題を解消する。

使い方:
  python3 scripts/generate-walk-order.py            # 全ルート更新
  python3 scripts/generate-walk-order.py --dry-run  # 計算だけ・書き込みなし

挙動:
  - 各ルートの全 stops の coords を src/content/people/<slug>.md から取得
  - 1 つでも coords 未取得偉人があればルート全体をスキップ(警告)
  - 全 NN-TSP 開始点を試して最短ツアーを選び、さらに 2-opt で改善
  - walkOrder を 1-indexed 配列で frontmatter に上書き(既存値・コメントアウト値を置換、
    無ければ stops の後ろに追加)
  - 本文中の `# walkOrder: [...]` コメントアウト行は active な walkOrder に昇格させる

注意:
  - 経路ラインは効率順だが、Google Maps の徒歩経路 URL(本文中のリンク)は更新しない
    (物語順を残すか効率順に書き換えるかはルートごとに人間判断、本スクリプトは触らない)
  - 本文中の「経路順:」リストも物語順を保持する設計(CLAUDE.md 参照)
"""

import os
import re
import sys
from math import sqrt

import yaml

ROUTES_DIR = "src/content/routes"
PEOPLE_DIR = "src/content/people"

# 緯度 1° ≈ 111km、経度 1° ≈ 91km @ lat 35.66
LAT_PER_DEG_KM = 111.0
LNG_PER_DEG_KM = 91.0


def read_md(path: str):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", content, re.DOTALL)
    if not m:
        return None, None, content
    fm = yaml.safe_load(m.group(1))
    body = m.group(2)
    return fm, body, content


def get_coords(slug: str):
    path = os.path.join(PEOPLE_DIR, f"{slug}.md")
    if not os.path.exists(path):
        return None
    fm, _, _ = read_md(path)
    if not fm or "coords" not in fm:
        return None
    return (fm["coords"]["lat"], fm["coords"]["lng"])


def dist_km(a, b):
    dlat = (a[0] - b[0]) * LAT_PER_DEG_KM
    dlng = (a[1] - b[1]) * LNG_PER_DEG_KM
    return sqrt(dlat * dlat + dlng * dlng)


def tour_length(path, coords):
    return sum(dist_km(coords[path[i]], coords[path[i + 1]]) for i in range(len(path) - 1))


def nn_from(start, coords):
    n = len(coords)
    visited = [False] * n
    path = [start]
    visited[start] = True
    current = start
    for _ in range(n - 1):
        best_next = -1
        best_d = float("inf")
        for nxt in range(n):
            if visited[nxt]:
                continue
            d = dist_km(coords[current], coords[nxt])
            if d < best_d:
                best_d = d
                best_next = nxt
        path.append(best_next)
        visited[best_next] = True
        current = best_next
    return path


def two_opt(path, coords):
    n = len(path)
    best_path = path[:]
    best_len = tour_length(best_path, coords)
    improved = True
    while improved:
        improved = False
        for i in range(1, n - 2):
            for j in range(i + 1, n):
                if j - i == 1:
                    continue
                new_path = best_path[:i] + best_path[i:j][::-1] + best_path[j:]
                new_len = tour_length(new_path, coords)
                if new_len < best_len - 1e-9:
                    best_path = new_path
                    best_len = new_len
                    improved = True
    return best_path, best_len


def optimize(coords):
    n = len(coords)
    best_path = None
    best_len = float("inf")
    for start in range(n):
        path = nn_from(start, coords)
        path, length = two_opt(path, coords)
        if length < best_len:
            best_len = length
            best_path = path
    return best_path, best_len


WALK_ORDER_ACTIVE_RE = re.compile(r"^walkOrder:.*$", re.MULTILINE)
WALK_ORDER_COMMENTED_RE = re.compile(r"^# walkOrder:.*$", re.MULTILINE)


def update_walk_order_in_file(path: str, walk_order):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    walk_str = "[" + ", ".join(map(str, walk_order)) + "]"
    new_line = f"walkOrder: {walk_str}"

    if WALK_ORDER_ACTIVE_RE.search(content):
        content = WALK_ORDER_ACTIVE_RE.sub(new_line, content, count=1)
    elif WALK_ORDER_COMMENTED_RE.search(content):
        content = WALK_ORDER_COMMENTED_RE.sub(new_line, content, count=1)
    else:
        # frontmatter 末尾の --- の前に追加
        parts = content.split("\n---\n", 1)
        if len(parts) == 2:
            # 末尾の改行整形
            head = parts[0].rstrip("\n")
            content = f"{head}\n{new_line}\n---\n{parts[1]}"
        else:
            raise RuntimeError(f"frontmatter 区切りが見つからない: {path}")

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    dry_run = "--dry-run" in sys.argv

    if not os.path.isdir(ROUTES_DIR):
        print(f"ERROR: {ROUTES_DIR} not found. プロジェクトルートで実行してください。", file=sys.stderr)
        sys.exit(1)

    results = []
    for fname in sorted(os.listdir(ROUTES_DIR)):
        if not fname.endswith(".md"):
            continue
        path = os.path.join(ROUTES_DIR, fname)
        fm, _, _ = read_md(path)
        if not fm:
            print(f"SKIP {fname}: frontmatter parse 失敗")
            continue
        stops = fm.get("stops", [])
        if len(stops) < 2:
            print(f"SKIP {fname}: stops が 2 未満")
            continue
        coords = []
        missing = []
        for s in stops:
            c = get_coords(s["slug"])
            if c is None:
                missing.append(s["slug"])
            coords.append(c)
        if missing:
            print(f"SKIP {fname}: coords 未取得 {missing}")
            continue

        old_walk_order = fm.get("walkOrder")
        path_indices, length = optimize(coords)
        walk_order = [i + 1 for i in path_indices]  # 1-indexed

        if old_walk_order == walk_order:
            print(f"= {fname}: walkOrder 変化なし(既に最適){walk_order}")
            continue

        results.append((fname, walk_order, length, old_walk_order))

    print()
    print("=== 更新対象 ===")
    for fname, wo, length, old in results:
        old_str = f" was {old}" if old else ""
        print(f"  {fname}: walkOrder = {wo}{old_str} (約 {length:.2f} km)")

    if dry_run:
        print("\n(dry-run) 書き込みなし。")
        return

    for fname, wo, _, _ in results:
        path = os.path.join(ROUTES_DIR, fname)
        update_walk_order_in_file(path, wo)
        print(f"WROTE {fname}")

    print(f"\ndone: {len(results)} ルート更新。")


if __name__ == "__main__":
    main()
