# -*- coding: utf-8 -*-
r"""导出「静音空洞」人工听测包。

对象：10 并发压测中「metadata 有文本、音频近乎无声」的文件
      （日语 0035/0054/0083，韩语 0044/0048；来源 analysis/audio_m2.json 的 gap_files）

包内结构（<包目录>/）：
  README.md                     听测总说明（怎么听、听什么、判据）
  听测记录表.md                  逐条待填表格
  01_完整音频/                   原始完整 mp3（保留上下文）
  02_问题片段/                   空洞前后截取的短片段（20s 前导 + 空洞 + 15s 收尾）
  03_字幕SRT/                    完整 SRT + 片段 SRT（时间轴已按片段起点重算）
  04_说明/                       逐文件说明（空洞位置、该处应有的文本、evidence）
  evidence/gaps.json             原始证据（空洞区间 + metadata 重叠段 + 电平）

用法：
  & "D:\python\python.exe" docs\听书测试物料\export_silence_review_pack_0924.py
"""
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(r"D:\python\dmx\cdtest")
MP3 = ROOT / "docs" / "听书测试物料" / "mp3"
PACK = ROOT / "docs" / "听书测试物料" / "人工听测包_静音空洞_0924"
FFMPEG = r"D:\ffmpeg-6.0-full_build\bin\ffmpeg.exe"

RUNS = {"ja": ("日语", MP3 / "Higgs_日语_10并发30分钟_0924"),
        "ko": ("韩语", MP3 / "Higgs_韩语_10并发30分钟_0924")}
PRE_S, POST_S = 20.0, 15.0          # 片段前导/收尾秒数
GAP_RMS = {("ja", 35): -81.8, ("ja", 54): -82.0, ("ja", 83): -66.3,
           ("ko", 44): -81.5, ("ko", 48): -81.7}


def fms(ms):
    h, m = ms // 3600000, (ms % 3600000) // 60000
    s, msec = (ms % 60000) // 1000, ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{msec:03d}"


def hms(sec):
    sec = max(0.0, sec)
    return f"{int(sec // 60):02d}:{sec % 60:06.3f}"


