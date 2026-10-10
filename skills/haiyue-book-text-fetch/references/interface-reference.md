# 海阅书籍正文接口参考

来源：`docs\雷霆素材接口\海阅自动化\全语种接口记录-*.jsonl` / `*.md`（Playwright 抓包 + 直连实测）
+ `docs\雷霆数据库\XR3书籍数据来源流程.md`（数据源）
实测日期：2026-09-18 ~ 2026-09-23

## 0. 数据源：`ai_center` 数据库（TiDB）

书籍数据**存在数据库里**，接口只是对外代理：

```
ai_center  (TiDB, tidb-in.changdu.ltd:4000) —— 对象/章节模块
├── ObjectBook        书籍主表        Id / BookId / BookName / BookCode / SwBookId / ToLanguage / FromLanguage
├── ObjectChapter     章节表          Id / BookId / ObjectBookId / ChapterId / ChapterName / ChapterContent
└── ObjectCatChapter  章节多语言内容   ObjectChapterId /
                                      ChapterConetnt(中) / EChapterContent(英) / PChapterContent(葡) /
                                      PEChapterContent(西) / WkChapterContent(俄) /
                                      MachineChapterContent(机翻) / ProofreadChapterContent(校对) / SelfChapterContent(自译)
        ↓  adassetserver 对外
GetTgtCodeInfo  -> 书籍元数据（书库枚举）
GetBookChapter  -> 章节正文
```

| 项 | 观察 |
|---|---|
| `GetTgtCodeInfo {"tgtType":1}` | 返回 **44,033 本**（一次全量，2~3s） |
| `GetTgtCodeInfo {"tgtType":0}` | 返回 **197,835 条**（含非书籍对象） |
| `keyword` 参数 | **不生效**——传任意关键词都返回全量，必须客户端过滤 |
| 文档与实测差异 | `XR3书籍数据来源流程.md` 记 `ObjectBook` 22 行（2026-08-21），与 44,033 不一致；可能统计范围不同，**待业务侧确认** |

### 书库语种分布（2026-09-23 实测）

| language | 语种 | 本数 |
|:--:|---|---:|
| 3 | 英语 | 12,567 |
| 4 | 西语 | 6,340 |
| 5 | 葡语 | 5,495 |
| 6 | 法语 | 5,055 |
| 2 | 繁体中文 | 4,962 |
| 11 | 印尼语 | 3,808 |
| 12 | 泰语 | 2,992 |
| 7 | 俄语 | 1,210 |
| 14 | 韩语 | 393 |
| 9 | 日语 | 303 |
| 13 | 越南语 | 260 |
| 16 | 德语 | 255 |
| 15 | 菲律宾语 | 150 |
| 10 | 阿拉伯语 | 82 |
| 22 | 土耳其语 | 64 |
| 21 | 马来语 | 53 |
| 8 | 意大利语 | 39 |
| **19** | **中文(简体)** | **1** |
| **20** | **中文(繁/简)** | **3** |
| 23 | 波兰语 | 1 |
| **1** | **中文（标准编号）** | **0** |

> ⚠️ **中文不要看 `language=1`**——标准映射里 1=中文，但书库中 `language=1` 为 **0 本**。
> 中文书实际挂在**非标准编号 19/20** 下，共 4 本；实测仅 2 本能取到正文：

| bookId | language | 文字 | 拉取 | 内容 |
|---|---|---|---|---|
| 22104449491 | 19 | 简体 | ✅ 2,299 字 | 《被渣男背叛后，他的黑手党哥哥把我宠上天》 |
| 22104449492 | 20 | 繁体 | ✅ 2,299 字 | 同书繁体版 |
| 100000481323 | 20 | 简体 | ❌ 在库但无章节 | 《离婚后，前夫竟是大佬！》 |
| 8714449492 | 20 | 繁体 | ❌ 在库但无章节 | 《渣男和我領假證，我轉身嫁他死對頭》 |

> 这 4 本的 `label` 缺少语种码段（形如 `[海阅]-P281/…`，其它书是 `[海阅]JP-U9/…`），
> 推测是**来源/编号异常的遗留数据**。
>
> ⏸ **中文语料：已决定暂不补充（2026-09-23）。** 本链路给不出成规模中文语料，**不再作为待办**。
> 日后若要启用：另找中文书源，或退用繁体 `language=2`（4,962 本），并改用 **CER（字级）** 判定。

## 1. 环境与基址

