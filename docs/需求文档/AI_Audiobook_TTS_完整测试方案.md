# AI Audiobook TTS API 完整测试方案

> **版本**：v2.0
> **日期**：2026-06-13
> **测试接口**：`POST /api/tts/synthesize`
> **服务地址**：`http://ai-audiobook-api-none-new-dev.changdu.ltd`
> **测试模型**：Higgs TTS v3（主要）
> **测试目标**：功能正确性 + 性能 + 字幕准确率 + 稳定性

---

## 〇、测试范围总览（汇报用）

### 0.1 系统架构概览

```
┌─────────────┐     HTTP/JSON      ┌──────────────────┐     GPU推理     ┌──────────────┐
│  调用方      │ ─────────────────> │  TTS API 服务     │ ────────────> │  Higgs TTS    │
│  (听书业务)   │ <───────────────── │  (FastAPI/80端口) │ <──────────── │  (Triton)     │
└─────────────┘    audio_url +      └──────────────────┘   音频流        └──────────────┘
                   metadata_url            │
                                           │ 上传
                                           ▼
                                    ┌──────────────┐
                                    │  腾讯云 COS   │
                                    │  (香港+广州)  │
                                    └──────────────┘
```

| 架构维度 | 说明 |
|------|------|
| **GPU 配置** | 5090 + 4090 × 8 卡 |
| **接口模式** | 同步接口 + 异步接口 均可用 |
| **并发控制** | 最大 16 并发，排队超时 30 秒 |
| **重试机制** | 客户端无重试，**服务端有重试机制**（失败冷却 60 秒） |
| **速率限制** | 无网关/三方限流，仅 16 并发槽位控制 |
| **数据存储** | 模型侧无数据库，音频文件 COS 存储 + 本地临时缓存 |
| **本次测试模型** | **Higgs TTS v3**（WAV→MP3，支持 metadata） |

### 0.2 测试范围矩阵

| 测试维度 | 子项 | 用例数 | 优先级 | 目标指标 |
|---------|------|:--:|:--:|------|
| **1. 稳定性** | 任务成功率/失败率 | 2 | P0 | 成功率 ≥ 99% |
| | 重试机制验证 | 1 | P0 | 服务端重试有效 |
| | 长时间运行稳定性 | 1 | P0 | 24h 错误率 < 0.1% |
| **2. 完整性** | 漏词率（WER/CER） | 4 | P0 | 英文 WER < 5%，中文 CER < 10% |
| | 语音与文案比对 | 2 | P0 | 逐句对齐，语义一致 |
| | 音频音质评估 | 2 | P1 | MOS ≥ 3.5，无杂音/截断 |
| **3. 吞吐率** | 单机吞吐率 | 2 | P0 | ≥ 120 任务/小时（8并发） |
| | 峰值吞吐率 | 1 | P0 | ≥ 200 任务/小时（16并发） |
| | 文本长度影响 | 1 | P1 | 找到最优文本长度 |
| **4. 中英文** | 英文全量 | 15 | P0 | 覆盖短/中/长/特殊文本 |
| | 中文全量 | 15 | P0 | 覆盖短/中/长/特殊文本 |
| | 中英文对比 | 2 | P1 | 量化差异 |
| **5. 功能正确性** | 参数校验 | 14 | P0 | 边界值/类型/缺失 |
| | 异常场景 | 9 | P1 | 空文本/超长/特殊字符 |
| | 响应校验 | 8 | P1 | 结构/格式/可访问性 |
| **合计** | | **62** | | |

### 0.3 核心测试指标一览

| 指标类别 | 指标名称 | 目标值 | 测试方法 |
|------|------|------|------|
| **稳定性** | 任务成功率 | ≥ 99% | 1000 任务统计 |
| | 任务失败率 | < 1% | code=-1 占比 |
| | 24h 错误率波动 | < 0.1% | 每小时采样 |
| | 并发槽位泄漏 | 0 | 满并发后释放验证 |
| **完整性** | 英文 WER | < 5% | Whisper 转写 + 原文对比 |
| | 中文 CER | < 10% | Whisper 转写 + 逐字对比 |
| | 漏词率 | < 2% | Deletion / 总词数 |
| | 多词率 | < 2% | Insertion / 总词数 |
| | 音质 MOS 分 | ≥ 3.5 | 人工评估 + 频谱分析 |
| | 音频截断率 | 0% | 音频时长 vs metadata 时长 |
| **吞吐率** | 8 并发吞吐率 | ≥ 120 任务/h | 30min 持续压力 |
| | 16 并发吞吐率 | ≥ 200 任务/h | 30min 持续压力 |
| | 单任务平均耗时 | < 30s | 300 词文本 |
| **中英文** | 英文功能覆盖 | 100% | 28 用例 |
| | 中文功能覆盖 | 100% | 28 用例 |
| | 中英文 WER 差异 | < 5% | 同长度文本对比 |

### 0.4 测试环境

| 配置项 | 值 |
|------|------|
| 服务地址 | `http://ai-audiobook-api-none-new-dev.changdu.ltd` |
| 测试模型 | Higgs TTS v3 |
| GPU 配置 | 5090 + 4090 × 8 卡 |
| 最大并发 | 16 |
| 排队超时 | 30 秒 |
| 失败冷却 | 60 秒（服务端重试） |
| 音频格式 | WAV → MP3（转码） |
| 存储 | 腾讯云 COS（香港 CDN + 广州） |
| 数据库 | 模型侧无数据库 |
| 文件缓存 | 本地临时缓存（`/data/audiobook/`） |

### 0.5 测试执行计划

| 阶段 | 内容 | 预计时长 | 依赖 |
|------|------|:--:|------|
| Phase 1 | 功能正确性（参数校验+异常+响应） | 2h | 服务可用 |
| Phase 2 | 英文完整性（WER+漏词率+音质） | 3h | Phase 1 通过 |
| Phase 3 | 中文完整性（CER+漏词率+音质） | 3h | Phase 1 通过 |
| Phase 4 | 吞吐率（8/16并发+文本长度） | 3h | 独立环境 |
| Phase 5 | 稳定性（1000任务+24h浸泡） | 26h | 独立环境 |
| Phase 6 | 报告输出 | 1h | 全部完成 |
| **合计** | | **38h** | |

---

## 一、本次测试范围（Higgs TTS 专项）

> **测试模型**：Higgs TTS v3
> **测试语言**：中文 + 英文
> **测试接口**：`POST /api/tts/synthesize`

---

### 1.1 稳定性测试

**测试目标**：验证 Higgs TTS 在大批量任务下的成功率和失败率。

| 测试项 | 测试方法 | 目标指标 |
|--------|----------|----------|
| **大批量任务成功率** | 下发 1000 个 TTS 合成任务（中英文各 500），统计 code=0 / code=-1 / HTTP 错误 | 成功率 ≥ 99%，失败率 < 1% |
| **重试机制验证** | 故意触发失败（如无效 voice），检查服务端重试日志，统计重试后成功率 | 重试成功率 ≥ 80%，最多重试 3 次，冷却 60s |
| **24h 长时间浸泡** | 8 并发持续 24 小时，每小时统计一次成功率 | 每小时成功率 ≥ 99%，无持续下降趋势 |
| **异常恢复** | 模拟 COS 不可用 2 分钟后恢复，观察任务处理 | 故障期间返回 code=-1，恢复后新任务正常 |

**稳定性报告模板**：

| 指标 | 目标 | 实际 | 判定 |
|------|------|------|:--:|
| 总任务数 | 1000 | | |
| 成功率 (code=0) | ≥ 99% | | |
| 业务失败率 (code=-1) | < 1% | | |
| HTTP 错误率 | < 0.1% | | |
| 重试成功率 | ≥ 80% | | |
| 24h 成功率波动 | < 1% | | |

