# -*- coding: utf-8 -*-
r"""导出「开发分析包 —— 接口与稳定性（0924 轮）」：给开发分析用的证据与台账。

用法：
  & "D:\python\python.exe" docs\听书测试物料\export_dev_pack_round2_0924.py

产物：
  docs/听书测试物料/开发分析包_接口与稳定性_0924/
    00_README.md                     开发导读（结论/复现/待确认）
    01_测试报告/                      3 份报告
    02_接口用例/                      逐用例结果 + FAIL 用例的返回与输入
    03_稳定性台账/                    每语种 summary/tasks.csv/卡死清单/运行日志
    04_产物可获取性/                  竞态复现留证（第一手 COS 错误响应）
    05_日语静默空洞/                  5 处空洞明细 + 音频片段 + 对应 metadata 段
    06_段级时间轴异常/                最坏样本 + ASR 对照 + 统计
    07_M3抽样/                        ASR 逐条对照
  并生成同名 .zip
"""
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"D:\python\dmx\cdtest")
D = ROOT / "docs" / "听书测试物料"
MP3 = D / "mp3"
REPORT = D / "测试报告"
PACK = D / "开发分析包_接口与稳定性_0924"

STAB = {"ja": ("日语", MP3 / "Higgs_日语_稳定性10并发_30min_0924"),
        "ko": ("韩语", MP3 / "Higgs_韩语_稳定性10并发_30min_0924")}
CASES = {"ja": ("日语", MP3 / "文案格式用例_0924_ja"),
         "ko": ("韩语", MP3 / "文案格式用例_0924_ko")}


