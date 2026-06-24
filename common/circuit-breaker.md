# 熔断保护机制 — 混合驱动版

## 定位

**固定基准 + AI 调整**。熔断需要明确的基准阈值保证可靠性，AI 在基准范围内动态调整。

---

## 一、固定基准（不可跳过）

```yaml
熔断基准:
  连续失败阈值: 5 次
  冷却时间: 5 分钟
  探测间隔: 30 秒
  最大冷却时间: 30 分钟

连续失败定义:
  - 同一 Phase 3b 执行会话内
  - 跨用例的连续失败（中间无 PASS 则继续累积）
  - Phase 3b 重启后重置计数
  - Phase 1.4 补充后不重置（补充用例可能复用失败环境）
```

## 二、AI 动态调整（在范围内）

```yaml
# AI 根据失败模式在基准范围内调整：
AI 调整规则:
  连续失败阈值: 3~8 次
    - 环境错误（503/设备断开/网络不可达）→ 阈值降为 3 次（立即熔断）
    - Token 过期（401）→ 自动重新走 auto-login.md Token 提取链，不计入连续失败
    - 断言失败（业务逻辑不符）→ 阈值保持 5 次
    - 元素未找到（UI 变化）→ 阈值升为 8 次（可能只是页面加载慢）

  冷却时间: 3~15 分钟
    - 失败原因明确（如环境问题）→ 冷却时间 × 1.5
    - 失败原因不明 → 冷却时间不变，等待探测
    - 连续 3 次探测成功 → 冷却时间重置为基准值
    - 历史平均冷却成功率 < 70% → 提示用户检查环境
    调整范围: 3-15 分钟（上下限保护）

  探测用例选择:
    - AI 选择"当前环境下最可能通过的用例"
    - 优先选择不依赖失败模块的用例
    - 优先选择 P2/P3 用例（失败影响小）
```

## 三、熔断状态机

```
正常执行
  ↓ AI 检测到连续失败 ≥ 阈值
熔断（记录失败模式 + 开始冷却）
  ↓ 冷却时间到
探测（执行 AI 选择的探测用例）
  ├─ 探测通过 → 恢复执行（重置失败计数）
  └─ 探测失败 → 继续熔断（冷却时间翻倍，最多 30 分钟）
       └─ 冷却时间到 → 再次探测
            ├─ 通过 → 恢复
            └─ 失败 → AI 评估：继续冷却 or 终止执行

探测用例执行方式:
  - 探测用例走简化的 4 步验证（非完整 8 步循环）:
    步骤 P1: 导航到目标页面
    步骤 P2: 执行关键操作（如点击导航菜单 / 输入简单搜索词）
    步骤 P3: 验证结果（只检查核心信号：页面加载 / 数据出现 / 无报错）
    步骤 P4: 记录 PASS/FAIL
  - 探测用例不计入失败统计（避免循环加深熔断）
  - 探测失败不触发新的熔断（只影响冷却时间）
  - 探测超时: 3 分钟 → 视为失败

剩余用例处理:
  - 探测通过: 从队列中恢复执行剩余用例
  - 探测失败 × 1: 继续冷却，剩余用例保持 PENDING
  - 探测失败 × 2: 剩余未执行用例全部标记 SKIP（reason="熔断未恢复"）
  - 探测失败 × 3+: 终止执行，剩余用例标记 SKIP，进入 Phase 4 报告
```

## 四、AI 日志

```yaml
# AI 在熔断时输出结构化日志：
日志格式:
  - 触发: "连续失败 {n} 次（阈值 {threshold}），失败模式={mode}"
  - 决策: "熔断 {cooling} 分钟"
  - 探测: "选择 {case_id}（原因：{reason}）"
  - 结果: "探测通过/失败 → 恢复/继续冷却"
```

---

## 五、探测成功率统计

> **定位**：记录每次探测的结果，按失败模式和探测用例类型统计成功率，供 AI 优化未来的探测用例选择。

### 探测历史格式

