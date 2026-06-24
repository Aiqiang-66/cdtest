# Phase 3.5：API 层测试 — 混合驱动版

## 定位

**固定骨架 + AI 填充**。Token 提取使用固定优先级链，API 测试设计由 AI 驱动。

## 条件

```yaml
入口条件:
  - Phase 3b 已完成（UI 执行循环结束）
  - Token 从 Phase 0/auto-login.md 已获取且有效
  - Swagger JSON 已下载（/swagger/CdCreatorWebApi/swagger.json）
  - 如果 Token 失效 → 重新走 auto-login.md 提取

出口条件:
  - 所有标记为 exec_method=API 的用例已执行
  - 输出: api_test_results.json {total: N, passed: N, failed: N, skipped: N}
```

---

## 一、Token 获取（固定优先级链）

```yaml
# Token 获取统一由 web/auto-login.md 完成，本文件不再重复。
# 执行模式流程: Phase 0 → auto-login.md → Token 已就绪 → 直接进入 Phase 3.5
# 如果 Token 在 Phase 3.5 阶段失效 → 重新走 auto-login.md 流程获取

Token 获取优先级:
  1. 从 Phase 0/auto-login 已提取的 Token 直接使用
     → 验证: 用已知 API 端点验证（优先用 Swagger JSON 中已有的轻量端点）
     → 401/403 → Token 过期，重新走 auto-login.md 提取

  2. APP session Token 提取:
     - 通过 Appium 获取 APP 本地存储或网络拦截
     → 验证

  3. ⛔ 禁止: 在不知道明确登录端点的情况下盲目尝试 POST /api/auth/login 等路径
     → 如果 auto-login.md 所有优先级都失败 → 提示用户手动提供 Token
```

## 二、API 接口发现（固定来源 + AI 筛选）

```yaml
# 固定来源：
接口发现来源:
  1. 页面操作中捕获的网络请求（通过浏览器 CDP 或 APP 代理）
  2. 需求文档/开发文档中描述的接口
  3. 用户提供的 API 文档（spec/ 目录下）

# AI 筛选：
AI 筛选:
  - 判断：哪些接口与当前测试相关？
  - 排除：静态资源请求（图片/CSS/JS）
  - 排除：第三方统计/监控请求
  - 保留：业务接口（/api/xxx）
```

## 三、API 测试设计（AI 驱动）

```yaml
# AI 根据业务场景设计测试：
测试类型:
  - 正常流程: 调接口验证返回符合预期
  - 参数校验: 空值/非法值/边界值
  - 业务规则: 重复拦截/状态前置/权限校验
  - DB 交叉验证: API 返回 vs DB 实际数据

# AI 设计示例：
AI 设计:
  接口: "POST /api/invoice/create"
  场景: "正常创建发票"
  请求: {amount: 1000, title: "测试发票"}
  预期: {code: 200, data: {status: "draft"}}
  DB 验证: "SELECT * FROM invoice WHERE id=123 → status='draft'"

  接口: "POST /api/invoice/create"
  场景: "重复创建（相同订单号）"
  请求: {order_no: "ORD-001", amount: 1000}
  预期: {code: 409, message: "订单号已存在"}
```

## 四、执行与验证（固定流程 + AI 判断）

```yaml
# 固定执行流程：
执行流程:
  1. 获取 Token（按优先级链）
  2. 构造请求（URL + Header + Body）
  3. 发送请求
  4. 检查响应状态码
  5. 检查响应体内容
  6. DB 交叉验证（如需要）
  7. 记录结果

# AI 判断：
AI 判断:
  - 状态码 200 → 继续检查响应体
  - 状态码 4xx → 分析错误信息（参数错误？Token 过期？权限不足？）
  - 状态码 5xx → 标记环境问题
  - 响应体不符合预期 → AI 分析原因
  - 自动回退: GET 405 → 改 POST；POST 405 → 改 GET
```