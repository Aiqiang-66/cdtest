# -*- coding: utf-8 -*-
"""导出 0910 17:46 批次（英语/德语/俄语章）全部丢失块的参考时间区间，供人工复测。"""
import difflib
import json
import re
import unicodedata
from pathlib import Path

OUT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\Higgs_全语种单章_0910")
TXT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\txt文本")
REPORT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\测试报告"
              r"\Higgs并发文案丢失_丢失位置明细_0910.md")

CONFIGS = [
    ("英语", "XR3 - EN.txt", r"^===\s*Chapter\s+\d+"),
    ("德语", "XR3 - DE.txt", r"^===\s*Kapitel\s+\d+"),
    ("俄语", "XR3 - RU.txt", r"^===\s*Глава\s+\d+"),
]

_EDGE = re.compile(r"^[^\w']+|[^\w']+$")


def tk(s):
    s = unicodedata.normalize("NFKC", s).replace("\u2019", "'")
    return [w for w in (_EDGE.sub("", x).lower() for x in s.split()) if w]


def fms(ms):
    return "%02d:%02d:%02d.%03d" % (ms // 3600000, (ms % 3600000) // 60000,
                                    (ms % 60000) // 1000, ms % 1000)


lines = ["# Higgs TTS 文案丢失位置明细（0910 17:46 批次）", "",
         "对象：`docs/听书测试物料/mp3/Higgs_全语种单章_0910` 下英语/德语/俄语第 1 章产物。",
         "时间列为该处丢失在音频中的参考区间（取相邻字幕段边界），可直接定位试听。", ""]

for cn, fname, pattern in CONFIGS:
    text = (TXT / fname).read_text(encoding="utf-8-sig")
    ms = list(re.finditer(pattern, text, flags=re.MULTILINE))
    body = text[ms[0].end():ms[1].start()].strip()
    segs = json.loads((OUT / f"{cn}_XR3_Ch1.json").read_text(encoding="utf-8"))
    sent = tk(body)

    ret, tok_seg, spans = [], [], []
    for idx, s in enumerate(segs):
        t = tk(s.get("text") or "")
        if not t:
            continue
        spans.append((s.get("startMs", 0), s.get("endMs", 0)))
        for _ in t:
            tok_seg.append(len(spans) - 1)
        ret.extend(t)

    sm = difflib.SequenceMatcher(a=sent, b=ret, autojunk=False)
    lines.append(f"## {cn}（原文 {len(sent)} 词 / 产物 {len(ret)} 词）")
    lines.append("")
    lines.append("| # | 参考时间区间 | 缺失词 | 原文上下文 |")
    lines.append("|---|--------------|--------|------------|")
    n = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag not in ("delete", "replace") or not sent[i1:i2]:
            continue
        n += 1
        seg_idx = tok_seg[j1] if j1 < len(tok_seg) else (len(spans) - 1 if spans else 0)
        prev_end = spans[seg_idx - 1][1] if seg_idx > 0 else 0
        next_start = spans[seg_idx][0] if spans else 0
        rng = f"{fms(prev_end)} → {fms(next_start)}"
        ctx = " ".join(sent[max(0, i1 - 6):i2 + 4])
        miss = " ".join(sent[i1:i2])
        lines.append(f"| {n} | {rng} | {miss} | ...{ctx} |")
    lines.append("")
    print(f"{cn}: {n} 处丢失")

REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"已写入：{REPORT}")