---

### 1.2 完整性测试

**测试目标**：验证 Higgs TTS 合成音频的漏词率、音质问题，以及语音与原文的比对准确率。

#### 1.2.1 漏词率测试（WER/CER）

**测试流程**：
```
原文(read_content) → TTS API → 音频(audio_url) → Whisper ASR 转写 → 转录文本 → 对比原文 → 计算 WER/CER
```

| 测试项 | 测试方法 | 目标指标 |
|--------|----------|----------|
| **英文 WER** | 20 条短文本(50-100词) + 10 条长文本(300-500词)，Whisper 转写后与原文对比 | WER < 5% |
| **中文 CER** | 20 条短文本(50-200字) + 10 条长文本(500-1000字)，Whisper 转写后逐字对比 | CER < 10% |
| **漏词率专项** | 逐词对齐原文和转录文本，统计 Deletion(漏词) / Insertion(多词) / Substitution(替换) | 漏词率 < 2%，多词率 < 2%，替换率 < 3% |
| **句级准确率** | 逐句比对原文与转录文本，标记缺失/多出/替换的句子 | 句级准确率 ≥ 95% |

**WER 计算公式**：
$$WER = \frac{S + D + I}{N} \times 100\%$$

其中：$S$ = 替换词数，$D$ = 删除词数（漏词），$I$ = 插入词数（多词），$N$ = 原文总词数

#### 1.2.2 音频音质评估

| 测试项 | 测试方法 | 目标指标 |
|--------|----------|----------|
| **MOS 主观评分** | 随机抽取 20 条合成音频，3 人独立评分（1-5分） | 平均 MOS ≥ 3.5 |
| **音频完整性** | 对比 audio_length 与实际文件时长，检查开头结尾是否截断 | 时长误差 < 1%，截断率 0% |
| **频谱分析** | 用 librosa 分析频率分布、底噪、削波 | 频率 80Hz-8000Hz，底噪 < -50dB |
| **编码参数** | ffprobe 检查采样率、码率、声道数 | 采样率 ≥ 16000Hz |

#### 1.2.3 语音与文案比对

| 测试项 | 测试方法 | 目标指标 |
|--------|----------|----------|
| **逐句文案比对** | Whisper 转写获取句级时间戳，逐句与原文比对 | 句级准确率 ≥ 95% |
| **语义完整性** | 从原文提取实体（数字/日期/人名/地名），检查转录文本中是否保留 | 实体保留率 ≥ 98% |
| **标点停顿** | 分析 metadata 时间戳间隔，检查标点处停顿 | 句号后停顿 > 300ms，段落间 > 800ms |
| **数字朗读** | 发送含数字/日期/金额的文本，验证朗读正确性 | 正确率 ≥ 95% |

**完整性报告模板**：

| 语言 | 文本数 | WER/CER | 漏词率 | 多词率 | 替换率 | 句准确率 | MOS |
|------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| 英文 | 30 | | | | | | |
| 中文 | 30 | | | | | | |

---

### 1.3 任务吞吐率测试

**测试目标**：测量 Higgs TTS 在不同并发下的任务处理能力（任务/小时）。

| 测试项 | 测试方法 | 目标指标 |
|--------|----------|----------|
| **8 并发吞吐率** | 8 并发持续 30 分钟，统计完成任务数 | ≥ 120 任务/小时 |
| **16 并发吞吐率** | 16 并发持续 30 分钟，统计完成任务数 | ≥ 200 任务/小时 |
| **阶梯并发测试** | 并发 1→2→4→8→12→16→20→24，每阶梯 2 分钟 | 找到吞吐率拐点和最优并发数 |
| **文本长度影响** | 50/100/300/500/1000 词，8 并发各 15 分钟 | 吞吐率与文本长度呈反比 |
| **中英文对比** | 相同字符数（300字 vs 300词），8 并发各 15 分钟 | 量化中英文处理效率差异 |

**吞吐率报告模板**：

| 并发数 | 文本长度 | 时长 | 完成任务 | 失败 | 吞吐率(任务/h) | Avg延迟 | P95延迟 |
|:--:|:--:|------|:--:|:--:|:--:|:--:|:--:|
| 8 | 300词(EN) | 30min | | | | | |
| 16 | 300词(EN) | 30min | | | | | |
| 8 | 300字(ZH) | 30min | | | | | |
| 16 | 300字(ZH) | 30min | | | | | |

---

### 1.4 测试语言范围

**测试语言**：中文 + 英文（Higgs TTS 主要支持语言）

| 语言 | 测试维度 | 用例数 | 说明 |
|------|---------|:--:|------|
| **英文 (en)** | 功能正确性 | 15 | 短/中/长/多段落/特殊字符文本 |
| | 完整性 (WER) | 6 | Whisper 转写 + 原文对比 |
| | 吞吐率 | 5 | 8/16 并发 + 文本长度影响 |
| | 稳定性 | 4 | 成功率 + 重试 + 长时间 |
| **中文 (zh)** | 功能正确性 | 15 | 短/中/长/多段落/特殊字符文本 |
| | 完整性 (CER) | 6 | Whisper 转写 + 逐字对比 |
| | 吞吐率 | 5 | 8/16 并发 + 文本长度影响 |
| | 稳定性 | 4 | 成功率 + 重试 + 长时间 |

**中英文差异关注点**：

| 关注点 | 英文 | 中文 |
|------|------|------|
| 评估指标 | WER（词错误率，空格分词） | CER（字错误率，逐字对比） |
| 标点符号 | ASCII 标点（. , ? !） | 全角标点（，。！？） |
| 数字读法 | 按英文规则朗读 | 按中文规则朗读 |
| 多音字 | 无 | 需关注（行 xing/hang 等） |
| 专有名词 | 首字母大写识别 | 无大小写区分 |

---

### 1.5 性能压测（QPS）

**测试目标**：通过压力测试获取 Higgs TTS 的 QPS（每秒请求数）数据。

| 测试项 | 测试方法 | 目标指标 |
|--------|----------|----------|
| **单请求基准** | 短(50词)/中(300词)/长(1000词)各 10 次取平均 | 建立 P50/P95/P99 基线 |
| **16 并发压测** | ThreadPoolExecutor(16) 持续 10 分钟，统计 QPS | QPS ≥ 2 req/s，成功率 ≥ 99% |
| **阶梯并发压测** | 并发 1→2→4→8→12→16→20→24→28→32，每阶梯 2 分钟 | 找到 QPS 拐点和最大有效并发 |
| **冷启动 vs 热启动** | 重启后立即发 10 个请求 vs 运行 30 分钟后发 10 个请求 | 冷启动不超过热启动 2 倍 |
| **资源监控** | 16 并发 30 分钟，每 30s 记录 CPU/内存 | 内存增长 < 10%/小时，无泄漏 |

**QPS 报告模板**：

| 并发数 | 文本长度 | P50 | P95 | P99 | Avg | QPS | 成功率 |
|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| 1 | 300词 | | | | | | |
| 8 | 300词 | | | | | | |
| 16 | 300词 | | | | | | |
| 16 | 50词 | | | | | | |
| 16 | 1000词 | | | | | | |

---

### 1.6 本次测试模型说明

