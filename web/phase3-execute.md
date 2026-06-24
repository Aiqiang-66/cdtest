# Web 执行引擎 — 混合驱动版（含交互探索）

## 定位

**两阶段执行**：先执行交互探索（发现所有页面元素），再执行用例循环（验证具体功能）。

探查策略、等待策略、加载判断等详细优化见 `common/execution-optimization.md`。
交互探索详细流程见 `web/exploration.md`（通用骨架见 `common/exploration.md`）。
探索发现→用例补充反馈链路见 `common/discovery-feedback.md`。
Phase 1.4 用例补充模式见 `common/phase1-analyze.md`。

---

## 〇、执行顺序：Phase 3b 与 Phase 3.5 的调度建议

```yaml
# ⚠️ 当前无并行任务工具支持，以下为建议调度策略，非硬性并行要求。
# AI 按依赖关系选择合适的执行顺序即可。
```

---

## 〇.五、交互探索阶段（先于执行循环）

```yaml
# 在执行测试用例之前，先系统性地探索页面上的所有交互元素
# 目的：发现"新增"、"编辑"、"删除"等被用例遗漏的场景
# 通用流程见 common/exploration.md，Web 平台细节见 web/exploration.md

执行顺序:
  Phase 2: 造数
    ↓
  Phase 3a: 交互探索 ← 本阶段
    ↓ 输出 exploration_result.json（含 discovery_gaps）
  Phase 1.4: 用例补充 ← AI 消费 discovery_gaps → 生成补充用例
    ↓ 合并 test_cases.json = 初始 + 补充
  Phase 3b + Phase 3.5: 执行 ← 按 §〇 策略决定并行/串行

关键发现处理:
  - 发现新菜单/页面 → 递归探索（深度≤3）→ 记录到 discovery_gaps → 触发 Phase 1.4
  - 发现遗漏的 CRUD 操作 → 记录到 discovery_gaps → 触发 Phase 1.4
  - 发现 5+ 个新页面 → 暂停，提示用户确认
```

---

## 一、固定执行循环（不可跳过）

```yaml
# 每个用例按以下循环执行：
执行循环:
  步骤 0: 检查熔断状态（每个用例开始前必须执行）:
    - 读取 circuit-breaker.md 熔断状态
    - 如果当前处于熔断状态 → 不执行当前用例，等待冷却或标记 SKIP
    - 如果处于探测模式 → 当前用例作为探测用例，走简化验证
    - 正常模式 → 继续
    → 详细规则见 common/circuit-breaker.md §三 状态机

  步骤 1: 探查页面 → 获取当前页面 snapshot（探查策略见 execution-optimization.md §一）
  步骤 2: AI 理解页面 → 判断当前页面是什么
  步骤 3: AI 选择操作 → 根据用例步骤选择操作
  步骤 4: 执行操作 → click / fill / select / upload
  步骤 5: 等待响应 → 等待页面变化（等待策略见 execution-optimization.md §二）
  步骤 6: 验证结果 → 探查页面验证（加载判断见 execution-optimization.md §三）
  步骤 7: 记录结果 → PASS/FAIL + 截图
     → 将结果反馈给熔断器（circuit-breaker.md）
  步骤 8: 下一个用例 → 回到步骤 0

# ⚠️ 执行过程中的知识库引用（每步可选）：
#   - 执行输入框操作时：引用 `common/测试知识库.md` §1.1~1.5 验证输入值
#   - 执行增删改查时：引用 `common/测试知识库.md` §2.1 检查成功/失败提示、重复限制
#   - 翻页操作后：引用 `common/测试知识库.md` §2.2 验证分页控件状态
#   - 操作异常时：引用 `common/测试知识库.md` §8 检查错误页面是否友好
```

---

## 二、AI 决策点

```yaml
# AI 在循环中的决策点：
决策点 1（步骤 2）: 理解页面
  - 当前页面是什么？（列表页/表单页/详情页/弹窗）
  - 页面是否加载完成？（参考 execution-optimization.md §三 加载信号）
  - 是否有异常？（错误提示/弹窗/空白页）

决策点 2（步骤 3）: 选择操作
  - 根据用例步骤在 snapshot 中找到目标元素
  - 通过元素文本/属性/位置定位
  - 选择操作类型（click/fill/select/upload）
  - 判断是否可以合并探查（参考 execution-optimization.md §一 探查触发条件）

决策点 3（步骤 5）: 等待响应
  - 根据操作类型选择等待策略（参考 execution-optimization.md §二 等待策略）
  - 根据页面复杂度/网络状况调整等待时间
  - 超时 → 高成本探查 → 判断是否继续等待

决策点 4（步骤 6）: 验证结果
  - 页面是否跳转到预期页面？
  - 是否出现预期元素/文本？
  - 是否有错误提示？
  - 参考 execution-optimization.md §三 加载完成判断
```

## 二.五、配置测试专项——"改完即还"检查点

### 问题

筛选配置、表头配置、显示选项等配置项修改后**持久化保存**，
如果不及时恢复，后续所有测试都在"残缺配置"环境下执行，结果不可信。

### 强制流程

```yaml
# 每条配置修改测试必须遵守以下循环：
配置测试循环（"改→验→还→验"）:
  步骤 1: 改前快照（记录当前配置状态）
    - 筛选配置: snapshot 记录当前页面上展示了哪些筛选器
      → 快速检查: eval "检查 filter labels 列表"
    - 表头配置: snapshot 记录当前表格有哪些 columnheader
      → 快速检查: eval "检查 columnheader 列表"
    - 显示选项: 记录三个 checkbox 的 checked 状态
      → 快速检查: eval "检查三个 checkbox"

  步骤 2: 执行修改测试
    - 打开对应弹窗 → 取消/勾选目标项 → 点击保存
    - 验证修改效果:
      ✅ 筛选器消失/出现
      ✅ 表格列消失/出现
      ✅ checkbox 状态变化

  步骤 3: 恢复修改（立即执行，不可跳过）
    - 重新打开对应弹窗
    - 将被修改的选项恢复为步骤 1 记录的状态
    - 点击保存
    
    恢复方式（按优先级）:
      a) UI 操作恢复: 打开弹窗 → 点击对应项 → 保存（推荐，最可靠）
      b) eval JS 恢复: 直接设置 checkbox.checked + 触发保存（回退方案）

  步骤 4: 验证恢复
    - 检查页面配置是否恢复到步骤 1 的状态
    - 筛选器数量/类型一致 ✅
    - 表头列数量/文本一致 ✅
    - checkbox 状态一致 ✅
```

