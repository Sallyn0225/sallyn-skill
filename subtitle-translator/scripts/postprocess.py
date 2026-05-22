#!/usr/bin/env python3
"""
SRT post-process for subtitle-translator skill.

Normalizes a (already-translated) Chinese SRT file by:
1. Folding intra-entry line breaks into a single line (the original transcription
   may have wrapped long lines for character-count limits, with no semantic meaning).
2. Stripping bracketed transcription annotations like [拍手] / [笑い] / [音楽] —
   these are stage-direction tags inserted by the ASR model, not spoken content,
   and don't belong in the final subtitle. Only half-width [] are touched;
   Chinese 【】 is left alone.
3. Stripping any trailing "single" punctuation marks from each entry — Chinese
   subtitles conventionally do not end with a punctuation mark.
4. Replacing in-text single punctuation marks (commas, periods, question marks,
   exclamations, etc.) with a single space; collapsing runs of whitespace to one
   space. "Paired" symbols like 「」 《》 () "" '' are left untouched.
5. Dropping entries that became empty after the above steps, and re-numbering.
6. If two adjacent entries have a gap in (0, 300ms), snap the earlier entry's
   end time to the later entry's start time, eliminating the visible flicker.

Usage:
    python postprocess.py <input.srt> <output.srt>

Input and output may be the same path (in-place rewrite).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Punctuation that should be removed at the end of an entry and replaced with a
# space when it appears mid-entry. Both half-width (English) and full-width
# (Chinese / Japanese) variants are included.
SINGLE_PUNCT = set("。.,，、;；:：?？!！…—–-")

TIME_RE = re.compile(
    r"(\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})"
)


def parse_srt(text: str) -> list[dict]:
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    blocks = re.split(r"\n[ \t]*\n+", text)
    entries: list[dict] = []
    for block in blocks:
        lines = block.split("\n")
        if len(lines) < 3:
            continue
        idx_line = lines[0].strip().lstrip("﻿")
        if not idx_line.isdigit():
            # tolerate missing index line by trying to read from line 0 as timecode
            m = TIME_RE.search(lines[0])
            if not m:
                continue
            start, end = m.groups()
            body = lines[1:]
        else:
            m = TIME_RE.search(lines[1])
            if not m:
                continue
            start, end = m.groups()
            body = lines[2:]
        while body and not body[-1].strip():
            body.pop()
        entries.append({"start": start, "end": end, "lines": body})
    return entries


def time_to_ms(t: str) -> int:
    t = t.replace(".", ",")
    hh, mm, sms = t.split(":")
    ss, ms = sms.split(",")
    return int(hh) * 3_600_000 + int(mm) * 60_000 + int(ss) * 1_000 + int(ms)


def ms_to_time(total_ms: int) -> str:
    if total_ms < 0:
        total_ms = 0
    hh, rem = divmod(total_ms, 3_600_000)
    mm, rem = divmod(rem, 60_000)
    ss, ms = divmod(rem, 1_000)
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"


def fold_lines(lines: list[str]) -> str:
    # Join with a single space; collapse runs of whitespace later.
    return " ".join(line.strip() for line in lines if line.strip())


def strip_bracket_annotations(text: str) -> str:
    """Remove half-width [xxx] annotations (e.g. [拍手], [笑い], [音楽]).
    Chinese 【】 is left untouched in case it's used meaningfully."""
    return re.sub(r"\[[^\[\]]*\]", "", text)


def normalize_punctuation(text: str) -> str:
    # 1. Strip trailing single-punct (allow several in a row, plus any whitespace).
    while text and (text[-1] in SINGLE_PUNCT or text[-1].isspace()):
        text = text[:-1]
    # 2. In-text single-punct → space.
    out_chars = []
    for ch in text:
        out_chars.append(" " if ch in SINGLE_PUNCT else ch)
    text = "".join(out_chars)
    # 3. Collapse whitespace runs.
    text = re.sub(r"\s+", " ", text).strip()
    return text


def adjust_timing(entries: list[dict]) -> list[dict]:
    for i in range(len(entries) - 1):
        cur_end = time_to_ms(entries[i]["end"])
        next_start = time_to_ms(entries[i + 1]["start"])
        gap = next_start - cur_end
        if 0 < gap < 300:
            entries[i]["end"] = entries[i + 1]["start"]
    return entries


def render_srt(entries: list[dict]) -> str:
    blocks = []
    for new_idx, e in enumerate(entries, 1):
        text = e["lines"] if isinstance(e["lines"], str) else "\n".join(e["lines"])
        # Normalize separators in timecode (always use comma)
        start = e["start"].replace(".", ",")
        end = e["end"].replace(".", ",")
        blocks.append(f"{new_idx}\n{start} --> {end}\n{text}")
    return "\n\n".join(blocks) + "\n"


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: postprocess.py <input.srt> <output.srt>", file=sys.stderr)
        return 1
    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])

    raw = in_path.read_text(encoding="utf-8-sig")
    entries = parse_srt(raw)

    for e in entries:
        text = fold_lines(e["lines"])
        text = strip_bracket_annotations(text)
        text = normalize_punctuation(text)
        e["lines"] = text

    entries = [e for e in entries if e["lines"]]
    entries = adjust_timing(entries)

    out_path.write_text(render_srt(entries), encoding="utf-8")
    print(f"Wrote {len(entries)} entries to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
