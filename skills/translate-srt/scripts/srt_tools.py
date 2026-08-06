#!/usr/bin/env python3
"""SRT 清理工具。文本规范的完整定义见 ../references/subtitle-rules.md。

用法:
  python srt_tools.py init <original.srt>      # 建工作区:复制原 srt + AGENTS.md + _context/(占位 brief/glossary + 空 research)
  python srt_tools.py normalize in.srt -o out.srt   # 解析+行合并+时间轴校验+重编号(修正阶段用)
  python srt_tools.py clean in.srt -o out.srt -l <lang>  # normalize + 标点规范化(译文阶段用; -l 决定标点风格)
  python srt_tools.py --self-test
"""
import argparse
import re
import shutil
import sys
import tempfile
import unicodedata
from pathlib import Path

TIME_RE = re.compile(
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})"
)

BRACKET_MAP = str.maketrans({"[": "(", "]": ")", "【": "(", "】": ")"})
ELLIPSIS_RE = re.compile(r"\.{2,}|。{2,}|‥+")
# 句中直接替换为空格的非成对标点;· 和 ・ 是人名分隔符,不在其列。破折号族含 —–―‒(ｰ 是片假名长音符号,属词内符号,不在其列)
MID_PUNCT = set(",，、。．.;；:：~～—–―‒")
# CJK 全角标点子集:western 风格保留 ASCII 标点与破折号族,但仍把残留的 CJK 全角标点转空格(译文不该出现这些)
CJK_MID_PUNCT = set("，、。．；：～")
OPEN = set('「『“‘《〈(（«‹"')
CLOSE = set('」』”’》〉)）»›"')
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


# 稀疏标点风格的 CJK 目标语言;其余(拉丁/西里尔等)走 western 风格,保留句中标点
CJK_LANGS = {"zh", "ja", "ko"}


def _style_for(lang):
    """根据目标语言决定 clean 的标点风格。缺省视为 cjk,保持向后兼容。"""
    if not lang:
        return "cjk"
    base = lang.lower().replace("_", "-").split("-")[0]
    return "cjk" if base in CJK_LANGS else "western"


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


def clean_text(text, style="cjk"):
    text = text.translate(BRACKET_MAP)
    text = ELLIPSIS_RE.sub("…", text)
    if style != "western":
        # cjk 风格:句中非成对标点转空格;数字/时间里的 . : ． ： 保留(str.isdigit 已覆盖全角数字 ０-９)
        chars = list(text)
        for i, ch in enumerate(chars):
            if ch in MID_PUNCT:
                prev = chars[i - 1] if i else ""
                nxt = chars[i + 1] if i + 1 < len(chars) else ""
                if ch in ".:．：" and prev.isdigit() and nxt.isdigit():
                    continue  # 3.5 / 12:30 / ３．５ / １２：３０
                chars[i] = " "
        text = "".join(chars)
    else:
        # western 风格:保留 ASCII 标点与破折号族,但仍把残留的 CJK 全角标点转空格(译文不该出现这些)
        chars = list(text)
        for i, ch in enumerate(chars):
            if ch in CJK_MID_PUNCT:
                prev = chars[i - 1] if i else ""
                nxt = chars[i + 1] if i + 1 < len(chars) else ""
                if ch in "．：" and prev.isdigit() and nxt.isdigit():
                    continue  # ３．５ / １２：３０
                chars[i] = " "
        text = "".join(chars)
    # 统一空白规范化(两种风格都需要,western 也要 collapse 首尾/多空格/制表符)
    text = re.sub(r"\s+", " ", text).strip()
    # 前导标点剥离(开引号/开括号除外)
    while text and _is_punct(text[0]) and text[0] not in OPEN:
        text = text[1:].lstrip()
    # 尾标点剥离,仅保留句末允许的标点;western 风格额外保留句号 .
    terminal = TERMINAL_KEEP if style != "western" else TERMINAL_KEEP | {"."}
    while text and _is_punct(text[-1]) and text[-1] not in terminal and text[-1] not in CLOSE:
        text = text[:-1].rstrip()
    return text


def process(text, mode, lang=None):
    entries = parse(text)
    if not entries:
        sys.exit("错误: 未解析到任何字幕条目")
    style = _style_for(lang)  # clean 模式用;normalize 不调用 clean_text,style 不影响
    entries.sort(key=lambda e: e["start"])
    for e in entries:
        if e["end"] < e["start"]:
            e["start"], e["end"] = e["end"], e["start"]
        if mode == "clean":
            e["text"] = clean_text(e["text"], style)
    return [e for e in entries if e["text"]]