### 多条配置测试的执行策略

```yaml
# 如果有 3 条配置测试项（如 A、B、C），按顺序逐一执行：

✅ 正确顺序:
  测试 A: 改→验→还→验
  测试 B: 改→验→还→验
  测试 C: 改→验→还→验

❌ 错误顺序（禁止）:
  测试 A: 改→验
  测试 B: 改→验（在 A 的修改基础上，状态叠加）
  测试 C: 改→验
  最后才恢复 → 丢失中间状态，无法确认恢复结果
```

### 配置测试的验证清单

```yaml
筛选配置验证:
  - 取消"短剧"后 → 页面上短剧筛选器消失
  - 取消"D7 ROI"后 → 页面上D7 ROI筛选器消失
  - 取消"平均CPM"后 → 页面上CPM筛选器消失
  - 全部恢复后 → 检查筛选器数量是否为 7 个（分析维度、日期、短剧、代理商、D7ROI、消耗、CPM）

表头配置验证:
  - 取消"平均点击单价"后 → 表格中该列消失
  - 取消"总展示数"后 → 表格中该列消失
  - 全部恢复后 → 检查表头列数是否为 16 列

显示选项验证:
  - "显示筛选"取消 → 所有筛选器消失（分析维度/日期/下拉框/spinbutton）
  - "显示筛选"恢复 → 筛选器重新出现
  - "首次进入加载列表"勾选 → 页面自动触发查询
```

---

## 三、元素交互模式（操作 → 验证 → 适应循环）

```yaml
# 核心原则: 每次操作后必须 snapshot 验证，不通过则换方式重试。

# ⚠️ 弹窗作用域规则（最高优先级，违反即导致错误操作）:
弹窗作用域规则:
  当页面上存在可见弹窗（dialog/modal）时:
    1. 必须先在 snapshot 中确认弹窗的存在和标题
    2. 所有元素查找必须限定在弹窗 DOM 范围内
    3. 禁止使用全局 document.querySelector(...) 查找弹窗内的元素
       → 原因: 搜索区/其他弹窗可能有同名 class 的元素
    
    正确模式（主页面弹窗）:
      const dialog = document.querySelector('.el-dialog__wrapper:not([style*="display:none"]) .el-dialog');
      const target = dialog.querySelector('.target-selector');
    
    # ⛔ 禁止: 用 eval 操作 iframe 内元素（agent-browser 无法直接操作 iframe）
    # ✅ 正确: 如果弹窗在 iframe 内 → 提取 iframe src → 新标签页打开 → 标准 snapshot-ref 流程
    # 详见 common/execution-optimization.md §场景 8
    
    查找前验证歧义:
      const allMatches = document.querySelectorAll('.target-class');
      if (allMatches.length > 1) {
        // 有歧义! 必须通过 dialog 限定范围!
      }

固定循环:
  1. 操作: click / fill / select / check / upload
  2. 快照: snapshot（弹窗操作后必须检查弹窗是否仍存在）
  3. 验证: AI 自问"操作成功了吗？元素/页面状态变了吗？"
     - click → 弹窗出现了？页面跳转了？元素状态变了？
     - fill → 输入框的值是填入的文本吗？
     - select → combobox 显示的文本变成目标值了吗？
     - check → checked 状态变了吗？
     - upload → 文件名出现在页面上了吗？input.files.length > 0？
  4. 适应: 验证失败 → 分析原因 → 换方式重试
     
     ⚠️ 重试层级（按顺序，每层最多 2 次）:
       层级 1: DOM click（修正作用域后重试）
       层级 2: Vue 实例方法（c.__vue__.select() / c.__vue__.model.xxx = yyy）
       层级 3: Form Model 直接赋值（form.__vue__.model.field = value）
       层级 4: 放弃 → 标记 SKIP + 跳到下一条独立用例
     
     ⚠️ 防卡死:
       - 同一操作失败 3 次后 → 不再重试，按 interaction-hierarchy 升级
       - 总交互次数 > 8 次 → 强制跳过
       - 单步骤耗时 > 3 分钟 → 强制跳过
       - 详细规则见 common/execution-optimization.md §场景 13~14
     
  5. 结果: 通过 → 继续下一步 | 强制跳过 → 标记 SKIP + 继续下一条用例

AI 职责:
  - 每次操作后必须 snapshot + 自行判断成功与否
  - 失败时思考原因而不是机械重试相同操作
  - 知道哪些操作可以合并验证（连续 fill 多个字段 → 一次 snapshot）
  - ⚠️ 遇到弹窗时，第一反应必须是"限定范围"，不是"直接查找"
  - ⚠️ 检测到操作的是错误元素（如同名但不同位置的元素）→ 立即反思作用域
```

## 三、agent-browser 执行规范（必须严格执行）

