---
name: cdtest
description: "Unified AI-native test skill. Supports design mode & execution mode. Covers Web, iOS, Android & hybrid."
version: 3.5.2
author: qa-architect
triggers:
  - 测试
  - test
  - 自动化测试
  - 回归测试
---

# cdtest v3.5.2 — AI 原生统一测试技能

## ⚙️ Phase 状态追踪（AI 必须维护此表）

> 每个 Phase 执行前检查前置条件，完成后更新状态。按此表追踪进度，禁止跳过不可跳过的 Phase。

```yaml
# AI 在执行开始时初始化此表，每完成一个 Phase 即更新。
# 状态: PENDING | IN_PROGRESS | DONE | SKIPPED | FAILED
pipeline:
  Phase0:    { status: "PENDING", prereq: "无",                   output: "token_valid + env_ready" }
  Phase1_0:  { status: "PENDING", prereq: "Phase0.DONE",          output: "搜索结果 / 搜索跳过记录" }
  Phase1_0_5:{ status: "PENDING", prereq: "Phase1_0.DONE + requirement_meta存在", output: "historical_cases.json" }
  Phase1_1:  { status: "PENDING", prereq: "Phase1_0_5.DONE",      output: "配置已提取 + 模块已识别" }
  Phase1_2:  { status: "PENDING", prereq: "Phase1_1.DONE",        output: "test_plan.md + 影响分析" }
  Phase1_3:  { status: "PENDING", prereq: "Phase1_2.DONE",        output: "test_cases.json (初始用例)" }
  Phase2:    { status: "PENDING", prereq: "Phase1_3.DONE",        output: "data_prep_report.json" }
  Phase3a:   { status: "PENDING", prereq: "Phase2.DONE",          output: "exploration_result.json" }
  Phase1_4:  { status: "PENDING", prereq: "Phase3a.DONE",         output: "合并后 test_cases.json" }
  Phase2_5:  { status: "PENDING", prereq: "Phase1_4.DONE",        output: "补充数据就绪（如 Phase1.4 有新增用例）" }
  Phase3b:   { status: "PENDING", prereq: "Phase2_5.DONE + 熔断未激活", output: "case_execution_log.json + 截图" }
  Phase3_5:  { status: "PENDING", prereq: "token_valid",          output: "api_test_results.json" }
  Phase4:    { status: "PENDING", prereq: "Phase3b.DONE + Phase3_5.DONE", output: "测试报告.md" }
  KB_SYNC:   { status: "PENDING", prereq: "Phase4.DONE + MCP可用", output: "kb_sync_report.json" }

# Phase2_5（补充造数）触发条件: Phase1_4 产生了补充用例（supplementary_test_cases.json 非空）
# 如无补充用例则自动 SKIP
# 输出产物: supplementary_data_prep_report.json（合并到 data_prep_report.json）

# Phase3b 与 Phase3_5 执行策略:
#   当前环境无并行工具支持，以下为逐步实现路径:
#   现阶段（串行）: Phase3b → Phase3_5（简单可靠）
#   短期（手动并行）: 先并行执行不依赖 UI 的 API 用例（如 Phase 1.3 标记的独立 API 用例）
#   长期（真并行）: 当 agent-browser 支持多标签/多 session 时，UI 和 API 可真正并行
#   Phase4 需等待两者均完成

# 资源回收（Phase 3b/3.5 完成后主动清理）:
#   Web: agent-browser close --all            # 关闭所有浏览器窗口
#   iOS/Android: driver.quit()                # 关闭 Appium session
#   appium --port 4723 --stop                 # 停止 Appium server
#   清理临时文件: rm -rf temp/                # AHK 上传临时文件
#   DB 连接: 断开所有数据库连接
```

## 核心理念

**固定骨架 + AI 填充。有确定模式的用固定代码，无确定模式的用 AI 判断。**

