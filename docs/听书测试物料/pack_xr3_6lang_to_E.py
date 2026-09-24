# -*- coding: utf-8 -*-
r"""把 Higgs 全语种单章产物（mp3 + srt + json + 对应章节原文）打包到 E:\测试数据。

产出：
  E:\测试数据\Higgs_XR3_6语种_单章_0910\<语种>\<语种>_XR3_Ch1.mp3 / .srt / .json / 章节原文.txt
  E:\测试数据\Higgs_XR3_6语种_单章_0910\清单.md
  E:\测试数据\Higgs_XR3_6语种_单章_0910.zip
"""
import json
import re
import shutil
import zipfile
from pathlib import Path

SRC = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3\Higgs_全语种单章_0910")
TXT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\txt文本")
DEST_ROOT = Path(r"E:\测试数据")
DEST = DEST_ROOT / "Higgs_XR3_6语种_单章_0910"

# 语种, 源小说文件, 章节标题正则, lang, voice
CONFIGS = [
    ("英语", "XR3 - EN.txt", r"^===\s*Chapter\s+\d+", 1, "English_female"),
    ("德语", "XR3 - DE.txt", r"^===\s*Kapitel\s+\d+", 1, "German_female"),
    ("法语", "XR3 - FR.txt", r"^===\s*Chapitre\s+\d+", 6, "French_female"),
    ("西语", "XR3 - SP.txt", r"^===\s*Cap[ií]tulo\s+\d+", 4, "Spanish_female"),
    ("葡语", "XR3 - PT.txt", r"^===\s*Cap[ií]tulo\s+\d+", 5, "Portuguese_female"),
    ("俄语", "XR3 - RU.txt", r"^===\s*Глава\s+\d+", 1, "Russian_female"),
]


def chapter1(fname: str, pattern: str):
    text = (TXT / fname).read_text(encoding="utf-8-sig")
    ms = list(re.finditer(pattern, text, flags=re.MULTILINE))
    title = ms[0].group().strip("= ").strip()
    start = ms[0].end()
    end = ms[1].start() if len(ms) > 1 else len(text)
    return title, text[start:end].strip()


def main():
    DEST_ROOT.mkdir(parents=True, exist_ok=True)
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)

    results = {r["lang"]: r for r in json.loads((SRC / "results.json").read_text(encoding="utf-8"))}
    rows = []
    for cn, fname, pattern, lang, voice in CONFIGS:
        title, content = chapter1(fname, pattern)
        sub = DEST / cn
        sub.mkdir()
        for ext in (".mp3", ".srt", ".json"):
            s = SRC / f"{cn}_XR3_Ch1{ext}"
            if s.exists():
                shutil.copy2(s, sub / s.name)
        (sub / "章节原文.txt").write_text(
            f"【语种】{cn}\n【书名】XR3\n【章节】{title}\n【模型】Higgs TTS v3\n"
            f"【音色】{voice}｜【lang】{lang}\n【字符数】{len(content)}\n"
            + "=" * 60 + "\n\n" + content + "\n",
            encoding="utf-8")
        r = results.get(cn, {})
        rows.append((cn, title, len(content), voice, lang, r.get("taskId"), r.get("elapsed"),
                     (sub / f"{cn}_XR3_Ch1.mp3").stat().st_size))

    lines = [
        "# Higgs TTS 全语种单章测试物料包",
        "",
        "- 模型：Higgs TTS v3（model=higgs）",
        "- 接口环境：https://ai-main-none-dev.changdu.ltd （测试环境）",
        "- 接口：POST /Video/CreateUniversalTransparent（taskType=74）",
        "- 数据来源：XR3 书籍，6 语种各取第 1 章",
        "- 下发时间：2026-09-10 17:42 ~ 17:51（6 并发）",
        "",
        "## 目录结构",
        "",
        "```",
        "Higgs_XR3_6语种_单章_0910/",
        "  英语/ 英语_XR3_Ch1.mp3 / .srt / .json / 章节原文.txt",
        "  ...（德语/法语/西语/葡语/俄语 同结构）",
        "  清单.md",
        "```",
        "",
        "说明：`.srt` 由接口返回的 metadata JSON 时间轴生成，用于与音频逐句对齐；`章节原文.txt` 是下发时实际提交的章节正文，可直接用于人工二测听测对照。",
        "",
        "## 语种清单",
        "",
        "| 语种 | 章节 | 字符数 | 音色 | lang | taskId | 端到端耗时(s) | mp3 大小(B) |",
        "|------|------|--------|------|------|--------|---------------|-------------|",
    ]
    for cn, title, n, voice, lang, tid, el, size in rows:
        lines.append(f"| {cn} | {title} | {n} | {voice} | {lang} | {tid} | {el} | {size:,} |")
    (DEST / "清单.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    zip_path = DEST_ROOT / "Higgs_XR3_6语种_单章_0910.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(DEST.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(DEST_ROOT))

    total = sum(f.stat().st_size for f in DEST.rglob("*") if f.is_file())
    print(f"目录：{DEST}")
    print(f"压缩包：{zip_path}  ({zip_path.stat().st_size:,} B)")
    print(f"目录内文件合计：{total:,} B")
    for cn, title, n, voice, lang, tid, el, size in rows:
        print(f"  {cn:<4} {title:<14} mp3={size:>9,}B 字符={n:<5} taskId={tid}")


if __name__ == "__main__":
    main()
