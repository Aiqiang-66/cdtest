import os
# -*- coding: utf-8 -*-
"""Higgs TTS v3 单次英语约500字符 连通性测试：调用接口 -> 轮询 -> 下载 mp3+srt。"""
import base64
import hashlib
import hmac
import json
import time
from pathlib import Path

import requests

import os

_TTS_KEY = os.environ.get("TTS_SECRET_KEY")
if not _TTS_KEY:
    raise SystemExit(
        "缺少环境变量 TTS_SECRET_KEY（测试环境密钥，请勿写入代码；设置后重试，例如：\n"
        "  在 PowerShell 里先设置环境变量 TTS_SECRET_KEY（值由项目统一管理）后再运行")

DEV_BASE_URL = "https://ai-main-none-dev.changdu.ltd"
SECRET_KEY = os.environ["TTS_SECRET_KEY"]
OUT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\Higgs_单次英文500_测试")
OUT.mkdir(parents=True, exist_ok=True)
POLL_INTERVAL = 5
POLL_TIMEOUT = 900

TARGET = 500

LONG_TEXT = (
    "The morning fog rolled in from the river, thick and white, swallowing the empty "
    "street. Simon pulled his coat tighter and walked toward the old station, where "
    "the last train had left an hour ago. A single lamp flickered above the ticket "
    "window, and behind the glass sat a clerk he had never seen before. The clerk "
    "looked up, slid a folded letter across the counter, and said only the stranger's "
    "name. Simon stared at the envelope, cold and certain, because no one alive should "
    "have known that name. The clock above the door struck seven, and somewhere outside "
    "a whistle blew, low and long, calling him toward the platform. He did not ask "
    "questions. He simply took the letter, stepped out into the pale light, and walked "
    "into the story his life had been waiting to tell."
)

def fit(s, n=TARGET):
    if len(s) <= n:
        return s
    cut = s[:n]
    idx = cut.rfind(" ")
    return cut[:idx] if idx > n * 0.6 else cut

def sign(text: str) -> str:
    h = hmac.new(SECRET_KEY.encode(), text.encode(), hashlib.sha256)
    return base64.b64encode(h.digest()).decode()

def signed_post(url: str, payload: dict, timeout: int = 40) -> dict:
    body = json.dumps(payload)
    headers = {"sign": sign(body), "Content-Type": "application/json"}
    r = requests.post(url, data=body.encode(), headers=headers, timeout=timeout)
    return r.json()

def create_task(ext_data: dict) -> int:
    payload = {"ext": json.dumps(ext_data), "taskType": 74, "priority": 0, "retry_times": 1, "cool_time": 600}
    body = signed_post(f"{DEV_BASE_URL}/Video/CreateUniversalTransparent", payload)
    if body.get("code") != 200:
        raise RuntimeError(f"创建失败: {body}")
    return body["data"]

def get_task_status(task_id: int) -> dict:
    body = signed_post(f"{DEV_BASE_URL}/Task/GetAllTaskStatus", {"taskType": 74, "taskIds": [task_id]})
    if body.get("code") != 200:
        raise RuntimeError(f"查询失败: {body}")
    lst = body.get("data", [])
    return lst[0] if lst else {}

def fms(ms):
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    sec = (ms % 60000) // 1000
    return f"{h:02d}:{m:02d}:{sec:02d},{ms % 1000:03d}"

def download(result):
    data = result.get("data", "{}")
    data = json.loads(data) if isinstance(data, str) else data
    audio_url = data.get("audio_url", "")
    meta_url = data.get("metadata_url", "")
    mp3_size = 0
    subs = 0
    if audio_url:
        r = requests.get(audio_url, timeout=240)
        (OUT / "test_en_500.mp3").write_bytes(r.content)
        mp3_size = len(r.content)
    if meta_url:
        r = requests.get(meta_url, timeout=240)
        (OUT / "test_en_500.json").write_bytes(r.content)
        segs = json.loads(r.text)
        lines = []
        for s in segs:
            idx = s.get("id", 0) + 1
            sm, em = s.get("startMs", 0), s.get("endMs", 0)
            t = s.get("text", "").strip()
            if not t:
                continue
            lines.append(str(idx))
            lines.append(f"{fms(sm)} --> {fms(em)}")
            lines.append(t)
            lines.append("")
        (OUT / "test_en_500.srt").write_text("\n".join(lines), encoding="utf-8")
        subs = len([ln for ln in lines if ln and ln[0].isdigit()])
    return mp3_size, subs

def main():
    content = fit(LONG_TEXT)
    print(f"[字符数] {len(content)} (目标~{TARGET})", flush=True)
    (OUT / "test_en_500.txt").write_text(content, encoding="utf-8")
    t0 = time.time()
    task_id = create_task({
        "read_content": content,
        "chapter_title": "Higgs English ~500 chars connectivity test",
        "model": "higgs",
        "lang": 1,
        "voice": "English_female",
    })
    print(f"[任务创建] taskId={task_id} create_time={time.time()-t0:.1f}s", flush=True)

    deadline = t0 + POLL_TIMEOUT
    result = None
    status = None
    while time.time() < deadline:
        info = get_task_status(task_id)
        status = info.get("taskStatus")
        elapsed = int(time.time() - t0)
        if elapsed % 20 < POLL_INTERVAL:
            print(f"  [{elapsed}s] status={status}", flush=True)
        if status == 2:
            result = info
            break
        elif status == 3:
            print(f"  [失败] comment={info.get('comment')}", flush=True)
            break
        time.sleep(POLL_INTERVAL)

    total = time.time() - t0
    if not result:
        print(f"[未完成] status={status} total={total:.1f}s", flush=True)
        return
    mp3_size, subs = download(result)
    print(f"[完成] total={total:.1f}s mp3={mp3_size:,}B subs={subs}", flush=True)
    print(f"[输出目录] {OUT}", flush=True)

if __name__ == "__main__":
    main()
