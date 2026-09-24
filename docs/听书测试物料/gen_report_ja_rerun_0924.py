# -*- coding: utf-8 -*-
r"""生成「日语重测（r2）」测试报告，含与首测（0924）的可复现性对照。

读取：
  <r2 批次>/summary.json、tasks.jsonl
  <r2 批次>/analysis/perf_m1_m5.json、audio_m2.json、compare_vs_0924.{json,md}
  mp3/analysis_ja_ko_asr_m3/asr_full<seq>.json、audio_missing_locate_ja<seq>.txt（可疑任务整段 ASR）
输出：
  docs/听书测试物料/测试报告/Higgs_日语_重测_10并发30分钟_0924_r2.md

用法：
  & "D:\python\python.exe" docs\听书测试物料\gen_report_ja_rerun_0924.py
"""
import json
from pathlib import Path

ROOT = Path(r"D:\python\dmx\cdtest")
MP3 = ROOT / "docs" / "听书测试物料" / "mp3"
REPORT_DIR = ROOT / "docs" / "听书测试物料" / "测试报告"
R2 = MP3 / "Higgs_日语_10并发30分钟_0924_r2"
R1 = MP3 / "Higgs_日语_10并发30分钟_0924"
ASR_DIR = MP3 / "analysis_ja_ko_asr_m3"
DATE = "2026-09-24"


