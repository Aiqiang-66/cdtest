# -*- coding: utf-8 -*-
r"""日语重测（r2）与首测（0924）可比性对照。

对比维度：
  性能：任务数/成功率/吞吐（加载期与全墙钟）/端到端分位/创建耗时/音频体积
  文案：M1（字级缺失率、逐字符一致任务数）
  字幕：空字幕、SRT=segments、paraIndex 缺口
  音质：峰值/触顶文件/削波样本/RMS/高频占比/长静音空洞
  段级（0924 复盘新增）：超长段、不可能语速段、静默样段、任务语速、估算内容缺口
输出：
  <r2 批次>/analysis/compare_vs_0924.json 与 .md

用法：
  & "D:\python\python.exe" docs\听书测试物料\compare_ja_rerun_0924.py
"""
import json
import statistics
from pathlib import Path

MP3 = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3")
BATCH = {
    "0924（首测）": MP3 / "Higgs_日语_10并发30分钟_0924",
    "r2（重测）": MP3 / "Higgs_日语_10并发30分钟_0924_r2",
}


def jload(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def load(run):
    rows = []
    p = run / "tasks.jsonl"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def pct(a, q):
    a = sorted(a)
    return round(a[min(len(a) - 1, int(len(a) * q))], 2) if a else None


def stats(run):
    rows = load(run)
    ok = [r for r in rows if r.get("ok")]
    s = jload(run / "summary.json") or {}
    m2 = jload(run / "analysis" / "audio_m2.json") or {}
    perf = jload(run / "analysis" / "perf_m1_m5.json") or {}
    sents = [r["sent_chars"] for r in ok]
    el = [r["elapsed_s"] for r in ok]
    ct = [r["create_s"] for r in ok if "create_s" in r]
    rates = sorted(r["task_chars_per_s"] for r in ok if r.get("task_chars_per_s"))
    base = rates[len(rates) // 2] if rates else None
    est = []
    for r in ok:
        if base and r.get("task_chars_per_s"):
            need = r["sent_chars"] / base
            e = max(0.0, 1 - r["audio_total_s"] / need) if need and r["audio_total_s"] < need else 0.0
            est.append((r["seq"], round(e, 4)))
    est.sort(key=lambda x: -x[1])
    return {
        "run": str(run), "rows": rows, "ok": ok,
        "tasks": len(rows), "success": len(ok), "failed": len(rows) - len(ok),
        "success_rate": round(len(ok) / max(1, len(rows)), 4),
        "wall_s": s.get("run_seconds"), "throughput_load": round(len(rows) / 30, 3) if rows else None,
        "throughput_wall": s.get("throughput_per_min"),
        "elapsed_avg": round(statistics.mean(el), 2) if el else None,
        "elapsed_p50": pct(el, 0.5), "elapsed_p90": pct(el, 0.9), "elapsed_p95": pct(el, 0.95),
        "elapsed_p99": pct(el, 0.99), "elapsed_min": round(min(el), 2) if el else None,
        "elapsed_max": round(max(el), 2) if el else None,
        "create_avg": round(statistics.mean(ct), 3) if ct else None,
        "create_max": round(max(ct), 3) if ct else None,
        # 文案 / 字幕
        "sent_chars": sum(sents),
        "missing_chars": sum(r["missing_chars"] for r in ok),
        "missing_char_ratio": round(sum(r["missing_chars"] for r in ok) / max(1, sum(sents)), 6),
        "identical_tasks": sum(1 for r in ok if r["missing_chars"] == 0 and r["extra_chars"] == 0),
        "empty_segs": sum(r["empty_segments"] for r in ok),
        "srt_ne": sum(1 for r in ok if r["srt_entries"] != r["segments_total"]),
        "para_gaps": sum(r["para_gaps"] for r in ok),
        # 音质
        "peak_max": m2.get("peak_max"), "peak_min": m2.get("peak_min"),
        "files_peak_fail": m2.get("files_peak_fail"), "analyzed": m2.get("analyzed"),
        "clipped_total": m2.get("clipped_total"), "rms_avg": m2.get("rms_avg"),
        "hf_avg": m2.get("hf_avg"), "files_hf_fail": m2.get("files_hf_fail"),
        "long_gaps": m2.get("long_gaps_total"), "files_long_gap_with_text": m2.get("files_long_gap_with_text"),
        "gap_max_s": m2.get("gap_max_s"), "dur_delta_max": m2.get("dur_delta_ms_max"),
        "not_audio": m2.get("not_audio_files"), "refetched": m2.get("refetched_files"),
        # 段级
        "seg_median_chars": (statistics.median([r.get("seg_chars_median") or 0 for r in ok])
                             if any(r.get("seg_chars_median") for r in ok) else None),
        "max_seg_chars": max([r.get("max_seg_chars") or 0 for r in ok], default=0),
        "max_seg_dur_s": max([r.get("max_seg_dur_s") or 0 for r in ok], default=0),
        "n_seg_gt200": sum(r.get("n_seg_gt200") or 0 for r in ok),
        "n_seg_rate_gt15": sum(r.get("n_seg_rate_gt15") or 0 for r in ok),
        "n_seg_rate_lt2": sum(r.get("n_seg_rate_lt2") or 0 for r in ok),
        "tasks_with_long": sum(1 for r in ok if (r.get("n_seg_gt200") or 0) > 0),
        "tasks_with_impossible": sum(1 for r in ok if (r.get("n_seg_rate_gt15") or 0) > 0),
        "chars_per_s_min": round(rates[0], 2) if rates else None,
        "chars_per_s_median": round(base, 2) if base else None,
        "chars_per_s_max": round(rates[-1], 2) if rates else None,
        "est_missing_top": est[:10],
        "tasks_est_missing_gt20": sum(1 for _, e in est if e > 0.2),
        "suspect_tasks": (s.get("suspect_tasks") or [])[:15],
    }


def md_table(d1, d2):
    keys = [
        ("任务数 / 成功 / 失败", lambda s: f"{s['tasks']} / {s['success']} / {s['failed']}"),
        ("成功率", lambda s: f"{s['success_rate']*100:.2f}%"),
        ("吞吐（加载期 30min 口径）", lambda s: f"{s['throughput_load']} 任务/分钟"),
        ("吞吐（全墙钟含 drain）", lambda s: f"{s['throughput_wall']} 任务/分钟"),
        ("端到端 平均 / P50", lambda s: f"{s['elapsed_avg']} / {s['elapsed_p50']}"),
        ("端到端 P90 / P95 / P99", lambda s: f"{s['elapsed_p90']} / {s['elapsed_p95']} / {s['elapsed_p99']}"),
        ("端到端 最小 / 最大", lambda s: f"{s['elapsed_min']} / {s['elapsed_max']}"),
        ("创建接口 平均 / 最大", lambda s: f"{s['create_avg']} / {s['create_max']}"),
        ("M1 发送字 / 缺失字", lambda s: f"{s['sent_chars']:,} / {s['missing_chars']}"),
        ("M1 缺失率（字级）", lambda s: f"{s['missing_char_ratio']*100:.4f}%"),
        ("M1 逐字符一致任务", lambda s: f"{s['identical_tasks']}/{s['success']}"),
        ("M5 空字幕段 / SRT≠segments / paraIndex 缺口",
         lambda s: f"{s['empty_segs']} / {s['srt_ne']} / {s['para_gaps']}"),
        ("音频 分析条数 / 触顶文件", lambda s: f"{s['analyzed']} / {s['files_peak_fail']}"),
        ("音频 峰值 min~max", lambda s: f"{s['peak_min']} ~ {s['peak_max']}"),
        ("音频 削波样本合计", lambda s: f"{s['clipped_total']:,}" if s['clipped_total'] is not None else "—"),
        ("音频 RMS 平均", lambda s: f"{s['rms_avg']} dBFS"),
        ("音频 高频均值 / >10% 文件", lambda s: f"{s['hf_avg']} / {s['files_hf_fail']}"),
        ("音频 长空洞处数 / 含文本文件 / 最长",
         lambda s: f"{s['long_gaps']} / {s['files_long_gap_with_text']} / {s['gap_max_s']}s"),
        ("音频 时长差最大", lambda s: f"{s['dur_delta_max']} ms"),
        ("音频 非音频响应 / 事后补齐", lambda s: f"{s['not_audio']} / {s['refetched']}"),
        ("段级 段长中位", lambda s: f"{s['seg_median_chars']} 字"),
        ("段级 最长段", lambda s: f"{s['max_seg_chars']} 字 / {s['max_seg_dur_s']}s"),
        ("段级 超长段(>200字) 总数 / 涉及任务", lambda s: f"{s['n_seg_gt200']} / {s['tasks_with_long']}"),
        ("段级 高语速段(>15字/秒) 总数 / 涉及任务",
         lambda s: f"{s['n_seg_rate_gt15']} / {s['tasks_with_impossible']}"),
        ("段级 低语速段(<2字/秒)", lambda s: f"{s['n_seg_rate_lt2']}"),
        ("任务语速 min / 中位 / max",
         lambda s: f"{s['chars_per_s_min']} / {s['chars_per_s_median']} / {s['chars_per_s_max']} 字/秒"),
        ("估算内容缺口 >20% 任务数", lambda s: f"{s['tasks_est_missing_gt20']}"),
    ]
    L = ["| 指标 | " + " | ".join(BATCH) + " | 结论 |", "|---|---|---|"]
    for name, f in keys:
        v1, v2 = f(d1), f(d2)
        verdict = "一致" if v1 == v2 else "有差异"
        L.append(f"| {name} | {v1} | {v2} | {verdict} |")
    return "\n".join(L)


def seg_stats_from_meta(run):
    """直接从 metadata 现算段级统计（两批口径统一，不依赖跑批时是否记录过新字段）。"""
    out = {"max_seg_chars": 0, "max_seg_dur_s": 0.0, "max_seg_rate": 0.0,
           "n_seg_gt200": 0, "n_seg_rate_gt15": 0, "n_seg_rate_lt2": 0,
           "tasks_with_long": 0, "tasks_with_impossible": 0,
           "rates": [], "long_tasks": [], "impossible_tasks": []}
    p = run / "tasks.jsonl"
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if not rec.get("ok"):
            continue
        meta_p = run / "meta" / f"task_{rec['seq']:04d}.json"
        if not meta_p.exists():
            continue
        segs = json.loads(meta_p.read_text(encoding="utf-8"))
        body = [s for s in segs if s.get("paraIndex", -1) >= 0]
        if not body:
            continue
        total_chars = sum(len((s.get("text") or "").strip()) for s in body)
        total_dur = max(s.get("endMs", 0) for s in segs) / 1000.0
        if total_dur:
            out["rates"].append(total_chars / total_dur)
        long_n = imp_n = lt2_n = 0
        for s in body:
            t = len((s.get("text") or "").strip())
            d = (s.get("endMs", 0) - s.get("startMs", 0)) / 1000.0
            rate = (t / d) if d > 0 else 0.0
            if t > out["max_seg_chars"]:
                out["max_seg_chars"] = t
            if d > out["max_seg_dur_s"]:
                out["max_seg_dur_s"] = round(d, 2)
            if rate > out["max_seg_rate"]:
                out["max_seg_rate"] = round(rate, 1)
            long_n += 1 if t > 200 else 0
            imp_n += 1 if (d > 0.5 and rate > 15) else 0
            lt2_n += 1 if (d > 5 and rate < 2) else 0
        out["n_seg_gt200"] += long_n
        out["n_seg_rate_gt15"] += imp_n
        out["n_seg_rate_lt2"] += lt2_n
        if long_n:
            out["tasks_with_long"] += 1
            out["long_tasks"].append(rec["seq"])
        if imp_n:
            out["tasks_with_impossible"] += 1
            out["impossible_tasks"].append(rec["seq"])
    r = sorted(out["rates"])
    out["seg_median_chars"] = None
    out["chars_per_s_min"] = round(r[0], 2) if r else None
    out["chars_per_s_median"] = round(r[len(r) // 2], 2) if r else None
    out["chars_per_s_max"] = round(r[-1], 2) if r else None
    out["chars_per_s"] = r
    return out


def main():
    data = {name: stats(run) for name, run in BATCH.items()}
    n1, n2 = list(BATCH)
    d1, d2 = data[n1], data[n2]
    # 段级统计统一改为「从 metadata 现算」，覆盖跑批时记录的字段
    for name, run in BATCH.items():
        seg = seg_stats_from_meta(run)
        data[name].update({k: v for k, v in seg.items() if k != "rates"})
        data[name]["rates_all"] = seg["rates"]
    d1, d2 = data[n1], data[n2]

    L = ["# 日语重测（r2）与首测（0924）对照", "",
         f"- 两批口径完全一致：`model=higgs`、`lang=9/Japanese_female`、10 并发 × 30 分钟、"
         f"同一批 107 个 ~5000 字符单元（语料逐字节一致）",
         f"- 首测 {n1}：`{BATCH[n1].name}`", f"- 重测 {n2}：`{BATCH[n2].name}`", "",
         "## 一、逐项对照", "", md_table(d1, d2), ""]

    L += ["## 二、可复现性判断", ""]
    checks = [
        ("M1 文案零缺失", d1["missing_char_ratio"] == 0 and d2["missing_char_ratio"] == 0),
        ("任务成功率 ≥99%", min(d1["success_rate"], d2["success_rate"]) >= 0.99),
        ("日语削波（全部文件峰值 >0.999）",
         d1["files_peak_fail"] == d1["analyzed"] and d2["files_peak_fail"] == d2["analyzed"]),
        ("存在长静默空洞（metadata 有文本）",
         d1["files_long_gap_with_text"] > 0 and d2["files_long_gap_with_text"] > 0),
        ("存在超长段（>200 字）", d1["n_seg_gt200"] > 0 and d2["n_seg_gt200"] > 0),
        ("存在不可能语速段（>15 字/秒）", d1["n_seg_rate_gt15"] > 0 and d2["n_seg_rate_gt15"] > 0),
    ]
    L += ["| 现象 | 首测 | 重测 | 是否复现 |", "|---|---|---|---|"]
    for name, both in checks:
        L.append(f"| {name} | 见上表 | 见上表 | {'✅ 复现' if both else '⚠️ 未同时出现'} |")
    L += ["", "## 三、重测中需要整段 ASR 核查的可疑任务（按估算缺口排序）", "",
          "| # | seq | taskId | 单元 | 字数 | 音频(s) | 任务语速 | 最长段 | 段时长 | 超长段 | 高语速段 | 估算缺口 |",
          "|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    src = d2["suspect_tasks"] or []
    for i, s in enumerate(src[:12], 1):
        L.append(f"| {i} | {s.get('seq')} | {s.get('taskId')} | {s.get('unit')} | {s.get('chars')} |"
                 f" {s.get('audio_s')} | {s.get('chars_per_s')} | {s.get('max_seg_chars')} 字 |"
                 f" {s.get('max_seg_dur_s')}s | {s.get('n_seg_gt200')} | {s.get('n_seg_rate_gt15')} |"
                 f" {100*(s.get('est_missing_ratio') or 0):.1f}% |")
    L += ["", "> 说明：`估算缺口` = 1 − 音频时长 ÷（字数 ÷ 任务语速中位），为估算值；"
          "上批已用整段 ASR 验证该估算与实测同量级（0040 估算 28.9%/实测 34.6%；0071 估算 46.8%/实测 46.0%）。",
          ""]

    out_dir = BATCH[n2] / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "compare_vs_0924.json").write_text(
        json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("rows", "ok")} for k, v in data.items()},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "compare_vs_0924.md").write_text("\n".join(L), encoding="utf-8")
    print(f"[OK] {out_dir / 'compare_vs_0924.md'}")
    print(f"  首测：任务 {d1['tasks']}｜成功率 {d1['success_rate']*100:.2f}%｜M1 缺失率 "
          f"{d1['missing_char_ratio']*100:.4f}%｜超长段 {d1['n_seg_gt200']}｜空洞文件 {d1['files_long_gap_with_text']}")
    print(f"  重测：任务 {d2['tasks']}｜成功率 {d2['success_rate']*100:.2f}%｜M1 缺失率 "
          f"{d2['missing_char_ratio']*100:.4f}%｜超长段 {d2['n_seg_gt200']}｜空洞文件 {d2['files_long_gap_with_text']}")


if __name__ == "__main__":
    main()
