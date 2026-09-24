# -*- coding: utf-8 -*-
"""定位整章产物的丢失位置：连续缺失文本块 + 时间轴空洞。"""
import difflib
import json
import re
import unicodedata
from pathlib import Path

OUT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\Higgs_全语种单章_0910")
TXT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\txt文本")

CONFIGS = [
    ("英语", "XR3 - EN.txt", r"^===\s*Chapter\s+\d+"),
    ("德语", "XR3 - DE.txt", r"^===\s*Kapitel\s+\d+"),
    ("俄语", "XR3 - RU.txt", r"^===\s*Глава\s+\d+"),
]

_EDGE = re.compile(r"^[^\w']+|[^\w']+$")


def tk(s):
    s = unicodedata.normalize("NFKC", s).replace("\u2019", "'")
    return [w for w in (_EDGE.sub("", x).lower() for x in s.split()) if w]


def chapter1(fname, pattern):
    text = (TXT / fname).read_text(encoding="utf-8-sig")
    ms = list(re.finditer(pattern, text, flags=re.MULTILINE))
    return text[ms[0].end():(ms[1].start() if len(ms) > 1 else len(text))].strip()


def fms(ms):
    return "%02d:%02d:%06.3f" % (ms // 3600000, (ms % 3600000) // 60000, (ms % 60000) / 1000.0)


for cn, fname, pattern in CONFIGS:
    body = chapter1(fname, pattern)
    segs = json.loads((OUT / f"{cn}_XR3_Ch1.json").read_text(encoding="utf-8"))
    sent = tk(body)
    ret = []
    times = []
    for s in segs:
        t = tk(s.get("text") or "")
        if not t:
            continue
        ret.extend(t)
        times.append((s.get("startMs", 0), s.get("endMs", 0)))

    print("=" * 78)
    print(f"=== {cn} === 原文 {len(sent)} 词 / 返回 {len(ret)} 词 / 段 {len(segs)}")

    sm = difflib.SequenceMatcher(a=sent, b=ret, autojunk=False)
    runs = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("delete", "replace") and sent[i1:i2]:
            runs.append((i1, i2, sent[i1:i2]))
    total = sum(b - a for a, b, _ in runs)
    print(f"连续缺失块 {len(runs)} 个，合计 {total} 词（{100.0*total/len(sent):.2f}%）")
    for a, b, words in runs[:12]:
        ctx = " ".join(sent[max(0, a - 8):a])
        print(f"  - 原文第 {a}-{b} 词（{b-a} 词）| 上文: ...{ctx[-70:]}")
        print(f"    缺失: {' '.join(words)[:160]}")

    gaps = []
    for i in range(1, len(times)):
        d = times[i][0] - times[i - 1][1]
        if d > 3000:
            gaps.append((i, d, times[i - 1][1], times[i][0]))
    print(f"时间轴空洞（相邻段间隔 > 3s）：{len(gaps)} 个")
    for i, d, a, b in gaps[:10]:
        print(f"  - 第 {i} 段后空洞 {d/1000.0:.1f}s（{fms(a)} -> {fms(b)}）")
    print()
