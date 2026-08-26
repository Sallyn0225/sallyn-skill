# -*- coding: utf-8 -*-
"""Kaho (小宮果穂) expression DNA quantitative stats.
Computes self-reference, sentence endings, laughs, high-freq nouns,
catchphrases, sentence features, and hero/tokusatsu vocabulary.
"""
import re
import os
import json
from collections import Counter

CORPUS_DIR = r"E:\Download\others\agent-test\shinycara-skill\.agents\skills\kaho-perspective\references\sources\corpus"
FULL = os.path.join(CORPUS_DIR, "kaho_lines_full.txt")
JP = os.path.join(CORPUS_DIR, "kaho_lines_jp.txt")
BY_STORY = os.path.join(CORPUS_DIR, "kaho_lines_by_story")

def load_lines(path):
    with open(path, "r", encoding="utf-8") as f:
        return [l.rstrip("\n") for l in f if l.strip()]

jp_lines = load_lines(JP)
full_lines = load_lines(FULL)
N = len(jp_lines)
print(f"TOTAL JP LINES: {N}")

# ---------- 1. Self-reference ----------
self_terms = ["あたし", "私", "アタシ", "自分", "オレ", "うち", "ボク", "俺"]
self_counts = Counter()
self_lines = {}
for term in self_terms:
    self_counts[term] = sum(1 for l in jp_lines if term in l)
    self_lines[term] = [l for l in jp_lines if term in l]

# normalize: remove 自分 which is a noun too; count per-line
print("\n=== 1. SELF-REFERENCE (per-line hit) ===")
for t in self_terms:
    print(f"{t}: {self_counts[t]} lines")

# Also count total occurrences (not just lines)
def total_occ(lines, term):
    return sum(l.count(term) for l in lines)
print("\n--- total occurrences ---")
for t in self_terms:
    print(f"{t}: {total_occ(jp_lines, t)}")

# ---------- 2. Sentence endings (verb-final / copula) ----------
# regex on line end, and general occurrence
endings = {
    "だよ": r"だよ",
    "だぞ": r"だぞ",
    "だね": r"だね",
    "だもん": r"だもん",
    "でしょ": r"でしょ",
    "です": r"です",
    "ます": r"ます",
    "なのだ": r"なのだ",
    "なんだ": r"なんだ",
    "のだ": r"のだ",
    "んだ": r"んだ",
    "なの？": r"なの[？?]",
    "なの!": r"なの[！!]",
    "のか": r"のか",
    "じゃん": r"じゃん",
    "っす": r"っす",
    "〜だ!": r"だ[！!]",
}
print("\n=== 2. SENTENCE ENDINGS (occurrence, per-line hit) ===")
for name, pat in endings.items():
    c = sum(1 for l in jp_lines if re.search(pat, l))
    print(f"{name}: {c} lines  (occ={total_occ(jp_lines, name)})")

# line-final analysis: what character/particle ends the line
line_end_counter = Counter()
for l in jp_lines:
    s = l.rstrip("　 ")
    if not s:
        line_end_counter["(empty)"] += 1
        continue
    last = s[-1]
    line_end_counter[last] += 1
print("\n--- line-final char distribution (top 20) ---")
for k, v in line_end_counter.most_common(20):
    print(f"'{k}': {v}")

# final particle: look at the last 3 chars for common endings
final3 = Counter()
for l in jp_lines:
    s = l.rstrip("　 ")
    final3[s[-3:]] += 1
print("\n--- line-final 3 chars (top 25) ---")
for k, v in final3.most_common(25):
    print(f"'{k}': {v}")

# ---------- 3. Laughs / interjections ----------
laughs = {
    "えへへ": "えへへ",
    "あはは": "あはは",
    "ははは": "ははは",
    "うふふ": "うふふ",
    "ふふ": "ふふ",
    "うふ": "うふ",
    "わぁ": "わぁ",
    "わーい": "わーい",
    "やった": "やった",
    "きゃー": "きゃー",
    "きゃっ": "きゃっ",
    "ぱぁ": "ぱぁ",
    "わわっ": "わわっ",
    "うわー": "うわー",
    "えっ": "えっ",
    "あっ": "あっ",
    "おー": "おー",
    "いえーい": "いえーい",
}
print("\n=== 3. LAUGHS / INTERJECTIONS ===")
for name, pat in laughs.items():
    c = sum(1 for l in jp_lines if pat in l)
    print(f"{name}: {c} lines  (occ={total_occ(jp_lines, pat)})")

