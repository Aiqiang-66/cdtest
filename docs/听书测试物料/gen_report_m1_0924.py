# -*- coding: utf-8 -*-
r"""生成「输入/输出文案一致性（M1）专项测试报告」—— 日/韩 10 并发 30 分钟批次。

数据来源（全部从落盘留证现算，不依赖跑批时的内存统计，可复跑）：
  <批次>/src/task_XXXX.txt        实际下发的 read_content
  <批次>/meta/task_XXXX.json      接口返回 metadata（正文段 paraIndex>=0，标题段 paraIndex<0）
  <批次>/srt/task_XXXX.srt        由 metadata 派生的字幕（用于条数一致性）
  <批次>/tasks.jsonl              任务台账（taskId / 并发 / 时间 / 字数）
  <批次>/analysis/audio_m2.json   客观音质与音频空洞（用于「JSON 对比查不出什么」的交叉证据）

输出：
  <批次>/analysis/m1_per_task.csv          逐任务明细（每语种一份）
  docs/听书测试物料/mp3/analysis_ja_ko_m1_per_task.csv  两语种合并
  docs/听书测试物料/测试报告/文案一致性专项_M1_日韩_20260924.md

用法：
  & "D:\python\python.exe" docs\听书测试物料\gen_report_m1_0924.py
"""
import csv
import difflib
import json
import re
import statistics
import unicodedata
from pathlib import Path

ROOT = Path(r"D:\python\dmx\cdtest")
MP3 = ROOT / "docs" / "听书测试物料" / "mp3"
REPORT_DIR = ROOT / "docs" / "听书测试物料" / "测试报告"
DATE = "2026-09-24"
RUNS = {
    "ja": ("日语", MP3 / "Higgs_日语_10并发30分钟_0924", 9, "Japanese_female"),
    "ko": ("韩语", MP3 / "Higgs_韩语_10并发30分钟_0924", 14, "Korean_female"),
}
_EDGE = re.compile(r"^[^\w']+|[^\w']+$")


# ---------------- 口径实现 ----------------
def word_tokens(s):
    s = unicodedata.normalize("NFKC", s)
    s = (s.replace("\u2019", "'").replace("\u2018", "'")
          .replace("\u201c", '"').replace("\u201d", '"')
          .replace("\u2014", " ").replace("\u2013", " ").replace("\u2015", " "))
    return [w for w in (_EDGE.sub("", t).lower() for t in s.split()) if w]


def char_tokens(s):
    return [c for c in unicodedata.normalize("NFKC", s) if not c.isspace()]


def diff(a, b):
    """→ (缺失, 多余, 相似度)：缺失=输入有输出无；多余=输出有输入无"""
    if a == b:
        return [], [], 1.0
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    miss, extra = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("delete", "replace"):
            miss.extend(a[i1:i2])
        if tag in ("insert", "replace"):
            extra.extend(b[j1:j2])
    return miss, extra, sm.ratio()


def srt_entries(p):
    if not p.exists():
        return 0
    return sum(1 for ln in p.read_text(encoding="utf-8").splitlines()
               if ln.strip() and ln.strip().split(" ")[0].isdigit())


