import os
# -*- coding: utf-8 -*-
r"""日语 / 韩语 Higgs TTS v3 —— 10 并发 × 30 分钟性能 + 文案/字幕完整性压测。

口径（链路 A，taskType=74）：
  接口 https://ai-main-none-dev.changdu.ltd  模型 higgs
  日语 lang=9  voice=Japanese_female
  韩语 lang=14 voice=Korean_female
  语料 build_ja_ko_5000char_material.py 生成的 ~5000 字符完整句单元（每任务一个不同单元，轮转）

同时留证（技能必测项）：
  M1 输入/输出文案一致性：日语按**字级**、韩语按**词级**（并附字级）做序列对齐，统计缺失/多余；
  M5 字幕完整性：segments 条数 / distinct paraIndex / paraIndex 缺口 / 空字幕段 / 时间轴空洞 / SRT 条目数；
  性能：创建耗时、端到端耗时（供 P50/P95/P99）、吞吐、成功率。

产物（<批次目录>/）：
  src/task_XXXX.txt       实际下发文案（M1 通道 A 的前提，必须落盘）
  meta/task_XXXX.json     接口返回 metadata 原文
  srt/task_XXXX.srt       由 metadata 派生的字幕（M5 ③）
  audio/task_XXXX.mp3     音频产物（M2 客观音质 / M3 ASR 复核用）
  tasks.jsonl             每任务一行明细（含发送/返回全文与统计）
  summary.json            即时汇总
  progress.log            运行日志

用法：
  & "D:\python\python.exe" docs\听书测试物料\run_higgs_ja_ko_10concurrent_30min.py --lang ja
  & "D:\python\python.exe" docs\听书测试物料\run_higgs_ja_ko_10concurrent_30min.py --lang ko
"""
import argparse
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

BASE_URL = "https://ai-main-none-dev.changdu.ltd"
SECRET_KEY = os.environ["TTS_SECRET_KEY"]
MP3_ROOT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3")

LANGS = {
    "ja": {"cn": "日语", "lang": 9, "voice": "Japanese_female", "unit": "char",
           "run_dir": MP3_ROOT / "Higgs_日语_10并发30分钟_0924"},
    "ko": {"cn": "韩语", "lang": 14, "voice": "Korean_female", "unit": "word",
           "run_dir": MP3_ROOT / "Higgs_韩语_10并发30分钟_0924"},
}

POLL_INTERVAL = 5
POLL_TIMEOUT = 2400        # 单任务最长等待（5000 字符长文案）
DRAIN_TIMEOUT = 1500       # 收尾等待在途任务
RETRY = 4
HOLE_MS = 3000             # 时间轴空洞判定：相邻段间隔 > 3s

_EDGE_PUNCT = re.compile(r"^[^\w']+|[^\w']+$")


def build_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", required=True, choices=sorted(LANGS))
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--minutes", type=float, default=30.0)
    ap.add_argument("--limit", type=int, default=0, help=">0 时只跑该数量任务（调试用）")
    ap.add_argument("--suffix", default="", help="批次目录后缀（如 _r2），避免覆盖历史批次")
    return ap.parse_args()


