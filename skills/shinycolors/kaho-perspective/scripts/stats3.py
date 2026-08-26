# -*- coding: utf-8 -*-
"""Round 3: final verification stats."""
import re, os
from collections import Counter

CORPUS_DIR = r"E:\Download\others\agent-test\shinycara-skill\.agents\skills\kaho-perspective\references\sources\corpus"
JP = os.path.join(CORPUS_DIR, "kaho_lines_jp.txt")
BY_STORY = os.path.join(CORPUS_DIR, "kaho_lines_by_story")

with open(JP, "r", encoding="utf-8") as f:
    jp_lines = [l.rstrip("\n") for l in f if l.strip()]

story_map = {}
for fn in os.listdir(BY_STORY):
    if not fn.endswith(".txt"):
        continue
    with open(os.path.join(BY_STORY, fn), "r", encoding="utf-8") as f:
        for l in f:
            l = l.rstrip("\n")
            if l.strip():
                story_map[l.split("\t")[0]] = fn.replace(".csv.txt", "")

def cnt(pat, is_regex=False):
    if is_regex:
        return sum(1 for l in jp_lines if re.search(pat, l))
    return sum(1 for l in jp_lines if pat in l)

def ex(pat, k=6, is_regex=False):
    hits = [l for l in jp_lines if (re.search(pat, l) if is_regex else pat in l)]
    return [(h, story_map.get(h, "?")) for h in hits[:k]]

print("=== 私 (5 lines) context ===")
for l, s in ex("私", 6):
    print(f"[{s}] {l}")

print("\n=== 自分 (19 lines) context ===")
for l, s in ex("自分", 10):
    print(f"[{s}] {l}")

print("\n=== ジャスティス / hero show in-universe ===")
for pat in ["ジャスティス", "ジャスティスⅤ", "ジャスティスファイブ", "スーパースペクタクルビーム", "スペクタクル"]:
    print(f"{pat}: {cnt(pat)}")
for l, s in ex("ジャスティス", 8):
    print(f"[{s}] {l}")

print("\n=== 樹里 addressing ===")
for pat in ["樹里", "樹里さん", "樹里ちゃん", "ジュリ"]:
    print(f"{pat}: {cnt(pat)}")
for l, s in ex("樹里", 6):
    print(f"[{s}] {l}")

print("\n=== ちょこ先輩 lines ===")
for l, s in ex("ちょこ先輩", 5):
    print(f"[{s}] {l}")

print("\n=== っ pattern detail ===")
print(f"えへへっ: {cnt('えへへっ')} / えへへ total: {cnt('えへへ')}")
print(f"はいっ: {cnt('はいっ')}")
print(f"わぁっ: {cnt('わぁっ')} / わぁ: {cnt('わぁ')}")
print(f"あっ: {cnt('あっ')}")
print(f"えっ: {cnt('えっ')}")
print(f"あたしっ: {cnt('あたしっ')}")
print(f"スッゴく: {cnt('スッゴく')}")
print(f"スゴい/スゴく: {cnt('スゴい')},{cnt('スゴく')}")

print("\n=== クライマックス/放クラ self-identification ===")
for pat in ["放課後クライマックスガールズ", "クライマックス", "放クラ"]:
    print(f"{pat}: {cnt(pat)}")
for l, s in ex("放課後クライマックスガールズの", 5):
    print(f"[{s}] {l}")

print("\n=== ごとく/ように hero metaphor ===")
for pat in ["みたいな", "みたいに", "のように"]:
    print(f"{pat}: {cnt(pat)}")
for l, s in ex("ヒーローみたい", 6):
    print(f"[{s}] {l}")

print("\n=== お願いします/ください request forms ===")
for pat in ["ください", "お願いします", "くださいっ", "ください！"]:
    print(f"{pat}: {cnt(pat)}")

print("\n=== ですっ/ますっ line-final breakdown ===")
for pat in [r"ですっ$", r"ますっ$", r"ですっ！$", r"ますっ！$", r"です！$", r"ます！$"]:
    print(f"{pat}: {cnt(pat, True)}")

print("\n=== ！ count total ===")
ex_total = sum(l.count("！") + l.count("!") for l in jp_lines)
print(f"total ！ chars: {ex_total}, avg per line: {ex_total/len(jp_lines):.2f}")

print("\n=== …… / … count ===")
dots = sum(1 for l in jp_lines if "…" in l)
print(f"lines with …: {dots}")

print("\n=== 決めポーズ example ===")
for l, s in ex("決め", 6):
    print(f"[{s}] {l}")

print("\n=== 変身 example ===")
for l, s in ex("変身", 6):
    print(f"[{s}] {l}")

print("\n=== やった/やったー example ===")
for l, s in ex("やった", 6):
    print(f"[{s}] {l}")

print("\n=== 正義 lines full ===")
for l, s in ex("正義", 10):
    print(f"[{s}] {l}")

print("\n=== カレー lines ===")
for l, s in ex("カレー", 6):
    print(f"[{s}] {l}")

print("\n=== マメ丸 lines ===")
for l, s in ex("マメ丸", 5):
    print(f"[{s}] {l}")
