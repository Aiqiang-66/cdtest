# MCP 测试用例知识库集成

## 定位

**定义与 MCP Test Case Server 交互的完整流程**：查询历史用例、检测逻辑冲突、执行后入库同步。

> MCP Server 详情见 `spec/用例初始化构建/1-需求说明/mcp接口说明.md`

---

## 一、MCP 连接与状态检查

### 状态检查

```yaml
# 每次涉及 MCP 知识库操作前，先检查可用性
调用: mcporter call test-case-mcp getTestCaseStatus
返回: { configured: bool, message: string, testCaseCount: int, archivedTestCaseCount: int }

不可用时的处理:
  - configured=false → 跳过所有 MCP 知识库操作
  - 记录警告到环境检查报告: "MCP Test Case Server 未配置数据库，用例知识库不可用"
  - 不影响测试执行和报告生成，仅跳过入库步骤

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔴 已知问题: MCP Server 需要服务端 PostgreSQL 连接
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
服务端配置要求（在 MCP Server 所在服务器上设置）:
  环境变量（任一即可）:
    - TEST_CASE_POSTGRES_DB       # 格式: postgresql://user:pass@host:port/db
    - POSTGRES_DB                 # 同上
    - POSTGRES_CONNECTION_STRING  # 同上
  
  如果 getTestCaseStatus 返回 {configured:false, testCaseCount:0}:
    → MCP Server 管理员需要在服务器上设置上述环境变量
    → 重启 MCP Server 服务后生效
    → 在此之前，所有 createTestCase/updateTestCase/searchTestCases 调用都将失败
```

### 连接信息

```yaml
MCP Server: Test Case MCP Server v1.0.0
协议: MCP 2025-03-26（Streamable HTTP + SSE）
端点: https://aiprd.changdu.vip/api/mcp/test-case-mcp-server/mcp
```

### mcporter 配置（必须先行配置，否则所有 MCP 知识库操作跳过）

mcporter 通过 `config add` 命令注册 MCP Server，一行命令即可完成：

```bash
# 配置（一行命令，自动识别协议类型）
mcporter config add test-case-mcp https://aiprd.changdu.vip/api/mcp/test-case-mcp-server/mcp

# 验证
mcporter list
# 期望输出: test-case-mcp (9 tools) ✓

# 测试连接
mcporter call test-case-mcp getTestCaseStatus
# 期望返回: { "configured": true, "testCaseCount": 309, ... }
```

**配置说明**：

| 参数 | 值 | 说明 |
|------|-----|------|
| 注册名 | `test-case-mcp` | cdtest 技能中所有 MCP 调用使用的 server 名称，**不可更改** |
| MCP 端点 | `https://aiprd.changdu.vip/api/mcp/test-case-mcp-server/mcp` | Streamable HTTP + SSE |

⚠️ **不要手动创建 JSON 配置文件**（`~/.mcporter/servers.json` 方式无效），mcporter 使用项目级配置（`config/mcporter.json`），`config add` 命令自动写入正确位置。

**验证结果**：配置成功后，cdtest 技能在 Phase 1.0.5 和 KB_SYNC 阶段将自动连接 MCP 知识库，执行用例查询和入库同步。之前跳过的管线步骤将不再跳过。

---

## 二、前置检查：提取 pageId 和系统名称

### 检查时机

```yaml
# Phase 0 环境检查时执行，在任何测试操作之前
# 如果缺失 → 立即提示用户，不等到 Phase 4 入库时才发现
```

### 检查流程

