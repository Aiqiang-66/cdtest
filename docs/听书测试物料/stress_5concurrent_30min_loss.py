import os
# -*- coding: utf-8 -*-
r"""Higgs TTS v3 五并发打满 30 分钟 —— 发送文案 vs 返回文案 丢失核查。

背景：并发量增大后，请求文案与返回文案不一致，返回文案存在丢失。
口径：模型端 5 并发，压测固定 5 路并发持续打满 30 分钟；单任务文案约 500 词。
记录：每个任务的发送文案全文、接口返回 metadata 的文案全文、token 级缺失/多余、
      创建耗时、端到端耗时，逐条追加写入 tasks.jsonl。

输出目录：docs\听书测试物料\mp3\Higgs_5并发30分钟_丢失核查_0910\
  tasks.jsonl               每任务一行（含发送/返回全文）
  meta\task_0001.json       接口返回的 metadata 原文
  src\task_0001.txt         实际提交的文案
  progress.log              运行日志
  summary.json              本脚本的即时统计
"""
import base64
import difflib
import hashlib
import hmac
import json
import re
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
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
BOOK = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\txt文本\XR3 - EN.txt")
OUT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\Higgs_5并发30分钟_丢失核查_0910")

RUN_SECONDS = 1800      # 打满 30 分钟
WORKERS = 5             # 与模型端并发上限一致
WINDOW_WORDS = 500      # 单任务文案词量
STEP_WORDS = 37         # 滑窗步长（与 500 互质，尽量让每个任务文案不同）
POLL_INTERVAL = 3
POLL_TIMEOUT = 900
DRAIN_TIMEOUT = 900     # 收尾：等待在途任务的最长时间
RETRY = 4

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "meta").mkdir(exist_ok=True)
(OUT / "src").mkdir(exist_ok=True)

_session = requests.Session()
_adapter = HTTPAdapter(pool_connections=WORKERS * 2, pool_maxsize=WORKERS * 2, max_retries=0)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)

_lock = threading.Lock()
_log_lines = []


def log(msg: str):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    with _lock:
        print(line, flush=True)
        _log_lines.append(line)
        (OUT / "progress.log").write_text("\n".join(_log_lines), encoding="utf-8")


def sign(text: str) -> str:
    return base64.b64encode(hmac.new(SECRET_KEY.encode(), text.encode(), hashlib.sha256).digest()).decode()


def signed_post(path: str, payload: dict, timeout: int = 40) -> dict:
    body = json.dumps(payload)
    headers = {"sign": sign(body), "Content-Type": "application/json"}
    last = None
    for i in range(RETRY):
        try:
            r = _session.post(DEV_BASE_URL + path, data=body.encode(), headers=headers, timeout=timeout)
            return r.json()
        except Exception as e:
            last = e
            time.sleep(min(1 + i * 2, 10))
    raise last


def create_task(ext_data: dict) -> int:
    payload = {"ext": json.dumps(ext_data), "taskType": 74, "priority": 0,
               "retry_times": 1, "cool_time": 600}
    body = signed_post("/Video/CreateUniversalTransparent", payload)
    if body.get("code") != 200:
        raise RuntimeError(f"创建失败: {body}")
    return body["data"]


def get_task_status(task_id: int) -> dict:
    body = signed_post("/Task/GetAllTaskStatus", {"taskType": 74, "taskIds": [task_id]})
    if body.get("code") != 200:
        raise RuntimeError(f"查询失败: {body}")
    lst = body.get("data", [])
    return lst[0] if lst else {}


_EDGE_PUNCT = re.compile(r"^[^\w']+|[^\w']+$")


def norm_tokens(s: str):
    """归一化到可比较的 token：全角转半角、统一引号、去首尾标点、小写。"""
    s = unicodedata.normalize("NFKC", s)
    s = (s.replace("\u2019", "'").replace("\u2018", "'")
          .replace("\u201c", '"').replace("\u201d", '"')
          .replace("\u2014", " ").replace("\u2013", " ").replace("\u2015", " "))
    out = []
    for t in s.split():
        t = _EDGE_PUNCT.sub("", t).lower()
        if t:
            out.append(t)
    return out


