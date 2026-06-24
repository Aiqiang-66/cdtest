# Web 交互探索阶段 — 系统性页面元素发现

> **定位**：Web 平台的探索流程。通用骨架见 `common/exploration.md`（唯一权威来源），本文件只补充 Web 差异化内容。
> 
> **核心引用链**：
> - 探索流程 6 步 + AI 职责 + 结果格式 + 熔断 + 反馈链路 → `common/exploration.md` §一~§八
> - 用例补充规则 → `common/discovery-feedback.md`
> - Phase 1.4 补充模式 → `common/phase1-analyze.md` § Phase 1.4
> - 执行策略 → `web/phase3-execute.md` §〇.五
> - 通用测试要点参考 → `common/测试知识库.md`（探索时可参照该文件识别遗漏的测试类型）

---

## 〇、核心原则：先 snapshot，再操作

```yaml
# ⚠️ 这是 Web 探索的最高优先级原则，任何操作都必须遵守：

执行顺序（不可颠倒）:
  1. agent-browser snapshot -i -c -d 3 --json        ← 先探查
  2. AI 读取 snapshot 输出，理解当前页面结构         ← 再理解
  3. 从 snapshot 中找到目标元素的 ref                 ← 再定位
  4. agent-browser click "@e61" / type "@e68" "xxx"   ← 后操作

禁止的行为:
  ❌ 不经过 snapshot，直接用 eval document.querySelectorAll 查找元素
  ❌ 不经过 snapshot，直接用 eval Array.from...filter 点击元素
  ❌ 弹窗打开/关闭后，不重新 snapshot 就使用之前的 ref
  ❌ 先操作再 snapshot 事后确认（必须先 snapshot 确认当前状态再操作）

什么时候必须做 snapshot:
  - 每次用例开始前（确认页面状态）
  - 每次导航/跳转后（URL 变化）
  - 每次操作后（click/fill/type 之后确认结果）
  - 弹窗打开后（重新获取弹窗内元素的 ref）
  - 弹窗关闭后（确认弹窗已关，页面恢复）
  - 异常发生后（诊断当前页面状态）
  - 等待超时后（确认是加载慢还是卡死）

可以合并探查的场景:
  - 连续 fill/type 操作：填完所有字段后做一次 snapshot 验证
  - 连续 click 操作：完成所有点击后做一次 snapshot
```

---

## 一、Web 差异化元素选择器

```yaml
# ⚠️ 补充 common/exploration.md §二 步骤 2 的元素识别：
# 本节要素：从 snapshot 的 JSON 输出中识别元素，而不是从 DOM 中自己找

Web 元素选择器 — snapshot ref 识别:
  从 snapshot JSON 的 refs 对象中找出所有可交互元素：
    - refs.e1 ~ refs.eN 中的 button、a、menuitem、tab 等 role
    - 通过 refs 的 name 字段判断按钮功能（"新增短剧"、"批量导入"等）
    - 通过 refs 的 role 字段判断元素类型（button/link/menuitem）

  snapshot 输出示例中的识别方式:
    refs: {
      "e61": {"name": "plus 新增短剧", "role": "button"},
      "e59": {"name": "批量导入", "role": "button"},
      "e58": {"name": "下载模板", "role": "button"},
      "e87": {"name": "查 询", "role": "button"},
      "e172": {"name": "编辑", "role": "button"}
    }

  按钮文本匹配规则（从 refs 的 name 字段匹配）:
    - 新增类: name 包含 "新增"/"新建"/"添加"/"创建"/"Add"/"Create"
    - 编辑类: name 包含 "编辑"/"修改"/"Edit"/"Update"
    - 删除类: name 包含 "删除"/"移除"/"Delete"/"Remove"
    - 操作类: name 包含 "查询"/"搜索"/"保存"/"提交"/"导出"/"导入"
```

---

## 二、Web 差异化交互方式

