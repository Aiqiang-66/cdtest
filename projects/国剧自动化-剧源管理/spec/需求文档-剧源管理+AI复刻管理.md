# 雷霆素材系统 — 国剧自动化：剧源管理 + AI复刻管理 需求文档

> **文档版本**：v1.0
> **创建日期**：2026年6月8日
> **业务模块**：雷霆素材系统 / 国剧自动化
> **测试环境**：dev（sc-test.changdu.ltd）
> **测试账号**：240017（艾强）
> **需求文档**：https://docs.changdu.vip/pages/viewpage.action?pageId=166421421

---

## 一、需求概述

### 1.1 业务目标

国剧自动化新增两个功能模块：
1. **剧源管理**：管理国剧剧源，支持上传剧源、查询剧源信息
2. **AI复刻管理**：管理AI复刻任务，支持创建AI复刻、查询任务状态

### 1.2 涉及页面

| 页面 | URL |
|------|-----|
| 剧源管理 | `https://sc-test.changdu.ltd/cn-video/source-manage` |
| AI复刻管理 | `https://sc-test.changdu.ltd/cn-video/ai-replica` |

---

## 二、剧源管理页面

### 2.1 筛选条件

| 序号 | 字段名 | 控件类型 | 说明 |
|------|--------|---------|------|
| 1 | 代号 | 下拉搜索 | 支持搜索剧集代号 |
| 2 | 剧源类型 | 下拉框 | 默认"全部" |

### 2.2 操作按钮

| 按钮 | 说明 |
|------|------|
| 查询 | 执行筛选 |
| 上传剧源 | 上传新的剧源文件 |

### 2.3 列表字段

| 字段 | 说明 |
|------|------|
| 短剧名称 | 剧集名称 |
| 短剧代号 | 剧集代号 |
| 短剧ID | 剧集ID |
| 已维护集数 | 已维护的集数 |
| 操作 | 操作按钮 |

---

## 三、AI复刻管理页面

### 3.1 筛选条件

| 序号 | 字段名 | 控件类型 | 说明 |
|------|--------|---------|------|
| 1 | 剧壳代号 | 下拉搜索 | 支持搜索剧壳代号 |
| 2 | 参考视频MD5 | 输入框 | 精确搜索 |
| 3 | 创建人 | 下拉框 | 默认"全部" |
| 4 | 作业状态 | 下拉框 | 默认"全部" |
| 5 | 创建时间 | 日期范围选择 | 开始日期 ~ 结束日期 |

### 3.2 操作按钮

| 按钮 | 说明 |
|------|------|
| 查询 | 执行筛选 |
| 重置 | 重置筛选条件 |
| 创建AI复刻 | 创建新的AI复刻任务 |

### 3.3 列表字段

| 字段 | 说明 |
|------|------|
| ID | 任务ID |
| 剧壳代号 | 剧壳代号 |
| 剧壳ID | 剧壳ID |
| 剧源类型 | 剧源类型 |
| 参考视频 | 参考视频 |
| 参考视频MD5 | 参考视频MD5值 |
| 输出视频 | 输出视频 |
| 作业状态 | 任务状态 |
| 错误信息 | 错误信息 |
| 创建人 | 创建人 |
| 创建时间 | 创建时间 |
| 操作 | 操作按钮 |

---

## 四、数据库相关表

### 4.1 AsyncJobInfo 表

```sql
CREATE TABLE `AsyncJobInfo` (
  `Id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `JobType` int NOT NULL COMMENT '作业类型',
  `DataId` bigint NOT NULL COMMENT '关联数据主键Id',
  `ExtendData` json DEFAULT NULL COMMENT '作业扩展数据',
  `Status` int NOT NULL COMMENT '任务状态|0=已创建,1=执行中,2=成功,3=失败,999=异常',
  `JobId` bigint NOT NULL COMMENT '异步作业ID',
  `JobData` mediumtext DEFAULT NULL COMMENT '异步作业参数',
  `JobResp` mediumtext DEFAULT NULL COMMENT '接口响应返回',
  `Error` mediumtext DEFAULT NULL COMMENT '错误信息',
  `CreateTime` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `UpdateTime` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  `CreatorUid` varchar(256) DEFAULT NULL COMMENT '创建人账号ID',
  `ResetCount` int NOT NULL DEFAULT '0' COMMENT '重置次数',
  PRIMARY KEY (`Id`),
  KEY `idx_JobType_DataId` (`JobType`,`DataId`),
  KEY `idx_JobId` (`JobId`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='异步任务';
```

**JobType 说明：**
- `JobType = 8`：剧源向量处理
- `JobType = 9`：AI复刻

**Status 说明：**
- `0`：已创建
- `1`：执行中
- `2`：成功
- `3`：失败
- `999`：异常

---

## 五、数据流

```
剧源管理（上传剧源）
    ↓
剧源向量处理（AsyncJobInfo, JobType=8）
    ↓
AI复刻管理（创建AI复刻）
    ↓
AI复刻任务（AsyncJobInfo, JobType=9）
    ↓
输出视频
```

---

## 六、待确认问题

1. 剧源管理"上传剧源"支持什么格式的文件？
2. AI复刻管理"创建AI复刻"弹窗中有哪些字段？
3. 剧源类型下拉框有哪些选项？
4. 作业状态下拉框有哪些选项？
5. 操作列有哪些操作按钮？
