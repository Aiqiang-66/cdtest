# TTS 听书测试 —— 新人熟悉计划（一周）

> **适用对象**：接手「听书 TTS（Higgs v3）测试」的新同事
> **计划周期**：7 天（约 1 个工作周 + 收尾日；只有 5 个工作日时见 §11 压缩方案）
> **编制日期**：2026-10-10　**依据版本**：`SKILL.md` v1.1.7（2026-09-24）
> **毕业标准**：能**独立**完成「1 个语种 × 接口用例 + 稳定性跑批 + 分析 + 报告 + git 入库」，不留悬空项

---

## 0. 怎么用这份计划

1. **先读 §1 毕业标准**——它是这一周的靶子，其余内容都是路径。
2. **每天开工前跑 §5 的例行三件事**（探活 / 快照 / 看日志），收工前交当天的「产出物」。
3. 每天与导师有 **30 分钟复盘**（§9），只讨论：今天卡在哪、口径有没有理解偏、产出物是否达标。
4. 文档里 **`MUST`** = 必须动手做一遍；**`READ`** = 读懂即可；**`REF`** = 需要时再查。

---

## 1. 毕业标准（Rubric，逐项打勾才算通过）

### 1.1 必须能独立回答的 10 个问题

| # | 问题 | 合格答案要点 |
|---|---|---|
| 1 | 这条链路怎么走？ | `POST /Video/CreateUniversalTransparent`（`taskType=74`）→ 轮询 `/Task/GetAllTaskStatus` → 产物 MP3 落 COS + metadata/SRT |
| 2 | 任务状态码含义？ | **2=成功**（带 audio_url/metadata_url）· **3=失败** · **67=处理中** |
| 3 | 判定"漏文案"用哪个口径？ | **文本口径（M1）**：下发 `read_content` ↔ 返回 metadata 正文段拼接；**ASR 删除率不能当漏词率** |
| 4 | 为什么有 M0 前置门禁？ | 语料丢了段落换行 → 服务端当成单段落 → `paraIndex≡0` → 切句退化（超长段/不可能语速/内容缺失） |
| 5 | 三种"看着像丢了"的缺陷怎么区分？ | **卡死 67**（无产物，404）／**产物竞态**（状态 2，首轮 440B XML，重下成功）／**静默空洞**（有音频，81.64s 无声） |
| 6 | 削波怎么判？ | 峰值 ≤0.999；≥1.0 样本数；日语长期越界（max≈1.22）、韩语正常 |
| 7 | 稳定性跑批要看哪些数？ | 成功率、端到端 P50/P95、吞吐（**区分加载期 vs 含收尾**）、分时段趋势、卡死任务数 |
| 8 | 报告最少要写什么？ | 见 §8（13 项交付规范），其中**数据范围声明**与**产物与分发结论**最易漏 |
| 9 | 密钥怎么处理？ | **只走环境变量 `TTS_SECRET_KEY`**，脚本内不含密钥；写入文件/仓库 = 红线 |
| 10 | 代码怎么入库？ | 只用 `scripts/sync_tingju_skill_to_git.ps1`（白名单 + 守卫 + 隔离索引），**禁用 `git add -A`** |

### 1.2 毕业交付（第 7 天）

- [ ] 一份**完整测试报告**（含 M0~M5 结论、缺陷分级、证据路径、数据范围声明）
- [ ] 一次**稳定性跑批**的完整留证（`src/meta/srt/audio/tasks.jsonl/summary.json/analysis/`）
- [ ] 一次**接口用例**执行与判定（19 条，含 FAIL 用例的证据）
- [ ] 一次 **git 入库**（`-DryRun` 通过后 `-Push`，报告可在远端看到）
- [ ] 一页**遗留问题与建议**（哪些缺陷已报、哪些待人工听测、哪些未覆盖）

---

## 2. 开工前必须确认的 8 件事（Day 1 上午一次性搞定）

