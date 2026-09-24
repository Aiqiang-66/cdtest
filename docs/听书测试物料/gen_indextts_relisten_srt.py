# -*- coding: utf-8 -*-
"""按源文本 + 音频时长估算生成 SRT（IndexTTS 二次听测）。"""
import json
import re
from pathlib import Path

import pysbd
import soundfile as sf

BASE = Path(r"D:\python\dmx\cdtest\docs\听书测试物料")
RESULT = BASE / "mp3" / "IndexTTS-2.5二次听测_0824" / "relisten_results.json"
TXT_DIR = BASE / "txt文本"
OUT = BASE / "mp3" / "IndexTTS-2.5二次听测_0824"

MARKERS = {
    "英语": re.compile(r"^=== Chapter"),
    "西语": re.compile(r"^=== Capítulo"),
}
FILES = {
    "英语": "XR3 - EN.txt",
    "西语": "XR3 - SP.txt",
}
LANGS = {"英语": "en", "西语": "es"}


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


def fmt_ms(ms):
    ms = max(0, int(ms))
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    msec = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{msec:03d}"


def make_srt(sentences, duration):
    total_chars = sum(len(s) for s in sentences) or 1
    lines = []
    cur = 0.0
    for idx, sent in enumerate(sentences, 1):
        frac = len(sent) / total_chars
        start = cur
        end = min(duration, start + frac * duration)
        if end <= start:
            end = start + 0.2
        lines.append(str(idx))
        lines.append(f"{fmt_ms(start*1000)} --> {fmt_ms(end*1000)}")
        lines.append(sent.strip())
        lines.append("")
        cur = end
    return "\n".join(lines)


def main():
    results = json.loads(RESULT.read_text(encoding="utf-8"))
    seg = {"英语": pysbd.Segmenter(language="en", clean=False),
           "西语": pysbd.Segmenter(language="es", clean=False)}
    count = 0
    for r in results:
        lang = r["lang"]
        ch = r["chapter"]
        label = f"{lang}_XR3_Ch{ch}"
        chapters = split_chapters(FILES[lang], MARKERS[lang])
        content = chapters[ch - 1][1]
        sentences = [s.strip() for s in seg[lang].segment(content) if s.strip()]
        audio = OUT / f"{label}.wav"
        info = sf.info(str(audio))
        duration = info.frames / info.samplerate
        srt = make_srt(sentences, duration)
        out = OUT / f"{label}.srt"
        out.write_text(srt, encoding="utf-8")
        count += 1
        print(label, len(sentences), "sentences", f"{duration:.1f}s", flush=True)
    print("generated srt:", count, flush=True)


if __name__ == "__main__":
    main()