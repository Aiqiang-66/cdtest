# 海剧素材上传 — Applovin新增Core4/Core5图片生成引导图 测试方案

> **cdtest v3.5.2** | 2026-06-24 | Web 执行模式
> 测试账号：240017（艾强）| 测试环境：test1 (sc-test.changdu.ltd)

---

## 一、需求解读

| 维度 | 内容 |
|------|------|
| 业务目标 | Applovin 媒体图片素材新增 Core4/Core5 一键生成引导图（GIF/PNG），提升素材投放效率 |
| 目标页面 | `/task/batch-upload-video`（海剧素材上传） |
| 本期新增 | Core4/Core5 图片生成引导图；GIF/PNG 格式选择；生成结果抽屉柜展示+预览+保存上传 |
| 本期修改 | "获取H5图"按钮逻辑根据 Core + 格式区分处理 |
| 保持不变 | Core18 行为；其他媒体（FB/TT/Google/Moloco/Snapchat/Mintegral）图片生成；视频类型 |

### 用户操作路径

```
海剧素材上传页面
  → 媒体选择 Applovin（需先清除默认 Facebook）
  → 类型选择 图片
  → Core 选择 Core4（或 Core5）
  → 剧集代号搜索 [海剧]EN-XY14/14583322
  → 一级标签 + 二级标签 任意选择
  → 生成引导图：GIF图 / PNG图（单选）
  → 点击"获取H5图"
  → 右下角抽屉柜展示生成结果
  → 点击名称 → 预览弹窗展示图片
  → 点击保存 → 上传至传输列表
```

---

## 二、页面探索结果

> 探索时间：2026-06-24 | agent-browser 0.27.0 | 页面已成功登录

### 2.1 UI 元素清单

| 元素 | 类型 | 状态 | 说明 |
|------|------|------|------|
| 项目 | combobox | disabled, value=海剧 | 固定值 |
| 裂变-是否 | radio | disabled, value=否 | 固定值 |
| 裂变-裂变45 | checkbox | checked | 裂变45勾选 |
| 媒体 | combobox | required, value=Facebook(默认) | ⚠️ 需先清除才能选其他 |
| Core | radio group | Core1(选中)/Core4/Core5/Core18/Core23 | ✅ 所有Core选项就绪 |
| 类型 | combobox | disabled, value=视频 | 选图片后待联动 |
| 剧集代号 | combobox | required, 支持搜索 | 搜索输入框 |
| 一级标签 | combobox | required | 待选择 |
| 二级标签 | combobox | disabled | 联动一级标签 |
| 上传区域 | upload zone | 视频模式: 仅支持 video/mp4, 916/45 | 切换图片后变化 |

### 2.2 媒体下拉选项

**全部7个选项**: Facebook(默认选中) / TikTok / Google / Moloco / Applovin / Snapchat / Mintegral

### 2.3 ⚠️ 交互注意事项

1. **媒体切换**: 默认选中 Facebook，需先点击清除按钮(X)取消 Facebook 后才能选择 Applovin
2. **类型联动**: 选择 Applovin 后类型 combobox 从 disabled 变为 enabled，可切"图片"
3. **GIF/PNG选择器**: 预计在"类型=图片"且媒体=Applovin时出现，位于"获取H5图"按钮附近
4. **Ant Design Select**: 使用虚拟滚动+Portal 渲染，agent-browser click 可能无法正确触发 React onChange

---

## 三、风险分析

| # | 风险项 | 等级 | 缓解措施 |
|---|--------|------|----------|
| R1 | Core4/Core5 生成引导图 API 未实现 | 高 | 先验证 API 是否接受 core=4/5 + format 参数 |
| R2 | GIF/PNG 格式选择 UI 未开发完成 | 高 | 探索阶段优先确认 UI 存在性 |
| R3 | 保存上传时 core=4/5 被后端拒绝 | 中 | DB 验证 MaterialUploadLog.Core 字段写入 |
| R4 | Core1 + Applovin 图片功能回归 | 中 | 包含 Core1 回归用例（TC-AL-005/006） |
| R5 | 抽屉柜预览/保存依赖新接口 | 中 | 确认抽屉组件是否复用已有 uploadStore |

---

## 四、用例清单（21条）

### 4.1 P0 — 核心冒烟（6条）

| ID | 用例名称 | 测试类型 |
|----|----------|----------|
| TC-AL-001 | Applovin-Core4-GIF生成-完整链路（生成→抽屉→预览→保存→传输列表） | 功能 |
| TC-AL-002 | Applovin-Core4-PNG生成-完整链路 | 功能 |
| TC-AL-003 | Applovin-Core5-GIF生成-完整链路 | 功能 |
| TC-AL-004 | Applovin-Core5-PNG生成-完整链路 | 功能 |
| TC-AL-005 | Applovin-Core1-GIF生成-回归验证 | 回归 |
| TC-AL-006 | Applovin-Core1-PNG生成-回归验证 | 回归 |

### 4.2 P1 — 主业务流程（8条）

| ID | 用例名称 | 测试类型 |
|----|----------|----------|
| TC-AL-007 | GIF/PNG格式切换-UI交互与按钮状态联动 | 功能 |
| TC-AL-008 | Core切换联动-生成引导图按钮可用性 | 功能 |
| TC-AL-009 | 抽屉柜-生成后自动打开展示 | 功能 |
| TC-AL-010 | 抽屉柜-预览弹窗-点击名称查看图片 | 功能 |
| TC-AL-011 | 抽屉柜-关闭/最小化/恢复操作 | 功能 |
| TC-AL-012 | 保存上传-单条任务提交到传输列表 | 功能 |
| TC-AL-013 | 保存上传-传输列表数据验证（跨页面） | 端到端 |
| TC-AL-014 | 传输列表→审核列表完整数据链路 | 端到端 |