```yaml
1. 扫描需求文档:
   - 读取 spec/ 目录下所有 .md 文档
   - 查找以下关键字段:
     * Confluence pageId（需求对应的 Confluence 页面 ID）
     * 系统名称（system，对应 createTestCase 的 system 字段）
     * 业务类型（businessType: 后台/APP）
     * 需求版本号（requirementVersion）

2. 提取规则:
   pageId:
     - Confluence URL 中的 pageId: /pages/viewpage.action?pageId=123456 → 123456
     - 需求文档中标注的 "Confluence ID" 或 "页面ID"
   
   系统名称（system）:
     - 必须从 MCP 接口说明中的 40 个系统列表匹配
     - 常用系统: 创作者后台、战神广告系统、星河文档系统、北斗数据中台 等
     - 模糊匹配: "创者" → "创作者后台", "广告" → "战神广告系统"
     - ⚠️ 无法确定时列出候选，让用户选择
   
   业务类型（businessType）:
     - Web 平台测试 → "后台"
     - APP 平台测试 → "APP"
     - 混合模式 → 根据主要测试目标判断
   
   需求版本号（requirementVersion）:
     - 从需求文档中提取版本号（如 "v2.3", "000001"）
     - 需求文档的 Confluence 版本号
     - 缺失 → 使用日期格式 YYYYMMDD 或提示用户提供

3. 缺失处理:
   任一必填项缺失 → 提示用户:
     "以下信息用于测试用例入库追溯，请提供：
      - Confluence pageId: [请提供需求对应的 Confluence 页面 ID]
      - 系统名称: [请从以下列表选择：神农、星河文档系统、...创作者后台...阅读APP、短剧APP]
      - 需求版本号: [如 000001，或按 YYYYMMDD 格式]"
   
   用户回复后 → 保存到 requirement_meta.json

4. 输出:
   requirement_meta.json:
   {
     "confluencePageId": "123456789",
     "system": "创作者后台",
     "businessType": "后台",
     "requirementVersion": "000001",
     "extractedAt": "2026-05-28T10:00:00+08:00",
     "source": "spec/需求说明.md"
   }
```

### 系统名称候选列表

```yaml
# 从 mcp接口说明.md 摘录，完整 40 个系统:
系统列表:
  - 神农
  - 星河文档系统
  - 风云项目管理系统
  - 修改工号密码
  - 电子图书馆
  - 爆款内容创作系统
  - 海剧内容后台
  - 国剧内容运营后台
  - 新掌中编辑后台
  - Simple内容后台
  - TAG运营后台
  - 战神广告系统
  - 雷霆素材系统
  - 内网邮件
  - 通用翻译平台
  - 财务管理后台
  - 创作者后台
  - 资料管理系统
  - 制片管理系统
  - AI短剧系统
  - 海剧运营后台
  - 北斗数据中台
  - KOC营销平台
  - 畅读分销平台
  - 自动化解说漫系统
  - 圣经运营后台
  - 业务中台
  - 沙盘
  - 极光大数据平台
  - 商业智能
  - 昆仑
  - 钟道
  - 伏羲
  - CMDB
  - 绩效系统
  - 招聘系统
  - 女娲
  - 版权方后台
  - 阅读APP
  - 短剧APP
```

---

## 三、用例知识库查询（Phase 1.0.5 执行）

### 触发条件

```yaml
# Phase 1.0（Confluence 知识搜索）完成后执行
触发:
  - MCP Test Case Server 可用（getTestCaseStatus.configured = true）
  - requirement_meta.json 中 system 已确定

跳过:
  - MCP 不可用
  - system 未确定（用户尚未提供）
  - 用户明确要求不查询历史用例
```

### 搜索策略

```yaml
1. 基础搜索（按系统+模块）:
   mcporter call test-case-mcp searchTestCases \
     system="<系统名称>" \
     businessType="<后台/APP>" \
     limit=50

2. 语义搜索（按需求关键词）:
   # 从需求文本提取 3-5 个核心关键词
   mcporter call test-case-mcp searchTestCases \
     system="<系统名称>" \
     businessType="<后台/APP>" \
     caseNameSemanticQuery="<关键词组合>" \
     caseNameSemanticMinScore=0.5 \
     limit=30

3. 版本过滤（可选）:
   # 如果已知历史需求版本，可直接查询
   mcporter call test-case-mcp searchTestCases \
     system="<系统名称>" \
     requirementVersion="<历史版本号>" \
     limit=50

硬限制:
  - Phase 1.0.5 中 searchTestCases 最多调用 3 次
  - 达到上限后使用已有结果
  - 结果按匹配度排序，取前 50 条用于后续整合
```

