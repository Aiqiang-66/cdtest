# Android 环境配置（Appium UIAutomator2 Driver）

## 依赖安装

### 1. Java JDK

```bash
java -version  # 需要 JDK 8+
```

### 2. Android SDK

安装 Android Studio（包含 SDK Manager），或单独安装命令行工具：

```bash
# 设置环境变量
export ANDROID_HOME=/path/to/Android/Sdk
export PATH=$PATH:$ANDROID_HOME/tools:$ANDROID_HOME/platform-tools:$ANDROID_HOME/cmdline-tools/latest/bin
```

### 3. Appium

```bash
npm install -g appium
appium --version

# 安装 UIAutomator2 驱动
appium driver install uiautomator2

# 验证驱动
appium driver list --installed
```

### 4. Python 依赖

```bash
pip install pymysql requests Appium-Python-Client
```

## 环境检查清单

| 检查项 | 检查方式 | 失败处理 |
|--------|----------|----------|
| Java | `java -version` | 提示安装 JDK 8+ |
| ADB | `adb --version` | 提示安装 Android SDK |
| Appium | `appium --version` | 提示 `npm install -g appium` |
| UIAutomator2 Driver | `appium driver list --installed` | 提示 `appium driver install uiautomator2` |
| Python 依赖 | `python -c "import appium"` | 提示 `pip install Appium-Python-Client` |
| 设备/模拟器 | `adb devices` | 提示启动模拟器或连接真机 |
| DB 连接 | 连接测试 | 标记 DB 验证跳过 |

## ADB 设备管理

```bash
# 列出已连接设备
adb devices -l

# 连接网络设备（WiFi 调试）
adb connect {ip}:5555

# 断开设备
adb disconnect {ip}:5555

# 重启 ADB 服务
adb kill-server
adb start-server
```

## 模拟器管理（AVD）

```bash
# 列出可用 AVD
emulator -list-avds

# 启动模拟器
emulator -avd {avd_name} -no-snapshot-load

# 列出模拟器
adb devices  # 模拟器通常显示为 emulator-5554
```

## Appium 服务启动

```bash
# 默认端口 4723
appium --port 4723

# 后台启动
appium --port 4723 &
```

## Android 特有检查项

| 检查项 | 说明 |
|--------|------|
| USB 调试 | 真机需要在开发者选项中开启 USB 调试 |
| APK 签名 | debug 包或已签名 release 包 |
| WebView 版本 | 如需要 WebView 测试，确保已安装对应版本 |
| 权限弹窗 | 首次运行需要处理权限请求弹窗（Android 6+） |
| 开发者选项 | 动画缩放建议关闭（窗口/过渡/Animator时长缩放 = 关闭） |