| 环节 | 固定部分（骨架） | AI 部分（填充） |
|------|-----------------|----------------|
| 环境检查+登录 | 固定 agent-browser 登录 + Token 提取优先级链 | AI 识别登录页面类型（工号/账号/标准表单/SSO/验证码/已登录） |
| 交互探索 | 固定 6 步探索流程 | AI 识别元素类型、判断弹窗类型、发现缺口 |
| 探索反馈 | 固定 Q1/Q2/Q3 相关性判断 + 反馈链路 | AI 判断是否需要补充用例、生成补充用例 |
| Token 提取 | 固定优先级链: localStorage > Cookies > JS变量 > 已知API > 配置文件 | AI 验证 Token 有效性 |
| 登录处理 | 固定 5 类型 + auto-login.md 标准流程 | AI 识别页面类型 |
| 熔断保护 | 固定基准阈值 | AI 在范围内动态调整 |
| 报告生成 | 固定 6 章节骨架 | AI 填充内容 + 分析 |
| 执行循环 | 固定 8 步骤循环 | AI 在决策点判断 |
| 元素交互 | 固定 4 类型 | AI 定位目标元素 |
| 异常处理 | 固定处理策略 | AI 判断异常类型 |
| 需求分析 | — | AI 按 Phase 1 框架分析（AI 强项） |
| DB 验证 | — | AI 按 db-verify.md 框架执行（AI 强项） |
| 人工绕过 | — | AI 按 bypass-human.md 框架决策（AI 强项） |

---

## 架构

```
cdtest/
├── SKILL.md                    # 本文件：AI 大脑
├── common/                     # 公共模块（AI 判断框架）
│   ├── phase0-env-check.md     # AI 自主检查环境（含 agent-browser 强制检查）
│   ├── phase1-analyze.md       # AI 自主分析需求、生成用例（含 Phase 1.4 补充模式）
│   ├── phase2-data-prep.md     # AI 自主造数
│   ├── phase3_5-api-test.md    # AI 自主 API 测试
│   ├── phase4-report.md        # AI 自主生成报告
│   ├── mcp-kb-sync.md           # MCP 测试用例知识库集成（查询/冲突检测/入库同步）
│   ├── execution-optimization.md # 探查策略、等待策略、加载判断优化
│   ├── exploration.md           # 交互探索通用骨架（6步流程/结果格式/熔断/反馈链路）
│   ├── discovery-feedback.md   # 探索发现→用例补充反馈机制（Q1/Q2/Q3）
│   ├── db-verify.md            # AI 自主 DB 验证
│   ├── bypass-human.md         # AI 自主绕过人工依赖
│   ├── circuit-breaker.md      # AI 自主熔断决策
│   ├── ai-decisions.md          # AI 决策置信度/可观测性/覆盖度量
│   ├── case-template.md        # 字段定义（唯一来源，AI 引用）
│   ├── plan-template.md        # 方案模板（AI 引用）
│   └── 测试知识库.md           # 通用测试要点库（输入框/CRUD/翻页/界面/异常等）—— 需求分析、用例设计、执行验证各阶段引用
├── web/                        # Web 平台（AI 执行框架，含探索+自动登录）
│   ├── setup.md                # 环境配置
│   ├── auto-login.md           # agent-browser 自动登录+Token提取（唯一标准路径）
│   ├── exploration.md          # Web 交互探索（平台差异化选择器/交互/加载判断）
│   └── phase3-execute.md       # AI 自主执行 Web 测试（探索+执行双阶段）
├── ios/                        # iOS 平台（AI 执行框架，含探索）
│   ├── setup.md                # 环境配置
│   ├── session.md              # AI 自主管理会话（含 Token 提取优先级链）
│   ├── exploration.md          # iOS 交互探索（平台差异化选择器/交互/加载判断）
│   └── phase3-execute.md       # AI 自主执行 iOS 测试（探索+执行双阶段）
├── android/                    # Android 平台（AI 执行框架，含探索）
│   ├── setup.md                # 环境配置
│   ├── session.md              # AI 自主管理会话（含 Token 提取优先级链）
│   ├── exploration.md          # Android 交互探索（平台差异化选择器/交互/加载判断）
│   └── phase3-execute.md       # AI 自主执行 Android 测试（探索+执行双阶段）
├── mixed/                      # 混合模式（AI 调度框架）
│   ├── routing.md              # AI 自主判断混合模式
│   ├── data-share.md           # AI 自主管理数据共享
│   └── phase3-execute.md       # AI 自主调度混合执行
├── references/                 # 参考文件（AI 引用）
│   ├── historical-case-index.md # 历史模块索引
│   ├── output-checklist.md     # 交付检查清单
│   ├── product-lines.md        # 业务线对照表（Confluence目录ID/父页面ID）
│   └── confluence-search-guide.md # Confluence知识搜索使用指南
└── scripts/                    # 工具脚本
    └── export_artifacts.py     # Word/Excel 导出
```

