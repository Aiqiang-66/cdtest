# 交互探索阶段 — 通用骨架

> **定位**：本文件定义交互探索的**通用流程骨架**，适用于 Web/iOS/Android 所有平台。
> 平台差异化细节（元素选择器、交互方式等）由各平台 `exploration.md` 补充。
> 本文档是 `web/exploration.md`、`ios/exploration.md`、`android/exploration.md` 的上游引用。

---

## 一、为什么需要探索阶段

```yaml
Phase 3 执行循环的问题:
  - 循环设计为"逐个执行预定义用例"，不是"探索页面"
  - AI 在决策点判断"下一步做什么"，但不会主动点击所有按钮
  - 如果用例没有写"点击新增按钮"，AI 就不会去点
  - 结果：页面上的"新增"、"编辑"按钮从未被点击，场景缺失

典型场景:
  1. 用例要求"验证列表展示" → AI 只检查列表，不点"新增"
  2. 用例要求"验证搜索功能" → AI 只搜索，不点"编辑"
  3. 用例要求"验证分页" → AI 只翻页，不点"删除"
  4. 结果：新增/编辑/删除场景全部缺失

解决方案:
  在 Phase 3 执行循环之前，增加一个探索阶段:
    - 目标：发现页面上所有交互元素，而不是执行用例
    - 方式：系统性地点击每个按钮、打开每个弹窗、记录每个表单
    - 输出：探索结果（元素清单 + 弹窗字段 + 发现的缺口）
    - 用途：探索结果指导后续用例执行（知道哪些元素可用）
```

---

## 二、探索流程（固定 6 步）

```yaml
探索流程:
  步骤 1: 导航到页面
    - 打开目标页面
    - 等待页面加载完成
    - 获取完整 snapshot

  步骤 2: 识别交互元素
    - 从 snapshot 中找出所有可交互元素
    - 具体元素选择器见各平台 exploration.md（Web 查 DOM 元素，APP 查 UI 控件）
    - 按文本内容分类：
      - 新增类: 包含"新增"/"新建"/"添加"/"创建"/"Add"/"Create"
      - 编辑类: 包含"编辑"/"修改"/"Edit"/"Update"
      - 删除类: 包含"删除"/"移除"/"Delete"/"Remove"
      - 查看类: 包含"查看"/"详情"/"View"/"Detail"
      - 操作类: 其他操作按钮（提交/保存/取消/搜索/刷新）
      - 导航类: Tab/菜单/面包屑

  步骤 3: 探索新增类元素
    - 对每个"新增"按钮：
      a. 点击按钮
      b. 等待弹窗/表单出现（最长 5 秒）
      c. 获取弹窗 snapshot
      d. 记录表单字段（label + type + required）
      e. 检查字段完整性（对照预期字段列表）
      f. 关闭弹窗（点击取消/关闭按钮）
    - 记录结果：弹窗出现？字段完整？有必填标记？

  步骤 4: 探索编辑类元素
    - 对每个"编辑"/"修改"入口：
      a. 点击入口
      b. 等待弹窗/表单出现（最长 5 秒）
      c. 获取弹窗 snapshot
      d. 检查是否有数据回填（input 是否有 value/选中值）
      e. 记录回填数据
      f. 关闭弹窗
    - 记录结果：弹窗出现？有回填数据？回填数据正确？

  步骤 5: 探索删除类元素
    - 对每个"删除"按钮：
      a. 点击按钮
      b. 等待确认弹窗出现（最长 3 秒）
      c. 获取弹窗 snapshot
      d. 记录确认弹窗内容
      e. 点击取消（不真正删除）
    - 记录结果：确认弹窗出现？有取消按钮？

  步骤 6: 探索导航类元素
    - 对每个 Tab/菜单项：
      a. 点击 Tab
      b. 等待内容切换（最长 5 秒）
      c. 获取新内容 snapshot
      d. 记录新内容中的交互元素
      e. 回到步骤 2（递归探索新内容）
    - 限制：递归深度最多 3 层，防止无限循环
```

---

## 三、AI 在探索中的职责

