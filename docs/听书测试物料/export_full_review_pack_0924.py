# -*- coding: utf-8 -*-
r"""导出「完整分析包」= 现有 metadata 分析包 + 原书内容与章节映射。

在原包（metadata 原始/段级明细/证据/ASR/音频片段）基础上新增：
  08_原书全文/            两本原书 txt（日语 CEOの彼の罠に落ちた / 韩语 나의 가짜 아내）
  09_原书章节索引/        每本书的章节清单 CSV（章序、标题、字符数、起止字符位置）
  10_单元与原书映射/      units.jsonl（单元 → 章节区间 → 标题）+ 样本任务映射表
  11_原书片段_样本任务/   每个样本任务对应单元的**原书原文片段**（含章节标记）

并追加 README 章节说明「原书 → 单元 → 下发文案 → metadata → 音频」的对照方法。

用法：
  & "D:\python\python.exe" docs\听书测试物料\export_full_review_pack_0924.py
"""
import csv
import importlib.util
import json
import re
import shutil
from pathlib import Path

ROOT = Path(r"D:\python\dmx\cdtest")
MP3 = ROOT / "docs" / "听书测试物料" / "mp3"
BASE_SCRIPT = ROOT / "docs" / "听书测试物料" / "export_metadata_review_pack_0924.py"
NEW_PACK = ROOT / "docs" / "听书测试物料" / "开发分析包_metadata与原书_0924"
TXT = ROOT / "docs" / "听书测试物料" / "txt文本"

LANGS = {
    "ja": {"cn": "日语", "run": MP3 / "Higgs_日语_10并发30分钟_0924",
           "book": "日语-CEOの彼の罠に落ちた.txt",
           "chapter_re": r"^\s*=+\s*((?:第\d+章|チャプター\s*\d+)[^=\r\n]*?)\s*=+\s*$"},
    "ko": {"cn": "韩语", "run": MP3 / "Higgs_韩语_10并发30分钟_0924",
           "book": "韩语-나의 가짜 아내.txt",
           "chapter_re": r"^\s*=+\s*(제\d+화[^=\r\n]*?)\s*=+\s*$"},
}
FOCUS = {
    # 日语：静默段 + 超长段代表 + 正常对照
    "ja": [35, 54, 83, 49, 63, 6, 1],
    # 韩语：全部「估算音频缺口 >20%」的任务（16 个）+ 正常对照
    "ko": [71, 6, 87, 96, 119, 44, 82, 13, 40, 88, 64, 94, 8, 83, 69, 24, 1],
}

# 与 build_ja_ko_5000char_material.py 一致的清洗规则（用于「原书 ↔ metadata」可定位性校验）
_STRAY = re.compile(r"^\s*=+.*=+\s*$", re.MULTILINE)
_SEP = re.compile(r"^\s*([*\-=_~·•#…—])\1{2,}\s*$")


