# -*- coding: utf-8 -*-
"""定点核查 ~82s 超长静音：是真实音频空洞，还是解码/下载残缺造成的假象。

核查项：
  ① 文件大小 vs 记录大小；时长 vs metadata 总时长（残缺文件会明显偏短）；
  ② 静音区间内是否「数字全零」还是「低电平噪声」（真空洞通常是数字静音或极低电平）；
  ③ ffmpeg 独立解码该文件的时长与 astats 峰值（排除 PyAV 单方面口径）。
"""
import json
import subprocess
import sys
from pathlib import Path

import av
import numpy as np

MP3 = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3")
FFMPEG = r"D:\ffmpeg-6.0-full_build\bin\ffmpeg.exe"
TARGETS = [("ja", 35), ("ja", 83), ("ko", 44), ("ko", 48)]


def dec(p):
    with av.open(str(p)) as c:
        st = c.streams.audio[0]
        sr = st.codec_context.sample_rate
        chunks = []
        for fr in c.decode(st):
            a = fr.to_ndarray()
            if a.ndim > 1:
                a = a.mean(axis=0)
            chunks.append(a.astype(np.float32))
    return (np.concatenate(chunks) if chunks else np.zeros(0, np.float32)), sr


for lang, seq in TARGETS:
    tag = "日语" if lang == "ja" else "韩语"
    run = MP3 / f"Higgs_{tag}_10并发30分钟_0924"
    p = run / "audio" / f"task_{seq:04d}.mp3"
    rec = None
    for line in (run / "tasks.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            if r["seq"] == seq:
                rec = r
                break
    segs = json.loads((run / "meta" / f"task_{seq:04d}.json").read_text(encoding="utf-8"))
    meta_total = max(s.get("endMs", 0) for s in segs) / 1000.0

    d, sr = dec(p)
    dur = d.size / sr
    sil = np.abs(d) < 1e-3
    runs, cs = [], None
    for i, s in enumerate(sil):
        if s:
            if cs is None:
                cs = i
        else:
            if cs is not None:
                runs.append((cs, i))
                cs = None
    if cs is not None:
        runs.append((cs, len(sil)))
    best = max(runs, key=lambda ab: ab[1] - ab[0]) if runs else (0, 0)

    print("=" * 78)
    print(f"[{tag}] task_{seq:04d}")
    print(f"  文件大小 = {p.stat().st_size:,} B（运行期记录 audio_bytes={rec.get('audio_bytes')}）")
    print(f"  PyAV 时长 = {dur:.2f}s ｜ metadata 总时长 = {meta_total:.2f}s ｜ 差 = {abs(dur-meta_total)*1000:.0f} ms")
    print(f"  最长静音 = {(best[1]-best[0])/sr:.2f}s @ {best[0]/sr:.2f}s~{best[1]/sr:.2f}s")
    seg = d[best[0]:best[1]]
    nz = int(np.count_nonzero(seg))
    print(f"  该区间样本 {seg.size:,} 个，非零样本 {nz:,}（{100*nz/max(1,seg.size):.2f}%）"
          f"｜最大幅值 {np.max(np.abs(seg)) if seg.size else 0:.3e}｜RMS "
          f"{20*np.log10(float(np.sqrt(np.mean(seg.astype(np.float64)**2)))+1e-12):.1f} dBFS")
    print("  1 秒包络（前 8 秒 / 后 8 秒）:")
    for k in list(range(0, min(8, seg.size // sr))) + list(range(max(0, seg.size // sr - 8), seg.size // sr)):
        ch = seg[k * sr:(k + 1) * sr]
        r0 = float(np.sqrt(np.mean(ch.astype(np.float64) ** 2))) if ch.size else 0.0
        print(f"     +{k:4d}s  {20*np.log10(r0+1e-12):7.1f} dBFS")
    # ffmpeg 独立口径
    try:
        out = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", str(p),
                              "-f", "null", "-"], capture_output=True, text=True, timeout=600)
        line = [l for l in out.stderr.splitlines() if "time=" in l or "Duration" in l]
        print("  ffmpeg:", " | ".join(x.strip()[:120] for x in line[-2:]))
    except Exception as e:
        print("  ffmpeg 复核失败:", e)
