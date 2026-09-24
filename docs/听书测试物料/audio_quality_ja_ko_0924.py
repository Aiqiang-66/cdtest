import os
# -*- coding: utf-8 -*-
r"""日/韩压测音频 —— M2 客观音质指标（削波/响度/高频占比/异常静音）+ TC-AUD-001 时长一致性。

口径（技能 Phase 5 / TC-AUD-006~011）：
  峰值 ≤ 0.999（不得触顶 1.000）｜高频占比 <10%（英语正常 ≈2%）｜
  异常静音：连续静音 > 3s 且该时段 metadata 有文本 = 音频空洞（内容本该在）；
  音频时长与 metadata 总时长差 < 1s。

工程要点（本次实测踩坑，已内置）：
  1. **只分析已完成任务的音频**（以 tasks.jsonl 的 audio_bytes 对齐文件大小），避免半截文件造成伪阳性；
  2. **识别非音频内容**：任务 status=2 返回的 audio_url 可能是 COS 错误响应（440B XML, NoSuchKey），
     这类文件不能当音频证据，需单列并支持 --refetch 重下补齐；
  3. 每次判定同时输出「与 metadata 有文本重叠的长静音」，避免把正常段落停顿当成缺陷。

产物：<批次目录>/analysis/audio_m2.json、audio_m2.md、audio_listen_checklist.md

用法：
  & "D:\python\python.exe" docs\听书测试物料\audio_quality_ja_ko_0924.py --lang both
  & "D:\python\python.exe" docs\听书测试物料\audio_quality_ja_ko_0924.py --lang ja --refetch
"""
import argparse
import json
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import av
import numpy as np

import os

_TTS_KEY = os.environ.get("TTS_SECRET_KEY")
if not _TTS_KEY:
    raise SystemExit(
        "缺少环境变量 TTS_SECRET_KEY（测试环境密钥，请勿写入代码；设置后重试，例如：\n"
        "  在 PowerShell 里先设置环境变量 TTS_SECRET_KEY（值由项目统一管理）后再运行")

MP3_ROOT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3")
LANGS = {
    "ja": ("日语", MP3_ROOT / "Higgs_日语_10并发30分钟_0924"),
    "ko": ("韩语", MP3_ROOT / "Higgs_韩语_10并发30分钟_0924"),
}

SIL_THRESH = 1e-3
MIN_SILENCE = 0.15
HF_START = 8000
PEAK_LIMIT = 0.999
HF_LIMIT = 0.10
SIL_LIMIT_MS = 300
GAP_LIMIT_MS = 3000        # 异常静音（空洞）判定：连续静音 > 3s


def is_audio_file(p: Path) -> bool:
    """按魔数判断是否音频（COS 错误响应会被保存成 .mp3，必须排除）。"""
    try:
        with p.open("rb") as f:
            head = f.read(4)
    except Exception:
        return False
    return head[:3] == b"ID3" or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")


def cos_error_code(p: Path) -> str:
    try:
        txt = p.read_text(encoding="utf-8", errors="ignore")
        if "<Code>" in txt:
            return txt.split("<Code>")[1].split("</Code>")[0]
    except Exception:
        pass
    return "非音频内容"


def load_tasks(run_dir):
    tasks = {}
    p = run_dir / "tasks.jsonl"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            tasks[r["seq"]] = r
    return tasks