```yaml
# probe_history.json — 每次熔断探测的记录：
probe_history.json:
  {
    "probes": [
      {
        "id": "probe-001",
        "timestamp": "2026-05-15T14:30:00+08:00",
        "trigger": {
          "consecutive_failures": 5,
          "threshold": 5,
          "failure_mode": "ASSERTION_FAILED",
          "failed_cases": ["TC-PI-003", "TC-PI-004", "TC-PI-005", "TC-PI-006", "TC-PI-007"]
        },
        "probe_case": {
          "case_id": "TC-NAV-001",
          "priority": "P2",
          "module": "导航",
          "selection_reason": "不依赖失败模块，纯页面导航验证"
        },
        "result": "PASS",
        "cooling_before_probe_ms": 300000,
        "recovery": true
      },
      {
        "id": "probe-002",
        "timestamp": "2026-05-15T14:45:00+08:00",
        "trigger": {
          "consecutive_failures": 3,
          "threshold": 3,
          "failure_mode": "ENV_ERROR",
          "failed_cases": ["TC-PL-001", "TC-PL-002", "TC-PL-003"]
        },
        "probe_case": {
          "case_id": "TC-PL-004",
          "priority": "P2",
          "module": "列表页",
          "selection_reason": "同模块 P2 用例，验证环境是否恢复"
        },
        "result": "FAIL",
        "cooling_before_probe_ms": 900000,
        "recovery": false,
        "follow_up": "冷却时间翻倍至 30min，下次探测选择不同模块"
      }
    ],

    "statistics": {
      "total_probes": 8,
      "total_recoveries": 6,
      "overall_success_rate": 0.75,

      "by_failure_mode": {
        "ASSERTION_FAILED": {
          "count": 3,
          "recoveries": 3,
          "success_rate": 1.0,
          "avg_cooling_ms": 300000
        },
        "ENV_ERROR": {
          "count": 3,
          "recoveries": 1,
          "success_rate": 0.33,
          "avg_cooling_ms": 900000
        },
        "ELEMENT_NOT_FOUND": {
          "count": 2,
          "recoveries": 2,
          "success_rate": 1.0,
          "avg_cooling_ms": 300000
        }
      },

      "by_probe_priority": {
        "P0": {"count": 1, "success_rate": 0.0},
        "P1": {"count": 2, "success_rate": 0.5},
        "P2": {"count": 4, "success_rate": 1.0},
        "P3": {"count": 1, "success_rate": 1.0}
      },

      "by_probe_module_relation": {
        "same_module": {"count": 5, "success_rate": 0.6},
        "different_module": {"count": 3, "success_rate": 1.0}
      }
    }
  }
```

### AI 如何利用统计数据优化探测选择

```yaml
# AI 在选择探测用例时，参考历史统计数据：
AI 优化规则:
  1. 模块选择:
     - different_module 成功率更高 → 优先选择不同模块的用例作为探测
     - same_module 成功率低 → 降级为备选

  2. 优先级选择:
     - P2/P3 成功率最高 → 优先用 P2/P3 作为探测（风险低）
     - P0 成功率最低 → 避免用 P0 探测（失败代价大）
     - 如果 P0 是唯一可用探测 → 可以选，但要记录风险

  3. 冷却时间预估:
     - ENV_ERROR 平均冷却 900s → 环境问题首次冷却直接用 15min
     - ASSERTION_FAILED 平均冷却 300s → 断言失败用 5min 即可
     - 避免固定 5min → 根据历史数据动态设置

  4. 连续失败预警:
     - 如果当前失败模式的历史成功率 < 0.5:
       → 提前通知用户"此失败模式历史恢复率低，建议人工介入"
     - 如果同模块探测连续 2 次失败:
       → 自动切换为不同模块探测

  5. 统计更新:
     - 每次探测完成后自动更新 probe_history.json
     - AI 重新计算 statistics 字段
     - 统计数据跨 session 保留，但仅保留最近 50 条探测记录
     - 超过 50 条时: 滚动删除最早记录，statistics 使用全量历史做聚合统计
     - 聚合统计（by_failure_mode/by_probe_priority 等）基于全量历史计算，不受记录裁剪影响
```