def taskid_of(run, seq):
    for line in (run / "tasks.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            if r["seq"] == seq:
                return r.get("taskId"), r.get("unit"), r.get("chapter_title")
    return None, None, None


def cut(src, start_s, dur_s, dst):
    # 注意：沙箱下不能用管道捕获子进程输出（CreatePipe 会被拒绝），
    # 一律走 DEVNULL（等价 stdio=ignore），只保留文件产物。
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(src),
                    "-ss", f"{start_s:.3f}", "-t", f"{dur_s:.3f}",
                    "-c:a", "libmp3lame", "-b:a", "64k", str(dst)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    if PACK.exists():
        print(f"[注意] 包目录已存在，本次为**增量覆盖**（不删除任何已有文件）：{PACK}")
    d_full, d_clip = PACK / "01_完整音频", PACK / "02_问题片段"
    d_srt, d_note, d_ev = PACK / "03_字幕SRT", PACK / "04_说明", PACK / "evidence"
    for d in (d_full, d_clip, d_srt, d_note, d_ev):
        d.mkdir(parents=True, exist_ok=True)

    evidence, items = {"generated_from": "analysis/audio_m2.json", "files": []}, []

    for lang, (cn, run) in RUNS.items():
        m2 = json.loads((run / "analysis" / "audio_m2.json").read_text(encoding="utf-8"))
        for g in m2.get("gap_files", []):
            seq = g["seq"]
            gaps = g.get("gaps", [])
            if not gaps:
                continue
            tid, unit, title = taskid_of(run, seq)
            src = run / "audio" / f"task_{seq:04d}.mp3"
            segs = json.loads((run / "meta" / f"task_{seq:04d}.json").read_text(encoding="utf-8"))
            total_s = max(s.get("endMs", 0) for s in segs) / 1000.0

            lo = max(0.0, min(x["start_s"] for x in gaps) - PRE_S)
            hi = min(total_s, max(x["start_s"] + x["dur_s"] for x in gaps) + POST_S)
            rng = f"{int(lo)}-{int(hi)}s"
            base = f"{cn}_task{seq:04d}_空洞{rng}"

            # 01 完整音频 + 03 完整 SRT
            full_mp3 = d_full / f"{base}_完整.mp3"
            shutil.copy2(src, full_mp3)
            full_srt_src = run / "srt" / f"task_{seq:04d}.srt"
            full_srt = d_srt / f"{base}_完整.srt"
            shutil.copy2(full_srt_src, full_srt)

            # 02 问题片段
            clip_mp3 = d_clip / f"{base}_片段.mp3"
            cut(src, lo, hi - lo, clip_mp3)

            # 03 片段 SRT（时间轴按 lo 重算）
            picked = [s for s in segs if (s.get("text") or "").strip()
                      and s.get("endMs", 0) / 1000 > lo and s.get("startMs", 0) / 1000 < hi]
            lines = []
            for i, s in enumerate(picked, 1):
                a = max(0, s.get("startMs", 0) - int(lo * 1000))
                b = max(0, s.get("endMs", 0) - int(lo * 1000))
                lines += [str(i), f"{fms(a)} --> {fms(b)}", (s.get("text") or "").strip(), ""]
            clip_srt = d_srt / f"{base}_片段.srt"
            clip_srt.write_text("\n".join(lines), encoding="utf-8")

            # 04 逐文件说明
            rows = []
            for x in gaps:
                a_ms, b_ms = x["start_s"] * 1000, (x["start_s"] + x["dur_s"]) * 1000
                cov = [s for s in segs if (s.get("text") or "").strip()
                       and min(s.get("endMs", 0), b_ms) - max(s.get("startMs", 0), a_ms) > 500]
                rows.append((x, cov))
            note = [f"# {cn} task_{seq:04d} — 静音空洞听测说明", "",
                    f"- 源文件：`{src.relative_to(ROOT)}`",
                    f"- taskId：`{tid}`｜语料单元：`{unit}`｜chapter_title：`{title}`",
                    f"- 音频总时长：{total_s:.2f}s｜片段文件：`02_问题片段/{clip_mp3.name}`"
                    f"（对应原音频 {hms(lo)} ~ {hms(hi)}）", "",
                    "## 需要重点听的位置", ""]
            for k, (x, cov) in enumerate(rows, 1):
                rel = x["start_s"] - lo
                note += [f"### 空洞 {k}：原音频 {hms(x['start_s'])} 起，持续 {x['dur_s']}s"
                         f"（该区间电平 ≈ {GAP_RMS.get((lang, seq), -82)} dBFS）", "",
                         f"- 在片段文件中的位置：**{hms(rel)} ~ {hms(rel + x['dur_s'])}**",
                         f"- 该时段 metadata 判定「本应有语音」的段数：{len(cov)}"]
                if cov:
                    note += ["- 该时段本应朗读的文本（节选）：", "", "  > " + (cov[0].get("text") or "")[:200]]
                note += [f"- 空洞完整 metadata 证据：`evidence/gaps.json`（seq={seq}）", ""]
            note += ["## 听测要点", "",
                     "1. 上述时段是否**完全无声或音量极低**（与前后正常朗读对比）？",
                     "2. 空洞**前后**是否有破音/爆音/杂音/卡顿？",
                     "3. 整段听感是否偏响、有失真（本批日语整体峰值 >1.0，存在削波风险）？",
                     "4. 结论请填入 `听测记录表.md`（含听测人、时间）。", ""]
            (d_note / f"{base}_说明.md").write_text("\n".join(note), encoding="utf-8")

            items.append({"lang": lang, "cn": cn, "seq": seq, "taskId": tid, "unit": unit,
                          "total_s": round(total_s, 2), "clip": clip_mp3.name,
                          "clip_range": f"{hms(lo)}~{hms(hi)}", "gaps": gaps,
                          "gaps_rel": [{"rel_s": round(x["start_s"] - lo, 1), "dur_s": x["dur_s"]}
                                       for x in gaps],
                          "gap_rms_dbfs": GAP_RMS.get((lang, seq))})
            evidence["files"].append({"lang": lang, "seq": seq, "taskId": tid,
                                      "total_s": round(total_s, 2),
                                      "clip_range_s": [round(lo, 2), round(hi, 2)],
                                      "gaps": gaps,
                                      "meta_segments_in_gap": [
                                          {"startMs": s.get("startMs"), "endMs": s.get("endMs"),
                                           "text_head": (s.get("text") or "")[:120]}
                                          for _, cov in rows for s in cov[:2]]})

    (d_ev / "gaps.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")

    # README
    readme = ["# 静音空洞 人工听测包（日/韩 10 并发压测）", "",
              "> 背景：2026-09-24 对 Higgs TTS v3 做日语、韩语各 10 并发 × 30 分钟压测。",
              "> **文本口径零缺失**（输入文案 ↔ 返回 JSON 逐字符一致），但音频分析发现 5 个文件在",
              "> **metadata 有文本的时段近乎无声**（电平 ≈ −82 dBFS），最长 82.6s。",
              "> 其中日语 0035 与韩语 0044 的异常段时长完全相同 = 81.64s，疑似「合成失败后插入固定时长静默占位」。",
              "> 现请人工听测确认。", "",
              "## 怎么听（3 步）", "",
              "1. 打开 `02_问题片段/` 的 mp3 —— 每个文件都是「空洞前 20s + 空洞 + 后 15s」的短片段，",
              "   文件名里带原音频时间范围（如 `日语_task0035_空洞49-166s_片段.mp3`）。",
              "2. 对照同目录同名 `03_字幕SRT/*_片段.srt`（字幕时间轴已按片段起点重算，可直接拖进播放器）。",
              "3. 先看 `04_说明/<同名>_说明.md`，里面写了**在片段内的第几秒到第几秒应当有语音却没有**。", "",
              "## 包内文件", ""]
    readme += ["| 目录 | 内容 |", "|---|---|",
               f"| `01_完整音频/` | 5 个原始完整 mp3（约 9~13 分钟/个，保留上下文） |",
               f"| `02_问题片段/` | 5 个短片段（空洞前后截取），**优先听这些** |",
               f"| `03_字幕SRT/` | 完整 SRT + 片段 SRT（片段 SRT 时间轴已重算） |",
               f"| `04_说明/` | 逐文件说明：空洞位置、片段内相对时间、该处应有的文本 |",
               f"| `evidence/gaps.json` | 原始证据：空洞区间、电平、该时段 metadata 文本 |",
               f"| `听测记录表.md` | **待填**：逐条结论 + 听测人 + 时间 |", ""]
    readme += ["## 待听测清单", "",
               "| # | 语种 | taskId | 片段文件 | 片段内需重点听的位置 | 空洞时长 |",
               "|---|---|---:|---|---|---:|"]
    for i, it in enumerate(items, 1):
        where = "；".join(f"第 {hms(g['rel_s'])} 起 {g['dur_s']}s" for g in it["gaps_rel"])
        readme.append(f"| {i} | {it['cn']} | {it['taskId']} | `{it['clip']}` | {where} | "
                      f"{max(x['dur_s'] for x in it['gaps'])}s |")
    readme += ["", "## 判据（填写时参考）", "",
               "- 若该时段**基本听不到朗读**：确认「音频内容丢失」缺陷成立（P1）。",
               "- 若该时段能听到朗读但音量很低：属「电平异常偏低」，同样需要修复。",
               "- 若整段听感偏响/破音：对应 M2「削波/响度越界」缺陷（日语更明显）。",
               "- 请勿只写「未发现问题」，需写明**听测人 / 抽样文件 / 听测方式**（技能要求）。", ""]
    (PACK / "README.md").write_text("\n".join(readme), encoding="utf-8")

    # 听测记录表
    rec = ["# 静音空洞 听测记录表（待填）", "",
           f"- 听测人：____________　听测日期：____________　播放设备/耳机：____________", "",
           "| # | 语种 | taskId | 片段文件 | 空洞在片段内的位置 | 是否听到朗读 | 是否有破音/杂音 | 听感备注 |",
           "|---|---|---:|---|---|---|---|---|"]
    for i, it in enumerate(items, 1):
        where = "；".join(f"{hms(g['rel_s'])}起{g['dur_s']}s" for g in it["gaps_rel"])
        rec.append(f"| {i} | {it['cn']} | {it['taskId']} | `{it['clip']}` | {where} | ☐ 有 ☐ 无 | ☐ 有 ☐ 无 | |")
    rec += ["", "## 整体结论", "",
            "- 日语：____________________________________________",
            "- 韩语：____________________________________________", "",
            "## 补充说明（可选）", "",
            "- 是否复听完整音频确认上下文：☐ 是 ☐ 否",
            "- 其它异常（卡顿/重复/串音/尾音截断）：____________________________", ""]
    (PACK / "听测记录表.md").write_text("\n".join(rec), encoding="utf-8")

    print(f"[OK] 听测包已生成：{PACK}")
    for d in sorted(PACK.iterdir()):
        if d.is_dir():
            fs = sorted(d.iterdir())
            print(f"  {d.name}/  {len(fs)} 个文件")
        else:
            print(f"  {d.name}")


if __name__ == "__main__":
    main()