def refetch_missing(run_dir, base="https://ai-main-none-dev.changdu.ltd",
                    key=None):
    """对运行期下载到非音频内容的任务，按 taskId 重新查询并重下音频。

    背景：任务 status=2 且带 audio_url，但**立即**下载会命中 COS NoSuchKey
    （对象尚未就绪的竞态）；稍后重下即可成功。此处补齐音频留证。
    """
    if not key:
        key = os.environ.get("TTS_SECRET_KEY")
        if not key:
            raise SystemExit("缺少环境变量 TTS_SECRET_KEY")
    import base64 as _b64
    import hashlib as _hl
    import hmac as _hmac
    import requests

    tasks = load_tasks(run_dir)
    audio_dir = run_dir / "audio"
    fixed, failed = [], []
    for p in sorted(audio_dir.glob("task_*.mp3")):
        if is_audio_file(p):
            continue
        seq = int(p.stem.split("_")[1])
        tid = (tasks.get(seq) or {}).get("taskId")
        if not tid:
            failed.append((seq, "无 taskId"))
            continue
        try:
            body = json.dumps({"taskType": 74, "taskIds": [tid]})
            sig = _b64.b64encode(_hmac.new(key.encode(), body.encode(), _hl.sha256).digest()).decode()
            info = requests.post(f"{base}/Task/GetAllTaskStatus", data=body.encode(),
                                 headers={"sign": sig, "Content-Type": "application/json"},
                                 timeout=60).json()
            data = info["data"][0].get("data", "{}")
            data = json.loads(data) if isinstance(data, str) else data
            r = requests.get(data["audio_url"], timeout=600)
            if is_audio_file_bytes(r.content):
                p.write_bytes(r.content)
                fixed.append((seq, len(r.content)))
            else:
                failed.append((seq, f"仍非音频 HTTP {r.status_code} len={len(r.content)}"))
        except Exception as e:
            failed.append((seq, f"{type(e).__name__}: {e}"))
    print(f"  [补齐] 重下成功 {len(fixed)} 个｜仍失败 {len(failed)} 个")
    for seq, n in fixed:
        print(f"     task_{seq:04d}: 重下 {n:,} B")
    for seq, why in failed:
        print(f"     task_{seq:04d}: {why}")
    return fixed, failed


def is_audio_file_bytes(b: bytes) -> bool:
    return b[:3] == b"ID3" or b[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")


def decode(path):
    """mp3 → (float32 mono, sample_rate, channels, bit_rate)"""
    with av.open(str(path)) as container:
        stream = container.streams.audio[0]
        sr = stream.codec_context.sample_rate
        ch = stream.codec_context.channels
        bit_rate = stream.codec_context.bit_rate or container.bit_rate
        chunks = []
        for frame in container.decode(stream):
            arr = frame.to_ndarray()
            if arr.ndim > 1:
                arr = arr.mean(axis=0)
            chunks.append(arr.astype(np.float32))
    data = np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)
    return data, sr, ch, bit_rate