def diff_stats(sent_tokens, ret_tokens):
    """返回 token 级缺失（发送有、返回无）与多余（返回有、发送无）明细。"""
    sm = difflib.SequenceMatcher(a=sent_tokens, b=ret_tokens, autojunk=False)
    missing, extra = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("delete", "replace"):
            missing.extend(sent_tokens[i1:i2])
        if tag in ("insert", "replace"):
            extra.extend(ret_tokens[j1:j2])
    return missing, extra, sm.ratio()


def build_windows():
    text = BOOK.read_text(encoding="utf-8-sig")
    # 去掉 "=== Chapter N ===" 之类的章节标记行
    text = re.sub(r"^=+.*$", " ", text, flags=re.MULTILINE)
    words = text.split()
    windows = []
    i = 0
    while i + WINDOW_WORDS <= len(words):
        windows.append(" ".join(words[i:i + WINDOW_WORDS]))
        i += STEP_WORDS
    return windows


def run_task(seq: int, content: str, deadline: float) -> dict:
    title = f"Stress {seq:04d}"
    rec = {"seq": seq, "taskId": None, "chapter_title": title,
           "chars": len(content), "sent_words": len(norm_tokens(content)),
           "ok": False, "start_ts": round(time.time(), 3)}
    (OUT / "src" / f"task_{seq:04d}.txt").write_text(content, encoding="utf-8")

    t0 = time.time()
    try:
        rec["taskId"] = create_task({"read_content": content, "chapter_title": title,
                                     "model": "higgs", "lang": 1, "voice": "English_female"})
        rec["create_s"] = round(time.time() - t0, 3)
    except Exception as e:
        rec.update({"error": f"create {type(e).__name__}: {e}", "elapsed_s": round(time.time() - t0, 2)})
        return rec

    meta = None
    status = None
    while time.time() - t0 < POLL_TIMEOUT and time.time() < deadline + DRAIN_TIMEOUT:
        try:
            info = get_task_status(rec["taskId"])
        except Exception as e:
            rec.setdefault("poll_errors", []).append(f"{type(e).__name__}: {e}")
            time.sleep(POLL_INTERVAL)
            continue
        status = info.get("taskStatus")
        if status == 2:
            data = info.get("data", "{}")
            meta = json.loads(data) if isinstance(data, str) else data
            break
        if status == 3:
            rec.update({"status": 3, "error": f"任务失败 comment={info.get('comment')}",
                        "elapsed_s": round(time.time() - t0, 2)})
            return rec
        time.sleep(POLL_INTERVAL)

    rec["elapsed_s"] = round(time.time() - t0, 2)
    rec["status"] = status
    if not meta:
        rec["error"] = "超时未产出结果"
        return rec

    rec["audio_url"] = meta.get("audio_url", "")
    rec["metadata_url"] = meta.get("metadata_url", "")
    try:
        r = _session.get(rec["metadata_url"], timeout=120)
        (OUT / "meta" / f"task_{seq:04d}.json").write_bytes(r.content)
        segs = json.loads(r.text)
    except Exception as e:
        rec["error"] = f"metadata 下载/解析失败 {type(e).__name__}: {e}"
        return rec

    ret_tokens = []
    for s in segs:
        ret_tokens.extend(norm_tokens(s.get("text") or ""))
    title_tokens = norm_tokens(title)
    title_in_meta = ret_tokens[:len(title_tokens)] == title_tokens
    if title_in_meta:
        ret_tokens = ret_tokens[len(title_tokens):]

    sent_tokens = norm_tokens(content)
    missing, extra, ratio = diff_stats(sent_tokens, ret_tokens)
    rec.update({
        "ok": True,
        "segments": len(segs),
        "title_in_meta": title_in_meta,
        "sent_tokens": len(sent_tokens),
        "ret_tokens": len(ret_tokens),
        "missing_count": len(missing),
        "missing_ratio": round(len(missing) / max(1, len(sent_tokens)), 4),
        "extra_count": len(extra),
        "extra_ratio": round(len(extra) / max(1, len(sent_tokens)), 4),
        "similarity": round(ratio, 4),
        "missing_head": missing[:40],
        "extra_head": extra[:20],
        "sent_text": content,
        "ret_text": " ".join(ret_tokens),
    })
    return rec


