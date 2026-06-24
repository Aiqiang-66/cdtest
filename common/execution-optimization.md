# AI 执行过程优化 — 探查策略、等待策略、加载判断、深度测试

## 定位

定义 AI 在执行过程中的**探查时机、等待策略、加载判断、执行优化、深度测试**。解决"什么时候探查页面"、"等多久"、"怎么判断加载完成"、"如何防止只探查不测试"等核心问题。

---

## 一、探查策略（什么时候做 snapshot/page_source）

### 问题

当前每个用例循环都做一次 snapshot，很多情况下不需要。频繁 snapshot 消耗资源（网络请求 + AI 处理时间），且可能触发反爬机制。

### 优化方案

```yaml
探查触发条件:
  必须探查（不可跳过）:
    - 页面导航/跳转后（URL 变化）
    - 操作执行后（click/submit/save）
    - 等待超时后（需要确认当前状态）
    - 异常发生后（需要诊断当前页面）
    - 用例开始时（首次进入页面）

  可以跳过（合并探查）:
    - 连续 fill 操作: 填完所有字段后再探查一次
      → 示例: 表单有 5 个字段，全部 fill 完 → 一次 snapshot 验证
    - 连续 select 操作: 选择完所有选项后再探查
    - 纯等待期间: 用轻量检查替代完整 snapshot
      → 轻量检查: URL 是否变化 / 特定元素是否存在 / 加载指示器是否消失

  选择性探查（AI 判断）:
    - 页面滚动后: 只探查新加载区域（懒加载内容）
    - 弹窗出现后: 只探查弹窗内容（不探查背景页面）
    - 输入验证: 只验证输入框的值（不探查整个页面）
```

### 探查成本分级

```yaml
探查成本:
  低成本（毫秒级）:
    - URL 检查: driver.current_url
    - 元素存在检查: driver.find_element (by specific locator)
    - 加载指示器检查: 检查 spinner/loading 元素是否存在
    - 适用: 等待期间的轮询检查

  中成本（百毫秒级）:
    - 部分 snapshot: 只获取可见区域（viewport）
    - 弹窗内容获取: 只获取 dialog/alert 的 page_source
    - 适用: 操作后的快速验证

  高成本（秒级）:
    - 完整 snapshot: 获取整个页面的 page_source
    - 完整 page_source: 获取 APP 整个页面的元素树
    - 适用: 页面导航后、异常诊断、用例开始时
```

### AI 探查决策

```yaml
# AI 根据当前操作类型选择探查成本：
AI 探查决策:
  - 操作是 click（导航类）→ 高成本探查（需要完整页面理解）
  - 操作是 click（非导航类，如弹窗确认）→ 中成本探查
  - 操作是 fill → 跳过探查（合并到后续操作）
  - 操作是 select → 跳过探查（合并到后续操作）
  - 操作是 submit/save → 中成本探查（检查保存结果）
  - 等待超时 → 高成本探查（诊断当前状态）
  - 异常发生 → 高成本探查（诊断异常原因）
```

---

## 二、等待策略（等多久、怎么等）

### 问题

当前"最长等待 10 秒"太粗糙。简单操作（click 后页面刷新）和复杂操作（文件上传）的等待时间完全不同。

### 优化方案

```yaml
等待策略:
  快速等待: 0-3 秒（含 0，不含 3）
    适用场景:
      - click 后页面局部刷新
      - 弹窗出现/消失
      - 简单表单提交
      - 切换 Tab/标签页
    轮询间隔: 每 500ms 检查一次
    检查方式: 低成本探查（URL 检查 / 元素存在检查）
    超时处理: 超时 → 中成本探查 → 判断是否继续轮询

  正常等待: 3-8 秒（含 3，不含 8）
    适用场景:
      - 列表数据加载
      - 搜索查询结果
      - 页面间导航跳转
      - 中等复杂度操作
    轮询间隔: 每 1s 检查一次
    检查方式: 中成本探查（部分 snapshot）
    超时处理: 超时 → 高成本探查 → 判断是否继续轮询

  慢速等待: 8-15 秒（含 8，不含 15）
    适用场景:
      - 文件上传/下载
      - 大数据量导出
      - 第三方服务调用
      - 复杂报表生成
    轮询间隔: 每 2s 检查一次
    检查方式: 低成本探查（加载指示器检查）
    超时处理: 超时 → 高成本探查 → 判断是否继续轮询

  自定义等待（AI 判断）:
    适用场景:
      - AI 根据历史数据判断"这个操作通常需要 X 秒"
      - AI 根据页面复杂度判断"这个页面加载需要 X 秒"
      - AI 根据网络速度判断"当前网络下需要 X 秒"
    轮询间隔: AI 动态决定（500ms ~ 2s）
    检查方式: AI 动态选择
    超时处理: AI 判断"继续等待"还是"标记失败"
```

### AI 等待时间预测

```yaml
# AI 根据以下因素预测等待时间：
AI 等待预测:
  操作类型:
    - click（导航）→ 3-8 秒（正常等待）
    - click（弹窗确认）→ 0-3 秒（快速等待）
    - submit/save → 3-8 秒（正常等待）
    - 文件上传 → 8-15 秒（慢速等待）
    - 搜索查询 → 3-8 秒（正常等待）
    - 页面滚动 → 0-3 秒（快速等待）

  页面复杂度:
    - 简单页面: ≤20 个元素 → 等待时间 × 0.5
    - 中等页面: 21-100 个元素 → 正常等待
    - 复杂页面: >100 个元素 → 等待时间 × 2

  网络状况:
    - 快速网络（API 响应 <200ms）→ 等待时间 × 0.5
    - 正常网络（API 响应 200-1000ms）→ 正常等待
    - 慢速网络（API 响应 >1000ms）→ 等待时间 × 2

  历史数据:
    - 同一操作历史平均耗时 → 作为基准
    - 同一操作历史最大耗时 → 作为超时阈值
```

---

## 三、页面加载完成判断（怎么知道加载完了）

### 问题

当前"等待页面变化"太模糊。AI 需要明确的信号来判断页面是否加载完成。

### 优化方案

