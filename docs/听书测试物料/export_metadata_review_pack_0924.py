# -*- coding: utf-8 -*-
r"""导出「metadata（切句后结果）」开发分析包。

对象：日/韩 10 并发压测返回的 metadata（= 切句/分段后的结果），聚焦三类异常：
  ① 超长段：单段文本远超正常句长（正常中位 ~42 字；实测最长 1757 字）；
  ② 不可能语速：段时长与文本量严重不符（正常 5~9 字/秒；实测出现 277 字/秒、0.33 字/秒）；
  ③ 静默段：81.64s 固定时长 + 音频近乎无声（日语 0035、韩语 0044）。

包内结构（<包目录>/）：
  README.md                     现象、证据链、可疑环节、复现步骤、待开发确认问题、字段字典
  01_metadata原始/<语种>/         task_XXXX.json（接口原样返回，未修改）
  02_输入原文/<语种>/             task_XXXX.txt（实际下发的 read_content）
  03_段级明细CSV/                 每个样本任务的逐段明细 + 全量异常段汇总
  04_字幕SRT/                     由 metadata 派生的 SRT
  05_汇总分析/                    task_rate_summary.csv / segment_anomalies_all.csv /
                                 splitter_api_evidence.json / asr_evidence.json
  06_音频片段/                    静默段片段 + 韩语 0040 的 0~60s 片段
  07_ASR证据/                     参考文本与 ASR 实际识别文本（逐条可对照）

用法：
  & "D:\python\python.exe" docs\听书测试物料\export_metadata_review_pack_0924.py
"""
import csv
import json
import shutil
import subprocess
import unicodedata
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()

ROOT = Path(r"D:\python\dmx\cdtest")
MP3 = ROOT / "docs" / "听书测试物料" / "mp3"
PACK = ROOT / "docs" / "听书测试物料" / "开发分析包_metadata切句_0924"
SILENCE_PACK = ROOT / "docs" / "听书测试物料" / "人工听测包_静音空洞_0924"
ASR_DIR = MP3 / "analysis_ja_ko_asr_m3"
FFMPEG = r"D:\ffmpeg-6.0-full_build\bin\ffmpeg.exe"
SPLITTER = "https://cuda-merge-server-audiobook.changdu.vip/sentence_spliter"

RUNS = {"ja": ("日语", MP3 / "Higgs_日语_10并发30分钟_0924", "ja"),
        "ko": ("韩语", MP3 / "Higgs_韩语_10并发30分钟_0924", "ko")}
# 样本任务：静默段 + 超长段/异常语速代表 + 正常对照
FOCUS = {"ja": [35, 54, 83, 49, 63, 6, 1], "ko": [44, 48, 40, 119, 87, 82, 1]}
SILENT = {("ja", 35), ("ja", 54), ("ja", 83), ("ko", 44), ("ko", 48)}

LONG_CHARS = 200        # 超长段阈值
RATE_HI = 15.0          # 不可能的高语速
RATE_LO = 2.0           # 异常低语速（疑似静默）


def seg_len(s):
    return len((s.get("text") or "").strip())


def seg_dur(s):
    return (s.get("endMs", 0) - s.get("startMs", 0)) / 1000.0


