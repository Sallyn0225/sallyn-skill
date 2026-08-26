#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Download 小宮果穂 story CSVs (+ 放クライ event stories) from SCTranslationData (GitHub).

Usage:
    python download_corpus.py <tree_json_path> <out_dir>

The tree JSON is fetched from:
    https://api.github.com/repos/ShinyGroup/SCTranslationData/git/trees/master?recursive=1
"""
import json
import os
import sys
import urllib.request
import urllib.parse

BASE = "https://raw.githubusercontent.com/ShinyGroup/SCTranslationData/master/"
API = "https://api.github.com/repos/ShinyGroup/SCTranslationData/git/trees/master?recursive=1"

# Extra 放クライ / Kaho-relevant event stories under 283活动剧情
EXTRA_EVENTS = [
    "data/story/283活动剧情/くつろぎクライマックスガールズ",
    "data/story/283活动剧情/ミッション・コンプリート！",
    "data/story/283活动剧情/アフター・スクール・タイム",
    "data/story/283活动剧情/ワールプールフールガールズ",
    "data/story/283活动剧情/完録、クエストロメリア！ ～サイコロ編～",
]


def get_tree():
    with urllib.request.urlopen(API, timeout=120) as r:
        return json.load(r)


def download(path, out_dir):
    url = BASE + urllib.parse.quote(path)
    rel = os.path.join(out_dir, *path.split("/")[2:])
    os.makedirs(os.path.dirname(rel), exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            data = r.read()
        with open(rel, "wb") as f:
            f.write(data)
        return True
    except Exception as e:
        print(f"FAIL {path}: {e}")
        return False


def main():
    tree = get_tree()
    wanted = []
    for item in tree["tree"]:
        p = item.get("path", "")
        if p.endswith(".csv") and p.startswith("data/story/小宮果穂/"):
            wanted.append(p)
    for ev in EXTRA_EVENTS:
        for item in tree["tree"]:
            p = item.get("path", "")
            if p.endswith(".csv") and p.startswith(ev + "/"):
                wanted.append(p)
    wanted = sorted(set(wanted))
    print(f"Total files to download: {len(wanted)}")
    out_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "references", "sources", "raw_commus",
    )
    ok = 0
    for p in wanted:
        if download(p, out_dir):
            ok += 1
    print(f"Downloaded {ok}/{len(wanted)}")


if __name__ == "__main__":
    main()