```yaml
加载完成判断:
  正向信号（页面已加载，可以继续）:
    - 目标操作元素可见且可交互
      → 示例: "保存"按钮从 disabled 变为 enabled
    - 页面 URL 已变化到预期地址
      → 示例: /list → /detail/123
    - 加载指示器消失
      → 示例: spinner/loading bar/skeleton screen 消失
    - 数据列表/表格已渲染
      → 示例: table 中有 tr 元素
    - 提示消息出现
      → 示例: Toast "保存成功" / Alert "操作完成"
    - 页面标题/面包屑变化
      → 示例: 面包屑从"首页 > 列表"变为"首页 > 列表 > 详情"

  负向信号（页面仍在加载，继续等待）:
    - Spinner/loading bar 可见
    - Skeleton screen 可见
    - 按钮处于 disabled 状态
    - "加载中"/"处理中"/"请稍候" 文本可见
    - 页面部分空白（数据未渲染）
    - 进度条未到 100%

  混合判断规则:
    - 正向信号出现 + 负向信号消失 → ✅ 加载完成
    - 正向信号出现 + 负向信号仍存在 → ⏳ 继续等待（可能部分加载）
    - 正向信号未出现 + 负向信号消失 → ❓ 重新探查（可能加载失败）
    - 正向信号未出现 + 负向信号仍存在 → ⏳ 继续等待
    - 超时 + 正向信号未出现 → ❌ 标记失败
```

### 平台专属加载信号

```yaml
Web 平台:
  正向信号:
    - document.readyState === 'complete'
    - 目标元素可见
    - 网络请求完成（无 pending XHR/Fetch）
    - 页面 title 变化
  负向信号:
    - 加载动画（CSS animation）运行中
    - 骨架屏可见
    - 按钮 disabled
    - 网络请求 pending

iOS 平台:
  正向信号:
    - 目标元素 label/name 可见
    - 页面标题/NavigationBar title 变化
    - ActivityIndicator 消失
  负向信号:
    - ActivityIndicator 可见
    - 页面空白（无元素）
    - 加载状态文本可见

Android 平台:
  正向信号:
    - 目标元素 text/content-desc 可见
    - Activity 变化（新页面出现）
    - ProgressBar 消失
  负向信号:
    - ProgressBar 可见
    - 页面空白（无元素）
    - Toast "加载中" 可见
```

---

## 四、执行流程优化

### 批量操作

```yaml
# 将连续的无等待操作合并执行，减少探查次数：
批量操作:
  表单填写:
    优化前: fill 字段1 → snapshot → fill 字段2 → snapshot → fill 字段3 → snapshot
    优化后: fill 字段1 → fill 字段2 → fill 字段3 → snapshot（一次验证）
    节省: 2 次不必要的 snapshot

  列表筛选:
    优化前: select 条件1 → snapshot → select 条件2 → snapshot → click 搜索 → snapshot
    优化后: select 条件1 → select 条件2 → click 搜索 → snapshot（一次等待）
    节省: 2 次不必要的 snapshot

  多步骤操作:
    优化前: click A → wait → click B → wait → click C → wait
    优化后: click A → click B → click C → wait（如果 A/B/C 无依赖关系）
    节省: 2 次不必要的等待
```

### 智能跳过

```yaml
# AI 判断是否可以跳过某些步骤：
智能跳过:
  页面已处于目标状态:
    - 用例要求"点击新增按钮" → 但页面已显示新增表单 → 跳过点击
    - 用例要求"输入搜索关键词" → 但搜索框已有内容 → 跳过输入

  元素已存在:
    - 需要等待"保存成功"提示 → 但提示已显示 → 跳过等待
    - 需要等待列表加载 → 但列表已有数据 → 跳过等待

  前置条件已满足:
    - 需要先登录 → 但已登录 → 跳过登录
    - 需要先造数 → 但数据已存在 → 跳过造数
```

### 并行检查

```yaml
# 等待期间同时检查多个条件，任一满足即继续：
并行检查:
  等待列表加载:
    同时检查:
      - 列表数据是否出现（tr/li/cell）
      - 分页组件是否出现
      - 加载指示器是否消失
      - 空数据提示是否出现
    任一满足 → 停止等待

  等待操作完成:
    同时检查:
      - 成功提示是否出现
      - 页面是否跳转
      - 目标元素状态是否变化
      - 错误提示是否出现
    任一满足 → 停止等待
```

---

## 五、Snapshot 缓存

```yaml
# 避免重复获取相同页面状态：
Snapshot 缓存:
  缓存时间: 2 秒（同一页面内）
  缓存内容: page_source / snapshot 数据

  ⚠️ 上下文管理: snapshot 结果写入文件（snapshots/step-N.txt），
  不在对话上下文中长期保留。AI 在验证时引用文件名，需详细分析时再读取。
  避免大型 page_source XML（100KB+）持续占用上下文窗口。

  缓存失效条件:
    - 执行了 click/submit 操作
    - 页面 URL 变化
    - 检测到 DOM 变化
    - 显式请求刷新

  部分更新:
    - 滚动后: 只获取新加载的元素
    - 弹窗出现: 只获取弹窗内容
    - 输入变化: 只验证输入框值
```

---

## 六、异常场景处理（模态框、动态下拉框、弹窗等）

### 问题

实际测试中会遇到各种异常场景：模态框遮挡页面、动态下拉框需要等待加载、弹窗改变页面结构等。AI 需要识别这些场景并采取对应策略。

---

### 场景 1：模态框 / Dialog / 弹窗

**特征**：页面出现覆盖层（overlay/modal/dialog），遮挡背景页面，新元素（弹窗内容）出现。

```yaml
检测方式:
  - Web: snapshot 中出现 role=dialog / class 包含 modal/overlay/dialog 的元素
  - iOS: page_source 中出现 Alert / Sheet / Popover
  - Android: page_source 中出现 Dialog / AlertDialog / PopupWindow

处理策略:
  1. 识别弹窗类型:
     - 信息提示类（"操作成功" / "确认删除？"）→ 自动处理
     - 表单类（"填写信息" / "选择选项"）→ 按用例步骤处理
     - 权限请求类（"允许访问位置？"）→ 接受（允许）
     - 错误类（"网络异常" / "系统错误"）→ 截图 + 标记失败

  2. 探查策略:
     - 弹窗出现 → 必须重新探查（弹窗内容不在之前的 snapshot 中）
     - 探查范围: 只探查弹窗内容（中成本探查），不探查背景页面
     - 弹窗关闭后 → 必须重新探查（背景页面可能已变化）

  3. ⚠️ 强制作用域规则（CRITICAL）:
     弹窗打开后，所有元素查找必须限定在弹窗 DOM 范围内，严禁无范围查找！
     
     错误做法（禁止）❌:
       document.querySelector('.el-select-dropdown__item')  
       → 可能命中页面搜索区/其他弹窗的元素，而非当前弹窗的
     
     正确做法（必须）✅:
       # 方式 1: 先定位弹窗容器，再从容器内查找
       const dialog = document.querySelector('.el-dialog__wrapper:not([style*="display:none"]) .el-dialog');
       const target = dialog.querySelector('.el-select-dropdown__item');
       
       # 方式 2: 使用 closest() 从已知弹窗元素向上回溯
       const dialog = knownElement.closest('.el-dialog');
       const target = dialog.querySelector('.target-element');
     
     查找顺序:
       1. 先查 dialog 内 → 2. 如果弹窗在 iframe 内 → 新标签页打开（详见 §场景 8）→ 3. 再查全局（仅当确认无歧义）
     
     ⛔ 禁止: 用 eval/contentDocument 直接操作 iframe 内弹窗
     
     判断歧义的方法:
       - 查找前先 count: document.querySelectorAll('.target-class').length
       - 如果 count > 1 且有弹窗打开 → 必须限定范围！
       - 如果 count == 1 → 可以用全局查找但仍推荐限定范围

  4. 操作策略:
     - 弹窗中的元素定位: 只在弹窗范围内查找（避免误操作背景元素）
     - 弹窗操作完成后: 检查弹窗是否已关闭
     - 弹窗未关闭: 尝试关闭（点击关闭按钮 / 点击背景遮罩 / 按 ESC）

  5. 特殊处理:
     - 多个弹窗叠加: 从最上层弹窗开始处理
     - 弹窗导致页面结构变化: 关闭弹窗后重新完整探查
     - 弹窗无法关闭: 标记为阻塞问题

示例:
  - 点击"删除"按钮 → 弹出确认弹窗 "确认删除？"
  - AI 识别: 信息提示类弹窗
  - 操作: 点击"确认"按钮（在弹窗范围内查找）
  - 弹窗关闭 → 重新探查 → 确认删除结果
```