```yaml
# agent-browser 在 Windows/PowerShell 下的执行规范：
# ⚠️ 核心原则：先 snapshot 取 ref，再用 ref 操作

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔴 模态上下文规则（最高优先级，违反即造成数据错误）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 当页面存在 visible modal/dialog 时，以下命令会自动匹配 DOM 中第一个
# 符合条件的元素，而这个元素往往在列表页搜索区而非弹窗内：
#
#   ❌ agent-browser type "input[placeholder='输入短剧名称']" "xxx"
#      → 匹配到列表页搜索框，数据填入错误位置
#   ❌ agent-browser fill "input[placeholder='例如：XC01']" "xxx"
#      → 匹配到列表页代号搜索框
#   ❌ agent-browser click "button:text('查 询')"
#      → 匹配到列表页查询按钮而非弹窗内按钮
#
# ✅ 弹窗内操作的正确方式（三选一，按优先级）:
#
#   方式 1 — snapshot ref（首选，最安全）:
#     agent-browser snapshot -i -c -d 4 --json
#     → 从输出中找到弹窗内的 textbox ref（如 @e168）
#     agent-browser type "@e168" "测试数据"
#
#   方式 2 — eval 聚焦 + keyboard type（Ant Design 必用）:
#     agent-browser eval "document.querySelector('.ant-modal input[placeholder='输入短剧名称']')?.focus()"
#     agent-browser keyboard type "测试数据"
#
#   方式 3 — type/fill 命令 + .ant-modal 限定（仅 input 有唯一 id 时可用）:
#     agent-browser type ".ant-modal input#storyCode" "YSJ001"
#     # 注意：type 不支持属性选择器嵌套，此时必须用方式 2
#
# 🔴 任何 type/fill/click 命令执行前，必须先问自己：
#   "当前有弹窗打开吗？这个选择器会匹配到弹窗外的元素吗？"
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

操作优先级（从高到低）:
  1. snapshot ref（首选，加双引号后用）
     agent-browser click "@e61"
     agent-browser type "@e168" "TCDN-TYPE"
     agent-browser fill "@e169" "测试名称"
     agent-browser get text "@e1"
     # ⚠️ 必须先 snapshot 拿到 ref 才能使用
     # ⚠️ 弹窗/页面切换后 ref 会变，必须重新 snapshot

  2. find role ... click --name（语义化，适合英文按钮/固定角色）
     agent-browser find role button click --name "查 询"
     # 注意：中文按钮名匹配不稳定

  3. eval + CSS 选择器（兜底 fallback，只在 ref/find 都失败时使用）
     agent-browser eval "document.querySelector('button:has(.anticon-plus)')?.click()"
     # ⚠️ eval 不可用于"探查/发现"元素，只用于"填充/聚焦已定位的元素"
     # ⚠️ eval 查找元素前，先 snapshot 确认该元素确实存在

  eval 的合理使用场景:
    - 聚焦输入框后 keyboard type（Ant Design 受控组件）
      agent-browser eval "document.querySelector('input#storyCode')?.focus()"
    - 简单验证（检查值、读取文本）
      agent-browser eval "document.querySelector('.ant-modal input#storyCode')?.value"
    - 检查弹窗是否存在
      agent-browser eval "!!document.querySelector('.ant-modal')"

❌ 禁止在 PowerShell 下不加引号使用 @ref：
  - agent-browser click @e61         → @e61 被当空变量
  - agent-browser fill @e76 "xxx"    → 同上
  - agent-browser type @e168 "xxx"   → 同上

✅ @ref 加双引号后完全可用:
  - 点击: agent-browser click "@e61"
  - 输入: agent-browser type "@e168" "TCDN-TYPE"
  - 填充: agent-browser fill "@e169" "测试名称"

窗口管理:
  - 每次 open 前必须 close --all（避免 Chrome daemon 僵尸进程）
  - 首次 open 必须带 --headed --args "--start-maximized"
  - 登录后先 snapshot 确认页面稳定 → 再导航到目标页
```

## 三.一、弹窗内元素定位规范（必须严格执行）

```yaml
# 弹窗打开后，snapshot 的 ref 会重新编号。
# 之前操作弹窗外元素时获得的 ref，弹窗打开后可能指向页面搜索区而非弹窗内。
# 禁止使用弹窗打开前的 ref 操作弹窗内元素！

弹窗操作的标准流程:
  1. 用 snapshot ref 点击触发弹窗的按钮
     agent-browser click "@e61"
  
  2. 等待弹窗出现后，立即重新 snapshot
     agent-browser snapshot -i -c -d 4 --json

  3. 从 snapshot 输出中仔细区分弹窗内元素和页面元素的 ref
     - 弹窗内输入框的 placeholder 通常是"请输入XXX"
     - 页面搜索框的 placeholder 通常是"代号"或"名称"
     - 弹窗内元素被 generic "Close 新增短剧..." 包裹
     - 页面元素被 generic "畅读创作者后台..." 包裹

  4. 操作弹窗内元素：用 ref（加双引号）或 .ant-modal 限定
     agent-browser type "@e168" "TCDN-TYPE"
     或
     agent-browser eval "document.querySelector('.ant-modal input#storyCode')?.focus()"
     agent-browser keyboard type "TCDN-TYPE"

弹窗/页面同名元素区分:
  | 弹窗内元素 | CSS 选择器 | 页面上对应元素 | CSS 选择器 |
  |-----------|-----------|---------------|-----------|
  | 代号输入框 | .ant-modal input#storyCode | 搜索区代号 | input#storyCode（不在 .ant-modal 内）|
  | 名称输入框 | .ant-modal input#storyName | 搜索区名称 | input[placeholder*="名称"] |
  | 剧目类型下拉 | .ant-modal .ant-select:first | 筛选剧目类型 | .ant-table-filter .ant-select |
  | 保存按钮 | .ant-modal-footer .ant-btn-primary | — | — |
  | 取消按钮 | .ant-modal-footer button:not(.ant-btn-primary) | — | — |
  | 关闭按钮 | .ant-modal-close | — | — |

判断弹窗是否存在的依据:
  - document.querySelector('.ant-modal') 存在 → 弹窗打开中
  - document.querySelector('.ant-modal-mask') 存在 → 遮罩层
  - 此时所有页面操作都被遮罩挡住
```

## 三.二、Ant Design 表单操作规范（已知限制及应对）

