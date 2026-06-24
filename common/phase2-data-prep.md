# Phase 2：测试造数与数据准备 — AI 驱动版

## 定位

AI 自主判断需要什么数据、如何获取、如何验证。**不预设造数优先级、不预设 12 种场景**。

## 条件

```yaml
入口条件:
  - Phase 1 已完成（test_cases.json 已生成）
  - 如果 DB 不可达 → 跳过 DB 造数方式，只用 API/UI
  - 如果用例中无数据需求（纯查询验证）→ 跳过 Phase 2

出口条件:
  - 所有前置条件中的数据已就绪 或 已标记无法准备的数据项
  - 输出: data_prep_report.json {status: "ready"|"partial", items_prepared: N, items_skipped: N, skipped_reasons: [...]}
```

## AI 判断框架

```yaml
# AI 在造数时自动执行以下流程：
1. 分析数据需求:
   - 从 Phase 1 生成的用例中提取前置条件
   - 判断：需要什么数据？数据的状态是什么？数据的量级是多少？
   - 示例：需要"一个已登录的 VIP 用户" → 检查是否有现成账号

2. 选择造数方式:
   - AI 按以下优先级尝试，任一步成功即停止：
     a. 检查是否已有现成数据（DB 查询）
     b. 通过 API 创建（最接近真实业务流程）
     c. 通过 DB INSERT 创建（效率最高）
     d. 通过 UI 创建（兜底，最慢）
   - AI 根据当前环境动态选择（API 可用→API，API 不可用→DB，都不行→UI）

3. 验证数据质量:
   - 造数后 AI 自动验证：
     - 数据是否已写入 DB
     - 数据状态是否符合预期
     - 数据是否满足后续用例的前置条件
   - 不满足 → AI 自动修复或重新造数

4. 标记与隔离:
   - 所有测试数据标记 【测试】
   - 记录到内存列表（用于后续清理）
   - 并行执行时使用独立 UUID 隔离
```

## AI 造数决策示例

```yaml
场景: 需要"一个已登录的 VIP 用户"
AI 推理:
  - 检查现有数据: SELECT * FROM users WHERE vip_status=1 LIMIT 1
  - 有现成数据 → 直接使用，跳过造数
  - 无现成数据 → 尝试 API 创建: POST /api/users/create {vip: true}
  - API 不可用 → DB INSERT: INSERT INTO users (..., vip_status=1) VALUES (...)
  - DB 也不可用 → UI 创建: 通过 agent-browser 在管理后台创建

场景: 需要"一个已配置的广告位"
AI 推理:
  - 检查现有数据: SELECT * FROM ad_config WHERE status='active' LIMIT 1
  - 有现成数据 → 直接使用
  - 无现成数据 → 尝试 API 创建
  - API 不可用 → DB INSERT
  - 注意：广告位配置可能影响其他测试 → 标记 【测试】 并在测试完成后清理
```

## AI 清理策略

```yaml
# AI 在测试完成后自动执行：
清理策略:
  - 查询所有标记 【测试】 的数据
  - 按类型分类清理：
    - 配置类数据（广告位/福利包）→ 询问人工确认后再清理
    - 业务类数据（用户/订单/书籍）→ 自动清理
    - 权益类数据（VIP/订阅）→ 恢复原态
  - 清理前输出清理清单
  - 清理后验证数据已恢复
```

---

## Phase 2.5：补充造数（Phase 1.4 完成后触发）

```yaml
触发条件:
  - Phase 1.4 产生了补充用例（supplementary_test_cases.json 非空）
  - 补充用例中有前置条件需要数据（检查每个补充用例的"前置条件"字段）

不触发条件:
  - supplementary_test_cases.json 为空 → 跳过 Phase 2.5
  - 补充用例均为纯查询/验证（无数据依赖）→ 跳过

执行流程:
  1. 解析补充用例的前置条件
  2. 按 Phase 2 的四步造数策略逐项准备数据（检查现有→API→DB→UI）
  3. 输出: supplementary_data_prep_report.json
  4. 合并到 data_prep_report.json 中
```