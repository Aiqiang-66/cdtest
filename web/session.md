# Web 浏览器会话管理

## 定位

登录和 Token 提取是工程问题，使用 **agent-browser 自动完成**。详细流程见 `web/auto-login.md`。

> ⛔ **核心规则**: 禁止跳过 agent-browser 直接用 curl 猜测 API 登录端点。必须先用 agent-browser 打开页面完成登录，再按优先级链提取 Token。

---

## 快速参考

```yaml
标准流程:
  Phase 0 环境检查 → 确认 agent-browser 可用
    ↓
  执行 web/auto-login.md:
    1. 打开页面（最大化）→ agent-browser open URL --headed --args "--start-maximized"
    2. 识别登录类型 → snapshot → 工号登录/标准表单/SSO/验证码/已登录
    3. 执行登录 → fill 凭证 → click 登录 → 等待跳转 → 确认已登录
    4. 提取 Token → localStorage → Cookies → JS变量 → 已知API → 配置文件
    5. 验证 Token → 调已知API端点确认200

引用:
  - 自动登录完整流程: web/auto-login.md
  - 环境检查（含 agent-browser 检查）: common/phase0-env-check.md
```