| # | 事项 | 怎么确认 |
|---|---|---|
| 1 | 仓库与分支权限 | `git -C D:\python\dmx\cdtest rev-parse --abbrev-ref HEAD` → `codex/asr-leakage-fallback`；能推送（有 GitHub 凭据） |
| 2 | 测试环境可达 | `python docs\听书测试物料\_probe_paragraph_once_0924.py --lang ja --unit 1` 能返回 `taskStatus=2` |
| 3 | **密钥获取方式** | 向负责人索取测试环境密钥；使用时 `$env:TTS_SECRET_KEY = '<key>'`（**不要写进任何文件**） |
| 4 | Python 依赖 | `requests` / `av`(PyAV) / `faster-whisper` / `torch`(CPU) 已装 |
| 5 | ffmpeg | `ffmpeg -version` 可用（本次为 6.0） |
| 6 | ASR 模型 | `tools\whisper_models\models--Systran--faster-whisper-large-v3\snapshots\large-v3` 存在（约 2.9 GB） |
| 7 | 磁盘余量 | 当前约 **28.9 GB**；一轮「30 分钟 × 10 并发」留证约 **0.4~0.5 GB/语种**（5000 字任务） |
| 8 | 线上数据红线 | **未经明确允许不得删除任何数据**（含测试产物）；删除前必须先问 |

---

## 3. 知识地图（先建立全局，再钻细节）

### 3.1 被测链路

```
read_content ──切句/分段──> 分段合成 ──编码──> MP3（落 COS）──> audio_url（时效签名）
                                          └──> metadata.json / SRT ──> metadata_url（时效签名）
```

- 接口：`POST {BASE}/Video/CreateUniversalTransparent`，`taskType=74`，`sign = base64(HMAC-SHA256(SECRET_KEY, 原始 body))`
- `BASE`：测试 `https://ai-main-none-dev.changdu.ltd`　生产 `https://ai-main-none.changdu.vip`
- 语种/音色：日语 `lang=9` / `Japanese_female`；韩语 `lang=14` / `Korean_female`（见 `语言参数`）

### 3.2 三个判定口径（**最容易搞混，必须记牢**）

| 口径 | 比对对象 | 用途 | 能/不能判定什么 |
|---|---|---|---|
| **文本口径** | 下发 `read_content` ↔ metadata 正文段 | **M1 漏文案（唯一口径）** | ✅ 能判定漏字；❌ 不能判定音频是否真的念了 |
| **ASR 口径** | metadata 文本 ↔ 语音转写 | M3 抽样听感 | 含识别误差，**不能**单独当漏词率 |
| **质量口径** | 音频波形 | M2 削波/响度/空洞 | 客观指标；仍需人工听测签字 |

### 3.3 文件地图（`docs\听书测试物料\`）

