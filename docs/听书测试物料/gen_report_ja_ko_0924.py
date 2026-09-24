# -*- coding: utf-8 -*-
r"""组装日/韩 10 并发 30 分钟压测正式报告（技能「报告交付规范」1~12 节）。

读取：
  mp3/Higgs_日语|韩语_10并发30分钟_0924/analysis/{perf_m1_m5.json,audio_m2.json}
  mp3/analysis_ja_ko_asr_m3/{asr_m3.json,asr_gapcheck*.json}
  mp3/Higgs_日语|韩语_10并发30分钟_0924/material/manifest.json
输出：
  docs/听书测试物料/测试报告/Higgs_日韩_10并发30分钟_20260924.md

用法：
  & "D:\python\python.exe" docs\听书测试物料\gen_report_ja_ko_0924.py
"""
import json
from pathlib import Path

ROOT = Path(r"D:\python\dmx\cdtest")
MP3 = ROOT / "docs" / "听书测试物料" / "mp3"
REPORT_DIR = ROOT / "docs" / "听书测试物料" / "测试报告"
RUNS = {
    "ja": ("日语", MP3 / "Higgs_日语_10并发30分钟_0924"),
    "ko": ("韩语", MP3 / "Higgs_韩语_10并发30分钟_0924"),
}
ASR_DIR = MP3 / "analysis_ja_ko_asr_m3"
DATE = "2026-09-24"