```yaml
# ⚠️ 补充 common/exploration.md §二 步骤 3~6 的交互方式：
# 本节要素：先 snapshot 拿到 ref，用 ref 操作，失败才 fallback

Web 交互方式:
  点击操作的标准流程:
    步骤 1: snapshot 获取当前页面的 refs
      agent-browser snapshot -i -c -d 3 --json

    步骤 2: 从 snapshot JSON 的 refs 中定位目标按钮的 ref
      → 查看 refs.e61 = {"name": "plus 新增短剧", "role": "button"}
      → 确认目标为 @e61

    步骤 3: 用 ref 点击（@ref 必须加双引号）
      agent-browser click "@e61"

    步骤 4: 等待操作完成
      agent-browser snapshot -i -c -d 4 --json

    步骤 5: 从新 snapshot 确认操作结果
      → 弹窗是否出现？URL 是否变化？表格数据是否刷新？
      → 确认后在当前 snapshot 中继续找下一步目标

    操作失败时的 fallback 链（按顺序，每层最多 2 次）:
      层级 1: snapshot 重新探查 → 可能是 ref 过期了 → 重新定位
      层级 2: eval + CSS 选择器（只用于点击，不用于查找元素）
        agent-browser eval "document.querySelector('button:has(.anticon-plus)')?.click()"
      层级 3: eval + textContent（兜底）
        agent-browser eval "Array.from(document.querySelectorAll('button')).filter(b=>b.textContent.includes('新增短剧'))[0]?.click()"
      层级 4: 标记为交互失败，记录到 skip 清单

    # ⚠️ PowerShell 下 @ref 必须加双引号：
    #   ✅ agent-browser click "@e61"
    #   ❌ agent-browser click @e61（@e61 被当空变量，click 缺参数）

  Ant Design 表单输入:
    填写弹窗内输入框的标准流程:
      步骤 1: snapshot 获取弹窗 refs
        agent-browser snapshot -i -c -d 4 --json

      步骤 2: 从 refs 中找到输入框的 ref
        → refs.e168 = {"name": "请输入短剧代号", "role": "textbox"}

      步骤 3: 用 type ref 填写（@ref 加双引号）
        agent-browser type "@e168" "TCDN-TYPE"

      步骤 4: 验证值已写入
        agent-browser eval "document.querySelector('.ant-modal input#storyCode')?.value"

      注意:
        ⚠️ Ant Design 的 React 受控组件可能不识别 fill/type 的输入
        → fallback: eval focus + keyboard type
          agent-browser eval "document.querySelector('.ant-modal input#storyCode')?.focus()"
          agent-browser keyboard type "TCDN-TYPE"

  关闭弹窗:
    步骤 1: snapshot 获取弹窗 refs
      agent-browser snapshot -i -c -d 4 --json

    步骤 2: 从 refs 中找关闭按钮
      → button "Close" / button "取 消" / button "保 存"

    步骤 3: 用 ref 关闭
      agent-browser click "@e57"    # Close 按钮
      # 或
      agent-browser click "@e67"    # 取 消 按钮

    步骤 4: 确认弹窗已关闭
      agent-browser eval "!document.querySelector('.ant-modal')"

  等待策略:
    - 操作后先 snapshot，不是固定 sleep
    - 等待弹窗出现: snapshot 检查 .ant-modal 是否存在（最长 5 秒）
    - 等待数据加载: snapshot 检查 .ant-table-row 数量（最长 15 秒）
    - 等待页面切换: snapshot 检查 URL 变化（最长 5 秒）
    # 详细等待策略见 common/execution-optimization.md §二
```

---

## 二.一、弹窗元素 vs 页面元素区分规则（必须严格执行）

```yaml
# 问题：弹窗打开后 snapshot 的 ref 重新编号，之前获得的弹窗内元素的 ref
# 可能指向页面上同 placeholder 的搜索框而非弹窗内输入框。
# 例如：弹窗内 "请输入短剧代号" 的 ref=e168，弹窗关闭后点新增按钮再 snapshot，
# e168 可能变成页面搜索框 "代号"。

# 必须执行的规则：

关键区分点:
  1. snapshot 输出的包裹关系:
     - 弹窗内的元素被 generic "Close 新增短剧 ..." 包裹
       → 在 snapshot 文本中表现为缩进在 "Close 新增短剧..." 下
     - 页面元素被导航/搜索区包裹
       → 在 snapshot 文本中表现为缩进在 "畅读创作者后台..." 下
     - ⚠️ 弹窗打开后必须重新 snapshot，不能使用弹窗打开前获得的 ref

  2. placeholder 文本差异:
     - 弹窗内输入框: placeholder="请输入短剧代号"、"请输入短剧名称"
     - 搜索区输入框: placeholder="代号"、"名称"
     - snapshot 中通过 textbox 的 name 字段区分

  3. 操作弹窗内元素的正确方式:
     - 先 snapshot 获取弹窗 refs
     - 从 snapshot 的 refs 中确认目标 ref（在弹窗包裹范围内的）
     - 用 ref 操作（加双引号）
       agent-browser type "@e168" "TCDN-TYPE"
     - 如需用 CSS 选择器:
       弹窗内: document.querySelector('.ant-modal input#storyCode')
       页面上: document.querySelector('input#storyCode')

弹窗操作标准流程:
  1. snapshot -i -c -d 3 --json                    ← 探查页面
  2. 从 refs 中找到"新增"按钮的 ref                ← 定位目标
  3. click "@e61"                                  ← 点击弹窗按钮
  4. snapshot -i -c -d 4 --json                    ← 重新探查（获取弹窗 refs）
  5. 从新 snapshot 确认弹窗存在                     ← 确认结果
     → 有 generic "Close 新增短剧..." → 弹窗出现
     → 否则 → 可能点击失败，回 fallback 链

  弹窗内填值:
    6. 从新 snapshot 的 refs 中找到输入框 ref      ← 定位弹窗内元素
    7. type "@e168" "TCDN-TYPE"                    ← 填值
    8. snapshot 确认值已填入                         ← 验证
```

---

## 三、Web 差异化加载判断

```yaml
# ⚠️ 补充 common/exploration.md §三 的加载判断：
# 本节要素：通过 snapshot 判断页面是否加载完成，而不是用 eval 探测

Web 加载信号（通过 snapshot 判断）:
  - 弹窗出现: snapshot 中有 generic "Close 新增短剧..." 或 button "Close"
  - loading 消失: snapshot 中没有 button 含 "loading" class（需要时用 eval 补充）
  - 表格数据加载: snapshot 中出现 ant-table-row
  - 空数据: snapshot 中有 cell "暂无数据"
  - 页面切换: snapshot 中的 URL 变化
  - 分页加载: snapshot 中有 listitem "下一页"
```
