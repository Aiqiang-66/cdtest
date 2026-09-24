import os
# -*- coding: utf-8 -*-
"""Higgs TTS v3 40章下发：XR3 英/西 Ch1-20，串行，供与 IndexTTS-2.5 人工对比。"""
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
OUT.mkdir(parents=True, exist_ok=True)
POLL_INTERVAL = 5
POLL_TIMEOUT = 3600
CHAPTERS = list(range(1, 21))

CONFIGS = [
    ("英语", "XR3 - EN.txt", re.compile(r"^=== Chapter"), 1, "English_female"),
    ("西语", "XR3 - SP.txt", re.compile(r"^=== Capítulo"), 4, "Spanish_female"),
]


def sign(text: str) -> str:
    h = hmac.new(SECRET_KEY.encode(), text.encode(), hashlib.sha256)
    return base64.b64encode(h.digest()).decode()


def signed_post(url: str, payload: dict, timeout: int = 40) -> dict:
    body = json.dumps(payload)
    headers = {"sign": sign(body), "Content-Type": "application/json"}
    resp = requests.post(url, data=body.encode(), headers=headers, timeout=timeout)
    return resp.json()


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


def poll_and_download(task_id: int, label: str, start: float) -> dict:
    deadline = start + POLL_TIMEOUT
    result = None
    return_elapsed = None
    while time.time() < deadline:
        info = get_task_status(task_id)
        if not info:
            time.sleep(POLL_INTERVAL)
            continue
        status = info.get("taskStatus")
        elapsed = int(time.time() - start)
        if elapsed % 30 < POLL_INTERVAL:
            print(f"  [{label}] [{elapsed}s] status={status}", flush=True)
        if status == 2:
            result = info
            return_elapsed = time.time() - start
            break
        elif status == 3:
            return_elapsed = time.time() - start
            print(f"  [{label}] 失败: {info.get('comment', '')}", flush=True)
            break
        time.sleep(POLL_INTERVAL)

    total_elapsed = time.time() - start
    if not result:
        print(f"  [{label}] 超时/失败", flush=True)
        return {"label": label, "taskId": task_id, "ok": False,
                "elapsed": round(total_elapsed, 2),
                "task_return_elapsed": round(return_elapsed, 2) if return_elapsed is not None else None}

    data_str = result.get("data", "{}")
    data = json.loads(data_str) if isinstance(data_str, str) else data_str
    audio_url = data.get("audio_url", "")
    meta_url = data.get("metadata_url", "")
    mp3_size = 0
    subs = 0

    if audio_url:
        r = requests.get(audio_url, timeout=240)
        (OUT / f"{label}.mp3").write_bytes(r.content)
        mp3_size = len(r.content)
    if meta_url:
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

    print(f"  [{label}] 完成! return={return_elapsed:.1f}s total={total_elapsed:.1f}s mp3={mp3_size:,}B subs={subs}", flush=True)
    return {"label": label, "taskId": task_id, "ok": True, "elapsed": round(total_elapsed, 2),
            "task_return_elapsed": round(return_elapsed, 2) if return_elapsed is not None else None,
            "mp3_size": mp3_size, "subs": subs}


def main():
    results = []
    ok_count = 0
    for cn_name, fname, marker, lang, voice in CONFIGS:
        chapters = split_chapters(fname, marker)
        print(f"\n===== {cn_name} ({fname}) 共 {len(chapters)} 章，选测 {len(CHAPTERS)} 章 =====", flush=True)
        for ci in CHAPTERS:
            title, content = chapters[ci - 1]
            label = f"{cn_name}_XR3_Ch{ci}"
            print(f"[开始] {label} ({len(content)} 字符)", flush=True)
            t0 = time.time()
            try:
                task_id = create_task({
                    "read_content": content,
                    "chapter_title": title,
                    "model": "higgs",
                    "lang": lang,
                    "voice": voice,
                })
                print(f"  [{label}] taskId={task_id}", flush=True)
                rec = poll_and_download(task_id, label, t0)
                rec["lang"] = cn_name
                rec["chapter"] = ci
                rec["chars"] = len(content)
                rec["title"] = title
                results.append(rec)
                if rec["ok"]:
                    ok_count += 1
            except Exception as e:
                elapsed = time.time() - t0
                results.append({"lang": cn_name, "chapter": ci, "title": title, "taskId": None, "ok": False,
                                "elapsed": round(elapsed, 2), "task_return_elapsed": None,
                                "chars": len(content), "error": f"{type(e).__name__}: {e}"})
                print(f"  [{label}] 异常: {e}", flush=True)

    out_json = OUT / "higgs_compare_results.json"
    out_json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n成功 {ok_count}/{len(results)}，结果已保存: {out_json}", flush=True)


if __name__ == "__main__":
    main()