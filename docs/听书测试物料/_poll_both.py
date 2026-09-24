import os
# -*- coding: utf-8 -*-
import base64, hashlib, hmac, json, time
import requests

import os

_TTS_KEY = os.environ.get("TTS_SECRET_KEY")
if not _TTS_KEY:
    raise SystemExit(
        "缺少环境变量 TTS_SECRET_KEY（测试环境密钥，请勿写入代码；设置后重试，例如：\n"
        "  在 PowerShell 里先设置环境变量 TTS_SECRET_KEY（值由项目统一管理）后再运行")
BASE = "https://ai-main-none-dev.changdu.ltd"
KEY = os.environ["TTS_SECRET_KEY"]
def sign(t):
    h = hmac.new(KEY.encode(), t.encode(), hashlib.sha256)
    return base64.b64encode(h.digest()).decode()
def post(url, payload):
    body = json.dumps(payload)
    r = requests.post(url, data=body.encode(),
                      headers={"sign": sign(body), "Content-Type": "application/json"}, timeout=30)
    return r.json()
ids = [650143, 650144]
t0 = time.time()
while time.time() - t0 < 8:
    info = post(f"{BASE}/Task/GetAllTaskStatus", {"taskType": 74, "taskIds": ids})
    m = {it.get("taskId"): it.get("taskStatus") for it in info.get("data", [])}
    print("higgs(650143)=%s  f5tts(650144)=%s" % (m.get(650143), m.get(650144)), flush=True)
    time.sleep(3)