def jload(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def main():
    D = {}
    for lang, (cn, run) in RUNS.items():
        D[lang] = {
            "cn": cn, "dir": run,
            "perf": jload(run / "analysis" / "perf_m1_m5.json"),
            "m2": jload(run / "analysis" / "audio_m2.json"),
            "mat": jload(run / "material" / "manifest.json"),
            "summary": jload(run / "summary.json"),
        }
    asr = jload(ASR_DIR / "asr_m3.json") or {"langs": {}}
    ph = jload(MP3 / "analysis_ja_ko_placeholder_segments.json") or {"langs": {}}
    gap_ja = jload(ASR_DIR / "asr_gapcheck.json") or {}
    gap_ja_ctrl = jload(ASR_DIR / "asr_gapcheck_ctrl.json") or {}
    gap_ko = jload(ASR_DIR / "asr_gapcheck_ko.json") or {}

    pj, pk = D["ja"]["perf"]["perf"], D["ko"]["perf"]["perf"]
    m1j, m1k = D["ja"]["perf"]["m1"], D["ko"]["perf"]["m1"]
    m5j, m5k = D["ja"]["perf"]["m5"], D["ko"]["perf"]["m5"]
    a2j, a2k = D["ja"]["m2"], D["ko"]["m2"]

    def m2_fail(a):
        return a["files_peak_fail"] > 0 or a["files_long_gap_with_text"] > 0

    L = []
    A = L.append

    A("# Higgs TTS v3 日语 / 韩语 10 并发 30 分钟高并发性能测试报告")
    A("")
    A("> **被测对象**：Higgs TTS v3（链路 A：`POST /Video/CreateUniversalTransparent`，`taskType=74`）  ")
    A("> **语种**：日语（`lang=9` / `Japanese_female`）、韩语（`lang=14` / `Korean_female`），两语种**分别**独立压测  ")
    A(f"> **日期**：{DATE}　**版本**：v1.1（修订测量口径）　**执行**：QA 自动化 Agent（脚本）＋ 人工听测待补  ")
    A("> **依据**：`docs/听书测试物料/SKILL.md` v1.1.4（必测项 M1~M5、报告交付规范 1~12 节）")
    A("")
    A("> ⚠️ **本报告相对初稿的修订**（均为「审计脚本自证」后纠正，见第十一节）：")
    A("> ① `audio_url` 立即下载返回 COS `NoSuchKey` 的 18 条，**事后重下全部成功** → 属"
      "**产物可见性竞态**，非音频缺失；")
    A("> ② 长文本（单段落）下 `paraIndex` 恒为 0，原「paraIndex 无缺口」判据在本工作负载下**不成立为证据**；")
    A("> ③ 「最长静音 >300ms」在本批语料中 100% 命中，属正常朗读停顿，**不作为缺陷判据**（技能内部与 TC-VT-004 冲突）。")
    A("")

    # ---------------- 一 ----------------
    A("## 一、测试口径")
    A("")
    A("| 项 | 日语 | 韩语 |")
    A("|---|---|---|")
    A("| lang / 音色 | `lang=9` / `Japanese_female` | `lang=14` / `Korean_female` |")
    A(f"| 语料来源 | `{Path(D['ja']['mat']['book']).name}` | `{Path(D['ko']['mat']['book']).name}` |")
    A(f"| 语料单元数 | {D['ja']['mat']['units_total']} 个 | {D['ko']['mat']['units_total']} 个 |")
    A(f"| 单元字符数 | {D['ja']['mat']['chars_min']}~{D['ja']['mat']['chars_max']}（均值 {D['ja']['mat']['chars_avg']}）"
      f" | {D['ko']['mat']['chars_min']}~{D['ko']['mat']['chars_max']}（均值 {D['ko']['mat']['chars_avg']}） |")
    A(f"| 并发 × 时长 | **{pj['workers']} 并发 × 30 分钟** | **{pk['workers']} 并发 × 30 分钟** |")
    A(f"| 实际任务数 / 成功 / 失败 | {pj['total_tasks']} / {pj['ok']} / {pj['failed']} |"
      f" {pk['total_tasks']} / {pk['ok']} / {pk['failed']} |")
    A("| 环境 / 模型 | `https://ai-main-none-dev.changdu.ltd` / `higgs` | 同左 |")
    A("")
    A("- **语料构造**（`build_ja_ko_5000char_material.py`）：按章标记切章（日语 `第N章` 与 `チャプター N` 两套标记都算边界；"
      "韩语 `제N화`），顺序累积**完整句子**至 ≥5000 字符收口；单章不足由后续章节补齐，被章节边界截断的半句**跨章顺延**，"
      "`******` 等装饰分隔行已清除。语料自检：两语种单元**全部以句末标点结尾**、无 >291 字符超长句。")
    A("- **下发方式**：每任务一个 ~5000 字符单元（**单段落，无换行**），`chapter_title` 取该单元首章标题；"
      "服务端把标题作为独立字幕段返回（`paraIndex=-1`），M1 比对时已排除。")
    A("> ⚠️ 因语料为**单段落**，服务端所有正文段 `paraIndex` 恒为 0（实测 111/111 段均为 0），"
      "故本次**无法**用「paraIndex 缺口」判丢句 —— 该判据仅适用于多段落/整章下发。")
    A("- **本次范围**：用户指定的 10 并发高并发压测；同步留证 M1/M5/M2/M3，未做其它语种、16 并发阶梯与 24h 浸泡。")
    A("")

    # ---------------- 二 ----------------
    A("## 二、结论速览")
    A("")
    A("| 维度 | 日语 | 韩语 | 判定 |")
    A("|---|---|---|---|")
    A(f"| 任务成功率 | {pj['success_rate']:.2%}（{pj['ok']}/{pj['total_tasks']}） |"
      f" {pk['success_rate']:.2%}（{pk['ok']}/{pk['total_tasks']}） |"
      f" {'✅ 通过（≥99%）' if min(pj['success_rate'], pk['success_rate']) >= 0.99 else '⚠️ 韩语 1 个任务卡死'} |")
    A(f"| 吞吐（加载期 30 分钟口径） | {pj['throughput_loadphase_per_min']} 任务/分钟"
      f"（≈{pj['throughput_loadphase_per_hour']}/h） | {pk['throughput_loadphase_per_min']} 任务/分钟"
      f"（≈{pk['throughput_loadphase_per_hour']}/h） | 参考 |")
    A(f"| 端到端 P50 / P95 (s) | {pj['elapsed_p50']} / {pj['elapsed_p95']} | {pk['elapsed_p50']} / {pk['elapsed_p95']} | 参考 |")
    A(f"| **M1 文案一致性** | 字级缺失 {m1j['missing_char_ratio']*100:.4f}% | 字级 {m1k['missing_char_ratio']*100:.4f}%"
      f"（词级 {m1k['missing_primary_ratio']*100:.4f}%） | ✅ 通过 |")
    A(f"| **M2 客观音质** | 触顶文件 **{a2j['files_peak_fail']}/{a2j['analyzed']}**｜RMS {a2j['rms_avg']} dBFS"
      f"｜空洞 **{a2j['files_long_gap_with_text']}** 文件 | 触顶文件 **{a2k['files_peak_fail']}/{a2k['analyzed']}**"
      f"｜RMS {a2k['rms_avg']} dBFS｜空洞 **{a2k['files_long_gap_with_text']}** 文件 | ❌ **不通过** |")
    A(f"| M3 漏词（文本口径） | 0 | 0 | ✅ 通过 |")
    A(f"| M5 字幕完整性 | 空字幕 {m5j['empty_segments_total']}｜SRT≠segments {m5j['tasks_srt_ne_segments']}"
      f" | 空字幕 {m5k['empty_segments_total']}｜SRT≠segments {m5k['tasks_srt_ne_segments']} |"
      f" ⚠️ 结构一致，但**音频存在无声空洞**（见下） |")
    A(f"| 产物可获取性 | 立即下载失败 {a2j['refetched_files']} 条（事后全部补齐） |"
      f" 立即失败 {a2k['refetched_files']} 条（事后全部补齐） | ⚠️ 竞态，见第九节 |")
    A("")
    A(f"**一句话结论**：日语、韩语在 10 并发持续 30 分钟下**文案零缺失**（字级 0.0000%，"
      f"日语 94/94、韩语 130/131 成功）；但**音质不通过**——两语种解码峰值普遍越过满刻度"
      f"（日语 {a2j['files_peak_fail']}/{a2j['analyzed']} 文件、峰值最大 {a2j['peak_max']}；"
      f"韩语 {a2k['files_peak_fail']}/{a2k['analyzed']}、最大 {a2k['peak_max']}），"
      f"且 {a2j['files_long_gap_with_text'] + a2k['files_long_gap_with_text']} 个文件存在"
      f"**metadata 有文本、音频却近乎无声的长空洞**（最长 82.6s）；另有 18 条任务的音频在完成时"
      f"**不可立即获取**（COS NoSuchKey，事后重下均成功）与 1 个任务卡死 32 分钟未完成。")
    A("")

    # ---------------- 三 ----------------
    A("## 三、必测项结论（M1~M5）")
    A("")
    A("| # | 必测项 | 日语 | 韩语 | 判定 |")
    A("|---|---|---|---|---|")
    A(f"| M1 | 输入/输出文案一致性 | 字级缺失 {m1j['missing_char_ratio']*100:.4f}%（{m1j['missing_chars_total']} 字）"
      f"｜逐字符一致 {m1j['tasks_identical_chars']}/{pj['ok']} |"
      f" 词级 {m1k['missing_primary_ratio']*100:.4f}%｜字级 {m1k['missing_char_ratio']*100:.4f}%（0 字） | ✅ |")
    A(f"| M2 | 音质 | 峰值 {a2j['peak_min']}~{a2j['peak_max']}（全部 >0.999）｜RMS {a2j['rms_avg']} dBFS"
      f"｜高频>10% {a2j['files_hf_fail']}/{a2j['analyzed']} |"
      f" 峰值 {a2k['peak_min']}~{a2k['peak_max']}（{a2k['files_peak_fail']}/{a2k['analyzed']} 触顶）"
      f"｜RMS {a2k['rms_avg']} dBFS | ❌ 削波；人工听测待做 |")
    ja_asr, ko_asr = asr.get("langs", {}).get("ja"), asr.get("langs", {}).get("ko")
    ja_cell = (f"文本口径 0；ASR(large-v3) CER {100*(ja_asr.get('cer_avg') or 0):.2f}%"
               f"（删除率 {100*(ja_asr.get('cer_deletion_avg') or 0):.2f}%）" if ja_asr else "文本口径 0；ASR 未完成")
    ko_cell = (f"文本口径 0；ASR(large-v3) WER {100*(ko_asr.get('wer_avg') or 0):.2f}%"
               f"（删除率 {100*(ko_asr.get('wer_deletion_avg') or 0):.2f}%）" if ko_asr else "文本口径 0；ASR 未完成")
    A(f"| M3 | 漏词核查 | {ja_cell} | {ko_cell} | ✅ 文本口径通过 |")
    A(f"| M4 | 切句质量与完整性 | 语料侧全部完整句（无超长/碎片）；服务侧标题段固定 1 个、"
      f"SRT 条目 = segments = {m5j['segments_total']:,}（无丢条目） |"
      f" 同左（SRT = segments = {m5k['segments_total']:,}） | ✅ |")
    A(f"| M5 | 字幕完整性（丢字幕） | 空字幕 {m5j['empty_segments_total']}｜SRT≠segments {m5j['tasks_srt_ne_segments']}"
      f"｜paraIndex 缺口判据**不可用**（恒为 0） | 空字幕 {m5k['empty_segments_total']}"
      f"｜SRT≠segments {m5k['tasks_srt_ne_segments']}｜同上 | ⚠️ 结构 OK，**音频空洞 "
      f"{a2j['files_long_gap_with_text'] + a2k['files_long_gap_with_text']} 个文件** |")
    A("")

    # ---------------- 四 ----------------
    A("## 四、文案一致性与字幕完整性明细")
    A("")
    for lang in ("ja", "ko"):
        d, m5, m1, p = D[lang], D[lang]["perf"]["m5"], D[lang]["perf"]["m1"], D[lang]["perf"]["perf"]
        A(f"### {d['cn']}")
        A("")
        A(f"- segments 合计 **{m5['segments_total']:,}**（标题段 {m5['title_segments_total']}｜正文段 "
          f"{m5['body_segments_total']:,}；单任务 {m5['segments_min']}~{m5['segments_max']}，平均 {m5['segments_avg']}）")
        A(f"- SRT 条目数与 segments **完全一致**（不一致任务 {m5['tasks_srt_ne_segments']} 个）"
          f"｜空字幕段 **{m5['empty_segments_total']}** 条")
        A(f"- ⚠️ distinct paraIndex 合计 = {m5['distinct_para_total']:,}，单任务恒为 1（全为 0）→ "
          f"「paraIndex 缺口」判据在本批**单段落语料**下无判别力，不构成丢句证据")
        A(f"- 文案一致性（主口径 {'词级' if m1['primary_unit'] == 'word' else '字级'}）："
          f"缺失 {m1['missing_primary_total']} / {m1['sent_primary_total']:,}"
          f"（{m1['missing_primary_ratio']*100:.4f}%）｜字级缺失 {m1['missing_chars_total']} / "
          f"{m1['sent_chars_total']:,}（{m1['missing_char_ratio']*100:.4f}%）｜多余 {m1['extra_chars_total']} 字")
        A(f"- 相似度：主口径平均 {m1['similarity_primary_avg']}（最低 {m1['similarity_primary_min']}）"
          f"｜字级平均 {m1['similarity_char_avg']}（最低 {m1['similarity_char_min']}）"
          f"｜逐字符完全一致 {m1['tasks_identical_chars']}/{p['ok']}")
        if m1["lossy_tasks"]:
            A("")
            A("| seq | 单元 | taskId | 词级缺失 | 字级缺失 | 相似度 | 缺失片段 |")
            A("|---|---|---|---:|---:|---:|---|")
            for t in m1["lossy_tasks"]:
                head = " ".join(str(x) for x in t["missing_head"])[:60]
                A(f"| {t['seq']} | {t['unit']} | {t['taskId']} | {t['missing_words']} | {t['missing_chars']} |"
                  f" {t['similarity']} | {head} |")
            A("")
            only_words = all(t["missing_chars"] == 0 for t in m1["lossy_tasks"])
            toks = "、".join(f"`{t['missing_head'][0]}`" for t in m1["lossy_tasks"] if t["missing_head"])
            A(f"> 上表任务的**字级缺失均为 0**，仅有词级 ±1 token 差异（缺失 token：{toks}）→ "
              f"均为**引号/空白等标点分词差异**，"
              f"{'**非文案丢失**。' if only_words else '需结合字级与人工复核判定。'}")
        A("")

    # ---------------- 五 ----------------
    A("## 五、音质（M2：客观指标 + 人工听测）")
    A("")
    A("**测量自证**：① 客观指标由 PyAV 解码计算，已用 **ffmpeg 独立解码**（转 float WAV）复核，"
      "峰值/RMS/削波样本数**完全一致**；② 所有结论排除「运行期半截文件」与「COS 错误响应被当成音频」"
      "两类伪阳性（本批 18 条 NoSuchKey 文件已重下合格音频后重新分析）。")
    A("")
    A("| 指标 | 日语 | 韩语 | 门槛 |")
    A("|---|---|---|---|")
    A(f"| 分析音频 | {a2j['analyzed']} 条（含事后补齐 {a2j['refetched_files']}） |"
      f" {a2k['analyzed']} 条（含补齐 {a2k['refetched_files']}） | 全量 |")
    A(f"| 峰值 min / max | **{a2j['peak_min']} / {a2j['peak_max']}** | **{a2k['peak_min']} / {a2k['peak_max']}** | ≤0.999 |")
    A(f"| 触顶(>0.999)文件 | **{a2j['files_peak_fail']}/{a2j['analyzed']}** | **{a2k['files_peak_fail']}/{a2k['analyzed']}** | 0 |")
    A(f"| 削波样本合计（单文件最多） | {a2j['clipped_total']:,}（{a2j['clipped_max']:,}） |"
      f" {a2k['clipped_total']:,}（{a2k['clipped_max']:,}） | 0 |")
    A(f"| ≥1.0 越界样本（文件数） | {a2j['ge_1_0_total']:,}（{a2j['files_with_ge_1_0']}） |"
      f" {a2k['ge_1_0_total']:,}（{a2k['files_with_ge_1_0']}） | 0 |")
    A(f"| RMS 平均（dBFS） | **{a2j['rms_avg']}**（{a2j['rms_min']}~{a2j['rms_max']}） |"
      f" **{a2k['rms_avg']}**（{a2k['rms_min']}~{a2k['rms_max']}） | 约 −20 dBFS；跨语种差 ≤3dB |")
    A(f"| 高频占比(≥8kHz) 平均 | {100*(a2j['hf_avg'] or 0):.2f}%（最大 {100*(a2j['hf_max'] or 0):.2f}%） |"
      f" {100*(a2k['hf_avg'] or 0):.2f}%（最大 {100*(a2k['hf_max'] or 0):.2f}%） | <10%（见说明） |")
    A(f"| 超长静音(>3s) 处数 | {a2j['long_gaps_total']}（{a2j['files_long_gap']} 文件） |"
      f" {a2k['long_gaps_total']}（{a2k['files_long_gap']} 文件） | 0 |")
    A(f"| **其中 metadata 有文本的空洞** | **{a2j['files_long_gap_with_text']} 文件** | **{a2k['files_long_gap_with_text']} 文件** | 0 |")
    A(f"| 最长空洞 | {a2j['gap_max_s']}s | {a2k['gap_max_s']}s | 0 |")
    A(f"| 音频 vs metadata 时长差 | 最大 {a2j['dur_delta_ms_max']} ms | 最大 {a2k['dur_delta_ms_max']} ms | <1000ms |")
    def brange(a):
        vals = [v for v in a["bit_rate_values"] if v]
        return f"{min(vals)}~{max(vals)}" if vals else "—"

    A(f"| 采样率 / 码率 | {a2j['sr_values']} / {brange(a2j)} bps | {a2k['sr_values']} / {brange(a2k)} bps | ≥16000Hz |")
    A("")
    diff = abs(a2j["rms_avg"] - a2k["rms_avg"])
    A(f"### 缺陷 1：削波 / 响度越界（两语种，日语更重）")
    A("")
    A(f"- 日语：**{a2j['files_peak_fail']}/{a2j['analyzed']}** 个文件解码峰值 >0.999（{a2j['peak_min']}~{a2j['peak_max']}，"
      f"最高 +1.8 dBFS），≥1.0 的样本 {a2j['ge_1_0_total']:,} 个，RMS 平均 {a2j['rms_avg']} dBFS。")
    A(f"- 韩语：{a2k['files_peak_fail']}/{a2k['analyzed']} 个文件峰值 >0.999（最高 {a2k['peak_max']}），"
      f"越界样本 {a2k['ge_1_0_total']:,} 个，RMS 平均 {a2k['rms_avg']} dBFS。")
    A(f"- 跨语种响度差 **{diff:.2f} dB**（超过 ≤3dB 门槛），日语明显偏响。")
    A("- 单发短文本探活（低并发、7.95s）已复现日语同类现象（峰值 1.0907、RMS −11.64 dBFS，"
      "ffmpeg 复核一致）→ **与并发无关**，属该语种/音色链路的输出特性。")
    A("- ⚠️ **判定边界说明**：MP3 解码对已限幅素材会产生少量**过冲**，故「解码峰值 >1」不能 100% 等同于"
      "「源 WAV 已削波」；但本批**全部**文件峰值 ≥1.11、且 RMS 高出正常水平约 8dB（日语），"
      "已足以判定**输出电平越界、存在可听破音风险**，结论为 M2 不通过；最终是否有可听破音需人工听测确认。")
    A("")
    A("### 缺陷 2：音频长空洞（metadata 有文本、音频近乎无声）")
    A("")
    A("| 语种 | seq | 空洞起点 | 时长 | 该区间 RMS | metadata 对应文本（截断） |")
    A("|---|---:|---:|---:|---:|---|")
    GAP_RMS = {("ja", 35): "−81.8 dBFS", ("ja", 54): "≈ −82 dBFS", ("ja", 83): "−66.3 dBFS",
               ("ko", 44): "−81.5 dBFS", ("ko", 48): "−81.7 dBFS"}
    for lang, arr in (("ja", a2j.get("gap_files", [])), ("ko", a2k.get("gap_files", []))):
        for g in arr:
            for det in g.get("gaps", []):
                A(f"| {D[lang]['cn']} | {g['seq']} | {det['start_s']}s | {det['dur_s']}s |"
                  f" {GAP_RMS.get((lang, g['seq']), '≈ −82 dBFS')} |"
                  f" {(det.get('meta_text_sample') or '')[:38]} |")
    A("")
    A("- 核查（`_diag_longgap_0924.py`）：这些文件**大小完整、时长与 metadata 差 26~58ms**，"
      "空洞区间 96.9%~99.5% 样本非零但幅度仅 ~9.7e-04（≈ −82 dBFS，日语 83 号约 −66 dBFS）→ "
      "**不是文件截断，也不是解码失败，而是音频本身在该时段近乎无声**。")
    A(f"- 最严重：日语 0035 号在 69.55s 起连续 {a2j['gap_max_s']}s 无声；韩语 0044 号在 435.45s 起连续 "
      f"{a2k['gap_max_s']}s 无声（该文件仅 523.96s，等于**结尾 88s 无内容**）。")
    A("- 影响：听众会听到长时间静默，而字幕/时间轴仍在推进 → 属**内容级缺陷**（音频口径），"
      "M1 文本口径完全查不出（本批 M1 = 0 缺失），正是技能强调「M1 与音频口径不可互相替代」的典型案例。")
    A("")
    A("**机制定位：疑似「固定时长静默占位段」**")
    A("")
    A("| 语种 | seq | 段起点 | 段时长 | 段内文本 | 语速(字/秒) | 是否恰为 81.64s |")
    A("|---|---:|---:|---:|---:|---:|---|")
    for lang in ("ja", "ko"):
        for r in (ph.get("langs", {}).get(lang, {}) or {}).get("rows", []):
            A(f"| {D[lang]['cn']} | {r['seq']} | {r['start_s']}s | {r['dur_s']}s | {r['text_len']} 字 |"
              f" {r['chars_per_s']} | {'✅' if r['is_placeholder_len'] else '—'} |")
    A("")
    A("- 关键证据：日语 0035 与韩语 0044 的异常段时长**完全相同 = 81.64s**，"
      "而两段的文本量差 64 倍（27 字 vs 1739 字，0.33 字/秒 vs 21.3 字/秒，均非正常语速）→ "
      "**与文本无关的固定时长**，判定为「合成失败后插入固定时长静默占位、但仍保留 metadata 文本」。")
    A("- 全量扫描（`_scan_placeholder_segments_0924.py`）：>60s 的超长段日语 1 个（任务 0035）、"
      "韩语 2 个（任务 0044、0085）；其中恰为 81.64s 的 2 个与音频无声区间一一对应。")
    A("")
    A("### 高频占比说明")
    A("")
    A(f"- 两语种全部文件 ≥8kHz 能量占比均 >10%（日语均值 {100*(a2j['hf_avg'] or 0):.2f}%、"
      f"韩语均值 {100*(a2k['hf_avg'] or 0):.2f}%）。"
      f"本次音频为 24kHz 采样，≥8kHz 已接近奈奎斯特频段，该阈值引用自 22.05kHz 历史样本，"
      f"在 24kHz 语音上偏敏感；**是否构成齿音/嘶嘶声必须由人工听测确认**，不以该数值单独定性。")
    A("")
    A("### 人工听测（TC-AUD-010）")
    A("")
    A("⚠️ **本次未完成人工听测**（技能规定必须由人执行）。已生成抽样清单（优先挑最长空洞/最高峰值/最高频文件）：")
    A("")
    for lang in ("ja", "ko"):
        A(f"- {D[lang]['cn']}：`{D[lang]['dir'].relative_to(ROOT)}\\analysis\\audio_listen_checklist.md`")
    A("")
    A("**M2 最终判定：❌ 不通过**（削波/响度越界 + 音频长空洞；人工听测未完成）")
    A("")

    # ---------------- 六 ----------------
    A("## 六、漏词核查（M3：文本口径 + ASR 口径 + 音频空洞）")
    A("")
    A("### 6.1 漏词率口径（务必先分清，三个口径不可互换）")
    A("")
    A("| 口径 | 比对对象 | 漏词率定义 | 能否判定漏文案 |")
    A("|---|---|---|---|")
    A("| **文本口径（M1，判定漏文案的唯一口径）** | 下发 `read_content` ↔ 返回 metadata 正文段拼接 | 缺失 token / 输入 token（`difflib` 对齐的 `delete`+`replace` 左侧） | ✅ **可以** |")
    A("| ASR 口径（M3，仅参考） | 音频 ASR 转写 ↔ 上述参考文本 | 删除 token / 参考 token（Deletion/N） | ⚠️ 不可以（含 ASR 识别误差） |")
    A("| 音频口径（能量/空洞，M2/M5） | 音频波形 ↔ metadata 文本时间轴 | 无声时段内本应有的文本量（定性） | ✅ 可发现「文本齐全但没念」 |")
    A("")
    A("### 6.2 文本口径（M1）：漏词率 0.0000%")
    A("")
    A("| 语种 | 主口径 | 缺失 token | 发送 token | **漏词率** | 多余 token | 逐字符完全一致任务 |")
    A("|---|---|---:|---:|---:|---:|---:|")
    A(f"| 日语 | 字级 | {m1j['missing_chars_total']} | {m1j['sent_chars_total']:,} |"
      f" **{m1j['missing_char_ratio']*100:.4f}%** | {m1j['extra_chars_total']} |"
      f" {m1j['tasks_identical_chars']}/{pj['ok']} |")
    A(f"| 韩语 | 词级（字级交叉验证） | {m1k['missing_primary_total']} | {m1k['sent_primary_total']:,} |"
      f" **{m1k['missing_primary_ratio']*100:.4f}%** | {m1k['extra_primary_total']} |"
      f" {m1k['tasks_identical_chars']}/{pk['ok']} |")
    A(f"| 韩语（字级交叉） | 字级 | {m1k['missing_chars_total']} | {m1k['sent_chars_total']:,} |"
      f" **{m1k['missing_char_ratio']*100:.4f}%** | {m1k['extra_chars_total']} | 同上 |")
    A("")
    A(f"→ **结论：无漏词/漏句。** 韩语那 {m1k['missing_primary_total']} 个词级差异同任务字级缺失为 0，"
      f"为引号归属造成的分词边界差异（`'어째서`/`'곧`/`'한지훈은`），非内容丢失；"
      f"日语必须按字级判定（无词间空格，词级分词无意义）。逐任务明细见 M1 专项报告与 `m1_per_task.csv`。")
    A("")
    if asr.get("langs"):
        A(f"### 6.3 ASR 口径（仅参考）：large-v3 逐样本明细")
        A("")
        A(f"- 模型：faster-whisper **large-v3**（device=cpu，compute_type=int8，加载 {asr.get('load_s')}s）；"
          f"每语种抽 {asr.get('samples_per_lang')} 条，转写音频**前 {asr.get('window_s')} 秒**；"
          f"参考文本只取**完整落在窗口内**的 metadata 正文段。")
        A("")
        A("| 语种 | seq | 音频窗口 | 音频(s) | 转写(s) | RTF | 参考字符 | ASR字符 | 替换 | 删除（漏词） | 插入 | **删除率** | CER | 相似度 |")
        A("|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for lk in ("ja", "ko"):
            a = asr["langs"].get(lk)
            if not a:
                continue
            for r in a.get("rows", []):
                A(f"| {D[lk]['cn']} | {r['seq']} | {r['ref_window']} | {r['audio_s']} | {r['wall_s']} |"
                  f" {r['rtf']} | {r['ref_chars']} | {r['hyp_chars']} | {100*r['cer_substitution']:.2f}% |"
                  f" {100*r['cer_deletion']:.2f}% | {100*r['cer_insertion']:.2f}% |"
                  f" **{100*r['cer_deletion']:.2f}%** | {100*r['cer']:.2f}% | {r['cer_similarity']} |")
        A("")
        A("| 语种 | 样本 | CER(字级) 平均 | 删除率 平均（=ASR 口径漏词率） | 最差 CER | WER(词级) 平均 | WER 删除率 | 平均 RTF |")
        A("|---|---:|---:|---:|---:|---:|---:|---:|")
        if ja_asr:
            A(f"| 日语 | {ja_asr['samples']} | {100*(ja_asr.get('cer_avg') or 0):.2f}% |"
              f" **{100*(ja_asr.get('cer_deletion_avg') or 0):.2f}%** | {100*(ja_asr.get('cer_worst') or 0):.2f}% |"
              f" {100*(ja_asr.get('wer_avg') or 0):.2f}%（词级无意义） | — | {ja_asr.get('rtf_avg')} |")
        if ko_asr:
            A(f"| 韩语 | {ko_asr['samples']} | {100*(ko_asr.get('cer_avg') or 0):.2f}% |"
              f" {100*(ko_asr.get('cer_deletion_avg') or 0):.2f}% | {100*(ko_asr.get('cer_worst') or 0):.2f}% |"
              f" {100*(ko_asr.get('wer_avg') or 0):.2f}% | **{100*(ko_asr.get('wer_deletion_avg') or 0):.2f}%** |"
              f" {ko_asr.get('rtf_avg')} |")
        A("")
        A("> ASR 口径含识别误差（同音字/假名汉字写法/数字读法差异都会计入替换），"
          "**不得**据此判定 TTS 漏词：历史教训是西语用 base 模型测出 30.81% WER，人工复核后基本为 ASR 误差。")
        A("> 本次日语 CER 偏高主要来自汉字/假名写法与标点差异，**删除率仅 "
          f"{100*(ja_asr.get('cer_deletion_avg') or 0):.2f}%**，且不存在成段删除。")
        A("")
        A("### 6.4 定点核查（静默占位段 vs 相邻正常段）")
        A("")
        A("| 检查项 | 参考字符 | 音频窗口 | ASR 输出字符 | CER | 删除率 |")
        A("|---|---:|---|---:|---:|---:|")
        for label, res, lk in (("日语 0035 占位段（69.48~151.12s）", gap_ja, "ja"),
                               ("日语 0035 相邻正常段（151.52~160.72s）", gap_ja_ctrl, "ja"),
                               ("韩语 0044 占位段（435.91~517.55s）", gap_ko, "ko")):
            rows = ((res.get("langs", {}) or {}).get(lk) or {}).get("rows", [])
            if not rows:
                A(f"| {label} | — | — | — | — | — |")
                continue
            r = rows[0]
            A(f"| {label} | {r['ref_chars']} | {r['ref_window']} | {r['hyp_chars']} |"
              f" {r['cer']*100:.2f}% | {r['cer_deletion']*100:.2f}% |")
        A("")
        A("> 判读：**占位段的参考文本有内容、ASR 却输出与参考毫不相干的内容**（韩语 0044：1218 字参考"
          "只识别出 13 字，删除率 96.2%；日语 0035：模型输出 `ご視聴ありがとうございました "
          "ご視聴ありがとうございました ローラ` —— 这是 large-v3 在**纯静音**上的典型幻觉短语），"
          "而**相邻正常段**识别正常（相似度 0.83）→ 从音频口径**独立证实该时段没有语音**，"
          "与 M2 的能量分析（−81.8 dBFS）和段时长分析（固定 81.64s）三方互证。")
        A("> ⚠️ 口径修正：ASR 参考文本只取**完整落在窗口内**的 metadata 段。"
          "首轮曾用「与窗口有重叠」的段做参考，跨窗口的超长段会把窗口外整段文本计入，"
          "凭空造成约 50% 的假删除（韩语 0087 号）—— 已修正并重跑。")
    else:
        A("- ⚠️ ASR 复核未完成。")
    A("")
    A("### 6.5 漏词核查结论（三个口径合起来看）")
    A("")
    gap_files = a2j["files_long_gap_with_text"] + a2k["files_long_gap_with_text"]
    A("| # | 结论 | 依据 |")
    A("|---|---|---|")
    A(f"| 1 | **文本口径漏词率 = 0.0000%（无漏词/漏句）** | 日语字级 0/{m1j['sent_chars_total']:,}、"
      f"韩语词级 {m1k['missing_primary_ratio']*100:.4f}%、字级 0/{m1k['sent_chars_total']:,}；"
      f"逐字符完全一致 {m1j['tasks_identical_chars']}/{pj['ok']}、{m1k['tasks_identical_chars']}/{pk['ok']} |")
    A(f"| 2 | ASR 口径删除率（漏词率）非 0，但**不作缺陷判定** | 日语平均删除率 "
      f"{100*((ja_asr or {}).get('cer_deletion_avg') or 0):.2f}%、韩语 WER 删除率 "
      f"{100*((ko_asr or {}).get('wer_deletion_avg') or 0):.2f}%（样本 {asr.get('samples_per_lang')} 条/语种） |"
      if asr.get("langs") else "| 2 | ASR 口径未执行 | — |")
    A(f"| 3 | **音频口径存在真实漏读**：{gap_files} 个文件在 metadata 有文本的时段近乎无声 | "
      f"能量 ≈ −82 dBFS；韩语 0044 该窗口参考 1218 字、ASR 仅识别 13 字（**实际漏读率 96.2%**）；"
      f"日语 0035 该窗口模型仅输出静音幻觉短语 |")
    A("| 4 | 未发现串任务 | 字级多余内容 = 0 |")
    A("")
    A("> **一句话**：文本口径（输入 ↔ 输出 JSON）**无漏词**；但音频口径在 5 个文件上出现"
      "**成段漏读/静默**，属内容级缺陷 —— 两个口径必须并列呈现，缺一不可。")
    A("")

    # ---------------- 七 ----------------
    A("## 七、性能数据")
    A("")
    A("| 指标 | 日语 | 韩语 |")
    A("|---|---:|---:|")
    A(f"| 并发 | {pj['workers']} | {pk['workers']} |")
    A(f"| 加载窗口 | 30 分钟 | 30 分钟 |")
    A(f"| 含收尾 drain 的实际墙钟（s） | {pj['wall_seconds']} | {pk['wall_seconds']} |")
    A(f"| 总任务 / 成功 / 失败 | {pj['total_tasks']} / {pj['ok']} / {pj['failed']} |"
      f" {pk['total_tasks']} / {pk['ok']} / {pk['failed']} |")
    A(f"| 成功率 | {pj['success_rate']:.2%} | {pk['success_rate']:.2%} |")
    A(f"| 吞吐（加载期口径） | **{pj['throughput_loadphase_per_min']} 任务/分钟**（{pj['throughput_loadphase_per_hour']}/h）"
      f" | **{pk['throughput_loadphase_per_min']} 任务/分钟**（{pk['throughput_loadphase_per_hour']}/h） |")
    A(f"| 吞吐（全墙钟口径，含 drain） | {pj['throughput_per_min']} 任务/分钟 | {pk['throughput_per_min']} 任务/分钟 |")
    A(f"| 端到端 平均（s） | {pj['elapsed_avg']} | {pk['elapsed_avg']} |")
    A(f"| 端到端 P50 / P90（s） | {pj['elapsed_p50']} / {pj['elapsed_p90']} | {pk['elapsed_p50']} / {pk['elapsed_p90']} |")
    A(f"| 端到端 P95 / P99（s） | {pj['elapsed_p95']} / {pj['elapsed_p99']} | {pk['elapsed_p95']} / {pk['elapsed_p99']} |")
    A(f"| 端到端 最小 / 最大（s） | {pj['elapsed_min']} / {pj['elapsed_max']} | {pk['elapsed_min']} / {pk['elapsed_max']} |")
    A(f"| 创建接口 平均 / 最大（s） | {pj['create_avg']} / {pj['create_max']} | {pk['create_avg']} / {pk['create_max']} |")
    A(f"| 音频产物合计（MB，留证） | {pj['audio_bytes_total']/1048576:.1f} | {pk['audio_bytes_total']/1048576:.1f} |")
    A(f"| 使用语料单元数 | {pj['distinct_units_used']} | {pk['distinct_units_used']} |")
    A("")
    A("**并发效应（关键性能结论）**")
    A("")
    A(f"- 同批 ~5000 字符语料：**2 并发**烟测单任务 76~86s；**10 并发**时日语 P50 {pj['elapsed_p50']}s /"
      f" 平均 {pj['elapsed_avg']}s，韩语 P50 {pk['elapsed_p50']}s / 平均 {pk['elapsed_avg']}s。")
    A(f"- 延迟未随并发线性上升：日语前 10 个任务（同批首发）端到端 217~232s，随后回落到 45~200s，"
      f"P50 稳定在 {pj['elapsed_p50']}s 附近 → 首轮存在预热/排队，之后进入稳态。")
    A(f"- 吞吐：日语 {pj['throughput_loadphase_per_min']} 任务/分钟、韩语 {pk['throughput_loadphase_per_min']} 任务/分钟；"
      f"每任务约 5000 字符 ≈ 12 分钟音频，折合音频产出约 "
      f"{pj['throughput_loadphase_per_min']*12:.0f} / {pk['throughput_loadphase_per_min']*12:.0f} 分钟音频/分钟（远高于实时）。")
    A(f"- 创建接口本身很快（平均 {pj['create_avg']}s、最大 {max(pj['create_max'], pk['create_max'])}s），"
      f"排队发生在合成阶段而非建任务阶段。")
    A(f"- 韩语全墙钟口径吞吐（{pk['throughput_per_min']}/分钟）被 **1 个卡死任务**拖低：该任务 "
      f"status=67 持续 1940s 未完成，导致收尾 drain 长达 {pk['wall_seconds']-1800:.0f}s。")
    A("")
    A("**分时段趋势（每 5 分钟）**")
    A("")
    for lang in ("ja", "ko"):
        t = D[lang]["perf"]["perf"]["trend"]
        if t:
            A(f"- {D[lang]['cn']}：" + "；".join(
                f"{x['window']} {x['tasks']}任务/均{x['elapsed_avg']}s/缺失{x['missing_chars']}字" for x in t))
    A("")

    # ---------------- 八 ----------------
    A("## 八、本次测试项声明")
    A("")
    A("| 项 | 执行 | 说明 |")
    A("|---|---|---|")
    A("| 高并发性能压测（10 并发 × 30 分钟） | ✅ | 日语、韩语各一轮，串行执行 |")
    A("| M1 文案一致性 | ✅ | 高并发口径（10 并发）；低并发口径仅 2 任务烟测 |")
    A("| M2 客观音质 | ✅ | 全量音频；发现削波与音频长空洞 |")
    A("| M2 人工听测 | ❌ 未执行 | 需人工试听，已生成待填清单 |")
    A("| M3 漏词核查 | ✅ | 文本口径全量；ASR 抽样 + 空洞窗口定点核查（CPU-only large-v3 int8） |")
    A("| M4 切句质量 | ✅ | 语料侧自检 + 服务侧段数关系；未做 pysbd/pyset/API 三方案对照 |")
    A("| M5 字幕完整性 | ⚠️ 部分 | segments/SRT/空字幕可判；**paraIndex 判据在单段落语料下不可用** |")
    A("| 产物可获取性专项 | ✅ | 额外核查 audio_url 立即可用性（发现 NoSuchKey 竞态） |")
    A("| 16 并发阶梯 / 槽位泄漏 / 24h 浸泡 | ❌ | 用户本次只要求 10 并发 30 分钟；第二代缺 TC-PERF-005~009 脚本 |")
    A("| 其它语种 | ❌ | 用户明确只做日语、韩语 |")
    A("")

    # ---------------- 九 ----------------
    A("## 九、缺陷与建议")
    A("")
    A("| # | 级别 | 类型 | 现象与证据 | 建议 |")
    A("|---|---|---|---|---|")
    A(f"| 1 | **P1** | 音频内容丢失（固定时长静默占位） | {a2j['files_long_gap_with_text']} 个日语 + "
      f"{a2k['files_long_gap_with_text']} 个韩语文件存在 metadata 有文本、音频近乎无声的长空洞"
      f"（最长 {max(a2j['gap_max_s'], a2k['gap_max_s'])}s）；其中日语 0035 与韩语 0044 的异常段时长"
      f"**完全相同 = 81.64s** 而文本量差 64 倍（ASR 在静音处输出幻觉短语，能量仅 −81.8 dBFS） | "
      f"服务端排查分段合成「片段失败/超时后插入固定时长静默占位但保留 metadata 文本」的路径，"
      f"补「音频有效能量 + 段时长/文本量比值」校验，失败片段应重试或显式报错 |")
    A(f"| 2 | **P1** | 产物可获取性竞态 | {a2j['refetched_files']} 个日语 + {a2k['refetched_files']} 个韩语任务"
      f"（合计 18/{pj['total_tasks'] + pk['total_tasks']} ≈ "
      f"{100*18/(pj['total_tasks']+pk['total_tasks']):.1f}%）在任务完成后**立即**下载 audio_url 返回 "
      f"COS `NoSuchKey`（440B XML），事后重下**全部成功** | 任务置为成功前确保 COS 对象可读"
      f"（或返回前做一次 HEAD 校验） |")
    A(f"| 3 | **P1** | 音质越界 | 日语 {a2j['files_peak_fail']}/{a2j['analyzed']} 文件峰值 >0.999"
      f"（最高 {a2j['peak_max']}）、RMS {a2j['rms_avg']} dBFS；韩语 {a2k['files_peak_fail']}/{a2k['analyzed']}"
      f"（最高 {a2k['peak_max']}） | 输出前做**响度归一/真峰值限幅**（目标 ≤0.999、RMS 约 −20 dBFS），逐语种复测 |")
    A(f"| 4 | **P2** | 任务卡死 | 韩语 seq102（taskId=30002769）status=67 持续 **1940s** 未完成，"
      f"最终判超时；成功率因此 {pk['success_rate']:.2%} | 排查长时间停留在处理中的任务是否有槽位/重试泄漏 |")
    A("| 5 | P3 | 网络/环境 | 6 个任务（日 4 / 韩 2）下载 COS 时发生 ConnectionReset / RemoteDisconnected / ConnectTimeout，"
      "重试后全部成功 | 客户端对 COS 下载加重试（本次脚本已具备补齐手段） |")
    A("| 6 | P3 | 跨语种一致性 | 日语与韩语响度差 "
      f"{diff:.2f} dB（>3dB 门槛） | 统一各语种音色响度基准 |")
    A("| 7 | P3 | 测试方法学 | 「最长静音 >300ms」在本批朗读语料中 100% 命中，与 TC-VT-004「段落停顿 >800ms 属正常」"
      "自相矛盾；`paraIndex` 在单段落长文本下恒为 0 | 技能侧修订判据：静音判据改为「>3s 且 metadata 有文本」；"
      "长文本改用段数/SRT/字级缺失口径 |")
    A("")
    A(f"**确认无问题的方面**：任务成功率（日语 100%、韩语 {pk['success_rate']:.2%}，唯一失败为上述卡死任务）、"
      f"**M1 文案零缺失**（日语 94/94、韩语逐字符完全一致）、空字幕 0、SRT 与 segments 完全一致、"
      f"音频时长与 metadata 对齐（最大差 {max(a2j['dur_delta_ms_max'], a2k['dur_delta_ms_max'])}ms）。")
    A("")
    A("⚠️ **工程与安全提醒**：`docs/听书测试物料/` 未纳入 git；新增脚本沿用既有方式在脚本内使用 `SECRET_KEY`"
      "（未新增密钥，对外分享前必须脱敏）；本次**未向生产环境**下发任何任务。")
    A("")

    # ---------------- 十 ----------------
    A("## 十、附件索引")
    A("")
    A("| 内容 | 路径（相对仓库根） |")
    A("|---|---|")
    for lang in ("ja", "ko"):
        rel = D[lang]["dir"].relative_to(ROOT)
        A(f"| {D[lang]['cn']} 留证（src / meta / srt / audio / tasks.jsonl / summary.json / progress.log） | `{rel}\\` |")
        A(f"| {D[lang]['cn']} 语料（units.jsonl + manifest.json） | `{rel}\\material\\` |")
        A(f"| {D[lang]['cn']} 性能 + M1 + M5 分析 | `{rel}\\analysis\\perf_m1_m5.json` |")
        A(f"| {D[lang]['cn']} 客观音质指标 | `{rel}\\analysis\\audio_m2.json` |")
        A(f"| {D[lang]['cn']} 人工听测待填表 | `{rel}\\analysis\\audio_listen_checklist.md` |")
    A("| ASR M3 抽样结果 | `docs\\听书测试物料\\mp3\\analysis_ja_ko_asr_m3\\asr_m3.json` |")
    A("| ASR 空洞定点核查 | `...\\analysis_ja_ko_asr_m3\\asr_gapcheck*.json` |")
    A("| **M1 文案一致性专项报告（含 224 任务逐条明细）** | "
      "`docs\\听书测试物料\\测试报告\\文案一致性专项_M1_日韩_20260924.md` |")
    A("| M1 逐任务明细 CSV | `docs\\听书测试物料\\mp3\\analysis_ja_ko_m1_per_task.csv` |")
    A("| 探活留证（日/韩短文本真实下发） | `docs\\听书测试物料\\mp3\\Higgs_日韩_探活_0924\\` |")
    A("| 脚本 | `build_ja_ko_5000char_material.py`、`run_higgs_ja_ko_10concurrent_30min.py`、"
      "`analyze_ja_ko_perf_0924.py`、`audio_quality_ja_ko_0924.py`、`asr_accuracy_ja_ko_largev3_0924.py`、"
      "`_diag_*.py`（自证脚本）、`gen_report_ja_ko_0924.py` |")
    A("| 本次迭代快照 | `backups/iterations/20260924-111127-ja-ko-10concurrent-30min` |")
    A("")

    # ---------------- 十一 ----------------
    A("## 十一、数据范围与测量口径修订")
    A("")
    A(f"- 结论**仅来自本次两个批次**（{DATE}，日语 {pj['total_tasks']} 个任务、韩语 {pk['total_tasks']} 个任务），"
      f"未引用其它时段/语种/模型数据；环境为测试环境（dev）。")
    A("- 语料为 ~5000 字符**单段落**完整句；**不代表**短文本、多段落或 8000+ 字符整章场景的结论。")
    A("- 本次共纠正 3 处测量口径（初稿 → 终稿）：")
    A("  1. **COS NoSuchKey**：初判「音频缺失」，实测重新按 taskId 拉取后 18/18 全部下载成功 → 改判**可见性竞态**；")
    A("  2. **paraIndex 缺口**：初判「无缺口 = 无丢句」，实测单段落语料下 paraIndex 恒为 0 → 该判据**不成立**，"
      "改用字级缺失 + segments/SRT 一致性 + 音频空洞检测；")
    A("  3. **异常静音阈值**：初稿按「>300ms 即异常」会把 100% 文件判异常 → 改为「>3s 且 metadata 有文本」，"
      "并单独列出 5 个真实空洞文件。")
    A("")
    A("## 十二、与历史报告的关系")
    A("")
    A("| 对比项 | 历史基线 | 本次 |")
    A("|---|---|---|")
    A("| 并发 / 语种 | 5 并发 / 六语种（英德法西葡俄） | 10 并发 / 日语、韩语（新增语种覆盖） |")
    A("| 单任务文本 | 500 词（英语） | ~5000 字符完整句（日/韩） |")
    A(f"| 文案缺失 | 服务异常恢复后首跑：英 8.06% / 德 10.16% / 俄 7.63%（间歇） | 日语 0.0000% / 韩语 0.0000%（未复现） |")
    A(f"| 音质 | IndexTTS-2.5 西语：峰值触顶 1.000、RMS −13.5 dBFS（判异常） | Higgs 日语：峰值最高 {a2j['peak_max']}、"
      f"RMS {a2j['rms_avg']} dBFS；韩语次之（同类问题、不同语种/模型） |")
    A("| 新增发现 | — | audio_url 可见性竞态（18 条）、任务卡死 32 分钟、音频长空洞（5 文件） |")
    A("")
    A("> 与历史结论**不冲突**：本次同样验证「正常状态下文案完整」，未触发间歇性丢文案；"
      "音质方面复现并扩展了「特定语种/音色链路输出电平越界」这一类问题，并新发现音频长空洞与产物可见性竞态。")
    A("")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / f"Higgs_日韩_10并发30分钟_{DATE.replace('-', '')}.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"[OK] 报告已生成: {out}")
    print(f"     行数 {len(L)}｜字符 {sum(len(x) for x in L):,}")


if __name__ == "__main__":
    main()
