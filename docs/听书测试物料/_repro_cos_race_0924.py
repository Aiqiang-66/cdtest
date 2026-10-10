# -*- coding: utf-8 -*-
r"""一次性：定向复现「产物立即可获取性竞态」（任务成功后立刻拉 audio_url，抓到 COS 错误页即留证）。

用法：
  $env:TTS_SECRET_KEY='...'
  & "D:\python\python.exe" docs\听书测试物料\_repro_cos_race_0924.py --lang ja --tasks 24 --workers 8

产物（默认写入开发分析包）：
  <out>/cos_error_<lang>_seq<NN>_<taskId>.txt     第一手 COS 错误响应原文
  <out>/cos_error_<lang>_seq<NN>_<taskId>.json    当时的响应头/长度等元信息
  <out>/cos_race_<lang>.json                      逐任务结果（含延迟若干秒后的重取结果）
"""
import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"D:\python\dmx\cdtest")
D = ROOT / "docs" / "听书测试物料"
BASE = "https://ai-main-none-dev.changdu.ltd"
LANGS = {"ja": (9, "Japanese_female", D / "mp3" / "Higgs_日语_10并发30分钟_0924_r3" / "material"),
         "ko": (14, "Korean_female", D / "mp3" / "Higgs_韩语_10并发30分钟_0924_r3" / "material")}
DEFAULT_OUT = D / "开发分析包_接口与稳定性_0924" / "04_产物可获取性"
POLL_INTERVAL = 3
POLL_TIMEOUT = 900


def sign(key, text):
    return base64.b64encode(hmac.new(key.encode(), text.encode(), hashlib.sha256).digest()).decode()


def is_audio(body: bytes, ctype: str) -> bool:
    if ctype and "audio" in ctype.lower():
        return True
    if body[:3] == b"ID3":
        return True
    if len(body) > 2 and body[0] == 0xFF and (body[1] & 0xE0) == 0xE0:
        return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", required=True, choices=["ja", "ko"])
    ap.add_argument("--tasks", type=int, default=24)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--chars", type=int, default=420, help="每个任务的文本长度（短文本→任务更快，提高竞态命中率）")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    key = os.environ.get("TTS_SECRET_KEY")
    if not key:
        raise SystemExit("缺少环境变量 TTS_SECRET_KEY")
    lang_code, voice, mat = LANGS[args.lang]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    units = sorted(mat.glob("unit_*.txt"))
    texts = []
    for i in range(args.tasks):
        t = units[i % len(units)].read_text(encoding="utf-8").replace("\n", "")
        texts.append(t[: args.chars])

    session = requests.Session()
    session.mount("https://", HTTPAdapter(pool_connections=args.workers * 2, pool_maxsize=args.workers * 2))

    def post(path, payload, timeout=60):
        body = json.dumps(payload)
        return session.post(BASE + path, data=body.encode(),
                            headers={"sign": sign(key, body), "Content-Type": "application/json"},
                            timeout=timeout).json()

    def one(seq):
        rec = {"seq": seq, "chars": len(texts[seq - 1])}
        t0 = time.time()
        try:
            ext = {"read_content": texts[seq - 1], "chapter_title": f"COS竞态复现 {seq}",
                   "model": "higgs", "lang": lang_code, "voice": voice}
            r = post("/Video/CreateUniversalTransparent",
                     {"ext": json.dumps(ext), "taskType": 74, "priority": 0,
                      "retry_times": 1, "cool_time": 600})
            if r.get("code") != 200:
                rec.update(ok=False, error=f"create:{r}")
                return rec
            tid = r["data"]
            rec["taskId"] = tid
            data = {}
            while time.time() - t0 < POLL_TIMEOUT:
                s = post("/Task/GetAllTaskStatus", {"taskType": 74, "taskIds": [tid]})
                lst = s.get("data") or []
                data = lst[0] if lst else {}
                if data.get("taskStatus") in (2, 3):
                    break
                time.sleep(POLL_INTERVAL)
            rec.update(ok=True, status=data.get("taskStatus"), create_s=round(time.time() - t0, 1))
            url = data.get("audio_url")
            rec["audio_url_present"] = bool(url)
            if not url:
                return rec
            # ① 成功后**立刻**拉取
            g = session.get(url, timeout=60)
            body = g.content
            rec["immediate_http"] = g.status_code
            rec["immediate_ct"] = g.headers.get("Content-Type")
            rec["immediate_len"] = len(body)
            rec["immediate_is_audio"] = is_audio(body, g.headers.get("Content-Type"))
            if not rec["immediate_is_audio"]:
                tag = f"cos_error_{args.lang}_seq{seq:02d}_{tid}"
                (out / f"{tag}.txt").write_bytes(body)
                (out / f"{tag}.json").write_text(json.dumps({
                    "lang": args.lang, "seq": seq, "taskId": tid, "audio_url": url,
                    "http_status": g.status_code, "content_type": g.headers.get("Content-Type"),
                    "content_length": g.headers.get("Content-Length"), "body_bytes": len(body),
                    "captured_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "captured_after_task_success_s": round(time.time() - t0, 1),
                }, ensure_ascii=False, indent=2), encoding="utf-8")
                rec["sample_saved"] = tag
                # ② 延迟后重取，验证是否为竞态（最终可读）
                for delay in (10, 30):
                    time.sleep(delay)
                    g2 = session.get(url, timeout=60)
                    if is_audio(g2.content, g2.headers.get("Content-Type")):
                        rec.update(retry_after_s=delay, retry_len=len(g2.content), retry_is_audio=True)
                        break
                else:
                    rec["retry_is_audio"] = False
            return rec
        except Exception as e:
            rec.update(ok=False, error=f"{type(e).__name__}: {e}")
            return rec

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        rows = list(ex.map(one, range(1, args.tasks + 1)))

    hits = [r for r in rows if r.get("immediate_is_audio") is False]
    res = {
        "lang": args.lang, "tasks": args.tasks, "workers": args.workers, "chars": args.chars,
        "captured_at": time.strftime("%Y-%m-%d %H:%M:%S"), "base": BASE,
        "immediate_non_audio": len(hits), "rows": rows,
    }
    (out / f"cos_race_{args.lang}.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{args.lang}] 任务 {len(rows)}｜立即拉取非音频 {len(hits)} 个"
          f"（{'全部延迟重取成功' if hits and all(r.get('retry_is_audio') for r in hits) else '见 JSON'}）")
    for r in hits:
        print(f"    seq {r['seq']} taskId={r['taskId']} http={r.get('immediate_http')} "
              f"ct={r.get('immediate_ct')} len={r.get('immediate_len')} "
              f"→ {r.get('retry_after_s')}s 后重取音频 {r.get('retry_len')} B｜样本 {r.get('sample_saved')}")


if __name__ == "__main__":
    main()