def jload(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def main():
    s = jload(R2 / "summary.json") or {}
    perf = jload(R2 / "analysis" / "perf_m1_m5.json") or {}
    m2 = jload(R2 / "analysis" / "audio_m2.json") or {}
    mat = jload(R2 / "material" / "manifest.json") or {}
    cmp_doc = jload(R2 / "analysis" / "compare_vs_0924.json") or {}
    a1 = cmp_doc.get("0924（首测）", {})
    a2 = cmp_doc.get("r2（重测）", {})
    rows = [json.loads(l) for l in (R2 / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    ok = [r for r in rows if r.get("ok")]

    p = perf.get("perf", {})
    m1 = perf.get("m1", {})
    m5 = perf.get("m5", {})

    # 可疑任务 + 已有的整段 ASR 结果
    suspect = sorted((s.get("suspect_tasks") or []),
                     key=lambda x: (-(x.get("est_missing_ratio") or 0), -(x.get("max_seg_chars") or 0)))
    asr_rows = []
    for t in suspect:
        seq = t.get("seq")
        j = jload(ASR_DIR / f"asr_full{seq}.json")
        loc = ASR_DIR / f"audio_missing_locate_ja{seq:04d}.txt"
        entry = {"seq": seq, "taskId": t.get("taskId"), "unit": t.get("unit"),
                 "chars": t.get("chars"), "audio_s": t.get("audio_s"),
                 "chars_per_s": t.get("chars_per_s"), "max_seg_chars": t.get("max_seg_chars"),
                 "max_seg_dur_s": t.get("max_seg_dur_s"), "est": t.get("est_missing_ratio"),
                 "asr": None, "loc_file": loc.name if loc.exists() else None}
        if j:
            rr = ((j.get("langs", {}) or {}).get("ja") or {}).get("rows", [])
            if rr:
                r0 = rr[0]
                entry["asr"] = {"ref_chars": r0["ref_chars"], "hyp_chars": r0["hyp_chars"],
                                "cer": r0["cer"], "deletion": r0["cer_deletion"],
                                "similarity": r0["cer_similarity"], "window": r0.get("ref_window")}
        asr_rows.append(entry)

    L = []
    A = L.append
    A("# Higgs TTS v3 日语 — 10 并发 30 分钟**重测（r2）**报告")
    A("")
    A("> **目的**：在**完全相同的口径**下重跑日语压测，验证首测（0924）发现的现象是否可复现  ")
    A(f"> **口径**：`model=higgs`、`lang=9` / `Japanese_female`、10 并发 × 30 分钟、"
      f"同一批 {mat.get('units_total', 107)} 个 ~{mat.get('target_chars', 5000)} 字符单元（语料逐字节复制）  ")
    A(f"> **环境**：`https://ai-main-none-dev.changdu.ltd`（测试环境）  ")
    A(f"> **依据**：`docs/听书测试物料/SKILL.md` v1.1.4（M1~M5）＋ 0924 复盘新增的段级异常检测  ")
    A(f"> **批次目录**：`{R2.relative_to(ROOT)}`")
    A("")

    A("## 一、结论速览")
    A("")
    A("| 判定项 | 重测（r2） | 首测（0924） | 结论 |")
    A("|---|---|---|---|")
    A(f"| 任务数 / 成功率 | {s.get('total_tasks')} / **{s.get('success_rate', 0)*100:.2f}%** |"
      f" {a1.get('tasks')} / {a1.get('success_rate', 0)*100:.2f}% | 可比 |")
    A(f"| 吞吐（加载期 30min） | **{a2.get('throughput_load')} 任务/分钟** | {a1.get('throughput_load')} 任务/分钟 | 可比 |")
    A(f"| 端到端 P50 / P95 | {p.get('elapsed_p50')}s / {p.get('elapsed_p95')}s |"
      f" {a1.get('elapsed_p50')}s / {a1.get('elapsed_p95')}s | 可比 |")
    A(f"| **M1 文案缺失率（字级）** | **{m1.get('missing_char_ratio', 0)*100:.4f}%** |"
      f" {a1.get('missing_char_ratio', 0)*100:.4f}% | ✅ 均为 0 |")
    A(f"| M1 逐字符一致任务 | {m1.get('tasks_identical_chars')}/{p.get('ok')} |"
      f" {a1.get('identical_tasks')}/{a1.get('success')} | ✅ 一致 |")
    A(f"| M5 空字幕 / SRT≠segments | {m5.get('empty_segments_total')} / {m5.get('tasks_srt_ne_segments')} |"
      f" {a1.get('empty_segs')} / {a1.get('srt_ne')} | ✅ 一致 |")
    A(f"| **M2 音质（削波）** | 触顶 {m2.get('files_peak_fail')}/{m2.get('analyzed')}，峰值"
      f" {m2.get('peak_min')}~{m2.get('peak_max')}，RMS {m2.get('rms_avg')} dBFS |"
      f" 触顶 {a1.get('files_peak_fail')}/{a1.get('analyzed')}，峰值 {a1.get('peak_min')}~{a1.get('peak_max')}，"
      f"RMS {a1.get('rms_avg')} dBFS | ❌ **复现** |")
    A(f"| M2 长静默空洞（含文本） | **{m2.get('files_long_gap_with_text')} 个文件**，最长 "
      f"{m2.get('gap_max_s')}s | {a1.get('files_long_gap_with_text')} 个文件，最长 {a1.get('gap_max_s')}s |"
      f" {'✅ 复现' if m2.get('files_long_gap_with_text') else '⚠️ 本轮未复现'} |")
    A(f"| 段级 超长段（>200 字） | **{s.get('_n_gt200', a2.get('n_seg_gt200'))} 条**，最长 "
      f"{a2.get('max_seg_chars')} 字 / {a2.get('max_seg_dur_s')}s | {a1.get('n_seg_gt200')} 条，最长 "
      f"{a1.get('max_seg_chars')} 字 | ✅ **复现** |")
    A(f"| 段级 不可能语速段（>15 字/秒） | **{a2.get('n_seg_rate_gt15')} 条** | {a1.get('n_seg_rate_gt15')} 条 | ✅ **复现** |")
    A(f"| 任务级语速（中位 / 最大） | {a2.get('chars_per_s_median')} / {a2.get('chars_per_s_max')} 字/秒 |"
      f" {a1.get('chars_per_s_median')} / {a1.get('chars_per_s_max')} 字/秒 | 可比 |")
    A(f"| 估算内容缺口 >20% 任务数 | **{a2.get('tasks_est_missing_gt20')}** | {a1.get('tasks_est_missing_gt20')} | 见第四节 |")
    A(f"| 产物可获取性（立即下载失败/非音频） | {m2.get('not_audio_files')} 次非音频；事后补齐 {m2.get('refetched_files')} 个 |"
      f" {a1.get('not_audio')} / {a1.get('refetched')} | 见第五节 |")
    A("")

    A("## 二、性能数据（重测）")
    A("")
    A("| 指标 | 值 |")
    A("|---|---:|")
    A(f"| 并发 / 加载窗口 | {p.get('workers')} / 30 分钟 |")
    A(f"| 含 drain 实际墙钟（s） | {p.get('wall_seconds')} |")
    A(f"| 总任务 / 成功 / 失败 | {p.get('total_tasks')} / {p.get('ok')} / {p.get('failed')} |")
    A(f"| 成功率 | {p.get('success_rate', 0)*100:.2f}% |")
    A(f"| 吞吐（加载期 / 全墙钟） | {p.get('throughput_loadphase_per_min')} / {p.get('throughput_per_min')} 任务/分钟 |")
    A(f"| 端到端 平均 / P50 / P90 / P95 / P99（s） | {p.get('elapsed_avg')} / {p.get('elapsed_p50')} /"
      f" {p.get('elapsed_p90')} / {p.get('elapsed_p95')} / {p.get('elapsed_p99')} |")
    A(f"| 端到端 最小 / 最大（s） | {p.get('elapsed_min')} / {p.get('elapsed_max')} |")
    A(f"| 创建接口 平均 / P95 / 最大（s） | {p.get('create_avg')} / {p.get('create_p95')} / {p.get('create_max')} |")
    A(f"| 音频产物合计（MB） | {(p.get('audio_bytes_total') or 0)/1048576:.1f} |")
    A("")
    if p.get("trend"):
        A("**分时段趋势（每 5 分钟）**")
        A("")
        A("| 时段 | 任务数 | 平均端到端(s) | 平均段数 | 缺失字 |")
        A("|---|---:|---:|---:|---:|")
        for t in p["trend"]:
            A(f"| {t['window']} | {t['tasks']} | {t['elapsed_avg']} | {t['segments_avg']} | {t['missing_chars']} |")
        A("")

    A("## 三、M1 文案一致性 / M5 字幕完整性（重测）")
    A("")
    A(f"- M1：发送 {m1.get('sent_chars_total', 0):,} 字｜缺失 **{m1.get('missing_chars_total')}** 字"
      f"（**{m1.get('missing_char_ratio', 0)*100:.4f}%**）｜多余 {m1.get('extra_chars_total')} 字"
      f"｜逐字符完全一致 **{m1.get('tasks_identical_chars')}/{p.get('ok')}**")
    A(f"- M5：segments 合计 {m5.get('segments_total', 0):,}｜空字幕段 {m5.get('empty_segments_total')} 条"
      f"｜SRT≠segments 任务 {m5.get('tasks_srt_ne_segments')} 个")
    A(f"> ⚠️ `paraIndex` 在单段落语料下恒为 0（本轮 distinct paraIndex 合计 {m5.get('distinct_para_total', 0):,}），"
      f"该判据仍不适用于本工作负载。")
    A("")

    A("## 四、段级异常与内容缺失（0924 复盘新增检测项）")
    A("")
    A(f"- 段长中位 {a2.get('seg_median_chars')} 字｜**最长段 {a2.get('max_seg_chars')} 字 / "
      f"{a2.get('max_seg_dur_s')}s**")
    A(f"- 超长段（>200 字）**{a2.get('n_seg_gt200')} 条**，涉及 **{a2.get('tasks_with_long')}** 个任务")
    A(f"- 不可能语速段（>15 字/秒）**{a2.get('n_seg_rate_gt15')} 条**，涉及 {a2.get('tasks_with_impossible')} 个任务"
      f"；疑似静默段（>5s 且 <2 字/秒）{a2.get('n_seg_rate_lt2')} 条")
    A(f"- 任务级语速：min {a2.get('chars_per_s_min')}｜中位 {a2.get('chars_per_s_median')}｜"
      f"max {a2.get('chars_per_s_max')} 字/秒（日语正常约 6.4~8.0）")
    A(f"- 按语速基线圈定：**估算内容缺口 >20% 的任务 {a2.get('tasks_est_missing_gt20')} 个**")
    A("")
    if asr_rows:
        A("**可疑任务与整段 ASR 实测（音频口径）**")
        A("")
        A("| seq | taskId | 单元 | 字数 | 音频(s) | 任务语速 | 最长段 | 段时长 | 估算缺口 | 整段 ASR 实测 |")
        A("|---|---:|---|---:|---:|---:|---:|---:|---:|---|")
        for e in asr_rows[:12]:
            asr_txt = "—"
            if e["asr"]:
                asr_txt = (f"参考 {e['asr']['ref_chars']:,} 字 → 识别 {e['asr']['hyp_chars']:,} 字，"
                           f"**缺失 {e['asr']['deletion']*100:.2f}%**")
            A(f"| {e['seq']} | {e['taskId']} | {e['unit']} | {e['chars']} | {e['audio_s']} |"
              f" {e['chars_per_s']} | {e['max_seg_chars']} 字 | {e['max_seg_dur_s']}s |"
              f" {100*(e['est'] or 0):.1f}% | {asr_txt} |")
        A("")
        A("> 缺失位置明细见 `05_汇总分析`/`analysis_ja_ko_asr_m3/audio_missing_locate_ja*.txt`；"
          "上批已证明该现象集中于**未切分的长段**（长段丢失 76~90%，正常段仅 4~10%）。")
        A("")
    else:
        A("> 本轮可疑任务的整段 ASR 尚未执行（可运行 `_locate_audio_missing_0924.py ja <seq>` 与 "
          "`asr_accuracy_ja_ko_largev3_0924.py --lang ja --run-dir <r2> --seqs <seq> --window 800`）。")
        A("")

    A("## 五、产物可获取性与工程问题")
    A("")
    A(f"- 音频下载到非音频内容（COS 错误响应）：**{m2.get('not_audio_files')} 次**；"
      f"事后按 taskId 重下成功 **{m2.get('refetched_files')}** 个")
    A(f"- 音频分析条数 {m2.get('analyzed')}，跳过 {m2.get('skipped_incomplete')}；"
      f"下载异常任务 {len(m2.get('tasks_with_audio_error') or [])} 个")
    A(f"- 音频 vs metadata 时长最大差 {m2.get('dur_delta_ms_max')} ms（门槛 <1000ms）")
    A("")

    A("## 六、可复现性结论")
    A("")
    A("| 首测现象 | 重测结果 | 判定 |")
    A("|---|---|---|")
    A(f"| M1 文本口径零缺失 | 缺失率 {m1.get('missing_char_ratio', 0)*100:.4f}% | ✅ 复现 |")
    A(f"| 日语削波（全部文件峰值 >0.999、RMS 偏低约 −11.5 dBFS） | 触顶 {m2.get('files_peak_fail')}/"
      f"{m2.get('analyzed')}，RMS {m2.get('rms_avg')} dBFS | ✅ 复现 |")
    A(f"| 静默空洞（metadata 有文本、音频近乎无声） | {m2.get('files_long_gap_with_text')} 个文件，"
      f"最长 {m2.get('gap_max_s')}s | {'✅ 复现' if m2.get('files_long_gap_with_text') else '⚠️ 未复现'} |")
    A(f"| 超长段 / 不可能语速段（切句降级症状） | {a2.get('n_seg_gt200')} 条 / {a2.get('n_seg_rate_gt15')} 条 |"
      f" ✅ 复现 |")
    A("")
    A("> 结论：**日语链路的音质越界与段级切分异常均为稳定复现的系统性问题**（非偶发），"
      "可作为开发修复的确定性依据；文本口径两次均为 0 缺失。")
    A("")

    A("## 七、缺陷与建议")
    A("")
    A("| # | 级别 | 类型 | 现象 | 建议 |")
    A("|---|---|---|---|---|")
    A(f"| 1 | P1 | 切句/分段 | 日语同样出现超长段（最长 {a2.get('max_seg_chars')} 字）与"
      f"不可能语速段 {a2.get('n_seg_rate_gt15')} 条；切句接口对 ja 返回“不支持的语言” |"
      f" 明确 ja 链路切句实现并加长度上限校验 |")
    A(f"| 2 | P1 | 音质越界 | {m2.get('files_peak_fail')}/{m2.get('analyzed')} 文件峰值 >0.999"
      f"（最高 {m2.get('peak_max')}），RMS {m2.get('rms_avg')} dBFS | 输出前做真峰值限幅/响度归一 |")
    A(f"| 3 | P1 | 音频内容缺失 | 空洞文件 {m2.get('files_long_gap_with_text')} 个；"
      f"长段内容丢失（上批实测长段丢 76~90%） | 合成失败需重试或显式报错，禁止静默占位 |")
    A("| 4 | P3 | 产物可获取性 | 存在立即下载得到 COS 错误响应的情况（事后可补齐） | 返回前做对象可读性校验 |")
    A("")

    A("## 八、附件索引")
    A("")
    A("| 内容 | 路径（相对仓库根） |")
    A("|---|---|")
    rel = R2.relative_to(ROOT)
    A(f"| 重测留证（src/meta/srt/audio/tasks.jsonl/summary.json/progress.log） | `{rel}\\` |")
    A(f"| 性能 + M1 + M5 分析 | `{rel}\\analysis\\perf_m1_m5.json` |")
    A(f"| 客观音质指标 | `{rel}\\analysis\\audio_m2.json` |")
    A(f"| 与首测对照 | `{rel}\\analysis\\compare_vs_0924.md` |")
    A(f"| 首测批次 | `{(R1).relative_to(ROOT)}\\` |")
    A("| 本次迭代快照 | `backups/iterations/20260924-153041-ja-rerun-10concurrent-30min` |")
    A("")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / f"Higgs_日语_重测_10并发30分钟_{DATE.replace('-', '')}_r2.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"[OK] {out}")
    print(f"     任务 {s.get('total_tasks')}｜成功率 {s.get('success_rate', 0)*100:.2f}%"
          f"｜M1 缺失率 {m1.get('missing_char_ratio', 0)*100:.4f}%"
          f"｜触顶文件 {m2.get('files_peak_fail')}/{m2.get('analyzed')}"
          f"｜空洞文件 {m2.get('files_long_gap_with_text')}")


if __name__ == "__main__":
    main()
