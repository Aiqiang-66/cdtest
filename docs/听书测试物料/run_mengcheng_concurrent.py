# -*- coding: utf-8 -*-
"""梦成接口 同并发对比：6 章同时下发，测每章从下发到完成的耗时。"""
import json
import re
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from gradio_client import Client, handle_file

BASE_URL = "http://192.168.21.184:11603/"
TXT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\txt文本")
OUT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\梦成接口_XR3_英西")

CONFIG = [
    ("英语", "XR3 - EN.txt", "EN", 2, [1, 2, 3]),
    ("西语", "XR3 - SP.txt", "ES", 4, [1, 2, 3]),
]


def split_chapters(fname, marker):
    text = (TXT / fname).read_text(encoding="utf-8")
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
        emo_text="", emo_random=False,
        max_text_tokens_per_segment=120, duration_factor=1,
        param_18=True, param_19=0.8, param_20=30, param_21=0.8,
        param_22=0, param_23=3, param_24=10, param_25=1500,
        api_name="/gen_single",
    )


def main():
    client = Client(BASE_URL, verbose=False)
    voices = {}
    tasks = []

    for name, fname, lang, ex, chapters in CONFIG:
        r = client.predict(example=ex, api_name="/on_example_click")
        prompt = r[0]["value"]
        voices[name] = (lang, prompt)
        chs = split_chapters(fname, re.compile(r"^==="))
        for i in chapters:
            title, content = chs[i - 1]
            tasks.append({
                "lang": name, "chapter": i, "title": title,
                "chars": len(content), "content": content,
                "prompt": prompt, "lang_code": lang,
            })

    print(f"共 {len(tasks)} 个任务并发下发...", flush=True)
    global_start = time.time()

    results = []
    def run(t):
        t0 = time.time()
        rec = dict(lang=t["lang"], chapter=t["chapter"], chars=t["chars"],
                   ok=False, elapsed=None, error=None, wall_from_global=None)
        try:
            synth(client, t["prompt"], t["content"], t["lang_code"])
            rec["ok"] = True
        except Exception as e:
            rec["error"] = f"{type(e).__name__}: {e}"
        rec["elapsed"] = round(time.time() - t0, 2)
        rec["wall_from_global"] = round(time.time() - global_start, 2)
        return rec

    with ThreadPoolExecutor(max_workers=len(tasks)) as ex:
        futs = [ex.submit(run, t) for t in tasks]
        for f in as_completed(futs):
            r = f.result()
            results.append(r)
            print(f"[{r['lang']} ch{r['chapter']}] {r['elapsed']}s (自全局起 {r['wall_from_global']}s) "
                  f"{'OK' if r['ok'] else 'FAIL ' + str(r['error'])[:120]}", flush=True)

    results.sort(key=lambda x: (x["lang"], x["chapter"]))
    out_json = OUT / "concurrent_results.json"
    out_json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n汇总（并发下发）:")
    for r in results:
        print(f"  {r['lang']} 第{r['chapter']}章: {r['chars']}字符, {r['elapsed']}s")
    print(f"\n已保存: {out_json}")


if __name__ == "__main__":
    main()