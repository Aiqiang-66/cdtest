import os
# -*- coding: utf-8 -*-
"""对照实验：同一章英语文案，拆开 lang 与 voice 两个变量，看丢失是否与参数相关。

4 个任务并发下发，全部使用 XR3 英语第 1 章全文：
  A lang=1 voice=English_female      （复现历史配置）
  B lang=3 voice=English_female
  C lang=3 voice=audiobook_female_2
  D lang=1 voice=audiobook_female_2
"""
import base64
import difflib
import hashlib
import hmac
import json
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

import os

_TTS_KEY = os.environ.get("TTS_SECRET_KEY")
if not _TTS_KEY:
    raise SystemExit(
        "缺少环境变量 TTS_SECRET_KEY（测试环境密钥，请勿写入代码；设置后重试，例如：\n"
        "  在 PowerShell 里先设置环境变量 TTS_SECRET_KEY（值由项目统一管理）后再运行")

DEV = "https://ai-main-none-dev.changdu.ltd"
KEY = os.environ["TTS_SECRET_KEY"]
TXT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\txt文本")
OUT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\Higgs_lang对照实验_0910")
OUT.mkdir(parents=True, exist_ok=True)

CASES = [
    ("A_lang1_English_female", 1, "English_female"),
    ("B_lang3_English_female", 3, "English_female"),
    ("C_lang3_audiobook_female_2", 3, "audiobook_female_2"),
    ("D_lang1_audiobook_female_2", 1, "audiobook_female_2"),
]

_EDGE = re.compile(r"^[^\w']+|[^\w']+$")


def tk(s):
    s = unicodedata.normalize("NFKC", s).replace("\u2019", "'")
    return [w for w in (_EDGE.sub("", x).lower() for x in s.split()) if w]


def sign(t):
    return base64.b64encode(hmac.new(KEY.encode(), t.encode(), hashlib.sha256).digest()).decode()


def post(path, payload, timeout=60):
    body = json.dumps(payload)
    headers = {"sign": sign(body), "Content-Type": "application/json"}
    return requests.post(DEV + path, data=body.encode(), headers=headers, timeout=timeout).json()


def chapter1():
    text = (TXT / "XR3 - EN.txt").read_text(encoding="utf-8-sig")
    ms = list(re.finditer(r"^===\s*Chapter\s+\d+", text, flags=re.MULTILINE))
    return ms[0].group().strip("= ").strip(), text[ms[0].end():ms[1].start()].strip()


def run(name, lang, voice, title, body):
    t0 = time.time()
    rec = {"case": name, "lang": lang, "voice": voice, "chars": len(body), "sent_tokens": len(tk(body))}
    try:
        r = post("/Video/CreateUniversalTransparent", {
            "ext": json.dumps({"read_content": body, "chapter_title": title,
                               "model": "higgs", "lang": lang, "voice": voice}),
            "taskType": 74, "priority": 0, "retry_times": 1, "cool_time": 600})
        rec["taskId"] = r.get("data")
    except Exception as e:
        rec["error"] = f"create {type(e).__name__}: {e}"
        return rec

    info = {}
    while time.time() - t0 < 1200:
        try:
            body_r = post("/Task/GetAllTaskStatus", {"taskType": 74, "taskIds": [rec["taskId"]]})
            info = (body_r.get("data") or [{}])[0]
        except Exception:
            time.sleep(5)
            continue
        if info.get("taskStatus") == 2:
            break
        if info.get("taskStatus") == 3:
            rec["error"] = f"任务失败 {info.get('comment')}"
            rec["elapsed_s"] = round(time.time() - t0, 1)
            return rec
        time.sleep(5)

    rec["elapsed_s"] = round(time.time() - t0, 1)
    if info.get("taskStatus") != 2:
        rec["error"] = "超时"
        return rec

    data = info.get("data") or "{}"
    data = json.loads(data) if isinstance(data, str) else data
    rec["audio_url"] = data.get("audio_url", "")
    rec["metadata_url"] = data.get("metadata_url", "")
    mr = requests.get(rec["metadata_url"], timeout=180)
    (OUT / f"{name}.json").write_bytes(mr.content)
    segs = json.loads(mr.text)
    ret = []
    for s in segs:
        ret.extend(tk(s.get("text") or ""))
    title_tokens = tk(title)
    if ret[:len(title_tokens)] == title_tokens:
        ret = ret[len(title_tokens):]

    sent = tk(body)
    sm = difflib.SequenceMatcher(a=sent, b=ret, autojunk=False)
    missing = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("delete", "replace"):
            missing.extend(sent[i1:i2])
    rec.update({"ok": True, "ret_tokens": len(ret), "missing": len(missing),
                "missing_ratio": round(100.0 * len(missing) / len(sent), 2),
                "similarity": round(sm.ratio(), 4), "segments": len(segs),
                "missing_head": missing[:25]})
    return rec


if __name__ == "__main__":
    title, body = chapter1()
    print(f"文案：{title}，{len(body)} 字符 / {len(tk(body))} 词", flush=True)
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(run, n, l, v, title, body) for n, l, v in CASES]
        results = [f.result() for f in futs]
    print()
    print("%-28s %-4s %-22s %-8s %-8s %-9s %s" % ("用例", "lang", "voice", "耗时(s)", "返回词", "缺失率", "相似度"))
    print("-" * 96)
    for r in results:
        if r.get("ok"):
            print("%-28s %-4s %-22s %-8s %-8s %-9s %s" % (
                r["case"], r["lang"], r["voice"], r["elapsed_s"], r["ret_tokens"],
                f"{r['missing_ratio']}%", r["similarity"]))
        else:
            print("%-28s %-4s %-22s %-8s %s" % (r["case"], r["lang"], r["voice"],
                                                r.get("elapsed_s", "-"), r.get("error")))
    (OUT / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n结果目录：{OUT}")
