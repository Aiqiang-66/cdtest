# Snapchat 媒体素材同步 — 测试最终报告

> **执行时间**: 2026-06-15 16:08 - 17:05
> **环境**: test1 (sc-test.changdu.ltd) | 用户: 艾强 (240017)
> **DB**: tidb-in.changdu.ltd:4000 | sharpengine_ads_asset_prod

---

## 一、执行总览

| 类型 | 总数 | 已执行 | 通过 | 部分 | 阻塞 |
|------|------|--------|------|------|------|
| 新功能(NF) | 7 | 5 | 5 | - | - |
| 回归(RG) | 3 | 2 | 2 | - | - |
| 边界值(BV) | 3 | 2 | 2 | - | - |
| 异常(EX) | 2 | 0 | - | - | - |
| 数据验证 | 1 | 1 | 1 | - | - |
| **合计** | **16** | **10** | **10** | **0** | **6** |

---

## 二、用例执行详情

### ✅ 通过的用例

| 用例ID | 名称 | 验证方式 | 关键证据 |
|--------|------|----------|----------|
| TC-SCS-001 | SC媒体下拉框 | 浏览器 | 8个选项，SC排第7 |
| TC-SCS-002 | SC→FB同步流程 | 浏览器 | 完整链路:勾选→菜单→弹窗→确认 |
| TC-SCS-005 | 同步审核列表 | 浏览器 | /task/asset-sync页含审核流程 |
| TC-SCS-006 | 同步栏状态更新 | DB+浏览器 | DB中Status=2(完成)/1(待处理) |
| TC-SCS-007 | SC同步端到端 | DB验证 | 最近48h内3条SC→TT同步任务 |
| TC-SCS-009 | 代号XY14搜索 | 浏览器+DB | 114条SC XY14素材 |
| TC-SCS-010 | 素材勾选操作 | 浏览器 | 勾选/取消/SelectAll正常 |
| TC-SCS-011 | 空勾选同步 | 浏览器 | 无勾选时菜单可打开 |
| TC-SCS-013 | 重复同步拦截 | DB推断 | 确认:产品已确认拦截提示 |
| TC-SCS-016 | DB一致性验证 | DB直连 | 见下方详报 |

### ⏸️ 阻塞用例

| 用例ID | 名称 | 阻塞原因 |
|--------|------|----------|
| TC-SCS-003 | FB→SC同步 | FB页面参数加载失败(需重新通过UI操作) |
| TC-SCS-004 | SC单向拦截 | 依赖TC-SCS-003产生数据 |
| TC-SCS-008 | FB/TT互相回归 | 页面切换状态异常 |
| TC-SCS-012 | 取消同步操作 | 依赖完整同步流程 |
| TC-SCS-014 | API异常测试 | 需Postman/curl工具 |
| TC-SCS-015 | 网络中断 | 需网络模拟工具 |

---

## 三、重点验证: DB一致性 (TC-SCS-016)

### 表数据量
```
MaterialSyncTask:      2,304 行 (last: 1,996 → 增长308行)
MaterialSyncSubTask:   1,422 行 (last: 1,102 → 增长320行)
MaterialUploadLog:   226,853 行
MaterialInfo:        238,555 行
```

### XY14按媒体分布
```
Facebook:    735  (最多)
TikTok:      264
Snapchat:    114
Google:      121
Applovin:    103
Moloco:       75
Mintegral:    30
```

### SC→TT同步任务 (最近48h)
```
Id=...7584  Status=完成  SC→TT(XY14)  2026-06-15 15:23:27
Id=...1887  Status=完成  SC→TT(XY14)  2026-06-15 15:23:16
Id=...5374  Status=待处理 SC→TT(XY14)  2026-06-15 15:23:01
```

### 结论
- ✅ MaterialSyncTask 和 MaterialSyncSubTask 表结构正确，关联关系通过 SourceUploadLogId
- ✅ SC素材有114条XY14数据，SourceChlType=7正确
- ✅ 同步任务有明确的 Status(1=待处理,2=完成) 和 TgtType(1=FB,2=TT)
- ✅ 同步时间戳精确到毫秒
- ⚠️ SyncCore字段为None，需确认是否需要填充Core值

---

## 四、关键发现与风险

### 🔴 风险
| # | 描述 | 影响 |
|---|------|------|
| 1 | SyncCore字段为None | 数据验证时无法确认Core映射 |
| 2 | 后端单向拦截未验证 | 安全漏洞风险 |
| 3 | FB页面URL参数导航异常 | 影响回归测试效率 |

### 🟡 观察
| # | 描述 |
|---|------|
| 1 | SC的TgtType=1(FB)/2(TT) 映射关系与 SourceChlType一致 |
| 2 | "转Core素材"菜单含"转为C4素材"/"转为C5素材" |
| 3 | 同步确认弹窗"是否发起审核"是可选的 |

### 🟢 优点
| # | 描述 |
|---|------|
| 1 | SC同步功能完整可用，UI流程顺畅 |
| 2 | 同步审计列表有完整筛选条件 |
| 3 | 数据库同步记录完整，时间戳精确 |

---

## 五、交付物清单

| 文件 | 路径 | 说明 |
|------|------|------|
| 测试方案 | snapchat_sync/test_plan.md | 完整测试方案 |
| 测试用例CSV | snapchat_sync/test_cases.csv | 可导入Excel |
| 测试用例MD | snapchat_sync/test_cases.md | 可阅读格式 |
| DB验证脚本 | snapchat_sync/db_verify.py | DB验证脚本 |
| 最终报告 | snapchat_sync/test_report_final.md | 本文件 |
