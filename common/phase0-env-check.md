# Phase 0：环境预检查与会话初始化

## 目的

验证所有依赖环境就绪，初始化会话连接，确保后续测试高效执行。

> ⛔ **关键规则**: Web 平台必须先检查 agent-browser 再初始化会话。禁止在 agent-browser 未就绪时尝试用 curl 猜测 API 登录。

---

## 通用检查项

| 检查项 | 检查方式 | 失败处理 |
|--------|----------|----------|
| Python依赖 | `pip list` 验证 pymysql, requests | 提示 `pip install pymysql requests` |
| 测试URL/APP可达性 | 连通性测试 | 标记环境不可用 |
| DB连接 | 连接测试 | 标记DB验证跳过 |
| **MCP知识库（mcporter）** | `mcporter list` — 验证 test-case-mcp 已注册 | **AI自动配置**（见下方 §MCP知识库自检） |
| spec/目录 | 检查需求文档存在 | 提示放置需求文档 |

---

## MCP知识库自检（Phase 0 必执行，在需求文档前置检查之后）

> **定位**：在任何 MCP 知识库操作之前，确保 mcporter 已安装并注册 test-case-mcp 服务器。未配置时 AI 自动完成配置，无需用户干预。

### 检查流程

```yaml
步骤 1 — 检查 mcporter 是否安装:
  命令: mcporter --version
  → 成功 → 继续步骤 2
  → 失败 → AI 提示用户安装 mcporter

步骤 2 — 检查 test-case-mcp 是否已注册:
  命令: mcporter list
  → 输出含 "test-case-mcp" → 继续步骤 3
  → 输出不含 "test-case-mcp" → AI 自动执行配置（步骤 2a）

步骤 2a — AI 自动注册（无需用户干预）:
  原理: 从 mcp-kb-sync.md 读取 MCP 端点 URL，自动执行 config add
  命令: mcporter config add test-case-mcp https://aiprd.changdu.vip/api/mcp/test-case-mcp-server/mcp
  → 成功 → 验证: mcporter list 应显示 "test-case-mcp (9 tools) ✓"
  → 失败 → 记录警告，后续 MCP 知识库操作跳过

步骤 3 — 验证 MCP 连接:
  命令: mcporter call test-case-mcp getTestCaseStatus
  → { configured: true, testCaseCount: N, ... } → 就绪，记录用例数到环境报告
  → { configured: false, ... } → MCP Server PostgreSQL 未配置，记录警告，MCP 操作跳过
  → 网络错误 → 记录警告，MCP 操作跳过

不可用时的处理:
  - 不影响测试执行和报告生成，仅跳过 MCP 入库步骤
  - 记录到环境检查报告的 warnings 字段
```

### 自动配置的端点来源

```yaml
# AI 从 mcp-kb-sync.md §一 读取端点 URL，无需用户提供:
端点: https://aiprd.changdu.vip/api/mcp/test-case-mcp-server/mcp
注册名: test-case-mcp（不可更改）
```

### 输出到环境报告

```json
{
  "mcp_kb": {
    "configured": true,
    "connected": true,
    "testCaseCount": 16,
    "auto_configured": false
  }
}
```

---

## 需求文档前置检查（Phase 0 必执行）

> **定位**：在任何测试操作之前，检查需求文档中是否提供了 Confluence pageId 和系统名称，用于最终测试用例入库到 MCP 知识库。缺失时立即提示用户，不等到 Phase 4 入库时才发现。
>
> 详细规则见 `common/mcp-kb-sync.md §二`。

### 检查项

| 检查项 | 检查方式 | 失败处理 | 用途 |
|--------|----------|----------|------|
| Confluence pageId | 从 spec/ 需求文档提取 | 提示用户提供 | 用例入库追溯 |
| 系统名称（system） | 从 spec/ 需求文档提取，匹配 40 个系统列表 | 提示用户从列表选择 | createTestCase 必填 |
| 业务类型（businessType） | 根据平台推断（Web→后台，APP→APP） | 提示用户确认 | createTestCase 必填 |
| 需求版本号（requirementVersion） | 从需求文档提取 | 默认 YYYYMMDD 或提示用户提供 | createTestCase 必填 |

### 检查流程

```yaml
1. 扫描 spec/ 目录下的需求文档
2. 提取 Confluence pageId:
   - Confluence URL 中的 pageId: /pages/viewpage.action?pageId=123456 → 123456
   - 需求文档中标注的 "Confluence ID" 或 "页面ID"
3. 提取系统名称:
   - 从 40 个系统列表中匹配（完整列表见 mcp-kb-sync.md §二）
   - 模糊匹配示例: "创者" → "创作者后台", "广告" → "战神广告系统"
   - ⚠️ 无法确定时列出候选，让用户选择
4. 提取需求版本号:
   - 从需求文档中提取（如 "v2.3", "000001"）
   - 缺失 → 使用日期格式 YYYYMMDD
5. 缺失处理:
   - 任一必填项缺失 → 立即提示用户
   - "以下信息用于测试用例入库追溯，请提供：
      - Confluence pageId: [请提供需求对应的 Confluence 页面 ID]
      - 系统名称: [请从列表选择]
      - 需求版本号: [如 000001]"
   - 用户回复后 → 保存到 requirement_meta.json
```

### 输出

```json
{
  "requirement_meta": {
    "confluencePageId": "123456789",
    "system": "创作者后台",
    "businessType": "后台",
    "requirementVersion": "000001",
    "extractedAt": "2026-05-28T10:00:00+08:00",
    "source": "spec/需求说明.md"
  }
}
```

---

## 平台专属检查

### Web 平台