```yaml
# 已知问题: Ant Design Form 使用 React 受控组件，以下方式不生效：
#   ❌ el.value = 'xxx' + dispatchEvent(input)
#   ❌ nativeValueSetter.call(el, 'xxx') + dispatchEvent(input)
#   ✅ keyboard type "xxx"（真实击键触发 React onChange）

Ant Design 输入的标准流程:
  1. 聚焦到输入框
     agent-browser eval "document.querySelector('input#storyCode')?.focus()"
  
  2. 真实击键输入
     agent-browser keyboard type "TCDN001"
  
  3. Tab 移出触发 blur 校验
     agent-browser press "Tab"
  
  4. 验证值已正确写入
     agent-browser eval "document.querySelector('input#storyCode')?.value"

Ant Design 表单提交失败的排查:
  问题表现: 填入值后点保存，无错误提示、无成功提示、弹窗不关闭
  排查步骤:
    1. 检查是否有字段校验错误
       agent-browser eval "document.querySelector('.ant-form-item-explain-error')?.textContent"
    2. 检查是否有全局消息
       agent-browser eval "document.querySelector('.ant-message-notice')?.textContent"
    3. 检查保存按钮是否 disabled
       agent-browser eval "document.querySelector('.ant-modal-footer .ant-btn-primary')?.getAttribute('disabled')"
    4. 检查输入框实际值（可能被 form 重置）
       agent-browser eval "document.querySelector('.ant-modal input#storyCode')?.value"
    
  如果以上都正常但表单仍不提交:
    - 尝试用 Tab 移动到保存按钮后按 Enter
    - 尝试直接点击 span 内的文本
    - 标记为工具限制 → SKIP → 继续下一条用例

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Ant Design DatePicker 操作规范（Ant Design 时间选择器）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ant Design DatePicker 受控组件:
  已知问题（已验证）:
    ❌ 仅点日历单元格(.ant-picker-cell-inner) → DOM value 有值但 React form.validateFields() 校验仍报"必填"
    ❌ nativeValueSetter + dispatchEvent(input/change) → 被 React form 重置
    ❌ 仅 click 日历日 → React onChange 不触发，Form.Item 内部状态不同步

  ✅ 方式一：keyboard type 直接键入日期（推荐，本次验证可靠）:
    # 原理: keyboard type 触发真实按键 → Ant Design parse 日期字符串
    #       Tab 移出焦点触发 blur → Form.Item.validateFields 执行 → 通过
    步骤 1: 用 snapshot ref 点击 DatePicker 使其获取焦点
      agent-browser click "@e267"

    步骤 2: 直接键入日期（YYYY-MM-DD 格式）
      agent-browser keyboard type "2026-05-30"

    步骤 3: Tab 移出焦点，触发 Ant Design Form.Item 的 blur 校验
      agent-browser keyboard type "\t"

    步骤 4: 🔴 强制验证：日期已写入 + 无校验错误（不可跳过）
      agent-browser eval "
      (function() {
        var val = document.getElementById('publish_time')?.value;
        var err = document.querySelector('.ant-modal .ant-form-item-explain-error');
        return JSON.stringify({value: val, error: err ? err.textContent : null});
      })()
      "
      → 应返回 {"value":"2026-05-30","error":null}
      → 如果 error 不为 null → 尝试方式二

  ✅ 方式二：日历点选（方式一失败时的回退方案）:
    步骤 1: 点击 datepicker input 打开日历面板
    步骤 2: wait 800ms 等日历渲染
    步骤 3: 在可见的日历下拉中点击目标日
      agent-browser eval "
      (function() {
        var cells = document.querySelectorAll('.ant-picker-dropdown:not(.ant-picker-dropdown-hidden) .ant-picker-cell:not(.ant-picker-cell-disabled) .ant-picker-cell-inner');
        for (var i = 0; i < cells.length; i++) {
          if (cells[i].textContent.trim() === '30') { cells[i].click(); return 'day 30'; }
        }
        return 'not found';
      })()
      "
    步骤 4: 如有"确定"按钮必须点击
    步骤 5: 回到方式一步骤 4 做强制验证

  ⚠️ 两种方式都失败 → SKIP → API 创建数据后 UI 列表验证

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Ant Design Select 操作规范（Ant Design 下拉选择器）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ant Design Select 受控组件:
  已知问题:
    ❌ mousedown on .ant-select-selector + click .ant-select-item-option
       → 下拉打开了但 React value 不一定同步（form.validateFields 失败）
    ❌ dispatchEvent(new MouseEvent('mousedown')) → React 可能不识别
    ❌ 上一个 dropdown 未关闭就点下一个 → 打开的还是旧 dropdown
  
  ✅ 正确流程（必须完整执行，不可跳过任何步骤）:
    步骤 1: 确保没有其他下拉框打开
      agent-browser press "Escape"  # 关闭任何已打开的下拉
    
    步骤 2: 点击目标 select 的 visible trigger
      agent-browser eval "
      document.querySelector('.ant-modal .ant-select-selector')?.click()
      "
      # 注意：如果有多个 select，必须指定是哪一个
      # 通过 .ant-modal .ant-form-item 逐一定位：
      agent-browser eval "
      (function() {
        var items = document.querySelectorAll('.ant-modal .ant-form-item');
        for (var i = 0; i < items.length; i++) {
          var label = items[i].querySelector('.ant-form-item-label label');
          if (label && label.textContent.trim() === '频道') {
            items[i].querySelector('.ant-select-selector').click();
            return 'clicked';
          }
        }
        return 'not found';
      })()
      "
    
    步骤 3: 等待下拉列表渲染完成
      agent-browser wait 600
    
    步骤 4: 验证下拉已打开（不是旧下拉）
      agent-browser eval "
      (function() {
        var dd = document.querySelector('.ant-select-dropdown:not(.ant-select-dropdown-hidden)');
        if (!dd) return 'no visible dropdown';
        var items = dd.querySelectorAll('.ant-select-item');
        var list = [];
        items.forEach(function(it) { list.push(it.textContent.trim()); });
        return list;
      })()
      "
      → 确认下拉中的选项是正确的（如 ['男频', '女频']）
      → 如果选项不对 → 关闭重来

    步骤 5: 点击目标选项
      agent-browser eval "
      (function() {
        var items = document.querySelectorAll('.ant-select-item-option-content');
        for (var i = 0; i < items.length; i++) {
          if (items[i].textContent.trim() === '男频' && items[i].offsetParent) {
            items[i].parentElement.click();  // 点 option 而非 content
            return 'selected';
          }
        }
        return 'not found';
      })()
      "
    
    步骤 6: 验证 select 显示值已更新
      agent-browser eval "
      (function() {
        var items = document.querySelectorAll('.ant-modal .ant-form-item');
        for (var i = 0; i < items.length; i++) {
          var label = items[i].querySelector('.ant-form-item-label label');
          if (label && label.textContent.trim() === '频道') {
            var sel = items[i].querySelector('.ant-select-selection-item');
            return sel ? sel.textContent.trim() : 'no selection item';
          }
        }
        return 'not found';
      })()
      "
      → 应返回 '男频'，如果不是 → React 状态未同步

  ⚠️ Select 验证失败的标准恢复流程:
    如果步骤 6 返回的值不是目标值 → React form 状态未同步
    → 判断为 工具限制 | 标记 SKIP | 使用 API 创建数据后验证 UI 列表展示
```

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Ant Design Radio 操作规范（Ant Design 单选按钮组）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ant Design Radio 受控组件:
  已知问题（已验证）:
    ❌ 点击 .ant-radio-wrapper → wrapper 被点但内部 input 未触发 React onChange
    ❌ 点击 .ant-radio 外层 span → checked 样式不变化
    ❌ 用 snapshot ref click radio → Agent browser 可能点中 wrapper 而非 input

  ✅ 正确流程:
    步骤 1: 找到目标 radio 的 .ant-radio-input（真正的 input 元素）
      agent-browser eval "
      (function() {
        var wrappers = document.querySelectorAll('.ant-modal .ant-radio-wrapper');
        var result = [];
        wrappers.forEach(function(w,i) {
          result.push(i + ': ' + w.textContent.trim());
        });
        return JSON.stringify(result);
      })()
      "
      → 例如: ["0: 预上架", "1: 已下架"]

    步骤 2: 🔴 点击 .ant-radio-input（必须是 input，不是 wrapper）
      agent-browser eval "
      (function() {
        var wrappers = document.querySelectorAll('.ant-modal .ant-radio-wrapper');
        for (var i = 0; i < wrappers.length; i++) {
          if (wrappers[i].textContent.trim().indexOf('预上架') === 0) {
            wrappers[i].querySelector('.ant-radio-input').click();
            return 'clicked radio';
          }
        }
        return 'not found';
      })()
      "

    步骤 3: 🔴 强制验证：radio checked 状态已变化
      agent-browser eval "
      (function() {
        var w = document.querySelector('.ant-modal .ant-radio-wrapper');
        return !!w?.querySelector('.ant-radio-checked');
      })()
      "
      → 应返回 true

  ⚠️ Radio checked 但不触发 form 状态更新的情况:
    → 先点另一个 radio 再点回目标 radio（模拟用户真实操作）
    → 仍失败 → SKIP → API 创建数据后 UI 列表验证

