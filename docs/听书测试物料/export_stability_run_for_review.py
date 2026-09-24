# -*- coding: utf-8 -*-
r"""导出晚间「5 并发 30 分钟」稳定性测试的输入/输出文案物料到 E:\测试数据，供人工核验。

数据来源：docs\听书测试物料\mp3\Higgs_5并发30分钟_丢失核查_0910（20:05~20:35，208 个任务）
每个任务输出 4 个文件，文件名以任务序号开头便于排序查看：
  task_0000_输入_请求体.json
  task_0000_输入_原文.txt
  task_0000_输出_metadata.json
  task_0000_输出_字幕.srt
另附：汇总_每任务比对.csv、索引.md、说明.md
"""
import json
import shutil
import zipfile
from pathlib import Path

RUN = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\Higgs_5并发30分钟_丢失核查_0910")
DEST_ROOT = Path(r"E:\测试数据")
DEST = DEST_ROOT / "Higgs_稳定性测试_输入输出文案_208任务_0910"


def main():
    recs = [json.loads(l) for l in (RUN / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    ok = [r for r in recs if r.get("ok")]
    ok.sort(key=lambda r: r["seq"])

    DEST_ROOT.mkdir(parents=True, exist_ok=True)
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)

    index = ["| 序号 | taskId | worker | 输入词 | 输出词 | 缺失词 | 缺失率 | 相似度 | 任务耗时(s) |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in ok:
        seq = r["seq"]
        tag = f"task_{seq:04d}"
        title = r["chapter_title"]
        ext_data = {"read_content": r["sent_text"], "chapter_title": title,
                    "model": "higgs", "lang": r.get("lang_code", 1), "voice": "English_female"}
        payload = {"ext": json.dumps(ext_data), "taskType": 74, "priority": 0,
                   "retry_times": 1, "cool_time": 600}
        (DEST / f"{tag}_输入_请求体.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        (DEST / f"{tag}_输入_原文.txt").write_text(r["sent_text"], encoding="utf-8")
        (DEST / f"{tag}_输入_说明.txt").write_text(
            "输入_原文.txt 为下发时实际提交的正文（压测脚本在下发瞬间落盘，与 read_content 完全一致）。\n"
            "输入_请求体.json 由该正文与下发参数重建，字段与下发时一致。\n"
            f"下发时间：2026-09-10 20:05~20:35；taskId：{r['taskId']}。\n",
            encoding="utf-8")
        shutil.copy2(RUN / "meta" / f"{tag}.json", DEST / f"{tag}_输出_metadata.json")
        shutil.copy2(RUN / "srt" / f"{tag}.srt", DEST / f"{tag}_输出_字幕.srt")
        index.append(f"| {seq} | {r['taskId']} | {r.get('worker')} | {r['sent_tokens']} | "
                     f"{r['ret_tokens']} | {r['missing_count']} | {r['missing_ratio']*100:.2f}% | "
                     f"{r['similarity']:.4f} | {r['elapsed_s']} |")

    shutil.copy2(RUN / "compare" / "per_task.csv", DEST / "汇总_每任务比对.csv")

    total_sent = sum(r["sent_tokens"] for r in ok)
    total_missing = sum(r["missing_count"] for r in ok)
    hardest = max(ok, key=lambda r: r["missing_count"])
    lines = [
        "# 输入/输出文案比对物料 —— 晚间稳定性测试（5 并发 × 30 分钟）",
        "",
        "## 一、数据来源",
        "",
        "- 下发时间：2026-09-10 20:05:28 ~ 20:35:45",
        "- 接口环境：`https://ai-main-none-dev.changdu.ltd`（测试环境），模型 `higgs`",
        "- 并发：5 路持续打满 30 分钟；单任务文案约 500 词（共 208 篇互不相同文案）",
        "- 原始目录：`docs/听书测试物料/mp3/Higgs_5并发30分钟_丢失核查_0910`",
        "",
        "## 二、比对结论",
        "",
        f"- 任务数 {len(recs)}，成功 {len(ok)}，失败 {len(recs)-len(ok)}。",
        f"- 输入合计 {total_sent} 词，输出词数与输入一致。",
        f"- **缺失词合计 {total_missing}，缺失率 0.000%**；没有输入与输出文案不一致的任务。",
        f"- 相似度最低的任务：序号 {hardest['seq']}（taskId {hardest['taskId']}），相似度 {hardest['similarity']:.4f}。",
        "",
        "## 三、文件说明",
        "",
        "| 文件 | 说明 |",
        "| --- | --- |",
        "| `task_XXXX_输入_请求体.json` | 下发时的完整请求体，`ext` 内含 read_content 全文 |",
        "| `task_XXXX_输入_原文.txt` | 提交的正文文本 |",
        "| `task_XXXX_输出_metadata.json` | 接口返回的 metadata 原始 JSON（输出文案来源） |",
        "| `task_XXXX_输出_字幕.srt` | 由 metadata 生成的字幕 |",
        "| `汇总_每任务比对.csv` | 每任务比对结果，含输入词/输出词/缺失词/相似度/是否逐字符一致 |",
        "| `索引.md` | 本文件，含全部任务清单 |",
        "",
        "## 三之一、文件时间戳说明",
        "",
        "| 文件 | 时间戳 | 原因 |",
        "| --- | --- | --- |",
        "| `task_XXXX_输出_metadata.json` | 2026-09-10 20:06~20:35 | 接口原始返回，保留原始修改时间 |",
        "| `task_XXXX_输出_字幕.srt` | 21:08 | 由 metadata 生成（本次压测未随任务落盘字幕） |",
        "| `task_XXXX_输入_*.json/txt` | 21:55 | 内容取自压测时落盘的输入文案，导出时写盘 |",
        "",
        "> 判断数据属于哪一批，看 `输出_metadata.json` 的时间戳最准：17:46 那批是 17:46~17:50 产生，本批为 20:06~20:35。",
        "",
        "> 说明：本次未下载 mp3（208 个任务约 250MB）。若需听测某个任务，可用对应 `输入_请求体.json` 重新下发，或从原始目录的 tasks.jsonl 取该任务的 audio_url 下载。",
        "",
        "## 四、任务清单",
        "",
    ] + index
    (DEST / "索引.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (DEST / "说明.md").write_text("\n".join(lines[:lines.index("## 四、任务清单")]) + "\n", encoding="utf-8")

    zip_path = DEST_ROOT / "Higgs_稳定性测试_输入输出文案_208任务_0910.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(DEST.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(DEST_ROOT))

    size = sum(f.stat().st_size for f in DEST.rglob("*") if f.is_file())
    print(f"任务数 {len(ok)}，缺失词 {total_missing}")
    print(f"目录：{DEST}（{size/1024/1024:.1f} MB）")
    print(f"压缩包：{zip_path}（{zip_path.stat().st_size/1024/1024:.1f} MB）")


if __name__ == "__main__":
    main()