---

## AI 决策流程

```yaml
# ⚠️ 注意: Phase 编号按功能模块划分，不代表严格执行顺序。
# Phase 1.4（用例补充）在 Phase 3a（交互探索）之后执行，
# 因为需要探索结果来发现遗漏的用例。
#
# 实际执行管线（按顺序）:
#
# ┌─────────────────────────────────────────────────────────────┐
# │ 执行模式完整流程                                            │
# ├─────────────────────────────────────────────────────────────┤
# │ Phase 0（环境检查+登录）                                    │
# │   ↓                                                        │
# │ Phase 1.0（Confluence 知识搜索）                           │
# │   ↓                                                        │
# │ Phase 1.0.5（MCP 测试用例知识库查询）                        │
# │   ↓                                                        │
# │ Phase 1.1（输入注入与历史资料召回）                          │
# │   ↓                                                        │
# │ Phase 1.2（产品需求解读与影响分析）                          │
# │   ↓                                                        │
# │ Phase 1.3（用例生成 - 初始用例集）                          │
# │   ↓                                                        │
# │ Phase 2（造数）                                            │
# │   ↓                                                        │
# │ Phase 3a（交互探索）→ 输出 discovery_gaps                  │
# │   ↓                                                        │
# │ Phase 1.4（用例补充 ← 消费 Phase 3a 探索结果）              │
# │   ↓ 合并完整用例集                                          │
# │ Phase 3b（UI 执行）                                         │
# │   ↓                                                        │
# │ Phase 3.5（API 测试）← 当前为串行执行，视工具支持可并行      │
# │   ↓                                                        │
# │ Phase 4（报告生成）                                         │
# │   ↓                                                        │
# │ KB_SYNC（用例入库到 MCP 知识库）                             │
# └─────────────────────────────────────────────────────────────┘
#
# 设计模式简化流程:
#   Phase 1.0 → Phase 1.1 → Phase 1.2 → Phase 1.3 → Phase 4(设计)

1. 理解意图:
   - AI 分析用户输入：用户想做什么？
   - 判断模式：设计模式 / 执行模式 / 混合模式
   - 判断平台：Web / iOS / Android / 混合

2. 收集信息:
   - AI 扫描可用输入源：spec/ 目录、用户描述、历史资料

3. 制定计划:
   - 执行模式: Phase 0(环境+需求前置检查+登录+Token) → Phase 1.0(Confluence搜索) → Phase 1.0.5(MCP历史用例查询) → Phase 1.1~1.3(分析+用例) → Phase 2(造数) → Phase 3a(探索) → Phase 1.4(补充) → Phase 3b(执行) → Phase 3.5(API) → Phase 4(报告) → KB_SYNC(入库)
   - 设计模式: Phase 1.1→1.2→1.3 → Phase 4(设计)
   - 混合模式: mixed/routing.md → 判定子模式 → 执行

4. ⛔ Web 平台禁止:
   - 跳过 agent-browser 直接用 curl 猜测 API 登录端点
   - 在不确认数据有效性的情况下反复重试 UI 操作
   - 遇到阻塞不告知用户直接静默跳过
5. ✅ Web 平台必须:
   - 配置持久化 Chrome Profile（agent-browser.json 配 "profile": "~/.chrome-persist"）：首次手动登录后点击"一律不"关闭密码弹窗，后续不再弹出（Chrome 148+ 密码弹窗无法通过 --args 彻底禁用）
   - 登录态复用：直接 open 目标页面 → 检查是否被重定向到登录页：
     * 到达目标页面（有用户信息/导航菜单）→ 登录态有效，跳过登录
     * 被重定向到登录页 → 执行登录流程
   - 登录流程优先用 eval 操作 Keycloak 表单（避免 ref 失效）
   - 操作前就近确认数据有效性: 有 DB 则用 DB, 无 DB 则从页面下拉/列表等 UI 元素确认可选值
   - 遇到人工阻塞: 请求用户 5 分钟内协助, 超时跳过并注明原因

6. 🧹 收尾:
   - 测试完成 → agent-browser close --all 关闭所有浏览器窗口
   - 按第七条生成全部交付物
```

