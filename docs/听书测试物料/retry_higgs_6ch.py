import os
# -*- coding: utf-8 -*-
"""Higgs TTS v3 补跑 6 个失败章节：优先复用已创建 taskId，失败则重建任务。带连接重试。"""
import base64
import hashlib
import hmac
import json
import re
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
TXT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\txt文本")
OUT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\Higgs_XR3_对比听测_0824")
POLL_INTERVAL = 5
POLL_TIMEOUT = 1800
MAX_POLL_RETRY = 10

# (cn_name, txt文件, marker, lang, voice, label, taskId, chapter)
TASKS = [
    ("英语", "XR3 - EN.txt", re.compile(r"^=== Chapter"), 1, "English_female", "英语_XR3_Ch7", 648354, 7),
    ("英语", "XR3 - EN.txt", re.compile(r"^=== Chapter"), 1, "English_female", "英语_XR3_Ch18", 648364, 18),
    ("西语", "XR3 - SP.txt", re.compile(r"^=== Capítulo"), 4, "Spanish_female", "西语_XR3_Ch2", 668756, 2),
    ("西语", "XR3 - SP.txt", re.compile(r"^=== Capítulo"), 4, "Spanish_female", "西语_XR3_Ch9", 668760, 9),
    ("西语", "XR3 - SP.txt", re.compile(r"^=== Capítulo"), 4, "Spanish_female", "西语_XR3_Ch11", 668762, 11),
    ("西语", "XR3 - SP.txt", re.compile(r"^=== Capítulo"), 4, "Spanish_female", "西语_XR3_Ch16", 648368, 16),
]


def sign(text: str) -> str:
    h = hmac.new(SECRET_KEY.encode(), text.encode(), hashlib.sha256)
    return base64.b64encode(h.digest()).decode()


def signed_post(url: str, payload: dict, timeout: int = 40, retries: int = MAX_POLL_RETRY) -> dict:
    body = json.dumps(payload)
    headers = {"sign": sign(body), "Content-Type": "application/json"}
    last = None
    for i in range(retries):
        try:
            resp = requests.post(url, data=body.encode(), headers=headers, timeout=timeout)
            return resp.json()
        except Exception as e:
            last = e
            time.sleep(min(2 + i * 2, 20))
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


def split_chapters(fname, marker):
    text = (TXT / fname).read_text(encoding="utf-8")
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


def download(label: str, result: dict) -> dict:
    data = result
    audio_url = data.get("audio_url", "")
    meta_url = data.get("metadata_url", "")
    mp3_size = 0
    subs = 0
    if audio_url:
        for i in range(4):
            try:
                r = requests.get(audio_url, timeout=240)
                (OUT / f"{label}.mp3").write_bytes(r.content)
                mp3_size = len(r.content)
                break
            except Exception as e:
                if i == 3:
                    raise
                time.sleep(5)
    if meta_url:
        for i in range(4):
            try:
                r = requests.get(meta_url, timeout=240)
                (OUT / f"{label}.json").write_bytes(r.content)
                segs = json.loads(r.text)
                lines = []
                for s in segs:
                    idx = s.get("id", 0) + 1
                    sm, em = s.get("startMs", 0), s.get("endMs", 0)
                    t = s.get("text", "").strip()
                    if not t:
                        continue

                    def fms(ms):
                        h = ms // 3600000
                        m = (ms % 3600000) // 60000
                        sec = (ms % 60000) // 1000
                        return f"{h:02d}:{m:02d}:{sec:02d},{ms % 1000:03d}"

                    lines.append(str(idx))
                    lines.append(f"{fms(sm)} --> {fms(em)}")
                    lines.append(t)
                    lines.append("")
                (OUT / f"{label}.srt").write_text("\n".join(lines), encoding="utf-8")
                subs = len([ln for ln in lines if ln and ln[0].isdigit()])
                break
            except Exception as e:
                if i == 3:
                    raise
                time.sleep(5)
    return {"mp3_size": mp3_size, "subs": subs}


