import os
# -*- coding: utf-8 -*-
r"""文案格式与切句 —— 正常/异常用例执行器（日语，Higgs TTS v3）。

⚠️ **当前不执行**：等大模型侧代码优化完成后再跑。
   先用 `--dry-run` 在本地构造全部用例输入并打印规模（不调用接口）。

用法：
  # 只构造输入（本地，不调接口）
  & "D:\python\python.exe" docs\听书测试物料\run_text_format_cases_0924.py --dry-run

  # 优化完成后正式执行（调用接口）
  & "D:\python\python.exe" docs\听书测试物料\run_text_format_cases_0924.py --lang ja --workers 4

产物（mp3/文案格式用例_0924/）：
  src/TC-FMT-*.txt        实际下发的 read_content
  meta/TC-FMT-*.json      接口返回 metadata
  case_inputs.json        dry-run 的输入规模清单
  results.json            逐用例指标 + 自动判定
"""
import argparse
import base64
import hashlib
import hmac
import json
import statistics
import threading
import time
import unicodedata
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
MP3 = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3")
REPORT_DIR = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\测试报告")
R3 = {"ja": (MP3 / "Higgs_日语_10并发30分钟_0924_r3", 9, "Japanese_female", "日语"),
      "ko": (MP3 / "Higgs_韩语_10并发30分钟_0924_r3", 14, "Korean_female", "韩语")}
OUT = MP3 / "文案格式用例_0924"

POLL_INTERVAL, POLL_TIMEOUT = 5, 2400
N_SEG_GT200, RATE_HI, RATE_LO, GAP81 = 200, 15.0, 2.0, 81.64
SESSION = requests.Session()
SESSION.mount("https://", HTTPAdapter(pool_connections=16, pool_maxsize=16, max_retries=0))
_lock = threading.Lock()


# ────────────────────────── 用例输入构造 ──────────────────────────
def _unit(lang, n):
    return (R3[lang][0] / "material" / f"unit_{n:04d}.txt").read_text(encoding="utf-8")


