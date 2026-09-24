import os
# -*- coding: utf-8 -*-
import base64, hashlib, hmac, json, time
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
OUT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\Higgs_全语种单章_0910")
def sign(t):
    h = hmac.new(KEY.encode(), t.encode(), hashlib.sha256)
    return base64.b64encode(h.digest()).decode()
def post(url, payload, timeout=30):
    body = json.dumps(payload)
    r = requests.post(url, data=body.encode(),
                      headers={"sign": sign(body), "Content-Type": "application/json"}, timeout=timeout)
    return r.json()
ext = {"read_content": "The lighthouse keeper climbed the worn stairs once more, carrying oil for the great lamp above the rocks.",
       "chapter_title": "ProbeShort", "model": "higgs", "lang": 1, "voice": "English_female"}
b = post(f"{BASE}/Video/CreateUniversalTransparent",
         {"ext": json.dumps(ext), "taskType": 74, "priority": 0, "retry_times": 1, "cool_time": 600})
tid = b.get("data")
(OUT / "probe_taskid.txt").write_text(str(tid), encoding="utf-8")
print("taskId =", tid)
t0 = time.time()
for _ in range(3):
    time.sleep(2)
    info = post(f"{BASE}/Task/GetAllTaskStatus", {"taskType": 74, "taskIds": [tid]})
    lst = info.get("data", [])
    st = lst[0].get("taskStatus") if lst else None
    print("[%ds] status=%s" % (int(time.time()-t0), st))
