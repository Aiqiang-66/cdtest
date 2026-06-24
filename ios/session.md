# iOS 设备会话管理（Appium）

## 会话生命周期

```
创建 Session → 启动 App → 登录 → 执行测试 → 关闭 Session
```

## Capabilities 配置

### 模拟器

```python
from appium import webdriver

desired_caps = {
    "platformName": "iOS",
    "appium:platformVersion": "17.0",
    "appium:deviceName": "iPhone 15 Pro",
    "appium:automationName": "XCUITest",
    "appium:app": "/path/to/app.app",          # .app 路径
    "appium:bundleId": "com.example.app",       # Bundle ID（可选，如已安装）
    "appium:udid": "auto",                       # 模拟器自动选择
    "appium:newCommandTimeout": 300,
    "appium:wdaLaunchTimeout": 120000,
    "appium:language": "en",
    "appium:locale": "en_US",
}

driver = webdriver.Remote("http://localhost:4723", desired_caps)
```

### 真机

```python
desired_caps = {
    "platformName": "iOS",
    "appium:platformVersion": "17.0",
    "appium:deviceName": "iPhone",
    "appium:automationName": "XCUITest",
    "appium:udid": "00008030-XXXXXXXXXXXX",     # 真机 UDID
    "appium:xcodeOrgId": "XXXXXXXXXX",           # Team ID
    "appium:xcodeSigningId": "iPhone Developer",
    "appium:app": "/path/to/app.ipa",            # .ipa 路径
    "appium:bundleId": "com.example.app",
    "appium:newCommandTimeout": 300,
    "appium:wdaLaunchTimeout": 120000,
    "appium:updatedWDABundleId": "com.yourteam.WebDriverAgentRunner",
}

driver = webdriver.Remote("http://localhost:4723", desired_caps)
```

## 会话复用策略

| 策略 | 说明 |
|------|------|
| 优先复用 | 如果 App 已在前台运行，复用当前 session |
| 热启动 | 不重新安装 App，直接启动（适合回归测试） |
| 冷启动 | 卸载后重新安装（适合新功能测试） |

```python
# 检查 App 状态
state = driver.query_app_state("com.example.app")
# 0=未安装, 1=未运行, 2=后台, 3=前台(未激活), 4=前台(激活)

if state == 4:
    # 已在前台，复用
    pass
elif state >= 1:
    # 已安装，激活或重启
    driver.activate_app("com.example.app")
else:
    # 未安装，安装
    driver.install_app("/path/to/app.app")
```

## App 生命周期管理

```python
# 启动 App
driver.activate_app(bundle_id)

# 后台化
driver.background_app(-1)  # -1 表示永久后台

# 终止 App
driver.terminate_app(bundle_id)

# 重置 App（清除数据）
driver.reset()
```

## 登录流程

### 识别登录页面类型

```python
# 获取页面源码（XML 树）
page_source = driver.page_source

# 查找登录元素
from selenium.webdriver.common.by import By

# 标准表单：用户名 + 密码
try:
    username_field = driver.find_element(By.ACCESSIBILITY_ID, "username")
    password_field = driver.find_element(By.ACCESSIBILITY_ID, "password")
except:
    # 尝试 XPath
    username_field = driver.find_element(By.XPATH, "//XCUIElementTypeTextField")
    password_field = driver.find_element(By.XPATH, "//XCUIElementTypeSecureTextField")
```

### 登录页面类型自适应

| 页面特征 | 类型 | 处理策略 |
|----------|------|----------|
| TextField + SecureTextField 同页 | 标准表单登录 | 填写用户名 → 填写密码 → 点击登录 |
| 出现"忘记密码"按钮 | 密码找回页 | 返回登录页 |
| 出现导航/TabBar（已登录态） | 已登录 | 跳过登录 |

### 登录成功验证

```python
# 确认首页元素出现
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.ACCESSIBILITY_ID, "home_tab"))
)
# 截图确认
driver.save_screenshot("report/screenshots/ios_login_success.png")
```

## Token 提取

```yaml
Token 提取优先级链（按顺序尝试，任一步成功即停止）:

  优先级 1: Appium execute_script 获取 Keychain / UserDefaults
    # iOS 可通过 Appium 的 mobile: 命令获取应用存储
    try:
        # 方式 1a: 从粘贴板获取（如果 APP 将 Token 复制到剪贴板）
        token = driver.get_clipboard_text()
        
        # 方式 1b: 从应用容器文件系统读取（需知道确切路径）
        token = driver.pull_file('@com.example.app/Documents/auth_token.txt')
        
        # 方式 1c: 通过 Appium 执行 Swift/ObjC 脚本获取 UserDefaults
        token = driver.execute_script("mobile: exec", {
            "script": "[[NSUserDefaults standardUserDefaults] stringForKey:@\"auth_token\"]"
        })
    except:
        pass

  优先级 2: 抓包工具代理拦截（半自动化）
    # 使用 mitmproxy / Proxyman / Charles 抓包
    # 配合 proxy 脚本自动提取 Authorization header
    # 优点: 通用性强，与 APP 实现解耦
    # 缺点: 需要安装代理证书，iOS 需额外配置

  优先级 3: 从网络请求日志获取
    # 通过 idevicesyslog 或 Xcode 设备日志过滤网络请求
    # 搜索 "Authorization" / "Bearer" / "X-Token" 关键字
    # 适用: 开发版本 APP 带有网络日志输出

  优先级 4: 配置/环境变量
    # spec/config.yaml 或 .env 中的 auth_token
    # 直接使用 → 验证有效性

  优先级 5: 人工提供（兜底）
    # 提示用户: "请在 Charles/Proxyman 中复制 Token"
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
# 自动接受系统权限弹窗
driver.execute_script("mobile: alert", {
    "action": "accept",
    "buttonLabel": "Allow"
})

# 常见权限弹窗
# - "允许访问位置" → Accept
# - "允许发送通知" → Accept
# - "允许访问相机" → Accept
```