def serialize(entries):
    return "\n".join(
        f"{i}\n{_fmt(e['start'])} --> {_fmt(e['end'])}\n{e['text']}\n"
        for i, e in enumerate(entries, 1)
    )


AGENTS_MD_TEMPLATE = """# {stem} 字幕翻译工作区

本目录是 `{stem}.srt` 的翻译工作区。外部原始字幕保持不动，所有产出都在本目录内。

## 文件布局

- `{stem}.srt` — 原始字幕副本（不要直接改，改带后缀的产物）
- `{stem}_fix.srt` — 转录修正稿（原语言，纠正听录错误）
- `{stem}_<lang>.srt` — 翻译初稿
- `{stem}_<lang>_fix.srt` — 复核终稿
- `AGENTS.md` — 本文件，说明结构与流程
- `_context/` — 背景资料区
  - `brief.md` — 背景简报：内容概述、专名、疑似听录错误。修正/翻译/复核前都要读。
  - `glossary.md` — 术语表：原语言 → 目标语言标准译名。翻译/复核必须遵循。
  - `research/` — 调研子代理产出的原始文件（`NN-topic.md`）。简报与术语表由它提炼而来；不够时回这里查细节。

## 流程

1. 建工作目录（已完成，由 `srt_tools.py init` 生成本文件与 `_context/` 占位）
2. 问清原始/目标语言与主题；通读 `{stem}.srt` 提炼专名；派调研子代理把结果写入 `_context/research/`；主代理读调研文件后编辑 `_context/brief.md` 和 `_context/glossary.md`
3. 主代理对照简报/术语表修正转录 → `{stem}_fix.srt`，跑 `normalize`
4. 派翻译子代理（先读 `_context/brief.md`、`_context/glossary.md`、规范）→ `{stem}_<lang>.srt`，跑 `clean`
5. 派复核子代理（先读 `_context/brief.md`、`_context/glossary.md`、规范）→ `{stem}_<lang>_fix.srt`，跑 `clean`
6. 主代理抽查终稿，向用户报告产出路径、术语表、修正要点
"""

BRIEF_MD_TEMPLATE = """# 背景简报 — {stem}

> 占位文件。第 2 步调研完成后，由主代理根据 `_context/research/` 下的调研文件编辑替换本内容。

## 内容概述

（待填）

## 专名

（待填）

## 疑似听录错误

（待填）
"""

GLOSSARY_MD_TEMPLATE = """# 术语表 — {stem}

> 占位文件。第 2 步调研完成后，由主代理编辑替换本内容。
> 格式：`原语言写法 → 目标语言标准译名`，查不到标"自拟"。

（待填）
"""


def init_workspace(original_srt):
    """在原 srt 同目录建 <stem>/ 工作区：复制原 srt、写 AGENTS.md、占位 brief/glossary、空 research/。"""
    src = Path(original_srt).expanduser().resolve()
    if not src.is_file() or src.suffix.lower() != ".srt":
        sys.exit(f"错误: {src} 不是有效的 .srt 文件")
    stem = src.stem
    workdir = src.parent / stem
    if workdir.exists():
        sys.exit(f"错误: 工作目录已存在: {workdir}（如需复用请手动检查，本脚本不覆盖）")
    context = workdir / "_context"
    research = context / "research"
    workdir.mkdir()
    context.mkdir()
    research.mkdir()
    shutil.copy2(src, workdir / src.name)
    (workdir / "AGENTS.md").write_text(AGENTS_MD_TEMPLATE.format(stem=stem), encoding="utf-8", newline="\n")
    (context / "brief.md").write_text(BRIEF_MD_TEMPLATE.format(stem=stem), encoding="utf-8", newline="\n")
    (context / "glossary.md").write_text(GLOSSARY_MD_TEMPLATE.format(stem=stem), encoding="utf-8", newline="\n")
    print(f"OK: 工作区已创建 -> {workdir}")
    print(f"  - {workdir / src.name}")
    print(f"  - {workdir / 'AGENTS.md'}")
    print(f"  - {context / 'brief.md'} (占位)")
    print(f"  - {context / 'glossary.md'} (占位)")
    print(f"  - {research} (空)")


