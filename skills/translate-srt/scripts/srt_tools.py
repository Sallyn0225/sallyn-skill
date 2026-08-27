#!/usr/bin/env python3
"""SRT 清理工具。文本规范的完整定义见 ../references/subtitle-rules.md。

用法:
  python srt_tools.py init <original.srt>      # 建工作区:复制原 srt + AGENTS.md + _context/(占位 brief/glossary + 空 research)
  python srt_tools.py stats in.srt                  # 体检条目形态,判定该 merge(被切碎)还是 split(多句粘连)
  python srt_tools.py merge in.srt -o out.srt       # 把按行宽切碎的条目合并回整句(翻译前用,启发式)
  python srt_tools.py split in.srt -o out.srt       # 把多句粘连的超长条目按句末标点拆成一句一条(翻译前用)
  python srt_tools.py normalize in.srt -o out.srt   # 解析+行合并+时间轴校验+重编号(修正阶段用)
  python srt_tools.py clean in.srt -o out.srt -l <lang>  # normalize + 标点规范化(译文阶段用; -l 决定标点风格)
  python srt_tools.py resplit in.srt -o out.srt -l <lang>  # 把整句译文切回观看用分条(交付前用)
  python srt_tools.py check base.srt target.srt     # 对比条目数/时间轴/漏译(第 4、5 步完成标准)
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
# 说话人前缀 `名字: `(ASR --diarize 产出)。要求冒号后至少一个空格,避免把 12:30 / 午後3:30 误判为前缀
SPEAKER_RE = re.compile(r"^([^\s:：,，、。．!?！？…]{1,24})[:：] +")
# 句末标点(merge 判断上一条是否已收句),其后可跟闭引号
SENT_END = set("。．.！!？?…")
# 整条只有一个音频事件/场景描述(如 [オープニングミュージック]),merge 时既不吞并也不被吞
EVENT_RE = re.compile(r"^[\[(（【][^\[\]()（）【】]*[\])）】]$")
# resplit 的换行禁则(禁則処理),与上游 ASR 的 output.py 同口径:不可行首 / 不可行末的字符
NO_LINE_START = frozenset(
    "ーｰ〜"                       # 长音符
    "ぁぃぅぇぉっゃゅょゎゕゖ"      # 小书平假名
    "ァィゥェォッャュョヮヵヶ"      # 小书片假名
    "、。，．,.!！?？:：;；…‥・"    # 标点
    "）］｝」』】〉》〕”’\"'"       # 闭合括号与引号
    ")]}"
    "%％‰℃°"                     # 后置单位
)
NO_LINE_END = frozenset("（［｛「『【〈《〔“‘\"'$￥#＄￥＃" "([{")
# 无空格语言里的词边界近似:脚本类转换处更可能是词首。数值越低越适合断开
SCRIPT_BREAK_COST = {
    ("hira", "kanji"): 1.0,
    ("hira", "kata"): 1.0,
    ("kata", "kanji"): 1.5,
    ("kanji", "kata"): 1.5,
    ("hira", "hira"): 3.0,
    ("kanji", "kanji"): 4.0,  # 连续汉字多半是一个复合词
    ("kanji", "hira"): 4.0,   # 后面的假名多半是送り仮名
    ("kata", "hira"): 4.0,
    ("kata", "kata"): 6.0,    # 连续片假名是单个外来语
}
# 每浪费一整行宽度所折算的切点代价。调高=更倾向塞满行宽,调低=更倾向找好切点
WASTE_WEIGHT = 4.0
# resplit 的单行列宽预算。上游 ASR 的 28 是「两行中的一行」,而本规范要求一条一行,
# 故 cjk 放宽到 38 列(≈19 个汉字,单行中文字幕的常见上限);拉丁保持 42
CJK_LINE_WIDTH = 38
LATIN_LINE_WIDTH = 42
# split/stats 的「超长条目」判据:一条整句 resplit 后不该超过三行,超过说明它是多句粘连
LONG_ENTRY_FACTOR = 3
LONG_ENTRY_SEC = 12.0
# stats 判定「被行宽切碎」的比例阈值:未收句条目占比超过它就该跑 merge
UNFINISHED_RATIO = 0.3


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


def _cw(ch):
    """单字符的显示列宽:全角/宽字符算 2 列,其余 1 列(与上游 ASR 的行宽口径一致)。"""
    return 2 if unicodedata.east_asian_width(ch) in "WF" else 1


def _width(text):
    return sum(_cw(ch) for ch in text)


def _split_speaker(text):
    """拆出说话人前缀:'丸岡和佳奈: 本日の' -> ('丸岡和佳奈', '本日の');无前缀则 ('', text)。"""
    m = SPEAKER_RE.match(text)
    return (m.group(1), text[m.end():]) if m else ("", text)


def _with_speaker(speaker, body):
    return f"{speaker}: {body}" if speaker and body else body


def _ends_sentence(body):
    """正文是否已经收句(末尾是句末标点,允许其后跟闭引号)。"""
    t = body.rstrip()
    while t and t[-1] in CLOSE:
        t = t[:-1].rstrip()
    return bool(t) and t[-1] in SENT_END


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
    # 说话人前缀原样透传:不参与句中标点替换,也不参与首尾标点剥离(否则 `丸岡和佳奈: ` 的冒号会被转成空格)
    speaker, text = _split_speaker(text)
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
    # 正文清空时整条作废(不留只有 `说话人: ` 的空壳),由 process 过滤
    return _with_speaker(speaker, text)


def merge_entries(entries, max_gap_ms, max_merged_ms):
    """把 ASR 按行宽切碎的条目合并回整句(启发式,主代理需抽查)。

    合并到上一条的条件(全部满足):上一条未收句 + 说话人前缀相同 + 间隔 <= max_gap +
    合并后总时长 <= max_merged_duration。整条只有音频事件的条目不参与合并。
    """
    out = []
    for e in entries:
        sp, body = _split_speaker(e["text"])
        is_event = bool(EVENT_RE.match(body.strip()))
        if out:
            p = out[-1]
            if (not p["_event"] and not is_event
                    and not _ends_sentence(p["_body"])
                    and p["_sp"] == sp
                    and e["start"] - p["end"] <= max_gap_ms
                    and e["end"] - p["start"] <= max_merged_ms):
                parts = [x for x in (p["_body"], body) if x]
                p["_body"] = _join_lines(parts) if parts else ""
                p["end"] = max(p["end"], e["end"])
                continue
        out.append({"start": e["start"], "end": e["end"], "_sp": sp, "_body": body, "_event": is_event})
    for e in out:
        e["text"] = _with_speaker(e["_sp"], e["_body"])
    return out


def _script_of(ch):
    """粗粒度字符类,用于在无空格语言里估计词边界。口径与上游 ASR 的 output.py 一致。"""
    if "ぁ" <= ch <= "ゟ":
        return "hira"
    if "゠" <= ch <= "ヿ" or "ｦ" <= ch <= "ﾝ":
        return "kata"
    if "一" <= ch <= "鿿" or "㐀" <= ch <= "䶿":
        return "kanji"
    if ch.isascii() and ch.isalnum():
        return "latin"
    return "other"


def _cut_cost(text, i):
    """把 text 切成 text[:i] / text[i:] 的代价,越低越好;None = 禁止在此切。

    日语/中文没有空格,脚本类转换代价近似词边界:假名后接汉字通常是新词开头,
    而汉字后接假名多半是同一个词的送り仮名,不能切。
    """
    if i <= 0 or i >= len(text):
        return None
    prev, nxt = text[i - 1], text[i]
    if nxt in NO_LINE_START or prev in NO_LINE_END:
        return None  # 禁则:闭合符号/小书假名/长音符不可行首,开括号不可行末
    if prev == " " or nxt == " ":
        return 0.0  # 空格是完美切点(clean 已把句中标点转成空格,即天然读点)
    a, b = _script_of(prev), _script_of(nxt)
    if a == "latin" and b == "latin":
        return None  # 不切开拉丁词
    return SCRIPT_BREAK_COST.get((a, b), 2.0)


def _split_body(body, budget):
    """按显示列 budget 把正文切成若干段,切点取代价最低者(平手时取最靠后)。"""
    if _width(body) <= budget:
        return [body]
    segs, rest = [], body
    while _width(rest) > budget:
        cut, w = 0, 0
        for i, ch in enumerate(rest):
            if w + _cw(ch) > budget:
                break
            w += _cw(ch)
            cut = i + 1
        cut = max(cut, 1)  # budget 小于单字宽时兜底,防死循环
        lo = max(1, cut // 3)
        best, best_score = None, None
        for i in range(cut, lo - 1, -1):
            c = _cut_cost(rest, i)
            if c is None:
                continue
            # 在切点质量与行宽利用率之间权衡:好切点值得留白,但不值得留太多
            score = c + (budget - _width(rest[:i].rstrip())) / budget * WASTE_WEIGHT
            if best_score is None or score < best_score:
                best, best_score = i, score
        if best is None:
            best = cut  # 候选全被禁则挡住,兜底硬切
        segs.append(rest[:best].rstrip())
        rest = rest[best:].lstrip()
    if rest:
        segs.append(rest)
    return [s for s in segs if s]


def _alloc(start, end, segs, min_dur_ms=0):
    """在 [start, end] 内按各段显示列数比例分配时间轴,首尾对齐原区间、段间不重叠。

    带 min_dur_ms 下界时用 water-filling:不足下界的段钉到下界,剩余时间在其余段按宽度重分,
    迭代至稳定 —— 即短段从长段借时间,而不是牺牲行宽把段合并回去。
    区间本身装不下 n 段下界时(异常输入)退化为均分。
    """
    span, n = end - start, len(segs)
    weights = [max(1, _width(s)) for s in segs]
    if min_dur_ms * n > span:
        durs = [span // n] * n
    else:
        pinned = [False] * n
        while True:
            free = span - min_dur_ms * sum(pinned)
            fw = sum(w for w, p in zip(weights, pinned) if not p)
            durs = [min_dur_ms if p else free * w // fw for w, p in zip(weights, pinned)]
            short = [i for i in range(n) if not pinned[i] and durs[i] < min_dur_ms]
            if not short:
                break
            for i in short:
                pinned[i] = True
    times, t = [], start
    for i, d in enumerate(durs):
        nxt = end if i == n - 1 else min(t + d, end)
        times.append((t, nxt))
        t = nxt
    return times


def _sentences(body):
    """按句末标点把正文切成若干句(标点留在句尾,其后的闭引号并入本句)。

    引号/括号内部的句号不断句(引用别人说的整句话是一句),数字里的 . 也不算句末。
    """
    out, buf, i, n, depth = [], "", 0, len(body), 0
    while i < n:
        ch = body[i]
        buf += ch
        i += 1
        if ch in OPEN and ch != '"':  # ASCII 直引号开闭同形,不参与配对计数
            depth += 1
        elif ch in CLOSE and ch != '"':
            depth = max(0, depth - 1)
        if ch not in SENT_END or depth:
            continue
        if ch in ".．" and len(buf) >= 2 and buf[-2].isdigit() and i < n and body[i].isdigit():
            continue  # 3.5 / １．５ 不是句末
        while i < n and (body[i] in SENT_END or body[i] in CLOSE):
            buf += body[i]  # 连续句末标点(!?、……)与随后的闭引号并入本句
            i += 1
        if i < n:  # 后面还有内容才断句
            out.append(buf.strip())
            buf = ""
    if buf.strip():
        out.append(buf.strip())
    return out


def split_entries(entries, max_width, max_dur_ms, min_dur_ms, report=None):
    """merge 的反向操作:把多句粘连的超长条目按句末标点拆成一句一条,时间轴按各句显示宽度比例分配。

    ASR 的分段依据是静音(VAD),说话人不停顿时十几句会被打包成一条、只在末尾补一个句号,
    这类条目在原文层就该拆开——原文字符数≈音节数≈时长,比例分配可靠;留到译文层的 resplit
    再切,分配依据变成译文字宽,跨语言字数比不恒定,时间轴会漂移。

    只有超出宽度或时长阈值的条目才拆(短的多句条目留在一起,翻译时上下文更完整);
    内部没有句末标点可切的超长条目原样保留并计入 report["stuck"],由主代理补句读后重跑。
    report 里的条目号是**产物**里的号(拆分会把后面的条目顺推),主代理拿着它直接去编辑产物。
    """
    out, done, stuck = [], [], []
    for e in entries:
        sp, body = _split_speaker(e["text"])
        over = _width(body) > max_width or e["end"] - e["start"] > max_dur_ms
        segs = _sentences(body) if over else [body]
        if not over or len(segs) <= 1:
            if over:
                stuck.append((len(out) + 1, e["end"] - e["start"], _width(body)))
            out.append(e)
            continue
        done.append((len(out) + 1, len(segs)))
        for s, (a, b) in zip(segs, _alloc(e["start"], e["end"], segs, min_dur_ms)):
            out.append({"start": a, "end": b, "text": _with_speaker(sp, s)})
    if report is not None:
        report["done"], report["stuck"] = done, stuck
    return out


def resplit_entries(entries, budget, min_dur_ms):
    """把整句译文切回观看用分条:每段不超行宽预算,说话人前缀每条都带且不占预算。"""
    out = []
    for e in entries:
        sp, body = _split_speaker(e["text"])
        segs = _split_body(body, budget) if body else [body]
        if len(segs) <= 1:
            out.append(e)
            continue
        for s, (a, b) in zip(segs, _alloc(e["start"], e["end"], segs, min_dur_ms)):
            out.append({"start": a, "end": b, "text": _with_speaker(sp, s)})
    return out


def check(base_path, target_path):
    """对比两份 SRT 的条目对齐情况。返回退出码:0=一致,1=有差异。"""
    base = parse(Path(base_path).read_text(encoding="utf-8-sig"))
    target = parse(Path(target_path).read_text(encoding="utf-8-sig"))
    n = min(len(base), len(target))
    ts_bad = [i + 1 for i in range(n)
              if abs(base[i]["start"] - target[i]["start"]) > 1 or abs(base[i]["end"] - target[i]["end"]) > 1]
    empty = [i + 1 for i, e in enumerate(target) if not _split_speaker(e["text"])[1].strip()]
    identical = [i + 1 for i in range(n) if base[i]["text"] == target[i]["text"]]
    print(f"base={len(base)} entries, target={len(target)} entries")  # ponytail: ASCII 输出
    ok = True
    if len(base) != len(target):
        print(f"  DIFF entry count: {len(base)} -> {len(target)} (diff {len(target) - len(base):+d})")
        ok = False
    if ts_bad:
        print(f"  DIFF timeline mismatch at {len(ts_bad)} entries: {_preview(ts_bad)}")
        ok = False
    if empty:
        print(f"  DIFF empty body at {len(empty)} entries: {_preview(empty)}")
        ok = False
    if identical:
        # 仅提示:日中翻译里纯汉字词/专名合法相同,但大量相同通常意味着漏译
        print(f"  NOTE identical to base at {len(identical)} entries (possible untranslated): {_preview(identical)}")
    if ok:
        print("OK: aligned")
    return 0 if ok else 1


def _preview(nums, limit=20):
    head = ", ".join(f"#{n}" for n in nums[:limit])
    return head + (f", ... (+{len(nums) - limit} more)" if len(nums) > limit else "")


def _median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def stats(path, lang=None, max_width=None, max_dur=LONG_ENTRY_SEC):
    """体检输入 SRT 的条目形态,判定该跑 merge(被行宽切碎)还是 split(多句粘连)。返回退出码 0。

    ASR 的两种失形是相反的:按显示行宽切的会把一句拆成三四条(多数条目不收句),
    按静音切的会把十几句打包成一条(条目收句、但又长又挤)。两者都要在翻译前整平。
    """
    entries = process(Path(path).read_text(encoding="utf-8-sig"), "normalize")
    style = _style_for(lang)
    if not max_width:
        max_width = LONG_ENTRY_FACTOR * (CJK_LINE_WIDTH if style == "cjk" else LATIN_LINE_WIDTH)
    max_dur_ms = int(max_dur * 1000)
    n = len(entries)
    bodies = [_split_speaker(e["text"])[1] for e in entries]
    durs = [e["end"] - e["start"] for e in entries]
    widths = [_width(b) for b in bodies]
    sents = [len(_sentences(b)) for b in bodies]
    unfinished = [i + 1 for i, b in enumerate(bodies) if not _ends_sentence(b)]
    long_ = [i + 1 for i in range(n) if widths[i] > max_width or durs[i] > max_dur_ms]
    stuck = [i for i in long_ if sents[i - 1] <= 1]
    print(f"entries={n}  total={_fmt(max(e['end'] for e in entries))}")  # ponytail: ASCII 输出
    print(f"duration/entry  min={min(durs) / 1000:.1f}s  median={_median(durs) / 1000:.1f}s  "
          f"max={max(durs) / 1000:.1f}s  (over {max_dur:.0f}s: {sum(d > max_dur_ms for d in durs)})")
    print(f"width/entry     min={min(widths)}  median={_median(widths):.0f}  "
          f"max={max(widths)} col  (over {max_width}: {sum(w > max_width for w in widths)})")
    ratio = len(unfinished) / n
    print(f"ends a sentence: {n - len(unfinished)}/{n} ({1 - ratio:.0%})")
    order = sorted(range(n), key=lambda i: -durs[i])[:5]
    print("longest: " + ", ".join(
        f"#{i + 1} ({durs[i] / 1000:.1f}s, {widths[i]}col, {sents[i]} sent)" for i in order))
    print("VERDICT")
    if ratio >= UNFINISHED_RATIO:
        print(f"  merge: NEEDED -- {len(unfinished)}/{n} ({ratio:.0%}) entries do not end a sentence, "
              "i.e. one sentence is spread over several entries")
    else:
        print(f"  merge: not needed -- only {len(unfinished)}/{n} ({ratio:.0%}) entries do not end a sentence")
    if long_:
        print(f"  split: NEEDED -- {len(long_)} entries over {max_width}col or {max_dur:.0f}s: {_preview(long_)}")
        if stuck:
            print(f"    {len(stuck)} of them have no sentence punctuation inside, `split` cannot cut them: "
                  f"{_preview(stuck)}")
            print("    -> add sentence punctuation to these while fixing the transcript, then run `split`")
    else:
        print(f"  split: not needed -- no entry over {max_width}col or {max_dur:.0f}s")
    return 0


def process(text, mode, lang=None, **opts):
    entries = parse(text)
    if not entries:
        sys.exit("ERROR: no subtitle entries parsed")
    style = _style_for(lang)  # clean/split/resplit 模式用;normalize、merge 不受 style 影响
    entries.sort(key=lambda e: e["start"])
    for e in entries:
        if e["end"] < e["start"]:
            e["start"], e["end"] = e["end"], e["start"]
        if mode == "clean":
            e["text"] = clean_text(e["text"], style)
    if mode == "merge":
        entries = merge_entries(entries, int(opts["max_gap"] * 1000), int(opts["max_merged_duration"] * 1000))
    elif mode == "split":
        max_width = opts.get("max_width") or LONG_ENTRY_FACTOR * (
            CJK_LINE_WIDTH if style == "cjk" else LATIN_LINE_WIDTH)
        entries = split_entries(entries, max_width, int(opts["max_duration"] * 1000),
                                int(opts["min_duration"] * 1000), opts.get("report"))
    elif mode == "resplit":
        budget = opts.get("max_line_width") or (CJK_LINE_WIDTH if style == "cjk" else LATIN_LINE_WIDTH)
        entries = resplit_entries(entries, budget, int(opts["min_duration"] * 1000))
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
- `{stem}_merged.srt` — `merge` 产物：按行宽切碎的条目合并回整句（输入本来就一句一条时没有这个文件）
- `{stem}_fix.srt` — 转录修正稿（原语言，一条一整句，纠正听录错误；`split` 原地作用于它）
- `{stem}_<lang>.srt` — 翻译初稿
- `{stem}_<lang>_fix.srt` — 复核稿
- `{stem}_<lang>_split.srt` — 重切分终稿，**交付给用户的就是这一份**
- `AGENTS.md` — 本文件，说明结构与流程
- `_context/` — 背景资料区
  - `brief.md` — 背景简报：内容概述、专名、疑似听录错误。修正/翻译/复核前都要读。
  - `glossary.md` — 术语表：原语言 → 目标语言标准译名（含说话人名）。翻译/复核必须遵循。
  - `research/` — 调研子代理产出的原始文件（`NN-topic.md`）。简报与术语表由它提炼而来；不够时回这里查细节。

## 流程

翻译全程走「一条一整句」：先把 ASR 的两种失形都整平——被行宽切碎的合并回整句（`merge`），
按静音粘连成一大坨的拆成一句一条（`split`）——再翻译（语义完整、时间轴对得上，译文质量最高），
最后一步才按目标语言行宽切回观看用分条。所以中间产物条目少而长，属正常。

0. 跑 `stats` 体检，看 `VERDICT` 判定该 `merge` 还是 `split`（或都不需要）
1. 建工作目录（已完成，由 `srt_tools.py init` 生成本文件与 `_context/` 占位）
2. 问清原始/目标语言、主题、各说话人是谁；通读 `{stem}.srt` 提炼专名与引述段落；派调研子代理把结果写入 `_context/research/`；主代理读调研文件后编辑 `_context/brief.md` 和 `_context/glossary.md`
3. 跑 `merge` → 复制为 `{stem}_fix.srt` → 主代理对照简报/术语表**定点 Edit** 纠错、给超长条目补句读 → 跑 `split`（没跑 `split` 则跑 `normalize`）
4. 派翻译子代理（先读 `_context/brief.md`、`_context/glossary.md`、规范）→ `{stem}_<lang>.srt`，跑 `clean` + `check`
5. 派复核子代理（先复制再定点 Edit）→ `{stem}_<lang>_fix.srt`，跑 `clean` + `check`
6. 跑 `resplit` 切回观看用分条 → `{stem}_<lang>_split.srt`
7. 主代理抽查终稿，向用户报告产出路径、术语表、修正要点
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
        sys.exit(f"ERROR: not a valid .srt file: {src}")
    stem = src.stem
    workdir = src.parent / stem
    if workdir.exists():
        sys.exit(f"ERROR: workspace already exists (this script never overwrites): {workdir}")
    context = workdir / "_context"
    research = context / "research"
    workdir.mkdir()
    context.mkdir()
    research.mkdir()
    shutil.copy2(src, workdir / src.name)
    (workdir / "AGENTS.md").write_text(AGENTS_MD_TEMPLATE.format(stem=stem), encoding="utf-8", newline="\n")
    (context / "brief.md").write_text(BRIEF_MD_TEMPLATE.format(stem=stem), encoding="utf-8", newline="\n")
    (context / "glossary.md").write_text(GLOSSARY_MD_TEMPLATE.format(stem=stem), encoding="utf-8", newline="\n")
    print(f"OK: workspace created -> {workdir}")
    print(f"  - {workdir / src.name}")
    print(f"  - {workdir / 'AGENTS.md'}")
    print(f"  - {context / 'brief.md'} (placeholder)")
    print(f"  - {context / 'glossary.md'} (placeholder)")
    print(f"  - {research} (empty)")


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
    # 说话人前缀:原样透传,只清理正文
    assert clean_text("丸岡和佳奈: 本日の、ワード。") == "丸岡和佳奈: 本日の ワード"
    assert clean_text("speaker_0: Hello, world.", "western") == "speaker_0: Hello, world."
    assert clean_text("丸岡和佳奈：本日の") == "丸岡和佳奈 本日の"  # 冒号后无空格,不当作前缀
    assert clean_text("集合は12:30だよ。") == "集合は12:30だよ"  # 时间不被误判为前缀
    assert clean_text("丸岡和佳奈: 。") == ""  # 正文清空 -> 整条作废,不留 `说话人: ` 空壳
    assert _split_speaker("丸岡和佳奈: 本日の") == ("丸岡和佳奈", "本日の")
    assert _split_speaker("本日のワード") == ("", "本日のワード")
    assert _width("今天的侘寂词") == 12 and _width("Hello") == 5
    assert _ends_sentence("そうですね。") and _ends_sentence("「はい。」") and not _ends_sentence("本日の")
    # merge: 未收句 + 同说话人 + 间隔够近 -> 合并,时间轴取并集
    two = ("1\n00:00:01,000 --> 00:00:02,000\nspeaker_0: 本日の\n\n"
           "2\n00:00:02,000 --> 00:00:04,000\nspeaker_0: ワード。\n")
    merged = process(two, "merge", max_gap=2.0, max_merged_duration=20.0)
    assert [e["text"] for e in merged] == ["speaker_0: 本日のワード。"]
    assert merged[0]["start"] == 1000 and merged[0]["end"] == 4000
    # merge 的四条否决路径:已收句 / 说话人不同 / 间隔过大 / 音频事件条目
    ended = two.replace("speaker_0: 本日の\n", "speaker_0: 本日の。\n")
    assert len(process(ended, "merge", max_gap=2.0, max_merged_duration=20.0)) == 2
    other = two.replace("2\n00:00:02,000 --> 00:00:04,000\nspeaker_0:", "2\n00:00:02,000 --> 00:00:04,000\nspeaker_1:")
    assert len(process(other, "merge", max_gap=2.0, max_merged_duration=20.0)) == 2
    assert len(process(two, "merge", max_gap=0.0, max_merged_duration=20.0)) == 1  # gap 恰为 0,仍合并
    far = two.replace("00:00:02,000 --> 00:00:04,000", "00:00:09,000 --> 00:00:11,000")
    assert len(process(far, "merge", max_gap=2.0, max_merged_duration=20.0)) == 2
    assert len(process(two, "merge", max_gap=2.0, max_merged_duration=1.5)) == 2  # 合并后 3s 超上限
    event = ("1\n00:00:01,000 --> 00:00:02,000\n[オープニングミュージック]\n\n"
             "2\n00:00:02,000 --> 00:00:04,000\n本日の\n")
    assert len(process(event, "merge", max_gap=2.0, max_merged_duration=20.0)) == 2  # 音频事件不被吞并
    # _sentences: 句末标点断句,引号内与数字里的 . 不断
    assert _sentences("はい。そうです。") == ["はい。", "そうです。"]
    assert _sentences("一文だけです。") == ["一文だけです。"]
    assert _sentences("3.5です。ね") == ["3.5です。", "ね"]
    assert _sentences("「はい。」と言った。ね") == ["「はい。」と言った。", "ね"]
    assert _sentences("本当に?!すごい") == ["本当に?!", "すごい"]
    # split: 多句粘连的超长条目按句末标点拆成一句一条(merge 的反向),时间轴按宽度比例分配
    glued = ("1\n00:00:00,000 --> 00:00:20,000\n"
             "speaker_0: 一つ目の文です。二つ目の文です。三つ目の文です。\n")
    rep = {}
    sp_parts = process(glued, "split", lang="ja", max_width=None, max_duration=12.0,
                       min_duration=1.0, report=rep)
    assert [p["text"] for p in sp_parts] == ["speaker_0: 一つ目の文です。",
                                             "speaker_0: 二つ目の文です。",
                                             "speaker_0: 三つ目の文です。"]
    assert sp_parts[0]["start"] == 0 and sp_parts[-1]["end"] == 20000  # 首尾对齐原区间
    assert all(sp_parts[i]["end"] == sp_parts[i + 1]["start"] for i in range(len(sp_parts) - 1))
    assert rep["done"] == [(1, 3)] and rep["stuck"] == []
    # 阈值内的多句条目不拆:短条目留在一起,翻译时上下文更完整
    assert len(process("1\n00:00:00,000 --> 00:00:03,000\nはい。そうです。\n", "split", lang="ja",
                       max_width=None, max_duration=12.0, min_duration=1.0, report={})) == 1
    # 宽度超限也触发拆分(即使时长没超)
    wide_glued = "1\n00:00:00,000 --> 00:00:05,000\n" + "あいうえおかきくけこ。" * 6 + "\n"
    assert len(process(wide_glued, "split", lang="ja", max_width=None, max_duration=12.0,
                       min_duration=0.0, report={})) == 6
    # 超长但内部无句读 -> 原样保留,stuck 记产物里的条目号(前面的拆分会把它顺推)
    rep2 = {}
    stuck_src = ("1\n00:00:00,000 --> 00:00:20,000\n一つ目の文です。二つ目の文です。\n\n"
                 "2\n00:00:20,000 --> 00:00:40,000\nずっと句読点がないまま話し続けている長い一文。\n")
    kept = process(stuck_src, "split", lang="ja", max_width=None, max_duration=12.0,
                   min_duration=1.0, report=rep2)
    assert len(kept) == 3 and [i for i, _, _ in rep2["stuck"]] == [3]
    # stats: 只读体检,不写文件
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "s.srt"
        p.write_text(glued, encoding="utf-8")
        assert stats(str(p), lang="ja") == 0
    # resplit: 超宽整句切回分条,前缀每条都带且不占预算
    long_zh = "speaker_0: 今天的侘寂词 从大家投稿的侘寂词里选出想到的东西说出来 然后清爽地总结一下"
    wide = f"1\n00:00:00,000 --> 00:00:12,000\n{long_zh}\n"
    parts = process(wide, "resplit", lang="zh", min_duration=1.0, max_line_width=None)
    assert len(parts) > 1
    assert all(p["text"].startswith("speaker_0: ") for p in parts)
    assert all(_width(_split_speaker(p["text"])[1]) <= CJK_LINE_WIDTH for p in parts)
    assert all(p["end"] - p["start"] >= 1000 for p in parts)  # 无闪现
    assert parts[0]["start"] == 0 and parts[-1]["end"] == 12000  # 首尾对齐原区间
    assert all(parts[i]["end"] == parts[i + 1]["start"] for i in range(len(parts) - 1))  # 单调不重叠
    assert "".join(_split_speaker(p["text"])[1].replace(" ", "") for p in parts) == \
        _split_speaker(long_zh)[1].replace(" ", "")  # 切分不丢字
    # min-duration 抬高后段数不变(行宽是硬约束),短段从长段借时间达标
    narrow = process(wide, "resplit", lang="zh", min_duration=2.5, max_line_width=None)
    assert len(narrow) == len(parts)
    assert all(p["end"] - p["start"] >= 2500 for p in narrow)
    assert narrow[0]["start"] == 0 and narrow[-1]["end"] == 12000
    assert len(process("1\n00:00:00,000 --> 00:00:02,000\n短句\n", "resplit", lang="zh",
                       min_duration=1.0, max_line_width=None)) == 1  # 预算内原样透传
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
    # check: 条目数/时间轴对齐
    with tempfile.TemporaryDirectory() as d:
        base = Path(d) / "base.srt"
        base.write_text("1\n00:00:01,000 --> 00:00:02,000\n本日の\n\n"
                        "2\n00:00:02,000 --> 00:00:03,000\nワード\n", encoding="utf-8")
        good = Path(d) / "good.srt"
        good.write_text("1\n00:00:01,000 --> 00:00:02,000\n今天的\n\n"
                        "2\n00:00:02,000 --> 00:00:03,000\n词\n", encoding="utf-8")
        assert check(str(base), str(good)) == 0
        short = Path(d) / "short.srt"
        short.write_text("1\n00:00:01,000 --> 00:00:02,000\n今天的\n", encoding="utf-8")
        assert check(str(base), str(short)) == 1  # 条目数不一致
        shifted = Path(d) / "shifted.srt"
        shifted.write_text("1\n00:00:01,000 --> 00:00:02,000\n今天的\n\n"
                           "2\n00:00:02,500 --> 00:00:03,000\n词\n", encoding="utf-8")
        assert check(str(base), str(shifted)) == 1  # 时间轴错位
        assert check(str(base), str(base)) == 0  # 全同 -> 仅 NOTE 提示漏译,不算失败
    print("self-test OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=["init", "stats", "merge", "split", "normalize", "clean", "resplit", "check"],
                    nargs="?")
    ap.add_argument("input", nargs="?")
    ap.add_argument("input2", nargs="?", help="check 模式的第二个文件(target)")
    ap.add_argument("-o", "--output")
    ap.add_argument("-l", "--lang", help=f"语言(ISO 639-1,如 zh/ja/en)。决定 clean 的标点风格与 resplit 的行宽:cjk=逗号转空格/{CJK_LINE_WIDTH} 列,其余=保留句中标点/{LATIN_LINE_WIDTH} 列。clean/resplit 传目标语言,stats/split 作用于原文、传原文语言")
    ap.add_argument("--max-gap", type=float, default=2.0, help="merge: 超过该静音秒数就不再合并(默认 2.0)")
    ap.add_argument("--max-merged-duration", type=float, default=20.0, help="merge: 合并后单条时长上限秒数(默认 20)")
    ap.add_argument("--max-width", type=int, help=f"stats/split: 超长条目的宽度阈值(全角算 2 列)。缺省按 -l 取行宽的 {LONG_ENTRY_FACTOR} 倍,即 cjk {LONG_ENTRY_FACTOR * CJK_LINE_WIDTH} / 其余 {LONG_ENTRY_FACTOR * LATIN_LINE_WIDTH}")
    ap.add_argument("--max-duration", type=float, default=LONG_ENTRY_SEC, help=f"stats/split: 超长条目的时长阈值秒数(默认 {LONG_ENTRY_SEC:.0f})")
    ap.add_argument("--max-line-width", type=int, help=f"resplit: 每条最大显示列宽(全角算 2 列)。缺省按 -l 取 cjk {CJK_LINE_WIDTH} / 其余 {LATIN_LINE_WIDTH}")
    ap.add_argument("--min-duration", type=float, default=1.0, help="resplit: 切分出的段的最短秒数,不足则从相邻长段借时间(默认 1.0)。无需切分、原样透传的条目不受影响")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if not args.mode or not args.input:
        ap.error("mode and input are required")
    if args.mode == "init":
        return init_workspace(args.input)
    if args.mode == "stats":
        return sys.exit(stats(args.input, args.lang, args.max_width, args.max_duration))
    if args.mode == "check":
        if not args.input2:
            ap.error("check needs two files: check <base.srt> <target.srt>")
        return sys.exit(check(args.input, args.input2))
    report = {}
    src = process(Path(args.input).read_text(encoding="utf-8-sig"), "normalize") if args.mode == "merge" else None
    entries = process(
        Path(args.input).read_text(encoding="utf-8-sig"), args.mode, lang=args.lang,
        max_gap=args.max_gap, max_merged_duration=args.max_merged_duration,
        max_width=args.max_width, max_duration=args.max_duration,
        max_line_width=args.max_line_width, min_duration=args.min_duration, report=report,
    )
    out = args.output or args.input
    Path(out).write_text(serialize(entries), encoding="utf-8", newline="\n")
    print(f"OK: {len(entries)} entries -> {out}")  # ponytail: ASCII 输出,避开 Windows 控制台编码问题
    if args.mode == "merge":
        print(f"  merged: {len(src)} -> {len(entries)} entries")
        longest = sorted(range(len(entries)), key=lambda i: entries[i]["start"] - entries[i]["end"])[:5]
        detail = ", ".join(f"#{i + 1} ({(entries[i]['end'] - entries[i]['start']) / 1000:.1f}s)" for i in sorted(longest))
        print(f"  longest entries (spot-check these): {detail}")
    if args.mode == "split":
        done, stuck = report.get("done", []), report.get("stuck", [])
        if done:
            print(f"  split: {len(done)} long entries -> {sum(n for _, n in done)} entries")
        if stuck:
            detail = ", ".join(f"#{i} ({d / 1000:.1f}s, {w}col)" for i, d, w in stuck[:10])
            print(f"  WARN {len(stuck)} entries still over limit, no sentence punctuation to cut on: {detail}")
            print("       add sentence punctuation to these, then run split again")


if __name__ == "__main__":
    main()
