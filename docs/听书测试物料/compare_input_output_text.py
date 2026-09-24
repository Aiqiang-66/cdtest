# -*- coding: utf-8 -*-
"""输入文案 vs 输出文案 纯文本比对（不含音频/ASR）。

输入：压测目录下的 tasks.jsonl（含每任务发送文案与返回 metadata 文案）
输出：<run>/srt/task_XXXX.srt     由返回 metadata 生成的字幕（输出文案）
      <run>/compare/per_task.csv  每任务比对结果
      <run>/compare/input_output_compare.md  纯文本比对报告
"""
import difflib
import json
import re
import unicodedata
from pathlib import Path

RUNS = [
    ("5并发30分钟_500词",
     Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\Higgs_5并发30分钟_丢失核查_0910")),
    ("5并发10分钟_1500词",
     Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\Higgs_5并发长文案10分钟_丢失核查_0910")),
]

_EDGE = re.compile(r"^[^\w']+|[^\w']+$")


def tokens(s):
    s = unicodedata.normalize("NFKC", s).replace("\u2019", "'")
    return [w for w in (_EDGE.sub("", x).lower() for x in s.split()) if w]


def flat(s):
    """仅压缩空白，用于字符级严格比对。"""
    return " ".join(unicodedata.normalize("NFKC", s).split())


def fms(ms):
    return "%02d:%02d:%02d,%03d" % (ms // 3600000, (ms % 3600000) // 60000,
                                    (ms % 60000) // 1000, ms % 1000)


def load(run_dir):
    return [json.loads(l) for l in (run_dir / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


def build_srt(run_dir, seq):
    """用返回的 metadata 生成输出字幕。"""
    meta = json.loads((run_dir / "meta" / f"task_{seq:04d}.json").read_text(encoding="utf-8"))
    lines = []
    for i, s in enumerate(meta):
        t = (s.get("text") or "").strip()
        if not t:
            continue
        lines += [str(len(lines) // 4 + 1),
                  f"{fms(s.get('startMs', 0))} --> {fms(s.get('endMs', 0))}", t, ""]
    (run_dir / "srt").mkdir(exist_ok=True)
    (run_dir / "srt" / f"task_{seq:04d}.srt").write_text("\n".join(lines), encoding="utf-8")
    return meta


def raw_output_text(meta, title):
    """从 metadata 还原输出文案原文，剔除开头的章节标题段。"""
    title_norm = tokens(title)
    parts = []
    for idx, s in enumerate(meta):
        t = (s.get("text") or "").strip()
        if not t:
            continue
        if idx == 0 and tokens(t)[:len(title_norm)] == title_norm:
            tail = t
            for w in title.split():
                tail = tail.replace(w, "", 1)
            t = tail.strip(" .,:;!?-")
        if t:
            parts.append(t)
    return " ".join(parts)


def bare(s):
    """去掉标点与大小写后的字符流，用于判断差异是否只来自标点。"""
    s = unicodedata.normalize("NFKC", s).lower()
    return re.sub(r"[^\w]", "", s)


report = ["# 输入文案 vs 输出文案 比对报告（纯文本口径）", "",
          "比对对象：下发时提交的输入文案（`read_content`） vs 接口返回的 metadata 文案（即 srt 文本）。",
          "不涉及 mp3 语音/ASR 漏词率。", ""]

for run_name, run_dir in RUNS:
    recs = load(run_dir)
    ok = [r for r in recs if r.get("ok")]
    cmp_dir = run_dir / "compare"
    cmp_dir.mkdir(exist_ok=True)
    csv = ["seq,taskId,worker,输入字符,输入词,输出词,缺失词,缺失率,多余词,相似度,字符完全一致,去标点后字符一致,首个缺失位置"]
    lossy = []
    total_sent = total_ret = total_missing = total_extra = 0
    exact_char = 0
    exact_bare = 0

    for r in ok:
        meta = build_srt(run_dir, r["seq"])
        raw_out = raw_output_text(meta, r.get("chapter_title", ""))
        sent = tokens(r["sent_text"])
        ret = tokens(r["ret_text"])
        sm = difflib.SequenceMatcher(a=sent, b=ret, autojunk=False)
        missing, extra = [], []
        first_at = ""
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag in ("delete", "replace") and sent[i1:i2]:
                if not first_at:
                    first_at = str(i1)
                missing.extend(sent[i1:i2])
            if tag in ("insert", "replace"):
                extra.extend(ret[j1:j2])

        same_char = flat(r["sent_text"]) == flat(raw_out)
        same_bare = bare(r["sent_text"]) == bare(raw_out)
        if same_char:
            exact_char += 1
        if same_bare:
            exact_bare += 1
        total_sent += len(sent)
        total_ret += len(ret)
        total_missing += len(missing)
        total_extra += len(extra)
        if missing:
            lossy.append((r, missing, extra))

        csv.append(",".join(str(x) for x in [
            r["seq"], r["taskId"], r.get("worker", ""), r["chars"], len(sent), len(ret),
            len(missing), f"{100.0*len(missing)/max(1,len(sent)):.2f}", len(extra),
            f"{sm.ratio():.4f}", "是" if same_char else "否",
            "是" if same_bare else "否", first_at]))

    (cmp_dir / "per_task.csv").write_text("\ufeff" + "\n".join(csv), encoding="utf-8")

    report += [f"## {run_name}", "",
               f"- 任务数 {len(recs)}，成功 {len(ok)}，失败 {len(recs)-len(ok)}。",
               f"- 输入合计 {total_sent} 词，输出合计 {total_ret} 词。",
               f"- **缺失词合计 {total_missing}（{100.0*total_missing/max(1,total_sent):.3f}%）**，多余词合计 {total_extra}。",
               f"- 字符级完全一致（仅压缩空白后逐字符相同）的任务：**{exact_char}/{len(ok)}**。",
               f"- 去掉标点与大小写后逐字符一致的任务：**{exact_bare}/{len(ok)}**（用于区分「真实丢词」与「仅标点写法差异」）。",
               f"- 存在缺失的任务：**{len(lossy)}/{len(ok)}**。",
               f"- 明细：`compare/per_task.csv`，输出字幕：`srt/task_XXXX.srt`，输入文案：`src/task_XXXX.txt`。", ""]

    if lossy:
        report += ["| seq | taskId | 输入词 | 输出词 | 缺失 | 缺失率 | 缺失词 |", "|---|---|---|---|---|---|---|"]
        for r, missing, extra in lossy[:50]:
            report.append(f"| {r['seq']} | {r['taskId']} | {r['sent_tokens']} | {r['ret_tokens']} | "
                          f"{len(missing)} | {100.0*len(missing)/max(1,r['sent_tokens']):.2f}% | {' '.join(missing[:20])} |")
        report.append("")
    else:
        report += ["本次没有出现输入与输出文案不一致的任务。", ""]

    print(f"{run_name}: 任务 {len(recs)}，缺失词 {total_missing}，字符完全一致 {exact_char}/{len(ok)}")

target = RUNS[0][1] / "compare" / "input_output_compare.md"
target.write_text("\n".join(report) + "\n", encoding="utf-8")
print(f"报告：{target}")