---

## 七、交付物（必须生成，不可跳过）

```yaml
执行模式交付物:
  1. 测试方案: test_plan.md
     - 按 `common/plan-template.md` 固定 8 章节骨架

  2. 测试用例（双格式）:
     - test_cases.json — 机器可读，供 Phase 3b 执行循环使用
     - test_cases.md — 人工评审，Markdown 表格
     - 按 `common/case-template.md` 字段定义
     - 用例数 ≥ 需求测试点总数

  3. 测试报告: 测试报告.md
     - 按 `common/phase4-report.md` 固定 6 章节骨架
     - 概览必须包含: 通过率 | 总数 | 通过 | 失败 | 跳过
     - 失败分析必须包含: 失败原因 | AI 根因分析 | 建议

  4. 输出路径: {spec目录}/ 下
     - test_plan.md / test_cases.json / test_cases.md / 测试报告.md
     - conflicts.md（如发现逻辑冲突）/ kb_sync_report.json（如 MCP 可用）

设计模式交付物:
  - Word 测试方案 .docx + Excel 测试用例 .xlsx
  - 由 scripts/export_artifacts.py 生成

⛔ 禁止:
  - 只给口头总结不给文件
  - 报告结构任意、缺少固定章节
  - 缺少概览统计数据
```

---

## 模式说明

### 设计模式

```yaml
# 产出：测试方案 Word + 测试用例 Excel
# AI 执行：Phase 1.0→1.1→1.2→1.3 → Phase 4(设计)
# AI 不执行：环境检查、造数、UI 执行、API 测试、交互探索
# 输出路径:
#   中间产物: {spec目录}/test_plan.md + test_cases.csv
#   最终产物: {spec目录}/前缀_测试方案.docx + 前缀_测试用例.xlsx
#   (由 scripts/export_artifacts.py 从 .md/.csv 生成 .docx/.xlsx)
```

### 执行模式

```yaml
# 产出：完整执行 + 截图 + 日志 + 测试报告
# AI 执行：
  - Phase 0: 检查环境 → 提取需求 pageId+系统名称 → agent-browser 自动登录 → 提取 Token
  - Phase 1: 分析需求 → 生成初始用例集
  - Phase 2: 判断数据需求 → 造数
  - Phase 3a: 交互探索 → 发现弹窗、功能、菜单
  - Phase 1.4: 探索反馈补充 → Q1/Q2/Q3 相关性判断 → 补充遗漏用例
  - Phase 2.5: 补充造数（如 Phase 1.4 有新增用例）
  - Phase 3b: 执行用例 → 截图 → 验证
  - Phase 3.5: API 测试
  - Phase 4: 分析结果 → 生成报告 → 给出结论
# 输出路径: {spec目录}/test_plan.md + test_cases.json + test_cases.md + 测试报告.md
```

### 混合模式

```yaml
# 产出：混合报告（Web 配置记录 + APP 验证结果 + 链路追踪）
# AI 执行：判断混合子模式 → 调度执行 → 跨平台数据共享 → 融合报告
```

---

## 参考文件

### 执行阶段文件（Phase 文件）

| 文件 | Phase | AI 如何使用 |
|------|-------|------------|
| `common/phase0-env-check.md` | Phase 0 | 环境检查 + agent-browser 初始化 + Swagger 预下载 |
| `web/auto-login.md` | Phase 0 | 自动登录+Token提取（Web 唯一标准路径） |
| `common/phase1-analyze.md` | Phase 1 | 需求分析框架 + 用例生成 + Phase 1.4 补充模式 |
| `common/phase2-data-prep.md` | Phase 2 + 2.5 | 造数策略 + 补充造数 |
| `common/phase3_5-api-test.md` | Phase 3.5 | API 测试设计+执行 |
| `common/phase4-report.md` | Phase 4 | 报告骨架 + case_execution_log.json 格式 |
| `common/mcp-kb-sync.md` | Phase 1.0.5 + KB_SYNC | MCP 历史用例查询 + 冲突检测 + 执行后入库同步 |
| `web/phase3-execute.md` | Phase 3b | Web 执行引擎（8步循环+探索+上传+异常） |
| `ios/phase3-execute.md` | Phase 3b | iOS 执行引擎 |
| `android/phase3-execute.md` | Phase 3b | Android 执行引擎 |
| `mixed/phase3-execute.md` | 混合 Phase 3 | 混合模式调度执行 |

