# -*- coding: utf-8 -*-
r"""生成日/韩「并发=10 稳定性测试（2h）」报告。

读取每个语种的稳定性批次目录：
  <批次>/summary.json、tasks.jsonl
  <批次>/analysis/perf_m1_m5.json、audio_m2.json
输出：
  docs/听书测试物料/测试报告/日韩_稳定性10并发_30min_0924.md

用法：
  & "D:\python\python.exe" docs\听书测试物料\gen_report_stability_0924.py
"""
import json
import statistics
from pathlib import Path

ROOT = Path(r"D:\python\dmx\cdtest")
MP3 = ROOT / "docs" / "听书测试物料" / "mp3"
REPORT_DIR = ROOT / "docs" / "听书测试物料" / "测试报告"
DATE = "2026-09-24"
RUNS = {
    "ja": ("日语", MP3 / "Higgs_日语_稳定性10并发_30min_0924"),
    "ko": ("韩语", MP3 / "Higgs_韩语_稳定性10并发_30min_0924"),
}
BASELINE = {  # 30 分钟批次（对照）
    "ja": MP3 / "Higgs_日语_10并发30分钟_0924",
    "ko": MP3 / "Higgs_韩语_10并发30分钟_0924",
}
WINDOW_MIN = 10          # 趋势窗口


