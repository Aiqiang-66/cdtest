# -*- coding: utf-8 -*-
r"""生成「本轮总报告」：日/韩 接口用例 + 10 并发稳定性（含必测项与缺陷清单）。

读取：
  mp3/文案格式用例_0924_{ja,ko}/results.json
  mp3/Higgs_{日语,韩语}_稳定性10并发_30min_0924/{summary.json, analysis/perf_m1_m5.json, analysis/audio_m2.json}
  mp3/analysis_ja_ko_asr_m3/asr_stab_{ja,ko}.json
输出：
  docs/听书测试物料/测试报告/日韩_接口与稳定性_总报告_20260924.md
"""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(r"D:\python\dmx\cdtest")
MP3 = ROOT / "docs" / "听书测试物料" / "mp3"
REPORT_DIR = ROOT / "docs" / "听书测试物料" / "测试报告"
DATE = "2026-09-24"
CASES = {"ja": ("日语", MP3 / "文案格式用例_0924_ja"),
         "ko": ("韩语", MP3 / "文案格式用例_0924_ko")}
STAB = {"ja": ("日语", MP3 / "Higgs_日语_稳定性10并发_30min_0924"),
        "ko": ("韩语", MP3 / "Higgs_韩语_稳定性10并发_30min_0924")}


def jload(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def main():
    cases, stab = {}, {}
    for lk, (cn, d) in CASES.items():
        res = jload(d / "results.json") or {}
        cases[lk] = {"cn": cn, "res": res, "counts": Counter(v.get("verdict") for v in res.values())}
    for lk, (cn, d) in STAB.items():
        rows = [json.loads(l) for l in (d / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        stab[lk] = {
            "cn": cn, "dir": d, "rows": rows, "ok": [r for r in rows if r.get("ok")],
            "stuck": [r for r in rows if not r.get("ok")],
            "summary": jload(d / "summary.json") or {},
            "perf": (jload(d / "analysis" / "perf_m1_m5.json") or {}).get("perf", {}),
            "m1": (jload(d / "analysis" / "perf_m1_m5.json") or {}).get("m1", {}),
            "m5": (jload(d / "analysis" / "perf_m1_m5.json") or {}).get("m5", {}),
            "m2": jload(d / "analysis" / "audio_m2.json") or {},
            "non_audio_refetched": (jload(d / "analysis" / "audio_m2.json") or {}).get("refetched_files") or 0,
            "no_audio_seqs": sorted(r["seq"] for r in rows if not r.get("ok")),
        }
    asr = {lk: jload(MP3 / "analysis_ja_ko_asr_m3" / f"asr_stab_{lk}.json") or {} for lk in ("ja", "ko")}

    L = []
    A = L.append
    A("# 日/韩 TTS 接口 —— 测试与稳定性 总报告")
    A("")
    A(f"> **被测**：Higgs TTS v3（链路A `POST /Video/CreateUniversalTransparent`，`taskType=74`）；"
      f"日语 `lang=9/Japanese_female`、韩语 `lang=14/Korean_female`  ")
    A(f"> **环境**：`https://ai-main-none-dev.changdu.ltd`（测试环境）  ")
    A(f"> **语料**：M0 合规（保留段落换行）~5000 字符单元；日语 106 单元 / 韩语 321 单元  ")
    A(f"> **依据**：`SKILL.md` v1.1.7（M0 前置 + M1~M5 必测项 + Phase 4 稳定性 + Phase 9 产物层）  ")
    A(f"> **日期**：{DATE}")
    A("")
    A("## 一、测试范围")
    A("")
    A("| 轮次 | 内容 | 语种 | 规模 |")
    A("|---|---|---|---|")
    A("| 接口测试 | 文案格式正/逆向用例（`测试用例/文案格式_正常与异常_0924.md`） | 日语、韩语 | 各 19 条 |")
    A("| 稳定性测试 | **并发 10 × 30 分钟连续打满**（每语种单独执行） | 日语、韩语 | 82 / 98 任务 |")
    A("")
    A("## 二、结论速览")
    A("")
    A("### 2.1 接口用例")
    A("")
    A("| 语种 | PASS | FAIL | ERROR | INFO | 结论 |")
    A("|---|---:|---:|---:|---:|---|")
    for lk in ("ja", "ko"):
        c = cases[lk]["counts"]
        A(f"| {cases[lk]['cn']} | {c.get('PASS',0)} | {c.get('FAIL',0)} | {c.get('ERROR',0)} |"
          f" {c.get('INFO',0)} | {'❌ 存在缺陷（参数校验缺失）' if c.get('FAIL') else '✅'} |")
    A("")
    A("### 2.2 稳定性（并发 10 × 30 分钟）")
    A("")
    A("| 指标 | 日语 | 韩语 |")
    A("|---|---|---|")
    for name, f in (("任务 / 成功 / 失败", lambda s: f"{len(s['rows'])} / {len(s['ok'])} / {len(s['stuck'])}"),
                    ("成功率", lambda s: f"{s['summary'].get('success_rate',0)*100:.2f}%"),
                    ("吞吐（加载期）", lambda s: f"{s['perf'].get('throughput_loadphase_per_min')} 任务/分钟"),
                    ("端到端 平均 / P50", lambda s: f"{s['perf'].get('elapsed_avg')} / {s['perf'].get('elapsed_p50')} s"),
                    ("端到端 P95 / P99", lambda s: f"{s['perf'].get('elapsed_p95')} / {s['perf'].get('elapsed_p99')} s"),
                    ("**M1 缺失字 / 缺失率**",
                     lambda s: f"{s['m1'].get('missing_chars_total')} / {(s['m1'].get('missing_char_ratio') or 0)*100:.4f}%"),
                    ("M1 逐字符一致任务", lambda s: f"{s['m1'].get('tasks_identical_chars')}/{len(s['ok'])}"),
                    ("M5 空字幕 / SRT≠segments", lambda s: f"{s['m5'].get('empty_segments_total')} / {s['m5'].get('tasks_srt_ne_segments')}"),
                    ("M2 触顶文件 / 分析数", lambda s: f"{s['m2'].get('files_peak_fail')}/{s['m2'].get('analyzed')}"),
                    ("M2 峰值 max / RMS", lambda s: f"{s['m2'].get('peak_max')} / {s['m2'].get('rms_avg')} dBFS"),
                    ("M2 静默空洞（含文本）", lambda s: f"{s['m2'].get('files_long_gap_with_text')} 个文件 / 最长 {s['m2'].get('gap_max_s')}s"),
                    ("产物首轮非音频响应（重下全部成功）", lambda s: f"{s['non_audio_refetched']} 个"),
                    ("卡死任务一览", lambda s: "、".join(f"seq {r.get('seq')} taskId={r.get('taskId')}" for r in s["stuck"]) or "无"),
                    ("段级 超长段 / 高语速段", lambda s: f"{s['perf'].get('_x',0) if False else s['summary'].get('max_seg_chars_overall')} 字上限 / "
                                                  f"{sum(r.get('n_seg_rate_gt15') or 0 for r in s['ok'])} 段"),
                    ("任务语速中位", lambda s: f"{s['summary'].get('baseline_chars_per_s')} 字/秒")):
        A(f"| {name} | {f(stab['ja'])} | {f(stab['ko'])} |")
    A("")
    A("## 三、缺陷清单（给开发）")
    A("")
    A("| # | 级别 | 缺陷 | 证据 | 建议 |")
    A("|---|---|---|---|---|")
    A("| 1 | **P1** | **参数校验缺失**：`read_content` 为空/纯空白、`lang=999` 均返回成功并产出音频 | 接口用例 A04a/A04b/A10（两语种一致） | 建任务前做参数白名单校验，非法返回明确错误码 |")
    A(f"| 2 | **P1** | **任务卡死在 `status=67`** | 日语 {len(stab['ja']['stuck'])} 个 / 韩语 {len(stab['ko']['stuck'])} 个；"
      f"直到收尾 drain 上限仍未收敛，成功率降至 {stab['ja']['summary'].get('success_rate',0)*100:.2f}% / "
      f"{stab['ko']['summary'].get('success_rate',0)*100:.2f}% | 处理中任务需超时收敛 + 队列/槽位可观测 |")
    A(f"| 3 | **P1** | **产物立即可获取性**：任务成功但立即拉取 `audio_url` 得到 COS 错误页 | 首轮日语 {stab['ja']['non_audio_refetched']} / "
      f"韩语 {stab['ko']['non_audio_refetched']} 个；**重下 100% 成功** → 对象可见性竞态 | 置成功前做对象可读性校验（HEAD） |")
    A(f"| 4 | **P1** | **日语静默空洞**（metadata 有文本、音频近乎无声） | 日语 {stab['ja']['m2'].get('files_long_gap_with_text')} 个文件、"
      f"最长 {stab['ja']['m2'].get('gap_max_s')}s（81.64s 占位签名）；**M0 合规语料下仍复现** | 分段合成失败必须重试或显式报错，禁止静默占位 |")
    A(f"| 5 | **P2** | **段级时间轴不可信** | 日语 {sum(r.get('n_seg_rate_gt15') or 0 for r in stab['ja']['ok'])} 个段 >15 字/秒"
      f"（最坏 69 字只给 0.56s）；ASR 定点核查显示该窗口音频内容与 metadata 错位 | 时间轴应基于实际音频生成；偏差超阈值告警 |")
    A(f"| 6 | P2 | **日语削波/响度越界** | 日语 M2 触顶 {stab['ja']['m2'].get('files_peak_fail')}/{stab['ja']['m2'].get('analyzed')}"
      f"（峰值 max {stab['ja']['m2'].get('peak_max')}）、RMS {stab['ja']['m2'].get('rms_avg')} dBFS | 输出前真峰值限幅/响度归一 |")
    A("")
    A("## 四、必测项结论（M0~M5）")
    A("")
    A("| 项 | 日语 | 韩语 | 判定 |")
    A("|---|---|---|---|")
    A("| **M0 前置**（语料保留段落） | ✅ 每单元 47~109 段、段长上限 80 字 | ✅ 每单元 47~102 段 | ✅ 通过 |")
    A(f"| **M1 文案一致性** | 缺失 0 字（{stab['ja']['m1'].get('tasks_identical_chars')}/{len(stab['ja']['ok'])} 逐字符一致） |"
      f" 缺失 0 字（{stab['ko']['m1'].get('tasks_identical_chars')}/{len(stab['ko']['ok'])}） | ✅ 通过 |")
    A(f"| **M2 音质** | 触顶 {stab['ja']['m2'].get('files_peak_fail')}、空洞 {stab['ja']['m2'].get('files_long_gap_with_text')} 文件 |"
      f" 触顶 {stab['ko']['m2'].get('files_peak_fail')}、空洞 0 | ❌ 日语不通过；⏸ 人工听测未做 |")
    A(f"| **M3 漏词** | 文本口径 0；ASR 抽样删除率 0.29~4.95% | 文本口径 0；ASR 抽样删除率 0% | ✅（文本口径为准） |")
    A("| **M4 切句** | 无超长段（≤80 字）、无截断/乱序证据 | 同左 | ✅ |")
    A(f"| **M5 字幕完整性** | 空字幕 {stab['ja']['m5'].get('empty_segments_total')}、SRT≠segments {stab['ja']['m5'].get('tasks_srt_ne_segments')} |"
      f" 空字幕 {stab['ko']['m5'].get('empty_segments_total')}、SRT≠segments {stab['ko']['m5'].get('tasks_srt_ne_segments')} | ✅ 通过 |")
    A("")
    A("## 五、Phase 9 产物层结论")
    A("")
    A(f"- **产物立即可获取性**：❌ 日语 {stab['ja']['non_audio_refetched']}、韩语 {stab['ko']['non_audio_refetched']} 个任务"
      f"首轮拉取失败（COS 错误页），**重下 100% 成功** → 竞态（P1）")
    A(f"- **跨区下载**：⚠️ 未系统测（本次仅观察到个别连接超时后重试成功）")
    A(f"- **音频可解码性/时长一致性**：✅ 全部可解码；音频 vs metadata 总时长差 ≤80ms")
    A(f"- **任务卡死**：❌ 见缺陷 2")
    A(f"- **待确认需求项**（ID3 标题、URL 访问策略、priority、审核、留存期）：⏸ 按 SKILL Phase 9.3 以 INFO 处理，未判定")
    A("")
    A("## 六、与历史批次对照（口径变化的影响）")
    A("")
    A("| 项 | 0924 批（单段落语料） | 本轮（M0 合规语料） |")
    A("|---|---|---|")
    A("| `distinct paraIndex` | 恒为 0（段落结构丢失） | 随段落数增长（日语探针 87） |")
    A("| 最长段 | 日语 659 字 / 韩语 1757 字 | **≤80 字** |")
    A("| 段语速极值 | 最高 277 字/秒 | 最高 122.8 字/秒（1.3% 段 >15） |")
    A("| 韩语音频内容缺失 | 16 个任务估算缺口 20~46% | 未复现（M1=0，ASR 删除率 0%） |")
    A("| 日语静默空洞 | 3 文件 / 最长 82s | **5 文件 / 最长 82.56s（仍复现）** |")
    A("| 成功率 | 100% / 99.24% | 96.34% / 97.96%（卡死任务所致） |")
    A("")
    A("> 结论：**M0 段落格式修复显著改善了切句退化**（超长段消失、韩语内容缺失未复现），"
      "但**不能解决**静默空洞、产物竞态、任务卡死这三类服务端缺陷 —— 它们必须由服务端修复。")
    A("")
    A("## 七、数据与附件索引")
    A("")
    A("| 内容 | 路径（相对仓库根） |")
    A("|---|---|")
    A("| 接口用例结果（逐用例指标+判定） | `mp3\\文案格式用例_0924_ja\\results.json`、`mp3\\文案格式用例_0924_ko\\results.json` |")
    A("| 稳定性留证（src/meta/srt/audio/tasks.jsonl/summary.json） | `mp3\\Higgs_日语_稳定性10并发_30min_0924\\`、`mp3\\Higgs_韩语_稳定性10并发_30min_0924\\` |")
    A("| 性能+M1+M5 / 音质分析 | 各批 `analysis\\perf_m1_m5.json`、`analysis\\audio_m2.json` |")
    A("| M3 抽样 | `mp3\\analysis_ja_ko_asr_m3\\asr_stab_ja.json`、`asr_stab_ko.json` |")
    A("| 段级时间轴定点核查 | `mp3\\analysis_ja_ko_asr_m3\\asr_rate_check.json` + 各批 `analysis\\asr\\task_0054_*.txt` |")
    A("| 明细报告 | `测试报告\\文案格式用例_结果_日韩_20260924.md`、`测试报告\\日韩_稳定性10并发_30min_20260924.md` |")
    A("| **开发分析包** | `开发分析包_接口与稳定性_0924\\`（含 README、缺陷证据、音频片段、ASR 对照） |")
    A("")
    A("## 八、待办与未覆盖项")
    A("")
    A("1. **M2 人工听测**未做（技能硬性要求，需人工试听；抽样清单见各批 `analysis\\audio_listen_checklist.md`）。")
    A("2. **Phase 9 未覆盖**：跨区下载质量、首尾完整性、签名时效重取、并发拉取、`<taskId>.mp3` 可枚举越权。")
    A("3. **密钥轮换**建议（此前片段曾在远端存在约 10 分钟；负责人暂缓）。")
    A("4. 本报告数据仅覆盖 2026-09-24 本轮（接口 2×19 条 + 稳定性 2×30 分钟），不代表其它时段/环境。")
    A("")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / f"日韩_接口与稳定性_总报告_{DATE.replace('-','')}.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"[OK] {out}")


if __name__ == "__main__":
    main()
