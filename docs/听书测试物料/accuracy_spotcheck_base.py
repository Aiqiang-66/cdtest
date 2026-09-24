# -*- coding: utf-8 -*-
"""Whisper 漏词/准确率核对（英语/西语抽查章节）。"""
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

MODEL_PATH = r"D:\python\dmx\cdtest\tools\whisper_models\models--Systran--faster-whisper-base\snapshots\d01c3014881c9c6f3133c182f3d2887eb6ca1c789a7538c5c007196857a0a6a9"
AUDIO_DIR = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\梦成接口_XR3_英西")
TXT_DIR = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\txt文本")
OUT_JSON = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\梦成接口_XR3_英西\accuracy_spotcheck_base.json")
OUT_PARTIAL = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\梦成接口_XR3_英西\accuracy_spotcheck_base_partial.json")

CONFIGS = [
    ("英语", "XR3 - EN.txt", re.compile(r"^=== Chapter"), "en", [1, 2, 3, 10, 14, 17]),
    ("西语", "XR3 - SP.txt", re.compile(r"^=== Capítulo"), "es", [1, 2, 3, 10, 14, 17]),
]

EN_CONTRACTIONS = {
    "can't": "cannot", "cannot": "cannot",
    "won't": "will not", "don't": "do not", "doesn't": "does not",
    "didn't": "did not", "isn't": "is not", "aren't": "are not",
    "wasn't": "was not", "weren't": "were not", "haven't": "have not",
    "hasn't": "has not", "hadn't": "had not", "wouldn't": "would not",
    "shouldn't": "should not", "couldn't": "could not", "mustn't": "must not",
    "it's": "it is", "that's": "that is", "what's": "what is",
    "who's": "who is", "here's": "here is", "there's": "there is",
    "he's": "he is", "she's": "she is", "i'm": "i am",
    "you're": "you are", "we're": "we are", "they're": "they are",
    "i'll": "i will", "you'll": "you will", "he'll": "he will",
    "she'll": "she will", "we'll": "we will", "they'll": "they will",
    "i've": "i have", "you've": "you have", "we've": "we have",
    "they've": "they have", "i'd": "i would", "you'd": "you would",
    "he'd": "he would", "she'd": "she would", "we'd": "we would",
    "they'd": "they would", "let's": "let us", "ma'am": "madam",
}


def split_chapters(fname, marker):
    text = (TXT_DIR / fname).read_text(encoding="utf-8")
    chapters = []
    cur_title = None
    cur_lines = []
    for ln in text.splitlines():
        if marker.match(ln):
            if cur_title is not None:
                chapters.append((cur_title, "\n".join(cur_lines).strip()))
            cur_title = ln.strip("=").strip()
            cur_lines = []
        else:
            cur_lines.append(ln)
    if cur_title is not None:
        chapters.append((cur_title, "\n".join(cur_lines).strip()))
    return chapters


def expand_en(text):
    # 按词边界替换常见缩写，避免误伤 don't 之类
    pattern = re.compile(r"\b(" + "|".join(re.escape(k) for k in sorted(EN_CONTRACTIONS, key=len, reverse=True)) + r")\b")
    return pattern.sub(lambda m: EN_CONTRACTIONS[m.group(1).lower()], text.lower())


