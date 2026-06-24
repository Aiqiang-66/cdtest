# Phase 4：智能报告生成 — 混合驱动版

## 定位

**固定骨架 + AI 填充**。报告需要一致性（利益相关者需要快速定位信息），AI 填充内容而非设计结构。

---

## 一、固定报告骨架（不可跳过）

```yaml
报告骨架:
  1. 标题 + 概览
     - 项目名 / 版本 / 日期
     - 通过率 / 总数 / 通过 / 失败 / 跳过
     - 总耗时
     - AI 一句话总结

  2. 测试范围
     - 覆盖的模块列表
     - 覆盖的功能点列表
     - 未覆盖的功能（如有）

  3. 执行结果明细
     - 用例 ID | 模块 | 步骤 | 预期 | 实际 | 结论 | 截图 | 耗时
     - 按模块分组

  4. 失败分析
     - 失败用例 ID | 失败原因 | AI 根因分析 | 建议

  5. 截图索引
     - 截图文件名 | 截图时机 | 关联用例

  6. 结论 + 建议
     - 结论: 建议上线 / 修复后上线 / 不建议上线
     - 建议: 具体修复方向 + 优先级
```

## 二、AI 填充内容

```yaml
# AI 在固定骨架中填充以下内容：
AI 填充:
  概览:
    - AI 总结关键数据（"12/12 通过，全部 PASS"）
    - AI 一句话总结（"本次测试覆盖了开票系统的核心链路，无阻塞问题"）

  失败分析:
    - AI 分析每个失败用例的根因
    - AI 给出修复建议
    - AI 区分：环境问题 vs 数据问题 vs 代码 Bug

  结论:
    - AI 综合评估：通过率 + P0/P1 覆盖 + DB 验证 + API 测试
    - AI 风险评估：未覆盖的功能 + 未通过的用例 + 环境问题
    - AI 建议：上线 / 修复后上线 / 不建议上线

  截图:
    - AI 从所有截图中选择关键截图插入报告
    - AI 为截图生成有意义的描述
```

## 三、AI 报告示例

```yaml
# 全部通过 → AI 填充简洁内容：
报告:
  标题: "测试报告 — 开票系统 v2.3"
  日期: "2026-05-14"
  概览:
    通过率: "100% (12/12)"
    总耗时: "15m 32s"
    AI 总结: "本次测试覆盖了开票系统的全部核心链路，所有用例通过"
  测试范围:
    - 模块: "发票创建" (5 用例)
    - 模块: "发票审核" (4 用例)
    - 模块: "发票作废" (3 用例)
  失败分析: "无"
  结论: "建议上线"

# 有失败 → AI 填充详细分析：
报告:
  标题: "测试报告 — 开票系统 v2.3"
  日期: "2026-05-14"
  概览:
    通过率: "83% (10/12)"
    总耗时: "18m 45s"
    AI 总结: "2 个用例失败，均为数据前置条件问题"
  失败分析:
    - 用例: TC-PI-003
      失败原因: "断言失败: 预期状态=已审核，实际状态=待审核"
      AI 根因分析: "数据问题：前置条件中的审批流程未完成，导致状态未流转"
      建议: "修复造数逻辑，确保审批流程完成后再验证状态"
    - 用例: TC-CA-005
      失败原因: "API 返回 500"
      AI 根因分析: "环境问题：服务端版本 10320 存在已知 Bug，升级到 10321 后修复"
      建议: "升级服务端版本后重新测试"
  结论: "修复后上线"
```

## 四、AI 截图决策

```yaml
# 固定必截图场景 + AI 额外截图判断：
必截图场景（固定）:
  - 操作涉及数据变更（新增/修改/删除/状态流转）
  - 用例失败
  - 异常发生（弹窗/闪退/错误页面）
  - 登录成功/失败

AI 额外判断:
  - 操作涉及 UI 布局变化 → 建议截图
  - 操作仅导航/滚动/筛选 → 不截图
  - 操作结果有歧义 → 截图供人工确认
```

## 五、AI 日志级别