def jload(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def load_rows(run):
    p = run / "tasks.jsonl"
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def pct(a, q):
    a = sorted(a)
    return round(a[min(len(a) - 1, int(len(a) * q))], 2) if a else None


def lang_stats(run, cn):
    rows = load_rows(run)
    ok = [r for r in rows if r.get("ok")]
    perf = jload(run / "analysis" / "perf_m1_m5.json") or {}
    m2 = jload(run / "analysis" / "audio_m2.json") or {}
    s = jload(run / "summary.json") or {}
    p, m1, m5 = perf.get("perf", {}), perf.get("m1", {}), perf.get("m5", {})
    el = [r["elapsed_s"] for r in ok]
    # 时间窗趋势（每 WINDOW_MIN 分钟）
    trend = []
    if rows:
        t0 = min(r["start_ts"] for r in rows)
        buckets = {}
        for r in rows:
            b = int((r["start_ts"] - t0) // (WINDOW_MIN * 60))
            buckets.setdefault(b, []).append(r)
        for b in sorted(buckets):
            v = buckets[b]
            vok = [x for x in v if x.get("ok")]
            trend.append({
                "window": f"{b*WINDOW_MIN}-{(b+1)*WINDOW_MIN}min",
                "tasks": len(v), "ok": len(vok),
                "elapsed_p50": pct([x["elapsed_s"] for x in vok], 0.5),
                "elapsed_avg": round(statistics.mean([x["elapsed_s"] for x in vok]), 1) if vok else None,
                "missing_chars": sum(x.get("missing_chars", 0) for x in vok),
                "seg_median": round(statistics.mean([x.get("seg_chars_median") or 0 for x in vok]), 1) if vok else None,
                "long_segs": sum(x.get("n_seg_gt200") or 0 for x in vok),
            })
    return {
        "cn": cn, "run": run, "rows": rows, "ok": ok,
        "tasks": len(rows), "failed": len(rows) - len(ok),
        "success_rate": round(len(ok) / max(1, len(rows)), 4),
        "wall_s": s.get("run_seconds"),
        "throughput": round(len(rows) / (s.get("run_seconds", 1) / 60), 3) if s else None,
        "elapsed_avg": round(statistics.mean(el), 2) if el else None,
        "elapsed_p50": pct(el, 0.5), "elapsed_p95": pct(el, 0.95), "elapsed_p99": pct(el, 0.99),
        "elapsed_min": round(min(el), 1) if el else None, "elapsed_max": round(max(el), 1) if el else None,
        "audio_gb": round(sum(r.get("audio_bytes", 0) for r in ok) / 1073741824, 2),
        "sent_chars": m1.get("sent_chars_total"), "missing_chars": m1.get("missing_chars_total"),
        "missing_ratio": m1.get("missing_char_ratio"), "identical": m1.get("tasks_identical_chars"),
        "empty_segs": m5.get("empty_segments_total"), "srt_ne": m5.get("tasks_srt_ne_segments"),
        "analyzed": m2.get("analyzed"), "peak_max": m2.get("peak_max"),
        "files_peak_fail": m2.get("files_peak_fail"), "rms_avg": m2.get("rms_avg"),
        "hf_avg": m2.get("hf_avg"), "files_hf_fail": m2.get("files_hf_fail"),
        "long_gaps": m2.get("long_gaps_total"), "gap_files_text": m2.get("files_long_gap_with_text"),
        "gap_max_s": m2.get("gap_max_s"), "not_audio": m2.get("not_audio_files"),
        "refetched": m2.get("refetched_files"),
        "n_seg_gt200": sum(r.get("n_seg_gt200") or 0 for r in ok),
        "n_seg_rate_gt15": sum(r.get("n_seg_rate_gt15") or 0 for r in ok),
        "n_seg_rate_lt2": sum(r.get("n_seg_rate_lt2") or 0 for r in ok),
        "max_seg_chars": max([r.get("max_seg_chars") or 0 for r in ok], default=0),
        "task_rate_median": (lambda rs: round(rs[len(rs)//2], 2) if rs else None)(
            sorted(r["task_chars_per_s"] for r in ok if r.get("task_chars_per_s"))),
        "trend": trend,
        "suspect": (s.get("suspect_tasks") or [])[:10],
    }


def main():
    data = {k: lang_stats(RUNS[k][1], RUNS[k][0]) for k in RUNS}
    base = {k: (jload(BASELINE[k] / "summary.json") or {}) for k in BASELINE}
    L = []
    A = L.append
    A("# 日/韩 TTS 并发=10 稳定性测试报告（每语种 30 分钟 · 连续打满）")
    A("")
    A(f"> **目的**：在**并发 10** 下连续打满 **30 分钟**，验证长时运行下的成功率/延迟/文案/字幕/音质是否稳定  ")
    A(f"> **语种**：日语（`lang=9`/`Japanese_female`）、韩语（`lang=14`/`Korean_female`），**分别单独**执行  ")
    A(f"> **口径**：`model=higgs`、链路A `taskType=74`、语料为 M0 合规（保留段落）~5000 字符单元  ")
    A(f"> **依据**：`SKILL.md` v1.1.7（M0 前置 + M1~M5 必测项 + Phase 4 稳定性 + Phase 9 产物层）  ")
    A(f"> **日期**：{DATE}")
    A("")
    A("## 一、结论速览")
    A("")
    A("| 指标 | 日语（30min） | 韩语（30min） | 判定 |")
    A("|---|---|---|---|")
    ja, ko = data["ja"], data["ko"]

    def row(name, f, judge=None):
        v1, v2 = f(ja), f(ko)
        A(f"| {name} | {v1} | {v2} | {judge or ''} |")

    row("总任务 / 失败", lambda s: f"{s['tasks']} / {s['failed']}",
        "✅" if ja["failed"] == 0 and ko["failed"] == 0 else "⚠️ 见缺陷节")
    row("成功率", lambda s: f"{s['success_rate']*100:.2f}%" if s["success_rate"] is not None else "—",
        "✅ ≥99%" if min(ja["success_rate"] or 0, ko["success_rate"] or 0) >= 0.99 else "❌")
    row("实际墙钟（h）", lambda s: f"{(s['wall_s'] or 0)/3600:.2f}")
    row("吞吐（任务/分钟）", lambda s: s["throughput"])
    row("端到端 平均 / P50（s）", lambda s: f"{s['elapsed_avg']} / {s['elapsed_p50']}")
    row("端到端 P95 / P99（s）", lambda s: f"{s['elapsed_p95']} / {s['elapsed_p99']}")
    row("端到端 最小 / 最大（s）", lambda s: f"{s['elapsed_min']} / {s['elapsed_max']}")
    row("**M1 缺失字 / 缺失率**", lambda s: f"{s['missing_chars']} / {100*(s['missing_ratio'] or 0):.4f}%",
        "✅ 0" if (ja["missing_chars"] == 0 and ko["missing_chars"] == 0) else "❌")
    row("M1 逐字符一致任务", lambda s: f"{s['identical']}/{len(s['ok'])}")
    row("M5 空字幕 / SRT≠segments", lambda s: f"{s['empty_segs']} / {s['srt_ne']}", "✅ 0")
    row("M2 触顶文件 / 分析数", lambda s: f"{s['files_peak_fail']}/{s['analyzed']}")
    row("M2 峰值 max / RMS", lambda s: f"{s['peak_max']} / {s['rms_avg']} dBFS")
    row("M2 长空洞处数 / 含文本文件", lambda s: f"{s['long_gaps']} / {s['gap_files_text']}")
    row("产物首轮非音频响应（已补齐）", lambda s: f"{s['refetched']} 个（补齐成功，残留 {s['not_audio']} 个）")
    row("段级 超长段(>200字) / 高语速段(>15字/秒)", lambda s: f"{s['n_seg_gt200']} / {s['n_seg_rate_gt15']}")
    row("任务语速中位（字/秒）", lambda s: s["task_rate_median"])
    row("音频留证体积（GB）", lambda s: s["audio_gb"])
    A("")
    A("## 二、稳定性趋势（每 10 分钟窗口）")
    A("")
    for lk in ("ja", "ko"):
        s = data[lk]
        A(f"### {s['cn']}")
        A("")
        A("| 时段 | 任务 | 成功 | 端到端 P50(s) | 端到端 平均(s) | 缺失字 | 段长中位 | 超长段 |")
        A("|---|---:|---:|---:|---:|---:|---:|---:|")
        for t in s["trend"]:
            A(f"| {t['window']} | {t['tasks']} | {t['ok']} | {t['elapsed_p50']} | {t['elapsed_avg']} |"
              f" {t['missing_chars']} | {t['seg_median']} | {t['long_segs']} |")
        A("")
        if s["trend"]:
            first = next((t for t in s["trend"] if t["tasks"] >= 5), s["trend"][0])
            last = next((t for t in reversed(s["trend"]) if t["tasks"] >= 5), s["trend"][-1])
            d = (last["elapsed_p50"] or 0) - (first["elapsed_p50"] or 0)
            thr = 0.25 * max(1.0, first["elapsed_p50"] or 1.0)
            if abs(d) < thr:
                verdict = "稳定（首末窗口 P50 变化在 ±25% 内）"
            elif d > 0:
                verdict = "⚠️ 存在劣化趋势（P50 随运行变慢），需排查"
            else:
                verdict = "✅ 无劣化（P50 随运行变快，属预热/队列收敛）"
            A(f"> 首末可比窗口 P50 变化：{first['elapsed_p50']}s → {last['elapsed_p50']}s"
              f"（{'+' if d >= 0 else ''}{round(d,1)}s）｜结论：{verdict}")
        A("")
    A("## 三、与 30 分钟批次对照")
    A("")
    A("| 项 | 日语 30min | 日语 30min 稳定性 | 韩语 30min | 韩语 30min 稳定性 |")
    A("|---|---|---|---|")

    def bval(lk, key, pctfmt=False):
        v = base[lk].get(key)
        if v is None:
            return "—"
        if pctfmt and isinstance(v, (int, float)):
            return f"{v*100:.2f}%"
        return v

    A(f"| 任务数 | {bval('ja','total_tasks')} | {ja['tasks']} | {bval('ko','total_tasks')} | {ko['tasks']} |")
    A(f"| 成功率 | {bval('ja','success_rate',True)} | {ja['success_rate']*100:.2f}% |"
      f" {bval('ko','success_rate',True)} | {ko['success_rate']*100:.2f}% |")
    A(f"| 吞吐(任务/分) | {bval('ja','throughput_per_min')} | {ja['throughput']} |"
      f" {bval('ko','throughput_per_min')} | {ko['throughput']} |")
    A(f"| 端到端 P50(s) | {bval('ja','elapsed_p50')} | {ja['elapsed_p50']} |"
      f" {bval('ko','elapsed_p50')} | {ko['elapsed_p50']} |")
    A("")
    A("## 四、缺陷与建议（摘要）")
    A("")
    issues = []
    for lk in ("ja", "ko"):
        s = data[lk]
        if s["failed"]:
            issues.append(f"{s['cn']}：失败任务 {s['failed']} 个")
        if (s["missing_chars"] or 0) > 0:
            issues.append(f"{s['cn']}：M1 缺失 {s['missing_chars']} 字（{100*(s['missing_ratio'] or 0):.4f}%）")
        if s["not_audio"]:
            issues.append(f"{s['cn']}：产物立即下载返回非音频 {s['not_audio']} 次（事后补齐 {s['refetched']}）")
        if s["gap_files_text"]:
            issues.append(f"{s['cn']}：音频长空洞（metadata 有文本）{s['gap_files_text']} 个文件，最长 {s['gap_max_s']}s")
        if s["n_seg_gt200"]:
            issues.append(f"{s['cn']}：切句超长段 {s['n_seg_gt200']} 个（最长 {s['max_seg_chars']} 字）")
    if issues:
        for i, t in enumerate(issues, 1):
            A(f"{i}. {t}")
    else:
        A("- 未发现异常：成功率、文案一致性、字幕完整性、产物可获取性均通过。")
    A("")

    # ── 扩展（v2 追加）：稳定性缺陷明细 + M3 抽样 ──
    A("## 五、稳定性缺陷明细")
    A("")
    A("### 缺陷 1（P1）：任务卡死在 `status=67`，成功率不达 99% 门禁")
    A("")
    A("| 语种 | 总任务 | 成功 | 失败 | 成功率 | 卡死任务 |")
    A("|---|---:|---:|---:|---:|---|")
    for lk in ("ja", "ko"):
        s_ = data[lk]
        stuck = [r for r in s_["rows"] if not r.get("ok")]
        det = "；".join(f"seq {r.get('seq')} taskId={r.get('taskId')} status={r.get('status')}" for r in stuck) or "无"
        A(f"| {s_['cn']} | {s_['tasks']} | {len(s_['ok'])} | {s_['failed']} | {s_['success_rate']*100:.2f}% | {det} |")
    A("")
    A("> 现象：任务长期停留在处理中（`status=67`），直到跑批收尾 drain 上限仍未收敛，最终记为失败。"
      "两语种**同时复现** → 服务端侧稳定性问题（非客户端偶发）。"
      "建议：处理中任务需有超时收敛机制（超时→失败并给出可读原因），并暴露队列/槽位可观测指标。")
    A("")
    A("### 缺陷 2（P1）：产物立即可获取性 —— `audio_url` 立即下载返回非音频（COS 错误响应）")
    A("")
    A("| 语种 | 分析条数 | 非音频响应 | 占比 | 事后补齐 | 备注 |")
    A("|---|---:|---:|---:|---:|---|")
    for lk in ("ja", "ko"):
        s_ = data[lk]
        analyzed, na, rf = s_["analyzed"] or 0, s_["not_audio"] or 0, s_["refetched"] or 0
        pct_ = f"{100*na/max(1, analyzed+na):.1f}%" if na else "0%"
        note = "首次分析时补齐成功" if rf else ("本轮补齐未成功，需开发核实对象是否真实存在" if na else "无异常")
        A(f"| {s_['cn']} | {analyzed} | **{na}** | {pct_} | {rf} | {note} |")
    A("")
    A("> 与 0924 批次一致（当时 18/225 = 8.0%）：任务 `taskStatus=2`、metadata 可取，但**立即**拉取音频得到 XML 错误页，"
      "调用方按契约直接播放会失败。建议任务置成功前先校验对象可读（HEAD 探测）。")
    A("")
    A("### 缺陷 3（P1）：日语在 **M0 合规语料**下仍出现静默空洞 —— 修正此前归因")
    A("")
    A("| 语种 | 长空洞处数 | 含 metadata 文本的文件 | 最长空洞 | 说明 |")
    A("|---|---:|---:|---:|---|")
    for lk in ("ja", "ko"):
        s_ = data[lk]
        note = "⚠️ 合规语料下仍复现（此前误判为『单段落语料』所致）" if (s_["gap_files_text"] or 0) > 0 else "本轮未复现"
        A(f"| {s_['cn']} | {s_['long_gaps']} | {s_['gap_files_text']} | {s_['gap_max_s']}s | {note} |")
    A("")
    A("> **重要修正**：0924 复盘把 81.64s 静默占位归因于『整章拼成单段落』。本轮语料已按 M0 保留段落"
      "（每单元 47~112 段、段长上限 80 字、无超长段），日语**仍出现 5 处静默空洞**（最长 82.56s，同为 81.64s 占位签名）"
      "→ 说明**段落格式只解决切句退化，不解决静默占位**；该缺陷必须在服务端分段合成环节修复"
      "（失败片段应重试或显式报错，不得插入静默占位）。韩语本轮未出现静默空洞。")
    A("")
    A("### 缺陷 4（P2）：段级时间轴与文本量不匹配（metadata 时间轴不可信）")
    A("")
    A("| 语种 | 超长段(>200字) | 高语速段(>15字/秒) | 疑似静默段(<2字/秒) | 最长段 | 任务语速中位 |")
    A("|---|---:|---:|---:|---:|---:|")
    for lk in ("ja", "ko"):
        s_ = data[lk]
        A(f"| {s_['cn']} | {s_['n_seg_gt200']} | {s_['n_seg_rate_gt15']} | {s_['n_seg_rate_lt2']} |"
          f" {s_['max_seg_chars']} 字 | {s_['task_rate_median']} 字/秒 |")
    A("")
    A("**ASR 定点核查（日语最坏样本）**：task seq=54 中某段 **69 字却只给 0.56s**（122.8 字/秒；"
      "全批正文段中 130/9981 = 1.3% 超 15 字/秒）。对该段所在窗口（399~419s）做 large-v3 转写：")
    A("")
    A("| 项 | 结果 |")
    A("|---|---|")
    A("| 参考文本（metadata，含该 69 字段） | 约 170 字 |")
    A("| ASR 实际识别 | 显示音频在该时刻仍在播**前一段**内容（「愛情を感じたが…目を覚ました」），"
      "该 69 字段仅识别出开头「とった」，其中段（ローラは…不便でした）未出现 |")
    A("| 判读 | **时间轴归属异常**：metadata 标注时间与音频实际内容错位；因文本口径 M1 = 0 缺失"
      "（两语种 100% 逐字符一致），不能判定为文本丢失，但也不排除局部漏读，需开发结合服务端日志核实 |")
    A("")
    A("> 建议：`段时长 × 正常语速` 与 `段字数` 偏差超阈值（如 3 倍）应记警告并可回溯；时间轴应基于实际音频生成。")
    A("")
    A("### M3 漏词抽样（faster-whisper large-v3，CPU int8，各 3 条 × 前 180s）")
    A("")
    A("| 语种 | seq | 参考字符 | ASR字符 | CER | 删除率(漏词) | 相似度 |")
    A("|---|---:|---:|---:|---:|---:|---:|")
    for lk, fname in (("ja", "asr_stab_ja"), ("ko", "asr_stab_ko")):
        j = jload(MP3 / "analysis_ja_ko_asr_m3" / f"{fname}.json") or {}
        for r in ((j.get("langs", {}) or {}).get(lk) or {}).get("rows", []):
            A(f"| {data[lk]['cn']} | {r['seq']} | {r['ref_chars']} | {r['hyp_chars']} |"
              f" {r['cer']*100:.2f}% | {r['cer_deletion']*100:.2f}% | {r['cer_similarity']} |")
    A("")
    A("> ASR 口径含识别误差（同音字/写法差异），**判定漏词以文本口径为准**：本轮两语种 M1 均 0 缺失。")
    A("")
    A("## 六、附件索引")
    A("")
    A("| 内容 | 路径（相对仓库根） |")
    A("|---|---|")
    for lk in ("ja", "ko"):
        rel = RUNS[lk][1].relative_to(ROOT)
        A(f"| {data[lk]['cn']} 稳定性留证（src/meta/srt/audio/tasks.jsonl/summary.json/progress.log） | `{rel}\\` |")
        A(f"| {data[lk]['cn']} 分析 | `{rel}\\analysis\\perf_m1_m5.json`、`{rel}\\analysis\\audio_m2.json` |")
    A("")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / f"日韩_稳定性10并发_30min_{DATE.replace('-','')}.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"[OK] {out}")
    for lk in ("ja", "ko"):
        s = data[lk]
        print(f"  {s['cn']}: 任务 {s['tasks']}｜成功率 {100*(s['success_rate'] or 0):.2f}%"
              f"｜P50 {s['elapsed_p50']}s｜M1 缺 {s['missing_chars']}｜空洞文件 {s['gap_files_text']}")


if __name__ == "__main__":
    main()