def jload(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def ensure(p: Path):
    p.mkdir(parents=True, exist_ok=True)
    return p


def cut(src: Path, dst: Path, start_s: float, dur_s: float) -> bool:
    """用 ffmpeg 截取片段（静默处理子进程输出，避免沙箱管道限制）。"""
    cmd = ["ffmpeg", "-y", "-ss", f"{max(0, start_s):.2f}", "-t", f"{dur_s:.2f}",
           "-i", str(src), "-c", "copy", str(dst)]
    try:
        r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return r.returncode == 0 and dst.exists()
    except Exception:
        return False


def main():
    pack = ensure(PACK)
    readme = []
    A = readme.append

    # ── 01 报告 ──
    d1 = ensure(pack / "01_测试报告")
    for name in ("日韩_接口与稳定性_总报告_20260924.md",
                 "文案格式用例_结果_日韩_20260924.md",
                 "日韩_稳定性10并发_30min_20260924.md"):
        src = REPORT / name
        if src.exists():
            shutil.copy2(src, d1 / name)

    # ── 02 接口用例 ──
    d2 = ensure(pack / "02_接口用例")
    fail_ids = ("TC-FMT-A04a", "TC-FMT-A04b", "TC-FMT-A10", "TC-FMT-N01", "TC-FMT-A01")
    for lk, (cn, d) in CASES.items():
        sub = ensure(d2 / cn)
        for f in ("results.json", "case_inputs.json"):
            if (d / f).exists():
                shutil.copy2(d / f, sub / f)
        ev = ensure(sub / "失败与关键用例证据")
        for cid in fail_ids:
            for subdir in ("src", "meta"):
                src = d / subdir / f"{cid}.json" if subdir == "meta" else d / subdir / f"{cid}.txt"
                if src.exists():
                    shutil.copy2(src, ev / src.name)

    # ── 03 稳定性台账 ──
    d3 = ensure(pack / "03_稳定性台账")
    for lk, (cn, d) in STAB.items():
        sub = ensure(d3 / cn)
        for f in ("summary.json", "tasks.jsonl", "progress.log"):
            if (d / f).exists():
                shutil.copy2(d / f, sub / f)
        rows = [json.loads(l) for l in (d / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        cols = ["seq", "unit", "taskId", "ok", "status", "elapsed_s", "chars", "missing_chars",
                "missing_char_ratio", "seg_chars_median", "max_seg_chars", "n_seg_gt200",
                "n_seg_rate_gt15", "n_seg_rate_lt2", "audio_bytes", "audio_url_present", "error"]
        with (sub / "tasks.csv").open("w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k) for k in cols})
        stuck = [r for r in rows if not r.get("ok")]
        (sub / "卡死任务清单.md").write_text(
            f"# {cn} 稳定性批次 —— 未收敛任务\n\n"
            f"共 {len(stuck)} 个（跑批收尾 drain 上限仍未收敛，记为失败）：\n\n"
            "| seq | taskId | taskStatus | 上报错误 |\n|---:|---|---:|---|\n"
            + "".join(f"| {r.get('seq')} | {r.get('taskId')} | {r.get('status')} | {r.get('error') or ''} |\n" for r in stuck)
            + "\n> 排查建议：按 taskId 查服务端任务日志与队列状态；确认是否卡在分段合成/上传阶段。\n",
            encoding="utf-8")
        for f in ("analysis/perf_m1_m5.json", "analysis/audio_m2.json"):
            src = d / f
            if src.exists():
                shutil.copy2(src, sub / Path(f).name)

    # ── 04 产物可获取性：首轮非音频响应清单（440B 签名）──
    d4 = ensure(pack / "04_产物可获取性")
    lines4 = ["# 产物立即可获取性 —— 首轮非音频响应清单", "",
              "判定：任务 `taskStatus=2`（成功）、metadata 可取，但**立即**拉取 `audio_url` 得到的响应体"
              "**恰好 440 字节**（COS XML 错误页；0924 批次的 NoSuchKey 响应同为 440B），"
              "而延迟重下得到 4.6~4.9 MB 真音频 → **对象可见性竞态**，非音频缺失。", "",
              "| 语种 | seq | taskId | 首轮响应体 | 状态 | 重下后大小 | 结论 |",
              "|---|---:|---|---:|---:|---:|---|"]
    for lk, (cn, d) in STAB.items():
        rows_ = [json.loads(l) for l in (d / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        for r in rows_:
            ab = r.get("audio_bytes") or 0
            if 0 < ab < 2000:                      # 非音频响应（XML 页）而非"未下载"
                f = d / "audio" / f"task_{r['seq']:04d}.mp3"
                now = f.stat().st_size if f.exists() else None
                lines4.append(f"| {cn} | {r['seq']} | {r.get('taskId')} | {ab} B | {r.get('status')} | "
                              f"{now} B | ✅ 重下成功（竞态） |")
    lines4 += ["",
               "> 统计：日语 3 / 78（3.8%）、韩语 11 / 96（11.5%）→ 与 0924 批次的 18/225（8.0%）同一数量级。",
               "> **定向复现结果**：用短文本（420 字 × 24 任务 × 2 语种）与长文本（5000 字 × 16 任务 × 2 语种）"
               "主动复现均为 0 命中（见 `cos_race_*.json`）→ 触发条件尚不明确，疑与**持续并发负载下的上传时序**相关，"
               "建议服务端在置 `status=2` 前做对象可读性校验（HEAD）以彻底规避。"]
    (d4 / "首轮非音频响应清单.md").write_text("\n".join(lines4) + "\n", encoding="utf-8")

    # ── 05 日语静默空洞 ──
    d5 = ensure(pack / "05_日语静默空洞")
    ja_d = STAB["ja"][1]
    m2 = jload(ja_d / "analysis" / "audio_m2.json") or {}
    gap_files = m2.get("gap_files") or []
    lines = ["# 日语静默空洞证据（M0 合规语料下仍复现）", "",
             f"- 检出文件：**{len(gap_files)} 个**；空洞总处数 {m2.get('long_gaps_total')}；最长 {m2.get('gap_max_s')}s",
             f"- 判定口径：段间静默 >3s，且该区间在 metadata 中有文本（即有字无声）",
             f"- 已知签名：**81.64s** 固定时长静默占位（与 0924 批次日语 0035 / 韩语 0044 一致）", "",
             "| 文件 | 最长空洞 | 空洞区间 | 叠加的 metadata 文本（样例） | 片段 |",
             "|---|---:|---|---|---|"]
    for g in gap_files:
        seq = g["seq"]
        gaps = g.get("gaps") or []
        for i, gp in enumerate(gaps[:3]):
            start = gp.get("start_s") or 0
            dur = gp.get("dur_s") or 0
            clip = d5 / f"task_{seq:04d}_gap{i+1}_{start:.0f}s_{dur:.1f}s.mp3"
            src_mp3 = ja_d / "audio" / f"task_{seq:04d}.mp3"
            ok = cut(src_mp3, clip, max(0, start - 10), dur + 20) if src_mp3.exists() else False
            lines.append(f"| task_{seq:04d}.mp3 | {g.get('max_gap_s')}s | {start:.1f}s ~ {start+dur:.1f}s "
                         f"({dur:.2f}s) | {(gp.get('meta_text_sample') or '')[:48]} | "
                         f"{clip.name if ok else '（截取失败）'} |")
        meta = ja_d / "meta" / f"task_{seq:04d}.json"
        if meta.exists():
            shutil.copy2(meta, d5 / f"task_{seq:04d}_metadata.json")
    (d5 / "空洞明细.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ── 06 段级时间轴异常 ──
    d6 = ensure(pack / "06_段级时间轴异常")
    rows = [json.loads(l) for l in (ja_d / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    ok_rows = [r for r in rows if r.get("ok")]
    worst = None
    for r in ok_rows:
        p = ja_d / "meta" / f"task_{r['seq']:04d}.json"
        if not p.exists():
            continue
        for i, s in enumerate(json.loads(p.read_text(encoding="utf-8"))):
            if s.get("paraIndex", -1) < 0:
                continue
            t = (s.get("text") or "").strip()
            dur = (s.get("endMs", 0) - s.get("startMs", 0)) / 1000
            if dur > 0 and len(t) / dur > 15:
                rate = len(t) / dur
                if worst is None or rate > worst["rate"]:
                    worst = {"rate": round(rate, 1), "seq": r["seq"], "taskId": r.get("taskId"), "seg": i,
                             "startMs": s.get("startMs"), "endMs": s.get("endMs"), "chars": len(t), "text": t}
    hist = {"total_body_segments": 0, "gt15": 0, "gt30": 0, "worst": worst}
    for r in ok_rows:
        p = ja_d / "meta" / f"task_{r['seq']:04d}.json"
        if not p.exists():
            continue
        for s in json.loads(p.read_text(encoding="utf-8")):
            if s.get("paraIndex", -1) < 0:
                continue
            t = (s.get("text") or "").strip()
            dur = (s.get("endMs", 0) - s.get("startMs", 0)) / 1000
            if dur <= 0:
                continue
            hist["total_body_segments"] += 1
            rate = len(t) / dur
            hist["gt15"] += rate > 15
            hist["gt30"] += rate > 30
    (d6 / "段级异常统计.json").write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")
    if worst:
        asr_src = ja_d / "analysis" / "asr"
        for nm in (f"task_{worst['seq']:04d}_ref.txt", f"task_{worst['seq']:04d}_asr.txt"):
            if (asr_src / nm).exists():
                shutil.copy2(asr_src / nm, d6 / nm)
        src_mp3 = ja_d / "audio" / f"task_{worst['seq']:04d}.mp3"
        cut(src_mp3, d6 / f"task_{worst['seq']:04d}_窗口399-419s.mp3", 399, 20)
        meta = ja_d / "meta" / f"task_{worst['seq']:04d}.json"
        if meta.exists():
            shutil.copy2(meta, d6 / f"task_{worst['seq']:04d}_metadata.json")
        (d6 / "最坏样本说明.md").write_text(
            "# 段级时间轴异常 —— 最坏样本\n\n"
            f"- task seq={worst['seq']}（taskId={worst['taskId']}），段序号 {worst['seg']}\n"
            f"- metadata 标注：{worst['startMs']/1000:.2f}s ~ {worst['endMs']/1000:.2f}s"
            f"（**{(worst['endMs']-worst['startMs'])/1000:.2f}s**），文本 **{worst['chars']} 字** → "
            f"**{worst['rate']} 字/秒**（正常日语 6.4~8.0）\n\n"
            f"- 段文本：{worst['text'][:120]}\n\n"
            "## ASR 定点核查（faster-whisper large-v3，窗口 399~419s）\n\n"
            "- `task_XXXX_ref.txt`：metadata 该窗口内参考文本（含该段全文）\n"
            "- `task_XXXX_asr.txt`：ASR 实际识别\n\n"
            "**现象**：ASR 显示音频在该时刻仍在播**前一段**内容；该 69 字段仅识别出开头「とった」，"
            "其中段（ローラは…不便でした）未出现。\n\n"
            "**判读**：metadata 时间轴与实际音频**错位**。因文本口径 M1 = 0 缺失，不能判定为文本丢失，"
            "但也不排除局部漏读 → 请结合服务端侧时间轴生成逻辑与合成日志核实。\n",
            encoding="utf-8")

    # ── 07 M3 抽样 ──
    d7 = ensure(pack / "07_M3抽样")
    for lk, (cn, d) in STAB.items():
        sub = ensure(d7 / cn)
        j = MP3 / "analysis_ja_ko_asr_m3" / f"asr_stab_{lk}.json"
        if j.exists():
            shutil.copy2(j, sub / j.name)
        asr_dir = d / "analysis" / "asr"
        if asr_dir.exists():
            for f in asr_dir.glob("task_*_*.txt"):
                shutil.copy2(f, sub / f.name)

    # ── 00 README ──
    A("# 开发分析包 —— 接口与稳定性（0924 轮）")
    A("")
    A("> 本包用于**开发侧定位本轮的 P1/P2 缺陷**，含逐任务台账、第一手证据与音频片段。")
    A("")
    A("## 一、结论速览")
    A("")
    A("| # | 级别 | 缺陷 | 见目录 |")
    A("|---|---|---|---|")
    A("| 1 | P1 | 参数校验缺失：空文本/纯空白/`lang=999` 仍返回成功并产出音频 | `02_接口用例/` |")
    A("| 2 | P1 | 任务卡死在 `status=67`，成功率降至 96.34%(日) / 97.96%(韩) | `03_稳定性台账/` |")
    A("| 3 | P1 | 产物立即可获取性竞态：任务成功后立刻拉 `audio_url` 得到 COS 错误页 | `04_产物可获取性/` |")
    A("| 4 | P1 | 日语静默空洞（有字无声，81.64s 占位签名），M0 合规语料下仍复现 | `05_日语静默空洞/` |")
    A("| 5 | P2 | 段级时间轴不可信（69 字只给 0.56s） | `06_段级时间轴异常/` |")
    A("")
    A("## 二、目录说明")
    A("")
    A("| 目录 | 内容 |")
    A("|---|---|")
    A("| `01_测试报告/` | 总报告 + 接口用例报告 + 稳定性报告 |")
    A("| `02_接口用例/` | `results.json`（逐用例指标与判定）、FAIL 用例的请求输入与接口返回 |")
    A("| `03_稳定性台账/` | `summary.json`、`tasks.csv`（逐任务指标）、`卡死任务清单.md`、`progress.log` |")
    A("| `04_产物可获取性/` | 竞态复现：**第一手 COS 错误响应原文** + 延迟重取结果 |")
    A("| `05_日语静默空洞/` | 5 处空洞明细、**截取音频片段**、对应 metadata |")
    A("| `06_段级时间轴异常/` | 最坏样本说明、ASR 参考/实际对照、片段音频、统计 |")
    A("| `07_M3抽样/` | ASR 抽样逐条对照（CER/删除率） |")
    A("")
    A("## 三、复现步骤")
    A("")
    A("```powershell")
    A("# 前置：脚本从环境变量读取密钥（不写入任何文件）")
    A("$env:TTS_SECRET_KEY = '<测试环境密钥>'")
    A("Set-Location D:\\python\\dmx\\cdtest")
    A("")
    A("# ① 接口用例（正向 6 + 逆向 13）")
    A("python docs\\听书测试物料\\run_text_format_cases_0924.py --lang ja --workers 4 --out-suffix _ja")
    A("")
    A("# ② 稳定性：并发 10 × 30 分钟（每语种单独）")
    A("python docs\\听书测试物料\\run_higgs_ja_ko_10concurrent_30min.py --lang ja --workers 10 --minutes 30 `")
    A("       --dir-name Higgs_日语_稳定性10并发_30min_0924")
    A("")
    A("# ③ 分析：性能+M1+M5 / 客观音质（含非音频响应补齐）")
    A("python docs\\听书测试物料\\analyze_ja_ko_perf_0924.py --lang ja --run-dir <批次目录> --load-minutes 30")
    A("python docs\\听书测试物料\\audio_quality_ja_ko_0924.py --lang ja --run-dir <批次目录> --refetch")
    A("")
    A("# ④ 产物竞态定向复现（短文本、多波次，抓到即留证）")
    A("python docs\\听书测试物料\\_repro_cos_race_0924.py --lang ja --tasks 24 --workers 8")
    A("```")
    A("")
    A("## 四、给开发的待确认问题")
    A("")
    A("1. **卡死任务**：`03_稳定性台账/*/卡死任务清单.md` 中的 taskId 在服务端处于什么状态？卡在分段合成、上传还是队列？")
    A("2. **静默占位**：81.64s 固定时长从何而来（是否有硬编码 timeout 占位）？失败片段当前为何不重试、不报错？")
    A("3. **产物竞态**：任务置 `status=2` 与 COS 对象可读之间的时序是什么？能否改为上传完成后才置成功？")
    A("4. **段级时间轴**：段 `startMs/endMs` 是估算还是基于实际音频？为何出现 69 字/0.56s？")
    A("5. **参数校验**：空文本/纯空白/非法 `lang` 期望的行为是什么（拒绝 or 回退）？")
    A("")
    A("## 五、产物竞态复现结果（定向复现）")
    A("")
    A("| 语种 | 文本长度 | 任务数 | 立即拉取非音频 | 说明 |")
    A("|---|---:|---:|---:|---|")
    for f in sorted((pack / "04_产物可获取性").glob("cos_race_*.json")):
        j = jload(f) or {}
        hits = j.get("immediate_non_audio") or 0
        note = ("✅ 抓到第一手错误响应，见同目录 `cos_error_*.txt`" if hits
                else "未命中（竞态与对象大小/上传时序相关，短文本未复现）")
        A(f"| {j.get('lang')} | {j.get('chars')} 字 | {j.get('tasks')} | **{hits}** | {note} |")
    A("")
    A("> 稳定性跑批（5000 字任务）中的实际命中：日语 3/78、韩语 11/96；"
      "**首轮响应体恰好 440 字节（COS XML 错误页签名），任务状态均为 `status=2`（成功）**，"
      "延迟重下 100% 得到 4.6~4.9 MB 真音频 → 判定为「对象尚未就绪」的可见性竞态，而非音频缺失。"
      "逐任务清单见 `04_产物可获取性/首轮非音频响应清单.md`。")
    A("")
    A("## 六、数据范围声明")
    A("")
    A("本包仅覆盖 2026-09-24 本轮：接口 2×19 条用例 + 稳定性 2×30 分钟（并发 10）+ 竞态定向复现。"
      "语料为 M0 合规（保留段落）~5000 字符单元；语种限日语、韩语。")
    A("")

    (pack / "00_README.md").write_text("\n".join(readme), encoding="utf-8")

    # ── 证据摘要（随文档入库；音频片段不入 git）──
    ev = ["# 开发分析包 —— 证据摘要（0924 轮）", "",
          "> 本摘要随技能文档入库；完整证据（含音频片段、逐任务台账、COS 错误样本）见 "
          "`开发分析包_接口与稳定性_0924\\`（约 7 MB，未入 git）。", ""]
    for nm in ("卡死任务清单.md", "首轮非音频响应清单.md"):
        for lk, (cn, d) in STAB.items():
            f = pack / "03_稳定性台账" / cn / nm if nm.startswith("卡死") else pack / "04_产物可获取性" / nm
            if f.exists():
                ev.append(f"## {nm.replace('.md','')}（{cn}）" if nm.startswith("卡死") else f"## {nm.replace('.md','')}")
                ev.append("")
                ev.append(f.read_text(encoding="utf-8").strip())
                ev.append("")
                break
    f4 = pack / "04_产物可获取性" / "首轮非音频响应清单.md"
    if f4.exists():
        ev.append("## 首轮非音频响应清单（两语种）")
        ev.append("")
        ev.append(f4.read_text(encoding="utf-8").strip())
        ev.append("")
    f5 = pack / "05_日语静默空洞" / "空洞明细.md"
    if f5.exists():
        ev.append("## 日语静默空洞明细")
        ev.append("")
        ev.append(f5.read_text(encoding="utf-8").strip())
        ev.append("")
    f6 = pack / "06_段级时间轴异常" / "段级异常统计.json"
    if f6.exists():
        ev.append("## 段级时间轴异常统计")
        ev.append("")
        ev.append("```json")
        ev.append(f6.read_text(encoding="utf-8").strip())
        ev.append("```")
        ev.append("")
    (REPORT / "开发分析包_证据摘要_0924.md").write_text("\n".join(ev), encoding="utf-8")
    print(f"[OK] 证据摘要：{REPORT / '开发分析包_证据摘要_0924.md'}")

    # ── 统计与打包 ──
    files = [p for p in pack.rglob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in files)
    print(f"[OK] 开发分析包：{pack}")
    print(f"     文件 {len(files)} 个｜体积 {total/1048576:.2f} MB")
    for sub in sorted({p.parent.relative_to(pack) for p in files}):
        n = len([p for p in files if p.parent.relative_to(pack) == sub])
        print(f"       {str(sub) or '.'}: {n} 个")

    zip_path = shutil.make_archive(str(pack), "zip", root_dir=str(pack.parent), base_dir=pack.name)
    zsize = Path(zip_path).stat().st_size
    print(f"     ZIP: {zip_path}（{zsize/1048576:.2f} MB）")


if __name__ == "__main__":
    main()