def poll_for_download(task_id: int, label: str, start: float):
    deadline = start + POLL_TIMEOUT
    while time.time() < deadline:
        info = get_task_status(task_id)
        if not info:
            time.sleep(POLL_INTERVAL)
            continue
        status = info.get("taskStatus")
        if status == 2:
            data = info.get("data", "{}")
            data = json.loads(data) if isinstance(data, str) else data
            return_elapsed = time.time() - start
            return "done", return_elapsed, info
        elif status == 3:
            return "fail", time.time() - start, info
        time.sleep(POLL_INTERVAL)
    return "timeout", None, None


def run_one(cn_name, fname, marker, lang, voice, label, task_id, chapter):
    t0 = time.time()
    # 先尝试复用已创建 taskId
    try:
        status, ret_elapsed, info = poll_for_download(task_id, label, t0)
        if status == "done":
            dl = download(label, json.loads(info.get("data", "{}")) if isinstance(info.get("data", "{}"), str) else info.get("data", {}))
            print(f"  [{label}] 复用taskId={task_id} 完成 return={ret_elapsed:.1f}s total={time.time()-t0:.1f}s mp3={dl['mp3_size']:,}B subs={dl['subs']}", flush=True)
            return {"label": label, "taskId": task_id, "ok": True, "elapsed": round(time.time() - t0, 2),
                    "task_return_elapsed": round(ret_elapsed, 2), "mp3_size": dl["mp3_size"], "subs": dl["subs"],
                    "lang": cn_name, "chapter": chapter, "status": "reuse"}
        elif status == "fail":
            print(f"  [{label}] 原任务失败(status=3)，重建", flush=True)
        else:
            print(f"  [{label}] 原任务查询超时/无结果，重建", flush=True)
    except Exception as e:
        print(f"  [{label}] 查询原任务异常: {e}，重建", flush=True)

    # 重建任务
    chapters = split_chapters(fname, marker)
    title, content = chapters[chapter - 1]
    new_id = create_task({"read_content": content, "chapter_title": title, "model": "higgs", "lang": lang, "voice": voice})
    print(f"  [{label}] 重建 taskId={new_id}", flush=True)
    status, ret_elapsed, info = poll_for_download(new_id, label, t0)
    if status == "done":
        dl = download(label, json.loads(info.get("data", "{}")) if isinstance(info.get("data", "{}"), str) else info.get("data", {}))
        print(f"  [{label}] 重建完成 return={ret_elapsed:.1f}s total={time.time()-t0:.1f}s mp3={dl['mp3_size']:,}B subs={dl['subs']}", flush=True)
        return {"label": label, "taskId": new_id, "ok": True, "elapsed": round(time.time() - t0, 2),
                "task_return_elapsed": round(ret_elapsed, 2), "mp3_size": dl["mp3_size"], "subs": dl["subs"],
                "lang": cn_name, "chapter": chapter, "title": title, "chars": len(content), "status": "rebuild"}
    err = info.get("comment", "") if info else "timeout"
    print(f"  [{label}] 重建后失败: {err}", flush=True)
    return {"label": label, "taskId": new_id, "ok": False, "elapsed": round(time.time() - t0, 2),
            "task_return_elapsed": round(ret_elapsed, 2) if ret_elapsed else None,
            "lang": cn_name, "chapter": chapter, "title": title, "chars": len(content), "error": err}


def main():
    results = []
    ok_count = 0
    for (cn_name, fname, marker, lang, voice, label, task_id, chapter) in TASKS:
        print(f"[开始] {label} taskId={task_id}", flush=True)
        rec = run_one(cn_name, fname, marker, lang, voice, label, task_id, chapter)
        results.append(rec)
        if rec["ok"]:
            ok_count += 1
    out_json = OUT / "higgs_retry_results.json"
    out_json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n补跑成功 {ok_count}/{len(results)}，结果已保存: {out_json}", flush=True)


if __name__ == "__main__":
    main()
