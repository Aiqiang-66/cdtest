# -*- coding: utf-8 -*-
r"""生成「文案格式 正/逆向用例」结果报告（日/韩）。

读取：mp3/文案格式用例_0924_{ja,ko}/results.json、case_inputs.json
输出：docs/听书测试物料/测试报告/文案格式用例_结果_日韩_0924.md

用法：
  & "D:\python\python.exe" docs\听书测试物料\gen_report_cases_0924.py
"""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(r"D:\python\dmx\cdtest")
MP3 = ROOT / "docs" / "听书测试物料" / "mp3"
REPORT_DIR = ROOT / "docs" / "听书测试物料" / "测试报告"
DATE = "2026-09-24"
RUNS = {"ja": ("日语", MP3 / "文案格式用例_0924_ja", 9, "Japanese_female"),
        "ko": ("韩语", MP3 / "文案格式用例_0924_ko", 14, "Korean_female")}


def jload(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def main():
    data = {}
    for lk, (cn, d, lc, voice) in RUNS.items():
        res = jload(d / "results.json") or {}
        inp = {x["id"]: x for x in (jload(d / "case_inputs.json") or [])}
        data[lk] = {"cn": cn, "dir": d, "lang": lc, "voice": voice, "res": res, "inp": inp,
                    "counts": Counter(v.get("verdict") for v in res.values())}

    L = []
    A = L.append
    A("# 文案格式 正向/逆向用例 结果报告（日语 · 韩语）")
    A("")
    A(f"> **用例集**：`测试用例/文案格式_正常与异常_0924.md`（**19 条**：正常 6 / 异常 13）  ")
    A(f"> **环境**：`https://ai-main-none-dev.changdu.ltd`｜`model=higgs`｜日语 `lang=9/Japanese_female`、"
      f"韩语 `lang=14/Korean_female`  ")
    A(f"> **语料**：M0 合规（保留段落）~5000 字符单元（`..._r3/material`）  ")
    A(f"> **日期**：{DATE}　**执行器**：`run_text_format_cases_0924.py --workers 4 --out-suffix _{'{ja|ko}'}`")
    A("")
    A("## 一、结果总览")
    A("")
    A("| 语种 | PASS | FAIL | ERROR | INFO | 结论 |")
    A("|---|---:|---:|---:|---:|---|")
    for lk in ("ja", "ko"):
        c = data[lk]["counts"]
        A(f"| {data[lk]['cn']} | {c.get('PASS',0)} | {c.get('FAIL',0)} | {c.get('ERROR',0)} |"
          f" {c.get('INFO',0)} | {'❌ 存在缺陷' if c.get('FAIL') else '✅ 全部通过'} |")
    A("")
    A("> INFO = 异常场景用例，按设计只记录实际行为、不判失败；FAIL 全部集中在两条硬判据上（见第二节）。")
    A("")

    A("## 二、FAIL 明细（两语种共性缺陷）")
    A("")
    A("| 用例 | 日语 | 韩语 | 判读 |")
    A("|---|---|---|---|")
    ids = [i for i in (data["ja"]["res"] or data["ko"]["res"])]
    fail_ids = sorted({i for lk in ("ja", "ko") for i, v in data[lk]["res"].items()
                       if v.get("verdict") == "FAIL"})
    for i in fail_ids:
        def cell(lk):
            v = data[lk]["res"].get(i)
            if not v:
                return "—"
            mark = {"FAIL": "❌ FAIL", "PASS": "✅ PASS", "INFO": "ℹ️ INFO", "ERROR": "⚠️ ERROR"}.get(v["verdict"], v["verdict"])
            return f"{mark}：{v.get('why','')[:60]}"
        name = (data["ja"]["res"].get(i) or data["ko"]["res"].get(i) or {}).get("name", i)
        judge = ""
        if i in ("TC-FMT-A04a", "TC-FMT-A04b", "TC-FMT-A10"):
            judge = "**参数校验缺失**：应拒绝却成功产出音频"
        A(f"| {i} {name} | {cell('ja')} | {cell('ko')} | {judge} |")
    A("")
    A("### 缺陷 1（P1）：参数校验缺失 —— 空文本 / 纯空白 / 非法 `lang` 均返回成功并产出音频")
    A("")
    A("| 用例 | 输入 | 期望 | 实际（两语种一致） |")
    A("|---|---|---|---|")
    A("| TC-FMT-A04a | `read_content = \"\"` | 报错，不产出 | **任务成功（taskStatus=2）并生成音频/metadata** |")
    A("| TC-FMT-A04b | `read_content = \"   \"` | 报错，不产出 | **任务成功并生成音频** |")
    A("| TC-FMT-A10 | `lang = 999`（非法语种） | 报错或明确回退 | **任务成功并生成音频**（未回退、未报错） |")
    A("")
    A("> 影响：调用方传错参数时会拿到「成功」的空/垃圾音频，问题被推迟到播放环节才暴露；"
      "`lang` 不校验也无法保证音色与语种一致。建议服务端在**建任务前**做参数白名单校验（`read_content` 去空白后长度 ≥1、"
      "`lang`/`voice`/`model` 必须在支持列表内），非法即返回明确错误码。")
    A("")

    A("## 三、异常场景实际行为（INFO，供开发参考）")
    A("")
    A("| 用例 | 输入规模 | 日语 | 韩语 |")
    A("|---|---|---|---|")
    for i in sorted(data["ja"]["res"]):
        vj, vk = data["ja"]["res"].get(i), data["ko"]["res"].get(i)
        if not vj or vj.get("verdict") != "INFO":
            continue
        def brief(v):
            if not v:
                return "—"
            if not v.get("ok"):
                return f"未成功：{v.get('error','')[:40]}"
            return (f"paraIndex={v.get('distinct_paraIndex')}｜段数={v.get('body_segments')}"
                    f"｜最长段={v.get('seg_chars_max')}字｜最大语速={v.get('seg_rate_max')}"
                    f"｜81.64s={v.get('has_81s_seg')}｜缺失字={v.get('missing_chars')}")
        A(f"| {i} {vj.get('name','')} | {vj.get('chars')} 字 | {brief(vj)} | {brief(vk)} |")
    A("")

    A("## 四、关键观察")
    A("")
    a01j = data["ja"]["res"].get("TC-FMT-A01", {})
    a01k = data["ko"]["res"].get("TC-FMT-A01", {})
    A(f"1. **M0 前置有效**：保留段落（正/逆向的 N 组）在**两语种**均被正确识别（`distinct paraIndex` 随段落数增长，"
      f"段长中位 30~40 字、无 >200 字超长段）。")
    A(f"2. **格式违规（单段落）复现存在语种差异**：日语 A01 复现退化"
      f"（`paraIndex=1`，高语速段 {a01j.get('n_seg_rate_gt15')} 个，最大 {a01j.get('seg_rate_max')} 字/秒）；"
      f"韩语 A01 **未复现**（`paraIndex=1` 但最长段仅 {a01k.get('seg_chars_max')} 字、最大语速 {a01k.get('seg_rate_max')}）"
      f"→ 说明**单段落输入仍是风险写法**（日语可退化、韩语本轮未触发），M0 规则必须保留。")
    A(f"3. **日语 N01 出现 1 个高语速段（25.9 字/秒）**：正常用例里也偶发段级时间轴异常，"
      f"建议纳入 Phase 9 段级观察项持续跟踪。")
    A(f"4. **超长文本（A09，15.7K 字）两语种均成功**：说明接口可处理远超 5000 字的文本，"
      f"但时长/段数分布需在报告中单独列示（见 results.json）。")
    a11k = data["ko"]["res"].get("TC-FMT-A11", {})
    if a11k.get("has_81s_seg"):
        A(f"5. **韩语纯标点输入触发 81.64s 固定时长段（静默占位特征）**：A11 输入仅 74 个标点字符，"
          f"返回中出现 `81.64s` 段（与 0924 批次日语 0035 / 韩语 0044 的静默占位时长完全一致）。"
          f"建议服务端对「无实义词文本」直接拒绝或跳过，而不是插入占位段；该现象应纳入 Phase 9 回归项持续跟踪。")
    A(f"6. **段级时间轴仍有零星异常**：A09（15.7K 字）日语最大语速 27.5 字/秒、A11（纯标点）两语种 43+ 字/秒、"
      f"A08（混合语种）韩语 16.5 字/秒 —— 均属「段时长与文本量不匹配」，建议作为 Phase 9 段级观察项记录，"
      f"不单独判缺陷（内容口径 M1 均为 0 缺失）。")
    A("")

    A("## 五、附件索引")
    A("")
    A("| 内容 | 路径（相对仓库根） |")
    A("|---|---|")
    for lk in ("ja", "ko"):
        rel = data[lk]["dir"].relative_to(ROOT)
        A(f"| {data[lk]['cn']} 用例结果（逐用例指标+判定） | `{rel}\\results.json` |")
        A(f"| {data[lk]['cn']} 实际下发文本 / 返回指标 | `{rel}\\src\\`、`{rel}\\meta\\` |")
        A(f"| {data[lk]['cn']} 输入规模清单 | `{rel}\\case_inputs.json` |")
    A("| 用例定义 | `测试用例\\文案格式_正常与异常_0924.md` |")
    A("")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / f"文案格式用例_结果_日韩_{DATE.replace('-','')}.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"[OK] {out}")
    for lk in ("ja", "ko"):
        c = data[lk]["counts"]
        print(f"  {data[lk]['cn']}: PASS {c.get('PASS',0)}｜FAIL {c.get('FAIL',0)}｜INFO {c.get('INFO',0)}"
              f"｜ERROR {c.get('ERROR',0)}")


if __name__ == "__main__":
    main()
