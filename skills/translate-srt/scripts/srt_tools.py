#!/usr/bin/env python3
"""SRT 清理工具。文本规范的完整定义见 ../references/subtitle-rules.md。

用法:
  python srt_tools.py normalize in.srt -o out.srt   # 解析+行合并+时间轴校验+重编号(修正阶段用)
  python srt_tools.py clean in.srt -o out.srt       # normalize + 标点规范化(译文阶段用)
  python srt_tools.py --self-test
"""
import argparse
import re
import sys
import unicodedata
from pathlib import Path

TIME_RE = re.compile(
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})"
)

BRACKET_MAP = str.maketrans({"[": "(", "]": ")", "【": "(", "】": ")"})
ELLIPSIS_RE = re.compile(r"\.{2,}|。{2,}|‥+")
# 句中直接替换为空格的非成对标点;· 和 ・ 是人名分隔符,不在其列
MID_PUNCT = set(",，、。．.;；:：~～—–")
OPEN = set("「『“‘《〈(（")
CLOSE = set("」』”’》〉)）")
TERMINAL_KEEP = set("?？!！…")


def _ms(h, m, s, ms):
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(ms.ljust(3, "0"))


def _fmt(t):
    h, r = divmod(t, 3600000)
    m, r = divmod(r, 60000)
    s, ms = divmod(r, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _is_cjk(ch):
    return any(a <= ord(ch) <= b for a, b in (
        (0x3000, 0x30FF), (0x3400, 0x4DBF), (0x4E00, 0x9FFF),
        (0xF900, 0xFAFF), (0xAC00, 0xD7AF), (0xFF00, 0xFFEF),
    ))


def _is_punct(ch):
    return unicodedata.category(ch).startswith("P") or ch in "~～"


def _join_lines(lines):
    out = lines[0]
    for nxt in lines[1:]:
        if out and nxt and _is_cjk(out[-1]) and _is_cjk(nxt[0]):
            out += nxt
        else:
            out += " " + nxt
    return out


def parse(text):
    entries = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n").strip()):
        lines = block.split("\n")
        ti = next((i for i, l in enumerate(lines) if TIME_RE.search(l)), None)
        if ti is None:
            continue
        g = TIME_RE.search(lines[ti]).groups()
        content = [l.strip() for l in lines[ti + 1:] if l.strip()]
        if not content:
            continue
        entries.append({"start": _ms(*g[:4]), "end": _ms(*g[4:]), "text": _join_lines(content)})
    return entries


def clean_text(text):
    text = text.translate(BRACKET_MAP)
    text = ELLIPSIS_RE.sub("…", text)
    chars = list(text)
    for i, ch in enumerate(chars):
        if ch in MID_PUNCT:
            prev = chars[i - 1] if i else ""
            nxt = chars[i + 1] if i + 1 < len(chars) else ""
            if ch in ".:" and prev.isdigit() and nxt.isdigit():
                continue  # 3.5 / 12:30
            chars[i] = " "
    text = re.sub(r"\s+", " ", "".join(chars)).strip()
    while text and _is_punct(text[0]) and text[0] not in OPEN:
        text = text[1:].lstrip()
    while text and _is_punct(text[-1]) and text[-1] not in TERMINAL_KEEP and text[-1] not in CLOSE:
        text = text[:-1].rstrip()
    return text


def process(text, mode):
    entries = parse(text)
    if not entries:
        sys.exit("错误: 未解析到任何字幕条目")
    entries.sort(key=lambda e: e["start"])
    for e in entries:
        if e["end"] < e["start"]:
            e["start"], e["end"] = e["end"], e["start"]
        if mode == "clean":
            e["text"] = clean_text(e["text"])
    return [e for e in entries if e["text"]]


def serialize(entries):
    return "\n".join(
        f"{i}\n{_fmt(e['start'])} --> {_fmt(e['end'])}\n{e['text']}\n"
        for i, e in enumerate(entries, 1)
    )


def self_test():
    assert _join_lines(["えっと、", "それはね"]) == "えっと、それはね"
    assert _join_lines(["Hello", "world"]) == "Hello world"
    assert clean_text("、你好,世界。") == "你好 世界"
    assert clean_text("[笑]真的吗?") == "(笑)真的吗?"
    assert clean_text("Wait... what.") == "Wait… what"
    assert clean_text("现在是3.5版本,时间12:30。") == "现在是3.5版本 时间12:30"
    assert clean_text("克里斯·埃文斯说:「没问题」") == "克里斯·埃文斯说 「没问题」"
    assert clean_text("嗯。。。") == "嗯…"
    sample = "2\n00:00:03,500 --> 00:00:02,000\nsecond\n\n1\n00:00:01,000 --> 00:00:02,000\n第一\n行\n"
    es = process(sample, "normalize")
    assert [e["text"] for e in es] == ["第一行", "second"]
    assert es[1]["start"] == 2000 and es[1]["end"] == 3500  # 起止倒置已交换
    assert serialize(es).startswith("1\n00:00:01,000 --> 00:00:02,000\n第一行\n")
    print("self-test OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=["normalize", "clean"], nargs="?")
    ap.add_argument("input", nargs="?")
    ap.add_argument("-o", "--output")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if not args.mode or not args.input:
        ap.error("需要 mode 和 input 参数")
    entries = process(Path(args.input).read_text(encoding="utf-8-sig"), args.mode)
    out = args.output or args.input
    Path(out).write_text(serialize(entries), encoding="utf-8", newline="\n")
    print(f"OK: {len(entries)} entries -> {out}")  # ponytail: ASCII 输出,避开 Windows 控制台编码问题


if __name__ == "__main__":
    main()