```yaml
AI 的职责:
  1. 识别元素类型:
     - 从 snapshot 中找出所有可交互元素
     - 按文本内容分类（新增/编辑/删除/查看/操作/导航）
     - 判断元素是"导航类"还是"操作类"

  2. 判断弹窗类型:
     - 新增/编辑弹窗 → 记录表单字段
     - 确认弹窗 → 记录确认内容
     - 详情弹窗 → 记录展示数据
     - 错误弹窗 → 记录错误信息

  3. 检查字段完整性:
     - 对照预期字段列表（从需求文档/API 文档提取）
     - 判断：哪些字段在弹窗中？哪些缺失？
     - 记录缺失字段到缺口列表

  4. 判断数据回填:
     - 编辑弹窗中，input 是否有 value？
     - value 是否与列表中的记录一致？
     - 记录回填状态

  5. 记录探索结果:
     - 每个页面的元素清单
     - 每个弹窗的字段清单
     - 发现的缺口（缺失字段/未回填/弹窗不出现）
```

---

## 四、探索结果格式

```yaml
探索结果输出到 exploration_result.json:
{
  "pages": {
    "/path/to/page": {
      "title": "页面标题",
      "in_original_scope": true,  # 该页面是否在初始用例集中
      "elements": {
        "新增类": [
          {"text": "新增X", "type": "button", "explored": true, "modal": true, "fields": ["字段A", "字段B", ...]}
        ],
        "编辑类": [
          {"text": "编辑", "type": "link", "explored": true, "modal": true, "prefilled": true}
        ],
        "删除类": [
          {"text": "删除", "type": "button", "explored": true, "confirm": true}
        ],
        "操作类": [
          {"text": "搜索", "type": "button", "explored": true}
        ],
        "导航类": [
          {"text": "某菜单", "type": "tab", "explored": true, "target_page": "/path/other", "in_original_scope": false}
        ]
      },
      "gaps": [
        {"type": "字段缺失", "description": "弹窗缺少'X'字段"}
      ]
    }
  },
  "discovery_gaps": [
    {
      "type": "未覆盖的页面",
      "page": "/path/new-page",
      "discovered_via": "Tab 导航",
      "reason": "初始用例未覆盖此页面",
      "estimated_impact": "影响说明",
      "supplement_priority": "P1"
    },
    {
      "type": "未覆盖的操作",
      "element": "某操作按钮",
      "parent_page": "/path/to/page",
      "reason": "初始用例未覆盖此场景",
      "supplement_priority": "P1"
    }
  ],
  "summary": {
    "pages_explored": 3,
    "pages_in_original_scope": 2,
    "pages_beyond_scope": 1,
    "elements_found": 15,
    "modals_opened": 4,
    "gaps_found": 2,
    "suggested_supplement_cases": 5
  }
}
```

---

## 五、与 Phase 3 执行循环的关系

```yaml
探索阶段在 Phase 3 执行循环之前执行:
  Phase 2: 造数
    ↓
  Phase 3a: 交互探索 ← 本阶段
    ↓ 输出 exploration_result.json（含 discovery_gaps）
  Phase 1.4: 用例补充
    ↓ AI 消费 exploration_result.json → 生成 supplementary_test_cases.json
    ↓ 合并初始用例 + 补充用例 → 完整用例集
  Phase 3b: 执行循环（使用完整用例集）
    ↓
  Phase 3.5: API 测试

探索结果如何指导执行:
  - 如果探索发现"新增弹窗有 8 个字段" → 执行循环知道要填 8 个字段
  - 如果探索发现"编辑弹窗有回填数据" → 执行循环知道要验证回填
  - 如果探索发现"删除有确认弹窗" → 执行循环知道要处理确认
  - 如果探索发现"某个按钮不存在" → 执行循环跳过该用例

⚠️ 探索结果复用: Phase 3b 使用 exploration_result.json 中已记录的页面结构信息
（弹窗字段布局、按钮位置、加载耗时），避免对已探索过的元素重新做完整探查。
Phase 3b 只验证操作结果，不重复 Phase 3a 的元素发现工作。

探索发现 → 用例补充:
  - 如果探索发现"新增弹窗"但用例集中无新增用例 → 触发 Phase 1.4 补充
  - 如果探索发现新页面/菜单（不在初始用例集中）→ 递归探索该页面 → 触发 Phase 1.4 补充
  - 如果探索发现"编辑"按钮可点击但用例无覆盖 → 补充编辑用例
  - 详细规则见 common/discovery-feedback.md
```

---

## 六、熔断保护

