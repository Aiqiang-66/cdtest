# -*- coding: utf-8 -*-
"""定位「音频缺失的文本区间」：整段 ASR 识别结果 vs 下发原文做字级对齐。

用法：
  & "D:\python\python.exe" docs\听书测试物料\_locate_audio_missing_0924.py ko 40

同时把报告落盘到 mp3/analysis_ja_ko_asr_m3/audio_missing_locate_<lang><seq>.txt
（供「开发分析包_metadata切句_0924」收录）。
"""
import difflib
import json
import sys
import unicodedata
from pathlib import Path

MP3 = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3")
OUT_DIR = MP3 / "analysis_ja_ko_asr_m3"
RUNS = {"ja": ("日语", MP3 / "Higgs_日语_10并发30分钟_0924"),
        "ko": ("韩语", MP3 / "Higgs_韩语_10并发30分钟_0924")}

REPORT = []


def emit(line=""):
    print(line, flush=True)
    REPORT.append(str(line))


def tok(s):
    s = unicodedata.normalize("NFKC", s)
    s = (s.replace("\u2019", "'").replace("\u2018", "'")
          .replace("\u201c", '"').replace("\u201d", '"'))
    return [c for c in s if not c.isspace()]


def main():
    args = sys.argv[1:]
    run_dir_override = None
    if "--run-dir" in args:
        i = args.index("--run-dir")
        run_dir_override = args[i + 1]
        del args[i:i + 2]
    lang = args[0] if args else "ko"
    seq = int(args[1]) if len(args) > 1 else 40
    cn, run = RUNS[lang]
    if run_dir_override:
        run = Path(run_dir_override)
    src = (run / "src" / f"task_{seq:04d}.txt").read_text(encoding="utf-8")
    asr_p = run / "analysis" / "asr" / f"task_{seq:04d}_asr.txt"
    asr = asr_p.read_text(encoding="utf-8") if asr_p.exists() else ""
    segs = json.loads((run / "meta" / f"task_{seq:04d}.json").read_text(encoding="utf-8"))
    body = [s for s in segs if s.get("paraIndex", -1) >= 0]

    st, at = tok(src), tok(asr)
    emit("=" * 100)
    emit(f"[{cn}] task_{seq:04d}｜原文 {len(st):,} 字（去空白）｜ASR 识别 {len(at):,} 字"
         f"｜缺口 {len(st)-len(at):,} 字（{100*(len(st)-len(at))/max(1,len(st)):.2f}%）")
    emit(f"数据来源：{asr_p}")
    sm = difflib.SequenceMatcher(a=st, b=at, autojunk=False)
    missing_runs = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("delete", "replace") and i2 - i1 > 0:
            missing_runs.append((i1, i2, "".join(st[i1:i2])))
    total = sum(b - a for a, b, _ in missing_runs)
    emit(f"连续缺失块 {len(missing_runs)} 个，合计 {total} 字（{100*total/max(1,len(st)):.2f}%）"
         f"｜相似度 {sm.ratio():.4f}")

    def seg_of(pos):
        acc = 0
        for i, s in enumerate(body):
            n = len(tok(s.get("text") or ""))
            if acc <= pos < acc + n:
                return i, s
            acc += n
        return None, None

    emit("")
    emit("缺失块明细（前 15 个，含所属 metadata 段）：")
    for a, b, txt in sorted(missing_runs, key=lambda x: -(x[1] - x[0]))[:15]:
        si, s = seg_of(a)
        extra = ""
        if s is not None:
            d = (s["endMs"] - s["startMs"]) / 1000
            n = len(tok(s.get("text") or ""))
            extra = f"｜所属段 idx={si} 段长 {n} 字/{d:.2f}s（{n/d if d else 0:.1f} 字/秒）"
        emit(f"  · 原文第 {a:,}~{b:,} 字，缺 {b-a} 字{extra}")
        emit(f"    缺失内容: {txt[:120]}")

    emit("")
    emit("按段统计缺失量（缺失最多的前 10 段）：")
    per = {}
    for a, b, txt in missing_runs:
        si, _ = seg_of(a)
        per[si] = per.get(si, 0) + (b - a)
    for si, n in sorted(per.items(), key=lambda x: -x[1])[:10]:
        if si is None:
            continue
        s = body[si]
        d = (s["endMs"] - s["startMs"]) / 1000
        L = len(tok(s.get("text") or ""))
        emit(f"  · idx={si} 缺 {n}/{L} 字（{100*n/max(1,L):.0f}%）｜段时长 {d:.2f}s｜"
             f"语速 {L/d if d else 0:.1f} 字/秒｜文本 {((s.get('text') or ''))[:60]!r}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tag = ("_" + Path(run_dir_override).name.split("_")[-1]) if run_dir_override else ""
    out = OUT_DIR / f"audio_missing_locate_{lang}{seq:04d}{tag}.txt"
    out.write_text("\n".join(REPORT) + "\n", encoding="utf-8")
    print(f"\n[OK] {out}")


if __name__ == "__main__":
    main()
