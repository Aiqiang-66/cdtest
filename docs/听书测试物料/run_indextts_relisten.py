# -*- coding: utf-8 -*-
"""IndexTTS-2.5 重新下发：XR3 英/西各 20 章，供人工二次听测。"""
import argparse
import json
import re
import shutil
import time
from pathlib import Path

from gradio_client import Client, handle_file

BASE_URL = "http://192.168.21.184:11603/"
TXT_DIR = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\txt文本")
OUT_DIR = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\IndexTTS-2.5二次听测_0824")
OUT_DIR.mkdir(parents=True, exist_ok=True)

LANGS = [
    ("英语", "XR3 - EN.txt", r"^=== Chapter", "EN", 2),
    ("西语", "XR3 - SP.txt", r"^=== Capítulo", "ES", 4),
]
CHAPTERS = list(range(1, 21))


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


def synth(client, prompt, text, lang):
    return client.predict(
        emo_control_method="Same as the voice reference",
        prompt=handle_file(prompt),
        text=text,
        lang_choice=lang,
        emo_ref_path=handle_file(prompt),
        emo_weight=0.65,
        vec1=0, vec2=0, vec3=0, vec4=0, vec5=0, vec6=0, vec7=0, vec8=0,
        emo_text="",
        emo_random=False,
        max_text_tokens_per_segment=120,
        duration_factor=1,
        param_18=True, param_19=0.8, param_20=30, param_21=0.8,
        param_22=0, param_23=3, param_24=10, param_25=1500,
        api_name="/gen_single",
    )


def main():
    client = Client(BASE_URL, verbose=False)
    voices = {}
    for name, fname, marker, lang, ex in LANGS:
        r = client.predict(example=ex, api_name="/on_example_click")
        voices[name] = (lang, r[0]["value"])
        print(f"[音色] {name}: {r[0]['value']} lang={lang}", flush=True)

    results = []
    ok_count = 0
    for name, fname, marker, lang, ex in LANGS:
        chapters = split_chapters(fname, re.compile(marker))
        print(f"\n===== {name} ({fname}) 共 {len(chapters)} 章，选测 {len(CHAPTERS)} 章 =====", flush=True)
        for i in CHAPTERS:
            title, content = chapters[i - 1]
            label = f"{name}_XR3_Ch{i}"
            chars = len(content)
            print(f"[开始] {label} ({chars} 字符) ...", flush=True)
            t0 = time.time()
            rec = {"lang": name, "chapter": i, "title": title, "chars": chars,
                   "ok": False, "elapsed": None, "audio": None, "error": None}
            try:
                out = synth(client, voices[name][1], content, lang)
                elapsed = time.time() - t0
                src = out["value"] if isinstance(out, dict) else out
                dst = None
                if src and Path(src).exists():
                    dst = OUT_DIR / f"{label}.wav"
                    shutil.copyfile(src, dst)
                rec.update({"ok": True, "elapsed": round(elapsed, 2), "audio": str(dst) if dst else str(src)})
                ok_count += 1
                print(f"[完成] {label}: {elapsed:.2f}s", flush=True)
            except Exception as e:
                elapsed = time.time() - t0
                rec.update({"elapsed": round(elapsed, 2), "error": f"{type(e).__name__}: {e}"})
                print(f"[失败] {label}: {elapsed:.2f}s {type(e).__name__} {str(e)[:300]}", flush=True)
            results.append(rec)

    out_json = OUT_DIR / "relisten_results.json"
    out_json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n成功 {ok_count}/{len(results)}，结果已保存: {out_json}", flush=True)


if __name__ == "__main__":
    main()