---

### 场景 2：动态下拉框 / 选择器

**特征**：点击下拉框后，选项列表通过 AJAX 异步加载，需要等待选项出现后才能选择。

```yaml
检测方式:
  - Web: click select/dropdown → 等待 option/li 元素出现
  - iOS: tap PickerView/ActionSheet → 等待 wheel/option 元素出现
  - Android: tap Spinner/DropDown → 等待 list item 元素出现

处理策略:
  1. 点击下拉框后:
     - 立即探查（低成本: 检查选项列表是否出现）
     - 如果选项未出现 → 等待（快速等待 0-3s）→ 再次探查
     - 如果选项已出现 → 直接选择

  2. 选项搜索:
     - 如果选项列表很长（>20 项）→ 尝试输入搜索关键词
     - 如果选项是异步加载的 → 等待加载完成后再选择
     - 如果选项包含滚动 → 可能需要滑动才能看到目标选项

  3. 特殊处理:
     - 级联下拉框（选择省份→加载城市）→ 每级都需要等待
     - 搜索式下拉框（输入关键词→加载匹配项）→ 输入后等待
     - 多选下拉框 → 选择所有目标项后关闭

示例:
  - 点击"省份"下拉框 → 选项列表加载中（spinner 可见）
  - AI 等待（快速等待 0-3s）→ 选项列表出现
  - 选择"广东省" → 触发"城市"下拉框加载
  - 等待"城市"选项出现 → 选择"深圳市"
```

---

### 场景 3：Toast / 通知提示

**特征**：短暂出现的提示消息（2-3 秒后自动消失），不影响页面结构但包含重要信息。

```yaml
检测方式:
  - Web: snapshot 中出现 class 包含 toast/notification/message 的元素
  - iOS: page_source 中出现 Toast / Banner / HUD
  - Android: page_source 中出现 Toast / Snackbar

⚠️ 核心问题: Toast 只存活 2-3 秒，snapshot 耗时 1-2 秒，
  如果先等页面响应再 snapshot，Toast 大概率已消失！

处理策略（必须按顺序，每步都是即时执行）:
  1. ⚠️ 提交操作后立即检测（不要等！）:
     
     # 步骤 A: 提交操作本身返回后，立即用轻量 eval 检测
     agent-browser eval "
       (() => {
         // 检测当前页面中的所有 toast/message（iframe 内容已在新标签页打开，无需跨 frame 检测）
         const sel = '.el-message, .el-notification, .el-alert, .el-message-box, [class*=toast], [class*=message--]';
         const all = [...document.querySelectorAll(sel)];
         return JSON.stringify(all.filter(e => e.offsetParent !== null)
           .map(e => ({ text: e.textContent.trim().substring(0,200), cls: e.className.substring(0,50) })));
       })()
     "
     
     # 步骤 B: 如果 eval 返回空 → 再用 snapshot 兜底（可能 DOM 更新延迟）
     # 步骤 C: 如果还是空 → 用其他信号判断（弹窗关闭/页面跳转/列表变化）
  
  2. ⚠️ 不要在提交后先 sleep/snapshot 再检测！
     错误: submit → sleep 2s → snapshot → Toast 已消失 ❌
     正确: submit → eval 立即检测 → 捕获到 Toast ✅
  
  3. 捕获到 Toast 后:
     - 读取 Toast 文本 → 判断是成功/失败/警告
     - 记录到用例结果（这是关键验证证据！）
     - 不需要等待 Toast 消失，直接继续下一步

  4. 特殊处理:
     - 如果 eval 未捕获但页面有其他成功信号（弹窗关闭、列表刷新）→ 视为成功
     - 如果 eval 未捕获且页面无变化 → 视为失败，重新探查
     - 连续 3 次 eval 漏掉 Toast → 改用 snapshot 兜底

防漏策略:
  - 每次 submit/save/delete 操作后，eval 检测是强制步骤，不可跳过
  - eval 检测耗时 < 100ms，远快于 snapshot（1-2s）
  - 即使 eval 返回空，也能从页面状态变化推断操作结果
```

---

### 场景 15：提交后结果验证 — 合并提交+检测模式

**特征**：每次 submit/save/delete 操作后需要验证结果。传统模式"提交→等→快照→分析"太慢，容易漏掉 Toast。

