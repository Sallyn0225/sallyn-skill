# -*- coding: utf-8 -*-
"""Round 2: deeper pattern analysis for Kaho."""
import re, os
from collections import Counter

CORPUS_DIR = r"E:\Download\others\agent-test\shinycara-skill\.agents\skills\kaho-perspective\references\sources\corpus"
JP = os.path.join(CORPUS_DIR, "kaho_lines_jp.txt")
BY_STORY = os.path.join(CORPUS_DIR, "kaho_lines_by_story")

with open(JP, "r", encoding="utf-8") as f:
    jp_lines = [l.rstrip("\n") for l in f if l.strip()]
N = len(jp_lines)

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

print("=== A. ですー drawl variants ===")
for pat in [r"ですー", r"ますー", r"でしたー", r"ですよー", r"ますよー", r"なー", r"かー", r"だー"]:
    print(f"{pat}: {cnt(pat, True)}")
print("\n--- ですー example ---")
for l, s in ex(r"ですー", 6, True):
    print(f"[{s}] {l}")
print("\n--- でしたー example ---")
for l, s in ex(r"でしたー", 5, True):
    print(f"[{s}] {l}")

print("\n=== B. self-name / intro phrases ===")
print(f"小宮果穂: {cnt('小宮果穂')}")
print(f"小宮 果穂: {cnt('小宮 果穂')}")
print(f"果穂です: {cnt('果穂です')}")
print(f"正義の味方、小宮果穂: {cnt('正義の味方、小宮果穂')}")
for l, s in ex(r"小宮果穂", 6):
    print(f"[{s}] {l}")

print("\n=== C. お仕事手帳 / signature items ===")
print(f"お仕事手帳: {cnt('お仕事手帳')}")
print(f"手帳: {cnt('手帳')}")
print(f"リュック/鞄/かばん: {cnt('リュック')},{cnt('鞄')},{cnt('かばん')}")
print(f"マフラー: {cnt('マフラー')}")
print(f"マメ丸: {cnt('マメ丸')}")
print(f"カレー: {cnt('カレー')}")
print(f"給食: {cnt('給食')}")
print(f"牛乳: {cnt('牛乳')}")

print("\n=== D. hero motto / fixed phrases ===")
for pat in ["ヒーローは、絶対に約束を破らない", "ヒーローは", "正義は勝つ", "ヒーローになる", "ヒーローになるんだ", "ヒーローアイドル", "ヒーローはかっこいい", "見せ場", "ドキドキ", "わくわく", "ワクワク", "キラキラ"]:
    print(f"{pat}: {cnt(pat)}")
for l, s in ex("正義は勝つ", 4):
    print(f"[{s}] {l}")
print("--- ヒーローは ... ---")
for l, s in ex(r"ヒーローは、", 6, True):
    print(f"[{s}] {l}")

print("\n=== E. question forms ===")
for pat in [r"ですか[？?]", r"ましょうか[？?]", r"ですかっ", r"ますか[？?]", r"でしょうか[？?]", r"ですか！", r"ますか！", r"いいですか", r"大丈夫ですか", r"ですよね[？?]"]:
    print(f"{pat}: {cnt(pat, True)}")
print("--- ですか！ example ---")
for l, s in ex(r"ですか！", 5, True):
    print(f"[{s}] {l}")

print("\n=== F. emphasis / superlatives ===")
for pat in ["スッゴく", "すっごく", "すごく", "スゴく", "スッごく", "いちばん", "一番", "最高", "完璧", "絶対", "もっともっと", "いっぱい", "ドキドキ", "わくわく", "ワクワク", "ドキッ", "はりきって", "張り切って"]:
    print(f"{pat}: {cnt(pat)}")
print("--- スッゴく example ---")
for l, s in ex("スッゴく", 6):
    print(f"[{s}] {l}")

print("\n=== G. っ！ / っ patterns ===")
print(f"っ！ (any): {cnt(r'っ[！!]', True)}")
print(f"〜っ… : {cnt(r'っ…', True)}")
print(f"……っ (line end): {cnt(r'……っ$', True)}")
print(f"っ！$ (line end): {cnt(r'っ[！!]$', True)}")
print(f"えへへっ: {cnt('えへへっ')}")
print(f"うぅ: {cnt('うぅ')}")
print(f"んー: {cnt('んー')}")
print(f"うーん: {cnt('うーん')}")

print("\n=== H. ヒーロー story contexts (top by frequency) ===")
hero_stories = Counter()
for l in jp_lines:
    if "ヒーロー" in l:
        hero_stories[story_map.get(l, "?")] += 1
for k, v in hero_stories.most_common(15):
    print(f"{v:4d}  {k}")

print("\n=== I. プロデューサーさん count & variants ===")
print(f"プロデューサーさん: {cnt('プロデューサーさん')}")
print(f"プロデューサー: {cnt('プロデューサー')}")
print(f"Pさん: {cnt('Pさん')}")

print("\n=== J. うち usage ===")
for l, s in ex("うちの", 6):
    print(f"[{s}] {l}")

print("\n=== K. あたしたち / みんなで style ===")
print(f"あたしたち: {cnt('あたしたち')}")
print(f"みんなで: {cnt('みんなで')}")
print(f"みんなの: {cnt('みんなの')}")
print(f"みんなも: {cnt('みんなも')}")
print(f"みんなに: {cnt('みんなに')}")
print(f"みんなで一緒: {cnt('みんなで一緒')}")

print("\n=== L. greeting / action words ===")
for pat in ["任されました", "まかされました", "任せて", "お任せ", "行きます", "行ってきます", "がんばります", "頑張ります", "やってやる", "やってみます", "お願いします", "よろしくお願い", "ありがとうございました", "ごちそうさま"]:
    print(f"{pat}: {cnt(pat)}")
print("--- 任されました example ---")
for l, s in ex("任されました", 5):
    print(f"[{s}] {l}")
print("--- がんばります example ---")
for l, s in ex("頑張ります", 5):
    print(f"[{s}] {l}")

print("\n=== M. 決めポーズ / tokusatsu action ===")
for pat in [r"変身", r"ポーズ", r"決め", r"ビシ", r"バシッ", r"ドーン", r"ドカーン", r"ズバッ", r"キメ"]:
    print(f"{pat}: {cnt(pat, True)}")

print("\n=== N. 放クラ member address names ===")
for pat in ["樹里さん", "凛世さん", "夏葉さん", "智代子さん", "ちょこ先輩", "果穂ちゃん"]:
    print(f"{pat}: {cnt(pat)}")