def analyze_file(mp3_path, meta_total_ms):
    data, sr, ch, bit_rate = decode(mp3_path)
    n = len(data)
    dur = n / sr if sr else 0.0
    peak = float(np.max(np.abs(data))) if n else 0.0
    rms = float(np.sqrt(np.mean(data.astype(np.float64) ** 2))) if n else 0.0
    rms_dbfs = 20 * np.log10(rms + 1e-12) if rms > 0 else -120.0
    dc = float(np.mean(data.astype(np.float64))) if n else 0.0
    clipped = int(np.sum(np.abs(data) >= PEAK_LIMIT))

    silent = np.abs(data) < SIL_THRESH
    runs, cur_start = [], None
    for i, s in enumerate(silent):
        if s:
            if cur_start is None:
                cur_start = i
        else:
            if cur_start is not None:
                runs.append((cur_start, i))
                cur_start = None
    if cur_start is not None:
        runs.append((cur_start, len(silent)))
    max_run = max((b - a for a, b in runs), default=0)
    max_sil_ms = max_run / sr * 1000 if sr else 0.0
    sil_segments = sum(1 for a, b in runs if (b - a) / sr >= MIN_SILENCE)
    long_gaps = [(round(a / sr, 2), round((b - a) / sr, 2)) for a, b in runs
                 if (b - a) / sr * 1000 > GAP_LIMIT_MS]

    if n >= 2048 and sr >= HF_START * 2:
        win = data[: (n // 2048) * 2048].reshape(-1, 2048)
        spec = np.abs(np.fft.rfft(win * np.hanning(2048), axis=1))
        freqs = np.fft.rfftfreq(2048, 1 / sr)
        total = spec.sum()
        hf_ratio = float(spec[:, freqs >= HF_START].sum() / (total + 1e-12))
    else:
        hf_ratio = None

    dur_delta_ms = abs(dur * 1000 - meta_total_ms) if meta_total_ms else None
    return {
        "file": mp3_path.name, "sr": sr, "channels": ch, "bit_rate": bit_rate,
        "dur_s": round(dur, 3), "peak": round(peak, 4), "clipped": clipped,
        "ge_1_0": int(np.sum(np.abs(data) >= 1.0)) if n else 0,
        "rms_dbfs": round(float(rms_dbfs), 2), "dc": round(dc, 6),
        "hf_ratio": None if hf_ratio is None else round(hf_ratio, 4),
        "max_sil_ms": round(max_sil_ms, 1), "sil_segments": sil_segments,
        "long_gaps": long_gaps, "long_gaps_n": len(long_gaps),
        "gap_max_s": max([g[1] for g in long_gaps], default=0.0),
        "meta_total_ms": meta_total_ms, "dur_delta_ms": None if dur_delta_ms is None else round(dur_delta_ms, 1),
        "clip_fail": peak > PEAK_LIMIT,
        "hf_fail": (hf_ratio is not None and hf_ratio > HF_LIMIT),
        "sil_fail": max_sil_ms > SIL_LIMIT_MS,
        "dur_fail": (dur_delta_ms is not None and dur_delta_ms > 1000),
    }


def meta_segments(run_dir, seq):
    p = run_dir / "meta" / f"task_{seq:04d}.json"
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


def annotate_gaps(row, segs):
    """标出「音频空洞时段内 metadata 有文本」的空洞（= 内容本该在）。"""
    out = []
    for start_s, dur_s in row.get("long_gaps", []):
        a_ms, b_ms = start_s * 1000, (start_s + dur_s) * 1000
        covered = [s for s in segs
                   if (s.get("text") or "").strip()
                   and min(s.get("endMs", 0), b_ms) - max(s.get("startMs", 0), a_ms) > 500]
        out.append({"start_s": start_s, "dur_s": dur_s,
                    "meta_segments_overlap": len(covered),
                    "meta_text_sample": (covered[0].get("text") or "")[:60] if covered else None})
    row["long_gaps_detail"] = out
    row["long_gaps_with_text"] = sum(1 for g in out if g["meta_segments_overlap"] > 0)
    return row


def analyze_lang(lang, cn, run_dir, max_per_lang, do_refetch=False):
    audio_dir = run_dir / "audio"
    tasks = load_tasks(run_dir)
    if do_refetch:
        print(f"[{cn}] 检查并补齐非音频文件…")
        refetch_missing(run_dir)

    all_files = sorted(audio_dir.glob("task_*.mp3"))
    files, skipped, not_audio, refetched = [], [], [], []
    for f in all_files:
        try:
            seq = int(f.stem.split("_")[1])
        except Exception:
            continue
        if not is_audio_file(f):
            not_audio.append((f.name, f.stat().st_size, cos_error_code(f)))
            continue
        rec = tasks.get(seq)
        if rec is None:
            skipped.append(f.name)          # 无对应完成记录 = 可能是半截文件
            continue
        exp = rec.get("audio_bytes")
        if exp is not None and f.stat().st_size != exp:
            # 运行期下载到的是 COS 错误响应（记录里的大小就是那段 XML），事后已补齐：
            # 这类文件是**完整音频**，必须纳入分析，只是标注为 refetched。
            refetched.append(f.name)
        files.append((seq, f))
    if max_per_lang and len(files) > max_per_lang:
        step = len(files) / max_per_lang
        files = [files[int(i * step)] for i in range(max_per_lang)]

    rows = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {}
        for seq, f in files:
            segs = meta_segments(run_dir, seq)
            total = max([s.get("endMs", 0) for s in segs], default=0)
            futs[ex.submit(analyze_file, f, total)] = (seq, segs)
        for fut, (seq, segs) in futs.items():
            try:
                r = annotate_gaps(fut.result(), segs)
                r["seq"] = seq
                rows.append(r)
            except Exception as e:
                print(f"  [跳过] seq={seq} {type(e).__name__}: {e}")

    rows.sort(key=lambda r: r["seq"])
    hf = [r["hf_ratio"] for r in rows if r["hf_ratio"] is not None]
    agg = {
        "lang": lang, "lang_cn": cn, "analyzed": len(rows),
        "audio_files_present": len(all_files), "skipped_incomplete": len(skipped),
        "not_audio_files": len(not_audio),
        "refetched_files": len(refetched),
        "tasks_done": len(tasks),
        "tasks_without_audio_file": sorted(set(tasks) - {int(f.stem.split("_")[1]) for f in all_files}),
        "tasks_with_audio_error": [{"seq": r["seq"], "taskId": r.get("taskId"), "error": r.get("audio_error")}
                                   for r in tasks.values() if r.get("audio_error")],
        "not_audio_detail": [{"file": f, "bytes": s, "cos_code": c} for f, s, c in not_audio],
        "sr_values": sorted({r["sr"] for r in rows}),
        "bit_rate_values": sorted({r["bit_rate"] for r in rows if r["bit_rate"]}),
        "peak_max": max([r["peak"] for r in rows], default=None),
        "peak_min": min([r["peak"] for r in rows], default=None),
        "files_peak_fail": sum(1 for r in rows if r["clip_fail"]),
        "clipped_total": sum(r["clipped"] for r in rows),
        "clipped_max": max([r["clipped"] for r in rows], default=0),
        "ge_1_0_total": sum(r["ge_1_0"] for r in rows),
        "files_with_ge_1_0": sum(1 for r in rows if r["ge_1_0"] > 0),
        "rms_avg": round(statistics.mean([r["rms_dbfs"] for r in rows]), 2) if rows else None,
        "rms_min": min([r["rms_dbfs"] for r in rows], default=None),
        "rms_max": max([r["rms_dbfs"] for r in rows], default=None),
        "hf_avg": round(statistics.mean(hf), 4) if hf else None,
        "hf_max": max(hf) if hf else None, "hf_min": min(hf) if hf else None,
        "files_hf_fail": sum(1 for r in rows if r["hf_fail"]),
        "max_sil_ms_max": max([r["max_sil_ms"] for r in rows], default=None),
        "files_sil_fail": sum(1 for r in rows if r["sil_fail"]),
        "files_long_gap": sum(1 for r in rows if r["long_gaps_n"] > 0),
        "files_long_gap_with_text": sum(1 for r in rows if r["long_gaps_with_text"] > 0),
        "long_gaps_total": sum(r["long_gaps_n"] for r in rows),
        "gap_max_s": max([r["gap_max_s"] for r in rows], default=0.0),
        "gap_files": [{"seq": r["seq"], "file": r["file"], "max_gap_s": r["gap_max_s"],
                       "gaps": r["long_gaps_detail"]}
                      for r in rows if r["long_gaps_n"] > 0],
        "files_dur_fail": sum(1 for r in rows if r["dur_fail"]),
        "dur_delta_ms_max": max([r["dur_delta_ms"] for r in rows if r["dur_delta_ms"] is not None], default=None),
        "dc_max_abs": max([abs(r["dc"]) for r in rows], default=None),
        "rows": rows,
    }
    out_dir = run_dir / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "audio_m2.json").write_text(json.dumps(agg, ensure_ascii=False, indent=2), encoding="utf-8")
    return agg


def _rng(vals):
    vals = [v for v in vals if v]
    return f"{min(vals)}~{max(vals)}" if vals else "—"


def md_section(a):
    L = [f"### {a['lang_cn']}（{a['lang']}）客观指标", ""]
    L.append(f"- 分析音频 **{a['analyzed']}** 条（目录内 {a['audio_files_present']} 条｜"
             f"其中事后补齐 {a['refetched_files']} 条｜跳过半截 {a['skipped_incomplete']} 条）"
             f"｜采样率 {a['sr_values']}｜码率 {_rng(a['bit_rate_values'])} bps")
    L.append(f"- 音频可获取性：完成任务 {a['tasks_done']} 个，**无音频文件 {len(a['tasks_without_audio_file'])} 个**，"
             f"下载异常 {len(a['tasks_with_audio_error'])} 个")
    L.append(f"- 峰值：最大 {a['peak_max']}｜最小 {a['peak_min']}｜触顶(>0.999)文件 **{a['files_peak_fail']}** 个"
             f"｜削波样本合计 {a['clipped_total']:,}（单文件最多 {a['clipped_max']:,}）")
    L.append(f"- 越界样本：≥1.0 合计 {a['ge_1_0_total']:,}（{a['files_with_ge_1_0']} 个文件）")
    L.append(f"- 响度 RMS：平均 {a['rms_avg']} dBFS（范围 {a['rms_min']} ~ {a['rms_max']}）")
    L.append(f"- 高频占比(≥8kHz)：平均 {100*(a['hf_avg'] or 0):.2f}%｜最大 {100*(a['hf_max'] or 0):.2f}%"
             f"｜>10% 文件 **{a['files_hf_fail']}** 个")
    L.append(f"- 最长静音：{a['max_sil_ms_max']} ms（>300ms 文件 {a['files_sil_fail']} 个，"
             f"朗读停顿属正常，不作为缺陷判据）")
    L.append(f"- **音频空洞（静音 >3s）**：{a['long_gaps_total']} 处，涉及 {a['files_long_gap']} 个文件，"
             f"其中 {a['files_long_gap_with_text']} 个文件的空洞时段 **metadata 有文本**（内容本该在）"
             f"｜最长空洞 {a['gap_max_s']}s")
    L.append(f"- TC-AUD-001 时长一致性：音频 vs metadata 总时长最大差 {a['dur_delta_ms_max']} ms"
             f"（≥1s 文件 **{a['files_dur_fail']}** 个）")
    return "\n".join(L)


def checklist(a, out_dir):
    rows = sorted(a["rows"], key=lambda r: (-(r["gap_max_s"] or 0), -(r["hf_ratio"] or 0), -r["peak"]))[:6]
    L = [f"# {a['lang_cn']} 人工听测记录表（M2 / TC-AUD-010）", "",
         "> 技能规定：音质结论必须「客观指标 + 人工听测」双管；人工听测**必须由人完成**，脚本不能替代。",
         "> 抽样策略：优先挑「最长空洞 / 高频占比 / 峰值」最异常的文件。", "",
         "| # | 文件 | 峰值 | 高频占比 | RMS(dBFS) | 削波样本 | 最长空洞(s) | 听测结论（待填） |",
         "|---|---|---:|---:|---:|---:|---:|---|"]
    for i, r in enumerate(rows, 1):
        L.append(f"| {i} | audio/{r['file']} | {r['peak']} | {r['hf_ratio']} | {r['rms_dbfs']} |"
                 f" {r['clipped']} | {r['gap_max_s']} | |")
    L += ["", "- 听测人：____　听测时间：____", f"- 音频目录：{out_dir.parent / 'audio'}", ""]
    (out_dir / "audio_listen_checklist.md").write_text("\n".join(L), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="both", choices=["ja", "ko", "both"])
    ap.add_argument("--max-per-lang", type=int, default=0, help="0 = 全量分析")
    ap.add_argument("--refetch", action="store_true", help="对非音频文件按 taskId 重下补齐")
    ap.add_argument("--run-dir", default="", help="指定批次目录（默认识别 LANGS 内置的两个批次）")
    args = ap.parse_args()

    runs = dict(LANGS)
    if args.run_dir:
        lang = args.lang if args.lang != "both" else "ja"
        runs = {lang: (LANGS[lang][0], Path(args.run_dir))}

    langs = sorted(runs) if args.lang == "both" else [args.lang]
    sections = []
    for lang in langs:
        cn, run_dir = runs[lang]
        a = analyze_lang(lang, cn, run_dir, args.max_per_lang, args.refetch)
        checklist(a, run_dir / "analysis")
        sections.append(md_section(a))
        print(f"[{cn}] 分析 {a['analyzed']} 条｜非音频 {a['not_audio_files']}｜峰值最大 {a['peak_max']}"
              f"｜触顶文件 {a['files_peak_fail']}｜高频>10% {a['files_hf_fail']}"
              f"｜空洞 {a['long_gaps_total']} 处（其中 metadata 有文本 {a['files_long_gap_with_text']} 文件）")
    out_md = MP3_ROOT / "analysis_ja_ko_audio_m2.md"
    out_md.write_text("# 日/韩压测音频 —— M2 客观音质指标（自动生成）\n\n" + "\n\n".join(sections) + "\n",
                      encoding="utf-8")
    print(f"\n[OK] {out_md}")


if __name__ == "__main__":
    main()
