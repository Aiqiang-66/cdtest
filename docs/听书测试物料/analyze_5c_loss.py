# -*- coding: utf-8 -*-
r"""分析 5 并发 30 分钟压测结果：发送文案 vs 返回文案 的丢失与串扰。

输入：docs\听书测试物料\mp3\Higgs_5并发30分钟_丢失核查_0910\tasks.jsonl
输出：同目录下 loss_report.md（结论 + 明细）
"""
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

OUT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\Higgs_5并发30分钟_丢失核查_0910")
JSONL = OUT / "tasks.jsonl"

_EDGE_PUNCT = re.compile(r"^[^\w']+|[^\w']+$")


def norm_tokens(s: str):
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


def load():
    recs = []
    for line in JSONL.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            recs.append(json.loads(line))
    return recs


def main():
    recs = load()
    ok = [r for r in recs if r.get("ok")]
    bad = [r for r in recs if not r.get("ok")]
    lossy = sorted([r for r in ok if r["missing_count"] > 0],
                   key=lambda r: -r["missing_ratio"])

    seg_counter = Counter()
    for r in ok:
        seg_counter[r.get("segments")] += 1

    # 串扰检测：返回文案与其它任务的发送文案做词集重合度比较
    crosstalk = []
    for r in lossy:
        ret = Counter(norm_tokens(r["ret_text"]))
        n_ret = sum(ret.values()) or 1
        best = None
        for other in ok:
            if other["seq"] == r["seq"]:
                continue
            sent = Counter(norm_tokens(other["sent_text"]))
            overlap = sum((ret & sent).values())
            cover = overlap / n_ret
            if best is None or cover > best[1]:
                best = (other["seq"], cover)
        own = None
        for other in ok:
            if other["seq"] != r["seq"]:
                continue
            sent = Counter(norm_tokens(other["sent_text"]))
            own = sum((ret & sent).values()) / n_ret
        if best and own is not None:
            crosstalk.append({"seq": r["seq"], "own_cover": round(own, 4),
                              "best_other_seq": best[0], "best_other_cover": round(best[1], 4)})

    lines = []
    add = lines.append
    add("# Higgs TTS v3 五并发 30 分钟压测 —— 文案丢失核查报告")
    add("")
    add("## 一、结论")
    add("")
    add(f"- 压测口径：接口 `https://ai-main-none-dev.changdu.ltd`，模型 `higgs`，5 路并发持续打满 30 分钟，"
        f"单任务文案 500 词（共 {len({r.get('window_index') for r in ok})} 篇互不相同文案）。")
    add(f"- 总任务 {len(recs)}，成功 {len(ok)}，失败 {len(bad)}。")
    if ok:
        total_sent = sum(r["sent_tokens"] for r in ok)
        total_missing = sum(r["missing_count"] for r in ok)
        total_extra = sum(r["extra_count"] for r in ok)
        add(f"- 发送 token 合计 {total_sent}，返回比对缺失 {total_missing}（{100.0*total_missing/total_sent:.3f}%），多余 {total_extra}（{100.0*total_extra/total_sent:.3f}%）。")
        add(f"- 存在文案缺失的任务：**{len(lossy)}/{len(ok)}（{100.0*len(lossy)/len(ok):.1f}%）**。")
        worst = lossy[0] if lossy else None
        if worst:
            add(f"- 单任务最严重：seq={worst['seq']} taskId={worst['taskId']}，发送 {worst['sent_tokens']} token，"
                f"缺失 {worst['missing_count']}（{worst['missing_ratio']*100:.2f}%），相似度 {worst['similarity']}。")
        sims = [r["similarity"] for r in ok]
        add(f"- 相似度：平均 {sum(sims)/len(sims):.4f}，最低 {min(sims):.4f}。")
    add("")
    add("## 二、失败任务")
    add("")
    if bad:
        add("| seq | worker | taskId | 状态 | 耗时(s) | 原因 |")
        add("|-----|--------|--------|------|---------|------|")
        for r in bad:
            add(f"| {r['seq']} | {r.get('worker','-')} | {r.get('taskId')} | {r.get('status')} | "
                f"{r.get('elapsed_s','-')} | {str(r.get('error'))[:90]} |")
    else:
        add("无失败任务。")
    add("")
    add("## 三、存在缺失的任务明细（按缺失比例倒序）")
    add("")
    if lossy:
        add("| seq | taskId | 段落 | 发送token | 返回token | 缺失 | 缺失率 | 多余 | 相似度 | 缺失词（前20） |")
        add("|-----|--------|------|-----------|-----------|------|--------|------|--------|----------------|")
        for r in lossy:
            miss = ", ".join(r["missing_head"][:20])
            add(f"| {r['seq']} | {r['taskId']} | {r.get('segments')} | {r['sent_tokens']} | {r['ret_tokens']} | "
                f"{r['missing_count']} | {r['missing_ratio']*100:.2f}% | {r['extra_count']} | {r['similarity']} | {miss} |")
    else:
        add("无缺失任务。")
    add("")
    add("## 四、串扰（返回内容指向其它任务文案）线索")
    add("")
    if crosstalk:
        add("| seq | 与自身文案重合度 | 最相近的其它任务 | 与其它文案重合度 |")
        add("|-----|------------------|------------------|------------------|")
        for c in crosstalk:
            add(f"| {c['seq']} | {c['own_cover']} | {c['best_other_seq']} | {c['best_other_cover']} |")
        add("")
        add("> 判读：若「与其它文案重合度」明显高于「与自身文案重合度」，说明返回内容串到了别的任务。")
    else:
        add("无疑似串扰。")
    add("")
    add("## 五、段落数分布（返回 metadata 段数）")
    add("")
    add("| 段数 | 任务数 |")
    add("|------|--------|")
    for s, c in sorted(seg_counter.items(), key=lambda x: -x[1])[:15]:
        add(f"| {s} | {c} |")

    (OUT / "loss_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:40]))
    print(f"\n报告已写入: {OUT / 'loss_report.md'}")


if __name__ == "__main__":
    main()