def self_test():
    # init 子命令：建临时 srt，跑 init，检查结构，再清理
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "how-to-code.srt"
        src.write_text("1\n00:00:01,000 --> 00:00:02,000\nhello\n", encoding="utf-8")
        init_workspace(str(src))
        wd = Path(d) / "how-to-code"
        assert (wd / "how-to-code.srt").read_text(encoding="utf-8").startswith("1\n")
        assert "how-to-code" in (wd / "AGENTS.md").read_text(encoding="utf-8")
        assert "待填" in (wd / "_context" / "brief.md").read_text(encoding="utf-8")
        assert "待填" in (wd / "_context" / "glossary.md").read_text(encoding="utf-8")
        assert (wd / "_context" / "research").is_dir()
        # 已存在应报错
        try:
            init_workspace(str(src))
            raise AssertionError("重复 init 应报错")
        except SystemExit:
            pass
    assert _join_lines(["えっと、", "それはね"]) == "えっと、それはね"
    assert _join_lines(["Hello", "world"]) == "Hello world"
    assert clean_text("、你好,世界。") == "你好 世界"
    assert clean_text("[笑]真的吗?") == "(笑)真的吗?"
    assert clean_text("Wait... what.") == "Wait… what"
    assert clean_text("现在是3.5版本,时间12:30。") == "现在是3.5版本 时间12:30"
    assert clean_text("现在是３．５版本,时间１２：３０。") == "现在是３．５版本 时间１２：３０"  # 全角数字/时间保护
    assert clean_text("Hello, world. This is nice.", "western") == "Hello, world. This is nice."  # western 保留句中标点
    assert clean_text("  Hello,   world.  ", "western") == "Hello, world."  # western 也规范化首尾/多空格(句尾 . 保留)
    assert clean_text("a\tb", "western") == "a b"  # western 制表符转空格
    assert clean_text("\"Hello\"", "western") == '"Hello"'  # ASCII 直引号不剥
    assert clean_text('"你好"') == '"你好"'  # cjk 下 ASCII 直引号同样不剥
    assert clean_text("克里斯·埃文斯说:「没问题」") == "克里斯·埃文斯说 「没问题」"
    assert clean_text("«Bonjour»", "western") == "«Bonjour»"  # 书名/引语引号不剥
    assert clean_text("好的―行") == "好的 行"  # 破折号变体 ― ‒ 也转空格
    # western 风格下残留的 CJK 全角标点应被清理(转空格),但 ASCII 标点/破折号族保留
    assert clean_text("Hello，world。", "western") == "Hello world"  # 全角逗号转空格、全角句号尾剥
    assert clean_text("Hello—world", "western") == "Hello—world"  # 破折号族保留
    assert clean_text("现在是３．５版本，时间１２：３０。", "western") == "现在是３．５版本 时间１２：３０"  # western 下全角数字仍保护
    assert clean_text("嗯。。。") == "嗯…"
    sample = "2\n00:00:03,500 --> 00:00:02,000\nsecond\n\n1\n00:00:01,000 --> 00:00:02,000\n第一\n行\n"
    es = process(sample, "normalize")
    assert [e["text"] for e in es] == ["第一行", "second"]
    assert es[1]["start"] == 2000 and es[1]["end"] == 3500  # 起止倒置已交换
    assert serialize(es).startswith("1\n00:00:01,000 --> 00:00:02,000\n第一行\n")
    # 端到端:-l 决定 clean 标点风格(en -> western,保留句尾句号)
    en_sample = "1\n00:00:01,000 --> 00:00:02,000\n  Hello,   world.  \n"
    en_es = process(en_sample, "clean", lang="en")
    assert [e["text"] for e in en_es] == ["Hello, world."]
    # 端到端:-l zh -> cjk(句中标点转空格、句尾句号剥)
    zh_sample = "1\n00:00:01,000 --> 00:00:02,000\n你好，世界。\n"
    zh_es = process(zh_sample, "clean", lang="zh")
    assert [e["text"] for e in zh_es] == ["你好 世界"]
    print("self-test OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=["init", "normalize", "clean"], nargs="?")
    ap.add_argument("input", nargs="?")
    ap.add_argument("-o", "--output")
    ap.add_argument("-l", "--lang", help="目标语言(ISO 639-1,如 zh/ja/en)。决定 clean 的标点风格:cjk=逗号转空格,其余=保留句中标点")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if not args.mode or not args.input:
        ap.error("需要 mode 和 input 参数")
    if args.mode == "init":
        return init_workspace(args.input)
    entries = process(Path(args.input).read_text(encoding="utf-8-sig"), args.mode, lang=args.lang)
    out = args.output or args.input
    Path(out).write_text(serialize(entries), encoding="utf-8", newline="\n")
    print(f"OK: {len(entries)} entries -> {out}")  # ponytail: ASCII 输出,避开 Windows 控制台编码问题


if __name__ == "__main__":
    main()