| 环境 | 基址 |
|---|---|
| **test1（默认，已实测）** | `https://adassetserver-cn-new-test1.changdu.ltd` |
| dev | `https://adassetserver-cn-new-dev.changdu.ltd` |
| test5 | `https://adassetserver-cn-new-test5.changdu.ltd` |
| 生产 | `https://adassetserver-cd-2.changdu.vip` |
| UI（取 token 用） | `https://sc-test.changdu.ltd` |

UI 路由：自动化创作 `/automation/create-make-material`、任务列表 `/task/list`、混剪制作 `/automation/automated-novel-mixed-cut/create`

## 1.5 GetTgtCodeInfo（书库枚举）

```
POST {BASE}/api/Common/GetTgtCodeInfo
Header: Authorization: Bearer <jwt>
Body:   {"tgtType":1}          # 1=书籍；0=全部对象
响应:   {"data":[{"id":"410419","code":"U9","label":"[海阅]JP-U9/410419/CEOの彼の罠に落ちた",
                  "name":"CEOの彼の罠に落ちた","isDrp":false,"language":9,
                  "tgtType":1,"storyType":0,"assetCategoryName":"现言"}],
         "code":200,"isSuccess":true,"message":"操作成功"}
```

- `id` 即 `GetBookChapter` 的 `bookId`；`language` 为数字语种编号。
- 也用作 **token 连通性校验**（本技能 `get_token.py --verify` 用它）。
- ⚠️ 不要用 `keyword` 过滤（不生效）。

## 2. GetBookChapter（本技能主接口）

```
POST {BASE}/api/AutoCreation/Task/GetBookChapter
Header:
    Authorization: Bearer <jwt>
    Content-Type: application/json
    Referer: https://sc-test.changdu.ltd/
Body（二选一）:
    {"bookId":"410419","from":1,"to":5}      # 区间，左闭右闭
    {"bookId":"410419","top":3}              # 前 N 章；top:1 即第 1 章
```

响应：

```json
{
  "data": [
    {"i": "1",
     "chapterName": "第1章あなたは私を救わなければならない",
     "chapterContent": "D市の5つ星のペニンシュラホテルにて…"}
  ],
  "code": 200,
  "isSuccess": true,
  "message": "操作成功"
}
```

约定与边界：

| 项 | 观察值 |
|---|---|
| `i` | 章节序号，字符串型，从 `"1"` 递增 |
| `chapterContent` | 单章 1,000~5,000 字符；`\r\n` 换行 |
| 书末判定 | `data` 为空数组（**不是报错**） |
| 单章耗时 | 0.4s ~ 19s 波动大（`top:1` 实测 kr 19.4s / jp 13.3s / th 0.4s） |
| **大区间** | `to=500` 会超时挂住 → **必须分批，建议每批 5 章** |

## 3. Token

- 形态：标准 JWT，`exp - nbf = 36000s`（**约 10 小时**）。
- 获取：Keycloak 工号登录 `sc-test.changdu.ltd` 后，从任意 `adassetserver-*` 请求的
  `Authorization: Bearer` 头抓取（见 `scripts/get_token.py`）。
- 解析剩余时效：
  ```python
  import base64, json
  p = token.split(".")[1]; p += "=" * (-len(p) % 4)
  exp = json.loads(base64.urlsafe_b64decode(p))["exp"]
  ```
- 已知历史 token 文件（工作区根目录，**多已过期，用前查修改时间**）：
  `temp_token_prod.txt`、`temp_token_latest.txt`、`_token_test1.txt`、`temp_token_test1_fresh.txt` 等。

## 4. 内置书籍清单（19 语种）

`language` 为 `Task/Add` 请求体里的数字编号，与 `ELEVENLABS_LANG_MAP` 一致
（`1=zh, 2=zh-Hant, 3=en, 4=es, 5=pt, 6=fr, 7=ru, 8=it, 9=ja, 10=ar, 11=id, 12=th, 13=vi, 14=ko, 15=fil, 16=de, 17=hi, 21=my, 22=tr, 23=pl`）。