## 三.三、AI 决策点补充：弹窗上下文检查

```yaml
# 在 AI 决策点 2（选择操作）和决策点 4（验证结果）中，追加以下检查：

决策点 2 补充: 当页面有弹窗时
  - 弹窗内的输入框用 .ant-modal input#id CSS 选择器
  - 页面搜索区的输入框用 input[placeholder*="名称"]
  - 禁止使用弹窗打开前获得的 ref 操作弹窗内元素
  - 判断依据：弹窗内的 input 一定被 .ant-modal 包裹，页面搜索框不在其中

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔴 表单填充后强制验证 check-loop（最高优先级，不可跳过）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 问题: 操作看似成功（click/fill/type 返回 Done），但 Ant Design Form.Item
#       内部 React 状态未同步 → 保存时报"必填"但不明确哪个字段失败
# 解决: 每填充一个字段后立即检查 .ant-form-item-explain-error
#       → 有错误 → 修复 → 重新检查 → 直到错误清零 → 再填下一个字段
#
# 🔴 操作流程（代替"一口气填完再保存"）:
#   填字段1 → 检查错误 → 无错误 → 填字段2 → 检查错误 → 无错误 → ...
#   → 全部填完且无错误 → 点保存
#
# 🔴 禁止: 一口气填完所有字段再检查（不知道哪个字段有问题）

决策点 4 补充: 弹窗表单填充后必须执行的强制验证:
  步骤 A: 检查是否存在校验错误
    agent-browser eval "
    (function() {
      var errors = document.querySelectorAll('.ant-modal .ant-form-item-explain-error');
      var msgs = [];
      errors.forEach(function(e) { msgs.push(e.textContent); });
      return JSON.stringify(msgs.length === 0 ? 'CLEAN' : msgs);
    })()
    "
    → 返回 "CLEAN" 或无错误的字段名列表

  步骤 B: 如果有错误 → 逐字段修复:
    "上架时间必填" → DatePicker 值未同步 → 重新 keyboard type + Tab
    "上架状态必填" → Radio 未选中 → 重新 click .ant-radio-input
    "xxxx必填"   → 对应字段未通过 React form 校验 → 重新操作该字段

  步骤 C: 修复后重新检查（回到步骤 A）→ 直到返回 "CLEAN"

  步骤 D: 确认无错误后，点击保存按钮
    agent-browser click "@e67"  # 保 存 按钮

  步骤 E: 等待保存结果:
    - 弹窗关闭 → 保存成功 → snapshot 检查列表中是否有新记录
    - 弹窗未关闭 → 重新执行步骤 A 检查是否有新错误

  Ant Design 表单提交失败的排查:
    问题表现: 填入值后点保存，无错误提示、无成功提示、弹窗不关闭
    排查步骤:
      1. 检查是否有字段校验错误（步骤 A）
      2. 检查是否有全局消息
         agent-browser eval "document.querySelector('.ant-message-notice')?.textContent"
      3. 检查保存按钮是否 disabled
         agent-browser eval "document.querySelector('.ant-modal-footer .ant-btn-primary')?.getAttribute('disabled')"
      4. 检查输入框实际值（可能被 form 重置）
         agent-browser eval "document.querySelector('.ant-modal input#storyCode')?.value"

    如果以上都正常但表单仍不提交:
      → 标记为 工具限制 | SKIP | 继续下一条用例
```

## 三.四、登录流程规范