| 检查项 | 检查方式 | 失败处理 | 重要度 |
|--------|----------|----------|--------|
| agent-browser | `agent-browser --version` | 提示 `npm install -g agent-browser` | **必须** |
| Chrome浏览器 | 启动验证 | 提示安装Chrome | **必须** |
| AutoHotkey | `ls "/c/Program Files/AutoHotkey/AutoHotkeyU64.exe"` | 提示安装（文件上传必需） | **必须** |
| 测试URL | curl 可达性测试 | 标记环境不可用 | **必须** |
| Python 依赖 | `python -c "import pymysql, requests"` | 提示 `pip install` | 可选 |

### iOS 平台

| 检查项 | 检查方式 | 失败处理 |
|--------|----------|----------|
| Appium | `appium --version` | 提示 `npm install -g appium` |
| XCUITest Driver | `appium driver list --installed` | 提示 `appium driver install xcuitest` |
| Xcode | `xcodebuild -version` | 提示安装Xcode |
| WebDriverAgent | 检查WDA配置 | 提示配置WDA |
| iOS设备/模拟器 | `xcrun simctl list` 或 `idevice_id -l` | 提示连接设备 |
| libimobiledevice | `idevice_id -l`（真机） | 提示 `brew install libimobiledevice` |
| ios-deploy | `ios-deploy --version`（真机） | 提示 `brew install ios-deploy` |
| Carthage | `carthage version`（WDA依赖） | 提示 `brew install carthage` |

### Android 平台

| 检查项 | 检查方式 | 失败处理 |
|--------|----------|----------|
| Appium | `appium --version` | 提示 `npm install -g appium` |
| UIAutomator2 Driver | `appium driver list --installed` | 提示 `appium driver install uiautomator2` |
| JDK | `java -version` | 提示安装JDK 8+ |
| Android SDK | `adb --version` | 提示安装Android SDK |
| ANDROID_HOME | 检查环境变量 | 提示设置ANDROID_HOME |
| Android设备/模拟器 | `adb devices` | 提示连接设备 |

---

## 会话初始化

### Web：浏览器会话初始化

```yaml
# 必须按此顺序执行：
步骤:
  0. 清理浏览器残留（前置清理，不可跳过）:
     # 如果之前测试异常退出，可能有残留窗口/session
     agent-browser close --all
     # 等待 2 秒确保进程完全退出
     sleep 2

  1. 检查 agent-browser:
     agent-browser --version
     → 失败 → 提示 npm install -g agent-browser，中断 Phase 0

  2. 打开目标页面（持久化 Profile 自动复用登录态）:
     agent-browser open "{测试URL}"
     → 等待页面加载

  3. 验证窗口尺寸:
     agent-browser eval "window.innerWidth + 'x' + window.innerHeight"
     → 宽度应 >= 1920

  4. 判断登录态:
     agent-browser snapshot -i -c -d 1
     → 页面含用户信息/导航菜单（如"刘金涛"）→ 登录态有效，跳到步骤 5
     → 页面含"工号登录"/"用户名"等登录表单 → 执行步骤 4a 登录

  4a. 自动登录（仅在登录态失效时执行）:
     见 web/auto-login.md

  4b. 登录后关闭密码弹窗:
     agent-browser press "Enter"   # 弹窗"一律不"按钮默认聚焦
     sleep 1
     agent-browser press "Escape"  # 兜底

  5. 验证 Token:
     用已知 API 端点验证（从 Swagger JSON 获取）
     → 200 → 登录成功，Token 有效
     → 401/403 → 重新提取

     # 如果 Swagger JSON 不可用，使用以下兜底验证方式:
     #   - 访问任意已知可达的页面 URL 并检查是否重定向到登录页
     #   - 用 agent-browser eval 检查页面上是否有用户信息/导航菜单（session 有效）

  6. 预下载 Swagger JSON（Web 平台）:
     # 在 Phase 0 提前下载，供后续 Phase 3.5 和 Token 验证使用
     # 尝试常见路径: /swagger/CdCreatorWebApi/swagger.json, /swagger/v1/swagger.json
     # 如果都不可用 → 记录 "Swagger 不可用"，Phase 3.5 将使用页面抓包代替
```

### iOS：Appium 会话

| 步骤 | 操作 | 说明 |
|------|------|------|
| 1 | 启动Appium Server | `appium --port 4723` |
| 2 | 创建Session | desired_capabilities 配置 |
| 3 | 等待App启动 | 轮询页面元素出现 |

详见 ios/session.md。

### Android：Appium 会话

| 步骤 | 操作 | 说明 |
|------|------|------|
| 1 | 启动Appium Server | `appium --port 4723` |
| 2 | 创建Session | desired_capabilities 配置 |
| 3 | 等待App启动 | 轮询页面元素出现 |

详见 android/session.md。

---

## 输出

环境检查报告 + 配置清单：
```json
{
  "platform": "web|ios|android",
  "environment_ready": true|false,
  "checks": {
    "python_deps": "pass|fail",
    "agent_browser": "pass|fail|skip",
    "platform_tools": "pass|fail",
    "device_available": "pass|fail|skip",
    "db_connectivity": "pass|fail",
    "spec_docs": "pass|fail",
    "mcporter": "pass|fail|auto_configured"
  },
  "mcp_kb": {
    "configured": true|false,
    "connected": true|false,
    "testCaseCount": 0,
    "auto_configured": false
  },
  "session_id": "auto",
  "warnings": [],
  "skipped": []
}
```

## 配置自动提取

从 spec/ 目录文档中自动提取：
- 测试URL / APP包名
- 登录凭证（用户名、密码）
- 数据库连接信息（host, port, user, password, database）
- API Base URL
- 设备ID（iOS UDID / Android serial）