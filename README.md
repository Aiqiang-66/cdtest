# cdtest v3.5.2 — AI-Native Unified Test Framework

> AI 原生统一测试框架，支持 Web / iOS / Android / Hybrid 多平台自动化测试，覆盖设计模式（Design Mode）与执行模式（Execution Mode）。

## 🎯 核心理念

**固定骨架 + AI 填充。** 有确定模式的用固定代码，无确定模式的用 AI 判断。

## ✨ 主要特性

- **多平台支持**: Web (Agent-Browser / Selenium), iOS (Appium + XCUITest), Android (Appium + UIAutomator2)
- **Phase Pipeline**: 从环境检查(Phase0) → 需求分析(Phase1) → 数据准备(Phase2) → 用例执行(Phase3) → 报告生成(Phase4) 全链路自动化
- **AI 驱动**: 基于 Claude Code 的 Agent 架构，AI 自动填充测试数据、生成测试用例、执行回归测试
- **知识库同步**: 支持 MCP Test Case Knowledge Base 同步，用例可追溯
- **熔断机制**: 智能检测测试阻塞并自动切换策略
- **大模型服务测试**: 内置 Whisper 语音识别准确率测试 (WER/CER)

## 📂 项目结构

```
cdtest/
├── SKILL.md                    # 核心 Skill 定义与 Phase Pipeline
├── README.md                   # 本文件
├── common/                     # 公共文档与模板
│   ├── phase0-env-check.md     # Phase0: 环境检查
│   ├── phase1-analyze.md       # Phase1: 需求分析
│   ├── phase2-data-prep.md     # Phase2: 数据准备
│   ├── phase3-execute.md       # Phase3: 用例执行
│   ├── phase3_5-api-test.md    # Phase3.5: API 测试
│   ├── phase4-report.md        # Phase4: 报告生成
│   ├── case-template.md        # 用例模板
│   ├── circuit-breaker.md      # 熔断机制
│   ├── db-verify.md            # 数据库校验
│   └── ai-decisions.md         # AI 决策记录
├── android/                    # Android 测试配置
├── ios/                        # iOS 测试配置
├── web/                        # Web 测试配置
├── mixed/                      # 混合(Hybrid)测试配置
├── projects/                   # 各业务模块测试项目
│   ├── 雷霆素材系统-水印图制作功能/
│   ├── 雷霆素材系统-视频混剪/
│   ├── 国剧自动化-剧源管理/
│   ├── 自动化扩语种/
│   ├── applovin同步功能/
│   ├── 口播混剪/
│   └── ...                     # 更多项目
├── docs/                       # 文档与知识库
│   ├── 雷霆数据库/              # 数据库 Schema
│   ├── 雷霆素材接口/            # API 接口文档
│   └── 需求文档/                # 需求文档
├── tools/                      # 工具脚本
│   └── whisper_models/         # Whisper 模型
├── scripts/                    # 项目级脚本
├── references/                 # 参考文档
├── analyze_cases.py            # 用例分析工具
├── analyze_dups.py             # 重复用例分析
└── compare_dups.py             # 用例对比工具
```

## 🚀 快速开始

### 环境要求

- Python 3.13+
- Node.js 18+
- Git

### 安装

```bash
# 克隆仓库
git clone <repo-url>
cd cdtest

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 运行测试

```bash
# Web 端测试
python run_test.py

# 指定 P0 用例
python run_p0_test.py

# API 接口测试
python projects/<项目名>/scripts/api_test.py
```

### 环境变量配置

```bash
# 数据库连接 (用于 DB 校验脚本)
export DB_HOST=your_db_host
export DB_PORT=4000
export DB_USER=your_user
export DB_PASSWORD=your_password
export DB_DATABASE=your_database

# API Token (用于接口测试)
export API_TOKEN=your_jwt_token
```

## 📊 用例分析

项目内置了用例分析工具，支持对测试知识库的全量分析：

```bash
# 用例全面分析
python analyze_cases.py

# 重复用例分析
python analyze_dups.py

# 重名用例字段级对比
python compare_dups.py
```

## 📋 Phase Pipeline

| Phase | 名称 | 输出 |
|-------|------|------|
| Phase 0 | 环境检查 | token_valid + env_ready |
| Phase 1.0 | 需求搜索 | 搜索结果 |
| Phase 1.0.5 | 历史用例关联 | historical_cases.json |
| Phase 1.1 | 配置提取 | 配置 + 模块识别 |
| Phase 1.2 | 测试计划 | test_plan.md |
| Phase 1.3 | 初始用例 | test_cases.json |
| Phase 2 | 数据准备 | data_prep_report.json |
| Phase 3a | 探索测试 | exploration_result.json |
| Phase 1.4 | 用例合并 | 合并后 test_cases.json |
| Phase 3b | 用例执行 | case_execution_log.json + 截图 |
| Phase 3.5 | API 测试 | api_test_results.json |
| Phase 4 | 报告生成 | 测试报告.md |
| KB Sync | 知识库同步 | kb_sync_report.json |

## 🛡️ 安全说明

- 所有数据库密码和 API Token 均通过环境变量注入，代码中不包含硬编码凭证
- `.gitignore` 已配置排除 `settings.local.json`、虚拟环境、二进制模型文件等

## 📄 License

Internal use only.

## 👤 Author

qa-architect
