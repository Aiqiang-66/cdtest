import os
# -*- coding: utf-8 -*-
"""Higgs TTS v3 全语种单章调用测试（测试环境）。

6 个语种各取对应书籍第 1 章，调用 Higgs TTS 接口合成，下载 mp3 + srt，
统计各语种响应耗时与产物大小，用于全语种连通性验证。
"""
import base64
import hashlib
import hmac
import json
import re
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
TXT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\txt文本")
OUT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\Higgs_全语种单章_0910")
OUT.mkdir(parents=True, exist_ok=True)

POLL_INTERVAL = 5
POLL_TIMEOUT = 1200
RETRY = 6
MAX_WORKERS = 6

# 语种配置：(文件名, 章节正则, lang, voice, 中文名)
CONFIGS = [
    ("XR3 - EN.txt", r"^===\s*Chapter\s+\d+",  1, "English_female",    "英语"),
    ("XR3 - DE.txt", r"^===\s*Kapitel\s+\d+",  1, "German_female",     "德语"),
    ("XR3 - FR.txt", r"^===\s*Chapitre\s+\d+", 6, "French_female",     "法语"),
    ("XR3 - SP.txt", r"^===\s*Cap[ií]tulo\s+\d+", 4, "Spanish_female", "西语"),
    ("XR3 - PT.txt", r"^===\s*Cap[ií]tulo\s+\d+", 5, "Portuguese_female", "葡语"),
    ("XR3 - RU.txt", r"^===\s*Глава\s+\d+",    1, "Russian_female",    "俄语"),
]

_session = requests.Session()
_adapter = HTTPAdapter(pool_connections=12, pool_maxsize=12, max_retries=0)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)


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
    payload = {"ext": json.dumps(ext_data), "taskType": 74, "priority": 0,
               "retry_times": 1, "cool_time": 600}
    body = signed_post(f"{DEV_BASE_URL}/Video/CreateUniversalTransparent", payload)
    if body.get("code") != 200:
        raise RuntimeError(f"创建失败: {body}")
    return body["data"]


def get_task_status(task_id: int) -> dict:
    body = signed_post(f"{DEV_BASE_URL}/Task/GetAllTaskStatus",
                       {"taskType": 74, "taskIds": [task_id]})
    if body.get("code") != 200:
        raise RuntimeError(f"查询失败: {body}")
    lst = body.get("data", [])
    return lst[0] if lst else {}


def fms(ms: int) -> str:
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    sec = (ms % 60000) // 1000
    return f"{h:02d}:{m:02d}:{sec:02d},{ms % 1000:03d}"


def fetch_chapter(fname: str, pattern: str):
    text = (TXT / fname).read_text(encoding="utf-8")
    matches = list(re.finditer(pattern, text, flags=re.MULTILINE))
    if not matches:
        raise RuntimeError(f"{fname} 未匹配到章节标记")
    m = matches[0]
    title = m.group().strip("= ").strip()
    start = m.end()
    end = matches[1].start() if len(matches) > 1 else len(text)
    return title, text[start:end].strip()


def download(label: str, data: dict) -> tuple:
    mp3_size = 0
    subs = 0
    audio_url = data.get("audio_url", "")
    meta_url = data.get("metadata_url", "")
    if audio_url:
        r = _session.get(audio_url, timeout=240)
        (OUT / f"{label}.mp3").write_bytes(r.content)
        mp3_size = len(r.content)
    if meta_url:
        r = _session.get(meta_url, timeout=240)
        (OUT / f"{label}.json").write_bytes(r.content)
        segs = json.loads(r.text)
        lines = []
        for s in segs:
            idx = s.get("id", 0) + 1
            sm, em = s.get("startMs", 0), s.get("endMs", 0)
            t = (s.get("text") or "").strip()
            if not t:
                continue
            lines.append(str(idx))
            lines.append(f"{fms(sm)} --> {fms(em)}")
            lines.append(t)
            lines.append("")
        (OUT / f"{label}.srt").write_text("\n".join(lines), encoding="utf-8")
        subs = len([ln for ln in lines if ln and ln[0].isdigit()])
    return mp3_size, subs