```yaml
# 登录类型C1（工号登录，Keycloak 统一认证）:
登录流程:
  步骤1: snapshot 识别登录页类型
    agent-browser snapshot -i -c -d 3 --json
    → 从 refs 中找 "LabelText 工号登录" 或 "radio user 工号登录"

  步骤2: 用 ref 点击工号登录入口
    agent-browser click "@e4"  # LabelText "工号登录"
    # 如果 click @ref 找不到，fallback 到 eval
    agent-browser eval "document.querySelector('label')?.click()"

  步骤3: 进入 Keycloak 后，从新 snapshot 中找输入框 ref
    agent-browser snapshot -i -c -d 3 --json
    → textbox "用户名" [ref=e2] / textbox "密码" [ref=e3]
    agent-browser type "@e2" "109013"
    agent-browser type "@e3" "Arvin@1314!"

  步骤4: 点登录
    agent-browser click "@e5"  # button "登录"
    # 或
    agent-browser eval "document.querySelector('#kc-login').click()"
    
  步骤5: 确认登录成功
    agent-browser snapshot → URL 从 keycloak 跳转到业务系统首页
```

## 三.五、报表查询——动态加载等待

### 问题

报表类查询通常需要 5-30 秒完成，固定等待容易导致：
- 等得太短 → 拿到 loading 状态或"暂无数据"的中间结果
- 等得太长 → 浪费时间
- 没有检测 → 查询未完成就开始验证

### 强制流程

```yaml
# 每次点击查询按钮后，使用轮询检测加载完成
报表查询等待流程:
  1. 点击查询按钮
  2. 立即检测按钮状态: 是否出现 loading 文本/class？
     → eval "检查 button 是否含 loading/spinner/disabled"

  3. 轮询检测加载完成（每 1.5 秒一次）:
     agent-browser eval "
     (() => {
       const btn = document.querySelector('button:has(StaticText:querySelector(\"查 询\"))');
       // 信号 1: loading 按钮 -> 正常按钮
       const noLoading = !btn || !btn.querySelector('.anticon-loading, .el-icon-loading, img[alt=loading]');
       
       // 信号 2: 表格中出现数据行
       const tableRow = document.querySelector('td, .ant-table-row, [class*=row]');
       const dataRow = tableRow && !tableRow.textContent.includes('暂无数据');
       
       // 信号 3: 分页组件显示'共 X 条'
       const pagination = document.querySelector('.ant-pagination, .el-pagination, nav[aria-label=pagination]');
       const pageText = document.body.innerText.match(/共\s*\d+\s*条/);
       
       // 信号 4: 空状态提示
       const empty = document.body.innerText.includes('暂无数据');
       
       return JSON.stringify({
         loading: !noLoading,
         hasData: dataRow,
         pagination: pageText ? pageText[0] : null,
         empty: empty
       });
     })()
     "

  4. 停止条件（任一满足即停止轮询）:
     - loading 消失 + hasData=true → ✅ 加载完成
     - loading 消失 + empty=true → ✅ 空数据，正常加载
     - loading 消失 + pagination 出现 → ✅ 分页加载完成
     - 超时 30 秒 → ⚠️ 高成本 snapshot 探查

  5. 超时后诊断:
     - snapshot → AI 判断:
       - 页面卡死（加载动画一直在转）→ 标记环境问题
       - 页面已加载但无数据（"暂无数据"）→ 这是有效状态
       - 页面报错（500/AxiosError）→ 标记失败
```

### 不同查询类型的超时阈值

```yaml
超时配置:
  简单查询（有索引、小数据量）: 10 秒超时
  中等查询（多表关联、几万条）: 15 秒超时
  复杂查询（大报表、跨数据源）: 30 秒超时
  ⚡ 首次查询（无缓存）: 超时 × 2

AI 可以根据每次的实际耗时，动态调整剩余测试的等待阈值。
```

### 注意事项

```yaml
- 轮询间隔 1.5 秒，不要太频繁（500ms）避免增加服务端压力
- 第一次轮询前先等 1 秒，给后端足够时间返回初始响应
- loading 消失后不要立即 snapshot，再等 500ms 确保 DOM 稳定
- 如果检测到"暂无数据"且是预期之外（如正常范围查询），
  可能是条件过严，换宽松条件重试一次
```

---

## 四、异常处理（固定策略 + AI 判断）

```yaml
# 固定异常处理策略：
异常处理:
  - 元素未找到:
    1. 重新 snapshot（高成本探查）
    2. 再找（最多 3 次）
    3. 仍找不到 → 标记失败
    AI 判断: 是页面未加载？还是元素确实不存在？

  - 操作无效果:
    1. 检查是否操作了错误元素（作用域是否正确？弹窗 vs 搜索区？）
    2. 按交互层级升级（DOM click → Vue 实例 → Form Model）
    3. 每层最多 2 次，总次数 > 8 次 → 强制跳过
    AI 判断: 是操作方式不对？还是组件特殊？还是功能有 Bug？

  - ⚠️ 交互卡住（新增）:
    1. 同一操作步骤失败 ≥ 3 次 → 检查是否卡在同一个交互模式
    2. 单步骤耗时 > 3 分钟 → 强制跳过
    3. 跳过当前用例 → 标记 SKIP + 记录详细跳过原因
    4. 清理状态（关闭弹窗/刷新页面）→ 继续下一条独立用例
    5. 所有用例执行完后汇总跳过清单
    → 详细规则见 common/execution-optimization.md §场景 13

  - 弹窗出现:
    1. 识别弹窗类型（信息提示/表单/确认/错误）
    2. 信息提示/错误类 → 截图 + 关闭 → 继续
    3. 表单类 → ⚠️ 限定弹窗作用域后再操作
    AI 判断: 弹窗是否影响当前操作？

  - 页面超时:
    1. 高成本探查（诊断当前状态）
    2. 如果页面已加载（只是慢）→ 继续执行
    3. 如果页面未加载（卡死）→ 刷新 → 重试（最多 2 次）
    4. 仍超时 → 标记环境问题
    AI 判断: 是网络问题？还是服务端问题？
```

---

## 四.一、异常场景清单（必须覆盖）

