# -*- coding: utf-8 -*-
"""
梦成网站(IndexTTS-2.5) XR3 英语/西语 各20章 响应时间测试。
直接通过 gradio_client 调用 /gen_single，串行执行，逐章记录耗时并保存音频。
"""
import argparse
import json
import re
import shutil
import time
from pathlib import Path

from gradio_client import Client, handle_file

BASE_URL = "http://192.168.21.184:11603/"
TXT_DIR = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\txt文本")
OUT_DIR = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\梦成接口_XR3_英西")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 语种配置：语言名、文件、章节正则、lang_choice、示例索引
LANGS = [
    ("英语", "XR3 - EN.txt", r"^=== Chapter", "EN", 2),
    ("西语", "XR3 - SP.txt", r"^=== Capítulo", "ES", 4),
]


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
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapters", default="1-20", help="章节区间，如 1-20 或 1,3,5")
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 章（0=全部）")
    args = ap.parse_args()

    client = Client(BASE_URL, verbose=False)

    # 取音色参考
    voices = {}
    for name, fname, marker, lang, ex in LANGS:
        r = client.predict(example=ex, api_name="/on_example_click")
        voices[name] = (lang, r[0]["value"])
        print(f"[音色] {name}: {r[0]['value']} lang={lang}")

    results = []
    for name, fname, marker, lang, ex in LANGS:
        chapters = split_chapters(fname, re.compile(marker))
        idxs = parse_chapters(args.chapters, len(chapters))
        if args.limit:
            idxs = idxs[: args.limit]
        print(f"\n===== {name} ({fname}) 共 {len(chapters)} 章，选测 {len(idxs)} 章 =====")
        for i in idxs:
            title, content = chapters[i - 1]
            label = f"{name}_XR3_Ch{i}"
            chars = len(content)
            print(f"[开始] {label} ({chars} 字符) ...", flush=True)
            t0 = time.time()
            rec = {
                "lang": name, "chapter": i, "title": title, "chars": chars,
                "ok": False, "elapsed": None, "audio": None, "error": None,
            }
            try:
                out = synth(client, voices[name][1], content, lang)
                elapsed = time.time() - t0
                src = out["value"] if isinstance(out, dict) else out
                dst = None
                if src and Path(src).exists():
                    dst = OUT_DIR / f"{label}.wav"
                    shutil.copyfile(src, dst)
                rec.update({"ok": True, "elapsed": round(elapsed, 2), "audio": str(dst) if dst else src})
                print(f"[完成] {label}: {elapsed:.2f}s")
            except Exception as e:
                elapsed = time.time() - t0
                rec.update({"elapsed": round(elapsed, 2), "error": f"{type(e).__name__}: {e}"})
                print(f"[失败] {label}: {elapsed:.2f}s {type(e).__name__} {str(e)[:300]}")
            results.append(rec)

    out_json = OUT_DIR / "results.json"
    out_json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 80)
    print("汇总：梦成接口 XR3 英/西 响应时间")
    print("=" * 80)
    print(f"{'语言':8s} {'章节':>4s} {'字符':>8s} {'耗时':>8s} {'结果':>8s}")
    for r in results:
        ok = "OK" if r["ok"] else "FAIL"
        el = f"{r['elapsed']:.1f}s" if r["elapsed"] is not None else "-"
        print(f"{r['lang']:8s} {r['chapter']:>4d} {r['chars']:>8d} {el:>8s} {ok:>8s}")

    ok_res = [r for r in results if r["ok"]]
    if ok_res:
        print("\n耗时排名（从快到慢，前10）：")
        for rank, r in enumerate(sorted(ok_res, key=lambda x: x["elapsed"])[:10], 1):
            print(f"  {rank:2d}. {r['lang']} 第{r['chapter']}章: {r['elapsed']:.1f}s")
    print(f"\n结果已保存: {out_json}")


def parse_chapters(spec, total):
    idxs = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            idxs.extend(range(int(a), int(b) + 1))
        else:
            idxs.append(int(part))
    return [i for i in idxs if 1 <= i <= total]


if __name__ == "__main__":
    main()