def run_one(fname: str, pattern: str, lang: int, voice: str, cn_name: str) -> dict:
    label = f"{cn_name}_XR3_Ch1"
    t0 = time.time()
    try:
        title, content = fetch_chapter(fname, pattern)
    except Exception as e:
        return {"label": label, "lang": cn_name, "ok": False,
                "error": f"{type(e).__name__}: {e}"}

    rec = {"label": label, "lang": cn_name, "voice": voice, "lang_code": lang,
           "title": title, "chars": len(content)}

    try:
        task_id = create_task({
            "read_content": content,
            "chapter_title": title,
            "model": "higgs",
            "lang": lang,
            "voice": voice,
        })
        rec["taskId"] = task_id
        rec["create_elapsed"] = round(time.time() - t0, 2)
    except Exception as e:
        rec.update({"ok": False, "error": f"创建异常 {type(e).__name__}: {e}",
                    "elapsed": round(time.time() - t0, 2)})
        return rec

    status = None
    result = None
    try:
        while time.time() - t0 < POLL_TIMEOUT:
            info = get_task_status(task_id)
            status = info.get("taskStatus")
            if status == 2:
                result = info
                break
            if status == 3:
                rec.update({"ok": False, "status": status,
                            "error": info.get("comment", "任务失败"),
                            "elapsed": round(time.time() - t0, 2)})
                return rec
            time.sleep(POLL_INTERVAL)
    except Exception as e:
        rec.update({"ok": False, "status": status,
                    "error": f"{type(e).__name__}: {e}",
                    "elapsed": round(time.time() - t0, 2)})
        return rec

    rec["elapsed"] = round(time.time() - t0, 2)
    rec["status"] = status
    if not result:
        rec.update({"ok": False, "error": "超时未完成"})
        return rec

    try:
        data = result.get("data", "{}")
        data = json.loads(data) if isinstance(data, str) else data
        mp3_size, subs = download(label, data)
        rec.update({"ok": True, "mp3_size": mp3_size, "subs": subs})
    except Exception as e:
        rec.update({"ok": False, "error": f"下载异常 {type(e).__name__}: {e}"})
    return rec


def main():
    print(f"接口环境: {DEV_BASE_URL} (测试环境)")
    print(f"模型: higgs | 语种数: {len(CONFIGS)} | 每语种取第 1 章\n")

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = [ex.submit(run_one, *cfg) for cfg in CONFIGS]
        for fut in as_completed(futs):
            rec = fut.result()
            results.append(rec)
            if rec.get("ok"):
                print(f"[完成] {rec['label']:14s} taskId={rec['taskId']} "
                      f"耗时={rec['elapsed']:>7.1f}s mp3={rec['mp3_size']:>9,}B 字幕={rec['subs']}")
            else:
                print(f"[失败] {rec['label']:14s} {rec.get('error')}")

    order = {c[4]: i for i, c in enumerate(CONFIGS)}
    results.sort(key=lambda r: order.get(r["lang"], 99))

    print("\n" + "=" * 78)
    print("全语种单章调用结果汇总")
    print("=" * 78)
    print(f"{'语种':<6} {'taskId':>8} {'字符':>7} {'创建(s)':>8} {'总耗时(s)':>10} {'mp3(B)':>10} {'字幕':>5}  状态")
    print("-" * 78)
    for r in results:
        if r.get("ok"):
            print(f"{r['lang']:<6} {r['taskId']:>8} {r['chars']:>7} "
                  f"{r.get('create_elapsed', 0):>8.1f} {r['elapsed']:>10.1f} "
                  f"{r['mp3_size']:>10,} {r['subs']:>5}  成功")
        else:
            print(f"{r['lang']:<6} {str(r.get('taskId', '-')):>8} {r.get('chars', 0):>7} "
                  f"{str(r.get('create_elapsed', '-')):>8} {'-':>10} {'-':>10} {'-':>5}  失败: {r.get('error')}")

    ok = [r for r in results if r.get("ok")]
    print("-" * 78)
    print(f"成功 {len(ok)}/{len(results)}")
    if ok:
        el = [r["elapsed"] for r in ok]
        print(f"耗时: 平均 {sum(el)/len(el):.1f}s / 最小 {min(el):.1f}s / 最大 {max(el):.1f}s")

    (OUT / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n产物目录: {OUT}")


if __name__ == "__main__":
    main()
