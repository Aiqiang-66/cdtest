---
name: haiyue-book-text-fetch
description: 从海阅自动化（AdAssetServer）接口按语种拉取书籍章节正文并落盘为多语种文本语料。书籍数据来自 ai_center(TiDB) 的 ObjectBook/ObjectChapter/ObjectCatChapter，经接口对外；支持实时书库枚举（约 4.4 万本）与按语种/关键词挑书。覆盖 Token 获取与时效、书库筛选、GetBookChapter 分批拉取（小批次+重试+中途落盘）、章节标记约定与切章正则推导、产物完整性校验。USE FOR 拉取书籍正文、拉取语料、拉取小说章节、补充语料、多语种语料准备、听书测试物料准备、韩语/日语/小语种书籍数据、查书库有哪些书、按语种挑书、GetBookChapter、token 过期重取。
---

# 海阅书籍正文拉取（语料获取）

从海阅自动化接口把整本书的章节正文拉下来，按统一约定落盘成文本语料，供听书/TTS 测试、多语种比对、文本分析等场景使用。

> **书籍数据来自数据库**（`ai_center` 的 `ObjectBook`/`ObjectChapter`/`ObjectCatChapter`），详见「数据来源」。
> 书库可实时枚举（约 4.4 万本），**优先用 `--library`/`--search` 挑书**，不要只依赖内置快照清单。

> 只做**文本获取**。拿到文本后的 TTS 合成与音频测试见 `docs/听书测试物料/SKILL.md`（技能 `tts-audio-test`）；
> 素材/任务下发见 `aimixedclip-dispatch`；画面比对见 `video-frame-compare`。

## 触发场景 → 用什么

| 用户诉求 | 动作 |
|---|---|
| 「书库里有哪些书」「某语种有哪些书可选」 | `--library` + `--stats`，再 `--language N` 列候选 |
| 「找一本讲 XX 的日语书」 | `--search <关键词> --language 9` |
| 「拉取韩语/日语书籍数据」「补充某语种语料」 | 先 `--language` 挑书，再 `--book-id` 拉；常用书可直接 `--lang kr` |
| 「拉某本书，bookId 是 xxx」 | `--book-id <id>` + `--out-name` |
| 「内置清单里的书拉不到了」 | `--probe-books` 核对是否已下架，再走 `--search` 换书 |
| 「token 过期了 / 401」 | 见「Token 获取与时效」 |
| 「拉下来的文本怎么切章」 | 见「产物约定与切章正则」 |
| 「为什么中文拉不到」 | 书库里标准编号中文为 0 本；**已决定暂不补中文**，见「数据来源」 |

---

## 快速开始

```powershell
$S = "$env:USERPROFILE\.codex\skills\haiyue-book-text-fetch\scripts"

# 1) 先刷新 token（约 10 小时有效，见下节）
& "D:\python\python.exe" $S\get_token.py

# ── A. 从实时书库挑书（推荐：书库会变，内置清单可能过期）────────────
# 拉取/刷新全量书库（约 4.4 万本，2~3s，缓存 24h 到 %TEMP%）
& "D:\python\python.exe" $S\fetch_book_text.py --library

# 看书库语种分布（走缓存，判断某语种有多少可选）
& "D:\python\python.exe" $S\fetch_book_text.py --stats

# 列出某语种候选书（这里是日语，共 303 本）
& "D:\python\python.exe" $S\fetch_book_text.py --language 9 --limit 30

# 关键词筛选（可多个 = AND），并导出完整候选到 JSON 便于批量挑选
& "D:\python\python.exe" $S\fetch_book_text.py --search Alpha --language 3 --search-json D:\tmp\en_alpha.json

# 挑好后拉取（bookId 从上面结果里取）
& "D:\python\python.exe" $S\fetch_book_text.py --book-id 19244419 --out-name "日语-XXX.txt"

# ── B. 快捷方式：直接拉内置清单里的常用书 ────────────────────────
& "D:\python\python.exe" $S\fetch_book_text.py --lang kr                 # 单语种整本
& "D:\python\python.exe" $S\fetch_book_text.py --lang kr --lang jp       # 多语种
& "D:\python\python.exe" $S\fetch_book_text.py --lang jp --max-chapters 40  # 只取前 40 章

# ── C. 核对与校验 ────────────────────────────────────────────
& "D:\python\python.exe" $S\fetch_book_text.py --list-books    # 内置快捷清单（离线，标注为快照）
& "D:\python\python.exe" $S\fetch_book_text.py --probe-books   # 对照实时书库 + 实拉，校验清单是否失效
& "D:\python\python.exe" $S\fetch_book_text.py --verify "D:\python\dmx\cdtest\docs\听书测试物料\txt文本\日语-CEOの彼の罠に落ちた.txt"
```

