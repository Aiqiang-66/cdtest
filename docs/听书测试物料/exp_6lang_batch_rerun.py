import os
# -*- coding: utf-8 -*-
"""复跑 0910 17:46 那批 6 语种整章下发（6 并发），逐语种与原文做 token 比对。

用于对照：历史批次英语/德语/俄语各丢失 8~10%，法语/西语/葡语 0%。
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
OUT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\Higgs_6lang批次复跑_0910")
OUT.mkdir(parents=True, exist_ok=True)

CONFIGS = [
    ("英语", "XR3 - EN.txt", r"^===\s*Chapter\s+\d+", 1, "English_female"),
    ("德语", "XR3 - DE.txt", r"^===\s*Kapitel\s+\d+", 1, "German_female"),
    ("法语", "XR3 - FR.txt", r"^===\s*Chapitre\s+\d+", 6, "French_female"),
    ("西语", "XR3 - SP.txt", r"^===\s*Cap[ií]tulo\s+\d+", 4, "Spanish_female"),
    ("葡语", "XR3 - PT.txt", r"^===\s*Cap[ií]tulo\s+\d+", 5, "Portuguese_female"),
    ("俄语", "XR3 - RU.txt", r"^===\s*Глава\s+\d+", 1, "Russian_female"),
]

_EDGE = re.compile(r"^[^\w']+|[^\w']+$")


def tk(s):
    s = unicodedata.normalize("NFKC", s).replace("\u2019", "'")
    return [w for w in (_EDGE.sub("", x).lower() for x in s.split()) if w]


def sign(t):
    return base64.b64encode(hmac.new(KEY.encode(), t.encode(), hashlib.sha256).digest()).decode()


def post(path, payload, timeout=60):
    body = json.dumps(payload)
    return requests.post(DEV + path, data=body.encode(),
                         headers={"sign": sign(body), "Content-Type": "application/json"},
                         timeout=timeout).json()


def chapter1(fname, pattern):
    text = (TXT / fname).read_text(encoding="utf-8-sig")
    ms = list(re.finditer(pattern, text, flags=re.MULTILINE))
    return ms[0].group().strip("= ").strip(), text[ms[0].end():ms[1].start()].strip()


def run(cn, fname, pattern, lang, voice):
    title, body = chapter1(fname, pattern)
    t0 = time.time()
    rec = {"lang": cn, "lang_code": lang, "voice": voice, "title": title,
           "chars": len(body), "sent_tokens": len(tk(body))}
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
            b = post("/Task/GetAllTaskStatus", {"taskType": 74, "taskIds": [rec["taskId"]]})
            info = (b.get("data") or [{}])[0]
        except Exception:
            time.sleep(5)
            continue
        if info.get("taskStatus") in (2, 3):
            break
        time.sleep(5)
    rec["elapsed_s"] = round(time.time() - t0, 1)
    if info.get("taskStatus") != 2:
        rec["error"] = f"未完成 status={info.get('taskStatus')} {info.get('comment')}"
        return rec

    data = info.get("data") or "{}"
    data = json.loads(data) if isinstance(data, str) else data
    mr = requests.get(data.get("metadata_url", ""), timeout=180)
    (OUT / f"{cn}.json").write_bytes(mr.content)
    segs = json.loads(mr.text)
    ret = []
    for s in segs:
        ret.extend(tk(s.get("text") or ""))
    tt = tk(title)
    if ret[:len(tt)] == tt:
        ret = ret[len(tt):]

    sent = tk(body)
    sm = difflib.SequenceMatcher(a=sent, b=ret, autojunk=False)
    missing = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("delete", "replace"):
            missing.extend(sent[i1:i2])
    rec.update({"ok": True, "segments": len(segs), "ret_tokens": len(ret),
                "missing": len(missing),
                "missing_ratio": round(100.0 * len(missing) / len(sent), 2),
                "similarity": round(sm.ratio(), 4), "missing_head": missing[:25]})
    return rec


if __name__ == "__main__":
    print("6 并发整章复跑（复现 0910 17:46 批次口径）", flush=True)
    with ThreadPoolExecutor(max_workers=6) as ex:
        results = [f.result() for f in [ex.submit(run, *c) for c in CONFIGS]]
    print()
    print("%-6s %-8s %-18s %-10s %-8s %-9s %-9s %s" % (
        "语种", "taskId", "voice", "耗时(s)", "返回词", "原文词", "缺失率", "相似度"))
    print("-" * 92)
    for r in results:
        if r.get("ok"):
            print("%-6s %-8s %-18s %-10s %-8s %-9s %-9s %s" % (
                r["lang"], r["taskId"], r["voice"], r["elapsed_s"], r["ret_tokens"],
                r["sent_tokens"], f"{r['missing_ratio']}%", r["similarity"]))
        else:
            print("%-6s %-8s %-18s %-10s %s" % (r["lang"], r.get("taskId", "-"), r["voice"],
                                                r.get("elapsed_s", "-"), r.get("error")))
    (OUT / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n结果目录：{OUT}")