```yaml
探索阶段的熔断:
  时间预算（硬限制）:
    - 单页面总探索时间上限: 10 分钟
    - 单个探索 Phase 3a 总时间上限: 30 分钟
    - 超时后: 停止探索，以已收集结果输出 exploration_result.json

  元素预算（硬限制）:
    - 单页面最多探索 30 个交互元素
    - 超限后: 停止该页面探索，标注"部分探索（已达上限）"

  其他熔断:
    - 单页面探索失败 → 跳过该页面，继续下一个
    - 连续 3 个页面失败 → 暂停探索，输出已收集的结果
    - 单个元素探索超时（>10 秒）→ 跳过该元素，继续下一个
    - 弹窗无法关闭 → 刷新页面，重新探索
    - 页面导航失败 → 标记页面不可达，跳过
    - 发现 5+ 个不在初始范围内的新页面 → 暂停探索，提示用户确认是否全部补充
    - 递归深度超过 3 层 → 停止递归，记录已达最大深度
```

---

## 七、与 bypass-human 的关系

```yaml
探索阶段遇到人工依赖:
  - 如果"新增"按钮需要特定前置数据才能点击 → 记录到缺口
  - 如果"编辑"入口需要列表有数据才能点击 → 先通过 API/DB 造数
  - 如果"删除"按钮需要特定状态才能点击 → 记录到缺口
  - 探索阶段不执行 bypass-human，只记录缺口
  - bypass-human 在 Phase 3 执行循环中处理
```

---

## 八、探索发现 → 用例补充反馈链路

```yaml
反馈链路:
  探索阶段完成 → 输出 exploration_result.json
    ↓
  AI 检查 discovery_gaps 数组:
    - gaps 为空 → 无遗漏，直接进入 Phase 3b 执行循环
    - gaps 非空 → 进入 Phase 1.4 用例补充
    ↓
  Phase 1.4 补充:
    - 消费 exploration_result.json 中的 discovery_gaps
    - 逐条生成补充用例（标注"来源依据 = 探索发现"）
    - 输出 supplementary_test_cases.json
    ↓
  合并用例集:
    - test_cases.json（初始） + supplementary_test_cases.json（补充）
    - 去重：功能重叠的用例合并为更详细的那条
    ↓
  进入 Phase 3b 执行循环（使用完整用例集）

引用:
  - 补充规则详细定义见 common/discovery-feedback.md
  - Phase 1.4 补充模式见 common/phase1-analyze.md § Phase 1.4
```

---

## 九、平台适配

```yaml
# 各平台 exploration.md 需要覆盖的差异化内容：
平台适配点:
  Web:
    - 元素选择器: button / a / [role=button] / [role=tab] / input[type=submit]
    - 交互方式: agent-browser click / eval JS
    - 加载判断: DOM 变化 / 网络请求完成
    - 详见: web/exploration.md

  iOS:
    - 元素选择器: XCUIElementTypeButton / XCUIElementTypeCell / accessibilityLabel
    - 交互方式: Appium tap / swipe
    - 加载判断: 控件可见性 / 页面标题变化
    - 详见: ios/exploration.md

  Android:
    - 元素选择器: android.widget.Button / content-desc / resource-id
    - 交互方式: Appium tap / swipe
    - 加载判断: 控件可见性 / Activity 切换
    - 详见: android/exploration.md
```

---

## 十、跨系统关联发现（🔴 对内变更必须考虑对外影响）

```yaml
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 问题: 探索阶段只检查当前系统页面，不会主动发现"对外系统"
#   例: 对内剧目表有新增/下架功能 → 对外剧目表需要验证同步
#   但探索阶段不会去打开对外系统，导致 E2E 场景在用例设计时就遗漏了
#
# 解决: 探索阶段追加一步"跨系统关联检查"
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

步骤 7: 跨系统关联检查（在步骤 6 之后执行）:

  7a: 识别跨系统信号:
    → 当前系统是否有"对外"相关菜单？（如 对外剧目表/对外分销结算）
    → 数据模型是否有"对外可见"字段？（如 external_show_time, shelf_status）
    → 需求文档是否提及"同步"、"外部"、"下游系统"？

  7b: 如果存在任一信号 → 🔴 必须触发 E2E 用例补充:
    → 新增 E2E 验证用例到 discovery_gaps:
      - 对内新增 → 对外可见
      - 对内修改 → 对外同步
      - 对内下架 → 对外不可见
    → 标记 discovery_gap.type = "cross_system"

  7c: 记录到 exploration_result.json:
    "cross_system": {
      "detected": true,
      "external_systems": ["对外剧目表", "对外分销结算"],
      "propagation_fields": ["shelf_status", "external_show_time"],
      "generated_e2e_cases": ["TC-E2E-001", "TC-E2E-002"]
    }

⚠️ 如果没有检测到跨系统信号 → 标记 "cross_system.detected": false 并记录原因
⚠️ 如果检测到但对外 API 不可达 → 标记为 SKIP 并记录到 risk_items
```