```yaml
# 固定日志级别：
日志级别:
  - INFO: 正常操作记录
  - WARN: 可能有问题但不影响当前执行
  - ERROR: 失败需要关注
  - RECOVER: 执行了恢复操作
  - CIRCUIT: 触发了熔断
```

---

## 六、结构化执行日志（测试结果可追溯）

> **定位**：每次执行产生 `case_execution_log.json`，AI 从中提取数据生成报告 §三 执行结果明细。
> 日志需包含每个用例执行过程的完整记录，确保任意一条结果可追溯到具体操作步骤和 AI 决策。

### 日志格式

```yaml
# execution_log.json → case_execution_log.json — 每条用例的执行记录：
execution_log.json:
  {
    "run_id": "run-20260515-143022",
    "started_at": "2026-05-15T14:30:22+08:00",
    "finished_at": "2026-05-15T14:48:54+08:00",
    "environment": {
      "url": "https://test.example.com",
      "browser": "Chrome",
      "resolution": "1920x1080",
      "token_source": "auto-login.md priority-1",
      "token_valid": true
    },
    "cases": [
      {
        "case_id": "TC-PI-001",
        "status": "PASS",            # PASS | FAIL | SKIP | BLOCKED
        "started_at": "2026-05-15T14:30:22+08:00",
        "finished_at": "2026-05-15T14:31:05+08:00",
        "duration_ms": 43000,
        "retries": 0,                # 重试次数

        "steps": [
          {
            "seq": 1,
            "action": "navigate",     # navigate | click | fill | select | snapshot | verify | eval
            "target": "https://test.example.com/distribution/partner-invoice-info",
            "timestamp": "2026-05-15T14:30:22+08:00",
            "screenshot": "TC-PI-001_step1_navigate.png",
            "result": "OK",
            "duration_ms": 2200
          },
          {
            "seq": 2,
            "action": "click",
            "target": "@ref=e47",     # 元素引用
            "target_text": "新增付款单位",
            "timestamp": "2026-05-15T14:30:25+08:00",
            "screenshot": "TC-PI-001_step2_click.png",
            "result": "OK",
            "effect": "modal_opened",  # 操作效果
            "duration_ms": 800
          },
          {
            "seq": 3,
            "action": "fill",
            "target": "input[name='companyName']",
            "value": "【测试】验证公司",
            "timestamp": "2026-05-15T14:30:27+08:00",
            "screenshot": null,         # 连续 fill 不单独截图
            "result": "OK",
            "duration_ms": 500
          },
          {
            "seq": 4,
            "action": "click",
            "target": "@ref=e89",
            "target_text": "保存",
            "timestamp": "2026-05-15T14:30:30+08:00",
            "screenshot": "TC-PI-001_step4_save.png",
            "result": "OK",
            "effect": "modal_closed, list_updated",
            "duration_ms": 600
          },
          {
            "seq": 5,
            "action": "verify",
            "check": "列表首行含名称'【测试】验证公司'",
            "timestamp": "2026-05-15T14:30:32+08:00",
            "screenshot": "TC-PI-001_step5_verify.png",
            "result": "PASS",
            "actual": "列表首行文本='【测试】验证公司'",
            "duration_ms": 1500
          }
        ],

        "ai_decisions": [             # AI 关键决策点
          {
            "point": "step2_element_location",
            "decision": "通过文本'新增付款单位'定位按钮 @ref=e47",
            "alternatives": ["@ref=e12"],
            "timestamp": "2026-05-15T14:30:24+08:00"
          }
        ],

        "errors": [],                 # 失败时的错误详情
        "data_used": {                # 使用的测试数据
          "company_name": "【测试】验证公司",
          "account": "622202..."
        },
        "data_produced": null         # 产生的数据（供后续依赖用例使用）
      },
      {
        "case_id": "TC-CA-005",
        "status": "FAIL",
        "started_at": "2026-05-15T14:35:00+08:00",
        "finished_at": "2026-05-15T14:35:12+08:00",
        "duration_ms": 12000,
        "retries": 2,

        "steps": [
          {
            "seq": 1,
            "action": "click",
            "target": "@ref=e120",
            "target_text": "计算开票金额",
            "timestamp": "2026-05-15T14:35:01+08:00",
            "result": "ERROR",
            "duration_ms": 500
          }
        ],

        "errors": [
          {
            "step": 1,
            "type": "ELEMENT_NOT_FOUND",
            "message": "snapshot 中未找到'计算开票金额'按钮",
            "retry_attempts": [
              {"attempt": 1, "action": "re-snapshot", "result": "still not found"},
              {"attempt": 2, "action": "scroll page, re-snapshot", "result": "still not found"}
            ],
            "ai_analysis": "按钮可能因权限/数据状态未显示，非环境问题"
          }
        ],

        "ai_decisions": [],
        "data_used": {},
        "data_produced": null
      }
    ],

    "summary": {
      "total": 16,
      "passed": 13,
      "failed": 1,
      "skipped": 2,
      "blocked": 0,
      "total_duration_ms": 1112000,
      "retries_total": 5
    }
  }
```