| 项目 | 说明 |
|------|------|
| **测试模型** | **Higgs TTS v3** |
| **模型特点** | 本地 GPU 推理（Triton），WAV→MP3 转码，支持 metadata 输出 |
| **GPU 配置** | 5090 + 4090 × 8 卡 |
| **接口模式** | 同步接口 + 异步接口均可用 |
| **最大并发** | 16 并发槽位 |
| **排队超时** | 30 秒 |
| **重试机制** | 服务端重试，失败冷却 60 秒，最多 3 次 |
| **音频格式** | MP3（WAV 合成后转码） |
| **存储** | 腾讯云 COS（香港 CDN + 广州） |

---

## 二、性能测试方案

### 2.1 测试目标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| P50 响应时间 | < 5s | 中等文本(~300字符) |
| P95 响应时间 | < 15s | 中等文本 |
| P99 响应时间 | < 30s | 中等文本 |
| 吞吐量(TPS) | ≥ 2 req/s | 16并发持续压力 |
| 首字节时间(TTFB) | < 500ms | 不含TTS合成 |
| 并发成功率 | ≥ 99% | 16并发持续10分钟 |
| COS上传耗时 | < 2s | 音频文件上传 |
| 端到端延迟 | < 20s | 请求→音频URL可访问 |

### 2.2 性能测试用例

#### TC-PF-001：单请求基准响应时间

| 项目 | 内容 |
|------|------|
| **测试目的** | 测量各引擎单请求的基准响应时间 |
| **测试方法** | 分别对 minimax/f5tts/higgs 发送短/中/长文本，各执行 10 次取平均 |
| **测试数据** | 短(50词)、中(300词)、长(1000词) |
| **预期结果** | 记录 P50/P95/P99，建立性能基线 |
| **校验点** | 1. 响应时间与文本长度正相关<br>2. f5tts/higgs 流式模式不应比 minimax 慢超过 3 倍 |

**测试脚本框架**：
```python
import time, requests, statistics

def benchmark_single(model, text, voice, iterations=10):
    times = []
    for i in range(iterations):
        start = time.time()
        resp = requests.post(URL, json={
            "read_content": text,
            "chapter_title": f"Benchmark {i}",
            "model": model,
            "voice": voice,
            "lang": 3
        })
        elapsed = time.time() - start
        times.append(elapsed)
    return {
        "model": model,
        "text_len": len(text),
        "p50": statistics.median(times),
        "p95": statistics.quantiles(times, n=20)[18],
        "p99": statistics.quantiles(times, n=100)[98],
        "min": min(times),
        "max": max(times),
        "avg": statistics.mean(times)
    }
```

---

#### TC-PF-002：并发压力测试（16并发）

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证在最大并发数下系统的吞吐量和稳定性 |
| **测试方法** | 使用 ThreadPoolExecutor(16) 持续发送请求 10 分钟 |
| **测试数据** | 中等文本(~300字符)，f5tts 模型 |
| **预期结果** | 1. 所有请求返回 HTTP 200<br>2. code=0 成功率 ≥ 99%<br>3. 无 503 错误<br>4. 平均响应时间不超过单请求的 3 倍 |
| **校验点** | 统计成功/失败/超时数量，计算实际 TPS |

**测试脚本框架**：
```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import time, requests

def concurrent_stress_test(duration_seconds=600, concurrency=16):
    results = {"success": 0, "fail": 0, "503": 0, "times": []}
    start_time = time.time()
    
    def worker():
        while time.time() - start_time < duration_seconds:
            t0 = time.time()
            try:
                resp = requests.post(URL, json=PAYLOAD, timeout=60)
                elapsed = time.time() - t0
                results["times"].append(elapsed)
                if resp.status_code == 503:
                    results["503"] += 1
                elif resp.json().get("code") == 0:
                    results["success"] += 1
                else:
                    results["fail"] += 1
            except:
                results["fail"] += 1
    
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(worker) for _ in range(concurrency)]
        for f in as_completed(futures):
            f.result()
    
    total = results["success"] + results["fail"] + results["503"]
    return {
        "duration": duration_seconds,
        "total_requests": total,
        "tps": total / duration_seconds,
        "success_rate": results["success"] / total * 100 if total else 0,
        "503_rate": results["503"] / total * 100 if total else 0,
        "avg_response_time": statistics.mean(results["times"]),
        "p95_response_time": statistics.quantiles(results["times"], n=20)[18]
    }
```

---

#### TC-PF-003：阶梯式并发测试

| 项目 | 内容 |
|------|------|
| **测试目的** | 找到系统性能拐点和最大有效并发数 |
| **测试方法** | 并发数从 1 逐步增加到 32，每阶梯持续 2 分钟 |
| **阶梯** | 1→2→4→8→12→16→20→24→28→32 |
| **预期结果** | 1. 16并发内响应时间线性增长<br>2. 超过16后出现503<br>3. 绘制并发数 vs 响应时间/TPS 曲线 |
| **校验点** | 确定最优并发数和系统瓶颈点 |

---

#### TC-PF-004：各引擎性能对比

| 项目 | 内容 |
|------|------|
| **测试目的** | 对比 minimax/f5tts/higgs 三个引擎的性能差异 |
| **测试方法** | 相同文本(300词)，各引擎单请求 20 次，并发 8 各 5 分钟 |
| **预期结果** | 生成性能对比表 |
| **校验点** | 1. f5tts 流式模式首字节时间应最短<br>2. minimax 端到端时间可能最长(外部API)<br>3. higgs 性能应与 f5tts 接近 |

---

#### TC-PF-005：文本长度对性能的影响

| 项目 | 内容 |
|------|------|
| **测试目的** | 分析文本长度与响应时间的关系 |
| **测试方法** | 使用 f5tts，文本长度从 50 到 5000 词，每档 5 次 |
| **文本档位** | 50, 100, 200, 500, 1000, 2000, 5000 词 |
| **预期结果** | 响应时间与文本长度呈近似线性关系 |
| **校验点** | 计算线性回归 R²，预期 > 0.8 |

---

#### TC-PF-006：COS上传性能

| 项目 | 内容 |
|------|------|
| **测试目的** | 测量音频文件上传到 COS 的耗时占比 |
| **测试方法** | 在代码中打点记录：TTS合成耗时 vs COS上传耗时 |
| **预期结果** | COS上传耗时 < 总耗时的 20% |
| **校验点** | 香港COS上传应在 2s 内完成 |

---

#### TC-PF-007：冷启动 vs 热启动

| 项目 | 内容 |
|------|------|
| **测试目的** | 对比服务刚启动时和运行一段时间后的性能差异 |
| **测试方法** | 1. 重启服务后立即发送 10 个请求<br>2. 运行 30 分钟后发送 10 个请求<br>3. 对比两组响应时间 |
| **预期结果** | 冷启动可能略慢（模型加载），但不应超过热启动的 2 倍 |
| **校验点** | 首次请求可能触发模型懒加载 |

---

#### TC-PF-008：内存/CPU监控

| 项目 | 内容 |
|------|------|
| **测试目的** | 监控长时间运行下的资源使用 |
| **测试方法** | 16并发持续 30 分钟，每 30 秒记录内存/CPU |
| **监控命令** | `ps -p <pid> -o %cpu,%mem,rss,vsz` |
| **预期结果** | 1. 内存无持续增长（无泄漏）<br>2. CPU 使用率稳定<br>3. 测试结束后内存回落 |
| **校验点** | 内存增长 < 10%/小时 |

---

## 三、字幕准确率测试方案

### 3.1 测试目标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 时间戳准确率 | ≥ 95% | startMs/endMs 与实际音频对齐 |
| 文本对齐准确率 | ≥ 98% | metadata text 与原文一致 |
| 词级时间误差 | < 200ms | 单词边界误差 |
| 句级时间误差 | < 500ms | 句子边界误差 |
| 漏字率 | < 1% | 原文有但音频/字幕缺失 |
| 多字率 | < 1% | 原文无但音频/字幕多出 |

