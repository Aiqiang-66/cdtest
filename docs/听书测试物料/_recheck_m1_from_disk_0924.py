# -*- coding: utf-8 -*-
"""独立复核：从留证文件（src 下发原文 + meta 返回 JSON）重算输入/输出文案一致性（M1）。

不依赖跑批时的内存统计，直接读盘复算，用于验证 M1 结论可复现。
口径：NFKC → 统一引号 → 去首尾标点 → 小写；日语按字级（无空格），韩语按词级（空格分词）+ 字级交叉。
注意：返回文本只取正文段（paraIndex>=0），标题段（paraIndex=-1，即 chapter_title）不计入。
"""
import difflib
import json
import re
import unicodedata
from pathlib import Path

MP3 = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3")
RUNS = {"ja": ("日语", MP3 / "Higgs_日语_10并发30分钟_0924"),
        "ko": ("韩语", MP3 / "Higgs_韩语_10并发30分钟_0924")}
_EDGE = re.compile(r"^[^\w']+|[^\w']+$")


def word_tokens(s):
    s = unicodedata.normalize("NFKC", s)
    s = (s.replace("\u2019", "'").replace("\u2018", "'")
          .replace("\u201c", '"').replace("\u201d", '"')
          .replace("\u2014", " ").replace("\u2013", " ").replace("\u2015", " "))
    return [w for w in (_EDGE.sub("", t).lower() for t in s.split()) if w]


def char_tokens(s):
    return [c for c in unicodedata.normalize("NFKC", s) if not c.isspace()]


def diff(a, b):
    if a == b:
        return [], [], 1.0
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    miss, extra = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("delete", "replace"):
            miss.extend(a[i1:i2])
        if tag in ("insert", "replace"):
            extra.extend(b[j1:j2])
    return miss, extra, sm.ratio()


for lang, (cn, run) in RUNS.items():
    tasks = {}
    for line in (run / "tasks.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            tasks[r["seq"]] = r
    tot_c = tot_w = 0
    miss_c = miss_w = ex_c = ex_w = 0
    identical = 0
    diffs = []
    checked = 0
    for seq, rec in sorted(tasks.items()):
        src = run / "src" / f"task_{seq:04d}.txt"
        meta = run / "meta" / f"task_{seq:04d}.json"
        if not src.exists() or not meta.exists():
            continue
        checked += 1
        sent = src.read_text(encoding="utf-8")
        segs = json.loads(meta.read_text(encoding="utf-8"))
        body = " ".join((s.get("text") or "") for s in segs if s.get("paraIndex", -1) >= 0)
        title = " ".join((s.get("text") or "") for s in segs if s.get("paraIndex", -1) < 0)

        sc, rc = char_tokens(sent), char_tokens(body)
        sw, rw = word_tokens(sent), word_tokens(body)
        mc, ec, ratio_c = diff(sc, rc)
        mw, ew, ratio_w = diff(sw, rw)
        tot_c += len(sc); tot_w += len(sw)
        miss_c += len(mc); miss_w += len(mw); ex_c += len(ec); ex_w += len(ew)
        if not mc and not ec:
            identical += 1
        if mc or ec or mw or ew:
            diffs.append({"seq": seq, "taskId": rec.get("taskId"), "chars": len(sent),
                          "title_len": len(title), "miss_c": len(mc), "miss_w": len(mw),
                          "miss_w_tokens": mw[:5], "sim_c": round(ratio_c, 4), "sim_w": round(ratio_w, 4)})

    print("=" * 78)
    print(f"[{cn}] 复核任务 {checked} 个（读 src + meta 重算）")
    print(f"  字级：发送 {tot_c:,} 字｜缺失 {miss_c}（{100*miss_c/max(1,tot_c):.4f}%）｜多余 {ex_c}")
    print(f"  词级：发送 {tot_w:,} 词｜缺失 {miss_w}（{100*miss_w/max(1,tot_w):.4f}%）｜多余 {ex_w}")
    print(f"  逐字符完全一致（无缺失且无多余）任务：{identical}/{checked}")
    for d in diffs:
        print(f"  差异任务 seq={d['seq']} taskId={d['taskId']}｜字级缺 {d['miss_c']}/词级缺 {d['miss_w']}"
              f"｜词级缺失 token={d['miss_w_tokens']}｜字级相似度 {d['sim_c']}")