| 路径 | 内容 | 优先级 |
|---|---|---|
| `SKILL.md` | **唯一规范源**（v1.1.7：M0 前置 + 必测项 M1~M5 + Phase 1~9 + 工程规范 §1~§7） | MUST |
| `测试用例\文案格式_正常与异常_0924.md` | 19 条正/逆向用例定义与判据 | MUST |
| `测试用例\接口与MP3产物_补充测试场景.md` | Phase 9 产物层场景池（9 族 60+ 条） | READ |
| `接口\` | 后端/大模型/切句/音色参数 接口文档 | MUST |
| `mp3\` | 每次跑批一个批次目录（39 个批次留证） | REF |
| `测试报告\` | 18 份报告（历史 + 本轮） | MUST |
| `txt文本\` | 源语料（长篇公版书 + 多语种） | REF |
| 脚本（78 个可复用 / 36 个一次性） | 见 §4 Day 1 的"第一批要认识的 8 个脚本" | MUST |

### 3.4 术语表

`M0` 语料段落门禁 ｜ `M1` 文案一致性 ｜ `M2` 音频质量 ｜ `M3` 漏词/准确率 ｜ `M4` 切句 ｜ `M5` 字幕完整性
`paraIndex` 段落序号 ｜ `segment` 字幕段 ｜ `hole` 时间轴空洞 ｜ `COS` 腾讯对象存储 ｜ `RTF` 实时率（转写耗时/音频时长）

---

## 4. 一周日程

### Day 1（周一）环境与地图 —— 目标：能自己跑通一个任务并解释它

| 项 | 内容 |
|---|---|
| **READ** | `SKILL.md` 的「模块定位 / 系统架构 / 测试流程 / 环境与端点」；`接口\后端接口`、`接口\音色参数和语言id` |
| **MUST** | ① 完成 §2 的 8 项确认；② 跑 `_probe_paragraph_once_0924.py --lang ja --unit 1` 并解释输出（`distinct paraIndex` / 段长 / 最长段 / 是否出现 81.64s 段）；③ 在 `mp3\段落格式验证_0924\` 找到对应 metadata 与结果 JSON |
| **MUST** | 认识这 8 个脚本（每个 `--help` 一次）：`build_ja_ko_5000char_material.py`、`run_text_format_cases_0924.py`、`run_higgs_ja_ko_10concurrent_30min.py`、`analyze_ja_ko_perf_0924.py`、`audio_quality_ja_ko_0924.py`、`asr_accuracy_ja_ko_largev3_0924.py`、`gen_report_round2_summary_0924.py`、`scripts\sync_tingju_skill_to_git.ps1` |
| **产出** | ① 环境自检记录（8 项逐条打勾 + 命令与输出摘录）；② 一页"链路 + 状态码 + 三口径"手绘笔记 |
| **自检** | 能不看文档说出：2/3/67 含义、M0 门禁为什么存在、文本口径与 ASR 口径的区别 |

### Day 2（周二）必测项与口径 —— 目标：能独立判定 M1 / M5

| 项 | 内容 |
|---|---|
| **READ** | `SKILL.md`：⛔ 必测项表、Phase 2.5（文案一致性）、Phase 2.6（切句）、Phase 5.5（字幕完整性） |
| **MUST** | 对**历史批次**重算一次，证明结论可复现：`analyze_ja_ko_perf_0924.py --lang ja --run-dir docs\听书测试物料\mp3\Higgs_日语_稳定性10并发_30min_0924 --load-minutes 30`，逐字段解释 `perf / m1 / m5` |
| **MUST** | 对照 `测试报告\日韩_稳定性10并发_30min_20260924.md` 核对自己的重算结果是否一致（不一致要能解释为什么） |
| **产出** | ① 「M1/M5 判定口径」笔记（含：为什么 `SRT≠segments` 要被单独统计）；② 重算结果与报告数字的对照表 |
| **自检** | 能解释：为什么必须**先在 M0 通过**再谈 M1；为什么单段落语料会让 M5 的"无 paraIndex 缺口"判据失去意义 |

### Day 3（周三）接口与异常用例 —— 目标：能跑完 19 条并判读

| 项 | 内容 |
|---|---|
| **READ** | `测试用例\文案格式_正常与异常_0924.md`（19 条判据）；`SKILL.md` Phase 2；`测试用例\接口与MP3产物_补充测试场景.md` 的 P0 部分 |
| **MUST** | 跑日语全量：`python docs\听书测试物料\run_text_format_cases_0924.py --lang ja --workers 4 --out-suffix _d3`（约 5 分钟），再跑韩语 `--lang ko --out-suffix _d3ko` |
| **MUST** | 对每个 FAIL 写清：现象 → 证据（`results.json` 字段 + `meta\TC-FMT-*.json`）→ 影响 → 建议 |
| **产出** | 判定表（PASS/FAIL/ERROR/INFO）+ 缺陷条目草案（至少覆盖：参数校验缺失） |
| **自检** | 能说出：空文本/纯空白/`lang=999` 的实际行为与危害；`440 B` 与 `81.64s` 两个**缺陷签名**各代表什么 |

### Day 4（周四）性能与稳定性 —— 目标：能跑批、能看趋势、能识别卡死

| 项 | 内容 |
|---|---|
| **READ** | `SKILL.md` Phase 4（含"测试项按用户要求选择"矩阵与稳定性最低要求） |
| **MUST** | ① 准备批次目录（**新目录必须自带合规语料**）：<br>`$src="docs\听书测试物料\mp3\Higgs_日语_10并发30分钟_0924_r3\material"`<br>`$dst="docs\听书测试物料\mp3\<你的批次目录>\material"` → 复制并在 `progress`/`summary` 里可溯源<br>② 小跑热身：`run_higgs_ja_ko_10concurrent_30min.py --lang ja --workers 5 --minutes 5 --dir-name <批次>`<br>③ 正式：`--workers 10 --minutes 30`（或按需求 60/120 分钟）|
| **MUST** | 分析：`analyze_ja_ko_perf_0924.py --lang ja --run-dir <批次> --load-minutes 30`；若执行期间机器空闲，**不要在跑批同时做本地重分析**（会污染延迟测量） |
| **产出** | 稳定性小结：成功率 / P50·P95 / 吞吐（**加载期 vs 含收尾**）/ 分时段趋势 / 卡死任务清单（taskId） |
| **自检** | 能解释：为什么"含收尾"的吞吐会明显偏低；如何从 `tasks.jsonl` 找出卡在 67 的任务；成功率不达 99% 时第一件事查什么 |

### Day 5（周五）音质与 ASR —— 目标：能出客观音质结论并组织人工听测

| 项 | 内容 |
|---|---|
| **READ** | `SKILL.md` Phase 5 / 5.5 / Phase 3（含"非英语语种必须用 large-v3"的提醒） |
| **MUST** | ① `audio_quality_ja_ko_0924.py --lang ja --run-dir <批次> --refetch`（削波/响度/长空洞/非音频响应补齐），逐字段解释 `peak_max / files_peak_fail / rms_avg / gap_files`<br>② ASR 抽样：`asr_accuracy_ja_ko_largev3_0924.py --lang ja --run-dir <批次> --samples 2 --window 180 --out asr_d5` |
| **MUST** | 从批次 `analysis\audio_listen_checklist.md` 生成**人工听测抽样单**（≥5 条，含 taskId 与抽样理由），交导师安排听测人 |
| **产出** | ① M2 客观指标表 + 判定；② 抽样单；③ 一页"ASR 删除率 ≠ 漏词率"的解释（举一条实际数据） |
| **自检** | 能判断：峰值 1.02 与 1.22 分别意味着什么；`gap_files_with_text` 与普通静音的差别 |

### Day 6（周六/次一工作日）报告与缺陷 —— 目标：能按规范产出可交付报告

| 项 | 内容 |
|---|---|
| **READ** | `SKILL.md` 工程规范 §6 **报告交付规范（13 项）**；`测试报告\日韩_接口与稳定性_总报告_20260924.md` 作为范例 |
| **MUST** | 用生成器产出报告并**逐节核对 13 项**：`gen_report_round2_summary_0924.py` / `gen_report_stability_0924.py` / `gen_report_cases_0924.py` |
| **MUST** | 把缺陷写成标准条目：**现象 / 证据（可复现路径）/ 影响 / 分级 / 建议**；与历史报告冲突处必须显式说明 |
| **产出** | 一份完整报告草稿（含数据范围声明、产物与分发结论、附件索引） |
| **自检** | 报告是否写明：本次测了什么、跳过了什么及原因；结论是否只用本批次数据；是否给了复现命令 |

### Day 7（周日/次一工作日）独立跑一轮 + 入库 —— **毕业考核**

| 项 | 内容 |
|---|---|
| **MUST** | 独立完成（导师只答疑不代做）：**1 个语种**的 ① 接口用例 ② 稳定性 15~30 分钟 ③ 分析（性能+M1+M5、M2）④ 报告 ⑤ git 入库 |
| **MUST** | 入库流程：`powershell -NoProfile -File scripts\sync_tingju_skill_to_git.ps1 -DryRun` → 核对清单 → `-Push`（含脚本改动时用 `-WithScripts`） |
| **产出** | 一次可复现的完整交付 + 一页遗留问题与建议 |
| **验收** | 按 §1 逐项打勾；导师复核"证据能否从磁盘复现结论" |

---

## 5. 每日例行（15 分钟，养成习惯）

```powershell
Set-Location D:\python\dmx\cdtest