# ---------- 4. High-frequency thematic nouns ----------
themes = {
    "ヒーロー": "ヒーロー",
    "ヒロイン": "ヒロイン",
    "カレー": "カレー",
    "正義": "正義",
    "センター": "センター",
    "みんな": "みんな",
    "応援": "応援",
    "夢": "夢",
    "家族": "家族",
    "リュック": "リュック",
    "アイドル": "アイドル",
    "お仕事": "お仕事",
    "仕事": "仕事",
    "お母さん": "お母さん",
    "お父さん": "お父さん",
    "弟": "弟",
    "チョコ": "チョコ",
    "放クラ": "放クラ",
    "仲間": "仲間",
    "笑顔": "笑顔",
    "元気": "元気",
    "勇気": "勇気",
    "約束": "約束",
    "頑張": "頑張",
    "パワー": "パワー",
    "お守り": "お守り",
    "学校": "学校",
    "小学": "小学",
}
print("\n=== 4. THEMATIC NOUNS ===")
for name, pat in themes.items():
    c = sum(1 for l in jp_lines if pat in l)
    print(f"{name}: {c} lines  (occ={total_occ(jp_lines, pat)})")

# ---------- 5. Catchphrases / fixed expressions ----------
# Extract top frequent n-gram phrases (4-12 chars) that repeat across lines
def phrase_counter(lines, min_n=4, max_n=12, min_count=5):
    cnt = Counter()
    for l in lines:
        s = re.sub(r"[。、！？!?〜ー…\s（）()「」『』\n]", "", l)
        if not s:
            continue
        for n in range(min_n, min(max_n, len(s)) + 1):
            for i in range(len(s) - n + 1):
                cnt[s[i:i+n]] += 1
    return cnt

phrases = phrase_counter(jp_lines)
# filter: keep phrases that appear in at least X lines (approx by count / line length)
print("\n=== 5. TOP REPEATED PHRASES (n=4..12) ===")
interesting = [p for p, c in phrases.items() if c >= 8 and len(p) >= 4]
interesting.sort(key=lambda x: -phrases[x])
for p in interesting[:40]:
    print(f"'{p}': {phrases[p]}")

# ---------- 6. Sentence features ----------
print("\n=== 6. SENTENCE FEATURES ===")
exclaim_lines = sum(1 for l in jp_lines if "！" in l or "!" in l)
print(f"lines with ！/!: {exclaim_lines} / {N} = {exclaim_lines/N:.1%}")

question_lines = sum(1 for l in jp_lines if "？" in l or "?" in l)
print(f"lines with ？/?: {question_lines} / {N} = {question_lines/N:.1%}")

# 〜 long sound: the file contains literal \n inside text, so 〜 char or ー char
tild_lines = sum(1 for l in jp_lines if "〜" in l)
print(f"lines with 〜: {tild_lines}")
choon_lines = sum(1 for l in jp_lines if "ー" in l)
print(f"lines with ー(chōon): {choon_lines}")

# small tsu っ (emphasis)
sutsu_lines = sum(1 for l in jp_lines if "っ" in l)
print(f"lines with っ (incl ですっ etc): {sutsu_lines}")

# っ！ style
sutsu_ex = sum(1 for l in jp_lines if "っ！" in l or "っ!" in l)
print(f"lines ending style っ！: {sutsu_ex}")

# emphasis adverbs
emphasis = {
    "めっちゃ": "めっちゃ",
    "すごく": "すごく",
    "すっごく": "すっごく",
    "ばっちり": "ばっちり",
    "ぴったり": "ぴったり",
    "バッチリ": "バッチリ",
    "絶対": "絶対",
    "絶対に": "絶対に",
    "きっと": "きっと",
    "ぜったい": "ぜったい",
    "マジで": "マジで",
    "ガチ": "ガチ",
    "めっちゃくちゃ": "めっちゃくちゃ",
    "もっともっと": "もっともっと",
    "いっぱい": "いっぱい",
    "たっぷり": "たっぷり",
}
print("--- emphasis adverbs ---")
for name, pat in emphasis.items():
    c = sum(1 for l in jp_lines if pat in l)
    print(f"{name}: {c}")

# line length stats
lens = [len(l) for l in jp_lines]
avg = sum(lens) / len(lens)
print(f"\navg chars/line: {avg:.1f}, max: {max(lens)}, short lines(<=5): {sum(1 for x in lens if x <= 5)}")

# multi-sentence per line (count 。 and ！ within one line, minus trailing)
multi = sum(1 for l in jp_lines if l.count("！") + l.count("!") + l.count("。") >= 2)
print(f"lines with 2+ sentence boundaries (multi-clause): {multi}")

