# -*- coding: utf-8 -*-
"""量化「静默占位段」签名：统计超长 segment（远长于其文本应有语速）在 metadata 中的出现情况。

依据：日语 task_0035 idx12（27 字对应 81.64s）与韩语 task_0044 idx55（1739 字对应 81.64s）
两者段时长**完全相同 = 81.64s**，且对应音频近乎无声 → 判定为"合成失败后插入的固定时长静默占位"。
本脚本按该签名全量扫描，给出受影响任务数与段数。
"""
import json
from pathlib import Path

MP3 = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3")
RUNS = {"ja": ("日语", MP3 / "Higgs_日语_10并发30分钟_0924"),
        "ko": ("韩语", MP3 / "Higgs_韩语_10并发30分钟_0924")}
LONG_MS = 60000          # 段时长 > 60s 即疑似占位
PLACEHOLDER_MS = 81640   # 观测到的占位时长
TOL_MS = 300


def cps(text, dur_s):
    """字/秒：用于判断该段时长是否与文本量严重不符"""
    return len(text) / dur_s if dur_s > 0 else 0


result = {"long_ms": LONG_MS, "placeholder_ms": PLACEHOLDER_MS, "langs": {}}

for lang, (cn, run) in RUNS.items():
    rows = []
    for line in (run / "tasks.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if not r.get("ok"):
            continue
        segs = json.loads((run / "meta" / f"task_{r['seq']:04d}.json").read_text(encoding="utf-8"))
        for s in segs:
            dur_ms = s.get("endMs", 0) - s.get("startMs", 0)
            if dur_ms <= LONG_MS:
                continue
            txt = (s.get("text") or "").strip()
            rows.append({
                "seq": r["seq"], "paraIndex": s.get("paraIndex"),
                "start_s": round(s.get("startMs", 0) / 1000, 2),
                "dur_s": round(dur_ms / 1000, 2),
                "text_len": len(txt),
                "chars_per_s": round(cps(txt, dur_ms / 1000), 3),
                "is_placeholder_len": abs(dur_ms - PLACEHOLDER_MS) <= TOL_MS,
                "text_head": txt[:40],
            })
    tasks = sorted({x["seq"] for x in rows})
    result["langs"][lang] = {"lang_cn": cn, "long_segments": len(rows), "tasks": tasks,
                             "rows": sorted(rows, key=lambda y: -y["dur_s"])}
    print("=" * 78)
    print(f"[{cn}] 完成任务 {sum(1 for l in (run/'tasks.jsonl').read_text(encoding='utf-8').splitlines() if l.strip() and json.loads(l).get('ok'))}"
          f"｜超长段(>60s) {len(rows)} 个，涉及任务 {len(tasks)} 个 -> {tasks}")
    for x in sorted(rows, key=lambda y: -y["dur_s"]):
        print(f"   seq={x['seq']:>4} paraIndex={x['paraIndex']} {x['start_s']:8.2f}s 持续 {x['dur_s']:7.2f}s"
              f"｜文本 {x['text_len']:>5} 字（{x['chars_per_s']} 字/秒）"
              f"｜占位时长({PLACEHOLDER_MS/1000:.2f}s)±0.3s={x['is_placeholder_len']}｜{x['text_head']!r}")

out = MP3 / "analysis_ja_ko_placeholder_segments.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n[OK] {out}")