def strip_accents(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s


def normalize_tokens(text, lang):
    t = text.lower()
    t = t.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    t = t.replace("\u2014", " ").replace("\u2013", " ").replace("\u2026", " ")
    if lang == "en":
        t = expand_en(t)
    # 仅保留拉丁字母/数字/撇号，其它（含标点、括号、引号）变空格
    t = re.sub(r"[^0-9a-zà-ÿ']+", " ", t, flags=re.UNICODE)
    t = t.replace("'", " ")
    t = strip_accents(t)
    toks = [tok for tok in t.split() if tok]
    return toks


def wer_alignment(ref, hyp):
    n, m = len(ref), len(hyp)
    if n == 0 and m == 0:
        return [], {"correct": 0, "substitutions": 0, "deletions": 0, "insertions": 0, "wer": 0.0,
                    "deletion_rate": 0.0, "insertion_rate": 0.0, "N": 0, "M": 0}
    D = np.empty((n + 1, m + 1), dtype=np.int32)
    D[0, :] = np.arange(m + 1, dtype=np.int32)
    D[:, 0] = np.arange(n + 1, dtype=np.int32)
    for i in range(1, n + 1):
        ri = ref[i - 1]
        row = D[i]
        prev = D[i - 1]
        for j in range(1, m + 1):
            sub = prev[j - 1] + (0 if ri == hyp[j - 1] else 1)
            dele = prev[j] + 1
            ins = row[j - 1] + 1
            row[j] = min(dele, ins, sub)
    ops = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            if D[i, j] == D[i - 1, j - 1] + cost:
                ops.append(("S" if cost else "C", i - 1, j - 1))
                i -= 1
                j -= 1
                continue
        if i > 0 and D[i, j] == D[i - 1, j] + 1:
            ops.append(("D", i - 1, None))
            i -= 1
        else:
            ops.append(("I", None, j - 1))
            j -= 1
    ops.reverse()
    stats = {
        "correct": sum(1 for op, _, _ in ops if op == "C"),
        "substitutions": sum(1 for op, _, _ in ops if op == "S"),
        "deletions": sum(1 for op, _, _ in ops if op == "D"),
        "insertions": sum(1 for op, _, _ in ops if op == "I"),
        "N": n,
        "M": m,
    }
    s, d, i_cnt = stats["substitutions"], stats["deletions"], stats["insertions"]
    stats["wer"] = round((s + d + i_cnt) / n, 6) if n else 0.0
    stats["deletion_rate"] = round(d / n, 6) if n else 0.0
    stats["insertion_rate"] = round(i_cnt / n, 6) if n else 0.0
    return ops, stats


def build_events(ref, hyp, ops, segs):
    # hyp 词到 segment 索引
    hyp_seg = []
    hyp_tokens = []
    for si, seg in enumerate(segs):
        toks = normalize_tokens(seg.text, "en" if False else seg.text and None)
    # 这里需要与 transcribe 返回的 hyp 一致，故单独函数处理
    return None


def transcribe_file(model, path, lang):
    t0 = time.time()
    segments_iter, info = model.transcribe(str(path), language=lang, beam_size=5, vad_filter=True)
    segs = list(segments_iter)
    elapsed = round(time.time() - t0, 2)
    hyp_tokens = []
    hyp_seg_idx = []
    for idx, seg in enumerate(segs):
        toks = normalize_tokens(seg.text, lang)
        hyp_tokens.extend(toks)
        hyp_seg_idx.extend([idx] * len(toks))
    return segs, info, hyp_tokens, hyp_seg_idx, elapsed


def make_events(ref_tokens, hyp_tokens, hyp_seg_idx, ops, segs):
    events = []
    for op, ri, hi in ops:
        if op == "C":
            continue
        if op == "S":
            seg = segs[hyp_seg_idx[hi]]
            events.append({"type": "S", "ref": ref_tokens[ri], "hyp": hyp_tokens[hi],
                           "start": round(seg.start, 2), "end": round(seg.end, 2)})
        elif op == "D":
            # 最近邻 ASR 词所在 segment
            prev_hi = next_hi = None
            # 向后找
            k = ops.index((op, ri, hi))  # 太慢，改在下面循环里先算
            events.append({"type": "D", "ref": ref_tokens[ri], "hyp": None,
                           "start": None, "end": None})
        elif op == "I":
            seg = segs[hyp_seg_idx[hi]]
            events.append({"type": "I", "ref": None, "hyp": hyp_tokens[hi],
                           "start": round(seg.start, 2), "end": round(seg.end, 2)})
    return events


def main():
    print("loading model ...", flush=True)
    t0 = time.time()
    model = WhisperModel(MODEL_PATH, device="cpu", compute_type="int8")
    print("model loaded", round(time.time() - t0, 1), "s", flush=True)

    all_rows = []
    for lang_name, fname, marker, lang_code, idxs in CONFIGS:
        chapters = split_chapters(fname, marker)
        print(f"\n===== {lang_name} ({fname}) chapters={len(chapters)} =====", flush=True)
        for ci in idxs:
            title, content = chapters[ci - 1]
            label = f"{lang_name}_XR3_Ch{ci}"
            audio = AUDIO_DIR / f"{label}.wav"
            if not audio.exists():
                print("MISSING", label, flush=True)
                continue
            ref_tokens = normalize_tokens(content, lang_code)
            segs, info, hyp_tokens, hyp_seg_idx, elapsed = transcribe_file(model, audio, lang_code)
            ops, stats = wer_alignment(ref_tokens, hyp_tokens)

            # 组装事件并映射时间
            events = []
            prev_hi = None
            # 先构造一个方便找邻近 hyp 的 op 序列
            op_list = ops
            for pos, (op, ri, hi) in enumerate(op_list):
                if op == "C":
                    prev_hi = hi
                    continue
                if op == "S":
                    seg = segs[hyp_seg_idx[hi]]
                    events.append({"type": "S", "ref": ref_tokens[ri], "hyp": hyp_tokens[hi],
                                   "start": round(seg.start, 2), "end": round(seg.end, 2)})
                    prev_hi = hi
                elif op == "D":
                    # 找最近邻 ASR 词索引
                    near_hi = prev_hi
                    if near_hi is None:
                        for op2, ri2, hi2 in op_list[pos + 1:]:
                            if hi2 is not None:
                                near_hi = hi2
                                break
                    if near_hi is not None:
                        seg = segs[hyp_seg_idx[near_hi]]
                        start, end = round(seg.start, 2), round(seg.end, 2)
                    else:
                        start, end = 0.0, round(segs[-1].end, 2) if segs else 0.0
                    events.append({"type": "D", "ref": ref_tokens[ri], "hyp": None,
                                   "start": start, "end": end})
                elif op == "I":
                    seg = segs[hyp_seg_idx[hi]]
                    events.append({"type": "I", "ref": None, "hyp": hyp_tokens[hi],
                                   "start": round(seg.start, 2), "end": round(seg.end, 2)})
                    prev_hi = hi

            # 连续漏词合并成窗口
            missing_windows = []
            cur = []
            for e in events:
                if e["type"] == "D":
                    if not cur:
                        cur = [e]
                    else:
                        # 与上一个时间窗间隔 <= 2s 视为同一片段
                        if e["start"] is not None and cur[-1]["end"] is not None and e["start"] - cur[-1]["end"] <= 2.0:
                            cur.append(e)
                        else:
                            missing_windows.append(cur)
                            cur = [e]
                else:
                    if cur:
                        missing_windows.append(cur)
                        cur = []
            if cur:
                missing_windows.append(cur)

            missing = []
            for grp in missing_windows:
                toks = [e["ref"] for e in grp]
                start = min(e["start"] for e in grp if e["start"] is not None) if any(e["start"] is not None for e in grp) else None
                end = max(e["end"] for e in grp if e["end"] is not None) if any(e["end"] is not None for e in grp) else None
                missing.append({"tokens": toks, "text": " ".join(toks), "start": start, "end": end})

            subs = [{"ref": e["ref"], "hyp": e["hyp"], "start": e["start"], "end": e["end"]} for e in events if e["type"] == "S"]
            ins = [{"hyp": e["hyp"], "start": e["start"], "end": e["end"]} for e in events if e["type"] == "I"]

            row = {
                "lang": lang_name, "chapter": ci, "title": title, "audio": str(audio),
                "lang_detected": info.language, "lang_prob": round(float(info.language_probability), 4),
                "transcribe_seconds": elapsed,
                "ref_words": stats["N"], "asr_words": stats["M"],
                "correct": stats["correct"], "substitutions": stats["substitutions"],
                "deletions": stats["deletions"], "insertions": stats["insertions"],
                "wer": stats["wer"], "deletion_rate": stats["deletion_rate"],
                "insertion_rate": stats["insertion_rate"],
                "missing_windows": missing,
                "substitutions_top": subs[:30],
                "insertions_top": ins[:30],
            }
            all_rows.append(row)
            OUT_PARTIAL.write_text(json.dumps(all_rows, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"{label}: WER={stats['wer']*100:.2f}% del={stats['deletion_rate']*100:.2f}% "
                  f"sub={stats['substitutions']} ins={stats['insertions']} ref={stats['N']} hyp={stats['M']} "
                  f"asr={elapsed:.1f}s", flush=True)

    OUT_JSON.write_text(json.dumps(all_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nSaved", OUT_JSON, flush=True)


if __name__ == "__main__":
    main()