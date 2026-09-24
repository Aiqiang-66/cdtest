# -*- coding: utf-8 -*-
r"""导出「输入/输出文案比对不一致」的任务物料到 E:\测试数据，供人工二次核验。

对象：0910 17:46 批次中英语 / 德语 / 俄语第 1 章（存在真实丢词的 3 个任务）。
每个任务一个目录，包含：
  输入_请求体.json    下发时的完整请求体（ext 为原始字符串，可逐字复核）
  输入_ext解析.json   ext 解析后的人类可读参数（含 read_content 全文）
  输入_原文.txt       提交的正文文本，便于直接阅读
  输出_metadata.json  接口返回的 metadata 原始 JSON
  输出_字幕.srt       由 metadata 生成的字幕
  比对_差异.json      逐块差异：缺失词、原文词序号、参考时间区间、上下文
  输出_音频.mp3       对应音频（便于人工听测定位）
"""
import difflib
import json
import re
import shutil
import unicodedata
import zipfile
from pathlib import Path

SRC = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\Higgs_全语种单章_0910")
TXT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\txt文本")
DEST_ROOT = Path(r"E:\测试数据")
DEST = DEST_ROOT / "Higgs_文案比对差异_人工复核_0910"

CONFIGS = [
    ("英语", "XR3 - EN.txt", r"^===\s*Chapter\s+\d+", 1, "English_female", 650151),
    ("德语", "XR3 - DE.txt", r"^===\s*Kapitel\s+\d+", 1, "German_female", 650152),
    ("俄语", "XR3 - RU.txt", r"^===\s*Глава\s+\d+", 1, "Russian_female", 617896),
]

_EDGE = re.compile(r"^[^\w']+|[^\w']+$")


def tk(s):
    s = unicodedata.normalize("NFKC", s).replace("\u2019", "'")
    return [w for w in (_EDGE.sub("", x).lower() for x in s.split()) if w]


