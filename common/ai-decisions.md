# AI 决策质量保障 — 置信度、可观测性、覆盖度量

> @since v3.4.3 | 2026-05-19

## 定位

定义 AI 在测试各阶段决策的**置信度机制、可观测性日志、测试覆盖度量指标**。
解决 "AI 决策是否可靠"、"如何追溯 AI 判断"、"测试是否充分" 三个核心问题。

---

## 一、决策置信度机制

```yaml
# AI 在关键决策点必须标注置信度等级:
置信度等级:
  HIGH (≥90%):   自主执行，记录决策依据即可
  MEDIUM (70-89%): 执行但记录风险，Phase 4 报告中汇总
  LOW (<70%):    暂停执行，请求人工确认后再继续

关键决策点（必须评估置信度）:
  1. 业务线识别 (Phase 1.0):
     - 从需求文本提取业务线关键词 → 匹配 product-lines.md
     - 单一匹配: HIGH | 多匹配: MEDIUM | 无匹配: LOW
  
  2. 登录页面类型识别 (Phase 0):
     - snapshot 特征匹配 auto-login.md 5 类型
     - 明确匹配: HIGH | 模糊匹配: MEDIUM | 新类型: LOW

  3. 探索发现相关性判断 (Phase 1.4):
     - Q1/Q2/Q3 三问全部明确满足/不满足: HIGH
     - 至少一问判断不确定: MEDIUM → 标记 "待人工确认"
     - 多问不确定: LOW → 暂停并列出问题

  4. 元素定位 (Phase 3b):
     - ref 定位单一匹配: HIGH
     - 多元素同 class → 限定 scope 后单一匹配: MEDIUM
     - 限定 scope 后仍多匹配或找不到: LOW → 申请人工指引

  5. 测试结果判断 (Phase 3b 步骤 6):
     - 预期与实际精确匹配: HIGH
     - 数值相近但偏差 > 5%: MEDIUM（记录偏差值）
     - 预期与实际完全不符: LOW（可能为代码 Bug 或环境问题）

置信度输出:
  每个关键决策点输出:
    { "phase": "1.0", "decision": "business_line", 
      "confidence": "HIGH", "basis": "关键词'ROI报表'→中台", 
      "timestamp": "..." }
```

---

## 二、决策可观测性日志

```yaml
# 每个 Phase 产出的 decisions.jsonl 记录 AI 所有关键决策:

decision_log 格式 (JSONL, 一行一条):
  {"ts":"...","phase":"1.0","decision":"confluence_search","input":"国剧 ROI","confidence":"HIGH","result":"2条相关文档","basis":"searchConfluenceKnowledge返回score>0.6"}
  {"ts":"...","phase":"1.3","decision":"case_priority","input":"TC-001 新增","confidence":"MEDIUM","result":"P0→P1","basis":"功能非核心链路，但涉及数据变更"}
  {"ts":"...","phase":"3a","decision":"skip_exploration","input":"帮助中心链接","confidence":"HIGH","result":"SKIP","basis":"Q1不满足-非业务页面"}
  {"ts":"...","phase":"3b","decision":"element_locate","input":"button:'保存'","confidence":"LOW","result":"BLOCK","basis":"页面有2个'保存'按钮，需限定弹窗作用域"}
  {"ts":"...","phase":"3b","decision":"test_result","input":"TC-PL-003","confidence":"HIGH","result":"PASS","basis":"列表首行含'【测试】验证公司'，DB记录存在"}

决策日志位置: {spec目录}/decisions.jsonl
Phase 4 报告使用:
  - 统计各 Phase 的 LOW 决策数量（需人工介入的决策点）
  - 列出所有 MEDIUM 决策的风险汇总
  - 评估 AI 自主执行的整体可信度
```

---

## 三、测试覆盖度量指标

```yaml
# Phase 4 报告中必须输出的量化覆盖指标:

覆盖度量:
  功能覆盖:
    指标: 功能点覆盖率 = 已覆盖功能点 / 需求识别功能点总数
    目标: ≥ 90%
    计算: 从 Phase 1.2 影响分析提取功能点列表，对照 test_cases.json 统计

  测试类型覆盖:
    指标: 类型覆盖率 = 实际测试类型数 / 基线要求的测试类型数
    基线: 每功能至少 正常流 + 1条异常/边界
    目标: 100%（每个功能点均满足基线）

  页面元素覆盖:
    指标: 元素覆盖率 = 已交互元素 / 探索发现的交互元素总数
    来源: exploration_result.json → elements_found vs Phase 3b 实际交互
    目标: P0/P1 元素 100%，P2 元素 ≥ 50%

  回归覆盖:
    指标: 回归用例命中率 = 有历史来源的用例数 / 用例总数
    来源: Phase 1.0 Confluence 搜索结果数
    目标: 有搜索时 ≥ 20%，无搜索时标注"N/A"

  APP 组合覆盖:
    指标: Core覆盖 / 语言覆盖 / 环境覆盖
    目标: Core 至少 2 个组合，语言至少 2 个，环境至少 2 个

  数据验证覆盖:
    指标: DB验证用例数 / 涉及数据变更的用例数
    目标: ≥ 50%

报告输出格式:
  覆盖度汇总:
    功能覆盖: 8/9 (89%)  ⚠️ 未达标 — "导出功能"未覆盖（用户要求跳过）
    类型覆盖: 9/9 (100%) ✅
    元素覆盖: P0/P1=15/15 (100%) ✅, P2=8/12 (67%) ⚠️
    回归覆盖: 5/20 (25%) ✅ (Confluence命中3条历史需求)
    APP组合: Core=2/5, 语言=2/10, 环境=2/3 ⚠️
    数据验证: 6/10 (60%) ✅
```

---

## 四、置信度联动熔断

```yaml
# 低置信度决策累积也会触发保护:
置信度熔断:
  - Phase 3b 中 LOW 置信度决策 ≥ 3 次 → 暂停执行，提示用户审查
  - 单个用例中 LOW 决策 ≥ 2 次 → 标记用例 SKIP（reason="多次低置信度决策"）
  - MEDIUM 决策累积 ≥ 10 次 → Phase 4 报告中标注"建议人工审查"
```