### 策略/增强文件

| 文件 | 用途 | AI 如何使用 |
|------|------|------------|
| `common/execution-optimization.md` | 探查/等待/加载判断 + 深度测试矩阵 + 异常场景处理 | AI 执行时引用交互策略 |
| `common/discovery-feedback.md` | 探索→补充反馈链路（Q1/Q2/Q3 过滤） | AI 判断探索发现是否与需求相关 |
| `common/circuit-breaker.md` | 熔断保护机制（状态机+探测+统计） | AI 在 Phase 3b 每个用例开始前检查 |
| `common/ai-decisions.md` | AI 决策置信度/可观测性/覆盖度量 | AI 在关键决策点评估置信度 + 输出 decisions.jsonl + Phase 4 用覆盖度量评估充分性 |
| `common/db-verify.md` | AI 自主 DB 验证框架 | AI 验证数据库完整性 |
| `common/bypass-human.md` | AI 自主绕过人工依赖（含回滚保护） | AI 在遇到阻塞时评估是否可绕过 |
| `common/mcp-kb-sync.md` | MCP 测试用例知识库集成（查询/冲突/入库） | AI 在 Phase 1.0.5 和 KB_SYNC 阶段引用 |

### 平台差异化文件

| 文件 | 用途 | AI 如何使用 |
|------|------|------------|
| `web/exploration.md` | Web 交互探索差异化 | AI 系统性发现 Web 页面交互元素 |
| `ios/exploration.md` | iOS 交互探索差异化 | AI 系统性发现 iOS 页面交互元素 |
| `android/exploration.md` | Android 交互探索差异化 | AI 系统性发现 Android 页面交互元素 |
| `web/setup.md` | Web 环境配置 | Phase 0 环境安装指引 |
| `ios/setup.md` | iOS 环境配置 | Phase 0 环境安装指引 |
| `ios/session.md` | iOS 会话管理 + Token 提取 | Phase 0 会话初始化 |
| `android/setup.md` | Android 环境配置 | Phase 0 环境安装指引 |
| `android/session.md` | Android 会话管理 + Token 提取 | Phase 0 会话初始化 |
| `mixed/routing.md` | 混合模式路由 | AI 判断混合子模式 |
| `mixed/data-share.md` | 跨平台数据共享策略 | AI 管理混合模式数据传递 |

### 模板/规范文件

| 文件 | 用途 | AI 如何使用 |
|------|------|------------|
| `common/case-template.md` | 用例字段定义 + 值域约束 + 最低覆盖基线（唯一来源） | AI 生成用例时引用字段格式和基线要求 |
| `common/plan-template.md` | 测试方案 8 章节模板 | AI 生成 test_plan.md 时引用结构 |
| `common/测试知识库.md` | 通用测试要点库（按功能类型分类引用） | AI 按功能类型选择性引用章节 |
| `references/historical-case-index.md` | 历史模块索引（Confluence 不可用时兜底） | AI 匹配历史资料时引用 |
| `references/output-checklist.md` | 交付检查清单 | AI 交付前自检 |
| `references/product-lines.md` | 业务线对照表（Confluence目录ID） | Phase 1.0 搜索时选择 directories |
| `references/confluence-search-guide.md` | Confluence 搜索指南 | Phase 1.0 搜索命令+返回值解析 |
| `scripts/export_artifacts.py` | Word/Excel 导出 | 设计模式最终交付物生成 |

---

## 已知限制

```yaml
限制:
  - Web 浏览器: 仅支持 Chrome（agent-browser 依赖）
  - APP 双端同时执行: 仅支持依次执行
  - P3 安全测试: 基础探测，非专业渗透测试
  - APP 真机测试: 需要额外配置
  - 混合模式: Web 和 APP 必须在同一测试环境
  - Word/Excel 导出: 依赖 python3 + export_artifacts.py
```

## 关键实践教训（v3.3.0 新增）

### 教训 1：配置修改后必须恢复——配置测试的"先改后还"原则

