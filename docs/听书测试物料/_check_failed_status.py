import os
# -*- coding: utf-8 -*-
"""查询失败任务原始状态详情。"""
import base64, hashlib, hmac, json
import requests

import os

_TTS_KEY = os.environ.get("TTS_SECRET_KEY")
if not _TTS_KEY:
    raise SystemExit(
        "缺少环境变量 TTS_SECRET_KEY（测试环境密钥，请勿写入代码；设置后重试，例如：\n"
        "  在 PowerShell 里先设置环境变量 TTS_SECRET_KEY（值由项目统一管理）后再运行")

BASE = "https://ai-main-none-dev.changdu.ltd"
KEY = os.environ["TTS_SECRET_KEY"]
IDS = [671392, 671390, 617893, 671393, 671391, 650139]

def sign(t):
    h = hmac.new(KEY.encode(), t.encode(), hashlib.sha256)
    return base64.b64encode(h.digest()).decode()

def post(url, payload):
    body = json.dumps(payload)
    r = requests.post(url, data=body.encode(),
                      headers={"sign": sign(body), "Content-Type": "application/json"}, timeout=40)
    return r.json()

resp = post(f"{BASE}/Task/GetAllTaskStatus", {"taskType": 74, "taskIds": IDS})
print(json.dumps(resp, ensure_ascii=False, indent=2))