默认输出目录：`D:\python\dmx\cdtest\docs\听书测试物料\txt文本`
默认文件名：`<中文语种名>-<书名>.txt`（与既有 `俄语-Молниеносный брак....txt` 约定一致）

> ⚠️ **优先用 A 路线（书库驱动），B 路线只是常用书快捷方式。**
> 内置清单是抓包快照，书会被下架——实测 `hi`/`pl` 的 bookId 已不在书库中。

---

## 数据来源（务必知悉）

书籍数据**来自数据库**，不是文件或配置：

```
ai_center 库 (TiDB, tidb-in.changdu.ltd:4000) —— 对象/章节模块
├── ObjectBook        书籍主表         Id / BookId / BookName / BookCode / ToLanguage / FromLanguage
├── ObjectChapter     章节表           BookId / ObjectBookId / ChapterId / ChapterName / ChapterContent
└── ObjectCatChapter  章节多语言内容    ChapterConetnt(中) / E(英) / P(葡) / PE(西) / Wk(俄) / Machine / Proofread / Self
        ↓  adassetserver 对外暴露
GetTgtCodeInfo  -> 书籍元数据（书库枚举）
GetBookChapter  -> 章节正文
```

**推论与注意事项：**

| 事项 | 说明 |
|---|---|
| 书库可实时枚举 | `--library` 走 `GetTgtCodeInfo {"tgtType":1}`，一次返回全量约 **44,033 本**（2~3s） |
| `keyword` 参数无效 | 实测传任意关键词都返回全量 → **只能客户端过滤**（脚本已如此实现） |
| 书会下架 | bookId 不在书库里时 `GetBookChapter` 返回 **空 `data`（code 仍是 200）**，与"到书末"现象相同 → 必须用书库交叉判断 |
| 中文很少，但**不是 0** | `language=1`（简体中文）为 **0 本**；中文书以**非标准编号 `19`/`20`** 存在：共 **4 本**，其中**仅 2 本能取到正文**（`22104449491` 简 / `22104449492` 繁，同一本书两版） |
| **中文语料：已决定暂不补充** | 2026-09-23 决定。本链路给不出成规模中文语料（仅 2 本可取），**不再作为待办**。日后要启用需另找中文源，或退用繁体 `language=2`（4,962 本），并改用 CER（字级）判定 |
| 编号 19/20 不在标准映射内 | `ELEVENLABS_LANG_MAP` 无 19/20；实测为中文书。脚本 `LANG_NAMES` 已按实测标注 |
| 文档口径待核 | `docs\雷霆数据库\XR3书籍数据来源流程.md` 记 `ObjectBook` 22 行（2026-08-21），与接口返回的 44,033 本不一致，可能是统计范围不同 |

---

## 核心接口

```
POST https://adassetserver-cn-new-test1.changdu.ltd/api/AutoCreation/Task/GetBookChapter
Header: Authorization: Bearer <token>
        Content-Type: application/json
        Referer: https://sc-test.changdu.ltd/
Body:   {"bookId":"410419","from":1,"to":5}      # 区间（推荐）
        或 {"bookId":"410419","top":3}            # 取前 N 章
响应:   {"data":[{"i":"1","chapterName":"第1章…","chapterContent":"…"}],
         "code":200,"isSuccess":true,"message":"操作成功"}

POST https://adassetserver-cn-new-test1.changdu.ltd/api/Common/GetTgtCodeInfo
Body:   {"tgtType":1}                            # 全量书库（约 4.4 万本）
响应:   {"data":[{"id":"410419","code":"U9","label":"[海阅]JP-U9/410419/…",
                  "name":"CEOの彼の罠に落ちた","language":9,"tgtType":1,…}]}
```

- `data` 为空数组 = **已到书末**，或 **bookId 不存在**（两者现象相同，需用书库区分）。
- 单章正文 1,000~5,000 字符；整本 300~900 章。
- 环境与更多接口见 `references/interface-reference.md`。

---

## 内置快捷清单（17 语种，快照）