### 搜索结果处理

```yaml
# 搜索返回格式: { data: [{ id, caseName, system, module, testType, priority,
#                          testSteps, expectedResult, requirementVersion, ... }], total }

结构化处理:
  1. 按功能模块分组（module 字段）
  2. 标注来源（id + requirementVersion）
  3. 提取可复用的验证点（testSteps + expectedResult 中的关键检查项）
  4. 识别历史风险点（priority=P0/P1 的回归/异常流程用例）

输出:
  historical_cases.json:
  {
    "query_info": { system, businessType, keywords, searchedAt },
    "total_found": 35,
    "by_module": {
      "报表查询": [
        { id, caseName, testType, priority, source_version, key_points: [...] }
      ],
      "筛选配置": [ ... ]
    },
    "reusable_patterns": [
      "空数据查询 → 验证'暂无数据'提示",
      "时间倒置 → 验证前端/后端校验提示"
    ],
    "risk_areas": [
      "指标计算精度（历史需求多次出现计算偏差）",
      "大数据量查询超时（历史 P0 用例）"
    ]
  }
```

---

## 四、用例整合与冲突检测

### 整合优先级

```yaml
# Phase 1.3 用例生成时，整合当前需求 + 历史用例
# 核心原则: 当前需求为主，历史用例为辅

整合策略:
  优先级 1（当前需求，直接采用）:
    - 需求文档明确描述的功能点 → 按需求描述生成用例
    - 需求文档中的字段定义、流程步骤 → 作为权威来源
  
  优先级 2（历史用例补充，标注来源）:
    - 历史用例中与当前功能点匹配的边界值/异常场景 → 补充
    - 历史用例中标记为 P0/P1 回归的 → 纳入回归用例集
    - 历史用例的验证点写法（具体检查项）→ 参考复用
    - ⚠️ 每条补充的历史用例必须标注来源: "来自历史用例 {id} (v{requirementVersion})"
  
  优先级 3（通用知识库，兜底）:
    - 当前需求和历史用例都未覆盖的场景 → 引用 测试知识库.md 补充

处理规则:
  - 历史用例的 testSteps 不直接复制，需根据当前页面结构适配
  - 历史用例的 expectedResult 不直接复制，需对比当前需求是否能匹配
  - 如果历史用例的场景在当前需求中已被删除/重构 → 不纳入，标注"已废弃"
```

### 冲突检测

```yaml
# Phase 1.3 用例生成后执行（在自我审查之后）
# 对比当前需求生成的用例 vs 历史 MCP 用例

冲突类型:
  A. 字段口径冲突:
     - 同一数据字段在不同版本中定义不同
     - 例: 历史用例验证 ROI=消耗/展示×1000，当前需求改为 ROI=收入/成本×100%
     - 检测方式: 对比 expectedResult/verificationPoint 中的公式和取值
  
  B. 流程步骤冲突:
     - 同一业务操作在不同版本中步骤不同
     - 例: 历史用例"先审核后提交"，当前需求"先提交后审核"
     - 检测方式: 对比 testSteps 中的操作顺序
  
  C. 预期结果矛盾:
     - 同一操作在不同版本中预期不同
     - 例: 历史用例预期"删除后列表刷新"，当前需求预期"删除后跳转回收站"
     - 检测方式: 对比 expectedResult 中的状态变化描述

检测流程:
  1. 对每个当前需求用例，在历史用例中查找同 module + 同功能点的用例
  2. 对比 testSteps / expectedResult / verificationPoint
  3. 发现差异 → 判断是"正常演进"还是"逻辑冲突"
     - 正常演进: 新增字段/新增步骤/新增验证 → 不冲突
     - 逻辑冲突: 相同字段不同定义/相同步骤不同顺序/相同操作不同预期 → 记录

输出:
  conflicts.md:
  | # | 冲突类型 | 当前需求 | 历史用例(来源) | 冲突描述 | 影响范围 | 建议 |
  |---|---------|---------|---------------|---------|---------|------|
  | 1 | 字段口径 | ROI=收入/成本 | TC-X-001(v1): ROI=消耗/展示 | ROI 计算公式不一致 | 报表验证用例 | 以当前需求为准 |
  | 2 | 流程步骤 | 先提交后审核 | TC-X-003(v1): 先审核后提交 | 操作顺序相反 | 状态流转用例 | 需确认哪个版本正确 |

用户确认:
  - 列出所有冲突 → 提示用户逐条确认
  - 用户选择: "采用新版本" / "保留旧版本" / "两者都保留（标注差异）"
  - 确认后更新用例集，冲突已解决的标记为 resolved
  - 未确认的冲突用例标记为"待确认"，不阻塞其他用例执行
```