```yaml
优化前（慢，易漏 Toast）:
  1. click 提交按钮
  2. sleep 2-3 秒（等待页面响应）
  3. snapshot（完整探查，1-2 秒）
  4. AI 分析 snapshot
  5. 判断结果
  → 总耗时: 4-6 秒，Toast 大概率已消失

优化后（快，能捕获 Toast）:
  1. click 提交按钮 + 立即 eval 检测（合并为一步）
  
  具体模式:
    # 一键提交+检测（推荐）
    agent-browser eval "
      (() => {
        // 1. 点击提交
        const dialog = document.querySelector('.el-dialog__wrapper:not([style*=\"display:none\"]) .el-dialog');
        const btn = dialog.querySelector('.el-button--primary');
        btn.click();
        
        // 2. 轮询检测结果（最多 3 秒）
        return new Promise(resolve => {
          let checks = 0;
          const timer = setInterval(() => {
            checks++;
            // 检测: dialog 关闭? toast 出现? 列表变化?
            const dialogGone = !document.querySelector('.el-dialog__wrapper:not([style*=\"display:none\"])');
            const sel = '.el-message, .el-notification, .el-message-box';
            const toast = document.querySelector(sel);
            
            if (dialogGone || (toast && toast.offsetParent !== null) || checks > 15) {
              clearInterval(timer);
              resolve(JSON.stringify({
                dialogClosed: dialogGone,
                toast: toast ? toast.textContent.trim().substring(0, 200) : null,
                checks: checks
              }));
            }
          }, 200);
        });
      })()
    "
  
  2. AI 直接读返回值判断结果，无需额外 snapshot
     - dialogClosed=true → 操作成功
     - toast 包含"成功" → 操作成功
     - toast 包含"失败"/"错误" → 操作失败
     - 都不满足 → 再 snapshot 诊断
  → 总耗时: 0.5-3 秒，Toast 几乎 100% 捕获

简化版（不支持 Promise 的环境）:
  # 分两步：先提交，立即 eval 检测
  步骤 1: click 提交
  步骤 2: eval 立即检测 toast/dialog（不等！）
  步骤 3: 如果有 toast → 记录结果
  步骤 4: 如果无 toast 但 dialog 关闭 → 记录成功
  步骤 5: 如果都不满足 → snapshot 诊断

验证信号优先级（从快到慢）:
  1. eval 检测 toast 文本（< 100ms，最可靠）
  2. eval 检测 dialog 是否关闭（< 100ms）
  3. eval 检测列表行数变化（< 100ms）
  4. snapshot 完整探查（1-2s，兜底）
```

---

### 场景 16：Element UI Message-Box 确认弹窗（el-message-box）

**特征**：Element UI 的 `this.$confirm()` / `this.$msgbox()` 创建的确认弹窗，
渲染在 `document.body` 下的 `.el-message-box__wrapper` 中。

```yaml
检测方式:
  - snapshot 中出现 "是否要删除" / "确认" 文本 + 取消/确定按钮
  - DOM: .el-message-box__wrapper > .el-message-box

⚠️ 已知坑点（已验证）:
  确定按钮对以下交互方式均不响应:
    ❌ agent-browser click @ref          — 无效果
    ❌ JS .click()                       — 无效果
    ❌ MouseEvent dispatch               — 无效果
    ❌ Vue __vue__.handleClick() 调用    — 无效果
  
  唯一有效的方式:
    ✅ agent-browser press Enter         — 触发默认按钮（确定）
    原因: el-message-box 内部通过键盘事件监听 Enter 键来触发
          Promise resolve，DOM click 被组件内部拦截/忽略

处理策略（严格按顺序）:
  策略 1: 直接按 Enter（首选，已验证有效）
    agent-browser press Enter

  策略 2: 查找 message-box 的 Vue 实例并 resolve Promise
    # 兜底方案（如果 Enter 无效）
    const wrapper = document.querySelector('.el-message-box__wrapper');
    const vm = wrapper.__vue__;
    // 查找内部 action callback 并调用

  策略 3: 按 ESC 关闭（放弃操作）
    agent-browser press Escape

注意:
  - 必须先确认弹窗已出现再按 Enter
  - 按 Enter 后立即检测: 弹窗消失 + 操作结果（Toast/列表变化）
  - 此坑点同样适用于 Element UI 的 el-popconfirm 组件
```

---

### 场景 4：加载状态（Spinner / Skeleton / ProgressBar）

**特征**：页面加载过程中出现加载指示器，完成后消失。

```yaml
检测方式:
  - Web: snapshot 中出现 spinner/loading/skeleton 类元素
  - iOS: page_source 中出现 ActivityIndicator / ProgressView
  - Android: page_source 中出现 ProgressBar / ProgressDialog

处理策略:
  1. 加载指示器出现时:
     - 进入等待模式（不探查，只轮询检查加载指示器是否消失）
     - 轮询间隔: 每 500ms 检查一次（低成本探查）
     - 加载指示器消失 → 完整探查（高成本）→ 继续执行

  2. 超时处理:
     - 加载指示器超过 15 秒未消失 → 高成本探查
     - 探查结果: 页面卡死 → 标记环境问题
     - 探查结果: 加载指示器是装饰性的（不消失）→ 忽略，继续执行

  3. 特殊处理:
     - 骨架屏（Skeleton Screen）→ 等待真实内容出现
     - 进度条（ProgressBar）→ 等待进度到 100%
     - 无限加载（Infinite Scroll）→ 等待第一批内容出现即可

示例:
  - 进入列表页 → 骨架屏出现
  - AI 检测: 骨架屏可见 → 进入等待模式
  - 每 500ms 检查一次 → 骨架屏消失 → 完整探查
  - 列表数据已加载 → 继续执行
```

---

### 场景 5：页面跳转 / 导航

**特征**：URL 变化、页面完全刷新、SPA 路由切换。

```yaml
检测方式:
  - Web: URL 变化 / document.readyState 变化 / SPA 路由变化
  - iOS: NavigationBar title 变化 / 新页面 push
  - Android: Activity 变化 / 新页面启动

处理策略:
  1. 页面跳转时:
     - 必须完整探查（高成本）— 新页面的元素完全不同
     - 等待新页面加载完成（参考 §三 加载完成判断）
     - 验证是否跳转到预期页面（URL/标题/关键元素）

  2. SPA 路由切换:
     - URL 变化但页面未完全刷新 → 仍需完整探查
     - 部分 SPA 保留 header/footer → 只探查内容区域

  3. 特殊处理:
     - 跳转到外部链接 → 可能需要切换 Tab/窗口
     - 跳转到下载链接 → 处理文件下载
     - 跳转失败（404/500）→ 截图 + 标记环境问题

示例:
  - 点击"查看详情" → URL 从 /list 变为 /detail/123
  - AI 检测: URL 变化 → 完整探查（高成本）
  - 等待新页面加载 → 确认详情页已显示
  - 继续执行详情页的用例步骤
```

---

### 场景 6：空状态 / 无数据

**特征**：页面正常加载但没有数据，显示空状态提示。

```yaml
检测方式:
  - Web: snapshot 中出现 "暂无数据" / "空列表" / "搜索无结果" 等文本
  - iOS: page_source 中出现 "No results" / "Empty" label
  - Android: page_source 中出现 "暂无数据" / "空空如也" text

处理策略:
  1. 空状态出现时:
     - 判断: 是预期空状态（如首次使用/条件过滤无结果）还是异常空状态（如数据未加载）
     - 预期空状态 → 截图 + 标记 PASS（空状态本身是测试点）
     - 异常空状态 → 截图 + 标记 FAIL（数据未加载）

  2. AI 判断依据:
     - 如果操作是"搜索无结果的关键词" → 预期空状态
     - 如果操作是"查看已有数据的列表" → 异常空状态
     - 如果操作是"首次进入空列表" → 预期空状态

  3. 空状态作为异常测试的必测项:
     - 每个查询/搜索功能必须包含空数据测试（一条不存在条件的查询）
     - 验证空状态的UI展示：占位图、友好提示文本、无JS报错

示例:
  - 搜索"不存在的书籍" → 显示"搜索无结果"
  - AI 判断: 预期空状态（搜索的是不存在的内容）
  - 截图 + 标记 PASS
```

