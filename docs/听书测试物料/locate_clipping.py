# -*- coding: utf-8 -*-
"""定位西语生成音频中的削波（|amp|>=0.999）时间段。"""
import json
import numpy as np
import soundfile as sf
from pathlib import Path

OUT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\梦成接口_XR3_英西")
CLIP_THRESH = 0.999
MERGE_GAP = 0.10  # 事件合并间隔（秒）

def fmt(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"

def find_clip_events(path):
    data, sr = sf.read(path, dtype="float32")
    if data.ndim > 1:
        data = data.mean(axis=1)
    mask = np.abs(data) >= CLIP_THRESH
    idx = np.flatnonzero(mask)
    events = []
    if len(idx) == 0:
        return data, sr, events
    # 按样本差分组
    splits = np.where(np.diff(idx) > 1)[0]
    groups = np.split(idx, splits + 1)
    for g in groups:
        start_sample = int(g[0])
        end_sample = int(g[-1])
        events.append([start_sample / sr, end_sample / sr])
    # 合并间隔小于 MERGE_GAP 的事件
    merged = []
    for s, e in events:
        if merged and s - merged[-1][1] <= MERGE_GAP:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    return data, sr, merged

def main():
    files = sorted(OUT.glob("西语_XR3_Ch*.wav"), key=lambda p: int(p.stem.split("Ch")[-1]))
    out = []
    for p in files:
        data, sr, events = find_clip_events(p)
        total_clip = int(np.sum(np.abs(data) >= CLIP_THRESH))
        peak = float(np.max(np.abs(data)))
        print(f"\n{p.name}: 时长={len(data)/sr:.1f}s 峰值={peak:.3f} 削波样本={total_clip} 事件数={len(events)}")
        ev_list = []
        for i, (s, e) in enumerate(events, 1):
            d = e - s
            seg = data[int(s*sr):int(e*sr)+1]
            seg_peak = float(np.max(np.abs(seg)))
            ev_list.append({"idx": i, "start": round(s, 3), "end": round(e, 3),
                            "start_hms": fmt(s), "end_hms": fmt(e),
                            "duration_s": round(d, 3), "seg_peak": round(seg_peak, 3)})
            print(f"  事件{i}: {fmt(s)} -> {fmt(e)} (时长 {d*1000:.0f}ms, 峰值 {seg_peak:.3f})")
        out.append({"file": p.name, "duration_s": round(len(data)/sr, 1),
                    "peak": peak, "clipped_samples": total_clip,
                    "event_count": len(events), "events": ev_list})

    out_json = OUT / "西语削波时间段.json"
    out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n已保存:", out_json)

if __name__ == "__main__":
    main()