### 3.2 字幕准确率测试用例

#### TC-AC-001：时间戳单调性校验

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 metadata 中时间戳严格递增无重叠 |
| **测试方法** | 下载 metadata JSON，逐条检查 |
| **校验逻辑** | 1. `startMs[i] < endMs[i]`<br>2. `endMs[i] <= startMs[i+1]`（允许微小间隙）<br>3. `id` 字段连续递增 |
| **预期结果** | 100% 通过单调性检查 |

**校验脚本**：
```python
def validate_timestamps(metadata):
    errors = []
    for i, item in enumerate(metadata):
        if item["startMs"] >= item["endMs"]:
            errors.append(f"Item {i}: startMs({item['startMs']}) >= endMs({item['endMs']})")
        if i > 0 and metadata[i-1]["endMs"] > item["startMs"] + 100:
            errors.append(f"Overlap at {i}: prev end={metadata[i-1]['endMs']}, cur start={item['startMs']}")
    return errors
```

---

#### TC-AC-002：文本偏移量一致性

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 startOffset/endOffset 与原始文本对应 |
| **测试方法** | 用 metadata 中的 offset 从原文截取，与 metadata.text 对比 |
| **校验逻辑** | `original_text[item.startOffset:item.endOffset] == item.text` |
| **预期结果** | 100% 匹配 |

**校验脚本**：
```python
def validate_offsets(original_text, metadata):
    errors = []
    for i, item in enumerate(metadata):
        extracted = original_text[item["startOffset"]:item["endOffset"]]
        if extracted != item["text"]:
            errors.append(f"Item {i}: offset text '{extracted}' != metadata text '{item['text']}'")
    return errors
```

---

#### TC-AC-003：WER（词错误率）计算

| 项目 | 内容 |
|------|------|
| **测试目的** | 使用 ASR 转写音频，与原文对比计算 WER |
| **测试方法** | 1. 下载 audio_url 音频<br>2. 使用 Whisper/ASR 引擎转写<br>3. 与原始 read_content 对比 |
| **计算公式** | WER = (S + D + I) / N（替换+删除+插入 / 总词数） |
| **预期结果** | WER < 5%（英文），WER < 10%（中文） |
| **校验点** | 分别测试 minimax/f5tts/higgs 的 WER |

**测试脚本框架**：
```python
import whisper  # 或使用 faster-whisper

def calculate_wer(audio_path, reference_text):
    model = whisper.load_model("base")
    result = model.transcribe(audio_path)
    hypothesis = result["text"]
    
    # 使用 jiwer 库计算 WER
    import jiwer
    wer = jiwer.wer(reference_text, hypothesis)
    return {
        "wer": wer,
        "reference": reference_text,
        "hypothesis": hypothesis,
        "audio_duration": result.get("duration", 0)
    }
```

---

#### TC-AC-004：段落索引正确性

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证多段落文本的 paraIndex 正确分段 |
| **测试方法** | 发送 3 段落文本，检查 metadata 中 paraIndex 分布 |
| **校验逻辑** | 1. paraIndex 覆盖 0/1/2<br>2. 同一 paraIndex 的 text 拼接后与原文段落一致 |
| **预期结果** | 段落边界正确，无跨段落混叠 |

---

#### TC-AC-005：时间戳与音频对齐（人工抽检）

| 项目 | 内容 |
|------|------|
| **测试目的** | 人工验证时间戳与实际音频朗读对齐 |
| **测试方法** | 1. 随机抽取 5 个 metadata 片段<br>2. 用音频播放器跳转到 startMs<br>3. 人工判断朗读内容是否与 text 一致 |
| **预期结果** | 5/5 对齐，误差 < 200ms |
| **校验点** | 特别关注段落开头和结尾的时间戳 |

---

#### TC-AC-006：跨引擎字幕一致性

| 项目 | 内容 |
|------|------|
| **测试目的** | 同一文本用不同引擎合成，对比 metadata 差异 |
| **测试方法** | 相同文本分别用 minimax/f5tts/higgs 合成 |
| **预期结果** | 1. 各引擎 metadata 结构一致<br>2. 时间戳因语速不同有差异属正常<br>3. text 内容应与原文一致 |
| **校验点** | elevenlabs 无 metadata（预期为空） |

---

## 四、稳定性测试方案

### 4.1 测试目标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 持续运行时间 | ≥ 24 小时 | 无崩溃无重启 |
| 内存泄漏 | < 5% / 24h | RSS 增长 |
| 错误率 | < 0.1% | 长时间运行 |
| 恢复时间 | < 60s | 异常恢复后正常服务 |
| 磁盘空间 | 无堆积 | 临时文件清理 |

### 4.2 稳定性测试用例

#### TC-ST-001：24小时浸泡测试

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证服务长时间运行的稳定性 |
| **测试方法** | 8 并发持续发送请求 24 小时，每 5 分钟记录一次状态 |
| **监控指标** | 1. 成功/失败/超时计数<br>2. 响应时间趋势<br>3. 内存/CPU 趋势<br>4. 磁盘使用趋势 |
| **预期结果** | 1. 无崩溃<br>2. 错误率 < 0.1%<br>3. 响应时间无持续恶化<br>4. 内存无持续增长 |
| **校验点** | 生成趋势图，分析是否存在性能衰减 |

**监控脚本框架**：
```python
import psutil, time, json, os

def monitor_process(pid, duration_hours=24, interval_seconds=300):
    proc = psutil.Process(pid)
    log = []
    start = time.time()
    while time.time() - start < duration_hours * 3600:
        mem = proc.memory_info()
        cpu = proc.cpu_percent(interval=1)
        log.append({
            "timestamp": time.time(),
            "rss_mb": mem.rss / 1024 / 1024,
            "vms_mb": mem.vms / 1024 / 1024,
            "cpu_percent": cpu,
            "threads": proc.num_threads(),
            "open_fds": proc.num_fds() if hasattr(proc, 'num_fds') else -1
        })
        time.sleep(interval_seconds)
    return log
```

---

#### TC-ST-002：内存泄漏检测

| 项目 | 内容 |
|------|------|
| **测试目的** | 检测长时间运行是否存在内存泄漏 |
| **测试方法** | 1. 记录初始 RSS<br>2. 16 并发持续运行 6 小时<br>3. 停止请求后等待 10 分钟<br>4. 对比 RSS 是否回落 |
| **预期结果** | 1. RSS 增长 < 5%/小时<br>2. 停止请求后 RSS 回落至接近初始值 |
| **校验点** | 使用 `gc` 模块和 `tracemalloc` 辅助分析 |

---

#### TC-ST-003：异常恢复测试

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证外部依赖异常后服务能自动恢复 |
| **测试场景** | 1. COS 暂时不可用（模拟网络中断）<br>2. TTS 引擎返回错误<br>3. 磁盘空间不足 |
| **测试方法** | 使用故障注入（如 iptables 阻断 COS 域名 30 秒后恢复） |
| **预期结果** | 1. 故障期间返回 code=-1<br>2. 恢复后下一个请求正常成功<br>3. 不导致服务崩溃 |
| **校验点** | 恢复时间 < 60 秒 |

---

#### TC-ST-004：并发槽位泄漏检测

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证异常情况下并发槽位不会泄漏 |
| **测试方法** | 1. 发送 5 个正常请求<br>2. 发送 1 个会导致 TTS 超时的请求<br>3. 等待超时后立即发送 16 个请求 |
| **预期结果** | 超时请求释放槽位后，后续 16 个请求全部正常（无 503） |
| **校验点** | 并发槽位数量始终 ≤ 16 |

