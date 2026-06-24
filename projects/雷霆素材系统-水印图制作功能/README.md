# 雷霆素材系统 - 水印图制作测试

## 项目信息

| 项目 | 内容 |
|------|------|
| 测试日期 | 2026-05-15 |
| 测试环境 | dev (sc-test.changdu.ltd) |
| 测试平台 | Web (Chrome, agent-browser 0.27.0) |
| 测试账号 | 240017 (艾强) |
| 通过率 | **36/36 PASS** ✅ |

## 目录结构

```
雷霆素材系统/
├── README.md              # 本文件
├── screenshots/           # 测试截图
│   ├── screenshot_before_click.png
│   ├── screenshot_drawer.png
│   ├── screenshot_after_submit.png
│   ├── screenshot_make_list.png
│   ├── screenshot_core5_submit.png
│   ├── screenshot_make_list_filtered.png
│   ├── screenshot_core5_filter.png
│   ├── screenshot_preview.png
│   └── screenshot_upload_resource.png
├── scripts/               # 测试脚本
│   ├── api_test.py        # API 接口测试
│   └── db_verify.py       # 数据库校验
└── reports/               # 测试报告
```

## 测试用例

### 第一轮（基础功能）

| 用例ID | 用例名称 | 优先级 | 结论 |
|--------|---------|--------|------|
| TC-WM-001 | 水印图制作-正常提交 | P0 | ✅ PASS |
| TC-WM-002 | 水印图制作-必填项校验 | P1 | ✅ PASS |
| TC-WM-003 | 水印图制作-取消操作 | P1 | ✅ PASS |
| TC-WM-004 | 制作列表-页面加载 | P0 | ✅ PASS |
| TC-WM-005 | API-BatchAdd接口 | P1 | ✅ PASS |

### 第二轮（补充场景）

| 用例ID | 用例名称 | 优先级 | 结论 |
|--------|---------|--------|------|
| TC-WM-006 | 尺寸多选组合(916+45) | P1 | ✅ PASS |
| TC-WM-007 | 尺寸至少保留一项校验 | P2 | ✅ PASS |
| TC-WM-008 | Core切换(Core1→Core5) | P1 | ✅ PASS |
| TC-WM-009 | 项目选项(水印图仅海剧) | P2 | ✅ PASS |
| TC-WM-010 | 代号搜索过滤 | P1 | ✅ PASS |
| TC-WM-011 | 代号多选(2个代号) | P1 | ✅ PASS |
| TC-WM-012 | 代号逐个删除 | P2 | ✅ PASS |
| TC-WM-013 | 不同Core提交(Core5) | P1 | ✅ PASS |
| TC-WM-014 | 制作列表-状态筛选 | P1 | ✅ PASS |
| TC-WM-015 | 制作列表-查看/重试操作 | P1 | ✅ PASS |
| TC-WM-016 | 制作列表-分页切换 | P2 | ✅ PASS |
| TC-WM-017 | 重复提交防重机制 | P1 | ✅ PASS |
| TC-WM-018 | 烧录资源配置-Core筛选 | P1 | ✅ PASS |

### 第三轮（自检补充）

| 用例ID | 用例名称 | 优先级 | 结论 |
|--------|---------|--------|------|
| TC-WM-019 | 类型切换(水印图/落地页/免费标签) | P1 | ✅ PASS |
| TC-WM-020 | 媒体切换(Facebook↔TikTok) | P1 | ✅ PASS |
| TC-WM-021 | 状态筛选(启用/禁用) | P1 | ✅ PASS |
| TC-WM-022 | 语言筛选(多语言下拉) | P1 | ✅ PASS |
| TC-WM-023 | 主页面代号搜索+查询 | P1 | ✅ PASS |
| TC-WM-024 | 制作列表-Core筛选 | P1 | ✅ PASS |
| TC-WM-025 | 制作列表-每页条数切换 | P2 | ✅ PASS |
| TC-WM-026 | 水印图预览功能 | P1 | ✅ PASS |
| TC-WM-027 | 上传资源按钮 | P1 | ✅ PASS |
| TC-WM-028 | 管理资源按钮 | P2 | ✅ PASS |

### 第四轮（水印图制作深度覆盖）

| 用例ID | 用例名称 | 优先级 | 结论 |
|--------|---------|--------|------|
| TC-WM-029 | 尺寸-取消916仅选45 | P2 | ✅ PASS |
| TC-WM-030 | Core4提交(防重校验) | P1 | ✅ PASS |
| TC-WM-031 | Core18提交(新代号成功) | P1 | ✅ PASS |
| TC-WM-032 | 代号一键清空(allowClear) | P2 | ✅ PASS |
| TC-WM-033 | 搜索不存在的代号 | P2 | ✅ PASS |
| TC-WM-034 | 必填校验-尺寸全不选 | P1 | ✅ PASS |
| TC-WM-035 | 必填校验-Core默认选中 | P2 | ✅ PASS |
| TC-WM-036 | 提交成功弹窗-确定关闭 | P1 | ✅ PASS |

## 数据库校验

- `BurnResource` 表：Core1(5925条)/Core4(2504条)/Core5(234条)/Core18(188条) 数据完整 ✅
- `BurnResourceTask` 表：最新任务ID=196(Core18,制作中)，链路正常 ✅
- 数据链路：UI → API → DB 完整 ✅
- 防重机制：同维度重复提交返回"创建失败" ✅
