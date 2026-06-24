# Android 设备会话管理（Appium UIAutomator2 Driver）

## 会话生命周期

```
创建 Session → 启动 App → 登录 → 执行测试 → 关闭 Session
```

## Capabilities 配置

### 模拟器

```python
from appium import webdriver

desired_caps = {
    "platformName": "Android",
    "appium:platformVersion": "14.0",
    "appium:deviceName": "emulator-5554",
    "appium:automationName": "UIAutomator2",
    "appium:app": "/path/to/app.apk",
    "appium:appPackage": "com.example.app",
    "appium:appActivity": ".MainActivity",
    "appium:newCommandTimeout": 300,
    "appium:uiautomator2ServerLaunchTimeout": 60000,
    "appium:language": "en",
    "appium:locale": "US",
    "appium:noReset": True,        # 不重置 App 数据
    "appium:fullReset": False,     # 不卸载 App
}

driver = webdriver.Remote("http://localhost:4723", desired_caps)
```

### 真机

```python
desired_caps = {
    "platformName": "Android",
    "appium:platformVersion": "14.0",
    "appium:deviceName": "XXXXXXXX",               # ADB devices 获取
    "appium:automationName": "UIAutomator2",
    "appium:udid": "XXXXXXXX",                      # 设备序列号
    "appium:app": "/path/to/app.apk",
    "appium:appPackage": "com.example.app",
    "appium:appActivity": ".MainActivity",
    "appium:newCommandTimeout": 300,
    "appium:noReset": True,
}

driver = webdriver.Remote("http://localhost:4723", desired_caps)
```

## ADB 设备管理

```bash
# 列出设备
adb devices

# 连接设备（网络 ADB）
adb connect 192.168.1.100:5555

# 断开设备
adb disconnect 192.168.1.100:5555

# 安装 APK
adb -s {serial} install /path/to/app.apk

# 卸载 App
adb -s {serial} uninstall com.example.app

# 启动 App
adb -s {serial} shell am start -n com.example.app/.MainActivity

# 停止 App
adb -s {serial} shell am force-stop com.example.app

# 清除 App 数据
adb -s {serial} shell pm clear com.example.app

# 截图
adb -s {serial} exec-out screencap -p > screenshot.png
```

## 会话复用策略

| 策略 | 说明 |
|------|------|
| 优先复用 | 如果 App 已在前台运行，复用当前 session |
| 热启动 | `noReset=True`，不重置数据（适合回归测试） |
| 冷启动 | `fullReset=True`，卸载重装（适合新功能测试） |

```python
# 检查 App 是否已安装并运行
# 通过 adb 检查
import subprocess
result = subprocess.run(
    ["adb", "-s", serial, "shell", "dumpsys", "package", package_name],
    capture_output=True, text=True
)
installed = "Unable to find package" not in result.stdout
```

## 登录流程

### 识别登录页面类型

```python
from selenium.webdriver.common.by import By

# 查找登录元素
try:
    # 通过 resource-id 定位（最稳定）
    username = driver.find_element(By.ID, "com.example.app:id/et_username")
    password = driver.find_element(By.ID, "com.example.app:id/et_password")
    login_btn = driver.find_element(By.ID, "com.example.app:id/btn_login")
except:
    # 通过文本定位
    username = driver.find_element(By.XPATH, "//android.widget.EditText[@text='请输入用户名']")
    password = driver.find_element(By.XPATH, "//android.widget.EditText[@text='请输入密码']")
```

### 登录页面类型自适应

| 页面特征 | 类型 | 处理策略 |
|----------|------|----------|
| EditText ×2 + 登录按钮同页 | 标准表单登录 | 填写用户名 → 密码 → 点击登录 |
| 出现"忘记密码"/验证码输入 | 找回密码/二次验证 | 跳过或用测试验证码 |
| 出现 Tab/BottomNav（已登录态） | 已登录 | 跳过登录 |

### 登录成功验证

```python
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.ID, "com.example.app:id/main_container"))
)
driver.save_screenshot("report/screenshots/android_login_success.png")
```

## Token 提取

```yaml
Token 提取优先级链（按顺序尝试，任一步成功即停止）:

  优先级 1: Appium execute_script 获取 SharedPreferences / 应用存储
    # Android 可通过 Appium 的 mobile: 命令获取应用存储
    try:
        # 方式 1a: 从 SharedPreferences 读取（需知道文件名和 key）
        token = driver.execute_script("mobile: exec", {
            "script": """
              import android.content.SharedPreferences;
              SharedPreferences prefs = getContext().getSharedPreferences("app_prefs", 0);
              return prefs.getString("auth_token", null);
            """
        })
        
        # 方式 1b: 从应用内部文件读取
        token = driver.pull_file('/data/data/com.example.app/shared_prefs/app_prefs.xml')
        # 解析 XML 提取 token 字段
        
        # 方式 1c: 通过 adb shell 直接读取（绕过 Appium）
        # adb -s {serial} shell run-as com.example.app cat /data/data/com.example.app/shared_prefs/app_prefs.xml
    except:
        pass

  优先级 2: 抓包工具代理拦截（半自动化）
    # 使用 mitmproxy / Charles / Fiddler 抓包
    # mitmproxy 模式: 启动 mitmdump -s token_extractor.py
    # token_extractor.py 自动提取请求中的 Authorization/Bearer header
    # 优点: 通用性强，与 APP 实现解耦
    # 缺点: Android 7+ 需额外配置证书信任

  优先级 3: 从 adb logcat 日志获取
    # 如果 APP 在开发模式下打印 Token
    adb -s {serial} logcat -d | grep -i "token\|authorization\|bearer"
    # 仅适用于开发/测试版本 APP

  优先级 4: 配置/环境变量
    # spec/config.yaml 或 .env 中的 auth_token
    # 直接使用 → 验证有效性

  优先级 5: 人工提供（兜底）
    # 提示用户: "请在 Charles/mitmproxy 中复制 Token"
    # 等待用户提供（5 分钟内）
    # 如超时 → 标记 APP API 测试跳过

验证方式:
  # 提取到 Token 后必须调任意已知 API 验证:
  curl -H "Authorization: Bearer {token}" {api_base}/api/health
  → 200 → 有效
  → 401/403 → Token 无效，尝试下一个优先级
```

## 权限弹窗处理

```python
# Android 权限弹窗通常出现在首次启动
try:
    # 等待权限弹窗
    allow_btn = driver.find_element(By.ID, "com.android.permissioncontroller:id/permission_allow_button")
    allow_btn.click()
except:
    pass  # 无权限弹窗

# 系统设置中的权限可以通过 adb 预授权
# adb -s {serial} shell pm grant com.example.app android.permission.CAMERA
# adb -s {serial} shell pm grant com.example.app android.permission.ACCESS_FINE_LOCATION
```