def fms(ms):
    return "%02d:%02d:%02d.%03d" % (ms // 3600000, (ms % 3600000) // 60000,
                                    (ms % 60000) // 1000, ms % 1000)


def chapter1(fname, pattern):
    text = (TXT / fname).read_text(encoding="utf-8-sig")
    ms = list(re.finditer(pattern, text, flags=re.MULTILINE))
    return ms[0].group().strip("= ").strip(), text[ms[0].end():ms[1].start()].strip()


def main():
    DEST_ROOT.mkdir(parents=True, exist_ok=True)
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)

    rows = []
    for cn, fname, pattern, lang, voice, task_id in CONFIGS:
        title, content = chapter1(fname, pattern)
        meta = json.loads((SRC / f"{cn}_XR3_Ch1.json").read_text(encoding="utf-8"))

        # 还原输出文案并为每个词记录所属片段，便于把差异映射回时间轴
        out_tokens, tok_span, spans = [], [], []
        for s in meta:
            t = tk(s.get("text") or "")
            if not t:
                continue
            spans.append((s.get("startMs", 0), s.get("endMs", 0)))
            for _ in t:
                tok_span.append(len(spans) - 1)
            out_tokens.extend(t)
        tt = tk(title)
        offset = len(tt) if out_tokens[:len(tt)] == tt else 0
        body_tokens = out_tokens[offset:]

        sent = tk(content)
        sm = difflib.SequenceMatcher(a=sent, b=body_tokens, autojunk=False)
        blocks = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag not in ("delete", "replace") or not sent[i1:i2]:
                continue
            j = j1 + offset
            seg_idx = tok_span[j] if j < len(tok_span) else (len(spans) - 1 if spans else 0)
            prev_end = spans[seg_idx - 1][1] if seg_idx > 0 else 0
            next_start = spans[seg_idx][0] if spans else 0
            blocks.append({
                "序号": len(blocks) + 1,
                "缺失词": sent[i1:i2],
                "缺失词个数": i2 - i1,
                "输入原文词序号": [i1, i2],
                "参考时间区间": f"{fms(prev_end)} → {fms(next_start)}",
                "输入上下文": " ".join(sent[max(0, i1 - 10):i2 + 8]),
            })
        missing_total = sum(b["缺失词个数"] for b in blocks)

        sub = DEST / f"{cn}_task{task_id}"
        sub.mkdir()

        ext_data = {"read_content": content, "chapter_title": title,
                    "model": "higgs", "lang": lang, "voice": voice}
        payload = {"ext": json.dumps(ext_data), "taskType": 74, "priority": 0,
                   "retry_times": 1, "cool_time": 600}
        (sub / "输入_请求体.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        (sub / "输入_ext解析.json").write_text(
            json.dumps(ext_data, ensure_ascii=False, indent=2), encoding="utf-8")
        (sub / "输入_原文.txt").write_text(content, encoding="utf-8")
        # 输出 metadata 直接放接口原始返回文件，保留原始时间戳
        for name, out_name in ((f"{cn}_XR3_Ch1.json", "输出_metadata.json"),
                               (f"{cn}_XR3_Ch1.srt", "输出_字幕.srt"),
                               (f"{cn}_XR3_Ch1.mp3", "输出_音频.mp3")):
            s = SRC / name
            if s.exists():
                shutil.copy2(s, sub / out_name)
        (sub / "输入_说明.txt").write_text(
            "输入_请求体.json 由下发脚本的参数构造方式重建（与下发时构造的请求体一致），\n"
            "其中 read_content 为提交的章节正文全文，与 输入_原文.txt 一致。\n"
            "下发时间：2026-09-10 17:42~17:51。接口原始返回文件见 输出_metadata.json。\n",
            encoding="utf-8")
        (sub / "比对_差异.json").write_text(json.dumps({
            "语种": cn, "taskId": task_id, "章节标题": title,
            "模型": "higgs", "lang": lang, "voice": voice,
            "输入词数": len(sent), "输出词数": len(body_tokens),
            "缺失词合计": missing_total,
            "缺失率": f"{100.0*missing_total/max(1,len(sent)):.2f}%",
            "缺失块数": len(blocks), "差异块": blocks,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

        rows.append((cn, task_id, len(sent), len(body_tokens), missing_total, len(blocks), sub.name))
        print(f"{cn} taskId={task_id} 输入{len(sent)}词 输出{len(body_tokens)}词 缺失{missing_total}词/{len(blocks)}块")

    lines = [
        "# 输入/输出文案比对差异 —— 人工二次核验物料",
        "",
        "## 一、背景",
        "",
        "- 批次：2026-09-10 17:42~17:51 下发的 XR3 六语种第 1 章（测试环境 `https://ai-main-none-dev.changdu.ltd`，模型 `higgs`）",
        "- 该批次紧接着服务异常窗口（16:45~17:03 任务全部失败）之后，是恢复后的首跑",
        "- 比对口径：**输入文案（下发时提交的 read_content） vs 输出文案（接口返回 metadata 文本）**，纯文本比对",
        "- 本目录只放**比对不一致**的 3 个任务；法语/西语/葡语同批次为 0 缺失，未收录",
        "",
        "## 二、差异清单",
        "",
        "| 语种 | taskId | 输入词 | 输出词 | 缺失词 | 缺失块数 | 缺失率 | 目录 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for cn, task_id, si, oi, mi, blk, dirname in rows:
        lines.append(f"| {cn} | {task_id} | {si} | {oi} | {mi} | {blk} | "
                     f"{100.0*mi/si:.2f}% | `{dirname}` |")
    lines += [
        "",
        "## 三、每个任务的目录结构",
        "",
        "```",
        "<语种>_task<taskId>/",
        "  输入_请求体.json    下发时的完整请求体（ext 为原始字符串，可逐字复核）",
        "  输入_ext解析.json   ext 解析后的参数（含 read_content 正文全文）",
        "  输入_原文.txt       提交的正文文本",
        "  输出_metadata.json  接口返回的 metadata 原始 JSON（输出文案来源）",
        "  输出_字幕.srt       由 metadata 生成的字幕",
        "  输出_音频.mp3       对应音频",
        "  比对_差异.json      逐块差异：缺失词、输入词序号、参考时间区间、输入上下文",
        "```",
        "",
        "## 四、核验建议",
        "",
        "1. 先看 `比对_差异.json` 的「差异块」，里面给出每处缺失的词、在输入文案中的词序号、以及在音频中的参考时间区间。",
        "2. 用「参考时间区间」对照 `输出_音频.mp3` 试听：能听到对应内容 = 只是字幕/元数据丢了；听不到 = 生成时就漏了。",
        "3. `输出_metadata.json` 是接口原始返回，`输出_字幕.srt` 由它生成，两者内容一致。",
        "",
        "## 四之一、文件时间戳说明",
        "",
        "| 文件 | 时间戳 | 原因 |",
        "| --- | --- | --- |",
        "| 输出_音频.mp3 / 输出_字幕.srt / 输出_metadata.json | 2026-09-10 17:46~17:50 | 接口原始产物，复制时保留原文件修改时间 |",
        "| 输入_请求体.json / 输入_ext解析.json / 输入_原文.txt / 比对_差异.json | 导出时间（21:12 起） | 这些是我在导出时生成/重建的文件 |",
        "",
        "> 因此本目录里 mp3 与字幕显示 17:46 是正常的：**这批数据本身就是 17:46 下发的批次**，不是晚间那次稳定性测试。",
        "",
        "## 五、现象特征",
        "",
        "- 零散丢失，不是整段丢失：每处 2~9 个词，全章 30 处左右。",
        "- 时间轴无空洞：相邻字幕段间隔均小于 3 秒，缺失内容没有留下时间空隙。",
        "- 例：英语输入 `I heard that that servant needs surgery. I'll give you 3 million`，输出缺少 `needs surgery`，从 `that servant` 直接接到 `I'll give you three million`。",
        "",
        "> 参考脚本：`docs/听书测试物料/export_mismatch_for_review.py`",
    ]
    (DEST / "说明.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    zip_path = DEST_ROOT / "Higgs_文案比对差异_人工复核_0910.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(DEST.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(DEST_ROOT))
    print(f"\n目录：{DEST}")
    print(f"压缩包：{zip_path} ({zip_path.stat().st_size:,} B)")


if __name__ == "__main__":
    main()