# ① 服务探活（用短文本，别拿长任务试水）
$env:TTS_SECRET_KEY = '<测试环境密钥>'      # 只存在于当前会话
python docs\听书测试物料\_probe_paragraph_once_0924.py --lang ja --unit 1

# ② 改任何文件前先快照（AGENTS.md 规则）
powershell -NoProfile -File scripts\create_iteration_backup.ps1 -Name <本次迭代名> <要改的路径...>

# ③ 跑批期间看进度**读文件**，不要依赖控制台
Get-Content docs\听书测试物料\mp3\<批次>\progress.log -Tail 5 -Encoding UTF8
(Get-Content docs\听书测试物料\mp3\<批次>\tasks.jsonl | Measure-Object).Count
```

> ⚠️ 后台运行 Python 时 stdout 是**块缓冲**，控制台可能长时间无输出——进度一律以 `progress.log` / `tasks.jsonl` 为准。

---

## 6. 必背口径卡片

| 项 | 判定线 | 备注 |
|---|---|---|
| **M0 语料门禁** | 每个单元**必须含换行**（多段落）；`distinct paraIndex > 1` | 单段落下发 = 不合格，不得开跑 |
| **M1 文案一致性** | 缺失字 = **0**（逐字符一致） | 唯一判漏口径；分母是下发字数 |
| **M2 音频质量** | 峰值 ≤0.999；无 >3s 且 metadata 有文本的长空洞 | 人工听测仍需签字 |
| **M3 漏词** | 文本口径 0；ASR 删除率仅参考 | 非英语语种必须 large-v3 |
| **M4 切句** | 无超长段（>200 字）；无不可能语速（>15 字/秒） | 段落语料下段长通常 ≤80 字 |
| **M5 字幕完整性** | 空字幕 0；`SRT 条目 ≠ segments` 0；无 paraIndex 缺口 | **每次必查**（含性能/稳定性跑批） |
| **稳定性** | 成功率 ≥99%；分时段无劣化趋势；无卡死任务 | 最低口径见 Phase 4（长时运行需 ≥2h） |
| **产物层（Phase 9）** | 成功后**立即**拉 `audio_url` 必须拿到 MP3 | 首轮失败要延迟重下验证是否竞态 |

---

## 7. 已知缺陷基线（**不要重复报告，但要每次回归**）

| # | 缺陷 | 级别 | 现状 |
|---|---|---|---|
| 1 | 参数校验缺失：空文本/纯空白/非法 `lang` 仍返回成功并产出音频 | P1 | 0924 轮新发现，待开发修 |
| 2 | 任务卡死 `status=67`：跨小时仍 67、`data` 空、`errorCode=0`、产物 404 | P1 | 已两次复现（0924 韩语 1 个 + 本轮 5 个） |
| 3 | 产物立即可获取性竞态：成功后立刻拉 `audio_url` 得 **440 B** COS 错误页 | P1 | 18/225（0924）+ 14/176（本轮），延迟重下 100% 成功 |
| 4 | 日语静默空洞：**81.64s** 固定时长无声段（有字无声） | P1 | M0 合规语料下仍复现（5 文件） |
| 5 | 段级时间轴不可信：69 字只给 0.56s（>15 字/秒 段占 1.3%） | P2 | ASR 定点核查显示时间轴错位 |
| 6 | 日语削波/响度越界：峰值 max ≈1.22、RMS ≈−11.5 dBFS | P2 | 日语批次全量触顶 |
| 7 | 韩语内容缺失（0924 扁平语料）：16 个任务估算缺口 20~46% | P1 | M0 合规语料下**未复现** → 与语料段落结构强相关 |

> 回归要求：每轮跑批都要核对 #1~#4 是否仍存在；若已修复，在报告中标注"本轮未复现"并附证据。

---

## 8. 报告交付规范（13 项，出报告前逐项打勾）

1 测试目的与范围 ｜ 2 环境与版本 ｜ 3 口径与判定标准 ｜ 4 数据与方法 ｜ 5 结果（M0~M5 逐项）｜
6 缺陷与建议（现象/证据/影响/分级）｜ 7 性能数据（创建耗时、端到端 P50/P90、吞吐、成功率；稳定性附趋势）｜
8 **本次测了什么、跳过了什么及原因** ｜ 9 缺陷含 taskId/时间窗/复现条件/排查建议 ｜ 10 附件索引 ｜
11 **数据范围声明**（只用本批次，不得拿其它时段数据填充）｜ 12 与历史结论冲突时必须说明采信理由 ｜
13 **产物与分发结论**（立即可获取性/签名时效/跨区/可解码性/首尾完整性/是否卡死；待确认项标 INFO）

---

## 9. 每日复盘与升级路径

| 时段 | 形式 | 内容 |
|---|---|---|
| 每天 09:30 | 15 分钟站会 | 昨天产出、今天计划、是否阻塞 |
| 每天 17:30 | 30 分钟复盘 | 走查当天产出物；纠正口径偏差；记录到新人笔记 |
| 遇到阻塞 | 立即 | 服务异常/权限/密钥 → 找负责人；口径不清 → 先查 `SKILL.md`，再问导师 |
| 缺陷确认 | 当天 | 新缺陷先按 §7 比对是否已报；已报的只做回归，不重复开单 |

**角色分工**：服务端问题 → 听书服务开发；语料与书籍 → 语料/数据同学；测试口径与报告 → 导师 + 新人；人工听测 → 指定听测人（由导师协调）。

---

## 10. 常见坑与红线（**都是踩过的，务必先读**）

### 红线（违反要回滚）

1. **未经明确允许，禁止删除任何数据**（含测试产物、批次目录、日志）——删除前必须先问。
2. **禁止 `git add -A` / `git add .`**：仓库里有大量他人未提交与已暂存内容，只用白名单入库脚本（隔离索引提交，不碰他人暂存区）。
3. **密钥只走环境变量**：不得写入脚本、文档、报告、git；发现疑似泄露立即上报。
4. **改文件前先快照**（`create_iteration_backup.ps1`），否则出问题无法回退。
5. **不得把 `taskStatus=2` 当作"通过"**：成功只代表有产物，必须独立跑 M1/M5 比对。

### 常见坑

6. **路径含中文**：命令行里给 git 传中文路径容易失败 → 用 `--pathspec-from-file`（脚本已内置）。
7. **`.ps1` 必须存为 UTF-8 with BOM**（Windows PowerShell 5.1 会把无 BOM 中文当 ANSI → 语法错误）。
8. **不要用管道捕获子进程输出**（ffmpeg/git 在受限沙箱下会因管道权限失败）→ 让输出直接落文件或终端。
9. **新批次目录必须自带 `material\`**（`units.jsonl` + `unit_*.txt`），否则跑批脚本直接报错。
10. **别读旧的 `summary.json`**：可能来自其它批次；吞吐/成功率一律从 `tasks.jsonl` 重算。
11. **ASR 参考文本只用"完全落在窗口内"的段**，否则会把"没念到一半的句子"误判成漏词（曾把 CER 3.81% 误算成 52.98%）。
12. **不要在跑批期间做本地重分析/解码**（CPU 抢占会污染延迟与吞吐结论）。
13. **`audio_url` 首轮拿到 XML 不是"音频丢了"**：先记下响应体大小（440 B 签名），隔 10~30 秒重下再判。
14. **harness 后台任务无输出 ≠ 卡住**：看 `progress.log`/`tasks.jsonl` 判断进度。
15. **磁盘**：每轮 30 分钟×10 并发约 0.4~0.5 GB/语种；余量低于 5 GB 时先申请清理（走红线 1）。

---

## 11. 只有 5 个工作日的压缩方案

| 工作日 | 合并内容 |
|---|---|
| D1 | §2 八项确认 + Day 1（环境与地图） |
| D2 | Day 2（必测项与口径）+ Day 3 的一半（跑 19 条用例） |
| D3 | Day 3 剩余（判读与缺陷条目）+ Day 4 的热身跑（5 分钟×5 并发） |
| D4 | Day 4 正式跑批（30 分钟×10 并发）+ 分析 |
| D5 | Day 5 精简（只做 M2 客观指标 + 抽样单）+ Day 6 报告（用生成器产出并核对 13 项） |
| 次周首日 | **Day 7 毕业考核**（独立跑一轮 + 入库） |

> 压缩后仍需保证：**M0 门禁**、**M1/M5 判定**、**一次完整报告**、**一次 git 入库** 四项不能省。

---

## 12. 附录

### A. 命令速查

```powershell
Set-Location D:\python\dmx\cdtest
$env:TTS_SECRET_KEY = '<测试环境密钥>'                    # 每次新会话都要设

