# Android 交互探索阶段 — 系统性页面元素发现

> **定位**：Android 平台的探索流程。通用骨架见 `common/exploration.md`（唯一权威来源），本文件只补充 Android 差异化内容。
> 
> **核心引用链**：
> - 探索流程 6 步 + AI 职责 + 结果格式 + 熔断 + 反馈链路 → `common/exploration.md` §一~§八
> - 用例补充规则 → `common/discovery-feedback.md`
> - Phase 1.4 补充模式 → `common/phase1-analyze.md` § Phase 1.4
> - 执行策略 → `android/phase3-execute.md` §〇
> - 通用测试要点参考 → `common/测试知识库.md`（探索时可参照该文件识别遗漏的测试类型）

---

## 一、Android 差异化元素选择器

```yaml
# 补充 common/exploration.md §二 步骤 2 的元素识别：
Android 元素选择器:
  从 Appium page_source (UIAutomator2) 中找出所有可交互元素：
    - android.widget.Button（按钮）
    - android.widget.TextView（可点击的文本 — 需检查 clickable=true）
    - android.widget.ImageButton（图片按钮）
    - android.widget.EditText（输入框）
    - TabLayout / BottomNavigationView（导航组件）
    - RecyclerView / ListView（列表 — 检查 item 是否可点击）
    - android.widget.Switch（开关控件）
    - android.widget.Spinner（下拉选择器）
    - android.widget.CheckBox / RadioButton（选择框）
    - NavigationView（侧边 Drawer 导航项）
```

---

## 二、Android 差异化交互方式

```yaml
# 补充 common/exploration.md §二 步骤 3~6 的交互方式：
Android 交互方式:
  点击操作:
    1. 优先: 通过 resource-id 定位 → driver.find_element(ID, "com.example:id/xxx").click()
    2. 备选: 通过 text 文本定位 → driver.find_element(XPATH, "//android.widget.Button[@text='xxx']").click()
    3. 通过 content-desc 定位 → driver.find_element(ACCESSIBILITY_ID, "xxx").click()
    4. 坐标点击: 通过元素 bounds 计算中心坐标
    # 通用 fallback 规则见 common/execution-optimization.md

  关闭弹窗/页面:
    - 优先: 点击 Dialog 中的取消按钮
    - 备选: driver.press_keycode(4)（Android BACK 键）
    - 仍失败: 切换 Fragment/Activity

  等待策略:
    # 详细等待策略见 common/execution-optimization.md §二
    - 弹窗出现: 最长 5 秒
    - Dialog/AlertDialog: 最长 3 秒
    - Activity 切换: 最长 5 秒
```

---

## 三、Android 差异化加载判断

```yaml
# 补充 common/exploration.md §二 步骤 1 的加载判断：
Android 加载完成判断:
  - ProgressBar 消失（正向信号）
  - 目标元素 text/content-desc 可见
  - Activity/Fragment 切换完成（page_source 中包名对应元素出现）
  - Toast "加载中" 消失
  # 详细加载判断见 common/execution-optimization.md §三 Android 平台
```

---

## 四、Android 权限弹窗自动处理

```yaml
Android 权限处理（探索阶段自动接受）:
  - 系统权限弹窗（permission dialog）：
    优先: driver.find_element(ID, "com.android.permissioncontroller:id/permission_allow_button").click()
  - 如果弹窗无标准 ID → 通过文本查找 "允许" / "Allow" → click()
  - 预授权（推荐）: adb shell pm grant {package} {permission}
  - 如果权限拒绝导致功能不可用 → 记录到 gaps，标注"权限限制"
```
