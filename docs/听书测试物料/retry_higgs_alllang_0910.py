import os
# -*- coding: utf-8 -*-
"""Higgs 全语种重跑：先短文本探活，通则批量下发 6 语种第 1 章。全过程写日志。"""
import base64, hashlib, hmac, json, re, time
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

BASE = "https://ai-main-none-dev.changdu.ltd"
KEY = os.environ["TTS_SECRET_KEY"]
TXT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\txt文本")
OUT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\Higgs_全语种单章_0910")
LOG = OUT / "retry_run.log"
PROBE_TIMEOUT = 240
POLL_INTERVAL = 5
POLL_TIMEOUT = 900
RETRY = 6

CONFIGS = [
    ("XR3 - EN.txt", r"^===\s*Chapter\s+\d+",   1, "English_female",    "英语"),
    ("XR3 - DE.txt", r"^===\s*Kapitel\s+\d+",   1, "German_female",     "德语"),
    ("XR3 - FR.txt", r"^===\s*Chapitre\s+\d+",  6, "French_female",     "法语"),
    ("XR3 - SP.txt", r"^===\s*Cap[ií]tulo\s+\d+", 4, "Spanish_female", "西语"),
    ("XR3 - PT.txt", r"^===\s*Cap[ií]tulo\s+\d+", 5, "Portuguese_female", "葡语"),
    ("XR3 - RU.txt", r"^===\s*Глава\s+\d+",    1, "Russian_female",    "俄语"),
]

_session = requests.Session()
_session.mount("https://", HTTPAdapter(pool_connections=12, pool_maxsize=12, max_retries=0))
_session.mount("http://", HTTPAdapter(pool_connections=12, pool_maxsize=12, max_retries=0))

def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def sign(t):
    h = hmac.new(KEY.encode(), t.encode(), hashlib.sha256)
    return base64.b64encode(h.digest()).decode()

def post(url, payload, timeout=40):
    body = json.dumps(payload)
    last = None
    for i in range(RETRY):
        try:
            r = _session.post(url, data=body.encode(),
                              headers={"sign": sign(body), "Content-Type": "application/json"}, timeout=timeout)
            return r.json()
        except Exception as e:
            last = e
            time.sleep(min(1 + i * 2, 15))
    raise last

def create(ext):
    b = post(f"{BASE}/Video/CreateUniversalTransparent",
             {"ext": json.dumps(ext), "taskType": 74, "priority": 0, "retry_times": 1, "cool_time": 600})
    if b.get("code") != 200:
        raise RuntimeError("create fail: %s" % b)
    return b["data"]

def status(tid):
    b = post(f"{BASE}/Task/GetAllTaskStatus", {"taskType": 74, "taskIds": [tid]})
    lst = b.get("data", [])
    return lst[0] if lst else {}

def fms(ms):
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms % 1000)

def wait_task(tid, name, timeout):
    t0 = time.time()
    while time.time() - t0 < timeout:
        info = status(tid)
        st = info.get("taskStatus")
        if st == 2:
            return True, round(time.time() - t0, 1), info
        if st == 3:
            return False, round(time.time() - t0, 1), info
        time.sleep(POLL_INTERVAL)
    return None, round(time.time() - t0, 1), None

def download(label, info):
    d = info.get("data", "{}")
    d = json.loads(d) if isinstance(d, str) else d
    mp3_size = 0
    subs = 0
    if d.get("audio_url"):
        r = _session.get(d["audio_url"], timeout=240)
        (OUT / (label + ".mp3")).write_bytes(r.content)
        mp3_size = len(r.content)
    if d.get("metadata_url"):
        r = _session.get(d["metadata_url"], timeout=240)
        (OUT / (label + ".json")).write_bytes(r.content)
        segs = json.loads(r.text)
        lines = []
        for s in segs:
            t = (s.get("text") or "").strip()
            if not t:
                continue
            lines += [str(s.get("id", 0) + 1),
                      "%s --> %s" % (fms(s.get("startMs", 0)), fms(s.get("endMs", 0))), t, ""]
        (OUT / (label + ".srt")).write_text("\n".join(lines), encoding="utf-8")
        subs = len([x for x in lines if x and x[0].isdigit()])
    return mp3_size, subs