---

## 五、用例入库同步（KB_SYNC 阶段执行）

### 触发条件

```yaml
# Phase 4 测试报告生成后、整个测试流程结束前执行
触发:
  - Phase 3b + Phase 3.5 均已完成
  - MCP Test Case Server 可用
  - requirement_meta.json 中 system + requirementVersion 已确定

跳过:
  - 设计模式（无执行结果，无需入库）
  - MCP 不可用
  - requirement_meta 不完整
```

### 入库筛选规则

```yaml
# 从 case_execution_log.json 中筛选待入库用例

入库（createTestCase）:
  条件:
    - status = PASS
    - 来源为"当前新需求"（非历史用例、非探索补充）
    - 历史用例中不存在同 caseName+system+module 的用例
  操作:
    # 🔴 必须使用 --args JSON 格式，禁止 key=value 格式!
    # 原因: key=value 格式下 mcporter 将纯数字值解析为 JSON number，
    #       而 MCP createTestCase 要求 requirementVersion 为 string，导致报错:
    #       MCP error -32602: expected string, received number
    #
    # ✅ 正确方式: --args '{"key":"value"}' JSON，类型由 JSON 规范保证
    mcporter call test-case-mcp createTestCase \
      --args '{
        "caseName": "<用例名称>",
        "system": "<requirement_meta.system>",
        "businessType": "<requirement_meta.businessType>",
        "requirementVersion": "<requirement_meta.requirementVersion>",
        "module": "<功能模块>",
        "testType": "<测试类型>",
        "priority": "<优先级>",
        "precondition": "<前置条件>",
        "testSteps": "<测试步骤>",
        "expectedResult": "<预期结果>",
        "verificationPoint": "<验证点>",
        "testData": "<测试数据>"
      }'

更新（updateTestCase）:
  条件:
    - status = PASS
    - 历史已存在同 caseName+system+module 的用例
    - 用例内容有变化（testSteps/expectedResult 不同）
  操作:
    mcporter call test-case-mcp updateTestCase \
      id="<历史用例UUID>" \
      testSteps="<更新后的步骤>" \
      expectedResult="<更新后的预期>" \
      verificationPoint="<更新后的验证点>"

不更新:
  条件:
    - 历史已存在且内容无变化 → 跳过，标注"已是最新"
    - status = FAIL/SKIP/BLOCKED → 跳过，不覆盖历史有效用例
    - 来源为"探索补充"且非 P0/P1 → 跳过

删除（deleteTestCase）:
  条件:
    - 仅对 conflicts.md 中用户确认"采用新版本"的冲突用例
    - 仅删除逻辑已被当前需求推翻的历史用例
    - ⚠️ 删除前必须列出清单 + 说明原因 → 用户确认后执行
  操作:
    mcporter call test-case-mcp deleteTestCase id="<历史用例UUID>"

跳过:
  条件:
    - status = FAIL 且失败原因是环境问题（非逻辑错误）→ 不入库，记录到报告
    - status = SKIP → 不入库
    - 探索补充的 P2 级别用例 → 不入库
```

### 入库参数映射