### AI 从日志生成报告的规则

```yaml
# AI 读取 execution_log.json 自动生成报告 §三 执行结果明细：
报告生成规则:
  执行结果明细:
    来源: cases[].case_id + status + duration_ms + steps[-1].actual
    格式: 用例 ID | 状态 | 耗时 | 最后一步验证结果 | 截图列表

  失败分析:
    来源: cases[status=FAIL].errors[]
    提取: error.type + error.message + error.ai_analysis
    格式: 用例 ID | 失败类型 | 失败描述 | AI 根因分析 | 重试次数

  截图索引:
    来源: cases[].steps[screenshot!=null]
    格式: 截图文件名 | 步骤序号 | 操作描述 | 关联用例

  追溯能力:
    - 每条 PASS/FAIL 可追溯到具体步骤（seq N）
    - 每次重试有完整记录（retry_attempts）
    - 每个 AI 决策有记录（ai_decisions）
    - 产生/消费的数据有记录（data_used / data_produced）
```

---

## 七、测试用例知识库同步（KB_SYNC 阶段）

> **定位**：Phase 4 报告生成后执行，将本次测试的正确用例同步到 MCP 测试用例知识库。
> 详细规则见 `common/mcp-kb-sync.md §五`。

### 触发条件

```yaml
触发:
  - Phase 3b + Phase 3.5 均已完成
  - MCP Test Case Server 可用（getTestCaseStatus.configured = true）
  - requirement_meta.json 中 system + requirementVersion 已确定

跳过:
  - 设计模式（无执行结果）
  - MCP 不可用 → 记录到报告 "用例知识库不可用，跳过入库同步"
  - requirement_meta 不完整 → 提示用户补充后重新触发
```

### 同步流程

```yaml
1. 筛选待入库用例:
   - 从 case_execution_log.json 中筛选 status=PASS 的用例
   - 按以下条件分类:
     * 来源为"当前新需求"且历史不存在 → createTestCase
     * 历史已存在（同 caseName+system+module）→ updateTestCase
     * 历史已存在且内容无变化 → 跳过
     * status=FAIL/SKIP/BLOCKED → 跳过，不入库

2. 筛选待删除用例:
   - 仅对 conflicts.md 中用户确认"采用新版本"的冲突用例
   - 删除前必须列出清单 → 用户确认后执行
   - 原因说明: "历史用例逻辑已被当前需求推翻，用户确认删除"

3. 执行入库:
   - 参数映射见 common/mcp-kb-sync.md §五
   - 批量执行: 每批次 ≤ 50 条，间隔 2 秒
   - 失败重试: 单条最多重试 1 次
   - 连续 5 条失败 → 暂停检查 MCP 连接

4. 输出 kb_sync_report.json

5. 安全规则:
   - 删除操作必须用户确认
   - FAIL 的用例不入库（避免覆盖历史有效用例）
   - 入库失败不阻塞报告生成
```