def worker(wid: int, windows, stop_at: float, results, results_path):
    idx = wid
    while time.time() < stop_at:
        content = windows[idx % len(windows)]
        rec = run_task(idx, content, stop_at)
        rec["worker"] = wid
        rec["window_index"] = idx % len(windows)
        with _lock:
            results.append(rec)
            with results_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if rec.get("ok"):
            log("[w%d] #%04d taskId=%s 耗时=%ss 段=%s 发送token=%d 返回token=%d 缺失=%d(%.2f%%) 多余=%d 相似度=%.4f"
                % (wid, rec["seq"], rec["taskId"], rec["elapsed_s"], rec["segments"],
                   rec["sent_tokens"], rec["ret_tokens"], rec["missing_count"],
                   rec["missing_ratio"] * 100, rec["extra_count"], rec["similarity"]))
        else:
            log("[w%d] #%04d taskId=%s 异常: %s" % (wid, rec["seq"], rec.get("taskId"), rec.get("error")))
        idx += WORKERS


def main():
    windows = build_windows()
    results_path = OUT / "tasks.jsonl"
    results_path.write_text("", encoding="utf-8")
    log(f"接口环境 {DEV_BASE_URL}｜模型 higgs｜并发 {WORKERS}｜时长 {RUN_SECONDS}s｜"
        f"单任务 {WINDOW_WORDS} 词（滑窗 {len(windows)} 个不同文案）")

    start = time.time()
    stop_at = start + RUN_SECONDS
    results = []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = [ex.submit(worker, wid, windows, stop_at, results, results_path) for wid in range(WORKERS)]
        for f in futs:
            f.result()
    wall = time.time() - start

    ok = [r for r in results if r.get("ok")]
    bad = [r for r in results if not r.get("ok")]
    lossy = [r for r in ok if r["missing_count"] > 0]
    summary = {
        "run_seconds": round(wall, 1),
        "workers": WORKERS,
        "total_tasks": len(results),
        "ok": len(ok),
        "failed": len(bad),
        "tasks_with_missing": len(lossy),
        "total_missing_tokens": sum(r["missing_count"] for r in ok),
        "total_sent_tokens": sum(r["sent_tokens"] for r in ok),
        "max_missing_ratio": max([r["missing_ratio"] for r in ok], default=0),
        "throughput_per_min": round(len(results) / (wall / 60), 2),
        "endpoint": DEV_BASE_URL,
        "model": "higgs",
        "window_words": WINDOW_WORDS,
        "distinct_texts": len(windows),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    log("=" * 70)
    log("压测结束：总任务 %d｜成功 %d｜失败 %d｜存在缺失的任务 %d"
        % (len(results), len(ok), len(bad), len(lossy)))
    if ok:
        log("发送 token 合计 %d，缺失 token 合计 %d（%.3f%%）"
            % (summary["total_sent_tokens"], summary["total_missing_tokens"],
               100.0 * summary["total_missing_tokens"] / max(1, summary["total_sent_tokens"])))
        el = [r["elapsed_s"] for r in ok]
        log("单任务耗时：平均 %.1fs 最小 %.1fs 最大 %.1fs｜吞吐 %.2f 任务/分钟"
            % (sum(el) / len(el), min(el), max(el), summary["throughput_per_min"]))
    log(f"结果目录 {OUT}")


if __name__ == "__main__":
    main()
