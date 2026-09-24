# -*- coding: utf-8 -*-
r"""日/韩 10 并发压测数据分析：性能指标 + M1 文案一致性 + M5 字幕完整性。

输入：<批次目录>/tasks.jsonl（run_higgs_ja_ko_10concurrent_30min.py 产出，含逐任务全文与统计）
输出：<批次目录>/analysis/perf_m1_m5.json 与 perf_m1_m5.md（供报告组装脚本引用）

口径声明：
  日语无空格 → M1 主口径为**字级**（CER 式），另附词级；
  韩语以空格分词 → M1 主口径为**词级**（WER 式），另附字级。
  M1 的比对文本仅取 body 段（paraIndex>=0），标题段（paraIndex=-1）已排除。
"""
import argparse
import json
import statistics
from pathlib import Path

MP3_ROOT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3")
LANGS = {
    "ja": ("日语", MP3_ROOT / "Higgs_日语_10并发30分钟_0924"),
    "ko": ("韩语", MP3_ROOT / "Higgs_韩语_10并发30分钟_0924"),
}
WINDOW_SEC = 300


def pct(a, q):
    if not a:
        return None
    a = sorted(a)
    return round(a[min(len(a) - 1, int(len(a) * q))], 2)


def load(run_dir):
    rows = []
    for line in (run_dir / "tasks.jsonl").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def analyze(lang, cn, run_dir, limit_head=10, load_minutes=30.0):
    rows = load(run_dir)
    ok = [r for r in rows if r.get("ok")]
    bad = [r for r in rows if not r.get("ok")]

    # ⚠️ summary.json 只在跑批结束时写入；若其 total_tasks 与当前 tasks.jsonl 不一致
    # （例如被早前的烟测结果占用），一律以 tasks.jsonl 现算为准，避免吞吐/成功率被污染。
    summary = {}
    sp = run_dir / "summary.json"
    if sp.exists():
        try:
            cand = json.loads(sp.read_text(encoding="utf-8"))
            if cand.get("total_tasks") == len(rows):
                summary = cand
        except Exception:
            summary = {}

    el = [r["elapsed_s"] for r in ok]
    ct = [r["create_s"] for r in ok if "create_s" in r]
    primary_word = (lang == "ko")

    # 实际墙钟区间用逐任务时间戳现算（含收尾在途任务）
    if rows:
        t_start = min(r["start_ts"] for r in rows)
        t_end = max(r["start_ts"] + r.get("elapsed_s", 0) for r in rows)
        wall = t_end - t_start
    else:
        wall = 0.0
    workers = summary.get("workers", 10)
    run_seconds = summary.get("run_seconds", round(wall, 1))
    throughput_per_min = round(len(rows) / (wall / 60), 3) if wall > 0 else 0.0

    m1 = {
        "primary_unit": "word" if primary_word else "char",
        "sent_primary_total": sum(r["sent_primary_tokens"] for r in ok),
        "missing_primary_total": sum(r["missing"] for r in ok),
        "extra_primary_total": sum(r["extra"] for r in ok),
        "sent_chars_total": sum(r["sent_chars"] for r in ok),
        "missing_chars_total": sum(r["missing_chars"] for r in ok),
        "extra_chars_total": sum(r["extra_chars"] for r in ok),
        "missing_words_total": sum(r["missing"] for r in ok) if primary_word else None,
        "missing_primary_ratio": round(sum(r["missing"] for r in ok)
                                       / max(1, sum(r["sent_primary_tokens"] for r in ok)), 6),
        "missing_char_ratio": round(sum(r["missing_chars"] for r in ok)
                                    / max(1, sum(r["sent_chars"] for r in ok)), 6),
        "similarity_primary_avg": round(statistics.mean([r["similarity"] for r in ok]), 6) if ok else None,
        "similarity_primary_min": min([r["similarity"] for r in ok], default=None),
        "similarity_char_avg": round(statistics.mean([r["similarity_char"] for r in ok]), 6) if ok else None,
        "similarity_char_min": min([r["similarity_char"] for r in ok], default=None),
        "tasks_with_missing_primary": sum(1 for r in ok if r["missing"] > 0),
        "tasks_with_missing_chars": sum(1 for r in ok if r["missing_chars"] > 0),
        "tasks_identical_chars": sum(1 for r in ok if r["missing_chars"] == 0 and r["extra_chars"] == 0),
        "lossy_tasks": [
            {"seq": r["seq"], "unit": r["unit"], "taskId": r["taskId"], "chars": r["chars"],
             "missing_chars": r["missing_chars"], "missing_char_ratio": r["missing_char_ratio"],
             "missing_words": r["missing"], "similarity": r["similarity"],
             "missing_head": r["missing_head"][:20]}
            for r in sorted(ok, key=lambda x: (-x["missing_chars"], -x["missing"]))
            if r["missing_chars"] > 0 or r["missing"] > 0
        ][:limit_head],
    }

    m5 = {
        "tasks": len(ok),
        "segments_total": sum(r["segments_total"] for r in ok),
        "segments_min": min([r["segments_total"] for r in ok], default=None),
        "segments_max": max([r["segments_total"] for r in ok], default=None),
        "segments_avg": round(statistics.mean([r["segments_total"] for r in ok]), 1) if ok else None,
        "distinct_para_total": sum(r["distinct_para"] for r in ok),
        "body_segments_total": sum(r["body_segments"] for r in ok),
        "title_segments_total": sum(r["title_segments"] for r in ok),
        "tasks_all_have_one_title_segment": all(r["title_segments"] == 1 for r in ok),
        "tasks_with_para_gaps": sum(1 for r in ok if r["para_gaps"] > 0),
        "para_gaps_total": sum(r["para_gaps"] for r in ok),
        "tasks_with_empty_segments": sum(1 for r in ok if r["empty_segments"] > 0),
        "empty_segments_total": sum(r["empty_segments"] for r in ok),
        "tasks_with_holes": sum(1 for r in ok if r["holes"] > 0),
        "holes_total": sum(r["holes"] for r in ok),
        "hole_max_ms": max([r["hole_max_ms"] for r in ok], default=0),
        "tasks_srt_ne_segments": sum(1 for r in ok if r["srt_entries"] != r["segments_total"]),
        "tasks_body_lt_distinct_para": sum(1 for r in ok if r["body_segments"] < r["distinct_para"]),
        "bad_tasks": [
            {"seq": r["seq"], "unit": r["unit"], "taskId": r["taskId"], "segments": r["segments_total"],
             "distinct_para": r["distinct_para"], "para_gaps": r["para_gaps"],
             "empty": r["empty_segments"], "holes": r["holes"], "srt": r["srt_entries"]}
            for r in ok if r["para_gaps"] or r["empty_segments"] or r["holes"]
            or r["srt_entries"] != r["segments_total"] or r["body_segments"] < r["distinct_para"]
        ][:limit_head],
    }

    # 时间窗趋势（稳定性观察）
    if ok:
        t0 = min(r["start_ts"] for r in ok)
        buckets = {}
        for r in ok:
            b = int((r["start_ts"] - t0) // WINDOW_SEC)
            buckets.setdefault(b, []).append(r)
        trend = [{"window": f"{b * WINDOW_SEC//60}-{(b + 1) * WINDOW_SEC//60}min",
                  "tasks": len(v),
                  "elapsed_avg": round(statistics.mean([x["elapsed_s"] for x in v]), 1),
                  "segments_avg": round(statistics.mean([x["segments_total"] for x in v]), 1),
                  "missing_chars": sum(x["missing_chars"] for x in v)}
                 for b, v in sorted(buckets.items())]
    else:
        trend = []

    perf = {
        "lang": lang, "lang_cn": cn, "run_dir": str(run_dir),
        "workers": workers, "run_seconds": run_seconds, "wall_seconds": round(wall, 1),
        "total_tasks": len(rows), "ok": len(ok), "failed": len(bad),
        "success_rate": round(len(ok) / max(1, len(rows)), 4),
        "throughput_per_min": throughput_per_min,
        "throughput_per_hour": round(throughput_per_min * 60, 1),
        "throughput_loadphase_per_min": round(len(rows) / load_minutes, 3) if load_minutes else None,
        "throughput_loadphase_per_hour": round(len(rows) / load_minutes * 60, 1) if load_minutes else None,
        "load_minutes": load_minutes,
        "elapsed_avg": round(statistics.mean(el), 2) if el else None,
        "elapsed_p50": pct(el, 0.5), "elapsed_p90": pct(el, 0.9),
        "elapsed_p95": pct(el, 0.95), "elapsed_p99": pct(el, 0.99),
        "elapsed_min": round(min(el), 2) if el else None, "elapsed_max": round(max(el), 2) if el else None,
        "create_avg": round(statistics.mean(ct), 3) if ct else None,
        "create_p50": pct(ct, 0.5), "create_p95": pct(ct, 0.95),
        "create_min": round(min(ct), 3) if ct else None, "create_max": round(max(ct), 3) if ct else None,
        "audio_bytes_total": sum(r.get("audio_bytes", 0) for r in ok),
        "audio_mb_avg": round(statistics.mean([r.get("audio_bytes", 0) for r in ok]) / 1048576, 2) if ok else None,
        "chars_total": sum(r["chars"] for r in ok),
        "distinct_units_used": len({r["unit"] for r in rows}),
        "failed_tasks": [{"seq": r["seq"], "unit": r["unit"], "taskId": r.get("taskId"),
                          "status": r.get("status"), "error": r.get("error")} for r in bad][:limit_head],
        "trend": trend,
    }
    return {"perf": perf, "m1": m1, "m5": m5}


def md_section(a):
    p, m1, m5 = a["perf"], a["m1"], a["m5"]
    unit_name = "词级" if m1["primary_unit"] == "word" else "字级"
    L = []
    L.append(f"### {p['lang_cn']}（{p['lang']}）")
    L.append("")
    L.append(f"- 并发 {p['workers']}｜时长 {p['run_seconds']}s｜总任务 {p['total_tasks']}｜成功 {p['ok']}｜失败 {p['failed']}"
             f"｜成功率 {p['success_rate']*100:.2f}%")
    L.append(f"- 吞吐 **{p['throughput_loadphase_per_min']} 任务/分钟（加载期 {p['load_minutes']:.0f} 分钟口径，"
             f"≈{p['throughput_loadphase_per_hour']} 任务/小时）**｜含收尾 drain 的全墙钟口径 "
             f"{p['throughput_per_min']} 任务/分钟（墙钟 {p['wall_seconds']}s）"
             f"｜单任务发送字符合计 {p['chars_total']:,}")
    L.append(f"- 端到端耗时(s)：平均 {p['elapsed_avg']}｜P50 {p['elapsed_p50']}｜P90 {p['elapsed_p90']}"
             f"｜P95 {p['elapsed_p95']}｜P99 {p['elapsed_p99']}｜最小 {p['elapsed_min']}｜最大 {p['elapsed_max']}")
    L.append(f"- 创建接口耗时(s)：平均 {p['create_avg']}｜P50 {p['create_p50']}｜P95 {p['create_p95']}"
             f"｜最小 {p['create_min']}｜最大 {p['create_max']}")
    L.append(f"- 音频产物：合计 {p['audio_bytes_total']/1048576:.1f} MB｜平均 {p['audio_mb_avg']} MB/任务"
             f"｜使用不同语料单元 {p['distinct_units_used']} 个")
    L.append("")
    L.append(f"**M1 文案一致性（主口径 {unit_name}，标题段已排除）**")
    L.append("")
    L.append(f"- 主口径缺失 {m1['missing_primary_total']} 个 token / 发送 {m1['sent_primary_total']:,}"
             f"（**{m1['missing_primary_ratio']*100:.4f}%**）｜多余 {m1['extra_primary_total']}")
    L.append(f"- 字级缺失 {m1['missing_chars_total']} 字 / 发送 {m1['sent_chars_total']:,}"
             f"（**{m1['missing_char_ratio']*100:.4f}%**）｜多余 {m1['extra_chars_total']} 字")
    L.append(f"- 相似度：主口径平均 {m1['similarity_primary_avg']}（最低 {m1['similarity_primary_min']}）"
             f"｜字级平均 {m1['similarity_char_avg']}（最低 {m1['similarity_char_min']}）")
    L.append(f"- 有缺失任务：主口径 {m1['tasks_with_missing_primary']} 个｜字级 {m1['tasks_with_missing_chars']} 个"
             f"｜去标点后逐字符完全一致任务 {m1['tasks_identical_chars']}/{p['ok']}")
    L.append("")
    L.append("**M5 字幕完整性**")
    L.append("")
    L.append(f"- segments 合计 {m5['segments_total']:,}（min {m5['segments_min']} / max {m5['segments_max']}"
             f" / 平均 {m5['segments_avg']}）｜其中标题段 {m5['title_segments_total']}｜正文段 {m5['body_segments_total']:,}")
    L.append(f"- distinct paraIndex 合计 {m5['distinct_para_total']:,}｜每任务恰好 1 个标题段："
             f"{m5['tasks_all_have_one_title_segment']}")
    L.append(f"- paraIndex 缺口：{m5['tasks_with_para_gaps']} 个任务 / 合计 {m5['para_gaps_total']} 处")
    L.append(f"- 空字幕段：{m5['tasks_with_empty_segments']} 个任务 / 合计 {m5['empty_segments_total']} 条")
    L.append(f"- 时间轴空洞（>3s）：{m5['tasks_with_holes']} 个任务 / 合计 {m5['holes_total']} 处"
             f"（最大 {m5['hole_max_ms']} ms）")
    L.append(f"- SRT 条目数 != segments 的任务：{m5['tasks_srt_ne_segments']} 个"
             f"｜正文段 < distinct paraIndex 的任务：{m5['tasks_body_lt_distinct_para']} 个")
    if m1["lossy_tasks"]:
        L.append("")
        L.append(f"**有缺失任务明细（前 {len(m1['lossy_tasks'])} 个）**")
        L.append("")
        L.append("| seq | 单元 | taskId | 缺失字 | 缺失率 | 相似度 | 缺失片段（截断） |")
        L.append("|---|---|---|---:|---:|---:|---|")
        for t in m1["lossy_tasks"]:
            head = " ".join(str(x) for x in t["missing_head"])[:80]
            L.append(f"| {t['seq']} | {t['unit']} | {t['taskId']} | {t['missing_chars']} |"
                     f" {t['missing_char_ratio']*100:.3f}% | {t['similarity']} | {head} |")
    if m5["bad_tasks"]:
        L.append("")
        L.append("**M5 异常任务明细**")
        L.append("")
        L.append("| seq | 单元 | taskId | segments | distinct para | 缺口 | 空字幕 | 空洞 | SRT |")
        L.append("|---|---|---|---:|---:|---:|---:|---:|---:|")
        for t in m5["bad_tasks"]:
            L.append(f"| {t['seq']} | {t['unit']} | {t['taskId']} | {t['segments']} | {t['distinct_para']} |"
                     f" {t['para_gaps']} | {t['empty']} | {t['holes']} | {t['srt']} |")
    if p["trend"]:
        L.append("")
        L.append("**分时段趋势（每 5 分钟）**")
        L.append("")
        L.append("| 时段 | 任务数 | 平均端到端(s) | 平均段数 | 缺失字 |")
        L.append("|---|---:|---:|---:|---:|")
        for t in p["trend"]:
            L.append(f"| {t['window']} | {t['tasks']} | {t['elapsed_avg']} | {t['segments_avg']} | {t['missing_chars']} |")
    if p["failed_tasks"]:
        L.append("")
        L.append("**失败任务**")
        L.append("")
        for t in p["failed_tasks"]:
            L.append(f"- seq {t['seq']} {t['unit']} taskId={t['taskId']} status={t['status']} {t['error']}")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="both", choices=["ja", "ko", "both"])
    ap.add_argument("--load-minutes", type=float, default=30.0,
                    help="压测加载窗口时长（用于计算加载期吞吐，排除收尾 drain 的影响）")
    ap.add_argument("--run-dir", default="", help="指定批次目录（默认识别 LANGS 内置的两个批次）")
    args = ap.parse_args()

    if args.run_dir:
        lang = args.lang if args.lang != "both" else "ja"
        runs = {lang: (LANGS[lang][0], Path(args.run_dir))}
    else:
        runs = LANGS

    langs = sorted(runs) if args.lang == "both" else [args.lang]
    out_md = []
    for lang in langs:
        cn, run_dir = runs[lang]
        a = analyze(lang, cn, run_dir, load_minutes=args.load_minutes)
        out_dir = run_dir / "analysis"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "perf_m1_m5.json").write_text(json.dumps(a, ensure_ascii=False, indent=2), encoding="utf-8")
        out_md.append(md_section(a))
        print(f"[{cn}] 任务 {a['perf']['total_tasks']}｜成功率 {a['perf']['success_rate']*100:.2f}%"
              f"｜吞吐 {a['perf']['throughput_per_min']} 任务/分｜缺失率(字级) {a['m1']['missing_char_ratio']*100:.4f}%"
              f"｜paraIndex 缺口任务 {a['m5']['tasks_with_para_gaps']}")
        print(f"     → {out_dir / 'perf_m1_m5.json'}")

    header = "# 日/韩 10 并发 30 分钟压测 —— 性能 / M1 / M5 数据（自动生成）\n"
    (LANGS[langs[0]][1].parent / "analysis_ja_ko_perf_m1_m5.md").write_text(
        header + "\n\n".join(out_md) + "\n", encoding="utf-8")
    print(f"\n[OK] 汇总 markdown: {LANGS[langs[0]][1].parent / 'analysis_ja_ko_perf_m1_m5.md'}")


if __name__ == "__main__":
    main()