```yaml
问题: 测试筛选配置、表头配置等可持久化配置项时，取消勾选某些字段后
      忘记恢复，导致后续所有查询和测试在"残缺"的配置环境下执行，
      影响测试结果的准确性。

根因: 配置修改是持久化的（保存到后端或 localStorage），
      不像页面操作可以通过刷新恢复。AI 在配置测试后容易遗漏"恢复"步骤。

强制规则（必须遵守）:
  1. 每条配置修改测试前，先 snapshot 保存当前配置的完整状态
  2. 每条配置修改测试后，立即恢复配置到测试前状态（"改完即还"）
  3. 恢复后必须 snapshot 验证配置已正确还原
  4. 多条配置测试连续执行时，每个子项独立执行"改→验→还→验"循环

执行模式:
  改前快照 → 执行修改 → 验证效果 → 恢复修改 → 验证恢复 → 下一条

校验方法:
  筛选配置: 检查页面上的筛选器数量/类型是否与保存一致
  表头配置: 检查表头 columnheader 数量/文本是否与保存一致
  显示选项: 检查对应 checkbox 的 checked 状态
```

### 教训 2：报表类查询必须动态等待加载完成

```yaml
问题: 报表类页面点击"查询"后，数据加载通常需要 5-15 秒，
      如果固定等待 3-5 秒就开始 snapshot 验证，得到的是 loading 状态
      或"暂无数据"的中间状态，而非最终结果。

强制规则（必须遵守）:
  1. 点击查询后，立即轮询检测加载完成信号
  2. 加载完成判断（任一满足即停止等待）:
     - loading 指示器消失（button 不再显示 spinner/loading 文本）
     - 表格中出现数据行（tr/row/cell 元素数量变化）
     - "暂无数据"提示消失
     - 分页组件出现（显示"共 X 条"）
     - 特定加载动画（如骨架屏）消失
  3. 轮询间隔: 每 1-2 秒检查一次（低成本 eval）
  4. 超时阈值: 默认 30 秒（报表类最慢可在 20-30 秒完成）
  5. 超时后: 高成本 snapshot 探查 → 判断是加载慢还是报错

注意事项:
  - 不要通过固定 sleep 等待，不同数据量/查询条件的耗时不同
  - 不要等完立即 full snapshot，先用 eval 轻量判断
  - 数据行检查兼顾 data-rows 与 empty-state 两种信号
```

### 教训 3：禁止"只探查不测试"——深度测试是必须的执行环节

```yaml
问题: AI 容易沦为"界面探索工具"——探索分析做了很多，但缺少对
      每个功能的深度测试（边界值、异常流、组合场景、数据验证）。
      用户指出的"只做了探查，没有深度测试"是核心问题。

强制规则（必须遵守）:
  1. 初步探索发现功能点后，必须针对每个功能点进行深度测试
  2. 深度测试测试矩阵（每个功能点至少覆盖以下类型）:
     ✅ 正常流程: 功能按预期工作
     ✅ 边界值: 输入最小/最大/空值/特殊字符
     ✅ 组合场景: 多个条件同时作用（如时间+短剧+消耗组合查询）
     ✅ 数据验证: 对计算指标做公式验证（如 CPM=消耗/展示×1000）
     ✅ 异常流程: 空数据/无效输入/超大数据量
  3. 不要在"探索→探索→探索"循环中浪费时间，发现即测试
  4. 深度测试产出物:
     - 每条测试记录实际值 vs 预期值
     - 计算公式书面验证（前后对比）
     - 截图保留证据

特别提示（报表类）:
  - 指标正确性验证是最核心的测试项
  - 每条数据的指标联动关系必须用 agent-browser eval 做实际计算验证:
    # 示例: 验证 CPM = 消耗/展示×1000
    agent-browser eval "
    (() => {
      const cost = parseFloat(document.querySelector('td:nth-child(N)').textContent);
      const imp = parseFloat(document.querySelector('td:nth-child(M)').textContent);
      const expectedCPM = (cost / imp * 1000).toFixed(2);
      const actualCPM = document.querySelector('td:nth-child(K)').textContent.trim();
      return JSON.stringify({ expected: expectedCPM, actual: actualCPM, match: expectedCPM === actualCPM });
    })()
    "
  - 输出格式: "公式: CPM=消耗/展示×1000, 计算值=X, 页面值=Y, 偏差=Z%"
  - 注意数据实时变化：首次查询的值和后续查询的值可能因数据更新而不同
```

