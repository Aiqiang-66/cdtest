# Confluence 知识搜索使用指南

## 定位

供 AI 在 Phase 1 需求分析阶段调用 Confluence MCP 搜索历史资料时参考。

---

## 一、前置检查

```yaml
# 每次使用前必须先检查 MCP 可用性：
检查命令:
  mcporter call 星河文档 getConfluenceStatus

预期返回:
  {
    "configured": true,
    "knowledge": { "configured": true },
    "tracking": { "configured": true },
    "message": "Knowledge 与 tracking 知识库均已配置完成，可以执行检索。"
  }

不可用时的处理:
  - 如果返回 configured=false 或命令失败
  - 跳过知识搜索
  - 在测试报告中记录："Confluence 知识库不可用，未搜索历史资料"
```

---

## 二、searchConfluenceKnowledge — 历史需求检索

### 命令格式

```
mcporter call 星河文档 searchConfluenceKnowledge queryText="搜索关键词" directories="[目录ID]" limit=结果数
```

### 参数说明

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| queryText | string | 搜索关键词，多个词组合 | `"国剧 ROI 报表 筛选器"` |
| directories | string | 目录ID数组，字符串格式 | `"[87270532]"` 或 `"[87270532,33292986]"` |
| limit | number | 返回结果数，建议 3-5 | `5` |

### 返回值说明

```
{
  "configured": true,
  "result": {
    "relevantContext": [
      {
        "title": "文档标题",
        "text": "匹配的文本片段（含关键信息）",
        "webUrl": "https://docs.changdu.vip/pages/viewpage.action?pageId=xxxxx",
        "score": 0.64,                    // 匹配度(0~1)
        "sourceDocumentId": "xxxxx",       // 文档ID
        "version": 12,                     // 版本号
        "updatedAt": "2024-05-06T15:24:56.700+08:00",  // 最后更新
        "ancestorTitles": ["产品部", "7.中台项目", "ADS投放中台", "1.需求", "2024/2"]
      }
    ]
  }
}
```

### 搜索策略

```yaml
关键词组合策略:
  策略 1: 功能名 + 业务线
    queryText: "国剧 ROI 报表"
    
  策略 2: 功能名 + 关联词
    queryText: "ADS 报表 筛选器"
    
  策略 3: 模块 + 关键词
    queryText: "国剧 分析维度"
    
  策略 4: 新特性 + 技术词
    queryText: "TiDB 数据源 报表"

结果不足时的扩搜:
  初始结果 < 2 条时：
  - 扩大查询词范围（用更通用的词）
  - 扩大时间范围（limit 从 3 设为 8）
  - 无业务线限制（不加 directories）
```

---

## 三、searchConfluenceTracking — 埋点/数据口径检索

### 触发条件

```yaml
# 必须搜索埋点的场景：
必须搜索:
  - 需求涉及数据指标：ROI/CPM/CTR/CVR/消耗/流水/转化/LTV
  - 需求涉及报表/统计/看板
  - 需求涉及埋点/事件/用户行为
  - 需求涉及广告收入/支出/归因

可选搜索:
  - 需求涉及字段定义/口径说明
  - 需求涉及计算公式
  - AI 判断可能有历史埋点可复用
```

### 命令格式

```
mcporter call 星河文档 searchConfluenceTracking queryText="搜索关键词" directories="[目录ID]" limit=结果数
```

### 返回值与 searchConfluenceKnowledge 格式相同

### 埋点搜索关键词示例

```
"国剧 ROI 字段 口径"
"广告 归因 数据"
"消耗 转化 统计"
"广告 报表 字段说明"
```

---

## 四、搜索结果的消费

### 在测试方案中引用

```markdown
## 历史资料检索结果

| 文档标题 | URL | 匹配内容 | 测试参考价值 |
|----------|-----|---------|-------------|
| ROI统计（国剧）-增加数据更新时间、字段说明 | [链接](https://...) | 字段说明：CPM/CTR/CVR/ROI定义 | 指标验证 -> TC-XXX |
| 国剧报表筛选器分析维度增加"微小"、"抖小" | [链接](https://...) | 分析维度产品类型 | 筛选器测试用例参考 |
```

### 在用例中引用来源

```json
{
  "用例ID": "TC-ROI-017",
  "用例名称": "报表字段完整性验证",
  "历史来源": "Confluence:60625007 - ROI统计（国剧）-增加数据更新时间、字段说明",
  "测试步骤": [...]
}
```

### 在测试报告中对比

```markdown
## 数据对比（历史 vs 当前）

| 字段 | 历史定义 | 当前页面值 | 一致性 |
|------|---------|-----------|--------|
| CPM | 消耗/展示数×1000 | 30.76 ✅ | ✅ |
| 7日综合ROI | 7日综合流水/总消耗 | 0.91 ✅ | ✅ |
```
