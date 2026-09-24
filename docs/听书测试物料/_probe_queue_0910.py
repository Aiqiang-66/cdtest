import os
# -*- coding: utf-8 -*-
"""队列对照探活：normal(priority=0) vs High(priority=1)，同时验证语音参数是否影响出音频。"""
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

KEY = os.environ["TTS_SECRET_KEY"]
OUT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\Higgs_全语种单章_0910")
TXT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\txt文本")
HOSTS = [
    "https://ai-main-none-new-dev.changdu.ltd",
    "https://ai-main-none-dev.changdu.ltd",
]
SHORT = ("The lighthouse keeper climbed the worn stairs once more, carrying oil "
         "for the great lamp above the rocks, and the sea kept its own counsel.")
POLL_TOTAL = 300
POLL_STEP = 10


def sign(t):
    return base64.b64encode(hmac.new(KEY.encode(), t.encode(), hashlib.sha256).digest()).decode()


def post(host, path, payload, timeout=40):
    body = json.dumps(payload)
    headers = {"sign": sign(body), "Content-Type": "application/json"}
    t0 = time.time()
    r = requests.post(host + path, data=body.encode(), headers=headers, timeout=timeout)
    return r.status_code, r.json(), round(time.time() - t0, 3)


def xr3_ch1(fname, pattern):
    text = (TXT / fname).read_text(encoding="utf-8")
    ms = list(re.finditer(pattern, text, flags=re.MULTILINE))
    start = ms[0].end()
    end = ms[1].start() if len(ms) > 1 else len(text)
    return text[start:end].strip()


def main():
    long_en = xr3_ch1("XR3 - EN.txt", r"^===\s*Chapter\s+\d+")
    cases = [
        ("normal_short_defaultvoice", 0, SHORT, 3, "audiobook_female_2"),
        ("high_short_defaultvoice", 1, SHORT, 3, "audiobook_female_2"),
        ("normal_short_xr3voice", 0, SHORT, 1, "English_female"),
        ("normal_ch1_xr3voice", 0, long_en[:6000], 1, "English_female"),
    ]
    created = []
    for host in HOSTS:
        for name, prio, text, lang, voice in cases:
            label = "%s@%s" % (name, host.split("//")[1].split(".")[0])
            ext = {"read_content": text, "chapter_title": "Probe-0910",
                   "model": "higgs", "lang": lang, "voice": voice}
            payload = {"ext": json.dumps(ext), "taskType": 74, "priority": prio,
                       "retry_times": 1, "cool_time": 600}
            try:
                code, body, el = post(host, "/Video/CreateUniversalTransparent", payload)
                if body.get("code") == 200:
                    created.append({"label": label, "host": host, "taskId": body["data"],
                                    "create_s": el, "chars": len(text), "priority": prio,
                                    "lang": lang, "voice": voice, "last": None})
                    print("[create OK] %-42s taskId=%-8s %.2fs chars=%d" % (label, body["data"], el, len(text)), flush=True)
                else:
                    print("[create FAIL] %-42s %s" % (label, json.dumps(body, ensure_ascii=False)[:200]), flush=True)
            except Exception as e:
                print("[create ERR] %-42s %s: %s" % (label, type(e).__name__, str(e)[:150]), flush=True)

    deadline = time.time() + POLL_TOTAL
    while time.time() < deadline and created:
        pending = [c for c in created if c["last"] not in (2, 3)]
        if not pending:
            break
        for c in pending:
            try:
                _, body, _ = post(c["host"], "/Task/GetAllTaskStatus",
                                  {"taskType": 74, "taskIds": [c["taskId"]]})
                item = (body.get("data") or [{}])[0]
                st = item.get("taskStatus")
                if st != c["last"]:
                    print("  [%s] status %s -> %s (t=%ds)" % (c["label"], c["last"], st,
                          int(POLL_TOTAL - (deadline - time.time()))), flush=True)
                c["last"] = st
                if st in (2, 3):
                    c["final"] = item
            except Exception as e:
                print("  [%s] poll err %s" % (c["label"], str(e)[:100]), flush=True)
        time.sleep(POLL_STEP)

    lines = []
    for c in created:
        d = c.get("final") or {}
        raw = d.get("data") or ""
        extra = ""
        if isinstance(raw, str) and raw.startswith("{"):
            try:
                dd = json.loads(raw)
                extra = "audio=%s meta=%s" % (str(dd.get("audio_url"))[:60], str(dd.get("metadata_url"))[:60])
            except Exception:
                extra = raw[:120]
        lines.append("%-42s taskId=%-8s prio=%s lang=%s voice=%-18s chars=%-5s create=%ss lastStatus=%s %s"
                     % (c["label"], c["taskId"], c["priority"], c["lang"], c["voice"],
                        c["chars"], c["create_s"], c["last"], extra))
    text = "\n".join(lines)
    print("\n===== SUMMARY =====\n" + text, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "probe_queue_0910.log").write_text(text, encoding="utf-8")
    (OUT / "probe_queue_0910.json").write_text(
        json.dumps([{k: v for k, v in c.items() if k != "final"} | {"final": c.get("final")} for c in created],
                   ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