### 4.3 P2 — 边界/补充（5条）

| ID | 用例名称 | 测试类型 |
|----|----------|----------|
| TC-AL-015 | 未选剧集代号时生成引导图按钮禁用 | 异常流程 |
| TC-AL-016 | 未选一级/二级标签时生成按钮禁用 | 异常流程 |
| TC-AL-017 | 抽屉柜-删除单条已生成任务 | 功能 |
| TC-AL-018 | DB验证-MaterialUploadLog.Core=4/5 写入正确 | 功能 |
| TC-AL-019 | DB验证-MaterialInfo关联+ConvertCore任务链 | 功能 |

### 4.4 P3 — 细节验证（2条）

| ID | 用例名称 | 测试类型 |
|----|----------|----------|
| TC-AL-020 | 抽屉柜-批量生成多条任务后列表展示 | 边界值 |
| TC-AL-021 | Core18时生成引导图按钮不显示（预期行为） | 功能 |

### 4.5 覆盖矩阵

| 需求点 | 覆盖用例 |
|--------|----------|
| 媒体选择Applovin | TC-AL-001~021 |
| Core4图片生成 | TC-AL-001/002/008 |
| Core5图片生成 | TC-AL-003/004/008 |
| GIF格式生成 | TC-AL-001/003/005/007 |
| PNG格式生成 | TC-AL-002/004/006/007 |
| GIF/PNG切换 | TC-AL-007 |
| 剧集代号 | TC-AL-001~006/015 |
| 标签 | TC-AL-001~006/016 |
| 抽屉柜展示 | TC-AL-009/018 |
| 预览弹窗 | TC-AL-010 |
| 抽屉柜交互 | TC-AL-011/017/020 |
| 保存上传 | TC-AL-012~014 |
| DB验证 | TC-AL-018/019 |
| Core1回归 | TC-AL-005/006 |
| Core18排除 | TC-AL-021 |

---

## 五、执行顺序与依赖

```
Phase 0 ✓ (已完成: 登录 + Token + 页面可达性确认)
  ↓
Phase 3a ✓ (已完成: 页面探索 + UI元素确认)
  ↓
Phase 1.3 (生成 test_cases.json + test_cases.md)
  ↓
Phase 3b: UI 执行
  ├── TC-AL-001 (Core4+GIF) → 首创链路
  ├── TC-AL-002 (Core4+PNG) → 依赖 TC-AL-001
  ├── TC-AL-003 (Core5+GIF) → Core4 通过后
  ├── TC-AL-004 (Core5+PNG) → 依赖 TC-AL-003
  ├── TC-AL-005/006 (Core1回归) → 新功能通过后
  ├── TC-AL-007/008 (切换交互) → 依赖 TC-AL-001~004
  ├── TC-AL-009~012 (抽屉柜+保存) → 依赖 TC-AL-001 数据
  ├── TC-AL-013/014 (跨页面) → 依赖 TC-AL-012
  ├── TC-AL-015~017 (异常+删除) → 任意时机
  └── TC-AL-020/021 (边界+P3) → 末尾
  ↓
Phase 3.5: API/DB验证 (TC-AL-018/019)
  ↓
Phase 4: 报告生成
```

### 关键依赖链

```
TC-AL-001(首创) → TC-AL-009(抽屉展示) → TC-AL-010(预览) → TC-AL-011(交互)
                                                        → TC-AL-012(保存) → TC-AL-013(传输列表) → TC-AL-014(审核列表)
```

---

## 六、DB验证要点

| 表 | 验证SQL方向 |
|----|------------|
| MaterialUploadLog | `WHERE SourceChlType=6 AND Core IN (4,5) ORDER BY Id DESC` |
| MaterialInfo | `JOIN MaterialUploadLog ON MaterialId` — 验证 MaterialStatus |
| MaterialConvertCoreTask | `WHERE ConvertType IN (4,5)` — 验证转换链 |
| GeneratePictureMaterial | 生成引导图链路的图片记录 |

测试库：`sharpengine_ads_asset_prod` @ tidb-in.changdu.ltd:4000

---

## 七、待确认项

| # | 问题 | 状态 |
|---|------|------|
| Q1 | GIF/PNG 选择 UI 是否已开发？（探索中未看到，需切换Applovin+图片后才能确认） | 🔴 待确认 |
| Q2 | API `GetCompositeImageLocalPathAsync` 是否支持 core=4/5？ | 🔴 待确认 |
| Q3 | 清除Facebook后才能选Applovin的交互是否预期行为？ | 🟡 已确认 |

---

## 八、交付物清单

| # | 文件 | 路径 |
|---|------|------|
| 1 | 测试方案 | `projects/海剧素材上传-Applovin-Core4-Core5/spec/test_plan.md` |
| 2 | 测试用例(JSON) | `projects/海剧素材上传-Applovin-Core4-Core5/spec/test_cases.json` |
| 3 | 测试用例(MD) | `projects/海剧素材上传-Applovin-Core4-Core5/spec/test_cases.md` |
| 4 | 探索结果 | `projects/海剧素材上传-Applovin-Core4-Core5/spec/exploration_result.json` |
| 5 | 执行日志 | `projects/海剧素材上传-Applovin-Core4-Core5/spec/case_execution_log.json` |
| 6 | 测试报告 | `projects/海剧素材上传-Applovin-Core4-Core5/reports/测试报告-Applovin-Core4-Core5-20260624.md` |