def norm_ns(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKC", s) if not c.isspace())


def clean_book(text):
    text = _STRAY.sub(" ", text)
    return "\n".join("" if _SEP.match(l) else l for l in text.split("\n"))


def locate_in_book(book_norm, seg_text, step=60):
    """返回 (是否命中, 连续可定位比例)"""
    t = norm_ns(seg_text)
    if not t or book_norm.find(t[: min(80, len(t))]) < 0:
        return False, 0.0
    i = 0
    while i + step <= len(t) and book_norm.find(t[i:i + step]) >= 0:
        i += step
    return True, round(i / len(t), 4)


def chapters_of(book_path, pattern):
    text = book_path.read_text(encoding="utf-8-sig")
    ms = list(re.finditer(pattern, text, flags=re.MULTILINE))
    out = []
    for i, m in enumerate(ms):
        start = m.end()
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        body = text[start:end].strip()
        out.append({"idx": i, "title": m.group(1).strip(), "chars": len(body),
                    "start": start, "end": end, "body": body})
    return out


def main():
    # 1) 先按原脚本生成基础包（metadata/证据/ASR/音频）
    spec = importlib.util.spec_from_file_location("meta_pack", BASE_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.PACK = NEW_PACK
    mod.FOCUS = FOCUS          # 同步样本任务清单（含全部受影响任务）
    print(f"[1/2] 生成基础包内容 -> {NEW_PACK}")
    mod.main()

    # 2) 追加原书内容与映射
    print("[2/2] 追加原书全文 / 章节索引 / 单元映射 / 原书片段")
    d_book = NEW_PACK / "08_原书全文"
    d_chap = NEW_PACK / "09_原书章节索引"
    d_map = NEW_PACK / "10_单元与原书映射"
    d_seg = NEW_PACK / "11_原书片段_样本任务"
    for d in (d_book, d_chap, d_map, d_seg):
        d.mkdir(parents=True, exist_ok=True)

    summary = []
    for lang, cfg in LANGS.items():
        cn, run = cfg["cn"], cfg["run"]
        book = TXT / cfg["book"]
        shutil.copy2(book, d_book / cfg["book"])
        chaps = chapters_of(book, cfg["chapter_re"])
        with (d_chap / f"{cn}_章节索引.csv").open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["idx", "title", "chars", "start_char", "end_char"])
            w.writeheader()
            for c in chaps:
                w.writerow({"idx": c["idx"], "title": c["title"], "chars": c["chars"],
                            "start_char": c["start"], "end_char": c["end"]})
        units_p = run / "material" / "units.jsonl"
        shutil.copy2(units_p, d_map / f"{cn}_units.jsonl")
        units = {json.loads(l)["unit"]: json.loads(l)
                 for l in units_p.read_text(encoding="utf-8").splitlines() if l.strip()}
        book_norm = norm_ns(clean_book(book.read_text(encoding="utf-8-sig")))

        # 样本任务映射表 + 原书片段
        rows = []
        for seq in FOCUS[lang]:
            rec = None
            for line in (run / "tasks.jsonl").read_text(encoding="utf-8").splitlines():
                if line.strip():
                    r = json.loads(line)
                    if r["seq"] == seq:
                        rec = r
                        break
            if not rec:
                continue
            unit = rec.get("unit")
            u = units.get(unit)
            a, b = (u["chapters"][0], u["chapters"][1]) if u else (None, None)
            titles = [c["title"] for c in chaps[a:b + 1]] if a is not None else []
            segs = json.loads((run / "meta" / f"task_{seq:04d}.json").read_text(encoding="utf-8"))
            body = [s for s in segs if s.get("paraIndex", -1) >= 0]
            by_chars = max(body, key=lambda s: len((s.get("text") or "").strip())) if body else None
            by_dur = max(body, key=lambda s: s["endMs"] - s["startMs"]) if body else None
            rows.append({
                "lang": lang, "lang_cn": cn, "seq": seq, "taskId": rec.get("taskId"),
                "unit": unit, "chapter_range": f"{a}~{b}" if a is not None else "",
                "chapter_titles": " / ".join(titles[:4]) + (" …" if len(titles) > 4 else ""),
                "book_file": cfg["book"],
                "src_chars": len((run / "src" / f"task_{seq:04d}.txt").read_text(encoding="utf-8")),
                "segments": len(body),
                # 最大字数段
                "max_chars_seg_chars": len((by_chars.get("text") or "").strip()) if by_chars else 0,
                "max_chars_seg_dur_s": round((by_chars["endMs"] - by_chars["startMs"]) / 1000, 2) if by_chars else None,
                "max_chars_seg_head": (by_chars.get("text") or "")[:60] if by_chars else "",
                # 最大时长段（静默占位常出现在这里）
                "max_dur_seg_dur_s": round((by_dur["endMs"] - by_dur["startMs"]) / 1000, 2) if by_dur else None,
                "max_dur_seg_chars": len((by_dur.get("text") or "").strip()) if by_dur else 0,
                "max_dur_seg_head": (by_dur.get("text") or "")[:60] if by_dur else "",
                # 原书 ↔ metadata 可定位性（验证「该段是原书连续文本」）
                "book_locate_ok": None, "book_contiguous_ratio": None,
            })
            if by_chars:
                hit, ratio = locate_in_book(book_norm, by_chars.get("text") or "")
                rows[-1]["book_locate_ok"] = hit
                rows[-1]["book_contiguous_ratio"] = ratio
            # 原书片段（该单元覆盖的章节原文，保留章节标记）
            if a is not None:
                parts = [f"=== {c['title']} ===" + "\n\n" + c["body"] for c in chaps[a:b + 1]]
                (d_seg / f"{cn}_task{seq:04d}_{unit}_原书_第{a}-{b}章.txt").write_text(
                    "\n\n".join(parts), encoding="utf-8")
        with (d_map / f"{cn}_样本任务与原书映射.csv").open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        summary += rows
        print(f"  [{cn}] 原书 {cfg['book']}（{len(chaps)} 章）｜单元 {len(units)} 个｜"
              f"样本任务 {len(rows)} 个｜原书片段已导出")

    # 追加 README 说明
    add = []
    A = add.append
    A("")
    A("---")
    A("")
    A("## 七、原书内容与对照方法（本包新增）")
    A("")
    A("| 目录 | 内容 |")
    A("|---|---|")
    A("| `08_原书全文/` | 两本原书全文 txt（与建语料时使用的同一份文件） |")
    A("| `09_原书章节索引/` | 每本书的章节清单（章序、标题、字符数、在书中的起止字符位置） |")
    A("| `10_单元与原书映射/` | `*_units.jsonl`（每个 ~5000 字符单元 ← 由哪些章拼接）＋"
      "`*_样本任务与原书映射.csv`（任务 → 单元 → 章节区间 → 标题 → 最长段信息） |")
    A("| `11_原书片段_样本任务/` | 每个样本任务对应的**原书原文片段**（保留 `=== 章标题 ===` 标记） |")
    A("")
    A("### 对照链路（每一环都有落盘文件，可逐级核对）")
    A("")
    A("```")
    A("原书 txt（08_原书全文）")
    A("  └─ 按章切分 → 09_原书章节索引.csv（章号/标题/字符数/字符位置）")
    A("       └─ 顺序累积整句至 ≥5000 字符 → 单元（10_单元与原书映射/*_units.jsonl：unit → chapters 区间）")
    A("            └─ 每任务下发一个单元 → 02_输入原文/task_XXXX.txt（read_content）")
    A("                 └─ 服务端切句/合成 → 01_metadata原始/task_XXXX.json（段文本 + 时间轴）")
    A("                      └─ 音频 → 06_音频片段/（含静默段与超长段片段）")
    A("```")
    A("")
    A("### 样本任务 → 原书位置")
    A("")
    A("| 语种 | seq | taskId | 单元 | 原书章节区间 | 章节标题（截断） | 最大字数段 | 最大时长段 | 原书可定位 |")
    A("|---|---:|---|---|---|---|---:|---:|---:|")
    for r in summary:
        loc = "—" if r.get("book_contiguous_ratio") is None else f"{100*r['book_contiguous_ratio']:.0f}%"
        A(f"| {r['lang_cn']} | {r['seq']} | {r['taskId']} | {r['unit']} | 第 {r['chapter_range']} 章 |"
          f" {r['chapter_titles'][:34]} | {r['max_chars_seg_chars']} 字 / {r['max_chars_seg_dur_s']}s |"
          f" {r['max_dur_seg_chars']} 字 / {r['max_dur_seg_dur_s']}s | {loc} |")
    A("")
    A("> **「原书可定位」列**：把该任务**最大字数段**的文本按与建语料一致的清洗规则（去章节标记、去 `******` 等分隔行、"
      "去空白）拿去原书里做连续子串定位，得到的**连续覆盖率**。")
    A("> 例如韩语 0040 的那个段（1757 字含空格 / 1328 字去空白，时间轴仅 6.33s）可定位率达 **99%** → "
      "证明该「段」是**原书里连续的一大段文字被服务端合并成了一个句子**，并非跨章拼接或改写；"
      "随后这段在合成阶段丢了 88%（整段 ASR 实测）。")
    A("")
    A("> 用法：先在 `10_单元与原书映射/*_样本任务与原书映射.csv` 找到某任务的章节区间，"
      "再到 `11_原书片段_样本任务/` 打开对应原书片段，即可确认「丢失的那段文本在原书里是什么内容」。")
    A("> 例如韩语 0040（整段 ASR 实测缺失 34.55%）那个 1757 字的超长段，其文本在原书中连续可定位 → "
      "说明服务端把**本应切成几十句的一大段原书内容合并成了一“句”**，随后在合成阶段丢了其中的 88%。")
    A("")
    (NEW_PACK / "README.md").write_text(
        (NEW_PACK / "README.md").read_text(encoding="utf-8") + "\n".join(add), encoding="utf-8")

    total = sum(f.stat().st_size for f in NEW_PACK.rglob("*") if f.is_file())
    n = sum(1 for f in NEW_PACK.rglob("*") if f.is_file())
    print(f"\n[OK] 完整包：{NEW_PACK}")
    print(f"     {n} 个文件｜{total/1048576:.1f} MB")
    for d in sorted(p for p in NEW_PACK.iterdir() if p.is_dir()):
        print(f"     {d.name}/  {sum(1 for _ in d.rglob('*') if _.is_file())} 个文件")


if __name__ == "__main__":
    main()