---

### 场景 7：分页 / 懒加载 / 滚动加载

**特征**：内容分多页显示，需要点击翻页或滚动加载更多。

```yaml
检测方式:
  - Web: 分页组件（页码/上一页/下一页）/ 滚动加载触发器
  - iOS: 列表底部 "加载更多" / 滚动触发加载
  - Android: 列表底部 "加载更多" / 滚动触发加载

处理策略:
  1. 分页操作:
     - 点击"下一页" → 等待新数据加载（正常等待 3-8s）
     - 点击页码 → 等待页面刷新
     - 验证: 新数据已加载 + 分页组件状态更新

  2. 滚动加载:
     - 滚动到列表底部 → 等待新内容出现（快速等待 0-3s）
     - 如果新内容未出现 → 再次滚动（可能触发距离不够）
     - 如果多次滚动无新内容 → 标记"已加载全部"

  3. 特殊处理:
     - 分页后页面回到顶部 → 需要重新定位操作元素
     - 滚动加载导致 DOM 元素增多 → snapshot 变大，注意性能
     - 无限滚动 → 设置最大滚动次数（防止死循环）

示例:
  - 列表第 1 页显示 20 条 → 点击"下一页"
  - AI 等待（正常等待 3-8s）→ 列表刷新为第 2 页数据
  - 验证: 数据不同 + 页码变为 2
  - 继续执行第 2 页的用例
```

---

### 场景 8：Iframe / WebView / 内嵌页面

**特征**：页面中包含 iframe 或 WebView，内容独立于主页面。

```yaml
检测方式:
  - Web: snapshot 中出现 iframe / frame 元素
  - iOS: page_source 中出现 WKWebView / UIWebView
  - Android: page_source 中出现 WebView

⛔ 禁止做法:
  - ❌ 不要通过 eval 进入 iframe 上下文操作（agent-browser 无法直接操作 iframe 内元素）
  - ❌ 不要用 document.querySelectorAll('iframe')[N].contentDocument 跨域访问

✅ 推荐做法（Web 平台）: 在新标签页打开 iframe 的 src URL

处理策略（Web 平台）:
  1. 提取 iframe src:
     agent-browser eval "
     (() => {
       const iframes = document.querySelectorAll('iframe');
       const urls = [];
       for (const f of iframes) {
         urls.push({ src: f.src, id: f.id, name: f.name, visible: f.offsetParent !== null });
       }
       return JSON.stringify(urls);
     })()
     "
  
  2. 判断 iframe 内容是否需要测试:
     - iframe src 与当前测试相关 → 在新标签页打开
     - iframe src 是第三方/无关内容 → 跳过
     - iframe 无 src（srcdoc/内联内容）→ 标记为工具限制，记录到报告

  3. 在新标签页打开 iframe src:
     # 用 agent-browser tab new 在当前浏览器会话中新建标签页
     # 优势: 复用已有登录态/Cookie，无需重新登录
     agent-browser tab new "<iframe_src_full_url>"
     
     # 等待新标签页加载完成
     agent-browser snapshot -i -c -d 3 --json
     
     # ⚠️ 注意: iframe src 可能是相对路径，需要拼接主页面 origin
     # 示例: src="/admin/config" → agent-browser tab new "https://test.example.com/admin/config"
  
  4. 在新标签页中使用标准 snapshot-ref 流程:
     - agent-browser snapshot -i -c -d 3 --json
     - 按 ref 操作: agent-browser click "@e5"
     - 操作完成后 snapshot 验证

  5. 操作完成后切回主页面:
     # 方式 A: 关闭当前标签页自动回到上一个标签页（推荐）
     agent-browser tab close
     
     # 方式 B: 切换到指定标签页
     agent-browser tab switch 0
     
     # 验证已回到主页面
     agent-browser snapshot

  6. 跨页面数据关联:
     - 在新标签页操作产生的结果（如配置保存）→ 切回主页面刷新验证
     - 异步更新（如配置需要等待生效）→ 等待后刷新主页面

APP 平台（iOS/Android）:
  - 仍使用 driver.switch_to.frame / driver.switch_to.context('WEBVIEW')
  - APP 内的 WebView 不支持"新标签页打开"

⚠️ 注意事项:
  - agent-browser tab new 在当前会话中打开，自动复用登录态和 Cookie
  - 如果 iframe src 跨域不可访问 → 标记为工具限制，记录到报告
  - 多个 iframe → 逐个新建标签页处理，每次用 tab close 返回主页面
  - tab switch 0 回到第一个标签页（通常是主页面）

示例:
  场景: 主页面是配置管理，iframe 中嵌入了一个表单编辑器
  处理流程:
    1. 主页面 snapshot → 发现 iframe src="/editor/form-builder"
    2. agent-browser tab new "https://test.example.com/editor/form-builder"
    3. 新标签页 snapshot → 按 ref 操作表单
    4. agent-browser tab close → 回到主页面
    5. 主页面刷新 → 验证配置已生效
    5. 主页面刷新 → 验证配置已生效
```

---

### 场景 9：文件上传 / 下载

**特征**：触发系统级文件对话框，需要处理文件选择。

```yaml
检测方式:
  - Web: click input[type=file] / drag-drop 区域
  - iOS: 系统文件选择器 / DocumentPicker
  - Android: 系统文件选择器 / SAF (Storage Access Framework)

处理策略:
  1. 文件上传:
     - 通过 input[type=file] 直接 send_keys 文件路径（绕过系统对话框）
     - 如果无法绕过 → 标记"需要人工处理"
     - 上传后等待（慢速等待 8-15s）→ 确认上传成功

  2. 文件下载:
     - 点击下载按钮 → 等待下载完成
     - 检查下载目录是否有新文件
     - 验证文件名/大小符合预期

  3. 特殊处理:
     - 大文件上传（>10MB）→ 等待时间加倍
     - 批量文件上传 → 等待所有文件上传完成
     - 上传失败 → 检查错误提示

示例:
  - 点击"上传文件" → input[type=file] 出现
  - AI 直接 send_keys 文件路径（绕过系统对话框）
  - 等待上传完成（慢速等待 8-15s）→ 确认"上传成功"提示
```

---

### 场景 10：Tab 切换 / 标签页

**特征**：点击 Tab 切换内容区域，页面 URL 不变但内容变化。

