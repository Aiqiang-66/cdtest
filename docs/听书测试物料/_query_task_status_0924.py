# -*- coding: utf-8 -*-
r"""一次性诊断：查询「卡在 status=67」任务的当前状态，并探测其产物对象是否已存在。

- 状态查询：POST /Task/GetAllTaskStatus（批量）
- 产物探测：HEAD 音频对象 https://reader-audio-1382266829.cos.ap-hongkong.myqcloud.com/audiobook/<taskId>.mp3

用法：
  $env:TTS_SECRET_KEY='...'
  & "D:\python\python.exe" docs\听书测试物料\_query_task_status_0924.py 30090607 30062698 ...
"""
import base64
import hashlib
import hmac
import json
import os
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://ai-main-none-dev.changdu.ltd"
COS_AUDIO = "https://reader-audio-1382266829.cos.ap-hongkong.myqcloud.com/audiobook/{}.mp3"
STATUS_CN = {1: "待处理", 2: "成功", 3: "失败", 66: "处理中(66)", 67: "处理中(67)"}


def sign(key, text):
    return base64.b64encode(hmac.new(key.encode(), text.encode(), hashlib.sha256).digest()).decode()


def main():
    ids = [a for a in sys.argv[1:] if a.strip().isdigit()]
    if not ids:
        print("用法：_query_task_status_0924.py <taskId> [taskId...]")
        return
    key = os.environ.get("TTS_SECRET_KEY")
    if not key:
        raise SystemExit("缺少环境变量 TTS_SECRET_KEY")

    body = json.dumps({"taskType": 74, "taskIds": [int(i) for i in ids]})
    r = requests.post(BASE + "/Task/GetAllTaskStatus", data=body.encode(),
                      headers={"sign": sign(key, body), "Content-Type": "application/json"}, timeout=60).json()
    print(f"接口返回 code={r.get('code')} msg={r.get('msg')}")
    rows = r.get("data") or []
    if isinstance(rows, dict):
        rows = [rows]
    print(f"\n{'taskId':>12} | {'taskStatus':>10} | 含义 | 产物字段 | 音频对象 HEAD | 查询时刻")
    print("-" * 110)
    import time
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    out = []
    for row in rows:
        tid = row.get("taskId") or row.get("id")
        st = row.get("taskStatus")
        has = []
        if row.get("audio_url"):
            has.append("audio_url")
        if row.get("metadata_url"):
            has.append("metadata_url")
        head = "-"
        try:
            h = requests.head(COS_AUDIO.format(tid), timeout=30, allow_redirects=True)
            size = h.headers.get("Content-Length")
            head = f"HTTP {h.status_code}" + (f" {int(size)/1048576:.2f} MB" if size and size.isdigit() and h.status_code == 200 else "")
        except Exception as e:
            head = f"探测失败 {type(e).__name__}"
        print(f"{tid:>12} | {str(st):>10} | {STATUS_CN.get(st, '未知'):<8} | {','.join(has) or '-':<20} | {head} | {now}")
        out.append({"taskId": tid, "taskStatus": st, "fields": has, "cos_head": head,
                    "comment": row.get("comment") or row.get("msg"), "checked_at": now})
    print("\n原始返回（截断）：")
    print(json.dumps(rows, ensure_ascii=False)[:1200])
    from pathlib import Path as _P
    _P(os.path.join(os.environ.get("TEMP", "."), "stuck_status_check.json")).write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