def chapter(fname, pattern):
    text = (TXT / fname).read_text(encoding="utf-8")
    ms = list(re.finditer(pattern, text, flags=re.MULTILINE))
    if not ms:
        raise RuntimeError("%s 未匹配到章节" % fname)
    start = ms[0].end()
    end = ms[1].start() if len(ms) > 1 else len(text)
    return text[start:end].strip("= \r\n").strip()

def run_lang(cfg):
    fname, pattern, lang, voice, cn = cfg
    label = "%s_XR3_Ch1" % cn
    t0 = time.time()
    try:
        content = chapter(fname, pattern)
        tid = create({"read_content": content, "chapter_title": "%s Ch1" % cn,
                      "model": "higgs", "lang": lang, "voice": voice})
    except Exception as e:
        return {"label": label, "lang": cn, "ok": False, "error": "%s: %s" % (type(e).__name__, e)}
    ok, el, info = wait_task(tid, label, POLL_TIMEOUT)
    rec = {"label": label, "lang": cn, "taskId": tid, "chars": len(content),
           "elapsed": el, "ok": bool(ok)}
    if ok:
        try:
            rec["mp3_size"], rec["subs"] = download(label, info)
        except Exception as e:
            rec.update({"ok": False, "error": "下载异常 %s" % e})
    else:
        rec["error"] = (info or {}).get("comment") or "status=%s" % ((info or {}).get("taskStatus"))
    return rec

def main():
    if LOG.exists():
        LOG.unlink()
    log("=== 重跑开始 ===")
    log("环境: %s" % BASE)

    probe_text = ("The lighthouse keeper climbed the worn stairs once more, carrying oil "
                  "for the great lamp above the rocks, and the sea kept its own counsel.")
    log("[探活] 提交短文本 ...")
    try:
        ptid = create({"read_content": probe_text, "chapter_title": "Probe",
                       "model": "higgs", "lang": 1, "voice": "English_female"})
    except Exception as e:
        log("[探活] 创建失败: %s" % e)
        return
    log("[探活] taskId=%s" % ptid)
    ok, el, info = wait_task(ptid, "probe", PROBE_TIMEOUT)
    if not ok:
        log("[探活] 未通过 (ok=%s, %ss) -> 服务仍未恢复，停止批量下发" % (ok, el))
        (OUT / "retry_results.json").write_text(json.dumps(
            [{"label": "probe", "taskId": ptid, "ok": False, "elapsed": el}], ensure_ascii=False, indent=2),
            encoding="utf-8")
        return
    log("[探活] 通过 (%ss)，开始 6 语种批量下发" % el)

    results = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(run_lang, c) for c in CONFIGS]
        for f in as_completed(futs):
            r = f.result()
            results.append(r)
            if r.get("ok"):
                log("[完成] %s taskId=%s %ss mp3=%s subs=%s" % (r["label"], r["taskId"], r["elapsed"], r.get("mp3_size"), r.get("subs")))
            else:
                log("[失败] %s %s" % (r["label"], r.get("error")))

    order = {c[4]: i for i, c in enumerate(CONFIGS)}
    results.sort(key=lambda r: order.get(r.get("lang"), 99))
    oks = [r for r in results if r.get("ok")]
    log("=== 汇总: 成功 %d/%d ===" % (len(oks), len(results)))
    if oks:
        el = [r["elapsed"] for r in oks]
        log("耗时 平均 %.1fs / 最小 %.1fs / 最大 %.1fs" % (sum(el)/len(el), min(el), max(el)))
    (OUT / "retry_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    log("=== 重跑结束 ===")

if __name__ == "__main__":
    main()