### 教训 4：必须包含基本异常场景测试

```yaml
问题: AI 倾向于测试"正常路径"，忽略异常场景（空数据、错误输入、
      网络中断、权限不足等），导致测试覆盖度不足。

强制规则（必须遵守）:
  1. 每个功能至少包含以下异常场景测试:
     - 空数据/无数据: 查询不存在的条件（如未来日期/不可能的 ID）
     - 无效输入: 输入非法格式（负数/超长字符串/特殊字符）
     - 边界值: 输入0/空串/最大值+1
     - 组合条件冲突: 时间范围开始>结束
     - 超大数据量: 不设筛选条件查询全量数据
  2. 异常场景的判断标准:
     - 页面是否显示友好的空状态提示（非白屏/非未捕获异常）
     - 是否有明确的错误提示（Toast/Alert/Form validation）
     - 是否出现 500/Bug 页面
  3. 异常场景的验证方式:
     - 预期空状态: check "暂无数据" / empty-state 图片
     - 预期错误提示: check 错误文本 / Toast 文本
     - 预期页面稳定: snapshot 确认无白屏/无 JS 报错

常见异常场景清单（必须覆盖）:
  - 报表查询 → 空时间段、未来时间、超大范围
  - 搜索框 → 不存在的关键词、空搜索、超长关键词
  - 表单提交 → 必填项空、邮箱格式错误、数字字段输入文本
  - 列表/表格 → 无数据、单条数据、大量数据（超过一页）
  - 导出 → 无数据导出、大数据导出
```

---

## 使用说明

### 环境准备（首次使用）

```bash
# 1. 配置 agent-browser（持久化 Profile + 最大化窗口）
#    在项目根目录创建 agent-browser.json：
#    {"headed": true, "args": "--start-maximized", "profile": "~/.chrome-persist"}

# 2. 配置 MCP 测试用例知识库（可选，用于 Phase 1.0.5 + KB_SYNC）
mcporter config add test-case-mcp http://mastra-dev.changdu.ltd/api/mcp/test-case-mcp-server/mcp
mcporter call test-case-mcp getTestCaseStatus   # 验证

# 3. 首次使用需手动登录一次，点击"一律不"关闭密码弹窗（持久化 Profile 会记住此设置）
```

### 触发关键字

cdtest 通过以下关键字自动激活：`测试`、`test`、`自动化测试`、`回归测试`

### 完整执行模式

```bash
# Web 执行模式 — 全管线：Phase 0 → 1.0.5 → 1.1~1.3 → 3a → 3b → 4 → KB_SYNC
"帮我测试 https://xxx.com 的XX功能"

# 指定 spec 目录执行
"使用cdtest，对 spec/版权方 进行完整测试"

# iOS / Android
"帮我测试 iOS 端 XX 功能"
"帮我测试 Android 端 XX 功能"
```

### 设计模式（仅生成方案和用例，不执行）

```bash
"帮我写一份XX功能的测试方案"
"帮我设计XX的测试用例"
```

### 分阶段执行

```bash
# 仅环境检查 + 登录（Phase 0）
"检查测试环境，登录 https://xxx.com"

# 仅查看历史用例（Phase 1.0.5）
"查询创作者后台的历史测试用例"

# 仅生成用例（Phase 1.0~1.3）
"根据 spec/版权方 需求，生成测试用例"

# 仅执行已有用例（Phase 3b）
"执行 spec/版权方/output/test_cases.json 中的用例"

# 仅 API 测试（Phase 3.5）
"对 https://xxx.com 的 API 进行测试"

# 仅同步用例到知识库（KB_SYNC）
"把 spec/版权方/output/case_execution_log.json 中的 PASS 用例入库"

# 仅查询知识库（searchTestCases）
"查询创作者后台 短剧管理 模块的 P0 用例"
```

### 跳过特定阶段

```bash
# 跳过高耗时阶段
"快速执行，跳过 Confluence 搜索和交互探索"
"只做 UI 执行，跳过历史用例查询"

# 指定设计模式（跳过所有执行阶段）
"设计模式，生成测试方案和用例即可"
```
