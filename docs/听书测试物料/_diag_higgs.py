import os
# -*- coding: utf-8 -*-
"""Higgs 失败诊断：短文本 vs 长章节（串行），结果实时写盘。"""
import base64, hashlib, hmac, json, re, time
from pathlib import Path
import requests

import os

_TTS_KEY = os.environ.get("TTS_SECRET_KEY")
if not _TTS_KEY:
    raise SystemExit(
        "缺少环境变量 TTS_SECRET_KEY（测试环境密钥，请勿写入代码；设置后重试，例如：\n"
        "  在 PowerShell 里先设置环境变量 TTS_SECRET_KEY（值由项目统一管理）后再运行")

BASE = "https://ai-main-none-dev.changdu.ltd"
KEY = os.environ["TTS_SECRET_KEY"]
TXT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\txt文本")
OUT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\Higgs_全语种单章_0910")
LOG = OUT / "diagnose.json"

def sign(t):
    h = hmac.new(KEY.encode(), t.encode(), hashlib.sha256)
    return base64.b64encode(h.digest()).decode()

def post(url, payload, timeout=40):
    body = json.dumps(payload)
    r = requests.post(url, data=body.encode(),
                      headers={"sign": sign(body), "Content-Type": "application/json"}, timeout=timeout)
    return r.json()

def create(ext):
    b = post(f"{BASE}/Video/CreateUniversalTransparent",
             {"ext": json.dumps(ext), "taskType": 74, "priority": 0, "retry_times": 1, "cool_time": 600})
    if b.get("code") != 200:
        raise RuntimeError(f"create fail: {b}")
    return b["data"]

def status(tid):
    b = post(f"{BASE}/Task/GetAllTaskStatus", {"taskType": 74, "taskIds": [tid]})
    lst = b.get("data", [])
    return lst[0] if lst else {}

def run(name, content, lang, voice):
    t0 = time.time()
    try:
        tid = create({"read_content": content, "chapter_title": name,
                      "model": "higgs", "lang": lang, "voice": voice})
    except Exception as e:
        rec = {"name": name, "chars": len(content), "ok": False, "error": f"create {type(e).__name__}: {e}"}
        return rec
    rec = {"name": name, "chars": len(content), "taskId": tid}
    while time.time() - t0 < 600:
        info = status(tid)
        st = info.get("taskStatus")
        if st == 2:
            d = info.get("data", "{}")
            d = json.loads(d) if isinstance(d, str) else d
            rec.update({"ok": True, "status": 2, "audio": bool(d.get("audio_url")),
                        "meta": bool(d.get("metadata_url"))})
            break
        if st == 3:
            rec.update({"ok": False, "status": 3, "comment": info.get("comment"),
                        "errorCode": info.get("errorCode")})
            break
        time.sleep(5)
    rec["elapsed"] = round(time.time() - t0, 1)
    return rec

def save(recs):
    LOG.write_text(json.dumps(recs, ensure_ascii=False, indent=2), encoding="utf-8")

results = []
# 1) 短文本
short = "The lighthouse keeper climbed the worn stairs again, carrying oil for the great lamp. Below him the sea moved like something asleep, and the village lights blinked once, then twice, before going dark."
results.append(run("short_en_240", short, 1, "English_female"))
save(results)
print(json.dumps(results[-1], ensure_ascii=False))

# 2) 中等文本（XR3 英语第 3 章，约 600 字符）
text = (TXT / "XR3 - EN.txt").read_text(encoding="utf-8")
ms = list(re.finditer(r"^===\s*Chapter\s+\d+", text, flags=re.MULTILINE))
if len(ms) > 2:
    mid = text[ms[2].end():ms[3].start()].strip() if len(ms) > 3 else text[ms[2].end():].strip()
    results.append(run("mid_en_ch3", mid, 1, "English_female"))
    save(results)
    print(json.dumps(results[-1], ensure_ascii=False))

# 3) 长章节（第 1 章全文）
if len(ms) > 1:
    long_c = text[ms[0].end():ms[1].start()].strip()
    results.append(run("long_en_ch1", long_c, 1, "English_female"))
    save(results)
    print(json.dumps(results[-1], ensure_ascii=False))

print("DONE")