```yaml
检测方式:
  - Web: snapshot 中出现 tab / tab-bar / nav-tabs 元素
  - iOS: page_source 中出现 TabBar / SegmentedControl
  - Android: page_source 中出现 TabLayout / TabWidget

处理策略:
  1. Tab 切换时:
     - 点击目标 Tab → 等待内容切换（快速等待 0-3s）
     - 必须重新探查（Tab 内容完全不同）
     - 验证: 目标 Tab 处于激活状态 + 对应内容已显示

  2. 特殊处理:
     - Tab 内容懒加载 → 切换后可能需要额外等待
     - Tab 数量动态变化 → 重新探查 Tab 列表
     - Tab 切换触发 URL 变化（#hash）→ 按页面跳转处理

示例:
  - 当前在"全部"Tab → 点击"待审核"Tab
  - AI 等待（快速等待 0-3s）→ Tab 内容切换
  - 验证: "待审核"Tab 处于激活状态 + 待审核列表已显示
```

---

### 场景 11：SegmentedControl / 分段控件（Ant Design Segmented）

**特征**：Ant Design `<Segmented>` 组件渲染为 `radiogroup`，包含多个 `radio` 选项。常见场景如"全部/只显示推荐"、"全部/只显示独家"。

```yaml
检测方式:
  - Web: snapshot 中出现 role=radiogroup + radio 元素
  - 常见 class: .ant-segmented / .ant-segmented-group

处理策略:
  ⛔ agent-browser click @ref 对此组件通常无效！
    原因: Ant Segmented 内部使用 label + 隐藏 input 结构，
    click 可能命中 label 但组件内部状态未同步。

  优先策略（必须按顺序尝试）:
    策略 1: JS eval 直接点击 .ant-segmented-item-label（首选，已验证有效）
      agent-browser eval "
      (() => {
        document.querySelectorAll('.ant-segmented-item-label').forEach(l => {
          if (l.textContent.trim() === '目标文本') l.click();
        });
        return 'done';
      })()
      "

    策略 2: JS eval 点击对应 radio 元素
      agent-browser eval "
      (() => {
        const radios = document.querySelectorAll('[role=radio]');
        for (const r of radios) {
          if (r.getAttribute('aria-label')?.includes('目标') || r.nextSibling?.textContent?.includes('目标')) {
            r.click();
            return 'clicked';
          }
        }
        return 'not found';
      })()
      "

    策略 3: 点击 label 文本（如果前两个都失败）
      agent-browser find text "目标文本" click

  验证:
    - 操作后必须检查 radio checked 状态（agent-browser is checked @ref）
    - 检查页面数据是否随之更新（如列表数量变化）

  注意:
    - 页面上可能有多个 Segmented 控件（如"推荐"+"首发"+"独家"），
      必须通过文本内容精确定位目标控件
    - click 后立即等待 2-3s，让页面数据刷新
```

---

### 场景 12：Portal 渲染的 Dropdown Option（Ant Design Select）

**特征**：Ant Design `<Select>` 的下拉选项通过 Portal 渲染到 `document.body` 下，
不在 combobox 元素的 DOM 子树中。agent-browser `snapshot` 能看到 option，
但 `click @ref` 可能因 DOM 层级问题而失效。

```yaml
检测方式:
  - 点击 combobox 后 snapshot → 出现 listbox + option 元素
  - option ref 在 snapshot 中存在，但 click 后无响应

处理策略（必须按顺序尝试）:
  策略 1: 点击 option 的 ref（如果可用）
    agent-browser click @ref_of_option

  策略 2: JS 查找并点击（Portal 渲染时首选）
    agent-browser eval "
    (() => {
      // Ant Select 下拉渲染在 body > .ant-select-dropdown 中
      const options = document.querySelectorAll('.ant-select-item-option-content');
      for (const o of options) {
        if (o.textContent.trim() === '目标选项文本') {
          o.closest('.ant-select-item-option')?.click();
          return 'clicked';
        }
      }
      return 'not found: ' + options.length + ' options';
    })()
    "

  策略 3: 键盘操作（如果 JS click 也失败）
    agent-browser press ArrowDown  # 导航到目标选项
    agent-browser press Enter      # 选中

  验证:
    - 检查 combobox 显示的文本是否变为目标值
    - 检查关联数据是否更新

  注意:
    - 必须先点击 combobox 打开下拉，再执行本文策略
    - 如果 .ant-select-dropdown 未出现，说明下拉未打开，需重新点击 combobox
```

---

### 场景 13：交互卡住 / 死循环 — 强制跳过机制

**特征**：同一操作步骤反复尝试无法完成，消耗大量时间但无进展。

```yaml
触发条件（任一满足即触发跳过）:
  - 同一元素/操作的交互失败 ≥ 3 次（click/fill/select 等）
  - 同一测试步骤耗时超过 3 分钟
  - 连续 5 次 eval/snapshot 后页面状态无任何变化
  - 同一自定义组件（select-all / popover-based 组件）交互失败 ≥ 2 次

跳过流程:
  1. 记录跳过原因:
     - 哪个用例、哪个步骤卡住
     - 尝试了哪些交互方式（DOM click / Vue 实例 / 坐标点击）
     - 每次失败的具体现象
     - 推断的根本原因（组件类型 / DOM 销毁重建 / 作用域错误等）

  2. 清理当前状态:
     - 关闭所有弹窗（点击取消/ESC）
     - 如弹窗无法关闭 → 刷新页面
     - 恢复到用例前置条件状态

  3. 标记用例:
     用例标记为: ⏭️ SKIP — 交互阻塞
     skip_reason: 详细描述卡住原因和建议的解决方案
     
  4. 继续执行:
     - 立即跳到下一条独立用例（不依赖当前用例结果的）
     - 不等待、不重试、不死循环
     - 所有跳过的用例在 Phase 3b 最后汇总列出

  5. 事后处理:
     - 所有用例执行完毕后，列出跳过的用例清单
     - 判断: 是否可以换个策略重试？（如换数据组合避免重复）
     - 如无法重试 → 标记为最终 SKIP，写入报告
     - 如可以重试 → 在 Phase 3b 末尾统一重试
```

### 场景 13.5：弹窗与页面元素混淆 — 作用域强制检查

**特征**：页面上存在弹窗（`.ant-modal`）时，弹窗内有同名的输入框/下拉框和搜索区里的一模一样，
导致直接在 document 级别查找元素时定位到错误元素。

