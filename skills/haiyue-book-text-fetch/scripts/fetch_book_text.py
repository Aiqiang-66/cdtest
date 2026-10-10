# -*- coding: utf-8 -*-
r"""海阅书籍正文拉取 —— 把整本书的章节正文落盘为文本语料。

接口: POST {BASE}/api/AutoCreation/Task/GetBookChapter
      Body: {"bookId":"<id>","from":1,"to":5}   (区间，推荐)
            或 {"bookId":"<id>","top":3}        (取前 N 章)
      响应: {"data":[{"i":"1","chapterName":"...","chapterContent":"..."}],
             "code":200,"isSuccess":true,"message":"操作成功"}
      data 为空数组 = 已到书末。

产物格式（与既有 XR3 语料一致，下游按行首 === 切章）:
    === <chapterName> ===
    <空行>
    <chapterContent>
    <空行>

常用:
    fetch_book_text.py --library                       # 拉取/刷新全量书库并缓存（约 4.4 万本）
    fetch_book_text.py --library --stats               # 只看书库语种分布
    fetch_book_text.py --search 少女 --language 9      # 在书库里挑书（日语）
    fetch_book_text.py --list-books                    # 内置快捷清单（快照，可能失效）
    fetch_book_text.py --probe-books                   # 对照书库+实拉，校验内置清单
    fetch_book_text.py --check-token --token-file <path>
    fetch_book_text.py --lang kr                       # 快捷方式：直接拉内置清单里的书
    fetch_book_text.py --lang kr --lang jp --max-chapters 40
    fetch_book_text.py --book-id 410419 --out-name "日语-xxx.txt"
    fetch_book_text.py --verify <txt路径>

数据来源（务必知悉）:
    书籍元数据来自 ai_center 库(TiDB) ObjectBook，章节正文来自 ObjectChapter/ObjectCatChapter，
    经 adassetserver 接口对外。内置 BOOKS 只是**抓包记录里的快照**，书可能被下架
    （实测 hi/pl 的 bookId 已不在库中 -> GetBookChapter 返回空 data）。
    要确认某本书现在是否可用，用 --search / --library，不要直接信内置清单。

实测经验（详见 SKILL.md）:
  * 大区间请求会超时 -> 默认每批 5 章
  * 长时间任务中断会白跑 -> 默认每 10 批中途落盘
  * token 约 10 小时过期 -> 先 --check-token
  * 日文章名混用「第N章」「チャプター N」-> --verify 反推正则，勿凭猜写死
  * GetTgtCodeInfo 的 keyword 参数不生效 -> 只能客户端过滤
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
import unicodedata
import urllib3
from pathlib import Path

import requests

urllib3.disable_warnings()

# ---------------------------------------------------------------- 常量

DEFAULT_BASE = "https://adassetserver-cn-new-test1.changdu.ltd"
DEFAULT_TOKEN_FILE = Path(r"D:\python\dmx\cdtest\temp_token_prod.txt")
DEFAULT_OUT_DIR = Path(r"D:\python\dmx\cdtest\docs\听书测试物料\txt文本")
# 书库缓存放在临时目录，避免污染技能目录（技能目录是逐字节镜像，缓存不该入库）
DEFAULT_LIB_CACHE = Path(os.environ.get("TEMP", ".")) / "haiyue_book_library.json"
LIB_TTL = 24 * 3600     # 书库缓存有效期（秒）

BATCH = 5           # 单批章节数（大区间必超时）
TIMEOUT = 240       # 单请求超时（秒）
RETRY = 3           # 失败重试次数
SAVE_EVERY = 10     # 每多少批中途落盘
HARD_CAP = 5000     # 无上限模式的安全上限
MAX_GROUPS = 10     # --verify 最多列出的章名结构类别数

# language 编号 -> 中文语种名（与 ELEVENLABS_LANG_MAP 一致）
# 19/20 不在标准映射内，实测为中文书（19=简体，20=简繁混）；library 里共 4 本，
# 其中仅 2 本能取到正文（22104449491 简 / 22104449492 繁，同一本书的两版）。
LANG_NAMES: dict[int, str] = {
    1: "中文", 2: "繁体中文", 3: "英语", 4: "西语", 5: "葡语", 6: "法语", 7: "俄语",
    8: "意大利语", 9: "日语", 10: "阿拉伯语", 11: "印尼语", 12: "泰语", 13: "越南语",
    14: "韩语", 15: "菲律宾语", 16: "德语", 17: "印地语", 19: "中文(简体)",
    20: "中文(繁/简)", 21: "马来语", 22: "土耳其语", 23: "波兰语",
}

# lang -> (language 编号, bookId, 中文语种名, 书名)
# 快捷方式清单。**这是抓包记录的快照，不是实时书库**：书可能被下架，bookId 可能失效。
# 每条均于 2026-09-23 在 test1 实拉通过；维护时用 --probe-books 对照实时书库复验。
# 需要清单以外的书 -> 用 --search / --library 从实时书库挑。
BOOKS: dict[str, tuple[int, str, str, str]] = {
    "ft": (2,  "99965466298", "繁体中文", "甜妻在上：老公，慢一點"),
    "en": (3,  "56385322",    "英语",     "My Alpha, My Enemy"),
    "sp": (4,  "3467375",     "西语",     "Acepto ser tu Mate"),
    "pt": (5,  "1155409",     "葡语",     "NÃO SIRVO PARA REINAR"),
    "fr": (6,  "6148410",     "法语",     "La femme du prince"),
    "ru": (7,  "6858418",     "俄语",     "ЕВА"),
    "it": (8,  "32304413",    "意大利语", "Il genio dimenticato: Rinascita dalle rovine"),
    "jp": (9,  "410419",      "日语",     "CEOの彼の罠に落ちた"),
    "ar": (10, "28898415",    "阿拉伯语", "عندما يأتي: الحب متأخرا"),
    "id": (11, "10030414",    "印尼语",   "Janda Lugu"),
    "th": (12, "5988433",     "泰语",     "บัวริมทาง"),
    "vi": (13, "74178435",    "越南语",   "Lệ tổng, chồng cũ của phu nhân lại tới"),
    "kr": (14, "39900436",    "韩语",     "나의 가짜 아내"),
    "tl": (15, "70467445",    "菲律宾语", "Muling pagsilang ang masilaw na babae"),
    "de": (16, "19873412",    "德语",     "Narben einer zerbrochenen Bindung"),
    "my": (21, "116465495",   "马来语",   "Kahwin Kilat Dengan Ayah Kawan Baikku"),
    "tr": (22, "86180497",    "土耳其语", "Eski Kocanın Pişmanlığı"),
}

# 接口记录里出现过、但 **2026-09-23 在 test1 探活返回空 data** 的条目（来自 09-16 早期批次，
# 可能属其它环境或已下架）。不纳入默认清单；如确认有效请移入 BOOKS 并用 --probe-books 复验。
RECORDED_ONLY: list[tuple[str, int, str]] = [
    ("hi", 17, "66589447"),
    ("pl", 23, "125996501"),
    ("pl", 23, "66474501"),
]

# 已实测的切章正则（100% 命中）；其它语种请用 --verify 反推，勿凭猜写死
VERIFIED_MARKERS: dict[str, str] = {
    "kr": r"^===\s*제\s*\d+\s*화",
    "jp": r"^===\s*(第\s*\d+\s*章|チャプター\s*\d+)",
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------- token

def token_exp(token: str):
    """解析 JWT 的 exp；失败返回 None。"""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload)).get("exp")
    except Exception:
        return None


def load_token(token: str | None, token_file: Path | None) -> str:
    if token:
        return token.strip()
    path = token_file or DEFAULT_TOKEN_FILE
    if not path.is_file():
        raise SystemExit(f"token 文件不存在：{path}\n先运行 scripts/get_token.py 获取，或用 --token/--token-file 指定。")
    return path.read_text(encoding="utf-8").strip()


def check_token(token: str) -> tuple[bool, str]:
    exp = token_exp(token)
    if exp is None:
        return True, "无法解析 exp（可能不是标准 JWT），跳过时效检查"
    left = (exp - time.time()) / 3600.0
    if left <= 0:
        return False, f"已过期 {abs(left):.2f} 小时（exp={exp}）"
    return True, f"剩余 {left:.2f} 小时（exp={exp}）"


# ---------------------------------------------------------------- 书库（实时）

def fetch_library(session, token, base, timeout) -> dict[str, dict]:
    """从 GetTgtCodeInfo 拉全量书库（tgtType=1，约 4.4 万本）。

    ⚠️ 实测 keyword 参数不生效（传任何词都返回全量），因此一律客户端过滤。
    """
    r = session.post(f"{base}/api/Common/GetTgtCodeInfo",
                     headers=headers(token), json={"tgtType": 1},
                     timeout=timeout, verify=False)
    d = r.json()
    if d.get("code") != 200 or not d.get("isSuccess"):
        raise RuntimeError(f"书库拉取失败：HTTP {r.status_code} code={d.get('code')} msg={d.get('message')}")
    return {str(it["id"]): it for it in (d.get("data") or [])}


def load_library(session, token, base, timeout, cache: Path, refresh: bool) -> dict[str, dict]:
    if not refresh and cache.is_file():
        age = time.time() - cache.stat().st_mtime
        if age < LIB_TTL:
            try:
                lib = json.loads(cache.read_text(encoding="utf-8"))
                log(f"书库缓存命中：{len(lib):,} 本（{age/3600:.1f} 小时前，TTL {LIB_TTL/3600:.0f}h）")
                return lib
            except Exception as e:
                log(f"⚠️ 缓存损坏（{type(e).__name__}），重新拉取")
        else:
            log(f"书库缓存已过期（{age/3600:.1f} 小时前），重新拉取")
    log("拉取全量书库 ...")
    t0 = time.time()
    lib = fetch_library(session, token, base, timeout)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(lib, ensure_ascii=False), encoding="utf-8")
    log(f"书库已缓存 {len(lib):,} 本（{time.time()-t0:.1f}s）-> {cache}")
    return lib


def lang_name(code) -> str:
    try:
        return LANG_NAMES.get(int(code), f"未知({code})")
    except Exception:
        return f"未知({code})"


def library_stats(lib: dict[str, dict]) -> None:
    from collections import Counter
    c = Counter(it.get("language") for it in lib.values())
    log(f"书库共 {len(lib):,} 本，按 language 分布：")
    for code, n in c.most_common():
        log(f"    language={str(code):<4} {lang_name(code):<10} {n:>7,} 本")


def search_library(lib, keywords, languages, limit, out_json=None) -> list[dict]:
    kw = [k.lower() for k in keywords]
    hits = []
    for bid, it in lib.items():
        if languages and it.get("language") not in languages:
            continue
        if kw:
            hay = f"{bid} {it.get('code','')} {it.get('name','')} {it.get('label','')}".lower()
            if not all(k in hay for k in kw):
                continue
        hits.append(it)
    # 有书名时按名称排序，稳定可读
    hits.sort(key=lambda it: (it.get("language") or 0, str(it.get("name") or "")))
    if out_json:
        Path(out_json).write_text(json.dumps(hits, ensure_ascii=False, indent=1), encoding="utf-8")
        log(f"命中结果已写入 {out_json}")
    return hits[:limit] if limit > 0 else hits


# ---------------------------------------------------------------- 拉取

def headers(token: str) -> dict:
    return {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
        "Referer": "https://sc-test.changdu.ltd/",
        "User-Agent": "Mozilla/5.0",
    }


def fetch_range(session, token, base, book_id, start, end, timeout):
    body = {"bookId": str(book_id), "from": start, "to": end}
    last = None
    for i in range(RETRY):
        try:
            r = session.post(f"{base}/api/AutoCreation/Task/GetBookChapter",
                             headers=headers(token), json=body, timeout=timeout, verify=False)
            d = r.json()
            if d.get("code") != 200 or not d.get("isSuccess"):
                last = f"HTTP {r.status_code} code={d.get('code')} msg={d.get('message')}"
            else:
                return True, (d.get("data") or []), None
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
        if i < RETRY - 1:
            time.sleep(3 * (i + 1))
    return False, [], last


def clean(text: str) -> str:
    """\\r\\n -> \\n，去行尾空白，压缩连续空行。"""
    if not text:
        return ""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    out, blank = [], 0
    for ln in t.split("\n"):
        ln = ln.rstrip()
        if ln.strip():
            blank = 0
            out.append(ln)
        else:
            blank += 1
            if blank == 1:
                out.append("")
    return "\n".join(out).strip()


def dump(chapters: list[dict], path: Path) -> Path:
    parts = []
    for c in chapters:
        parts += [f"=== {c['name']} ===", "", c["content"], ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    return path


def fetch_book(session, token, base, book_id, out_path, max_chapters, batch,
               timeout, save_every) -> dict:
    limit = max_chapters if max_chapters > 0 else HARD_CAP
    chapters, nxt = [], 1
    while len(chapters) < limit:
        end = min(nxt + batch - 1, limit)
        ok, data, err = fetch_range(session, token, base, book_id, nxt, end, timeout)
        if not ok:
            log(f"  拉取 {nxt}-{end} 失败：{err}（已得 {len(chapters)} 章，提前结束）")
            break
        if not data:
            log(f"  {nxt}-{end} 无数据，判定书末")
            break
        for c in data:
            content = clean(c.get("chapterContent"))
            if content:
                chapters.append({"i": c.get("i"),
                                 "name": (c.get("chapterName") or f"Chapter {c.get('i')}").strip(),
                                 "content": content})
        log(f"  {nxt}-{end} -> {len(data)} 章，累计 {len(chapters)} 章")
        if save_every and (end // batch) % save_every == 0:
            dump(chapters, out_path)
            log(f"  [中途落盘] {len(chapters)} 章")
        if len(data) < (end - nxt + 1):
            log("  返回不足请求量，判定书末")
            break
        nxt = end + 1
    else:
        log(f"  达到上限 {limit} 章（书可能更长）")

    if not chapters:
        log("  ❌ 0 章：该 bookId 在当前环境无数据，或 from/to 越界。")
        log("     **不写文件**（避免产出空白语料，也不会覆盖已有文件）。")
        log("     请用 --list-books 核对 bookId，或改用 --token-file 指向对应环境的 token。")
        return {"chapters": 0, "chars": 0, "bytes": 0, "path": str(out_path), "ok": False}

    dump(chapters, out_path)
    chars = sum(len(c["content"]) for c in chapters)
    log(f"  已写入 {out_path.name}：{len(chapters)} 章 / {chars:,} 字符 / {out_path.stat().st_size:,} 字节")
    return {"chapters": len(chapters), "chars": chars, "bytes": out_path.stat().st_size,
            "path": str(out_path), "ok": True}


# ---------------------------------------------------------------- 校验

def marker_key(body: str) -> str:
    """抽取「章节编号结构」作为分组键。

    只保留开头到章节编号（含紧跟的一个单位字），忽略后面的标题正文。
      제1화 바람          -> 제#화
      第1章あなたは…        -> 第#章
      チャプター 60  ウェンディ -> チャプター #
    """
    m = re.search(r"\d+", body)
    if not m:
        return body[:12]
    end = m.end()
    tail = body[end] if (end < len(body) and not body[end].isspace()) else ""
    return body[:m.start()] + "\x00" + tail


def suggest_regex(items: list[str]) -> str:
    """由同类章名反推候选正则：编号结构 -> \\d+。"""
    prefix = marker_key(items[0].strip("= ").strip()).rstrip()
    if not prefix or prefix == "\x00":
        return "(无法反推：章名开头无编号)"
    return "^===\\s*" + re.escape(prefix).replace("\x00", r"\d+")


def verify(path: Path) -> int:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        log(f"❌ 无法按 UTF-8 解码：{e}")
        return 1
    lines = text.splitlines()
    marks = [ln for ln in lines if ln.startswith("===")]
    bad = text.count("\ufffd")
    b0m = raw[:3] == b"\xef\xbb\xbf"

    log(f"文件：{path}")
    log(f"  体积 {len(raw):,} 字节 | 字符 {len(text):,} | 行 {len(lines):,} | "
        f"BOM={'是' if b0m else '否'} | 章标记 {len(marks)} | U+FFFD 乱码 {bad}")

    if not marks:
        log("  ❌ 未发现 '===' 章标记，请确认文件格式")
        return 1

    # 按「章节编号结构」分组（不是按整条标题，否则每章一组）
    groups: dict[str, list[str]] = {}
    for m in marks:
        body = m.strip("= ").strip()
        groups.setdefault(marker_key(body), []).append(body)

    log(f"  章名结构 {len(groups)} 类：")
    for key, items in sorted(groups.items(), key=lambda kv: -len(kv[1]))[:MAX_GROUPS]:
        log(f"    {len(items):>5} 章 × [{items[0][:30]}]")
        log(f"           建议正则: {suggest_regex(items)}")
    if len(groups) > MAX_GROUPS:
        log(f"    … 另有 {len(groups) - MAX_GROUPS} 类未列出")

    log(f"  首个标记：{marks[0]!r}")
    log(f"  末个标记：{marks[-1]!r}")

    if bad:
        log(f"  ❌ 存在 {bad} 个乱码字符（U+FFFD），语料不可用")
        return 1
    if len(groups) > 1:
        log("  ⚠️ 章名有多种样式：切章正则必须兼容全部样式，否则会静默漏章")
    log("  ✅ 校验通过" if len(groups) == 1 else "  ⚠️ 需确认切章正则")
    return 0


# ---------------------------------------------------------------- CLI

def main() -> int:
    ap = argparse.ArgumentParser(description="海阅书籍正文拉取")
    ap.add_argument("--lang", action="append", default=[],
                    help=f"语种码，可重复；可选：{', '.join(sorted(BOOKS))}")
    ap.add_argument("--book-id", help="直接指定 bookId（配合 --out-name）")
    ap.add_argument("--out-name", help="输出文件名（默认 <语种名>-<书名>.txt）")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--max-chapters", type=int, default=0, help="单本上限；0=拉到书末")
    ap.add_argument("--batch", type=int, default=BATCH, help=f"每批章数（默认 {BATCH}，调大会超时）")
    ap.add_argument("--timeout", type=int, default=TIMEOUT, help=f"单请求超时秒（默认 {TIMEOUT}）")
    ap.add_argument("--save-every", type=int, default=SAVE_EVERY, help=f"每 N 批中途落盘（默认 {SAVE_EVERY}）")
    ap.add_argument("--base", default=DEFAULT_BASE, help=f"接口基址（默认 {DEFAULT_BASE}）")
    ap.add_argument("--token", default=None, help="直接传 JWT")
    ap.add_argument("--token-file", type=Path, default=None, help=f"token 文件（默认 {DEFAULT_TOKEN_FILE}）")
    ap.add_argument("--list-books", action="store_true", help="列出内置快捷清单（快照）后退出")
    ap.add_argument("--library", action="store_true",
                    help="拉取/刷新实时全量书库并缓存；配合 --stats 只看分布")
    ap.add_argument("--stats", action="store_true", help="打印书库语种分布")
    ap.add_argument("--search", action="append", default=[],
                    help="在实时书库里按关键词筛选（书名/code/id，可重复=AND）；配合 --language")
    ap.add_argument("--language", action="append", type=int, default=[],
                    help="按 language 编号筛选，可重复（如 --language 9 日语）")
    ap.add_argument("--limit", type=int, default=30, help="--search 输出条数上限（0=全部，默认 30）")
    ap.add_argument("--search-json", type=Path, default=None, help="把 --search 结果写入 JSON 文件")
    ap.add_argument("--cache", type=Path, default=DEFAULT_LIB_CACHE, help=f"书库缓存路径（默认 {DEFAULT_LIB_CACHE}）")
    ap.add_argument("--refresh", action="store_true", help="忽略书库缓存，强制重新拉取")
    ap.add_argument("--probe-books", action="store_true",
                    help="对照实时书库 + 实拉首章，校验内置快捷清单")
    ap.add_argument("--check-token", action="store_true", help="只检查 token 时效后退出")
    ap.add_argument("--verify", type=Path, help="校验已落盘语料（章标记/编码/建议正则）后退出")
    a = ap.parse_args()

    # ---- 纯离线动作 ----
    if a.list_books:
        print("内置快捷清单（**抓包快照**，非实时书库；书可能已下架）")
        print(f"{'lang':<5}{'language':>9}  {'bookId':<13}{'语种':<11}书名")
        print("-" * 88)
        for code, (ln, bid, cn, title) in sorted(BOOKS.items(), key=lambda kv: kv[1][0]):
            print(f"{code:<5}{ln:>9}  {bid:<13}{cn:<11}{title}")
        print(f"\n共 {len(BOOKS)} 个语种。已实测切章正则：{', '.join(VERIFIED_MARKERS)}")
        print("需要清单以外的书 -> 用 --search 从实时书库挑；校验这些是否还有效 -> --probe-books")
        if RECORDED_ONLY:
            print("\n⚠️ 以下条目仅见于接口记录，2026-09-23 已确认**不在实时书库**（已下架）：")
            for code, ln, bid in RECORDED_ONLY:
                print(f"    {code} (language={ln}, bookId={bid})")
        return 0

    if a.verify:
        return verify(a.verify)

    # ---- 需要 token ----
    token = load_token(a.token, a.token_file)
    ok, desc = check_token(token)
    log(f"token：{desc}")
    if a.check_token:
        return 0 if ok else 1
    if not ok:
        log("❌ token 已过期，请先运行 scripts/get_token.py 重取")
        return 1
    session = requests.Session()

    # ---- 书库：分布 ----
    if a.stats:
        lib = load_library(session, token, a.base, a.timeout, a.cache, a.refresh)
        library_stats(lib)
        return 0

    # ---- 书库：刷新 ----
    if a.library and not a.search:
        lib = load_library(session, token, a.base, a.timeout, a.cache, refresh=True)
        library_stats(lib)
        return 0

    # ---- 书库：搜索（给 --search 或 --language 即进入）----
    if a.search or a.language:
        lib = load_library(session, token, a.base, a.timeout, a.cache, a.refresh)
        total = len(search_library(lib, a.search, a.language, 0))
        hits = search_library(lib, a.search, a.language, a.limit, a.search_json)
        cond = f"关键词={' AND '.join(a.search) or '（无）'}"
        if a.language:
            cond += " language=" + ",".join(f"{n}({lang_name(n)})" for n in a.language)
        log(f"命中 {total:,} 本  [{cond}]，显示前 {len(hits)} 条：")
        print(f"\n{'bookId':<13}{'code':<12}{'language':<16}书名")
        print("-" * 92)
        for it in hits:
            print(f"{str(it.get('id')):<13}{str(it.get('code')):<12}"
                  f"{str(it.get('language')) + '(' + lang_name(it.get('language')) + ')':<16}"
                  f"{str(it.get('name'))[:46]}")
        if total > len(hits):
            print(f"… 另有 {total - len(hits):,} 条（--limit 0 可全列，或 --search-json 导出）")
        print(f"\n挑好后拉取：--book-id <bookId> --out-name \"<语种>-<书名>.txt\"")
        return 0

    # ---- 校验内置清单（对照实时书库 + 实拉）----
    if a.probe_books:
        try:
            lib = load_library(session, token, a.base, a.timeout, a.cache, a.refresh)
        except Exception as e:
            log(f"⚠️ 书库拉取失败（{type(e).__name__}: {e}），仅做实拉校验")
            lib = {}
        in_lib_missing, fetch_fail = [], []
        for code, (ln, bid, cn, title) in sorted(BOOKS.items(), key=lambda kv: kv[1][0]):
            tag = "在库" if (not lib or bid in lib) else "不在库"
            ok2, data, err = fetch_range(session, token, a.base, bid, 1, 1, a.timeout)
            if ok2 and data:
                mark = "✅" if tag == "在库" else "⚠️"
                log(f"  {mark} {code:<4} {bid:<12} lang={ln:<3} {tag}  首章={data[0].get('chapterName','')[:30]!r}")
            else:
                log(f"  ❌ {code:<4} {bid:<12} lang={ln:<3} {tag}  {err or '空数据'}")
                (in_lib_missing if tag == "不在库" else fetch_fail).append(code)
        bad = in_lib_missing + fetch_fail
        if in_lib_missing:
            log(f"⚠️ 已下架（建议从 BOOKS 移除）：{in_lib_missing}")
        if fetch_fail:
            log(f"⚠️ 仍在库但取不到正文：{fetch_fail}")
        log(f"可用 {len(BOOKS) - len(bad)}/{len(BOOKS)}")
        return 0 if not bad else 1

    # ---- 拉取正文 ----
    if not a.lang and not a.book_id:
        ap.error("需指定 --lang / --book-id（或用 --library/--search 从书库挑，--list-books 看快捷清单）")

    jobs: list[tuple[str, str, Path]] = []
    if a.book_id:
        name = a.out_name or f"book_{a.book_id}.txt"
        jobs.append((a.book_id, name, a.out_dir / name))
    for code in a.lang:
        if code not in BOOKS:
            log(f"⚠️ 未知语种码 {code}，跳过（用 --list-books 查看，或 --search 从书库挑）")
            continue
        _ln, bid, cn, title = BOOKS[code]
        name = a.out_name if (a.out_name and len(a.lang) == 1) else f"{cn}-{title}.txt"
        jobs.append((bid, name, a.out_dir / name))

    log(f"接口 {a.base} | 输出 {a.out_dir} | 批大小 {a.batch} | "
        f"范围 {'全书' if a.max_chapters <= 0 else str(a.max_chapters) + ' 章'} | 任务 {len(jobs)} 本")
    results = []
    for bid, name, path in jobs:
        log(f"── {name} (bookId={bid}) ──")
        try:
            results.append(fetch_book(session, token, a.base, bid, path,
                                      a.max_chapters, a.batch, a.timeout, a.save_every))
        except Exception as e:
            log(f"  ❌ 失败：{type(e).__name__}: {e}")

    log("=" * 72)
    for r in results:
        flag = "✅" if r.get("ok") else "❌"
        log(f"{flag} {r['chapters']:>5} 章  {r['chars']:>10,} 字符  {r['path']}")
    failed = [r for r in results if not r.get("ok")]
    if failed:
        log(f"⚠️ {len(failed)} 个任务未产出语料。若 bookId 来自内置清单，可能已下架——"
            f"改用 --search 从实时书库挑，或跑 --probe-books 核对清单")
    log("提示：新语种建议接着跑 --verify 反推切章正则")
    return 0 if results and not failed else 1


if __name__ == "__main__":
    sys.exit(main())