# 探活（M0 验证）
python docs\听书测试物料\_probe_paragraph_once_0924.py --lang ja --unit 1

# 语料构建（M0 合规：保留段落换行 ~5000 字符）
python docs\听书测试物料\build_ja_ko_5000char_material.py --langs ja --suffix _dX

# 接口用例（正向 6 + 逆向 13）
python docs\听书测试物料\run_text_format_cases_0924.py --lang ja --workers 4 --out-suffix _d3

# 稳定性跑批（新目录先复制 material）
python docs\听书测试物料\run_higgs_ja_ko_10concurrent_30min.py --lang ja --workers 10 --minutes 30 --dir-name <批次目录>

# 分析：性能 + M1 + M5 ／ M2 客观音质（含非音频补齐）／ M3 ASR 抽样
python docs\听书测试物料\analyze_ja_ko_perf_0924.py --lang ja --run-dir <批次目录> --load-minutes 30
python docs\听书测试物料\audio_quality_ja_ko_0924.py --lang ja --run-dir <批次目录> --refetch
python docs\听书测试物料\asr_accuracy_ja_ko_largev3_0924.py --lang ja --run-dir <批次目录> --samples 2 --window 180 --out asr_d5

# 报告生成
python docs\听书测试物料\gen_report_round2_summary_0924.py      # 总报告
python docs\听书测试物料\gen_report_stability_0924.py           # 稳定性报告
python docs\听书测试物料\gen_report_cases_0924.py               # 接口用例报告