> 这是**抓包记录的快照**，不是实时书库。全部于 2026-09-23 在 test1 实拉通过，
> 但**书可能被下架**——维护时用 `--probe-books` 对照实时书库复验。
> 需要清单以外的书，一律走 `--search` / `--library`。

`language` 为请求体里的数字编号（与 `ELEVENLABS_LANG_MAP` 一致）；`lang` 为命令/文件名用的语种码。

| lang | language | bookId | 书名 |
|---|:--:|---|---|
| ft | 2 | 99965466298 | 甜妻在上：老公，慢一點（繁体中文） |
| en | 3 | 56385322 | My Alpha, My Enemy |
| sp | 4 | 3467375 | Acepto ser tu Mate |
| pt | 5 | 1155409 | NÃO SIRVO PARA REINAR |
| fr | 6 | 6148410 | La femme du prince |
| ru | 7 | 6858418 | ЕВА |
| it | 8 | 32304413 | Il genio dimenticato: Rinascita dalle rovine |
| jp | 9 | 410419 | CEOの彼の罠に落ちた |
| ar | 10 | 28898415 | عندما يأتي: الحب متأخرا |
| id | 11 | 10030414 | Janda Lugu |
| th | 12 | 5988433 | บัวริมทาง |
| vi | 13 | 74178435 | Lệ tổng, chồng cũ của phu nhân lại tới… |
| kr | 14 | 39900436 | 나의 가짜 아내 |
| tl | 15 | 70467445 | Muling pagsilang ang masilaw na babae |
| de | 16 | 19873412 | Narben einer zerbrochenen Bindung |
| my | 21 | 116465495 | Kahwin Kilat Dengan Ayah Kawan Baikku |
| tr | 22 | 86180497 | Eski Kocanın Pişmanlığı |

> ⚠️ **接口记录里还有 3 条当前无效**（`hi/66589447`、`pl/125996501`、`pl/66474501`，均来自 09-16 早期批次）——
> 2026-09-23 在 test1 探活返回**空 `data`**，可能是其它环境的书或已下架，**未纳入清单**。
> 扩充/更新清单后务必跑 `--probe-books` 复验；不要直接把记录里的 bookId 当成可用。

> 已实测全书拉完：**韩语 850 章 / 1.70M 字符 / 3.95MB**，**日语 322 章 / 0.56M 字符 / 1.58MB**（2026-09-23）。
> 清单来源：`docs\雷霆素材接口\海阅自动化\全语种接口记录-*.jsonl`，换书重新提取的方法见 references。

---

## Token 获取与时效 ★

**Token 有效期约 10 小时，过期必须重取 —— 这是本流程最常见的失败点。**

| 方式 | 说明 |
|---|---|
| 自动获取（推荐） | `scripts/get_token.py`：用 Playwright 登录 `sc-test.changdu.ltd` 切换到目标环境，从请求头抓 `Authorization: Bearer`，写入 token 文件 |
| 复用现成 | 工作区根目录 `temp_token_prod.txt` / `temp_token_latest.txt` 等（**注意看修改时间，多为已过期**） |
| 指定传入 | `--token-file <path>` 或 `--token <jwt>` |

Token 文件都被 `.gitignore` 覆盖；**凭据一律不入库、不写进脚本**。

判断是否过期（脚本会自动解析 `exp` 并给出剩余小时数）：
```powershell
& "D:\python\python.exe" $S\fetch_book_text.py --check-token --token-file D:\python\dmx\cdtest\temp_token_prod.txt
```

---

## 拉取策略与实测经验（踩过的坑）