class Runner:
    def __init__(self, cfg, workers, run_seconds, limit):
        self.cfg = cfg
        self.workers = workers
        self.run_seconds = run_seconds
        self.limit = limit
        self.out = cfg["run_dir"]
        self.mat = self.out / "material"
        for sub in ("src", "meta", "srt", "audio"):
            (self.out / sub).mkdir(parents=True, exist_ok=True)

        self.units = [json.loads(l) for l in (self.mat / "units.jsonl").read_text(encoding="utf-8").splitlines()]
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=workers * 3, pool_maxsize=workers * 3, max_retries=0)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self.lock = threading.Lock()
        self.log_lines = []
        self.seq = 0
        self.unit_cursor = 0
        self.results = []
        self.results_path = self.out / "tasks.jsonl"

    # ---------- 基础设施 ----------
    def log(self, msg):
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        with self.lock:
            print(line, flush=True)
            self.log_lines.append(line)
            (self.out / "progress.log").write_text("\n".join(self.log_lines), encoding="utf-8")

    @staticmethod
    def sign(text):
        return base64.b64encode(hmac.new(SECRET_KEY.encode(), text.encode(), hashlib.sha256).digest()).decode()

    def post(self, path, payload, timeout=60):
        body = json.dumps(payload)
        headers = {"sign": self.sign(body), "Content-Type": "application/json"}
        last = None
        for i in range(RETRY):
            try:
                return self.session.post(BASE_URL + path, data=body.encode(), headers=headers, timeout=timeout).json()
            except Exception as e:
                last = e
                time.sleep(min(1 + i * 2, 10))
        raise last

    def create_task(self, ext):
        body = self.post("/Video/CreateUniversalTransparent",
                         {"ext": json.dumps(ext), "taskType": 74, "priority": 0,
                          "retry_times": 1, "cool_time": 600})
        if body.get("code") != 200:
            raise RuntimeError(f"创建失败: {body}")
        return body["data"]

    def task_status(self, tid):
        body = self.post("/Task/GetAllTaskStatus", {"taskType": 74, "taskIds": [tid]})
        if body.get("code") != 200:
            raise RuntimeError(f"查询失败: {body}")
        lst = body.get("data", [])
        return lst[0] if lst else {}

    # ---------- 文本口径 ----------
    @staticmethod
    def word_tokens(s):
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

    @staticmethod
    def char_tokens(s):
        s = unicodedata.normalize("NFKC", s)
        return [c for c in s if not c.isspace()]

    @staticmethod
    def diff_stats(sent, ret):
        if sent == ret:
            return [], [], 1.0
        sm = difflib.SequenceMatcher(a=sent, b=ret, autojunk=False)
        missing, extra = [], []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag in ("delete", "replace"):
                missing.extend(sent[i1:i2])
            if tag in ("insert", "replace"):
                extra.extend(ret[j1:j2])
        return missing, extra, sm.ratio()

    @staticmethod
    def fms(ms):
        return "%02d:%02d:%02d,%03d" % (ms // 3600000, (ms % 3600000) // 60000,
                                        (ms % 60000) // 1000, ms % 1000)

    # ---------- 单任务 ----------
    def next_unit(self):
        with self.lock:
            u = self.units[self.unit_cursor % len(self.units)]
            idx = self.unit_cursor % len(self.units)
            self.unit_cursor += 1
            self.seq += 1
            return self.seq, idx, u

    def run_task(self, seq, unit_idx, unit, deadline):
        content = (self.mat / f"{unit['unit']}.txt").read_text(encoding="utf-8")
        title = unit["title"]
        rec = {"seq": seq, "unit": unit["unit"], "unit_index": unit_idx, "chapter_title": title,
               "chars": len(content), "start_ts": round(time.time(), 3), "ok": False}
        (self.out / "src" / f"task_{seq:04d}.txt").write_text(content, encoding="utf-8")

        t0 = time.time()
        try:
            rec["taskId"] = self.create_task({"read_content": content, "chapter_title": title,
                                              "model": "higgs", "lang": self.cfg["lang"],
                                              "voice": self.cfg["voice"]})
            rec["create_s"] = round(time.time() - t0, 3)
        except Exception as e:
            rec.update({"error": f"create {type(e).__name__}: {e}", "elapsed_s": round(time.time() - t0, 2)})
            return rec

        info, status = None, None
        while time.time() - t0 < POLL_TIMEOUT and time.time() < deadline + DRAIN_TIMEOUT:
            try:
                info = self.task_status(rec["taskId"])
            except Exception as e:
                rec.setdefault("poll_errors", []).append(f"{type(e).__name__}: {e}")
                time.sleep(POLL_INTERVAL)
                continue
            status = info.get("taskStatus")
            if status == 2:
                break
            if status == 3:
                rec.update({"status": 3, "error": f"任务失败 comment={info.get('comment')}",
                            "elapsed_s": round(time.time() - t0, 2)})
                return rec
            time.sleep(POLL_INTERVAL)

        rec["elapsed_s"] = round(time.time() - t0, 2)
        rec["status"] = status
        if status != 2 or not info:
            rec["error"] = f"超时/未成功 status={status}"
            return rec

        data = info.get("data", "{}")
        data = json.loads(data) if isinstance(data, str) else data
        rec["audio_url_present"] = bool(data.get("audio_url"))
        rec["metadata_url_present"] = bool(data.get("metadata_url"))

        # meta + SRT
        try:
            r = self.session.get(data["metadata_url"], timeout=180)
            (self.out / "meta" / f"task_{seq:04d}.json").write_bytes(r.content)
            segs = json.loads(r.text)
        except Exception as e:
            rec["error"] = f"metadata 下载/解析失败 {type(e).__name__}: {e}"
            return rec

        lines, srt_entries = [], 0
        for s in segs:
            t = (s.get("text") or "").strip()
            if not t:
                continue
            srt_entries += 1
            lines += [str(srt_entries), f"{self.fms(s.get('startMs', 0))} --> {self.fms(s.get('endMs', 0))}", t, ""]
        (self.out / "srt" / f"task_{seq:04d}.srt").write_text("\n".join(lines), encoding="utf-8")

        body = [s for s in segs if s.get("paraIndex", -1) >= 0]
        title_segs = [s for s in segs if s.get("paraIndex", -1) < 0]
        pas = sorted(s["paraIndex"] for s in body)
        gaps = [i for i in range(min(pas), max(pas) + 1) if i not in set(pas)] if pas else []
        empty_segs = sum(1 for s in segs if not (s.get("text") or "").strip())
        times = sorted((s.get("startMs", 0), s.get("endMs", 0)) for s in segs if (s.get("text") or "").strip())
        holes = [(times[i][1], times[i + 1][0], times[i + 1][0] - times[i][1])
                 for i in range(len(times) - 1) if times[i + 1][0] - times[i][1] > HOLE_MS]

        ret_text = " ".join((s.get("text") or "") for s in body)
        sent_chars, ret_chars = self.char_tokens(content), self.char_tokens(ret_text)
        sent_words, ret_words = self.word_tokens(content), self.word_tokens(ret_text)
        primary_sent, primary_ret = ((sent_chars, ret_chars) if self.cfg["unit"] == "char"
                                     else (sent_words, ret_words))
        m, e, ratio = self.diff_stats(primary_sent, primary_ret)
        m_c, e_c, ratio_c = self.diff_stats(sent_chars, ret_chars)

        # ── 段级异常标记（0924 复盘新增）：超长段 / 不可能语速 / 疑似静默段 ──
        seg_stats = []
        for s in body:
            t = (s.get("text") or "").strip()
            d = (s.get("endMs", 0) - s.get("startMs", 0)) / 1000.0
            seg_stats.append((len(t), d, (len(t) / d) if d > 0 else 0.0, t))
        audio_total_s = (max((s.get("endMs", 0) for s in segs), default=0)) / 1000.0
        by_chars = max(seg_stats, key=lambda x: x[0]) if seg_stats else (0, 0.0, 0.0, "")
        by_dur = max(seg_stats, key=lambda x: x[1]) if seg_stats else (0, 0.0, 0.0, "")
        sent_chars_n = len(self.char_tokens(content))
        rec.update({
            "audio_total_s": round(audio_total_s, 2),
            "task_chars_per_s": round(sent_chars_n / audio_total_s, 2) if audio_total_s else None,
            "seg_chars_median": (sorted(x[0] for x in seg_stats)[len(seg_stats) // 2] if seg_stats else 0),
            "max_seg_chars": by_chars[0], "max_seg_dur_s": round(by_chars[1], 2),
            "max_seg_rate": round(by_chars[2], 1), "max_seg_head": by_chars[3][:60],
            "maxdur_seg_chars": by_dur[0], "maxdur_seg_dur_s": round(by_dur[1], 2),
            "maxdur_seg_rate": round(by_dur[2], 2), "maxdur_seg_head": by_dur[3][:60],
            "n_seg_gt200": sum(1 for x in seg_stats if x[0] > 200),
            "n_seg_rate_gt15": sum(1 for x in seg_stats if x[1] > 0.5 and x[2] > 15),
            "n_seg_rate_lt2": sum(1 for x in seg_stats if x[1] > 5 and x[2] < 2),
        })

        rec.update({
            "ok": True,
            "segments_total": len(segs),
            "title_segments": len(title_segs),
            "body_segments": len(body),
            "distinct_para": len(set(pas)),
            "para_gaps": len(gaps),
            "empty_segments": empty_segs,
            "srt_entries": srt_entries,
            "holes": len(holes),
            "hole_max_ms": max([h[2] for h in holes], default=0),
            "meta_first_startMs": segs[0].get("startMs") if segs else None,
            "meta_last_endMs": max([s.get("endMs", 0) for s in segs], default=0),
            "sent_primary_tokens": len(primary_sent),
            "ret_primary_tokens": len(primary_ret),
            "missing": len(m), "missing_ratio": round(len(m) / max(1, len(primary_sent)), 6),
            "extra": len(e), "similarity": round(ratio, 4),
            "sent_chars": len(sent_chars), "ret_chars": len(ret_chars),
            "missing_chars": len(m_c), "extra_chars": len(e_c),
            "missing_char_ratio": round(len(m_c) / max(1, len(sent_chars)), 6),
            "similarity_char": round(ratio_c, 4),
            "missing_head": m[:60], "extra_head": e[:20],
            "sent_text": content, "ret_text": ret_text,
        })

        # 音频留证（M2/M3 用）
        if data.get("audio_url"):
            try:
                r = self.session.get(data["audio_url"], timeout=600)
                (self.out / "audio" / f"task_{seq:04d}.mp3").write_bytes(r.content)
                rec["audio_bytes"] = len(r.content)
            except Exception as e:
                rec["audio_error"] = f"{type(e).__name__}: {e}"
        return rec

    # ---------- 主流程 ----------
    def run(self):
        self.results_path.write_text("", encoding="utf-8")
        m = json.loads((self.mat / "manifest.json").read_text(encoding="utf-8"))
        self.log(f"环境 {BASE_URL}｜模型 higgs｜语种 {m['lang_cn']}({self.cfg['lang']})｜"
                 f"音色 {self.cfg['voice']}｜并发 {self.workers}｜时长 {int(self.run_seconds)}s｜"
                 f"单任务 ~{m['target_chars']} 字符（{len(self.units)} 个不同单元，轮转）")

        start = time.time()
        stop_at = start + self.run_seconds

        def worker(wid):
            while time.time() < stop_at:
                with self.lock:
                    if self.limit and len(self.results) >= self.limit:
                        return
                seq, idx, unit = self.next_unit()
                rec = self.run_task(seq, idx, unit, stop_at)
                rec["worker"] = wid
                with self.lock:
                    self.results.append(rec)
                    with self.results_path.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                if rec.get("ok"):
                    self.log("[w%d] #%04d %s taskId=%s 创建=%ss 端到端=%ss 段=%d(题%d/文%d) "
                             "para缺口=%d 空字幕=%d 空洞=%d SRT=%d 缺失=%d(%.4f%%) 缺字=%d(%.4f%%) 相似=%.4f "
                             "｜语速=%.2f字/秒 最长段=%d字/%.1fs 超长段=%d 高语速段=%d"
                             % (wid, rec["seq"], rec["unit"], rec["taskId"], rec["create_s"], rec["elapsed_s"],
                                rec["segments_total"], rec["title_segments"], rec["body_segments"],
                                rec["para_gaps"], rec["empty_segments"], rec["holes"], rec["srt_entries"],
                                rec["missing"], rec["missing_ratio"] * 100,
                                rec["missing_chars"], rec["missing_char_ratio"] * 100, rec["similarity"],
                                rec.get("task_chars_per_s") or 0, rec.get("max_seg_chars") or 0,
                                rec.get("max_seg_dur_s") or 0, rec.get("n_seg_gt200") or 0,
                                rec.get("n_seg_rate_gt15") or 0))
                else:
                    self.log("[w%d] #%04d %s 异常: %s" % (wid, rec["seq"], rec["unit"], rec.get("error")))

        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            futs = [ex.submit(worker, w) for w in range(self.workers)]
            for f in futs:
                f.result()
        wall = time.time() - start

        ok = [r for r in self.results if r.get("ok")]
        bad = [r for r in self.results if not r.get("ok")]
        el = sorted(r["elapsed_s"] for r in ok)
        ct = sorted(r["create_s"] for r in ok)

        def pct(a, q):
            return round(a[min(len(a) - 1, int(len(a) * q))], 2) if a else None

        lossy = [r for r in ok if r["missing_chars"] > 0]
        summary = {
            "lang": self.cfg["lang"], "lang_cn": m["lang_cn"], "lang_code": self.cfg["lang"],
            "voice": self.cfg["voice"], "model": "higgs", "endpoint": BASE_URL,
            "workers": self.workers, "run_seconds": round(wall, 1),
            "target_chars": m["target_chars"], "distinct_units": len(self.units),
            "total_tasks": len(self.results), "ok": len(ok), "failed": len(bad),
            "success_rate": round(len(ok) / max(1, len(self.results)), 4),
            "throughput_per_min": round(len(self.results) / (wall / 60), 3),
            "elapsed_p50": pct(el, 0.5), "elapsed_p90": pct(el, 0.9),
            "elapsed_p95": pct(el, 0.95), "elapsed_p99": pct(el, 0.99),
            "elapsed_min": round(el[0], 2) if el else None, "elapsed_max": round(el[-1], 2) if el else None,
            "elapsed_avg": round(sum(el) / len(el), 2) if el else None,
            "create_avg": round(sum(ct) / len(ct), 3) if ct else None,
            "create_min": round(ct[0], 3) if ct else None, "create_max": round(ct[-1], 3) if ct else None,
            "sent_chars_total": sum(r["sent_chars"] for r in ok),
            "ret_chars_total": sum(r["ret_chars"] for r in ok),
            "missing_chars_total": sum(r["missing_chars"] for r in ok),
            "extra_chars_total": sum(r["extra_chars"] for r in ok),
            "tasks_with_missing_chars": len(lossy),
            "missing_char_ratio_overall": round(sum(r["missing_chars"] for r in ok)
                                                / max(1, sum(r["sent_chars"] for r in ok)), 6),
            "tasks_with_para_gaps": sum(1 for r in ok if r["para_gaps"] > 0),
            "tasks_with_empty_segments": sum(1 for r in ok if r["empty_segments"] > 0),
            "tasks_with_holes": sum(1 for r in ok if r["holes"] > 0),
            "srt_ne_segments_tasks": sum(1 for r in ok if r["srt_entries"] != r["segments_total"]),
            "body_lt_distinct_para_tasks": sum(1 for r in ok if r["body_segments"] < r["distinct_para"]),
            "audio_bytes_total": sum(r.get("audio_bytes", 0) for r in ok),
        }
        # ── 段级/内容缺失相关汇总（0924 复盘新增）──
        rates = sorted(r["task_chars_per_s"] for r in ok if r.get("task_chars_per_s"))
        base = rates[len(rates) // 2] if rates else None
        suspect = []
        for r in ok:
            if not base or not r.get("task_chars_per_s"):
                continue
            need = r["sent_chars"] / base
            est = max(0.0, 1 - r["audio_total_s"] / need) if need and r["audio_total_s"] < need else 0.0
            r["est_missing_ratio"] = round(est, 4)
            if r["n_seg_gt200"] > 0 or r["n_seg_rate_gt15"] > 0 or r["n_seg_rate_lt2"] > 0 or est > 0.2:
                suspect.append({
                    "seq": r["seq"], "taskId": r["taskId"], "unit": r["unit"],
                    "chars": r["sent_chars"], "audio_s": r["audio_total_s"],
                    "chars_per_s": r["task_chars_per_s"], "max_seg_chars": r["max_seg_chars"],
                    "max_seg_dur_s": r["max_seg_dur_s"], "max_seg_rate": r["max_seg_rate"],
                    "n_seg_gt200": r["n_seg_gt200"], "n_seg_rate_gt15": r["n_seg_rate_gt15"],
                    "n_seg_rate_lt2": r["n_seg_rate_lt2"], "est_missing_ratio": est,
                    "max_seg_head": r["max_seg_head"],
                })
        suspect.sort(key=lambda x: (-x["est_missing_ratio"], -x["max_seg_chars"]))
        summary.update({
            "baseline_chars_per_s": round(base, 2) if base else None,
            "chars_per_s_min": round(rates[0], 2) if rates else None,
            "chars_per_s_max": round(rates[-1], 2) if rates else None,
            "max_seg_chars_overall": max([r["max_seg_chars"] for r in ok], default=0),
            "max_seg_dur_s_overall": max([r["max_seg_dur_s"] for r in ok], default=0),
            "tasks_with_long_segments": [r["seq"] for r in ok if r["n_seg_gt200"] > 0],
            "tasks_with_impossible_rate": [r["seq"] for r in ok if r["n_seg_rate_gt15"] > 0],
            "tasks_with_silent_like_seg": [r["seq"] for r in ok if r["n_seg_rate_lt2"] > 0],
            "tasks_est_missing_gt20pct": [s["seq"] for s in suspect if s["est_missing_ratio"] > 0.2],
            "est_missing_ratio_max": max([s["est_missing_ratio"] for s in suspect], default=0.0),
            "suspect_tasks": suspect,
        })
        (self.out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

        self.log("=" * 78)
        self.log("压测结束：总任务 %d｜成功 %d｜失败 %d｜成功率 %.2f%%｜吞吐 %.2f 任务/分钟"
                 % (len(self.results), len(ok), len(bad), summary["success_rate"] * 100,
                    summary["throughput_per_min"]))
        if ok:
            self.log("端到端(s)：平均 %s P50 %s P90 %s P95 %s P99 %s 最小 %s 最大 %s"
                     % (summary["elapsed_avg"], summary["elapsed_p50"], summary["elapsed_p90"],
                        summary["elapsed_p95"], summary["elapsed_p99"], summary["elapsed_min"], summary["elapsed_max"]))
            self.log("M1 缺失字合计 %d / 发送 %d（%.4f%%）｜有缺失任务 %d"
                     % (summary["missing_chars_total"], summary["sent_chars_total"],
                        summary["missing_char_ratio_overall"] * 100, len(lossy)))
            self.log("M5 有 paraIndex 缺口任务 %d｜有空字幕任务 %d｜有时间轴空洞任务 %d｜SRT!=segments 任务 %d"
                     % (summary["tasks_with_para_gaps"], summary["tasks_with_empty_segments"],
                        summary["tasks_with_holes"], summary["srt_ne_segments_tasks"]))
        self.log(f"结果目录 {self.out}")


def main():
    args = build_args()
    cfg = dict(LANGS[args.lang])
    if args.suffix:
        cfg["run_dir"] = cfg["run_dir"].with_name(cfg["run_dir"].name + args.suffix)
    Runner(cfg, args.workers, args.minutes * 60, args.limit).run()


if __name__ == "__main__":
    main()
