# -*- coding: utf-8 -*-
r"""日/韩压测音频 —— M3 漏词复核（faster-whisper large-v3，CPU int8）。

口径说明（技能 Phase 3/6/8）：
  **判定漏文案只看文本口径（M1）**；ASR 口径含识别误差，本脚本结论**仅供参考/复核**。
  非英语语种必须用 large-v3（base 会把 ASR 误差误判成 TTS 漏词）。
  本机为 CPU-only（torch 2.7.1+cpu），故按「音频前 N 秒窗口」抽样转写，
  参考文本取该窗口内 metadata 段文本拼接（与音频严格对齐），计算：
    日语 → CER（字级）；韩语 → WER（词级）＋ CER 参考。

产物：<批次目录>/analysis/asr_m3.json、asr_m3.md、asr/<seq>_{asr,ref}.txt

用法：
  & "D:\python\python.exe" docs\听书测试物料\asr_accuracy_ja_ko_largev3_0924.py --lang both --samples 3 --window 180
"""
import argparse
import difflib
import json
import re
import time
import unicodedata
from pathlib import Path

import av
import numpy as np

MP3_ROOT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3")
LANGS = {
    "ja": ("日语", MP3_ROOT / "Higgs_日语_10并发30分钟_0924", "ja"),
    "ko": ("韩语", MP3_ROOT / "Higgs_韩语_10并发30分钟_0924", "ko"),
}
MODEL_DIR = Path(r"D:\python\dmx\cdtest\tools\whisper_models\models--Systran--faster-whisper-large-v3\snapshots\large-v3")

_EDGE = re.compile(r"^[^\w']+|[^\w']+$")
_PUNCT = re.compile(r"[^\w\u3040-\u30ff\u4e00-\u9fff\uac00-\ud7af]", re.UNICODE)


def char_tokens(s):
    s = unicodedata.normalize("NFKC", s)
    s = _PUNCT.sub("", s)
    return [c for c in s if not c.isspace()]


def word_tokens(s):
    s = unicodedata.normalize("NFKC", s)
    out = []
    for w in s.split():
        w = _EDGE.sub("", w).lower()
        if w:
            out.append(w)
    return out


def err_stats(ref, hyp):
    """返回 (替换, 删除, 插入, 命中, 相似度)"""
    sm = difflib.SequenceMatcher(a=ref, b=hyp, autojunk=False)
    sub = dele = ins = hit = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            hit += i2 - i1
        elif tag == "replace":
            sub += max(i2 - i1, j2 - j1)
        elif tag == "delete":
            dele += i2 - i1
        elif tag == "insert":
            ins += j2 - j1
    return sub, dele, ins, hit, sm.ratio()


def load_window(run_dir, seq, start_s, end_s):
    """→ (ref_text, start_ms, end_ms)：只取**完整落在窗口内**的 metadata 正文段。

    ⚠️ 不能用「与窗口有重叠」的段：分段较粗时（如韩语某任务仅 42 段），
    跨窗口的长段会把窗口外的整段文本算进参考，凭空造出大量"删除"（实测伪阳性）。
    只取完整段后，窗口终点取这些段的最大 endMs，参考与音频严格同区间。
    """
    segs = json.loads((run_dir / "meta" / f"task_{seq:04d}.json").read_text(encoding="utf-8"))
    body = [s for s in segs if s.get("paraIndex", -1) >= 0 and (s.get("text") or "").strip()]
    a_ms, b_ms = start_s * 1000, end_s * 1000
    picked = [s for s in body if s.get("startMs", 0) >= a_ms and s.get("endMs", 0) <= b_ms]
    if not picked:
        picked = [s for s in body if s.get("startMs", 0) >= a_ms][:1] or body[:1]
    ref = " ".join(s["text"].strip() for s in picked)
    return ref, int(min(s.get("startMs", 0) for s in picked)), int(max(s.get("endMs", 0) for s in picked))