```yaml
# 每个功能点的测试用例中，必须包含以下异常场景：

必测异常场景:
  报表/查询类:
    - 空数据查询: 输入不可能有数据的时间范围（如 2010年）
      → 验证: 显示"暂无数据"，无 JS 报错，无白屏
    - 超大范围查询: 不设筛选条件，查询全量数据
      → 验证: 正常返回数据（可能慢），不超时崩溃
    - 未来时间查询: 结束时间 > 当前时间
      → 验证: 正常处理（显示未来时间段的数据或空状态）
    - 时间倒置: 开始时间 > 结束时间
      → 验证: 前端校验/后端返回友好的错误提示
    - 区间值为 0: 所有数值区间设为 0（最小值=0, 最大值=0）
      → 验证: 正常过滤（0 值数据或全部数据）
    - 极端值: 输入极大数字（如消耗=999999999）
      → 验证: 前/后端不崩溃，返回合理结果
    - 快速连续查询: 两次快速点击查询按钮
      → 验证: 无重复请求/无状态混乱

  配置弹窗类:
    - 不保存直接关闭: 打开弹窗 → 修改 → 点关闭/取消
      → 验证: 修改不生效，配置恢复为修改前状态
    - 空搜索过滤: 在弹窗搜索框输入不存在的关键词
      → 验证: 显示"无匹配项"或空的搜索结果
    - 全取消: 取消所有字段勾选 → 保存
      → 验证: 页面对应的筛选器/表头列全部消失
    - 全选恢复: 全部勾选 → 保存
      → 验证: 页面恢复完整状态

  筛选输入类:
    - 负值: 输入负数（如消耗最小值=-100）
      → 验证: 前端校验（负值被纠正为 0 或被拒绝）
    - 小数精度: 输入超长小数（如 0.123456789）
      → 验证: 精度截断/四舍五入处理合理
    - 下拉为空: 下拉列表空时点击
      → 验证: 显示"暂无数据"或空提示
```

---

### 四.一 人工协助阻塞处理

```yaml
# 当遇到必须人工介入的阻塞时，不暂停等待，而是请求用户在 5 分钟内协助：
阻塞场景:
  - 文件上传（仅当 §五 方案 A/B 均失败时）: Ant Design Upload 等组件库 React 状态不同步
  - 验证码/滑块: 页面有图形验证码
  - 短信/邮箱验证: 需要接收验证码
  - 第三方授权: 钉钉/微信扫码等
  - 信息缺失: 缺少登录凭证/Token/配置等明确需要用户提供的信息
  - 环境限制: agent-browser 能力边界（如 Ant Design Portal 交互已穷尽）

处理流程:
  1. 报告用户:
     - 说明具体阻塞原因（哪个操作、为什么无法自动完成）
     - 告知用户需要做什么（如"请上传文件 X"、"请提供 Token"）
     - 请求用户在 5 分钟内协助

  2. 等待期间:
     - 不空等 — 继续执行其他不需要此阻塞步骤的用例
     - 如果后续步骤依赖当前阻塞 → 先跳到下一条独立用例

  3. 5 分钟后用户未反馈:
     - 标记该用例为 "⏭️ 跳过（人工协助超时）"
     - 记录跳过原因到测试报告
     - 继续执行剩余用例

  4. 用户反馈后:
     - 立即回到阻塞点继续执行
     - 如果页面状态已变化（超时/刷新）→ 重新构造前置条件

  5. 禁止:
     - ❌ 不告知用户直接静默跳过
     - ❌ 无限期等待用户反馈
     - ❌ 遇到阻塞就停止所有测试
```

---

## 五、文件上传策略

> **定位**：优先使用 AutoHotkey（通用性最强），upload 命令作为简单场景快速路径。

### 方案 A：AutoHotkey（首选，通用方案）

```yaml
# ⭐ 首选方案，适用于所有场景（标准 input / Ant Design / 组件库 Upload）
方案 A:
  原理:
    - CDP 点击页面上的上传区域 → 浏览器弹出原生 OS 文件对话框
    - AutoHotkey 监听对话框 → 自动填充文件路径 → 点击确认
    - 完全绕过前端框架（React/Vue）的 JS 拦截，通用性最强

  前置:
    - Windows: 安装 AutoHotkey v1，路径 C:\Program Files\AutoHotkey\AutoHotkeyU64.exe
    - 技能初始化时自动检查，未安装则提示用户

  执行步骤:
    1. 探查上传区域:
       eval "document.querySelector('[class*=\"upload\"]')?.className"
       → 获取 CSS class（如 uploadBox-CcgOWE3k）

    2. 处理文件路径（避开 AHK v1 CLI ANSI 编码限制）:
       方案 2a（中文路径）: 写 UTF-8 路径文件
         powershell "[IO.File]::WriteAllText('temp/upload_path.txt', '<完整路径>', [Text.Encoding]::UTF8)"
       方案 2b（英文路径）: 如果路径无中文，可直接传参；或将文件复制到英文路径
         cp "<原路径>" "D:/AI-Explore/temp/upload.xlsx"

    3. 启动 AHK（后台监听对话框）:
       powershell "Start-Process 'C:\Program Files\AutoHotkey\AutoHotkeyU64.exe' -ArgumentList '<ahk脚本>'"

    4. CDP 点击上传区域:
       agent-browser click "div.<upload-class>"
       → 触发原生 OS 文件对话框

    5. 等待 AHK 处理（AHK 脚本 15 秒超时自退）:
       sleep 5; cat temp/upload_log.txt
       → 检查日志: START → DETECTED → PATH_SET → OK_DIALOG_CLOSED

    6. snapshot 验证上传结果

  AHK 脚本模板（upload_file.ahk）:
    - 必须用 AutoHotkeyU64.exe（Unicode build）启动
    - 从 temp/upload_path.txt 读取路径（避开 CLI ANSI 限制）
    - 轮询 IfWinExist ahk_class #32770
    - 检测到 → ControlFocus Edit1 → ControlSetText Edit1 → ControlClick Button1
    - 写日志到 temp/upload_log.txt

  验证:
    - AHK 日志: DETECTED + PATH_SET + OK → 对话框处理成功
    - snapshot 检查页面: 文件名显示? 导入结果页?
    - 如果有错误提示 → 后端校验拦截，不重试，标记 FAIL

  适用:
    - Ant Design Upload ✅ — 唯一有效方案
    - Element UI Upload ✅
    - 标准 file input ✅
    - 任何组件库 Upload ✅
```