```yaml
触发条件（只要页面有弹窗就自动触发）:
  - document.querySelector('.ant-modal') !== null
  - document.querySelector('.ant-modal-mask') !== null

强制规则（必须严格执行，不可跳过）:
  1. 所有元素查找必须限定在 .ant-modal 内或明确限定在弹窗外部
  2. 禁止使用无作用域限定的 document.querySelector 查找弹窗内元素
     ❌ document.querySelector('input#storyCode')
     ✅ document.querySelector('.ant-modal input#storyCode')
     ✅ document.querySelector('input#storyCode')（确定当前无弹窗时）

  3. 禁止使用弹窗打开前的 snapshot ref 操作弹窗内元素
     ❌ agent-browser type @e168 "xxx"（e168 可能变成搜索框）
     ✅ agent-browser eval "document.querySelector('.ant-modal input#storyCode')?.focus()"
     ✅ agent-browser keyboard type "TCDN001"

  4. snapshot 后必须仔细检查 ref 归属:
     - 弹窗内的 input placeholder 通常是"请输入XXX"
     - 搜索区的 placeholder 通常是"代号" / "名称"
     - 弹窗被 generic "Close 新增短剧..." 包裹
     - 搜索区被导航/菜单包裹

  5. 每次弹窗打开后必须重新 snapshot 获取最新 refs

执行检查（每次操作前自我审查）:
  - 当前页面有弹窗吗？→ 有 → 操作目标是弹窗内还是页面上？
  - 操作弹窗内 → .ant-modal 限定
  - 操作页面上 → 确保选择器不命中弹窗内
  - 不确定 → 先 eval 检查 document.querySelectorAll 的数量

Ant Design 表单提交失败时的排查方向:
  1. 检查字段校验错误: .ant-form-item-explain-error
  2. 检查全局消息: .ant-message-notice  
  3. 检查保存按钮状态: disabled
  4. 检查表单实际值 vs 显示值（React 状态 vs DOM 值可能不一致）
  5. 如以上都正常仍不提交 → 标记 SKIP（工具限制）+ 继续下一条用例
```

---

### 场景 14：自定义多选/单选组件（select-all / popover-based）

**特征**：非标准 HTML select，使用 div+popover 实现的下拉选择组件。
常见模式：`select-all` container → `el-popover__reference` 触发区 → Portal 渲染的 `selectDataBox` 下拉面板 → `exactAreaClassName` 选项。

```yaml
检测方式:
  - snapshot 中 select/combobox 的选项不在自身 DOM 子树中
  - 选项渲染在 Portal 层（body 下的独立 div）
  - 常见 class: select-all, selectDataBox, exactAreaClassName, el-popover__reference

处理策略（必须按顺序尝试，每层最多 2 次）:

  层级 1: DOM click（首选，需正确的作用域限定）
    # 必须限定在弹窗/iframe 范围内！
    const dialog = document.querySelector('.el-dialog__wrapper:not([style*="display:none"]) .el-dialog');
    const popRef = dialog.querySelectorAll('.select-all')[N].querySelector('.el-popover__reference');
    popRef.click();  // 打开下拉
    
    # 查找可见的 selectDataBox 并点击选项
    const boxes = document.querySelectorAll('.selectDataBox');
    for (const box of boxes) {
      if (box.offsetParent !== null) {
        const items = box.querySelectorAll('.exactAreaClassName');
        items[M].querySelector('span').click();
        break;
      }
    }
    
    ⚠️ 关键: 必须在同一个 eval 中完成"打开+点击"，因为 eval 结束后 DOM 可能被重建
    ⚠️ 点击后立即检查: item.classList.contains('checked_s') 或 check-icon display !== 'none'

  层级 2: Vue 实例直接操作（DOM click 失败时使用）
    # 查找 select-all 组件中带 select() 方法的 Vue 实例
    const selectAll = dialog.querySelectorAll('.select-all')[N];
    const children = selectAll.querySelectorAll('*');
    for (const c of children) {
      if (c.__vue__ && typeof c.__vue__.select === 'function') {
        c.__vue__.select(TARGET_VALUE);  // 直接调用组件的 select 方法
        break;
      }
    }
    
    ⚠️ 注意: 调用 Vue select 后可能需要额外更新显示的 input 值

  层级 3: Form Model 直接赋值（前两层都失败时使用）
    # 直接修改 el-form 的 Vue model
    const form = dialog.querySelector('.el-form');
    form.__vue__.model.fieldName = TARGET_VALUE;
    
    # 然后直接调用父组件的提交方法或点击提交按钮
    # 注意: model 赋值可能不触发 Vue 响应式更新，需验证

  层级 4: 放弃 + 跳过（前三层都失败时）
    # 不要再继续尝试！
    # 标记用例为 SKIP，记录失败原因
    # 原因可能是: 组件结构特殊 / DOM 频繁重建 / 事件绑定方式未知

防卡死规则:
  - 层级 1 失败 2 次 → 立即跳到层级 2，不反复尝试层级 1
  - 层级 2 失败 2 次 → 立即跳到层级 3
  - 层级 3 失败 1 次 → 立即跳到层级 4（放弃）
  - 总交互次数（所有层级）> 8 次 → 强制跳过
  - 总耗时 > 3 分钟 → 强制跳过
```

---

## 七、工具适配注意

```yaml
工具差异:
  - Web 使用 agent-browser CLI:
    - 探查: agent-browser snapshot
    - 验证: agent-browser eval "document.querySelector('...').textContent"
    - 等待: 轮询 snapshot 检查目标元素是否出现
  - iOS/Android 使用 Appium WebDriver:
    - 探查: driver.page_source
    - 验证: driver.find_element(By.XPATH, '...')
    - 等待: WebDriverWait(driver, timeout).until(...)
  
  禁止在 Web 场景使用 Selenium 风格的 driver.xxx 命令，
  必须使用 agent-browser 的 snapshot / eval / click / fill 命令。

交互兜底规则（当 agent-browser click @ref 无效时）:
  - Ant Design Segmented 组件:
    agent-browser click @ref 对 .ant-segmented-item-label 通常无效，
    必须降级为 agent-browser eval JS .click()
  
  - Ant Design Select 下拉选项:
    选项通过 Portal 渲染在 body 下，click @ref 可能失效，
    优先使用 agent-browser eval 查找 .ant-select-item-option 并 click()
  
  - 通用规则:
    如果 click @ref 连续 2 次不生效（元素状态未变化），
    立即改用 eval JS .click()，不要反复尝试 click @ref
```

---

## 八、深度测试矩阵——防止"只探查不测试"

### 问题

AI 容易在交互探索阶段发现大量页面元素和功能点，但**对每个功能点的
深度测试不足**，停留在"探查→记录"循环。用户反馈的核心问题就是
"只做了探查，没有深度测试"。

### 深度测试定义