def build_cases(lang):
    u1 = _unit(lang, 1)
    paras1 = u1.split("\n")
    mid = "\n".join(paras1[:10])                                  # ~10 段
    multi_space = "\n\n".join(paras1[:10])                        # 段落间空行
    single_ok = " ".join(paras1[:3])                              # 合法单段落（多句）
    flat = u1.replace("\n", " ")                                  # A01 整章拼单段落
    no_punct_paras = "\n".join(
        [("この段落には句末の記号が一切ありません そのため切句の手がかりが無い状態になります "
          "どこで区切るのかを観察するための長い文字列です ") * 5] * 10)
    single_nopunct = ("この段落には句末の記号が一切なく しかも改行も存在しないため "
                      "サービス側がどこで区切るのかを観察するための長い文字列になります ") * 45
    repeated = "\n".join([" ".join(["ローラは静かに微笑んだ。"] * 10)] * 10)   # 10 段 × 10 句 = 100 次
    newline_boom = "\n".join(["あ"] * 200)                        # 200 个单字段落
    mixed = "\n".join([
        "こんにちは、今日はいい天気ですね。",
        "Hello world, this is a mixed-language paragraph for testing.",
        "今天我们来测试中英日混排的情况。",
        "これはテストです。This is a test. 这是一个测试。",
    ])
    numbers = "\n".join([
        "2026年9月24日、株式会社の売上は1,234,567円でした。",
        "担当はローラ・リー、連絡先は03-1234-5678です。",
        "契約金額は $12,345.67、納期は 2026-10-01 です。",
        "第3四半期の成長率は 12.5% でした。",
    ])
    punct_only = "\n".join(["。！？…、；：。！？…、；："] * 5)
    big = "\n".join(_unit(lang, i) for i in (2, 3, 4))            # A09 超长（3 单元）
    single_long_sentence = ("これは非常に長い一文であり句末の記号が最後にしか現れないため"
                           "サービス側の切句処理がどのように扱うかを確認するための文章です" * 16) + "。"

    return [
        # ---------- 正常 ----------
        dict(id="TC-FMT-N01", group="正常", name="标准单元（保留段落 ~5000 字）",
             text=u1, expect="paraIndex>1 且无异常段"),
        dict(id="TC-FMT-N02", group="正常", name="短文本（2 段 2 句）",
             text="夜のホテルの廊下は静かだった。\n彼女はゆっくりと歩いていった。",
             expect="成功且段长正常"),
        dict(id="TC-FMT-N03", group="正常", name="中文本（10 段 ~500 字）",
             text=mid, expect="无异常段"),
        dict(id="TC-FMT-N04", group="正常", name="段落间空行（\\n\\n 分段）",
             text=multi_space, expect="paraIndex>1（空行同样识别为段落）"),
        dict(id="TC-FMT-N05", group="正常", name="合法单段落（~300 字多句一段）",
             text=single_ok, expect="paraIndex=1 但段长正常（单段落本身合法）"),
        dict(id="TC-FMT-N06", group="正常", name="数字/日期/专有名词密集（4 段）",
             text=numbers, expect="文本口径一致，读法留人工/ASR"),
        # ---------- 异常 ----------
        dict(id="TC-FMT-A01", group="异常", name="整章拼成单段落（无换行）★漏测场景",
             text=flat, expect="可复现退化：paraIndex=1 且出现超长段/高语速段/81.64s 段"),
        dict(id="TC-FMT-A02", group="异常", name="无句末标点的长文（10 段 ~2000 字）",
             text=no_punct_paras, expect="观察：切句退化程度"),
        dict(id="TC-FMT-A03", group="异常", name="单段超长且无标点（~3000 字）",
             text=single_nopunct, expect="观察：预期出现超长段"),
        dict(id="TC-FMT-A04a", group="异常", name="空文本", text="",
             expect="应报错（不得静默产出空音频）", timeout=90),
        dict(id="TC-FMT-A04b", group="异常", name="纯空白文本", text="   ",
             expect="应报错（不得静默产出空音频）", timeout=90),
        dict(id="TC-FMT-A05", group="异常", name="特殊字符（HTML/emoji/控制符/零宽）",
             text=("<p>タグ付きテキスト</p>\n😀🎧 絵文字のテストです\n"
                   "制御文字:\u0001\u0002 とゼロ幅\u200b文字を含みます\n末尾に改行なし"),
             expect="成功或明确报错，不得崩溃"),
        dict(id="TC-FMT-A06", group="异常", name="大量重复句（同一句 100 次，10 段）",
             text=repeated, expect="观察是否丢内容（missing_chars）"),
        dict(id="TC-FMT-A07", group="异常", name="换行爆炸（200 个单字段落）",
             text=newline_boom, expect="观察段数/paraIndex 是否爆炸或失败"),
        dict(id="TC-FMT-A08", group="异常", name="混合语种（中/英/日，4 段）",
             text=mixed, expect="成功；观察漏读"),
        dict(id="TC-FMT-A09", group="异常", name="超长文本（3 单元拼接 ~15000 字）",
             text=big, expect="观察上限行为：成功看时长/段数，失败记录报错"),
        dict(id="TC-FMT-A10", group="异常", name="非法参数 lang=999",
             text="これはパラメータ検証のための短いテキストです。", lang_override=999,
             expect="应报错或明确回退，不得静默成功", timeout=90),
        dict(id="TC-FMT-A11", group="异常", name="纯标点（5 段）",
             text=punct_only, expect="观察是否产出音频/空字幕"),
        dict(id="TC-FMT-A12", group="异常", name="单句超长（1 句 ~1000 字）",
             text=single_long_sentence, expect="观察切句能否处理；预期超长段"),
    ]


# ────────────────────────── 指标与判定 ──────────────────────────
def norm_ns(s):
    return "".join(c for c in unicodedata.normalize("NFKC", s) if not c.isspace())


def sign(t):
    return base64.b64encode(hmac.new(KEY.encode(), t.encode(), hashlib.sha256).digest()).decode()


def post(path, payload, timeout=60):
    body = json.dumps(payload)
    return SESSION.post(BASE + path, data=body.encode(),
                        headers={"sign": sign(body), "Content-Type": "application/json"},
                        timeout=timeout).json()