# 入库（先看清单，再推送；含脚本改动加 -WithScripts）
powershell -NoProfile -File scripts\sync_tingju_skill_to_git.ps1 -DryRun
powershell -NoProfile -File scripts\sync_tingju_skill_to_git.ps1 -Push
```

### B. 本批资产清单（交接物）

| 资产 | 位置 | 说明 |
|---|---|---|
| 技能规范 | `docs\听书测试物料\SKILL.md` | v1.1.7，唯一规范源 |
| 用例定义 | `测试用例\文案格式_正常与异常_0924.md`、`测试用例\接口与MP3产物_补充测试场景.md` | 19 条 + 9 族 60+ 条 |
| 可复用脚本 | `docs\听书测试物料\*.py`（78 个） | 语料/跑批/分析/报告/导出 |
| 一次性诊断脚本 | `docs\听书测试物料\_*.py`（36 个） | 结论落档后可清理 |
| 历史报告 | `测试报告\`（18 份） | 含 0924 轮 3 份 |
| 证据批次 | `mp3\`（39 个批次） | `src/meta/srt/audio/tasks.jsonl/summary.json/analysis/` |
| 开发分析包 | `开发分析包_接口与稳定性_0924.zip`（2.17 MB） | 含 8 个复现脚本，可直接给开发 |
| 入库流程 | `scripts\sync_tingju_skill_to_git.ps1` + `scripts\tingju_script_allowlist.txt`（72 条） | 白名单 + 守卫 + 隔离索引 |
| ASR 模型 | `tools\whisper_models\...\large-v3` | 2.9 GB，CPU int8 可用 |
| git | 分支 `codex/asr-leakage-fallback` | 远端已同步（HEAD `6b23745`） |

### C. 未覆盖项（交接时明确告知，避免误以为已测）

1. **人工听测**：多轮批次仍未做（技能硬性要求，需听测人）。
2. **Phase 9 未系统测**：跨区下载质量、首尾完整性、签名时效重取、并发拉取、`<taskId>.mp3` 可枚举越权。
3. **多语种**：本轮只做日语/韩语；其它语种（英/西/俄/葡等）沿用历史批次结论。
4. **长时稳定性**：本轮为 30 分钟；技能给出的"稳定性"最低口径是 2h（24h 浸泡更强），尚未执行。
