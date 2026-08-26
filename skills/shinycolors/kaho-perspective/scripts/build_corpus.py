#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build 小宮果穂 corpus from raw_commus CSVs.

Extracts every line spoken by 果穂/小宮果穂 (JP + CN), writes:
- corpus/kaho_lines_full.txt   (tab-separated JP\tCN, one per line)
- corpus/kaho_lines_jp.txt     (JP only)
- corpus/story_stats.json      (line counts per story file)
- corpus/kaho_lines_by_story/  (per-story line files for reading context)
"""
import csv
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "sources")
COMMUS = os.path.join(ROOT, "raw_commus")
OUT = os.path.join(ROOT, "corpus")
BY_STORY = os.path.join(OUT, "kaho_lines_by_story")
os.makedirs(BY_STORY, exist_ok=True)

SPEAKERS = {"果穂", "小宮果穂", "小宫果穗"}


def read_csv_rows(path):
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            with open(path, encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except (UnicodeDecodeError, csv.Error):
            continue
    return []


def main():
    full_lines = []
    stats = {}
    n_files = 0
    for dirpath, _dirs, files in os.walk(COMMUS):
        for fn in sorted(files):
            if not fn.endswith(".csv"):
                continue
            n_files += 1
            p = os.path.join(dirpath, fn)
            rows = read_csv_rows(p)
            story_lines = []
            for r in rows:
                name = (r.get("name") or "").strip()
                text = (r.get("text") or "").strip()
                trans = (r.get("trans") or "").strip()
                if name in SPEAKERS and text:
                    line = text.replace("\n", "\\n")
                    tr = trans.replace("\n", "\\n")
                    full_lines.append(f"{line}\t{tr}")
                    story_lines.append(f"{line}\t{tr}")
            rel = os.path.relpath(p, COMMUS)
            stats[rel] = {"total_rows": len(rows), "kaho_lines": len(story_lines)}
            if story_lines:
                safe = rel.replace("/", "__").replace("\\", "__")
                with open(os.path.join(BY_STORY, safe + ".txt"), "w", encoding="utf-8") as f:
                    f.write("\n".join(story_lines))

    with open(os.path.join(OUT, "kaho_lines_full.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(full_lines))
    with open(os.path.join(OUT, "kaho_lines_jp.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(l.split("\t")[0] for l in full_lines))
    with open(os.path.join(OUT, "story_stats.json"), "w", encoding="utf-8") as f:
        json.dump({"files": n_files, "total_kaho_lines": len(full_lines), "stories": stats},
                  f, ensure_ascii=False, indent=1)

    # summary
    by_dir = {}
    for rel, s in stats.items():
        top = rel.split("/")[0]
        by_dir.setdefault(top, [0, 0])
        by_dir[top][0] += s["total_rows"]
        by_dir[top][1] += s["kaho_lines"]
    print(f"files={n_files} total_kaho_lines={len(full_lines)}")
    for k, v in sorted(by_dir.items()):
        print(f"  {k}: rows={v[0]} kaho_lines={v[1]}")


if __name__ == "__main__":
    main()