def measure(text, lang_code, voice, title, poll_timeout=None):
    """下发一个任务并返回指标；异常路径也返回结构化结果。"""
    rec = {"ok": False}
    t0 = time.time()
    limit = poll_timeout or POLL_TIMEOUT
    try:
        body = post("/Video/CreateUniversalTransparent",
                    {"ext": json.dumps({"read_content": text, "chapter_title": title,
                                        "model": "higgs", "lang": lang_code, "voice": voice}),
                     "taskType": 74, "priority": 0, "retry_times": 1, "cool_time": 600})
    except Exception as e:
        rec["error"] = f"create {type(e).__name__}: {e}"
        return rec
    rec["create_code"] = body.get("code")
    rec["create_msg"] = str(body.get("msg") or "")[:120]
    tid = body.get("data")
    rec["taskId"] = tid
    if body.get("code") != 200 or not tid:
        rec["error"] = f"创建被拒 code={body.get('code')} msg={rec['create_msg']}"
        return rec
    info = None
    while time.time() - t0 < limit:
        time.sleep(POLL_INTERVAL)
        try:
            lst = post("/Task/GetAllTaskStatus", {"taskType": 74, "taskIds": [tid]}).get("data", [])
        except Exception:
            continue
        if lst and lst[0].get("taskStatus") == 2:
            info = lst[0]
            break
        if lst and lst[0].get("taskStatus") == 3:
            rec["error"] = f"任务失败 comment={lst[0].get('comment')}"
            rec["status"] = 3
            return rec
    rec["elapsed_s"] = round(time.time() - t0, 1)
    if not info:
        rec["error"] = "超时未产出（status 仍为处理中）"
        return rec
    data = info.get("data", "{}")
    data = json.loads(data) if isinstance(data, str) else data
    try:
        segs = SESSION.get(data["metadata_url"], timeout=180).json()
    except Exception as e:
        rec["error"] = f"metadata 下载失败 {type(e).__name__}: {e}"
        return rec
    segs = segs if isinstance(segs, list) else []
    body_segs = [s for s in segs if s.get("paraIndex", -1) >= 0]
    stats = []
    for s in body_segs:
        t = (s.get("text") or "").strip()
        d = (s.get("endMs", 0) - s.get("startMs", 0)) / 1000.0
        stats.append((len(t), d, (len(t) / d) if d > 0 else 0.0))
    lens = sorted((x[0] for x in stats), reverse=True)
    rates = sorted((x[2] for x in stats), reverse=True)
    pas = sorted({s.get("paraIndex") for s in body_segs})
    audio_s = max((s.get("endMs", 0) for s in segs), default=0) / 1000.0
    ret = norm_ns(" ".join((s.get("text") or "") for s in body_segs))
    sent = norm_ns(text)
    rec.update({
        "ok": True, "segments_total": len(segs), "body_segments": len(body_segs),
        "distinct_paraIndex": len(pas), "paraIndex_range": [pas[0], pas[-1]] if pas else None,
        "seg_chars_median": statistics.median(lens) if lens else 0,
        "seg_chars_max": lens[0] if lens else 0,
        "seg_rate_max": round(rates[0], 1) if rates else 0,
        "n_seg_gt200": sum(1 for x in lens if x > N_SEG_GT200),
        "n_seg_rate_gt15": sum(1 for x in stats if x[1] > 0.5 and x[2] > RATE_HI),
        "n_seg_rate_lt2": sum(1 for x in stats if x[1] > 5 and x[2] < RATE_LO),
        "has_81s_seg": any(abs(x[1] - GAP81) < 0.3 for x in stats),
        "empty_segments": sum(1 for s in segs if not (s.get("text") or "").strip()),
        "audio_total_s": round(audio_s, 1),
        "task_chars_per_s": round(len(sent) / audio_s, 2) if audio_s else None,
        "sent_chars": len(sent), "ret_chars": len(ret),
        "missing_chars": max(0, len(sent) - len(ret)),
        # 文本口径（简版）：去空白后逐字符比较
        "text_identical": sent == ret,
    })
    return rec


