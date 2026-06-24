# Web 环境配置（agent-browser）

## 依赖安装

### Python 依赖

```bash
pip install pymysql requests
```

### agent-browser

**NPM 全局安装（推荐）**:

```bash
npm install -g agent-browser
agent-browser --version
```

**Windows 注意事项**:
- npm 全局安装后命令名为 `agent-browser.cmd`
- 如提示"无法识别"，将 npm 全局 bin 目录加入 PATH：`C:\Users\{用户名}\AppData\Roaming\npm`
- PowerShell 执行策略如阻止脚本，运行: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### AutoHotkey（文件上传必需）

**Windows 安装**:

从 https://www.autohotkey.com/ 下载安装 AutoHotkey v1（推荐 v1.1+）

检查是否已安装:
```bash
ls "/c/Program Files/AutoHotkey/AutoHotkeyU64.exe"
```

如未安装，提示用户:
> AutoHotkey 未安装。文件上传功能需要 AutoHotkey 来自动填充系统文件对话框。
> 请访问 https://www.autohotkey.com/ 下载安装。

## 环境检查清单

| 检查项 | 检查方式 | 失败处理 |
|--------|----------|----------|
| agent-browser | `agent-browser --version` | 提示安装 |
| Chrome 浏览器 | 启动验证 | 提示安装 |
| AutoHotkey | `ls "/c/Program Files/AutoHotkey/AutoHotkeyU64.exe"` | 提示安装（文件上传必需） |
| daemon 状态 | `agent-browser daemon status` | 自动启动 |
| Python 依赖 | `python -c "import pymysql, requests"` | 提示 `pip install` |
| 测试 URL | curl 可达性测试 | 标记环境不可用 |
| DB 连接 | 连接测试 | 标记 DB 验证跳过 |

## daemon 管理

```bash
# 检查状态
agent-browser daemon status

# 启动（如未运行）
agent-browser daemon start

# 重启（如有异常）
agent-browser daemon restart
```