---

#### TC-ST-005：临时文件清理

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证音频临时文件不会无限堆积 |
| **测试方法** | 1. 记录 `/data/audiobook/` 初始文件数<br>2. 发送 100 个请求<br>3. 等待 5 分钟后再次检查文件数 |
| **预期结果** | 临时文件被正确清理，文件数不持续增长 |
| **校验点** | 临时文件应有 TTL 机制 |

---

#### TC-ST-006：快速重启恢复

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证服务重启后快速恢复服务能力 |
| **测试方法** | 1. 发送请求确认服务正常<br>2. 重启服务<br>3. 立即发送请求，记录恢复时间 |
| **预期结果** | 重启后 30 秒内可正常服务 |
| **校验点** | 首个请求可能触发模型加载，允许稍慢 |

---

#### TC-ST-007：网络波动测试

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证网络不稳定时的服务表现 |
| **测试方法** | 使用 `tc` (traffic control) 模拟：<br>1. 10% 丢包率<br>2. 200ms 延迟<br>3. 带宽限制 1Mbps |
| **预期结果** | 1. 请求可能变慢但不崩溃<br>2. 超时请求正确返回错误<br>3. 网络恢复后服务正常 |
| **校验点** | 无部分成功/数据不一致 |

---

## 五、测试执行计划

### 5.1 测试阶段

| 阶段 | 内容 | 时长 | 依赖 |
|------|------|:--:|------|
| Phase 1 | 功能+参数校验（28+14用例） | 2h | 服务可用 |
| Phase 2 | 异常+响应校验（9+8用例） | 1h | Phase 1 通过 |
| Phase 3 | 性能基准测试（8用例） | 3h | 独立环境 |
| Phase 4 | 字幕准确率（6用例） | 2h | ASR 环境 |
| Phase 5 | 稳定性测试（7用例） | 26h | 独立环境 |
| Phase 6 | 报告生成 | 1h | 全部完成 |

### 5.2 环境要求

| 环境 | 用途 | 配置 |
|------|------|------|
| 功能测试环境 | Phase 1-2 | dev3 即可 |
| 性能测试环境 | Phase 3-5 | 独立实例，避免干扰 |
| ASR 环境 | Phase 4 | GPU 服务器 + Whisper |

### 5.3 测试数据准备

| 数据类型 | 数量 | 用途 |
|------|:--:|------|
| 短文本(50词) | 20条 | 基准性能 |
| 中文本(300词) | 50条 | 压力测试 |
| 长文本(1000词) | 10条 | 极限测试 |
| 超长文本(5000词) | 3条 | 边界测试 |
| 中文文本 | 10条 | 多语言 |
| 特殊字符文本 | 5条 | 鲁棒性 |
| 多段落文本 | 5条 | 段落校验 |

---

## 六、测试脚本目录结构

```
tests/
├── functional/
│   ├── test_normal.py          # TC-N-001 ~ TC-N-007
│   ├── test_validation.py      # TC-V-001 ~ TC-V-014
│   ├── test_concurrency.py     # TC-C-001 ~ TC-C-003
│   ├── test_exception.py       # TC-E-001 ~ TC-E-009
│   └── test_response.py        # TC-R-001 ~ TC-R-008
├── performance/
│   ├── benchmark_single.py     # TC-PF-001, TC-PF-004, TC-PF-005
│   ├── stress_concurrent.py    # TC-PF-002, TC-PF-003
│   ├── benchmark_cos.py        # TC-PF-006
│   ├── cold_start.py           # TC-PF-007
│   └── monitor_resources.py    # TC-PF-008
├── accuracy/
│   ├── validate_timestamps.py  # TC-AC-001
│   ├── validate_offsets.py     # TC-AC-002
│   ├── calculate_wer.py        # TC-AC-003
│   ├── validate_paragraphs.py  # TC-AC-004
│   └── manual_alignment.py     # TC-AC-005
├── stability/
│   ├── soak_test_24h.py        # TC-ST-001
│   ├── memory_leak.py          # TC-ST-002
│   ├── fault_injection.py      # TC-ST-003
│   ├── slot_leak.py            # TC-ST-004
│   ├── temp_file_check.py      # TC-ST-005
│   ├── restart_recovery.py     # TC-ST-006
│   └── network_chaos.py        # TC-ST-007
├── stability_special/
│   ├── batch_success_rate.py   # TC-STAB-001 大批量成功率
│   ├── retry_mechanism.py      # TC-STAB-002 重试机制
│   ├── long_run_stability.py   # TC-STAB-003 长时间稳定性
│   └── fault_recovery.py       # TC-STAB-004 异常恢复
├── integrity/
│   ├── wer_english_short.py    # TC-INT-001 英文短文本WER
│   ├── wer_english_long.py     # TC-INT-002 英文长文本WER
│   ├── cer_chinese_short.py    # TC-INT-003 中文短文本CER
│   ├── cer_chinese_long.py     # TC-INT-004 中文长文本CER
│   ├── word_error_analysis.py  # TC-INT-005 漏词率分析
│   └── cross_engine_wer.py     # TC-INT-006 跨引擎对比
├── throughput/
│   ├── throughput_bench.py     # TC-TP-001 吞吐率基准
│   ├── engine_compare_tp.py    # TC-TP-002 多引擎对比
│   ├── text_length_tp.py       # TC-TP-003 文本长度影响
│   ├── zh_en_compare_tp.py     # TC-TP-004 中英文对比
│   └── peak_stress_tp.py       # TC-TP-005 峰值压测
├── test_data/
│   ├── english_texts.json      # 英文测试数据
│   └── chinese_texts.json      # 中文测试数据
├── conftest.py                  # 公共配置/fixture
├── test_data.py                 # 测试数据
└── run_all.py                   # 一键执行入口
```

---

## 七、报告模板

### 7.1 性能测试报告

| 引擎 | 文本长度 | P50 | P95 | P99 | Avg | TPS(16并发) |
|------|---------|-----|-----|-----|-----|------------|
| minimax | 50词 | | | | | |
| minimax | 300词 | | | | | |
| f5tts | 50词 | | | | | |
| f5tts | 300词 | | | | | |
| higgs | 50词 | | | | | |
| higgs | 300词 | | | | | |

### 7.2 字幕准确率报告

| 引擎 | 时间戳单调性 | Offset一致性 | WER | 段落正确性 |
|------|:--:|:--:|:--:|:--:|
| minimax | | | | |
| f5tts | | | | |
| higgs | | | | |

### 7.3 稳定性报告

| 指标 | 目标 | 实际 | 判定 |
|------|------|------|:--:|
| 24h错误率 | < 0.1% | | |
| 内存增长 | < 5%/24h | | |
| 恢复时间 | < 60s | | |
| 临时文件堆积 | 无 | | |

---

## 八、稳定性专项：任务成功率与重试机制

### 8.1 测试目标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 任务成功率 | ≥ 99% | code=0 占比 |
| 任务失败率 | < 1% | code=-1 或 HTTP 非200 |
| 重试覆盖率 | 100% | 失败任务是否有重试记录 |
| 重试成功率 | ≥ 80% | 重试后成功的比例 |
| 最大重试次数 | ≤ 3 | 单任务重试上限 |
| 重试间隔 | 60s | 失败冷却时间 |

### 8.2 测试用例

#### TC-STAB-001：大批量任务成功率统计