def decode_window(mp3_path, start_ms, end_ms):
    with av.open(str(mp3_path)) as container:
        stream = container.streams.audio[0]
        sr = stream.codec_context.sample_rate
        chunks = []
        for frame in container.decode(stream):
            if frame.pts is None:
                continue
            t_ms = float(frame.pts * frame.time_base) * 1000
            if t_ms + (frame.samples / sr * 1000) < start_ms:
                continue
            if t_ms > end_ms:
                break
            arr = frame.to_ndarray()
            if arr.ndim > 1:
                arr = arr.mean(axis=0)
            chunks.append(arr.astype(np.float32))
    data = np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)
    if data.size == 0:
        return data, sr
    if sr != 16000:
        from scipy.signal import resample_poly
        from math import gcd
        g = gcd(int(sr), 16000)
        data = resample_poly(data, 16000 // g, int(sr) // g).astype(np.float32)
    return data, 16000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="both", choices=["ja", "ko", "both"])
    ap.add_argument("--samples", type=int, default=3, help="每语种抽样条数")
    ap.add_argument("--window", type=int, default=180, help="每条转写的音频窗口秒数")
    ap.add_argument("--start", type=int, default=0, help="窗口起始秒（默认从头开始）")
    ap.add_argument("--seqs", default="", help="指定任务序号（逗号分隔），用于定点核查空洞等")
    ap.add_argument("--out", default="asr_m3", help="输出文件名前缀（避免定点核查覆盖抽样结果）")
    ap.add_argument("--run-dir", default="", help="指定批次目录（默认识别 LANGS 内置的两个批次）")
    args = ap.parse_args()

    runs = dict(LANGS)
    if args.run_dir:
        lang0 = args.lang if args.lang != "both" else "ja"
        runs = {lang0: (LANGS[lang0][0], Path(args.run_dir), LANGS[lang0][2])}

    from faster_whisper import WhisperModel

    t_load = time.time()
    print(f"[加载模型] {MODEL_DIR}")
    model = WhisperModel(str(MODEL_DIR), device="cpu", compute_type="int8")
    load_s = time.time() - t_load
    print(f"[加载完成] {load_s:.1f}s｜device=cpu｜compute_type=int8")

    langs = sorted(runs) if args.lang == "both" else [args.lang]
    result = {"model": str(MODEL_DIR), "device": "cpu", "compute_type": "int8",
              "load_s": round(load_s, 1), "window_s": args.window, "samples_per_lang": args.samples,
              "langs": {}}

    md = [f"# 日/韩压测音频 —— M3 漏词复核（faster-whisper large-v3 / CPU int8，自动生成）", "",
          f"- 模型：`{MODEL_DIR}`（large-v3）｜device=cpu｜compute_type=int8｜加载 {load_s:.1f}s",
          f"- 抽样：每语种 {args.samples} 条，各转写**音频前 {args.window}s**；参考文本取该窗口内 metadata 正文段拼接",
          f"- ⚠️ ASR 口径含识别误差，**判定文案丢失以 M1 文本口径为准**，本表仅供复核", ""]

    for lang in langs:
        cn, run_dir, wlang = runs[lang]
        audio_files = sorted((run_dir / "audio").glob("task_*.mp3"))
        if not audio_files:
            print(f"[{cn}] 无音频文件，跳过")
            continue
        seqs = [int(f.stem.split("_")[1]) for f in audio_files]
        if args.seqs:
            wanted = [int(x) for x in args.seqs.split(",") if x.strip()]
            seqs = [s for s in wanted if s in set(seqs)]
        elif len(seqs) > args.samples:
            step = len(seqs) / args.samples
            seqs = [seqs[int(i * step)] for i in range(args.samples)]

        rows = []
        for seq in seqs:
            mp3 = run_dir / "audio" / f"task_{seq:04d}.mp3"
            start_s, end_s = args.start, args.start + args.window
            ref_text, ref_a_ms, ref_b_ms = load_window(run_dir, seq, start_s, end_s)
            src_text = (run_dir / "src" / f"task_{seq:04d}.txt").read_text(encoding="utf-8")
            t0 = time.time()
            audio, sr = decode_window(mp3, start_s * 1000, end_s * 1000)
            audio_s = len(audio) / sr
            segments, info = model.transcribe(audio, language=wlang, beam_size=1,
                                              vad_filter=False, condition_on_previous_text=False)
            hyp = " ".join(s.text.strip() for s in segments)
            wall = time.time() - t0

            ref_c, hyp_c = char_tokens(ref_text), char_tokens(hyp)
            ref_w, hyp_w = word_tokens(ref_text), word_tokens(hyp)
            sub_c, del_c, ins_c, hit_c, ratio_c = err_stats(ref_c, hyp_c)
            sub_w, del_w, ins_w, hit_w, ratio_w = err_stats(ref_w, hyp_w)
            row = {
                "seq": seq, "taskId": None, "window": f"{start_s}~{end_s}s",
                "ref_window": f"{ref_a_ms/1000:.1f}~{ref_b_ms/1000:.1f}s",
                "audio_s": round(audio_s, 1), "wall_s": round(wall, 1),
                "rtf": round(wall / audio_s, 3) if audio_s else None,
                "src_chars": len(src_text), "ref_chars": len(ref_c), "hyp_chars": len(hyp_c),
                "cer": round((sub_c + del_c + ins_c) / max(1, len(ref_c)), 4),
                "cer_deletion": round(del_c / max(1, len(ref_c)), 4),
                "cer_substitution": round(sub_c / max(1, len(ref_c)), 4),
                "cer_insertion": round(ins_c / max(1, len(ref_c)), 4),
                "cer_similarity": round(ratio_c, 4),
                "wer": round((sub_w + del_w + ins_w) / max(1, len(ref_w)), 4) if ref_w else None,
                "wer_deletion": round(del_w / max(1, len(ref_w)), 4) if ref_w else None,
                "wer_similarity": round(ratio_w, 4) if ref_w else None,
                "hyp_head": hyp[:200], "ref_head": ref_text[:200],
            }
            rows.append(row)
            asr_dir = run_dir / "analysis" / "asr"
            asr_dir.mkdir(parents=True, exist_ok=True)
            (asr_dir / f"task_{seq:04d}_ref.txt").write_text(ref_text, encoding="utf-8")
            (asr_dir / f"task_{seq:04d}_asr.txt").write_text(hyp, encoding="utf-8")
            print(f"[{cn}] seq={seq} 音频 {audio_s:.0f}s 转写 {wall:.0f}s (RTF {row['rtf']}) "
                  f"CER {row['cer']*100:.2f}% 删除 {row['cer_deletion']*100:.2f}%｜WER {row['wer']}")

        n = len(rows)
        agg = {
            "samples": n,
            "cer_avg": round(sum(r["cer"] for r in rows) / n, 4) if n else None,
            "cer_deletion_avg": round(sum(r["cer_deletion"] for r in rows) / n, 4) if n else None,
            "cer_worst": max([r["cer"] for r in rows], default=None),
            "wer_avg": round(sum(r["wer"] for r in rows if r["wer"] is not None) / n, 4) if n else None,
            "wer_deletion_avg": round(sum(r["wer_deletion"] for r in rows if r["wer_deletion"] is not None) / n, 4) if n else None,
            "rtf_avg": round(sum(r["rtf"] for r in rows) / n, 3) if n else None,
            "rows": rows,
        }
        result["langs"][lang] = agg
        md += [f"### {cn}（{lang}）", "",
               f"- 抽样 {n} 条｜CER 平均 **{agg['cer_avg']*100:.2f}%**（删除率 {agg['cer_deletion_avg']*100:.2f}%，"
               f"最差 {agg['cer_worst']*100:.2f}%）｜WER 平均 "
               f"{(agg['wer_avg'] or 0)*100:.2f}%（删除率 {(agg['wer_deletion_avg'] or 0)*100:.2f}%）"
               f"｜平均 RTF {agg['rtf_avg']}", "",
               "| seq | 窗口 | 音频(s) | 转写(s) | RTF | 参考字符 | ASR字符 | CER | 删除率 | WER | 相似度(字级) |",
               "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for r in rows:
            md.append(f"| {r['seq']} | {r['window']} | {r['audio_s']} | {r['wall_s']} | {r['rtf']} | {r['ref_chars']} |"
                      f" {r['hyp_chars']} | {r['cer']*100:.2f}% | {r['cer_deletion']*100:.2f}% | {r['wer']} |"
                      f" {r['cer_similarity']} |")
        md.append("")

    out_dir = MP3_ROOT / "analysis_ja_ko_asr_m3"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{args.out}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / f"{args.out}.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\n[OK] {out_dir / (args.out + '.json')}")


if __name__ == "__main__":
    main()