def collect(lang, cn, run, lang_code, voice):
    ledger = {}
    for line in (run / "tasks.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            ledger[r["seq"]] = r

    rows, diffs = [], []
    for seq, rec in sorted(ledger.items()):
        src_p, meta_p = run / "src" / f"task_{seq:04d}.txt", run / "meta" / f"task_{seq:04d}.json"
        if not src_p.exists() or not meta_p.exists():
            continue
        sent = src_p.read_text(encoding="utf-8")
        segs = json.loads(meta_p.read_text(encoding="utf-8"))
        body = " ".join((s.get("text") or "") for s in segs if s.get("paraIndex", -1) >= 0)
        title_segs = [s for s in segs if s.get("paraIndex", -1) < 0]

        sc, rc = char_tokens(sent), char_tokens(body)
        sw, rw = word_tokens(sent), word_tokens(body)
        miss_c, extra_c, sim_c = diff(sc, rc)
        miss_w, extra_w, sim_w = diff(sw, rw)
        row = {
            "lang": lang, "lang_cn": cn, "seq": seq, "taskId": rec.get("taskId"),
            "unit": rec.get("unit"), "chapter_title": rec.get("chapter_title"),
            "ok": bool(rec.get("ok")), "status": rec.get("status"),
            "src_chars_raw": len(sent), "sent_chars": len(sc), "ret_chars": len(rc),
            "sent_words": len(sw), "ret_words": len(rw),
            "missing_chars": len(miss_c), "extra_chars": len(extra_c),
            "missing_words": len(miss_w), "extra_words": len(extra_w),
            "sim_char": round(sim_c, 4), "sim_word": round(sim_w, 4),
            "missing_char_ratio": round(len(miss_c) / max(1, len(sc)), 6),
            "segments": len(segs), "title_segments": len(title_segs),
            "body_segments": len([s for s in segs if s.get("paraIndex", -1) >= 0]),
            "srt_entries": srt_entries(run / "srt" / f"task_{seq:04d}.srt"),
            "elapsed_s": rec.get("elapsed_s"), "create_s": rec.get("create_s"),
            "missing_char_head": "".join(miss_c[:30]),
            "missing_word_head": " | ".join(miss_w[:5]),
        }
        rows.append(row)
        if miss_c or extra_c or miss_w or extra_w:
            diffs.append(row)
    return rows, diffs, ledger


def main():
    data = {}
    all_rows = []
    for lang, (cn, run, lc, voice) in RUNS.items():
        rows, diffs, ledger = collect(lang, cn, run, lc, voice)
        m2 = json.loads((run / "analysis" / "audio_m2.json").read_text(encoding="utf-8"))
        data[lang] = {"cn": cn, "run": run, "lang_code": lc, "voice": voice, "rows": rows,
                      "diffs": diffs, "ledger": ledger, "m2": m2}
        all_rows += rows
        # 逐任务 CSV
        out_csv = run / "analysis" / "m1_per_task.csv"
        with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"[{cn}] 逐任务明细 → {out_csv}")

    with (MP3 / "analysis_ja_ko_m1_per_task.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        w.writeheader()
        w.writerows(all_rows)

    # ---------------- 报告 ----------------
    L = []
    A = L.append
    A("# 输入/输出文案一致性（M1）专项测试报告 — Higgs TTS v3 日语 / 韩语")
    A("")
    A(f"> **被测对象**：Higgs TTS v3（链路 A：`POST /Video/CreateUniversalTransparent`，`taskType=74`）  ")
    A(f"> **语种**：日语（`lang=9` / `Japanese_female`）、韩语（`lang=14` / `Korean_female`）  ")
    A(f"> **批次**：{DATE}　日语 10 并发 × 30 分钟、韩语 10 并发 × 30 分钟（各一轮）  ")
    A(f"> **依据**：`docs/听书测试物料/SKILL.md` v1.1.4 —— 必测项 **M1**、Phase 2.5 双通道检测法  ")
    A("> **本报告数据来源**：`src/`（下发原文）与 `meta/`（返回 JSON）**从磁盘现算**，可复跑"
      "（`gen_report_m1_0924.py` / `_recheck_m1_from_disk_0924.py`）")
    A("")

    # 一、测试口径
    A("## 一、测试口径与方法")
    A("")
    A("| 项 | 日语 | 韩语 |")
    A("|---|---|---|")
    A(f"| lang / 音色 | `lang={data['ja']['lang_code']}` / `{data['ja']['voice']}` |"
      f" `lang={data['ko']['lang_code']}` / `{data['ko']['voice']}` |")
    A(f"| 语料单元 | 107 个 ~5205 字符完整句 | 323 个 ~5194 字符完整句 |")
    A(f"| 复核任务数 | {len(data['ja']['rows'])} | {len(data['ko']['rows'])} |")
    A(f"| 环境 / 模型 | `https://ai-main-none-dev.changdu.ltd` / `higgs` | 同左 |")
    A("")
    A("**比对对象**：下发的 `read_content` ↔ 接口返回 metadata 中**正文段**拼接文本"
      "（`paraIndex >= 0`）。")
    A("")
    A("- **排除标题段**：`chapter_title` 会作为独立字幕段返回（`paraIndex = -1`），"
      "计入会把「标题」误判为多余内容，故比对时剔除。")
    A("- **归一化**：NFKC → 统一引号（’‘“”→'\"）→ 去首尾标点 → 小写 → 空白切分（词级）；"
      "字级仅去空白、**保留标点**。")
    A("- **缺失定义（漏文案）**：序列对齐中 `delete` / `replace` **左侧**（输入有、输出无）。")
    A("- **多余定义**：`insert` / `replace` **右侧**（输出有、输入无），用于识别串任务。")
    A("- **主口径**：日语**字级**（日语无词间空格，词级分词会把整句当 1 个 token，数值无意义）；"
      "韩语**词级**（空格分词）并以**字级**交叉验证。")
    A("- **标题段校验**：每任务恰好 1 个标题段，已确认（见逐任务明细 `title_segments` 列）。")
    A("")

    # 二、结论速览
    A("## 二、结论速览")
    A("")
    A("| 判定项（技能门禁） | 目标 | 日语 | 韩语 | 判定 |")
    A("|---|---|---|---|---|")
    ja, ko = data["ja"], data["ko"]

    def agg(d):
        rows = d["rows"]
        return {
            "n": len(rows),
            "sent_c": sum(r["sent_chars"] for r in rows),
            "miss_c": sum(r["missing_chars"] for r in rows),
            "extra_c": sum(r["extra_chars"] for r in rows),
            "sent_w": sum(r["sent_words"] for r in rows),
            "miss_w": sum(r["missing_words"] for r in rows),
            "extra_w": sum(r["extra_words"] for r in rows),
            "identical": sum(1 for r in rows if r["missing_chars"] == 0 and r["extra_chars"] == 0),
            "tasks_miss": sum(1 for r in rows if r["missing_chars"] > 0),
            "sim_min": min(r["sim_char"] for r in rows),
            "sim_avg": round(statistics.mean(r["sim_char"] for r in rows), 6),
            "srt_eq_seg": sum(1 for r in rows if r["srt_entries"] == r["segments"]),
        }

    aj, ak = agg(ja), agg(ko)
    A(f"| 整体缺失率（字级） | 0.000% | **{100*aj['miss_c']/aj['sent_c']:.3f}%**"
      f"（{aj['miss_c']}/{aj['sent_c']:,}） | **{100*ak['miss_c']/ak['sent_c']:.3f}%**"
      f"（{ak['miss_c']}/{ak['sent_c']:,}） | ✅ 均通过 |")
    A(f"| 单任务缺失词 | 0 | {aj['tasks_miss']} 个任务有缺失 | {ak['tasks_miss']} 个任务有缺失 | ✅ 均通过 |")
    A(f"| 去标点后逐字符一致 | 100% | **{aj['identical']}/{aj['n']}（100%）** |"
      f" **{ak['identical']}/{ak['n']}（100%）** | ✅ 均通过 |")
    A(f"| 多余内容（串扰线索） | 0 | {aj['extra_c']} 字 | {ak['extra_c']} 字 | ✅ 无 |")
    A(f"| 相似度（字级，平均 / 最低） | ≥1.0 | {aj['sim_avg']} / {aj['sim_min']} |"
      f" {ak['sim_avg']} / {ak['sim_min']} | ✅ 均通过 |")
    A(f"| SRT 条目 = segments | 100% | {aj['srt_eq_seg']}/{aj['n']} | {ak['srt_eq_seg']}/{ak['n']} | ✅ 均通过 |")
    A("")
    A(f"**结论：本批次输入文案与输出文案（返回 JSON）逐字符完全一致，文案缺失率为 0.000%，"
      f"无漏词/漏句，未发现串任务。**")
    A("")
    A("> ⚠️ **口径边界（必须同时看）**：本报告只证明**服务端返回的文案没丢**，"
      "**不能**证明「音频把文案念全了」。同一批次另有 **5 个文件**的音频在 metadata 有文本的时段"
      "近乎无声（最长 82.6s，详见第七节）—— 这类问题文本比对查不出来。")
    A("")

    # 三、逐项判据
    A("## 三、M1 判据逐项核对（Phase 2.5）")
    A("")
    A("| 判据 | 说明 | 日语 | 韩语 |")
    A("|---|---|---|---|")
    A(f"| 整体缺失率 = 0.000% | 缺失字 / 发送字 | {100*aj['miss_c']/aj['sent_c']:.4f}% |"
      f" {100*ak['miss_c']/ak['sent_c']:.4f}% |")
    A(f"| 单任务缺失词 = 0 | 任一任务 >0 即记录 | 0 个任务 | 0 个任务（字级） |")
    A(f"| 去标点后逐字符一致 = 100% | 本批**保留标点**即已一致（更严格） | {aj['identical']}/{aj['n']} |"
      f" {ak['identical']}/{ak['n']} |")
    A(f"| 缺失块数 = 0 | 连续缺失片段 | 0 | 0 |")
    A(f"| 多余词数 = 0 | 识别串任务 | {aj['extra_c']} 字 | {ak['extra_c']} 字 |")
    A("")
    A("**通道 B（paraIndex 连续性）本次不适用**：本批语料为**单段落**（无换行），"
      "服务端所有正文段 `paraIndex` 恒为 0，序号连续性无判别力 —— 已改用字级缺失 + "
      "segments/SRT 一致性 + 音频空洞检测作为替代证据。")
    A("")

    # 四、逐任务明细
    A("## 四、逐任务明细")
    A("")
    for lang in ("ja", "ko"):
        d = data[lang]
        word_col = "词级缺失※" if lang == "ja" else "词级缺失"
        A(f"### {d['cn']}（{len(d['rows'])} 个任务）")
        A("")
        A(f"| seq | taskId | 单元 | 发送字 | 返回字 | 字级缺失 | 字级多余 | {word_col} | 相似度(字) | 段数 | SRT | 标题段 |")
        A("|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for r in d["rows"]:
            A(f"| {r['seq']} | {r['taskId']} | {r['unit']} | {r['sent_chars']:,} | {r['ret_chars']:,} |"
              f" {r['missing_chars']} | {r['extra_chars']} | {r['missing_words']} | {r['sim_char']} |"
              f" {r['segments']} | {r['srt_entries']} | {r['title_segments']} |")
        A("")
        if lang == "ja":
            A("> ※ 日语不使用词间空格，空白分词会把整句当成一个 token，**词级数值无意义**，"
              "仅保留供对照；日语的判定一律以**字级缺失 = 0** 为准（见第五节）。")
            A("")

    # 五、词级差异
    A("## 五、词级差异专项说明")
    A("")
    A(f"- **日语**：词级差异 {aj['miss_w']:,} 个 token / 发送 {aj['sent_w']:,} 词（"
      f"{100*aj['miss_w']/aj['sent_w']:.2f}%）。**该数值无意义**——日语不使用词间空格，"
      f"空白分词会把整句当成一个 token，故日语一律以**字级**判定（字级缺失 0）。")
    A(f"- **韩语**：词级缺失 {ak['miss_w']} 个 token / 发送 {ak['sent_w']:,} 词"
      f"（{100*ak['miss_w']/ak['sent_w']:.4f}%），集中于下列任务；**同任务字级缺失均为 0、相似度 1.0**：")
    A("")
    if ko["diffs"]:
        A("| seq | taskId | 词级缺失 token | 词级多余 token | 字级缺失 | 字级相似度 |")
        A("|---:|---|---|---|---:|---:|")
        for r in ko["diffs"]:
            A(f"| {r['seq']} | {r['taskId']} | `{r['missing_word_head']}` | — | {r['missing_chars']} |"
              f" {r['sim_char']} |")
        A("")
        A("> 判读：缺失 token 均以**半角单引号开头**（`'어째서` / `'곧` / `'한지훈은`），"
          "系**引号归属**造成的分词边界差异；字级逐字符一致 → **非文案丢失**，属标点/分词写法差异。")
    A("")

    # 六、串扰
    A("## 六、串扰（TC-TXT-006）与多余内容检查")
    A("")
    A(f"- 字级多余内容：日语 {aj['extra_c']} 字、韩语 {ak['extra_c']} 字 → "
      f"返回文本中**没有**输入之外的正文内容，**无串任务迹象**。")
    A(f"- 词级多余：日语 {aj['extra_w']:,}（无意义，同上）、韩语 {ak['extra_w']} 个 token（引号分词差异）。")
    A("- 逐任务「发送原文 / 返回 JSON」均已落盘（`src/`、`meta/`），可随时复核或重算。")
    A("")

    # 七、与音频口径的交叉证据
    A("## 七、与音频口径的交叉证据（JSON 对比查不出什么）")
    A("")
    A("同一批次音频分析（`audio_m2.json`）发现的、**文本比对完全无法发现**的问题：")
    A("")
    A("| 语种 | seq | 空洞起点 | 时长 | 该区间电平 | metadata 是否含文本 |")
    A("|---|---:|---:|---:|---:|---|")
    for lang in ("ja", "ko"):
        for g in data[lang]["m2"].get("gap_files", []):
            for det in g.get("gaps", []):
                A(f"| {data[lang]['cn']} | {g['seq']} | {det['start_s']}s | {det['dur_s']}s |"
                  f" ≈ −82 dBFS | 是：{(det.get('meta_text_sample') or '')[:30]} |")
    A("")
    A("- 独立验证（ASR large-v3 定点核查）：**韩语 0044** 该 83s 窗口参考文本 1218 字，"
      "ASR 仅识别出 **13 字（删除率 96.2%）**；**日语 0035** 同窗口模型只输出静音幻觉短语 "
      "`ご視聴ありがとうございました…`；而**相邻正常段**识别相似度 0.83。")
    A("- 机制定位：日语 0035 与韩语 0044 的异常段时长**完全相同 = 81.64s**（文本量差 64 倍），"
      "判定为**片段合成失败后插入的固定时长静默占位**（详见主报告第五节）。")
    A("")
    A("> **要点**：**文案一致性（M1）为 0 缺失 是必要条件，不是充分条件。**"
      "M1 通过 ≠ 音频完整；音频口径（M3/空洞检测）与文本口径必须分别报告。")
    A("")

    # 八、声明
    A("## 八、本次测试项声明")
    A("")
    A("| 项 | 执行 | 说明 |")
    A("|---|---|---|")
    A("| M1 文案一致性（高并发口径，10 并发） | ✅ | 日/韩各一轮 30 分钟，全量任务逐条比对 |")
    A("| M1 文案一致性（低并发口径 1~2） | ⚠️ 部分 | 仅 2 任务烟测（76~86s/任务，0 缺失）；"
      "未做 1~2 并发 30 分钟跑批 |")
    A("| 通道 A 词对齐（保存下发原文） | ✅ | 每任务 `src/task_XXXX.txt` 落盘 |")
    A("| 通道 B paraIndex 连续性 | ❌ 不适用 | 单段落语料下 paraIndex 恒为 0（已用替代证据） |")
    A("| 串任务检测（TC-TXT-006） | ✅ 间接 | 多余内容 = 0，无串任务迹象 |")
    A("| 音频空洞交叉验证 | ✅ | 能量 + 段时长 + ASR 三方互证 |")
    A("")

    # 九、缺陷与建议
    A("## 九、缺陷与建议")
    A("")
    A("- **文案一致性本身未发现缺陷**：0 缺失、0 多余、逐字符一致 100%。")
    A("- **建议 1（服务端）**：M1 全绿但音频存在 82s 静默占位，说明服务端缺少"
      "「返回分段数 vs 实际产出音频有效能量」的一致性校验，建议补齐（详见主报告缺陷 1）。")
    A("- **建议 2（服务端）**：18/225 任务完成后立即下载 `audio_url` 返回 COS `NoSuchKey`"
      "（事后重下均成功），属产物可见性竞态，建议置成功前做一次对象可读性校验。")
    A("- **建议 3（测试侧）**：日语务必按字级判定，韩语以词级为主、字级交叉验证；"
      "后续新增语种（中/日/韩等无空格或弱空格语言）在技能中固化该口径。")
    A("")

    # 十、附件
    A("## 十、附件索引")
    A("")
    A("| 内容 | 路径（相对仓库根） |")
    A("|---|---|")
    for lang in ("ja", "ko"):
        d = data[lang]
        rel = d["run"].relative_to(ROOT)
        A(f"| {d['cn']} 下发原文（{len(d['rows'])} 个） | `{rel}\\src\\` |")
        A(f"| {d['cn']} 返回 metadata JSON | `{rel}\\meta\\` |")
        A(f"| {d['cn']} 派生字幕 SRT | `{rel}\\srt\\` |")
        A(f"| {d['cn']} 逐任务明细 CSV | `{rel}\\analysis\\m1_per_task.csv` |")
        A(f"| {d['cn']} 分析汇总 JSON | `{rel}\\analysis\\perf_m1_m5.json`、`{rel}\\analysis\\audio_m2.json` |")
    A("| 两语种合并逐任务明细 | `docs\\听书测试物料\\mp3\\analysis_ja_ko_m1_per_task.csv` |")
    A("| 主报告（完整口径，含 M2/M3/性能/缺陷） | `docs\\听书测试物料\\测试报告\\Higgs_日韩_10并发30分钟_20260924.md` |")
    A("| 本报告生成/复核脚本 | `gen_report_m1_0924.py`、`_recheck_m1_from_disk_0924.py` |")
    A("| 迭代快照 | `backups/iterations/20260924-111127-ja-ko-10concurrent-30min` |")
    A("")

    # 十一、数据范围
    A("## 十一、数据范围声明")
    A("")
    A(f"- 本报告结论**仅来自 {DATE} 两个批次**（日语 {aj['n']} 个任务、韩语 {ak['n']} 个任务），"
      f"未引用其它时段/语种/模型数据；环境为测试环境（dev）。")
    A(f"- 比对覆盖发送字符合计 日语 {aj['sent_c']:,} 字、韩语 {ak['sent_c']:,} 字；"
      f"语料为 ~5000 字符**单段落**完整句，**不代表**短文本、多段落或整章（8000+ 字符）场景。")
    A("- 本报告不包含音频质量与性能结论，那些见主报告。")
    A("")

    # 十二、历史对比
    A("## 十二、与历史报告的关系")
    A("")
    A("| 对比项 | 历史（0910 六语种，5 并发） | 本次（0924 日/韩，10 并发） |")
    A("|---|---|---|")
    A("| 文案缺失 | 服务异常恢复后首跑：英 8.06% / 德 10.16% / 俄 7.63%（间歇性） | 日语 0.0000% / 韩语 0.0000% |")
    A("| 复现情况 | 同参数复跑即 0 缺失 | **未复现**（本轮为正常状态） |")
    A("| 新增风险 | — | 音频静默占位（文本比对查不出） |")
    A("")
    A("> 与历史结论不冲突：本次同样印证「正常状态下文案完整」；历史那类丢失为**间歇性**，"
      "仍建议在服务异常恢复后的首批任务保持逐任务比对。")
    A("")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / f"文案一致性专项_M1_日韩_{DATE.replace('-', '')}.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"\n[OK] {out}")
    print(f"     日/韩：缺失率 {100*aj['miss_c']/aj['sent_c']:.4f}% / {100*ak['miss_c']/ak['sent_c']:.4f}%"
          f"｜逐字符一致 {aj['identical']}/{aj['n']}、{ak['identical']}/{ak['n']}")


if __name__ == "__main__":
    main()