def cut(src, start_s, dur_s, dst):
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(src),
                    "-ss", f"{start_s:.3f}", "-t", f"{dur_s:.3f}",
                    "-c:a", "libmp3lame", "-b:a", "64k", str(dst)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    if PACK.exists():
        print(f"[注意] 包目录已存在，本次**增量覆盖**（不删除既有文件）：{PACK}")
    dirs = {k: PACK / k for k in ("01_metadata原始", "02_输入原文", "03_段级明细CSV",
                                 "04_字幕SRT", "05_汇总分析", "06_音频片段", "07_ASR证据")}
    for k, d in dirs.items():
        (d / "ja" if k in ("01_metadata原始", "02_输入原文") else d).mkdir(parents=True, exist_ok=True)
        if k in ("01_metadata原始", "02_输入原文"):
            (d / "ko").mkdir(parents=True, exist_ok=True)

    anomalies, task_rows = [], []
    fieldnames = ["lang", "seq", "taskId", "seg_index", "paraIndex", "startMs", "endMs",
                  "dur_s", "chars", "chars_per_s", "startOffset", "endOffset", "text"]

    # 静默空洞（来自音质分析），用于从「可用时长」中扣除静默
    silent_gap_s = {}
    for lang, (cn, run, lc) in RUNS.items():
        m2 = json.loads((run / "analysis" / "audio_m2.json").read_text(encoding="utf-8"))
        for g in m2.get("gap_files", []):
            silent_gap_s[(lang, g["seq"])] = sum(x["dur_s"] for x in g.get("gaps", []))

    # 各语种正常语速基线（全任务中位数），用于估算音频缺口
    rate_all = {}
    for lang, (cn, run, lc) in RUNS.items():
        rates = []
        for line in (run / "tasks.jsonl").read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if not rec.get("ok"):
                continue
            segs = json.loads((run / "meta" / f"task_{rec['seq']:04d}.json").read_text(encoding="utf-8"))
            body = [s for s in segs if s.get("paraIndex", -1) >= 0]
            c = sum(seg_len(s) for s in body)
            d = max(s.get("endMs", 0) for s in segs) / 1000.0
            if d:
                rates.append(c / d)
        rates.sort()
        rate_all[lang] = rates[len(rates) // 2]
    print(f"[语速基线] 日语 {rate_all['ja']:.2f} 字/秒｜韩语 {rate_all['ko']:.2f} 字/秒（全任务中位数）")

    for lang, (cn, run, lc) in RUNS.items():
        for line in (run / "tasks.jsonl").read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if not rec.get("ok"):
                continue
            seq = rec["seq"]
            meta_p = run / "meta" / f"task_{seq:04d}.json"
            src_p = run / "src" / f"task_{seq:04d}.txt"
            segs = json.loads(meta_p.read_text(encoding="utf-8"))
            body = [s for s in segs if s.get("paraIndex", -1) >= 0]
            total_chars = sum(seg_len(s) for s in body)
            total_dur = max(s.get("endMs", 0) for s in segs) / 1000.0
            long_n = sum(1 for s in body if seg_len(s) > LONG_CHARS)
            hi_n = sum(1 for s in body if seg_dur(s) > 0.5 and seg_len(s) / seg_dur(s) > RATE_HI)
            lo_n = sum(1 for s in body if seg_dur(s) > 5 and seg_len(s) / seg_dur(s) < RATE_LO)
            gap = silent_gap_s.get((lang, seq), 0.0)
            base = rate_all[lang]
            need_s = total_chars / base if base else None
            usable_s = max(0.0, total_dur - gap)
            est_missing = (1 - usable_s / need_s) if (need_s and usable_s < need_s) else 0.0
            task_rows.append({
                "lang": lang, "lang_cn": cn, "seq": seq, "taskId": rec.get("taskId"),
                "unit": rec.get("unit"), "segments": len(body),
                "total_chars": total_chars, "audio_total_s": round(total_dur, 2),
                "chars_per_s": round(total_chars / total_dur, 2) if total_dur else None,
                "baseline_chars_per_s": round(base, 2),
                "silent_gap_s": round(gap, 2),
                "est_need_s": round(need_s, 1) if need_s else None,
                "est_missing_ratio": round(est_missing, 4),
                "max_seg_chars": max((seg_len(s) for s in body), default=0),
                "max_seg_dur_s": round(max((seg_dur(s) for s in body), default=0), 2),
                "n_seg_gt200chars": long_n, "n_seg_rate_gt15": hi_n, "n_seg_rate_lt2": lo_n,
                "is_silent_gap_task": int((lang, seq) in SILENT), "ok": True,
            })
            for i, s in enumerate(body):
                L, D = seg_len(s), seg_dur(s)
                rate = L / D if D else 0
                if (L > LONG_CHARS) or (D > 20) or (D > 0.5 and rate > RATE_HI) or (D > 5 and rate < RATE_LO):
                    anomalies.append({
                        "lang": lang, "seq": seq, "taskId": rec.get("taskId"), "seg_index": i,
                        "paraIndex": s.get("paraIndex"), "startMs": s.get("startMs"),
                        "endMs": s.get("endMs"), "dur_s": round(D, 2), "chars": L,
                        "chars_per_s": round(rate, 2), "startOffset": s.get("startOffset"),
                        "endOffset": s.get("endOffset"), "text": (s.get("text") or "")[:200],
                        "flag_long": int(L > LONG_CHARS), "flag_rate_hi": int(D > 0.5 and rate > RATE_HI),
                        "flag_rate_lo": int(D > 5 and rate < RATE_LO), "flag_dur_gt20s": int(D > 20),
                    })

            if seq in FOCUS[lang]:
                shutil.copy2(meta_p, dirs["01_metadata原始"] / lang / f"task_{seq:04d}.json")
                shutil.copy2(src_p, dirs["02_输入原文"] / lang / f"task_{seq:04d}.txt")
                srt_src = run / "srt" / f"task_{seq:04d}.srt"
                if srt_src.exists():
                    shutil.copy2(srt_src, dirs["04_字幕SRT"] / f"{cn}_task{seq:04d}.srt")
                with (dirs["03_段级明细CSV"] / f"{cn}_task{seq:04d}_segments.csv").open(
                        "w", encoding="utf-8-sig", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=fieldnames)
                    w.writeheader()
                    for i, s in enumerate(body):
                        L, D = seg_len(s), seg_dur(s)
                        w.writerow({"lang": lang, "seq": seq, "taskId": rec.get("taskId"),
                                    "seg_index": i, "paraIndex": s.get("paraIndex"),
                                    "startMs": s.get("startMs"), "endMs": s.get("endMs"),
                                    "dur_s": round(D, 3), "chars": L,
                                    "chars_per_s": round(L / D, 2) if D else None,
                                    "startOffset": s.get("startOffset"), "endOffset": s.get("endOffset"),
                                    "text": s.get("text")})
                print(f"  [{cn}] 已收录 task_{seq:04d}（{len(body)} 段，最长段 {max((seg_len(s) for s in body), default=0)} 字）")

    # 汇总 CSV
    with (dirs["05_汇总分析"] / "segment_anomalies_all.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(anomalies[0].keys()))
        w.writeheader()
        w.writerows(anomalies)
    with (dirs["05_汇总分析"] / "task_rate_summary.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(task_rows[0].keys()))
        w.writeheader()
        w.writerows(task_rows)

    # 切句接口证据
    ev = {"endpoint": SPLITTER, "probes": []}
    for label, text, lc in (("日语短句", "夜のホテルの廊下は静かで、彼女はゆっくりと歩いていた。窓の外では雨が降り続いている。", "ja"),
                            ("韩语短句", "밤의 호텔 복도는 조용했고, 그녀는 천천히 걸어갔다. 창밖에는 비가 계속 내리고 있었다.", "ko"),
                            ("英语短句(对照)", "The night was quiet, and she walked slowly down the corridor.", "en")):
        item = {"label": label, "language_code": lc, "text_chars": len(text)}
        try:
            r = requests.post(SPLITTER, json={"text": text, "language_code": lc}, timeout=30, verify=False)
            item["http_status"] = r.status_code
            item["response_raw"] = r.text[:300]
            item["sentences"] = r.json().get("sentences")
        except Exception as e:
            item["error"] = f"{type(e).__name__}: {e}"
        ev["probes"].append(item)
    (dirs["05_汇总分析"] / "splitter_api_evidence.json").write_text(
        json.dumps(ev, ensure_ascii=False, indent=2), encoding="utf-8")

    # ASR 证据
    asr_ev = {"note": "ASR 仅作音频口径参考（判定漏文案以文本口径为准）"}
    for f, tag in ((ASR_DIR / "asr_full40.json", "ko_task0040_整段475s"),
                   (ASR_DIR / "asr_full71.json", "ko_task0071_整段356s"),
                   (ASR_DIR / "asr_check40.json", "ko_task0040_0-60s_超长段"),
                   (ASR_DIR / "asr_gapcheck_ko.json", "ko_task0044_435-518s_静默段"),
                   (ASR_DIR / "asr_gapcheck.json", "ja_task0035_69-152s_静默段"),
                   (ASR_DIR / "asr_gapcheck_ctrl.json", "ja_task0035_151-163s_正常段")):
        if f.exists():
            asr_ev[tag] = json.loads(f.read_text(encoding="utf-8"))
    (dirs["05_汇总分析"] / "asr_evidence.json").write_text(
        json.dumps(asr_ev, ensure_ascii=False, indent=2), encoding="utf-8")

    # 缺失位置定位报告（整段 ASR 后由 _locate_audio_missing_0924.py 落盘）
    for tag in ("ko0040", "ko0071"):
        loc_p = ASR_DIR / f"audio_missing_locate_{tag}.txt"
        if loc_p.exists():
            shutil.copy2(loc_p, dirs["05_汇总分析"] / loc_p.name)
        else:
            print(f"  [提示] 未找到 {loc_p.name}，可先运行 _locate_audio_missing_0924.py")
    for lang, seq, tag in (("ko", 40, "ko_task0040"), ("ja", 35, "ja_task0035")):
        run = RUNS[lang][1]
        for suf in ("ref", "asr"):
            p = run / "analysis" / "asr" / f"task_{seq:04d}_{suf}.txt"
            if p.exists():
                shutil.copy2(p, dirs["07_ASR证据"] / f"{tag}_{suf}.txt")

    # 音频片段
    if SILENCE_PACK.exists():
        for p in (SILENCE_PACK / "02_问题片段").glob("*.mp3"):
            shutil.copy2(p, dirs["06_音频片段"] / p.name)
    cut(RUNS["ko"][1] / "audio" / "task_0040.mp3", 0, 60,
        dirs["06_音频片段"] / "韩语_task0040_前60s_含1757字超长段.mp3")

    # README
    n_seg_anom = len(anomalies)
    n_long = sum(1 for a in anomalies if a["flag_long"])
    n_hi = sum(1 for a in anomalies if a["flag_rate_hi"])
    n_lo = sum(1 for a in anomalies if a["flag_rate_lo"])
    R = []
    A = R.append
    A("# metadata（切句后结果）开发分析包 — Higgs TTS v3 日/韩 10 并发压测")
    A("")
    A("> **结论摘要**：文本口径（输入文案 ↔ 返回 metadata 文本）**完全一致、0 缺失**；")
    A("> 但 **metadata 的分段与时间轴存在系统性异常**，且**音频与 metadata 文本不匹配**：")
    A("> 长段被合并不切（最长 1757 字）、段时长与文本量严重不符（0.33 ~ 277 字/秒，正常 5~9）、")
    A("> 部分长段在音频中**只念出约 20%**，个别段落为 **81.64s 固定时长的静默占位**。")
    A("")
    A("## 一、现象与证据链")
    A("")
    A("| # | 现象 | 证据 | 数据位置 |")
    A("|---|---|---|---|")
    A(f"| 1 | **切句接口不支持日/韩语** | `POST /sentence_spliter` 返回 "
      f"`{{\"code\":1,\"msg\":\"不支持的语言: ja\"}}` / `ko`（英语对照组正常） | "
      f"`05_汇总分析/splitter_api_evidence.json` |")
    A(f"| 2 | **超长段**：日语最长 659 字、韩语最长 1757 字（正常中位 42 字） | "
      f"本包共导出异常段 {n_seg_anom} 条，其中超长段（>{LONG_CHARS} 字）**{n_long}** 条 | "
      f"`03_段级明细CSV/`、`05_汇总分析/segment_anomalies_all.csv` |")
    A(f"| 3 | **不可能语速**：段时长与文本量不符 | 语速 >{RATE_HI} 字/秒 **{n_hi}** 条"
      f"（最高 277 字/秒）；<{RATE_LO} 字/秒 **{n_lo}** 条 | 同上（`chars_per_s` 列） |")
    A(f"| 4 | **静默占位段**：时长恰为 **81.64s** 且音频近乎无声 | 日语 0035（26 字/81.64s）、"
      f"韩语 0044（1739 字/81.64s），两语种时长完全相同 | `01_metadata原始/`、"
      f"`06_音频片段/`、`07_ASR证据/` |")
    A(f"| 5 | **长段内容在音频中大量缺失** | 韩语 0040 前 60s：参考文本含 1757 字超长段，"
      f"ASR 实际只识别出约 20%（删除率 **80.03%**）；同批 180s 正常窗口删除率仅 0~3.7% | "
      f"`05_汇总分析/asr_evidence.json`、`07_ASR证据/ko_task0040_*.txt` |")
    A(f"| 6 | **整段核查（决定性证据）** | 韩语 0040 **整段 475s 转写**：原文 3,962 字（去空白）、"
      f"ASR 识别 2,593 字 → **缺失 1,369 字（34.55%）**；缺失集中在 **idx=1 那个 1328 字的超长段**"
      f"（**88% 未念出**，其时间轴仅 6.33s = 209.6 字/秒）；其余正常段缺失仅 ~5~11%（ASR 噪声量级） | "
      f"`05_汇总分析/asr_evidence.json`、`05_汇总分析/audio_missing_locate_ko0040.txt` |")
    A(f"| 7 | **第二个整段复现** | 韩语 0071 **整段 356s 转写**：原文 3,896 字、ASR 识别 2,105 字 → "
      f"**缺失 1,791 字（45.97%）**；三个超长段分别丢失 **90% / 89% / 76%**（idx=13 906字、"
      f"idx=20 444字、idx=2 341字），正常段仅 4~10% | `05_汇总分析/audio_missing_locate_ko0071.txt` |")
    A("")
    A("### 1.1 影响范围量化（全 224 个任务）")
    A("")
    A("| 语种 | 任务数 | 语速中位 | 语速 > 基线×1.5 | 估算音频缺口 >20% | 含超长段(>200字) | 含静默空洞 |")
    A("|---|---:|---:|---|---:|---:|---:|")
    for lang in ("ja", "ko"):
        rs = [r for r in task_rows if r["lang"] == lang]
        base = rate_all[lang]
        fast = [r for r in rs if (r["chars_per_s"] or 0) > base * 1.5]
        miss = [r for r in rs if r["est_missing_ratio"] > 0.2]
        longt = [r for r in rs if r["n_seg_gt200chars"] > 0]
        sil = [r for r in rs if r["is_silent_gap_task"]]
        fmt = lambda lst, key: ("—" if not lst else
                                ", ".join(str(r["seq"]) for r in sorted(lst, key=key)[:8])
                                + ("…" if len(lst) > 8 else ""))
        A(f"| {RUNS[lang][0]} | {len(rs)} | {base:.2f} 字/秒 | {len(fast)} 个"
          f"（{fmt(fast, lambda x: -x['chars_per_s'])}） |"
          f" **{len(miss)} 个**（{fmt(miss, lambda x: -x['est_missing_ratio'])}） |"
          f" {len(longt)} 个 | {len(sil)} 个 |")
    A("")
    A("> `est_missing_ratio` = 1 − (音频时长 − 已知静默) ÷ (文本字数 ÷ 该语种语速中位)，"
      "为**估算值**。已用两次整段 ASR 验证其可信度：韩语 0040 估算 28.9% / 实测 **34.55%**；"
      "韩语 0071 估算 46.8% / 实测 **45.97%** —— 同一量级，可用于圈定范围。")
    A("")
    A("## 二、可疑环节（建议开发按此顺序排查）")
    A("")
    A("```")
    A("输入 read_content（单段落 ~5200 字）")
    A("   ↓  ① 切句/分段：服务端切句接口不支持 ja/ko → 走降级/兜底切句")
    A("   ↓     症状：产出超长段（最长 1757 字，占 3.2% 段），未按句切分")
    A("   ↓  ② 合成：超长段一次性送 TTS")
    A("   ↓     症状：只合成出前一部分（实测前 60s 仅念出约 20%），其余被丢弃或跳读")
    A("   ↓  ③ 时间轴：异常段的 startMs/endMs 与文本量不匹配")
    A("   ↓     症状：出现 277 字/秒（时间远不够）与 81.64s（固定时长静默占位）两种极端")
    A("   ↓  ④ metadata 汇总：文本仍按原样拼接 → 文本口径 100% 一致，掩盖了音频缺失")
    A("```")
    A("")
    A("**要点**：`metadata` 的文本来自切句结果，**文本完整不代表音频完整**——")
    A("这正是本次「文本口径 0 缺失、音频却缺内容」的原因。")
    A("")
    A("## 三、复现步骤")
    A("")
    A("1. 取 `02_输入原文/<语种>/task_XXXX.txt`（即下发的 `read_content`）")
    A("2. 走一次完整链路（`POST /Video/CreateUniversalTransparent`，`taskType=74`，"
      "`model=higgs`，日语 `lang=9/Japanese_female`，韩语 `lang=14/Korean_female`）")
    A("3. 对照 `01_metadata原始/<语种>/task_XXXX.json` 的段数与时长，并听 `06_音频片段/`")
    A("4. 用 `POST /sentence_spliter` 以 `language_code=ja|ko` 复现「不支持的语言」")
    A("")
    A("## 四、待开发确认的问题")
    A("")
    A("1. 日/韩链路的切句**实际走的是哪个实现**（API？换行符？其它模型）？为何会产生 1757 字的单段？")
    A("2. 超长段送 TTS 时是否有长度上限/分片逻辑？超出部分是否被**静默丢弃**（实测前 60s 仅念出约 20%）？")
    A("3. **81.64s** 这个时长从何而来（固定超时/占位常量）？为何文本仍保留在 metadata？")
    A("4. 为何同一段的 `chars_per_s` 会出现 0.33 与 277 两个极端（时间轴分配算法）？")
    A("5. 能否在返回前增加校验：`段时长 × 正常语速` 与 `段字数` 相差过大即报错/重试？")
    A("")
    A("## 五、数据字典")
    A("")
    A("| 字段 | 含义 |")
    A("|---|---|")
    A("| `seg_index` | 正文段序号（从 0，已排除 `paraIndex=-1` 的标题段） |")
    A("| `paraIndex` | 服务端段号；**单段落输入下恒为 0**，多段落输入才递增 |")
    A("| `startMs/endMs` | 该段在音频中的起止时间（毫秒） |")
    A("| `dur_s` | 段时长（秒） |")
    A("| `chars` | 该段文本字符数（去首尾空白） |")
    A("| `chars_per_s` | 语速代理指标 = chars / dur_s（正常 5~9；>15 时间不够，<2 疑似静默） |")
    A("| `startOffset/endOffset` | 段内字符偏移（累计），可用于核对文本是否连续、有无缺口 |")
    A("| `flag_long / flag_rate_hi / flag_rate_lo / flag_dur_gt20s` | 四类异常标记（1=命中） |")
    A("")
    A("## 六、包内文件")
    A("")
    A("| 目录 | 内容 |")
    A("|---|---|")
    A(f"| `01_metadata原始/` | 样本任务接口原样返回的 metadata JSON（未做任何修改）："
      f"日语 {len(FOCUS['ja'])} 个、韩语 {len(FOCUS['ko'])} 个 |")
    A(f"| `02_输入原文/` | 对应的下发文案（read_content） |")
    A(f"| `03_段级明细CSV/` | 每个样本任务的逐段明细（可直接 Excel 排序/筛选） |")
    A(f"| `04_字幕SRT/` | 由 metadata 派生的字幕 |")
    A(f"| `05_汇总分析/` | `segment_anomalies_all.csv`（全量异常段）、`task_rate_summary.csv`"
      f"（全任务语速/段长汇总）、`splitter_api_evidence.json`（切句接口实测）、`asr_evidence.json` |")
    A(f"| `06_音频片段/` | 静默段片段 + 韩语 0040 前 60s（含 1757 字超长段） |")
    A(f"| `07_ASR证据/` | 参考文本与 ASR 实际识别文本，逐条可对照 |")
    A("")
    A("> 数据范围：2026-09-24 两个批次（日语 94 任务、韩语 130 任务），测试环境 "
      "`https://ai-main-none-dev.changdu.ltd`；异常段汇总覆盖全部任务，样本任务为异常代表 + 正常对照。")
    A("")
    (PACK / "README.md").write_text("\n".join(R), encoding="utf-8")

    print(f"\n[OK] 开发分析包：{PACK}")
    for k, d in sorted(dirs.items()):
        n = len(list(d.rglob("*")))
        print(f"  {k}/  {n} 项")
    print(f"  异常段 {n_seg_anom} 条（超长 {n_long}｜高语速 {n_hi}｜低语速 {n_lo}）")
    print(f"  README.md")


if __name__ == "__main__":
    main()
