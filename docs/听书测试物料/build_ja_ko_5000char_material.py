# -*- coding: utf-8 -*-
r"""构建日语 / 韩语 ~5000 字符压测语料（**保留原文段落换行**）。

来源（单章普遍不足 5000 字符，按章拼接补齐）：
  日语：txt文本\日语-CEOの彼の罠に落ちた.txt   章节标记  === 第N章... ===  与  === チャプター N ... ===
  韩语：txt文本\韩语-나의 가짜 아내.txt        章节标记  === 제N화 ... ===

⚠️ **v2 关键修正（M0 前置）**：v1 把整章的句子拼成**单段落**（`" ".join(...)`），
   导致服务端拿不到段落结构（`paraIndex` 恒为 0）→ 切句退化 → 超长段（实测最长 1757 字）、
   不可能语速（最高 277 字/秒）、81.64s 静默占位、音频实际缺失 20~46%。
   **v2 改为保留原文段落**：单元文本 = 多个**完整段落**，段内句子用空格连接，**段落间用换行 `\n` 分隔**。
   单元边界仍按累计字符数 ≥ TARGET_CHARS 收口（不再跨段落硬切）。

规则：
  1. 按章标记切章（日语两套标记都算边界），去掉标记行与装饰性分隔行（如 `******`）；
  2. 正文按行 → 行内切句（句末标点 。．！？!?… 及其后的引号/括号归属本句）→ **一行 = 一个段落**；
  3. 无句末标点的残尾 / 被章节边界截断的半句 → **跨段跨章顺延**，保证每句完整；
  4. 段内 < FRAGMENT_CHARS 的碎片句向前并入上一句（1~5 字碎片会造成语音断续）；
  5. 顺序累积**整段**，累计字符 ≥ TARGET_CHARS 即收口为一个单元 → **每个单元天然是多段落**。

产物（落在指定批次目录的 material/ 下）：
  material/units.jsonl        每单元一行：id / title / 章节范围 / 字符数 / 段落数 / 句数
  material/unit_0001.txt      实际下发的 read_content 全文（**含换行**）
  material/manifest.json      语种、来源书、目标字符数、单元总数、字符与段落分布、清洗统计

用法：
  & "D:\python\python.exe" docs\听书测试物料\build_ja_ko_5000char_material.py            # 默认两语种
  & "D:\python\python.exe" docs\听书测试物料\build_ja_ko_5000char_material.py --langs ja --suffix _r3
"""
import argparse
import json
import re
import statistics
from pathlib import Path

TXT = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\txt文本")
MP3 = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\mp3")

TARGET_CHARS = 5000
TAIL_MIN_RATIO = 0.9        # 收尾残段达到目标的 90% 才作为独立单元，否则丢弃

CONFIGS = {
    "ja": {
        "lang": "ja", "cn": "日语", "book": "日语-CEOの彼の罠に落ちた.txt",
        "chapter_re": r"^\s*=+\s*((?:第\d+章|チャプター\s*\d+)[^=\r\n]*?)\s*=+\s*$",
        "lang_code": 9, "voice": "Japanese_female",
        "run_dir": MP3 / "Higgs_日语_10并发30分钟_0924",
    },
    "ko": {
        "lang": "ko", "cn": "韩语", "book": "韩语-나의 가짜 아내.txt",
        "chapter_re": r"^\s*=+\s*(제\d+화[^=\r\n]*?)\s*=+\s*$",
        "lang_code": 14, "voice": "Korean_female",
        "run_dir": MP3 / "Higgs_韩语_10并发30分钟_0924",
    },
}

SENT_END = "。．.！!？?…"
CLOSERS = "」』）)】》〉\"'”’"
SENT_RE = re.compile(rf"[^{re.escape(SENT_END)}\n]*[{re.escape(SENT_END)}]+[{re.escape(CLOSERS)}]*")

STRAY_MARKER_RE = re.compile(r"^\s*=+.*=+\s*$", re.MULTILINE)
SEPARATOR_LINE_RE = re.compile(r"^\s*([*\-=_~·•#…—])\1{2,}\s*$")

FRAGMENT_CHARS = 6
GLUE_HEAD = set(CLOSERS + "、，,：:；;。．.！!？?…")
TERMINATORS = set(SENT_END + CLOSERS)


def split_chapters(text: str, pattern: str):
    """→ ([(title, body), ...], 清除的残留标记行数)"""
    ms = list(re.finditer(pattern, text, flags=re.MULTILINE))
    out, stray = [], 0
    for i, m in enumerate(ms):
        start = m.end()
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        body = text[start:end].strip()
        stray += len(STRAY_MARKER_RE.findall(body))
        body = STRAY_MARKER_RE.sub(" ", body).strip()
        if body:
            out.append((m.group(1).strip(), body))
    return out, stray


def split_paragraphs(block: str):
    """一章正文 → [[句, 句, ...], ...]（**一行 = 一个段落**，段内碎片句前并）。"""
    paras = []
    for raw_line in block.split("\n"):
        line = raw_line.strip()
        if not line or SEPARATOR_LINE_RE.match(line):
            continue
        found = SENT_RE.findall(line)
        consumed = "".join(found)
        rest = line[len(consumed):].strip()
        sents = [s.strip() for s in found if s and s.strip()]
        if rest:
            if sents:
                sents[-1] = sents[-1] + rest
            else:
                sents.append(rest)
        # 段内碎片合并（不跨段）
        merged, pending = [], ""
        for s in sents:
            if pending:
                s, pending = pending + s, ""
            if len(s) < FRAGMENT_CHARS:
                if merged:
                    sep = "" if s[:1] in GLUE_HEAD else " "
                    merged[-1] = merged[-1] + sep + s
                else:
                    pending = s
                continue
            merged.append(s)
        if pending and merged:
            merged[-1] = merged[-1] + pending
        if merged:
            paras.append(merged)
    return paras