| # | 坑 | 现象 | 正确做法 |
|---|---|---|---|
| 1 | **大区间请求超时** | `from=1,to=500` 直接挂住；单章接口耗时可 13~19s | **每批 5 章**（`--batch 5`），实测每批 1~3s |
| 2 | **长时间任务中断丢数据** | 拉几百章要数分钟，中断即白跑 | 默认**每 10 批中途落盘**（`--save-every`） |
| 3 | **Token 过期** | 拉到一半 401 / code≠200 | 先 `--check-token`；大批量前确认剩余 >1h |
| 4 | **误把"没数据"当失败** | 书末返回空 `data` | 空 `data` = 正常书末，脚本自动停止并落盘 |
| 5 | **日文章名混用两种写法** | 下游按单一正则切章会**静默漏章** | 见下节，日语必须用兼容正则 |
| 6 | **下载的正文含 `\r\n`** | 行尾污染、空行堆积 | 脚本统一 `\r\n→\n` 并压缩连续空行 |
| 7 | **bookId 已下架** | 返回 `code=200` + **空 `data`**，与"到书末"现象**完全相同**，肉眼分不出 | 先 `--library` 拉书库再交叉判断：`--probe-books` 会区分「不在库」与「在库但取不到」 |
| 8 | **`GetTgtCodeInfo` 的 `keyword` 不生效** | 传任何关键词都返回全量 4.4 万本，以为筛选了其实没有 | 只能**客户端过滤**（`--search` 已如此实现）；不要指望接口侧筛选 |
| 9 | **内置清单会过期** | 抓包快照，书下架后静默失效（实测 `hi`/`pl` 已不在库） | 优先用 `--search` 从实时书库挑；定期 `--probe-books` 体检 |

---

## 产物约定与切章正则 ★

**统一格式**（与既有 `XR3 - XX.txt` 语料一致）：

```
=== <chapterName> ===
<空行>
<chapterContent 正文>
<空行>
=== <下一章 chapterName> ===
```

章标题行用 `=== ` + 接口返回的 `chapterName` + ` ===`，正文即 `chapterContent`。
**下游按行首 `===` 切章**，正文中不含该前缀。

### 各语种切章正则（已实测）

| 语种 | 章名样式 | 切章正则 | 命中率 |
|---|---|---|---|
| 韩语 | `제N화 …` | `^===\s*제\s*\d+\s*화` | 850/850 ✅ |
| 日语 | `第N章…`（246）+ `チャプター N …`（76） | `^===\s*(第\s*\d+\s*章\|チャプター\s*\d+)` | 322/322 ✅ |
| 日语（错误写法） | — | `^===\s*第\s*\d+\s*章` | **246/322 ❌ 漏 76 章** |

> ⚠️ **日语必须用兼容正则**。只匹配 `第N章` 会漏掉 76 章且**不报错**，属于静默数据缺失。
> 其它语种未逐一实测，**不要凭猜写正则**——先用 `--verify` 让脚本从实际标记反推候选正则。

### 反推正则

```powershell
& "D:\python\python.exe" $S\fetch_book_text.py --verify <txt路径>
```
输出：章数、样式分布、每类样式的**建议正则**（数字已替换为 `\d+`）、`U+FFFD` 乱码数、BOM、体积、首末标记。
**新语种一律先跑 --verify 再写进下游脚本。**

---

## 校验清单（语料交付前必做）

| 项 | 期望 |
|---|---|
| 章标记数 == 章数 | 一致 |
| 切章正则命中率 | **100%**（不是"大部分"） |
| U+FFFD 乱码字符 | **0** |
| 编码 | UTF-8，无 BOM |
| 章节连续性 | `i` 从 1 递增无缺口（脚本已按序累加） |
| 与源文抽查 | 随机 2~3 章首尾与接口返回一致 |

---

## 环境与端点

| 环境 | 基址 |
|---|---|
| **test1（默认，已实测）** | `https://adassetserver-cn-new-test1.changdu.ltd` |
| dev | `https://adassetserver-cn-new-dev.changdu.ltd` |
| test5 | `https://adassetserver-cn-new-test5.changdu.ltd` |
| 生产 | `https://adassetserver-cd-2.changdu.vip` |
| UI（取 token 用） | `https://sc-test.changdu.ltd`（Keycloak 工号登录） |

| 项 | 值 |
|---|---|
| Python | 系统 `D:\python\python.exe`（3.13.7，已装 requests / playwright） |
| ⚠️ 不要用 `.venv` | 仓库内 `.venv` 是空壳（仅 pip），必然 `ModuleNotFoundError` |
| 请求超时 | 单批 `--timeout 240`，失败重试 3 次（指数退避） |

---

## 安全与约束

- **禁止删除线上/生产环境数据**；本流程只做**读**（`GetBookChapter` 是查询接口），不写库、不下发任务。
- 拉取生产环境（`adassetserver-cd-2`）前先向用户确认。
- 凭据不入库：token 只落本地文件，脚本内不得硬编码。
- 语料体积较大（单本 1.5~4MB），拉取前确认目标目录空间与是否需要快照。
- **改动已有语料目录前**，按仓库 AGENTS.md 先执行 `scripts\create_iteration_backup.ps1` 打快照。
