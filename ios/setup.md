# iOS 环境配置（Appium XCUITest Driver）

## 依赖安装

### 1. Xcode + Command Line Tools

```bash
xcode-select --install
```

### 2. Appium

```bash
npm install -g appium
appium --version

# 安装 XCUITest 驱动
appium driver install xcuitest

# 验证驱动
appium driver list --installed
```

### 3. WebDriverAgent (WDA)

Appium XCUITest Driver 会自动管理 WDA。如需手动配置：

```bash
# WDA 位于 Appium 安装目录
cd $(appium driver which xcuitest | xargs dirname)/appium-xcuitest-driver/node_modules/appium-webdriveragent

# 用 Xcode 打开 WebDriverAgent.xcodeproj
# 配置签名（Team + Bundle Identifier）
```

### 4. Carthage（WDA 依赖）

```bash
brew install carthage
```

### 5. Python 依赖

```bash
pip install pymysql requests Appium-Python-Client
```

### 6. ios-deploy（真机）

```bash
brew install ios-deploy
```

## 环境检查清单

| 检查项 | 检查方式 | 失败处理 |
|--------|----------|----------|
| Xcode | `xcodebuild -version` | 提示安装 |
| Appium | `appium --version` | 提示 `npm install -g appium` |
| XCUITest Driver | `appium driver list --installed` | 提示 `appium driver install xcuitest` |
| Python 依赖 | `python -c "import appium"` | 提示 `pip install Appium-Python-Client` |
| 设备/模拟器 | `xcrun simctl list devices` | 提示创建模拟器或连接真机 |
| DB 连接 | 连接测试 | 标记 DB 验证跳过 |

## iOS 模拟器管理

```bash
# 列出可用模拟器
xcrun simctl list devices available

# 创建模拟器
xcrun simctl create "iPhone 15 Pro" "iPhone 15 Pro"

# 启动模拟器
xcrun simctl boot {device_udid}

# 关闭模拟器
xcrun simctl shutdown {device_udid}
```

## Appium 服务启动

```bash
# 默认端口 4723
appium --port 4723 --use-plugins=images

# 后台启动
appium --port 4723 &
```

## iOS 特有检查项

| 检查项 | 说明 |
|--------|------|
| 签名配置 | 真机需要有效的开发者账号和 provisioning profile |
| UDID | 真机需要 UDID，`idevice_id -l` 查看 |
| WDA 签名 | WebDriverAgentRunner 需要正确的 Team 和 Bundle ID |
| 系统权限弹窗 | 首次运行需要处理位置/通知/相机等权限弹窗 |