### 方案 B：upload 命令（简单场景快速路径）

```yaml
# 仅当文件路径无中文且页面是标准 HTML input 时，可跳过 AHK 直接用此方案：
方案 B:
  步骤:
    1. 定位 file input: eval "document.querySelectorAll('input[type=file]')"
    2. agent-browser upload "input[type=file]" <file_path>
  适用:
    - 标准 HTML file input（有 id/name，无组件库封装）
    - 测试用的本地 HTML 页面
  不适用:
    - Ant Design / Element UI / 任何组件库 Upload ❌
  验证:
    - eval "input.files.length" 确认 > 0
```

### 方案 C：人工协助（兜底）

```yaml
方案 C:
  条件: 方案 A 和 B 均失败
  操作:
    1. 告知用户: "请在浏览器中点击上传区域，手动选择文件 <file_path>"
    2. 等待用户操作（最长 5 分钟）
    3. snapshot 确认文件已上传
  超时处理:
    - 标记用例为 "⏭️ 跳过（文件上传需人工协助）"
```

### 上传验证与防死循环

```yaml
# ⚠️ 上传失败时不要死循环重试，先判断失败原因：
验证层次:
  层次 1 — 前端验证:
    - AHK 日志是否显示 DETECTED? → 否 → 对话框未弹出，检查 CDP 点击
    - AHK 日志是否显示 PATH_SET + OK? → 否 → 路径或 AHK 脚本异常
    - input.files.length > 0? / 页面显示文件名?
    → 前端成功但页面无变化 → 检查接口

  层次 2 — 接口监测:
    - snapshot 检查页面变化
    - 出现错误提示（"格式错误"、"校验失败"等）:
      → 后端校验拦截，不是上传机制问题
      → 记录错误信息，标记 FAIL，不重试
    - 页面 30 秒无响应:
      → 检查弹窗/loading → 仍无响应 → 标记 FAIL，不重试

  层次 3 — 防死循环规则:
    - 同一用例上传重试 ≤ 2 次
    - 连续 2 次上传后页面状态无变化 → 停止，标记 FAIL
    - 后端返回明确错误 → 不重试，记录错误原因
    - 仅在"文件未挂载"时换方案重试（B→A→C）
```

### 方案选择决策树

```yaml
AI 决策:
  1. 探查页面
     → 是否有上传区域？
     → 是标准 input 还是组件库 Upload?

  2. 首选方案 A (AutoHotkey):
     → 写路径文件 → 启动 AHK → CDP 点击上传区
     → 验证: snapshot 检查页面变化
     → 文件名/导入结果显示 → 继续测试
     → 错误提示 → 标记 FAIL（数据/后端问题），不重试
     → 页面无变化 + AHK 日志 TIMEOUT → 对话框没弹出，重试 1 次
       → 仍失败 → 进入步骤 3

  3. 备选方案 B (upload 命令):
     → 仅适用于简单标准 input（无组件库封装）
     → agent-browser upload "input[type=file]" <path>
     → 验证: input.files.length > 0?
     → 是 → 继续 | 否 → 进入步骤 4

  4. 兜底方案 C: 请求人工协助
```

---

## 六、数据隔离

```yaml
# 固定数据隔离策略：
数据隔离:
  - 所有测试数据添加 【测试】 前缀
  - 操作前检查：数据是否已被其他测试使用？
  - 操作后标记：数据已被当前测试使用
  - 测试完成后 AI 自动清理
```

---

## 七、跨系统端到端验证（E2E）— 🔴 对内变更必须验证对外系统

```yaml
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔴 问题: 当前技能只覆盖了目标系统（对内），完全没有验证对外/下游系统。
#   对内新增/修改/下架了数据 → 对外系统是否同步变化？→ 从未检查!
#   这导致"测试全覆盖"的假象 —— 所有用例 PASS，但对外用户看到的是错的。
#
# 🔴 规则: 任何对内操作，如果需求涉及对外可见性，必须追加 E2E 验证步骤。
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

E2E 验证触发条件（满足任一即触发）:
  条件 1: 需求涉及"对外"系统（对外剧目表/对外分销结算/对外投放链接）
  条件 2: 数据有"对外可见性"字段（如 external_show_time, shelf_status）
  条件 3: 需求文档明确写了"同步到对外"、"外部可见"等

E2E 验证步骤（必须在 对内操作 → 验证对内结果 之后执行）:

  步骤 1: 对内新增/修改数据（如新增已上架+对外展示=今天的剧目）
     → 验证对内 DB 数据正确

  步骤 2: 🔴 调用对外 API 验证数据可见（不可跳过）
     # 例如: 对内新增了已上架剧目 → 对外 DistributionStoryOut/GetList 应包含该剧
     /c/Python314/python -c "
     import urllib.request,json
     url='对外API地址'
     data=json.dumps({'storyCode':'E2E001'}).encode('utf-8')
     req=urllib.request.Request(url,data=data,headers={
       'Content-Type':'application/json',
       'Authorization':'Bearer '+token
     },method='POST')
     resp=urllib.request.urlopen(req)
     result=json.loads(resp.read().decode())
     # 检查: data.list 中应包含目标记录
     "

  步骤 3: 🔴 对内下架/隐藏数据
     # 对内 BatchOffline → DB shelf_status=3

  步骤 4: 🔴 调用对外 API 验证数据不可见（不可跳过）
     # 对外 DistributionStoryOut/GetList → 目标记录应消失
     # totalCount 应递减

  步骤 5: 记录 E2E 验证结果到测试报告
     → 新增 2.9 端到端验证章节

E2E 验证检查清单:
  ✅ 对内新增已上架 → 对外列表可见
  ✅ 对内下架（shelf_status 2/1 → 3）→ 对外列表不可见
  ✅ 对内修改对外展示时间 → 对外按时间规则显示/隐藏
  ✅ totalCount 变化验证（新增→+1, 下架→-1）

⚠️ 如果不满足 E2E 触发条件 → 标记为 N/A 并记录原因
⚠️ 如果对外 API 不可达 → 标记为 SKIP 并记录原因
```