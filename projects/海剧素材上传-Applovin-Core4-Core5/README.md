# 海剧素材上传 — Applovin Core4/Core5 图片生成引导图 测试

> 测试日期：2026-06-24 | cdtest v3.5.2 | 测试账号：240017

## 项目结构

```
├── README.md                    # 本文件
├── spec/
│   ├── test_plan.md             # 测试方案 (21条用例)
│   ├── test_cases.json          # 测试用例 JSON
│   └── exploration_result.json  # 页面探索结果
├── scripts/
│   └── db_verify.py             # DB 验证脚本
├── reports/
│   └── 测试报告-Applovin-Core4-Core5-20260624.md
└── screenshots/
```

## 快速运行

```bash
# DB验证
export DB_HOST=xxx DB_USER=xxx DB_PASSWORD=xxx
python scripts/db_verify.py
```

## 需求摘要

Applovin 媒体 + 图片类型新增 Core4/Core5 生成引导图（GIF/PNG），含抽屉柜预览+保存上传。

## 结论

✅ **测试通过** — DB 验证 Core4(37条)/Core5(17条) 数据完整，用户手动验证 UI 交互正常。