| 项目 | 内容 |
|------|------|
| **测试目的** | 统计大批量 TTS 合成任务的成功/失败率 |
| **测试方法** | 发送 1000 个请求（中英文各 500），统计 code=0 / code=-1 / HTTP错误 |
| **测试数据** | 中文 300 字 × 500 + 英文 300 词 × 500，f5tts 模型 |
| **预期结果** | 成功率 ≥ 99%，失败率 < 1% |
| **校验点** | 1. 分类统计成功(code=0)/业务失败(code=-1)/HTTP错误<br>2. 失败任务记录错误原因(msg字段)<br>3. 按引擎/语言维度分别统计 |

**测试脚本框架**：
```python
import requests, time, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

def batch_success_rate_test(requests_list, concurrency=8):
    """
    requests_list: [{"payload": {...}, "id": "xxx"}, ...]
    """
    results = {
        "total": 0, "success": 0, "business_fail": 0, "http_error": 0,
        "errors": Counter(), "latencies": [], "retry_success": 0
    }
    
    def do_request(req):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                t0 = time.time()
                resp = requests.post(URL, json=req["payload"], timeout=120)
                latency = time.time() - t0
                
                if resp.status_code == 200:
                    body = resp.json()
                    if body.get("code") == 0:
                        return {"id": req["id"], "status": "success", "latency": latency, "retries": attempt}
                    else:
                        if attempt < max_retries - 1:
                            time.sleep(60)  # 冷却
                            continue
                        return {"id": req["id"], "status": "business_fail", "msg": body.get("msg"), "retries": attempt}
                elif resp.status_code == 503:
                    time.sleep(30)
                    continue
                else:
                    return {"id": req["id"], "status": "http_error", "code": resp.status_code, "retries": attempt}
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(10)
                    continue
                return {"id": req["id"], "status": "exception", "error": str(e), "retries": attempt}
    
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {executor.submit(do_request, r): r for r in requests_list}
        for f in as_completed(futures):
            r = f.result()
            results["total"] += 1
            results[r["status"]] += 1
            if r["status"] == "success":
                results["latencies"].append(r["latency"])
                if r["retries"] > 0:
                    results["retry_success"] += 1
            else:
                results["errors"][r.get("msg", r.get("error", "unknown"))] += 1
    
    results["success_rate"] = results["success"] / results["total"] * 100
    results["avg_latency"] = sum(results["latencies"]) / len(results["latencies"]) if results["latencies"] else 0
    return results
```

---

#### TC-STAB-002：重试机制验证

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证失败任务是否有重试机制，重试是否有效 |
| **测试方法** | 1. 故意触发失败（如无效 voice）<br>2. 检查服务端日志是否有重试记录<br>3. 统计重试后成功率 |
| **预期结果** | 1. 失败后有 60s 冷却<br>2. 最多重试 3 次<br>3. 重试后成功率 ≥ 80% |
| **校验点** | 1. 重试次数不超过上限<br>2. 重试间隔符合配置<br>3. 重试不会导致重复扣费 |

---

#### TC-STAB-003：长时间运行稳定性

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 24 小时持续运行的任务成功率是否稳定 |
| **测试方法** | 8 并发持续 24 小时，每小时统计一次成功率 |
| **预期结果** | 每小时成功率均 ≥ 99%，无持续下降趋势 |
| **校验点** | 绘制成功率趋势图，检测是否存在性能衰减 |

---

#### TC-STAB-004：异常恢复后任务重试

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证外部依赖故障恢复后，积压任务能否正常处理 |
| **测试方法** | 1. 发送 50 个请求<br>2. 模拟 COS 不可用 2 分钟<br>3. 恢复后观察任务处理情况 |
| **预期结果** | 故障期间任务失败(code=-1)，恢复后新任务正常，无任务丢失 |
| **校验点** | 无任务永久卡住，无并发槽位泄漏 |

---

### 8.3 稳定性报告模板

| 指标 | 目标 | 实际 | 判定 |
|------|------|------|:--:|
| 总任务数 | - | | |
| 成功率 | ≥ 99% | | |
| 业务失败率 | < 1% | | |
| HTTP错误率 | < 0.1% | | |
| 重试成功率 | ≥ 80% | | |
| 平均重试次数 | ≤ 1 | | |
| 24h成功率波动 | < 1% | | |

---

## 九、完整性专项：漏词率（WER）测试

### 9.1 测试目标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 英文 WER | < 5% | 词错误率 |
| 中文 CER | < 10% | 字错误率（中文用字符级） |
| 漏词率 | < 2% | 原文有但音频缺失的词 |
| 多词率 | < 2% | 原文无但音频多出的词 |
| 替换率 | < 3% | 识别错误的词 |
| 句级准确率 | ≥ 95% | 完整句子正确比例 |

### 9.2 测试流程

```
原文(read_content) → TTS API → 音频(audio_url) → Whisper ASR → 转录文本 → 对比原文 → 计算 WER/CER
```

### 9.3 测试用例

#### TC-INT-001：英文短文本 WER

| 项目 | 内容 |
|------|------|
| **测试目的** | 测量英文短文本的 WER |
| **测试方法** | 1. 发送 50 词英文文本到 TTS API<br>2. 下载生成的音频<br>3. 用 Whisper 转写音频<br>4. 对比原文计算 WER |
| **测试数据** | 20 条短文本（50-100 词），覆盖不同主题 |
| **预期结果** | WER < 5% |
| **校验点** | 分别统计 S(替换)/D(删除)/I(插入) 三类错误 |

---

#### TC-INT-002：英文长文本 WER

| 项目 | 内容 |
|------|------|
| **测试目的** | 测量英文长文本的 WER |
| **测试方法** | 同上，使用 300-500 词文本 |
| **测试数据** | 10 条长文本（小说段落） |
| **预期结果** | WER < 5% |
| **校验点** | 长文本不应比短文本显著恶化 |

---

#### TC-INT-003：中文短文本 CER

| 项目 | 内容 |
|------|------|
| **测试目的** | 测量中文文本的字错误率（CER） |
| **测试方法** | 1. 发送 100 字中文文本<br>2. 下载音频<br>3. Whisper 转写<br>4. 逐字对比计算 CER |
| **测试数据** | 20 条中文短文本（50-200 字） |
| **预期结果** | CER < 10% |
| **校验点** | 中文分词不做词级对比，用字符级 CER |

---

#### TC-INT-004：中文长文本 CER

| 项目 | 内容 |
|------|------|
| **测试目的** | 测量中文长文本的字错误率 |
| **测试方法** | 同上，使用 500-1000 字文本 |
| **测试数据** | 10 条中文长文本（小说章节） |
| **预期结果** | CER < 10% |
| **校验点** | 长文本 CER 不应显著高于短文本 |

---

#### TC-INT-005：漏词率专项分析

| 项目 | 内容 |
|------|------|
| **测试目的** | 精确统计漏词（原文有、音频无）和多词（原文无、音频有） |
| **测试方法** | 1. 用 Whisper 获取词级时间戳<br>2. 逐词对齐原文和转录文本<br>3. 统计 Deletion(漏词) / Insertion(多词) / Substitution(替换) |
| **预期结果** | 漏词率 < 2%，多词率 < 2% |
| **校验点** | 分析漏词模式：是否集中在特定词性（专有名词、数字等） |

