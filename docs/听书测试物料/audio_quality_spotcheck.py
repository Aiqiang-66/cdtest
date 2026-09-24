# -*- coding: utf-8 -*-
"""梦成接口生成音频的客观音质抽查：爆音、静音段、响度、DC偏移、高频噪声。"""
import json
import sys
import numpy as np
import soundfile as sf
from pathlib import Path

OUT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\梦成接口_XR3_英西")

# 抽查样本：覆盖大章/中章/小章
SAMPLE = [
    "英语_XR3_Ch1.wav", "英语_XR3_Ch2.wav", "英语_XR3_Ch3.wav",
    "英语_XR3_Ch10.wav", "英语_XR3_Ch14.wav", "英语_XR3_Ch17.wav",
    "西语_XR3_Ch1.wav", "西语_XR3_Ch2.wav", "西语_XR3_Ch3.wav",
    "西语_XR3_Ch10.wav", "西语_XR3_Ch14.wav", "西语_XR3_Ch17.wav",
]

SIL_THRESH = 1e-3      # 视为静音的幅度阈值
MIN_SILENCE = 0.15     # 只统计 >=150ms 的静音段（卡顿/异常停顿判定）
HF_START = 8000        # 高频段起始（Hz），22.05k 采样下 Nyquist=11025

def analyze(path):
    data, sr = sf.read(path, dtype="float32")
    if data.ndim > 1:
        data = data.mean(axis=1)
    n = len(data)
    dur = n / sr
    peak = float(np.max(np.abs(data))) if n else 0.0
    rms = float(np.sqrt(np.mean(data.astype(np.float64)**2))) if n else 0.0
    rms_dbfs = 20*np.log10(rms + 1e-12) if rms > 0 else -120
    dc = float(np.mean(data.astype(np.float64)))
    clipped = int(np.sum(np.abs(data) >= 0.999))
    # 静音段检测
    silent = np.abs(data) < SIL_THRESH
    # 最长连续静音长度
    max_sil = 0
    cur = 0
    for s in silent:
        if s:
            cur += 1
            max_sil = max(max_sil, cur)
        else:
            cur = 0
    max_sil_ms = max_sil / sr * 1000
    silence_ratio = float(np.mean(silent)) if n else 0.0
    # 静音段数量（>=MIN_SILENCE）
    seg_count = 0
    cur = 0
    for s in silent:
        if s:
            cur += 1
            if cur == int(MIN_SILENCE * sr):
                seg_count += 1
        else:
            cur = 0
    # 高频能量占比（his/noise 代理指标）
    if n >= 2048:
        win = data[: (n // 2048) * 2048].reshape(-1, 2048)
        spec = np.abs(np.fft.rfft(win * np.hanning(2048), axis=1))
        freqs = np.fft.rfftfreq(2048, 1/sr)
        total = spec.sum(axis=1).sum()
        hf = spec[:, freqs >= HF_START].sum()
        hf_ratio = float(hf / (total + 1e-12))
    else:
        hf_ratio = float("nan")
    return dict(dur=dur, peak=peak, rms_dbfs=rms_dbfs, dc=dc, clipped=clipped,
                max_sil_ms=max_sil_ms, silence_ratio=silence_ratio,
                sil_segments=seg_count, hf_ratio=hf_ratio)

def main():
    rows = []
    for name in SAMPLE:
        p = OUT / name
        if not p.exists():
            print("MISSING", name)
            continue
        m = analyze(p)
        rows.append((name, m))
        print(f"{name}: dur={m['dur']:.2f}s peak={m['peak']:.3f} rms={m['rms_dbfs']:.1f}dBFS "
              f"dc={m['dc']:.5f} clip={m['clipped']} maxSil={m['max_sil_ms']:.0f}ms "
              f"silRatio={m['silence_ratio']*100:.2f}% silSeg={m['sil_segments']} hf={m['hf_ratio']*100:.2f}%")

    out_json = OUT / "audio_quality_spotcheck.json"
    out_json.write_text(json.dumps([{ "file": n, **m } for n, m in rows], ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n已保存:", out_json)

if __name__ == "__main__":
    main()