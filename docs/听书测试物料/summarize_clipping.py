# -*- coding: utf-8 -*-
"""汇总西语削波事件：每文件总事件数 + 最长削波段（供人工复测）。"""
import json
from pathlib import Path

OUT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\梦成接口_XR3_英西")
data = json.loads((OUT / "西语削波时间段.json").read_text(encoding="utf-8"))

lines = []
lines.append("# 西语削波时间段（人工复测用）\n")
lines.append("西语生成音频削波为**遍布全片**的短促过载，以下列出每文件总事件数与最长的 5 个削波段。\n")
lines.append("| 文件 | 时长 | 削波样本 | 事件数 | 最长事件 | 建议复测时间段（前5） |")
lines.append("|------|------|----------|--------|----------|------------------------|")

for d in data:
    evs = d["events"]
    top = sorted(evs, key=lambda e: -e["duration_s"])[:5]
    ranges = "；".join(f"{e['start_hms']}–{e['end_hms']}" for e in top)
    longest = max(evs, key=lambda e: e["duration_s"])
    lines.append(
        f"| {d['file']} | {d['duration_s']}s | {d['clipped_samples']} | {d['event_count']} | "
        f"{longest['duration_s']*1000:.0f}ms | {ranges} |"
    )

txt = "\n".join(lines) + "\n"
out_md = OUT / "西语削波复测时间段.md"
out_md.write_text(txt, encoding="utf-8")
print(txt)
print("已保存:", out_md)