**漏词分析脚本**：
```python
def analyze_word_errors(reference, hypothesis):
    """分析漏词/多词/替换"""
    import jiwer
    
    # 使用 jiwer 的详细输出
    measures = jiwer.compute_measures(reference, hypothesis)
    words = jiwer.process_words(reference, hypothesis)
    
    deletions = [w for w in words.deletions]
    insertions = [w for w in words.insertions]
    substitutions = [(w.ref, w.hyp) for w in words.substitutions]
    hits = len(words.hits)
    
    total = hits + len(deletions) + len(substitutions)
    
    return {
        "wer": measures["wer"],
        "total_words": total,
        "correct": hits,
        "deletions": len(deletions),
        "deletion_rate": len(deletions) / total,
        "insertions": len(insertions),
        "insertion_rate": len(insertions) / total,
        "substitutions": len(substitutions),
        "substitution_rate": len(substitutions) / total,
        "deletion_examples": deletions[:10],
        "substitution_examples": substitutions[:10],
    }
```

---

#### TC-INT-006：跨引擎完整性对比

| 项目 | 内容 |
|------|------|
| **测试目的** | 对比 minimax/f5tts/higgs 三个引擎的 WER/CER |
| **测试方法** | 相同 20 条文本，分别用三个引擎合成，计算 WER |
| **预期结果** | 三个引擎 WER 差异 < 3% |
| **校验点** | 生成对比表，识别最优引擎 |

---

### 9.4 完整性报告模板

| 引擎 | 语言 | 文本数 | WER/CER | 漏词率 | 多词率 | 替换率 | 句准确率 |
|------|------|:--:|:--:|:--:|:--:|:--:|:--:|
| minimax | EN | 20 | | | | | |
| minimax | ZH | 20 | | | | | |
| f5tts | EN | 20 | | | | | |
| f5tts | ZH | 20 | | | | | |
| higgs | EN | 20 | | | | | |
| higgs | ZH | 20 | | | | | |

---

## 十、吞吐率专项：任务处理能力

### 10.1 测试目标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 单机吞吐率 | ≥ 120 任务/小时 | 8 并发持续 |
| 峰值吞吐率 | ≥ 200 任务/小时 | 16 并发 |
| 单任务平均耗时 | < 30s | 300 词文本 |
| 排队等待时间 | < 30s | 并发满时 |
| CPU 利用率 | < 80% | 持续压力下 |
| 内存使用 | < 4GB | 持续压力下 |

### 10.2 测试用例

#### TC-TP-001：单引擎吞吐率基准

| 项目 | 内容 |
|------|------|
| **测试目的** | 测量各引擎在不同并发下的吞吐率（任务/小时） |
| **测试方法** | 分别用 1/4/8/16 并发，持续 30 分钟，统计完成任务数 |
| **测试数据** | 300 词英文文本，f5tts 模型 |
| **预期结果** | 8 并发 ≥ 120 任务/小时，16 并发 ≥ 200 任务/小时 |
| **校验点** | 绘制并发数 vs 吞吐率曲线，找到最优并发数 |

**吞吐率测试脚本**：
```python
def throughput_test(duration_minutes=30, concurrency=8):
    """测量吞吐率（任务/小时）"""
    start_time = time.time()
    end_time = start_time + duration_minutes * 60
    completed = 0
    failed = 0
    latencies = []
    
    def worker():
        nonlocal completed, failed
        while time.time() < end_time:
            t0 = time.time()
            try:
                resp = requests.post(URL, json=PAYLOAD, timeout=120)
                elapsed = time.time() - t0
                if resp.status_code == 200 and resp.json().get("code") == 0:
                    completed += 1
                    latencies.append(elapsed)
                else:
                    failed += 1
            except:
                failed += 1
    
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(worker) for _ in range(concurrency)]
        for f in as_completed(futures):
            f.result()
    
    actual_duration = (time.time() - start_time) / 3600  # 小时
    throughput = completed / actual_duration
    
    return {
        "duration_hours": round(actual_duration, 2),
        "concurrency": concurrency,
        "completed": completed,
        "failed": failed,
        "throughput_per_hour": round(throughput),
        "avg_latency": sum(latencies)/len(latencies) if latencies else 0,
        "p95_latency": sorted(latencies)[int(len(latencies)*0.95)] if latencies else 0,
    }
```

---

#### TC-TP-002：多引擎吞吐率对比

| 项目 | 内容 |
|------|------|
| **测试目的** | 对比 minimax/f5tts/higgs 的吞吐率差异 |
| **测试方法** | 相同条件（8 并发，30 分钟，300 词），分别测试三个引擎 |
| **预期结果** | f5tts/higgs 吞吐率应高于 minimax（本地推理 vs 外部API） |
| **校验点** | 生成吞吐率对比柱状图 |

---

#### TC-TP-003：文本长度对吞吐率的影响

| 项目 | 内容 |
|------|------|
| **测试目的** | 分析文本长度与吞吐率的关系 |
| **测试方法** | 分别用 50/100/300/500/1000 词文本，8 并发各 15 分钟 |
| **预期结果** | 吞吐率与文本长度呈反比，绘制曲线 |
| **校验点** | 找到性价比最优的文本长度范围 |

---

#### TC-TP-004：中英文吞吐率对比

| 项目 | 内容 |
|------|------|
| **测试目的** | 对比中文和英文的吞吐率差异 |
| **测试方法** | 相同字符数（300 字 vs 300 词），8 并发各 15 分钟 |
| **预期结果** | 中文吞吐率可能略低于英文（中文字符信息密度更高） |
| **校验点** | 量化中英文处理效率差异 |

---

#### TC-TP-005：峰值吞吐率压测

| 项目 | 内容 |
|------|------|
| **测试目的** | 找到系统的极限吞吐率 |
| **测试方法** | 并发从 16 逐步增加到 32，观察吞吐率拐点和 503 出现时机 |
| **预期结果** | 峰值吞吐率 ≥ 200 任务/小时，超过 16 并发后出现排队/503 |
| **校验点** | 确定系统瓶颈（CPU/内存/网络/外部API） |

---

### 10.3 吞吐率报告模板

| 引擎 | 并发 | 文本长度 | 时长 | 完成任务 | 失败 | 吞吐率(任务/h) | Avg延迟 | P95延迟 |
|------|:--:|:--:|------|:--:|:--:|:--:|:--:|:--:|
| f5tts | 1 | 300词 | 30min | | | | | |
| f5tts | 4 | 300词 | 30min | | | | | |
| f5tts | 8 | 300词 | 30min | | | | | |
| f5tts | 16 | 300词 | 30min | | | | | |
| minimax | 8 | 300词 | 30min | | | | | |
| higgs | 8 | 300词 | 30min | | | | | |
| f5tts | 8 | 100词 | 15min | | | | | |
| f5tts | 8 | 500词 | 15min | | | | | |
| f5tts | 8 | 300字(ZH) | 15min | | | | | |

---

## 十一、音质评估专项

### 11.1 测试目标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| MOS 主观评分 | ≥ 3.5 / 5 | 人工听感评估 |
| 音频截断率 | 0% | 音频完整无截断 |
| 采样率 | 16000 Hz+ | 不低于电话音质 |
| 底噪水平 | < -50dB | 无明显背景噪音 |
| 音量一致性 | ±3dB | 整段音频音量均匀 |
| 语速自然度 | 偏差 < 10% | 与 speed 参数一致 |

### 11.2 测试用例

#### TC-AQ-001：MOS 主观音质评分

| 项目 | 内容 |
|------|------|
| **测试目的** | 人工评估 Higgs TTS 合成音频的音质 |
| **测试方法** | 随机抽取 20 条合成音频，3 人独立评分（1-5分） |
| **评分标准** | 5=自然流畅无机械感，4=轻微机械感，3=可接受，2=明显机械感，1=不可用 |
| **预期结果** | 平均 MOS ≥ 3.5 |
| **校验点** | 评分一致性（Kappa > 0.6） |