def build_units(chapters, target=TARGET_CHARS):
    """顺序累积**整段**到 >= target 收口；未收口半句跨段/跨章顺延。"""
    units = []
    buf, buf_chars = [], 0
    first_title = first_ch = last_ch = None
    carry = ""
    for ch_idx, (title, body) in enumerate(chapters):
        for para in split_paragraphs(body):
            # 1) 承接上一段未收口的半句（para 是「句子的列表」= 一个段落）
            if carry:
                first = carry + ("" if para[0][:1] in GLUE_HEAD else " ") + para[0]
                para = [first] + para[1:]
                carry = ""
            # 2) 本段最后一句若未收口 → **整句**顺延到下一段（不可只留末字）
            if para and para[-1]:
                if para[-1][-1] not in TERMINATORS:
                    carry = para[-1]
                    para = para[:-1]
            if not para:
                continue
            if not buf:
                first_title, first_ch = title, ch_idx
            buf.append(para)
            buf_chars += sum(len(s) for s in para)
            last_ch = ch_idx
            if buf_chars >= target:
                units.append({"title": first_title, "chapters": [first_ch, last_ch],
                              "paras": buf, "chars": buf_chars})
                buf, buf_chars, first_title = [], 0, None
    if buf and buf_chars >= target * TAIL_MIN_RATIO:
        units.append({"title": first_title, "chapters": [first_ch, last_ch],
                      "paras": buf, "chars": buf_chars})
    dropped = buf_chars if buf else 0
    return units, dropped, carry


def unit_text(u):
    """段内句子空格连接，**段落之间用换行**（M0 要求）。"""
    return "\n".join(" ".join(sents) for sents in u["paras"] if sents)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", default="ja,ko", help="逗号分隔：ja / ko")
    ap.add_argument("--suffix", default="", help="批次目录后缀（如 _r3），避免覆盖已有语料")
    ap.add_argument("--target-chars", type=int, default=TARGET_CHARS)
    args = ap.parse_args()

    for lang in [x.strip() for x in args.langs.split(",") if x.strip()]:
        cfg = dict(CONFIGS[lang])
        run_dir = cfg["run_dir"]
        if args.suffix:
            run_dir = run_dir.with_name(run_dir.name + args.suffix)
        cfg["run_dir"] = run_dir
        mat_dir = run_dir / "material"
        mat_dir.mkdir(parents=True, exist_ok=True)

        book = TXT / cfg["book"]
        text = book.read_text(encoding="utf-8-sig")
        chapters, stray = split_chapters(text, cfg["chapter_re"])
        if not chapters:
            raise RuntimeError(f"{book} 未匹配到章节标记")

        units, dropped, carry = build_units(chapters, target=args.target_chars)
        rows = []
        for i, u in enumerate(units, 1):
            uid = f"unit_{i:04d}"
            t = unit_text(u)
            (mat_dir / f"{uid}.txt").write_text(t, encoding="utf-8")
            rows.append({
                "unit": uid, "title": u["title"], "chapters": u["chapters"],
                "chars": len(t), "paragraphs": len(u["paras"]),
                "sentences": sum(len(p) for p in u["paras"]),
                "has_newline": "\n" in t,
                "ends_with_punct": t.rstrip()[-1] in TERMINATORS if t else False,
            })
        with (mat_dir / "units.jsonl").open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        chars = [r["chars"] for r in rows]
        paras = [r["paragraphs"] for r in rows]
        manifest = {
            "lang": cfg["lang"], "lang_cn": cfg["cn"], "book": str(book),
            "lang_code": cfg["lang_code"], "voice": cfg["voice"],
            "target_chars": args.target_chars,
            "format_rule": "保留原文段落：段内句子以空格连接，段落之间以换行分隔（M0 前置要求）",
            "chapters_total": len(chapters), "stray_marker_lines_removed": stray,
            "units_total": len(rows),
            "chars_min": min(chars), "chars_max": max(chars),
            "chars_avg": round(statistics.mean(chars), 1), "chars_median": statistics.median(chars),
            "paragraphs_min": min(paras), "paragraphs_max": max(paras),
            "paragraphs_avg": round(statistics.mean(paras), 1), "paragraphs_median": statistics.median(paras),
            "all_units_have_newline": all(r["has_newline"] for r in rows),
            "all_units_end_with_punct": all(r["ends_with_punct"] for r in rows),
            "chapters_used": max(r["chapters"][1] for r in rows) + 1,
            "dropped_tail_chars": dropped,
            "unterminated_carry_at_book_end": carry[:120],
        }
        (mat_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"=== {cfg['cn']} ({cfg['lang']}) ===")
        print(f"  书: {book.name}  章: {len(chapters)}  单元: {len(rows)}  清除残留标记行: {stray}")
        print(f"  字符: min={manifest['chars_min']} max={manifest['chars_max']} "
              f"avg={manifest['chars_avg']} median={manifest['chars_median']}")
        print(f"  段落: min={manifest['paragraphs_min']} max={manifest['paragraphs_max']} "
              f"avg={manifest['paragraphs_avg']}（**M0 要求 >=2 且保留换行**）")
        print(f"  全部单元含换行: {manifest['all_units_have_newline']}｜全部以句末标点结尾: "
              f"{manifest['all_units_end_with_punct']}｜丢弃尾部残段: {dropped} 字符")
        if manifest["paragraphs_min"] < 2:
            print("  ⚠️ 警告：存在段落数 <2 的单元，需检查原文分段")
        print(f"  产物: {mat_dir}")

    print("\n[OK] 语料构建完成（保留段落换行）")


if __name__ == "__main__":
    main()
