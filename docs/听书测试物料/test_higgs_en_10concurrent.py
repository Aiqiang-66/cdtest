import os
# -*- coding: utf-8 -*-
"""Higgs TTS v3 英语约500字符 十连并发压测（增强版：连接重试+共享会话+轮询容错）。"""
import base64
import hashlib
import hmac
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter

import os

_TTS_KEY = os.environ.get("TTS_SECRET_KEY")
if not _TTS_KEY:
    raise SystemExit(
        "缺少环境变量 TTS_SECRET_KEY（测试环境密钥，请勿写入代码；设置后重试，例如：\n"
        "  在 PowerShell 里先设置环境变量 TTS_SECRET_KEY（值由项目统一管理）后再运行")

DEV_BASE_URL = "https://ai-main-none-dev.changdu.ltd"
SECRET_KEY = os.environ["TTS_SECRET_KEY"]
OUT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\Higgs_英文500_十连_测试")
OUT.mkdir(parents=True, exist_ok=True)
POLL_INTERVAL = 4
POLL_TIMEOUT = 900
N = 10
MAX_WORKERS = 10
TARGET = 500
RETRY = 6

CONTENT = (
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

_session = requests.Session()
_adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=0)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)

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
    last = None
    for i in range(RETRY):
        try:
            r = _session.post(url, data=body.encode(), headers=headers, timeout=timeout)
            return r.json()
        except Exception as e:
            last = e
            time.sleep(min(1 + i * 2, 15))
    raise last

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

def download(idx, data):
    mp3_size = 0
    subs = 0
    audio_url = data.get("audio_url", "")
    meta_url = data.get("metadata_url", "")
    if audio_url:
        r = _session.get(audio_url, timeout=240)
        (OUT / f"task_{idx:02d}.mp3").write_bytes(r.content)
        mp3_size = len(r.content)
    if meta_url:
        r = _session.get(meta_url, timeout=240)
        (OUT / f"task_{idx:02d}.json").write_bytes(r.content)
        segs = json.loads(r.text)
        lines = []
        for s in segs:
            i_ = s.get("id", 0) + 1
            sm, em = s.get("startMs", 0), s.get("endMs", 0)
            t = s.get("text", "").strip()
            if not t:
                continue
            lines.append(str(i_))
            lines.append(f"{fms(sm)} --> {fms(em)}")
            lines.append(t)
            lines.append("")
        (OUT / f"task_{idx:02d}.srt").write_text("\n".join(lines), encoding="utf-8")
        subs = len([ln for ln in lines if ln and ln[0].isdigit()])
    return mp3_size, subs

def run_one(idx, content):
    label = f"task_{idx:02d}"
    t0 = time.time()
    task_id = None
    try:
        task_id = create_task({
            "read_content": content,
            "chapter_title": f"Higgs EN ~500 #{idx}",
            "model": "higgs",
            "lang": 1,
            "voice": "English_female",
        })
        create_t = time.time() - t0
    except Exception as e:
        return {"label": label, "ok": False, "error": f"{type(e).__name__}: {e}", "elapsed": round(time.time()-t0, 2)}

    status = None
    result = None
    try:
        while time.time() - t0 < POLL_TIMEOUT:
            info = get_task_status(task_id)
            status = info.get("taskStatus")
            if status == 2:
                result = info
                break
            elif status == 3:
                print(f"  [{label}] 失败 comment={info.get('comment')}", flush=True)
                break
            time.sleep(POLL_INTERVAL)
    except Exception as e:
        total = time.time() - t0
        return {"label": label, "taskId": task_id, "ok": False, "status": status,
                "create_t": round(create_t, 2), "elapsed": round(total, 2),
                "error": f"{type(e).__name__}: {e}"}

    total = time.time() - t0
    if not result:
        return {"label": label, "taskId": task_id, "ok": False, "status": status,
                "create_t": round(create_t, 2), "elapsed": round(total, 2), "error": "timeout/no-result"}
    try:
        data = result.get("data", "{}")
        data = json.loads(data) if isinstance(data, str) else data
        mp3_size, subs = download(idx, data)
        return {"label": label, "taskId": task_id, "ok": True, "create_t": round(create_t, 2),
                "elapsed": round(total, 2), "mp3_size": mp3_size, "subs": subs, "status": status}
    except Exception as e:
        return {"label": label, "taskId": task_id, "ok": False, "status": status,
                "create_t": round(create_t, 2), "elapsed": round(total, 2), "error": f"{type(e).__name__}: {e}"}

def main():
    content = fit(CONTENT)
    print(f"[文本字符数] {len(content)}  并发 {N} 路", flush=True)
    (OUT / "source_text.txt").write_text(content, encoding="utf-8")
    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {ex.submit(run_one, i, content): i for i in range(1, N + 1)}
        for fut in as_completed(futs):
            rec = fut.result()
            results.append(rec)
            if rec["ok"]:
                print(f"[完成] {rec['label']} taskId={rec['taskId']} create={rec['create_t']}s total={rec['elapsed']}s mp3={rec['mp3_size']:,}B subs={rec['subs']}", flush=True)
            else:
                print(f"[失败] {rec['label']} taskId={rec.get('taskId')} {rec.get('error')}", flush=True)

    results.sort(key=lambda r: r["label"])
    ok = [r for r in results if r["ok"]]
    print("\n===== 十连结果汇总 =====", flush=True)
    print(f"成功: {len(ok)}/{len(results)}", flush=True)
    if ok:
        ct = [r["create_t"] for r in ok]
        tt = [r["elapsed"] for r in ok]
        print(f"创建耗时(秒): 平均={sum(ct)/len(ct):.2f} 最小={min(ct):.2f} 最大={max(ct):.2f}", flush=True)
        print(f"整任务耗时(秒): 平均={sum(tt)/len(tt):.2f} 最小={min(tt):.2f} 最大={max(tt):.2f}", flush=True)
        print(f"总墙钟≈{max(tt):.1f}s", flush=True)
    (OUT / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[输出目录] {OUT}", flush=True)

if __name__ == "__main__":
    main()