#### TC-AQ-002：音频完整性检查

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证音频无截断、无丢帧 |
| **测试方法** | 1. 对比 audio_length 与实际文件时长<br>2. 检查音频开头和结尾是否完整<br>3. 用 ffprobe 检查音频元数据 |
| **预期结果** | 1. audio_length 与实际时长误差 < 1%<br>2. 无截断<br>3. 编码参数正确 |
| **校验点** | `ffprobe -v quiet -print_format json -show_format audio.mp3` |

#### TC-AQ-003：频谱分析

| 项目 | 内容 |
|------|------|
| **测试目的** | 分析音频频谱，检测异常 |
| **测试方法** | 用 librosa 绘制频谱图，检查频率分布、底噪、削波 |
| **预期结果** | 1. 频率范围覆盖 80Hz-8000Hz<br>2. 无高频削波<br>3. 底噪 < -50dB |
| **校验点** | 生成频谱图对比 |

---

## 十二、语音与文案比对专项

### 12.1 测试目标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 句级准确率 | ≥ 95% | 完整句子正确比例 |
| 语义一致性 | ≥ 98% | 关键信息不丢失 |
| 标点停顿 | 正确率 ≥ 90% | 标点处有明显停顿 |
| 段落停顿 | 正确率 ≥ 95% | `\n\n` 处有明显停顿 |
| 数字朗读 | 正确率 ≥ 95% | 数字按语境正确朗读 |
| 专有名词 | 正确率 ≥ 90% | 人名/地名发音正确 |

### 12.2 测试用例

#### TC-VT-001：逐句文案比对

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证合成音频的每一句都与原文对应 |
| **测试方法** | 1. 用 Whisper 转写音频获取句级时间戳<br>2. 逐句与原文比对<br>3. 标记缺失/多出/替换的句子 |
| **预期结果** | 句级准确率 ≥ 95% |
| **校验点** | 生成句级差异报告 |

#### TC-VT-002：语义完整性验证

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证关键信息（数字、人名、地名）不丢失 |
| **测试方法** | 1. 从原文提取实体（数字/日期/人名/地名）<br>2. 检查转录文本中是否保留<br>3. 人工抽检 10 条验证 |
| **预期结果** | 实体保留率 ≥ 98% |
| **校验点** | 实体提取用正则 + NER 模型 |

#### TC-VT-003：标点停顿验证

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证标点符号处有对应的停顿 |
| **测试方法** | 1. 分析 metadata 时间戳间隔<br>2. 检查 `.` `,` `?` `!` 后的间隔是否 > 平均间隔<br>3. 检查 `\n\n` 段落间是否有明显长停顿 |
| **预期结果** | 句号后停顿 > 300ms，段落间停顿 > 800ms |
| **校验点** | 统计停顿时长分布 |

---

## 十三、中英文测试范围

### 13.1 测试语言覆盖

| 语言 | 代码 | 测试优先级 | 说明 |
|------|------|:--:|------|
| 英文 | en / lang=3 | **P0** | 主要目标语言，全量测试 |
| 中文 | zh / lang=1,2 | **P0** | 主要目标语言，全量测试 |
| 中英混合 | - | P1 | 原文包含中英文混排 |

### 13.2 英文测试范围

| 测试维度 | 覆盖内容 | 用例数 |
|---------|------|:--:|
| 功能 | 短/中/长/多段落文本合成 | 4 |
| 参数 | speed/volume 全边界值 | 6 |
| 性能 | 单请求/并发/吞吐率 | 5 |
| 完整性 | WER/漏词率/句准确率 | 3 |
| 稳定性 | 成功率/重试/长时间 | 4 |
| 异常 | 空文本/超长/特殊字符 | 4 |

### 13.3 中文测试范围

| 测试维度 | 覆盖内容 | 用例数 |
|---------|------|:--:|
| 功能 | 短/中/长/多段落文本合成 | 4 |
| 参数 | speed/volume 全边界值 | 6 |
| 性能 | 单请求/并发/吞吐率 | 5 |
| 完整性 | CER/漏字率/句准确率 | 3 |
| 稳定性 | 成功率/重试/长时间 | 4 |
| 异常 | 空文本/超长/特殊字符(中文标点) | 4 |

### 13.4 中英文测试数据

#### 英文测试文本

```python
ENGLISH_TEXTS = {
    "short_50": "The sun rose over the quiet village, casting golden light across the rooftops. Birds began their morning songs as the world slowly awakened.",
    
    "medium_300": """The old library stood at the end of the cobblestone street, its windows dark and its doors always slightly ajar. No one could remember the last time anyone had gone inside. The townspeople spoke of it in hushed tones, as if the building itself were listening. Sarah had walked past it a hundred times, but today was different. Today, she pushed the door open and stepped inside. The air was thick with dust and the scent of old paper. Shelves lined every wall, filled with books that hadn't been touched in decades.""",
    
    "long_1000": """[1000-word novel excerpt]""",
    
    "multi_para": "Chapter One: The Beginning.\n\nThe journey started on a cold winter morning.\n\nNobody knew what lay ahead.",
    
    "special_chars": "He said: \"Hello—wait...\" She replied, 'Are you OK?' The cost was $19.99 (50% off!). Email: test@example.com",
    
    "numbers": "There are 1,234 items in stock. The temperature is -5.2 degrees. Version 3.14.159 was released on 2024/01/15.",
}
```

#### 中文测试文本

```python
CHINESE_TEXTS = {
    "short_50": "太阳从东方升起，金色的光芒洒满了整个村庄。鸟儿开始在枝头歌唱，新的一天开始了。",
    
    "medium_300": """老街的尽头有一座古老的图书馆，它的窗户总是黑着的，门也总是半掩着。镇上的人们提起它时总是压低了声音，仿佛那栋建筑本身在偷听。小林从这里路过无数次，但今天不同。今天，她推开门走了进去。空气中弥漫着灰尘和旧书的气味。书架从地板延伸到天花板，上面摆满了数十年无人问津的书籍。她随手抽出一本，封面上用烫金的字写着：《时间简史》。""",
    
    "long_1000": """[1000字小说章节]""",
    
    "multi_para": "第一章：开始。\n\n旅程在一个寒冷的冬日早晨开始。\n\n没有人知道前方有什么在等待着他们。",
    
    "special_chars": "他说："你好——等等……"她回答："你还好吗？"价格是￥19.99（五折！）。邮箱：test@example.com",
    
    "numbers": "库存还有1，234件。温度是零下5.2度。版本3.14.159于2024年1月15日发布。",
}
```

### 13.5 中英文差异关注点

| 关注点 | 英文 | 中文 |
|------|------|------|
| 评估指标 | WER（词错误率） | CER（字错误率） |
| 分词方式 | 空格分词 | 逐字对比 |
| 标点符号 | ASCII 标点 | 全角标点（，。！？） |
| 数字读法 | 按英文规则朗读 | 按中文规则朗读 |
| 专有名词 | 首字母大写识别 | 无大小写区分 |
| 多音字 | 无 | 需关注（行/xing vs hang） |
| 语速感知 | speed=1.0 基准 | speed=1.0 基准（可能偏快） |
| 段落停顿 | \n\n 自然停顿 | \n\n 自然停顿 |

### 13.6 中英文测试执行顺序

```
Phase 1: 英文功能测试（28 用例）
Phase 2: 中文功能测试（28 用例）
Phase 3: 英文性能+吞吐率（8 用例）
Phase 4: 中文性能+吞吐率（8 用例）
Phase 5: 英文完整性 WER（6 用例）
Phase 6: 中文完整性 CER（6 用例）
Phase 7: 稳定性（7 用例，中英文混合）
```