| lang | language | bookId | tgtCode | 书名 |
|---|:--:|---|---|---|
| ft | 2 | 99965466298 | FT-CPF3000 | 甜妻在上：老公，慢一點 |
| en | 3 | 56385322 | EN-Y4103 | My Alpha, My Enemy |
| sp | 4 | 3467375 | SP-Y20231 | Acepto ser tu Mate |
| pt | 5 | 1155409 | PT-Y16917 | NÃO SIRVO PARA REINAR |
| fr | 6 | 6148410 | FR-Y19547 | La femme du prince |
| ru | 7 | 6858418 | RU-Y23240 | ЕВА |
| it | 8 | 32304413 | IT-ZJ103 | Il genio dimenticato: Rinascita dalle rovine |
| jp | 9 | 410419 | JP-U9 | CEOの彼の罠に落ちた |
| ar | 10 | 28898415 | AR-R16 | عندما يأتي: الحب متأخرا |
| id | 11 | 10030414 | ID-Y2582 | Janda Lugu |
| th | 12 | 5988433 | TH-Y14165 | บัวริมทาง |
| vi | 13 | 74178435 | VI-A265 | Lệ tổng, chồng cũ của phu nhân lại tới… |
| kr | 14 | 39900436 | KR-R3 | 나의 가짜 아내 |
| tl | 15 | 70467445 | TL-A8 | Muling pagsilang ang masilaw na babae |
| de | 16 | 19873412 | DE-J40 | Narben einer zerbrochenen Bindung |
| hi | 17 | 66589447 | — | （未取到书名） |
| my | 21 | 116465495 | MY-Z134 | Kahwin Kilat Dengan Ayah Kawan Baikku |
| tr | 22 | 86180497 | TR-P127 | Eski Kocanın Pişmanlığı |
| pl | 23 | 125996501 | PL-Z512 | Poślubiona szefowi: Ukryty miliarder |

> 另有 `pl: 66474501`、`hi: 66589447` 出现在 `GetBookChapter` 汇总但无对应 `Task/Add` 记录，未纳入内置清单。

### 实测体量（2026-09-23 全书拉取）

| 语种 | bookId | 章数 | 字符 | 体积 |
|---|---|---|---|---|
| 韩语 kr | 39900436 | 850 | 1,704,724 | 3.95 MB |
| 日语 jp | 410419 | 322 | 564,651 | 1.58 MB |

## 5. 如何扩充/更新书籍清单

清单从接口记录里提取（不要凭记忆手写）：

```python
import json, re
from pathlib import Path
D = Path(r"D:\python\dmx\cdtest\docs\雷霆素材接口\海阅自动化")
books, chap = {}, {}
for p in sorted(D.glob("*.jsonl")):
    if p.stat().st_size > 20_000_000:      # 跳过 200MB 大包
        continue
    for line in p.open(encoding="utf-8"):
        if "Task/Add" not in line and "GetBookChapter" not in line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        nm, rq = o.get("name", ""), o.get("request") or {}
        if nm.startswith("Task/Add") and rq.get("tgtId"):
            books[str(rq["tgtId"])] = (rq.get("language"), rq.get("tgtCode"), rq.get("tgtName"))
        elif nm.startswith("GetBookChapter") and rq.get("bookId"):
            chap[str(rq["bookId"])] = nm.split("/")[1]
for bid, (ln, code, name) in sorted(books.items()):
    print(chap.get(bid, "?"), bid, ln, (name or "").replace("[海阅]", ""))
```

## 6. 相关接口（非本技能必需，按需参考）

| 接口 | 说明 |
|---|---|
| `POST /api/Common/GetTgtCodeInfo` | `{"tgtType":1}` 返回书籍代号下拉；**也用作 token 连通性校验** |
| `POST /api/AutoCreation/Task/Add` | 下发任务；请求体含 `chapterInfo`（即章节正文）、`language`、`tgtId` |
| `POST /api/AutoCreation/Task/GetSelectItems` | 渠道/类型下拉枚举 |
| `POST /api/AutoCreationMixedCut/*` | 自动化小说混剪（Extract/Create/GetTask/审核），见同目录 `自动化小说混剪接口.md` |

## 7. 实测踩坑记录

| # | 现象 | 原因 | 处置 |
|---|---|---|---|
| 1 | `to=500` 请求挂住 120s+ 超时 | 大区间在服务端逐章取，耗时为线性叠加 | 每批 5 章 |
| 2 | 拉到一半失败，前功尽弃 | 无中途持久化 | 每 10 批落盘一次 |
| 3 | 401 / `code≠200` | token 10 小时过期 | 先 `--check-token` |
| 4 | 以为"没数据"是异常 | 书末返回空 `data` | 空 `data` 视为正常结束 |
| 5 | 日语句料按 `第N章` 切章少了 76 章 | 章名混用 `第N章` 与 `チャプター N` | 用兼容正则，见 SKILL.md |
| 6 | 控制台中文乱码 | Windows 控制台编码 | 先设 `PYTHONIOENCODING=utf-8` 并 `[Console]::OutputEncoding = [Text.Encoding]::UTF8` |