def evaluate(case, rec):
    """→ (判定, 说明)"""
    cid, exp = case["id"], case["expect"]
    if cid in ("TC-FMT-A04a", "TC-FMT-A04b", "TC-FMT-A10"):
        # 期望被拒绝
        if not rec.get("ok"):
            return "PASS", f"按预期被拒绝：{rec.get('error') or rec.get('create_msg')}"
        return "FAIL", "期望报错，但任务成功并产出了音频"
    if not rec.get("ok"):
        return "ERROR", f"未成功：{rec.get('error')}"
    if cid == "TC-FMT-A01":
        degraded = (rec["distinct_paraIndex"] == 1 and
                    (rec["n_seg_gt200"] > 0 or rec["n_seg_rate_gt15"] > 0 or rec["has_81s_seg"]))
        if degraded:
            return "PASS", ("按预期复现格式违规退化：paraIndex=1，"
                            f"超长段 {rec['n_seg_gt200']}、高语速段 {rec['n_seg_rate_gt15']}、"
                            f"81.64s 段 {rec['has_81s_seg']}")
        return "INFO", ("未复现退化（服务端可能已修复或该文本未触发）："
                        f"paraIndex={rec['distinct_paraIndex']}、最长段 {rec['seg_chars_max']} 字")
    if case["group"] == "正常":
        problems = []
        if rec["n_seg_gt200"] > 0:
            problems.append(f"超长段 {rec['n_seg_gt200']} 个（最长 {rec['seg_chars_max']} 字）")
        if rec["n_seg_rate_gt15"] > 0:
            problems.append(f"高语速段 {rec['n_seg_rate_gt15']} 个（最大 {rec['seg_rate_max']} 字/秒）")
        if rec["has_81s_seg"]:
            problems.append("出现 81.64s 段")
        if rec["missing_chars"] > 0:
            problems.append(f"文本口径缺失 {rec['missing_chars']} 字")
        if rec["empty_segments"] > 0:
            problems.append(f"空字幕 {rec['empty_segments']} 条")
        if cid in ("TC-FMT-N01", "TC-FMT-N03", "TC-FMT-N04", "TC-FMT-N06") and rec["distinct_paraIndex"] <= 1:
            problems.append(f"distinct paraIndex={rec['distinct_paraIndex']}（多段落输入应 >1）")
        return ("PASS", "全部判据通过") if not problems else ("FAIL", "；".join(problems))
    return "INFO", "异常场景，仅记录实际行为"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="ja", choices=["ja", "ko"])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true", help="只构造输入并打印规模，不调用接口")
    ap.add_argument("--out-suffix", default="", help="输出目录后缀（如 _ko），避免跨语种覆盖结果")
    args = ap.parse_args()

    global OUT
    if args.out_suffix:
        OUT = MP3 / ("文案格式用例_0924" + args.out_suffix)

    run_dir, lang_code, voice, cn = R3[args.lang]
    cases = build_cases(args.lang)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "src").mkdir(exist_ok=True)
    (OUT / "meta").mkdir(exist_ok=True)

    print(f"[{cn}] 用例 {len(cases)} 个（正常 {sum(1 for c in cases if c['group']=='正常')}｜"
          f"异常 {sum(1 for c in cases if c['group']=='异常')}）｜接口 {BASE}｜model=higgs｜lang={lang_code}")
    print(f"{'ID':<14}{'组':<5}{'字数':>7}{'段落':>6}  用例名")
    inputs = []
    for c in cases:
        t = c["text"]
        n_para = t.count("\n") + 1 if t.strip() else 0
        (OUT / "src" / f"{c['id']}.txt").write_text(t, encoding="utf-8")
        inputs.append({"id": c["id"], "group": c["group"], "name": c["name"],
                       "chars": len(t), "paragraphs": n_para, "newlines": t.count("\n"),
                       "expect": c["expect"]})
        print(f"{c['id']:<14}{c['group']:<5}{len(t):>7}{n_para:>6}  {c['name']}")
    (OUT / "case_inputs.json").write_text(json.dumps(inputs, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.dry_run:
        print(f"\n[DRY-RUN] 已构造全部用例输入（未调用接口）。清单：{OUT / 'case_inputs.json'}")
        print("         待大模型侧优化完成后，去掉 --dry-run 即可执行。")
        return

    print("\n→ 开始调用接口…")
    results = {}

    def work(c):
        r = measure(c["text"], c.get("lang_override", lang_code), voice, f"{c['id']} {c['name']}",
                    poll_timeout=c.get("timeout"))
        v, why = evaluate(c, r)
        r.update({"id": c["id"], "group": c["group"], "name": c["name"],
                  "chars": len(c["text"]), "expect": c["expect"], "verdict": v, "why": why})
        (OUT / "meta" / f"{c['id']}.json").write_text(
            json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        with _lock:
            results[c["id"]] = r
            print(f"  [{v}] {c['id']} {c['name']}｜{why}")
        return r

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(work, c) for c in cases]
        for _ in as_completed(futs):
            pass

    (OUT / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for r in results.values() if r["verdict"] == "PASS")
    fail = sum(1 for r in results.values() if r["verdict"] == "FAIL")
    err = sum(1 for r in results.values() if r["verdict"] == "ERROR")
    info = sum(1 for r in results.values() if r["verdict"] == "INFO")
    print(f"\n===== 汇总：PASS {ok}｜FAIL {fail}｜ERROR {err}｜INFO {info} =====")
    print(f"结果：{OUT / 'results.json'}")


if __name__ == "__main__":
    main()