```yaml
# 每个被探查发现的功能点，必须完成以下测试矩阵：

测试矩阵（+ = 必须测试，○ = 可选，— = 不需测试）:

功能类型   | 正常流 | 边界值 | 组合场景 | 异常流 | 数据验证
----------|--------|--------|----------|--------|---------
筛选条件   |   +    |   +    |    +     |   +    |   —
排序       |   +    |   —    |    +     |   —    |   +    
报表表格   |   +    |   —    |    —     |   +    |   +    
导出       |   +    |   —    |    —     |   +    |   ○    
搜索       |   +    |   +    |    —     |   +    |   —    
表单输入   |   +    |   +    |    ○     |   +    |   —    
配置修改   |   +    |   —    |    ○     |   +    |   —    
数据源切换 |   +    |   —    |    +     |   —    |   —    
```

### 深度测试示例（报表类）

```yaml
筛选条件功能:
  ✅ 正常流: 设置单个筛选条件查询，返回正确结果
  ✅ 边界值: 最小值=0、最大值=最大数据的边界
  ✅ 组合场景: 时间+短剧+消耗区间 三重组合
  ✅ 异常流: 空数据时间范围、负数值、超长日期范围

排序功能:
  ✅ 正常流: 点击表头排序（降序）
  ✅ 组合场景: 先排序再筛选、排序后改变筛选条件
  ✅ 数据验证: 行序是否符合排序规则（升序/降序）

表格数据:
  ✅ 正常流: 查询返回多行数据
  ✅ 异常流: 空数据展示
  ✅ 数据验证: 
     - CPM = 消耗 / 展示数 × 1000  # 计算验证
     - CTR = 点击数 / 展示数       # 计算验证
     - CVR = 转化数 / 点击数        # 计算验证
     - 7日综合ROI = 7日综合流水 / 总消耗  # 核心指标验证

导出功能:
  ✅ 正常流: 有数据时导出，触发下载
  ✅ 异常流: 空数据时导出（预期：无文件/提示无数据）
```

### 深度测试的验证深度

```yaml
# 不同功能类型的验证深度：

L1 — UI 可见性:
  - 元素出现/消失
  - 文本正确显示
  - 组件状态变化
  适用: 配置修改、Tab切换、弹窗

L2 — 功能正确性:
  - 操作结果符合预期
  - 数据变化正确
  - 页面跳转正确
  适用: 筛选、搜索、表单提交

L3 — 数据/计算正确性:
  - 数值公式计算验证
  - 前后数据一致
  - 聚合/汇总逻辑正确
  适用: 报表、统计、财务类功能
  
L4 — 组合/联动正确性:
  - 多个条件同时作用
  - 条件之间无冲突
  - 排列组合结果可预期
  适用: 多条件筛选、级联下拉、排序+筛选
```

### 深度测试防漏检查清单

```yaml
执行用例前逐项检查:
  - [ ] 每个筛选器都做了至少 1 条正常查询 + 1 条异常查询吗？
  - [ ] 每个排序字段都验证了升序 AND 降序吗？
  - [ ] 计算指标（CPM/CTR/CVR/ROI）验证了公式吗？
  - [ ] 配置修改后是否恢复并验证了恢复结果？
  - [ ] 功能组合（如筛选+排序、多条件筛选）测试了吗？
  - [ ] 空数据/无效输入场景覆盖了吗？
  - [ ] 至少做了 1 条端到端查询验证（用户完整操作路径）？
```

---

## 九、历史操作数据缓存

### 目的

记录每次执行中的操作耗时、交互方式成功率，供后续 AI 决策参考。

> **命名说明**: 本文件使用 `execution_history.json` 记录**按操作类型聚合的统计数据**（如"click_segmented_control 平均耗时 2500ms"）。
> 与此不同，`common/phase4-report.md` 定义的 `case_execution_log.json` 记录**每条用例的详细执行步骤**（逐步骤记录）。
> 两者互补: `execution_history.json` 用于 AI 预测和策略选择，`case_execution_log.json` 用于报告生成和结果追溯。

### 缓存文件

```yaml
# 存储在 {spec目录}/execution_history.json
# 每次 Phase 3b 执行时增量更新
```

### 数据结构

```json
{
  "version": "1.0",
  "updated": "2026-05-15T17:00:00Z",
  "operations": {
    "login": {
      "avg_duration_ms": 8500,
      "min_ms": 5000,
      "max_ms": 15000,
      "count": 5,
      "success_rate": 1.0
    },
    "click_segmented_control": {
      "avg_duration_ms": 2500,
      "min_ms": 1500,
      "max_ms": 4000,
      "count": 8,
      "success_rate": 0.875,
      "preferred_method": "eval_js_click",
      "methods": {
        "click_ref": { "count": 8, "success": 2, "rate": 0.25 },
        "eval_js_click": { "count": 6, "success": 6, "rate": 1.0 }
      }
    },
    "click_ant_select_dropdown": {
      "avg_duration_ms": 4000,
      "count": 10,
      "success_rate": 0.3,
      "preferred_method": "eval_find_dropdown_option",
      "methods": {
        "click_ref": { "count": 10, "success": 1, "rate": 0.1 },
        "eval_find_dropdown_option": { "count": 5, "success": 3, "rate": 0.6 },
        "keyboard_navigate": { "count": 2, "success": 1, "rate": 0.5 }
      }
    },
    "page_navigation": {
      "avg_duration_ms": 3000,
      "count": 20,
      "success_rate": 0.95
    },
    "form_fill": {
      "avg_per_field_ms": 500,
      "count": 30,
      "success_rate": 1.0
    }
  },
  "pages": {
    "https://drp-test.changdu.ltd/operate/playlet-best-reels": {
      "avg_load_ms": 3500,
      "min_ms": 2000,
      "max_ms": 6000,
      "element_count_avg": 350,
      "visits": 3
    }
  }
}
```

### AI 如何使用缓存

```yaml
AI 决策时查询 execution_history.json:
  等待时间预测:
    - 查询 operations.{操作类型}.avg_duration_ms → 作为初始等待时间
    - 查询 pages.{URL}.avg_load_ms → 作为页面加载预期时间
    - 如果无历史数据 → 使用 execution-optimization.md §二 默认值

  交互方式选择:
    - 查询 operations.{操作类型}.preferred_method → 优先使用成功率最高的方式
    - 例: click_segmented_control.preferred_method = "eval_js_click"
      → AI 直接用 eval JS click，跳过 click @ref 尝试
    - 如果无历史数据 → 按 §七 兜底规则依次尝试

  风险预警:
    - success_rate < 0.5 → AI 标记为"高风险操作"，准备兜底方案
    - success_rate = 0 → AI 跳过该操作方式，直接问用户或标记失败

更新时机:
  - 每次 Phase 3b 用例执行完成后，AI 更新对应操作的耗时和成功率
  - 每次 Phase 4 报告生成前，AI 确保 execution_history.json 已保存
  - 新项目首次运行 → 创建空 execution_history.json，纯靠默认策略
```