# ですっ / ますっ style
desu_tsu = sum(1 for l in jp_lines if re.search(r"(ですっ|ますっ)", l))
print(f"ですっ/ますっ: {desu_tsu}")

# 〜っ！ trailing
trail_tsu_ex = sum(1 for l in jp_lines if re.search(r"(ですっ|ますっ|です！|ます！|でした！)$", l))
print(f"lines ending with polite-exclaim (ですっ/ますっ/です！/ます！/でした！): {trail_tsu_ex}")

# ---------- 7. Hero / tokusatsu vocabulary ----------
hero_words = {
    "変身": "変身",
    "必殺技": "必殺技",
    "正義の味方": "正義の味方",
    "怪人": "怪人",
    "戦隊": "戦隊",
    "レンジャー": "レンジャー",
    "敵": "敵",
    "わるもの": "わるもの",
    "悪者": "悪者",
    "怪獣": "怪獣",
    "かっこいい": "かっこいい",
    "かっこよい": "かっこよい",
    "ヒーローショー": "ヒーローショー",
    "悪の": "悪の",
    "勝利": "勝利",
    "勝つ": "勝つ",
    "必ず": "必ず",
    "大勝利": "大勝利",
    "見せ場": "見せ場",
    "必殺": "必殺",
    "戦う": "戦う",
    "パンチ": "パンチ",
    "キック": "キック",
    "変身ベルト": "変身ベルト",
}
print("\n=== 7. HERO / TOKUSATSU VOCAB ===")
for name, pat in hero_words.items():
    c = sum(1 for l in jp_lines if pat in l)
    print(f"{name}: {c}")

# 必殺技 name patterns: 〜キック/〜パンチ
kick = sum(1 for l in jp_lines if re.search(r"キック|パンチ", l))
print(f"キック/パンチ lines: {kick}")

# かほ third person self-naming (かほちゃん / 果穂)
kaho_self = sum(1 for l in jp_lines if "かほちゃん" in l)
kaho_kanji = sum(1 for l in jp_lines if "果穂" in l)
print(f"\n'かほちゃん' lines: {kaho_self}, '果穂' lines: {kaho_kanji}")

# hero self-intro phrase 正義の味方、小宮果穂！
intro = [l for l in jp_lines if "正義" in l and ("味方" in l or "！" in l)]
print(f"lines with 正義: {len(intro)}")

# ---------- Example extraction helpers ----------
# map line -> story
story_map = {}
for fn in os.listdir(BY_STORY):
    if not fn.endswith(".txt"):
        continue
    path = os.path.join(BY_STORY, fn)
    with open(path, "r", encoding="utf-8") as f:
        for l in f:
            l = l.rstrip("\n")
            if l.strip():
                story_map[l.split("\t")[0]] = fn.replace(".csv.txt", "")

def examples(pattern, k=5, is_regex=False):
    hits = []
    for l in jp_lines:
        if (is_regex and re.search(pattern, l)) or (not is_regex and pattern in l):
            hits.append(l)
    out = []
    for h in hits[:k]:
        out.append((h, story_map.get(h, "?")))
    return out

print("\n=== EXAMPLE: あたし ===")
for l, s in examples("あたし", 4):
    print(f"[{s}] {l}")
print("\n=== EXAMPLE: なのだ/なんだ ===")
for l, s in examples("なのだ", 4):
    print(f"[{s}] {l}")
print("\n=== EXAMPLE: えへへ ===")
for l, s in examples("えへへ", 4):
    print(f"[{s}] {l}")
print("\n=== EXAMPLE: ヒーロー ===")
for l, s in examples("ヒーロー", 4):
    print(f"[{s}] {l}")
print("\n=== EXAMPLE: ですっ ===")
for l, s in examples(r"ですっ", 4, True):
    print(f"[{s}] {l}")
print("\n=== EXAMPLE: なのですっ ===")
for l, s in examples("なのです", 4):
    print(f"[{s}] {l}")
print("\n=== EXAMPLE: っ！ line-final ===")
hits = []
for l in jp_lines:
    if re.search(r"っ！$", l):
        hits.append(l)
for h in hits[:5]:
    print(f"[{story_map.get(h, '?')}] {h}")
print("\n=== EXAMPLE: かほちゃん self-naming ===")
for l, s in examples("かほちゃん", 4):
    print(f"[{s}] {l}")
print("\n=== EXAMPLE: 正義の味方 ===")
for l, s in examples("正義の味方", 4):
    print(f"[{s}] {l}")
print("\n=== EXAMPLE: 必殺技 ===")
for l, s in examples("必殺技", 4):
    print(f"[{s}] {l}")