```yaml
# 用例字段 → MCP createTestCase 参数

映射表:
  | 用例字段          | MCP 参数            | 必填 | 说明 |
  |------------------|--------------------|------|------|
  | 用例名称          | caseName           | ✅   | 直接映射 |
  | 所属系统          | system             | ✅   | 从 requirement_meta.system |
  | 业务类型          | businessType       | ✅   | 后台/APP，从 requirement_meta |
  | 需求版本号        | requirementVersion | ✅   | 从 requirement_meta |
  | 功能模块          | module             | ❌   | 直接映射 |
  | 测试类型          | testType           | ✅   | 功能/异常流程/回归 |
  | 优先级            | priority           | ✅   | P0/P1/P2/P3 |
  | 前置条件          | precondition       | ❌   | 直接映射 |
  | 测试步骤          | testSteps          | ❌   | 直接映射 |
  | 预期结果          | expectedResult     | ❌   | 直接映射 |
  | 测试数据          | testData           | ❌   | 直接映射 |
  | 验证点            | verificationPoint  | ❌   | 直接映射 |
  
  APP 额外字段:
  | 平台              | platform           | ❌   | ["Android","iOS"] |
  | 测试环境          | testEnvironment    | ❌   | ["内网","外网","预发","测试"] |
  | APP版本号         | appVersion         | ❌   | iOS:X.X.X; Android:X.X.X |
  | 服务端版本号      | serverVersion      | ❌   | 纯数字 |
```

### 批量策略

```yaml
批量规则:
  - 每批次最多 50 条用例
  - 超过 50 条 → 分批次执行，每批间隔 2 秒
  - 单条入库失败 → 记录错误，继续下一条（不阻断批量操作）
  - 连续 5 条失败 → 暂停，检查 MCP 连接状态

重试:
  - 单条失败 → 重试 1 次
  - 仍失败 → 跳过，记录到 kb_sync_report.json 的 failed 列表
```

### 输出

```yaml
kb_sync_report.json:
{
  "synced_at": "2026-05-28T15:30:00+08:00",
  "requirement": {
    "confluencePageId": "123456789",
    "system": "创作者后台",
    "businessType": "后台",
    "requirementVersion": "000001"
  },
  "created": [
    { "id": "uuid-1", "caseName": "新增短剧-正常创建", "system": "创作者后台" }
  ],
  "updated": [
    { "id": "uuid-2", "caseName": "列表筛选-按类型", "changedFields": ["testSteps", "expectedResult"] }
  ],
  "deleted": [
    { "id": "uuid-3", "caseName": "旧版审核流程", "reason": "用户确认采用新版流程，旧版逻辑已废弃" }
  ],
  "skipped": [
    { "caseName": "批量导入-异常格式", "reason": "用例 FAIL（环境问题），不入库" },
    { "caseName": "导出-空数据", "reason": "已存在且内容无变化" }
  ],
  "failed": [
    { "caseName": "XXX", "error": "MCP 连接超时" }
  ],
  "summary": {
    "total_created": 12,
    "total_updated": 3,
    "total_deleted": 1,
    "total_skipped": 5,
    "total_failed": 1,
    "total_unchanged": 8
  }
}
```

---

## 六、完整管线集成

```yaml
# MCP 知识库在 cdtest 管线中的位置:

Phase 0（环境检查）:
  └── §需求文档前置检查 → 提取 pageId + system → requirement_meta.json
      缺失时立即提示用户，不等到入库时才发现

Phase 1.0（Confluence 知识搜索）:
  └── 搜索 Confluence 中的 PRD/设计文档

Phase 1.0.5（MCP 历史用例查询）:
  └── searchTestCases → historical_cases.json

Phase 1.3（用例生成）:
  └── 整合: 当前需求 + historical_cases + 测试知识库
  └── 冲突检测 → conflicts.md

Phase 3b + 3.5（执行）:
  └── 正常执行，记录 case_execution_log.json

Phase 4（报告生成）:
  └── 测试报告.md

KB_SYNC（用例入库）:
  └── 消费 case_execution_log.json + conflicts.md
  └── createTestCase / updateTestCase / deleteTestCase
  └── 输出 kb_sync_report.json
  └── 删除操作 → 用户确认后执行
```