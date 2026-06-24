# iOS 交互探索阶段 — 系统性页面元素发现

> **定位**：iOS 平台的探索流程。通用骨架见 `common/exploration.md`（唯一权威来源），本文件只补充 iOS 差异化内容。
> 
> **核心引用链**：
> - 探索流程 6 步 + AI 职责 + 结果格式 + 熔断 + 反馈链路 → `common/exploration.md` §一~§八
> - 用例补充规则 → `common/discovery-feedback.md`
> - Phase 1.4 补充模式 → `common/phase1-analyze.md` § Phase 1.4
> - 执行策略 → `ios/phase3-execute.md` §〇
> - 通用测试要点参考 → `common/测试知识库.md`（探索时可参照该文件识别遗漏的测试类型）

---

## 一、iOS 差异化元素选择器

```yaml
# 补充 common/exploration.md §二 步骤 2 的元素识别：
iOS 元素选择器:
  从 Appium page_source (XCUITest) 中找出所有可交互元素：
    - XCUIElementTypeButton（按钮）
    - XCUIElementTypeLink（链接）
    - XCUIElementTypeTab（标签页）
    - XCUIElementTypeCell（列表项 — 可能可点击）
    - XCUIElementTypeTextField / XCUIElementTypeSecureTextField（输入框）
    - XCUIElementTypeTextView（文本视图 — 可编辑时）
    - XCUIElementTypePickerWheel（选择器滚轮）
    - XCUIElementTypeSwitch（开关控件）
    - XCUIElementTypeSegmentedControl（分段控件）
```

---

## 二、iOS 差异化交互方式

```yaml
# 补充 common/exploration.md §二 步骤 3~6 的交互方式：
iOS 交互方式:
  点击操作:
    1. 优先: 通过 accessibilityLabel 定位 → driver.find_element(ACCESSIBILITY_ID, label).click()
    2. 备选: 通过 XPath 定位 → driver.find_element(XPATH, "//XCUIElementTypeButton[@name='xxx']").click()
    3. 坐标点击: 通过参考元素坐标 + 偏移计算
    # 通用 fallback 规则见 common/execution-optimization.md

  关闭弹窗/页面:
    - 优先: 点击弹窗中的"取消"/"关闭"按钮（accessibilityLabel 匹配）
    - 备选: driver.back() 或左右滑动返回
    - 仍失败: 切换 Tab 后再回来

  等待策略:
    # 详细等待策略见 common/execution-optimization.md §二
    - 弹窗出现: 最长 5 秒
    - 确认弹窗（Alert/ActionSheet）: 最长 3 秒
    - 页面切换: 最长 5 秒
```

---

## 三、iOS 差异化加载判断

```yaml
# 补充 common/exploration.md §二 步骤 1 的加载判断：
iOS 加载完成判断:
  - ActivityIndicator 消失（正向信号）
  - NavigationBar title 稳定（不再变化）
  - 目标元素 label/name 可见
  - 页面无白屏/闪退
  # 详细加载判断见 common/execution-optimization.md §三 iOS 平台
```

---

## 四、iOS 权限弹窗自动处理

```yaml
iOS 权限处理（探索阶段自动接受）:
  - 系统权限弹窗（位置/通知/相机/相册/麦克风）：
    driver.execute_script("mobile: alert", {"action": "accept", "buttonLabel": "Allow"})
  - 如果弹窗无 Allow 按钮 → 查找 "OK" / "好" / "允许"
  - 如果权限弹窗已过期/缓存 → 跳过
  - 如果权限拒绝导致功能不可用 → 记录到 gaps，标注"权限限制"
```
