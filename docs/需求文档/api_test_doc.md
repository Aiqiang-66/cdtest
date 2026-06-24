# AI Audiobook API 接口测试文档

## 1. 接口概述

| 项目 | 说明 |
|------|------|
| **接口路径** | `POST /api/tts/synthesize` |
| **接口功能** | 将文本合成为语音，上传至腾讯云 COS 并返回可访问的音频 URL |
| **Content-Type** | `application/json` |
| **认证方式** | 无 |
域名：http://ai-audiobook-api-none-new-dev.changdu.ltd
### 1.1 支持的 TTS 引擎

| model 值 | 引擎 | 音频格式 | 是否支持 metadata | 备注 |
|----------|------|---------|------------------|------|
| `minimax` | MiniMax TTS | MP3 | ✅ 支持 | 支持 speed/volume 参数 会消耗金额 |
| `elevenlabs` | ElevenLabs | MP3 | ❌ 不支持（metadata_url 为空） | 支持 speed 参数 目前不支持该模型！ |
| `f5tts` | F5 TTS (Triton) | WAV → 转码为 MP3 | ✅ 支持（流式模式） | speed/volume 会被忽略 主要测试目标 |
| `higgs` | Higgs TTS v3 | WAV → 转码为 MP3 | ✅ 支持 | speed/volume 会被忽略  主要测试目标 |

### 1.2 并发控制

- **最大并发数**：16（通过环境变量 `TTS_MAX_CONCURRENT` 配置）
- **排队超时**：30 秒
- **超时后行为**：返回 HTTP 503，提示"并发已达上限，请稍后重试..."

---

## 2. 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 约束 | 说明 |
|--------|------|------|--------|------|------|
| `read_content` | string | **是** | - | - | 需要朗读的文本内容（段落以 `\n` 分隔） |
| `chapter_title` | string | **是** | - | - | 章节标题（会拼接到音频开头） |
| `voice` | string | **是** | - | - | 音色名称或 ID（各引擎格式不同） |
| `model` | string | 否 | `"minimax"` | 枚举：`minimax` / `elevenlabs` / `f5tts` / `higgs` | TTS 引擎选择 |
| `lang` | int | 否 | `3` | - | 语言 ID：1/2=中文，3=英文，4-17=其他语言 |
| `speed` | float | 否 | `1.0` | [0.5, 2.0] | 语速（minimax/elevenlabs 生效，f5tts/higgs 忽略） |
| `volume` | float | 否 | `1.0` | [0.1, 10.0] | 音量（仅 minimax 生效，f5tts/higgs 忽略） |
| `cos_path` | string \| null | 否 | `null` | - | 自定义 COS 对象路径（不含扩展名），不传则自动生成 |

### 2.1 voice 参数说明（按引擎）

| 引擎 | voice 格式 | 示例 |
|------|-----------|------|
| minimax | MiniMax 平台的 voice_id | 需联系管理员获取 |
| elevenlabs | ElevenLabs 平台的 voice_id | 需联系管理员获取 |
| f5tts | 预配置的音色名称（从 `F5_VOICE_REF_AUDIO_MAP` 查找） | `"audiobook_female_2"` |
| higgs | 已注册的 voice_id，或预配置的音色名称（走克隆模式） | `"audiobook_female_2"` 或注册的 voice_id |

---

## 3. 响应格式

### 3.1 成功响应（HTTP 200）

```json
{
  "code": 0,
  "msg": "success",
  "audio_url": "https://reader-audio-1382266829.cos.ap-hongkong.myqcloud.com/audiobook/{task_id}.mp3",
  "audio_length": 12345,
  "metadata_url": "https://reader-audio-cn-1382266829.cos.ap-guangzhou.myqcloud.com/audiobook/{task_id}.json"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | int | `0` = 成功 |
| `msg` | string | `"success"` |
| `audio_url` | string | 音频文件的香港 CDN 公开访问 URL（MP3 格式） |
| `audio_length` | int | 音频时长，单位**毫秒** |
| `metadata_url` | string | 时间戳对齐 JSON 文件的广州 COS URL（elevenlabs 模型下为空字符串） |

### 3.2 失败响应（HTTP 200，业务失败）

```json
{
  "code": -1,
  "msg": "<错误描述>",
  "audio_url": "",
  "audio_length": 0,
  "metadata_url": ""
}
```

> **注意**：TTS 合成过程中的异常不会抛出 HTTP 错误状态码，而是返回 HTTP 200 但 `code: -1`。失败后会 sleep 60 秒再返回，以抑制调用方的快速重试。

### 3.3 参数校验失败（HTTP 422）

FastAPI 自动校验，返回标准 Pydantic 校验错误格式：

```json
{
  "detail": [
    {
      "loc": ["body", "read_content"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 3.4 不支持的模型（HTTP 400）

```json
{
  "detail": "不支持的模型: <model值>"
}
```

### 3.5 并发超限（HTTP 503）

```json
{
  "detail": "并发已达上线，请稍后重试..."
}
```

### 3.6 metadata JSON 格式

metadata_url 指向的 JSON 文件内容格式（minimax/f5tts/higgs 模型）：

```json
[
  {
    "id": 0,
    "startMs": 0,
    "endMs": 2450,
    "paraIndex": 0,
    "startOffset": 0,
    "endOffset": 65,
    "text": "A sharp, tearing sensation"
  }
]
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 片段序号，从 0 开始 |
| `startMs` | int | 片段开始时间，毫秒 |
| `endMs` | int | 片段结束时间，毫秒 |
| `paraIndex` | int | 所属段落索引 |
| `startOffset` | int | 在原始文本中的起始字符位置 |
| `endOffset` | int | 在原始文本中的结束字符位置 |
| `text` | string | 该片段对应的文本内容 |

---

## 4. 测试用例

### 4.1 正常功能测试

#### TC-N-001：MiniMax 模型基本合成

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 MiniMax 模型能正常合成音频并返回完整响应 |
| **前置条件** | 服务正常运行，MiniMax API 可用 |
| **请求体** | `{"read_content": "Hello world. This is a test.", "chapter_title": "Chapter 1", "model": "minimax", "lang": 3, "voice": "<有效voice_id>", "speed": 1.0, "volume": 1.0}` |
| **预期结果** | HTTP 200；`code`=0；`audio_url` 非空且以 `.mp3` 结尾；`audio_length` > 0；`metadata_url` 非空且以 `.json` 结尾 |
| **校验点** | 1. `audio_url` 可访问下载<br>2. `audio_length` 与下载音频实际时长一致<br>3. `metadata_url` 返回有效 JSON，数组非空 |

---

#### TC-N-002：ElevenLabs 模型基本合成

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 ElevenLabs 模型能正常合成音频 |
| **前置条件** | 服务正常运行，ElevenLabs API 可用 |
| **请求体** | `{"read_content": "Hello world. This is a test.", "chapter_title": "Chapter 1", "model": "elevenlabs", "lang": 3, "voice": "<有效voice_id>", "speed": 1.0}` |
| **预期结果** | HTTP 200；`code`=0；`audio_url` 非空；`audio_length` > 0；`metadata_url` 为空字符串 `""` |
| **校验点** | 1. `metadata_url` 必须为空（ElevenLabs 不支持时间戳）<br>2. `audio_url` 可访问下载 |

---

#### TC-N-003：F5 TTS 模型基本合成

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 F5 TTS 模型流式模式正常合成音频 |
| **前置条件** | 服务正常运行，Triton 推理服务可用 |
| **请求体** | `{"read_content": "Hello world. This is a test.", "chapter_title": "Chapter 1", "model": "f5tts", "lang": 3, "voice": "audiobook_female_2", "speed": 1.0, "volume": 1.0}` |
| **预期结果** | HTTP 200；`code`=0；`audio_url` 非空；`audio_length` > 0；`metadata_url` 非空 |
| **校验点** | 1. speed/volume 被忽略不影响合成结果<br>2. metadata JSON 时间戳与音频对齐 |

---

#### TC-N-004：Higgs TTS 模型基本合成

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 Higgs TTS 模型正常合成音频 |
| **前置条件** | 服务正常运行，Higgs TTS v3 服务可用 |
| **请求体** | `{"read_content": "Hello world. This is a test.", "chapter_title": "Chapter 1", "model": "higgs", "lang": 3, "voice": "audiobook_female_2", "speed": 1.0, "volume": 1.0}` |
| **预期结果** | HTTP 200；`code`=0；`audio_url` 非空；`audio_length` > 0；`metadata_url` 非空 |
| **校验点** | 1. speed/volume 被忽略不影响合成结果<br>2. metadata JSON 格式正确 |

---

#### TC-N-005：自定义 cos_path

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证传入自定义 cos_path 时，音频 URL 使用指定路径 |
| **前置条件** | 服务正常运行 |
| **请求体** | `{"read_content": "Test content.", "chapter_title": "Title", "model": "minimax", "lang": 3, "voice": "<有效voice_id>", "cos_path": "custom/path/my-audio"}` |
| **预期结果** | HTTP 200；`code`=0；`audio_url` 包含 `custom/path/my-audio.mp3` |
| **校验点** | `audio_url` 路径与传入 `cos_path` 一致 |

---

#### TC-N-006：中文内容合成

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证中文文本能正常合成 |
| **前置条件** | 对应 TTS 引擎支持中文 |
| **请求体** | `{"read_content": "你好，这是一段测试文本。", "chapter_title": "第一章", "model": "minimax", "lang": 1, "voice": "<有效voice_id>"}` |
| **预期结果** | HTTP 200；`code`=0；`audio_url` 非空 |
| **校验点** | 音频可正常播放，朗读内容为中文 |

---

#### TC-N-007：多段落文本合成

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证多段落文本（以 `\n` 分隔）能正确处理 |
| **前置条件** | 服务正常运行 |
| **请求体** | `{"read_content": "Paragraph one.\n\nParagraph two.\n\nParagraph three.", "chapter_title": "Multi Para", "model": "minimax", "lang": 3, "voice": "<有效voice_id>"}` |
| **预期结果** | HTTP 200；`code`=0；metadata JSON 中 `paraIndex` 覆盖 0/1/2 多个段落 |
| **校验点** | metadata 中各段落的时间戳均存在 |

---

### 4.2 参数校验测试

#### TC-V-001：缺失必填字段 read_content

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证缺少 `read_content` 时返回 422 |
| **请求体** | `{"chapter_title": "Title", "voice": "test"}` |
| **预期结果** | HTTP 422；`detail` 中包含 `read_content` 缺失的错误信息 |

---

#### TC-V-002：缺失必填字段 chapter_title

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证缺少 `chapter_title` 时返回 422 |
| **请求体** | `{"read_content": "Test", "voice": "test"}` |
| **预期结果** | HTTP 422；`detail` 中包含 `chapter_title` 缺失的错误信息 |

---

#### TC-V-003：缺失必填字段 voice

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证缺少 `voice` 时返回 422 |
| **请求体** | `{"read_content": "Test", "chapter_title": "Title"}` |
| **预期结果** | HTTP 422；`detail` 中包含 `voice` 缺失的错误信息 |

---

#### TC-V-004：非法的 model 值

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证传入不支持的 model 值返回 400 |
| **请求体** | `{"read_content": "Test", "chapter_title": "Title", "voice": "test", "model": "invalid_model"}` |
| **预期结果** | HTTP 400；`detail` 为 `"不支持的模型: invalid_model"` |

---

#### TC-V-005：speed 超出上限

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 speed > 2.0 时返回 422 |
| **请求体** | `{"read_content": "Test", "chapter_title": "Title", "voice": "test", "speed": 2.1}` |
| **预期结果** | HTTP 422；`detail` 中包含 speed 超出范围的校验错误 |

---

#### TC-V-006：speed 低于下限

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 speed < 0.5 时返回 422 |
| **请求体** | `{"read_content": "Test", "chapter_title": "Title", "voice": "test", "speed": 0.4}` |
| **预期结果** | HTTP 422；`detail` 中包含 speed 超出范围的校验错误 |

---

#### TC-V-007：speed 边界值 0.5（合法）

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 speed=0.5 为合法值，请求正常处理 |
| **请求体** | `{"read_content": "Test", "chapter_title": "Title", "model": "minimax", "voice": "<有效voice_id>", "speed": 0.5}` |
| **预期结果** | HTTP 200；`code`=0 |

---

#### TC-V-008：speed 边界值 2.0（合法）

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 speed=2.0 为合法值，请求正常处理 |
| **请求体** | `{"read_content": "Test", "chapter_title": "Title", "model": "minimax", "voice": "<有效voice_id>", "speed": 2.0}` |
| **预期结果** | HTTP 200；`code`=0 |

---

#### TC-V-009：volume 超出上限

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 volume > 10.0 时返回 422 |
| **请求体** | `{"read_content": "Test", "chapter_title": "Title", "voice": "test", "volume": 10.1}` |
| **预期结果** | HTTP 422；`detail` 中包含 volume 超出范围的校验错误 |

---

#### TC-V-010：volume 低于下限

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 volume < 0.1 时返回 422 |
| **请求体** | `{"read_content": "Test", "chapter_title": "Title", "voice": "test", "volume": 0.09}` |
| **预期结果** | HTTP 422；`detail` 中包含 volume 超出范围的校验错误 |

---

#### TC-V-011：volume 边界值 0.1（合法）

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 volume=0.1 为合法值 |
| **请求体** | `{"read_content": "Test", "chapter_title": "Title", "model": "minimax", "voice": "<有效voice_id>", "volume": 0.1}` |
| **预期结果** | HTTP 200；`code`=0 |

---

#### TC-V-012：volume 边界值 10.0（合法）

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 volume=10.0 为合法值 |
| **请求体** | `{"read_content": "Test", "chapter_title": "Title", "model": "minimax", "voice": "<有效voice_id>", "volume": 10.0}` |
| **预期结果** | HTTP 200；`code`=0 |

---

#### TC-V-013：空请求体

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证发送空 JSON 对象时返回 422 |
| **请求体** | `{}` |
| **预期结果** | HTTP 422；`detail` 中包含 read_content、chapter_title、voice 三个字段缺失的错误 |

---

#### TC-V-014：字段类型错误

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 speed 传入字符串类型时返回 422 |
| **请求体** | `{"read_content": "Test", "chapter_title": "Title", "voice": "test", "speed": "fast"}` |
| **预期结果** | HTTP 422；`detail` 中包含类型错误的校验信息 |

---

### 4.3 并发控制测试

#### TC-C-001：未超并发上限的正常请求

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证在并发上限内（≤16）请求正常处理 |
| **前置条件** | 服务正常运行 |
| **测试方法** | 同时发送 10 个 TTS 合成请求 |
| **预期结果** | 所有请求均返回 HTTP 200，`code`=0 |
| **校验点** | 无请求返回 503 |

---

#### TC-C-002：超出并发上限返回 503

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证超过最大并发数的请求在 30 秒排队超时后返回 503 |
| **前置条件** | 已占用 16 个并发槽位（可通过大量耗时请求占满） |
| **测试方法** | 先发送 16 个处理耗时较长的请求（如超长文本），待槽位占满后，再发送第 17 个请求 |
| **预期结果** | 第 17 个请求在 ~30 秒后返回 HTTP 503，`detail` 为 `"并发已达上线，请稍后重试..."` |
| **校验点** | 1. 前 16 个请求正常处理<br>2. 第 17 个请求返回 503（非 200 也非超时） |

---

#### TC-C-003：请求完成释放槽位后新请求可进入

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证请求完成后释放信号量，后续请求可以获取槽位 |
| **前置条件** | 占用满 16 个并发槽位 |
| **测试方法** | 1. 占满 16 个槽位<br>2. 等待其中一个请求完成<br>3. 立即发送新请求 |
| **预期结果** | 新请求能正常获取槽位并返回成功 |
| **校验点** | 新请求不返回 503，正常完成合成 |

---

### 4.4 异常场景测试

#### TC-E-001：read_content 为空字符串

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证空文本内容的行为 |
| **请求体** | `{"read_content": "", "chapter_title": "Title", "model": "minimax", "voice": "<有效voice_id>"}` |
| **预期结果** | 取决于 MiniMax API 对空内容的处理：可能返回成功（仅标题被朗读）或返回 `code: -1` |
| **校验点** | 服务不崩溃，返回格式符合规范 |

---

#### TC-E-002：read_content 超长文本

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证超长文本（如 >10000 字符）的处理行为 |
| **请求体** | `{"read_content": "<10000+字符的英文小说文本>", "chapter_title": "Long Chapter", "model": "minimax", "voice": "<有效voice_id>"}` |
| **预期结果** | 取决于 TTS 引擎的文本长度限制：可能成功或返回 `code: -1` |
| **校验点** | 1. 服务不崩溃不超时<br>2. 超限时有明确的错误信息<br>3. 不导致其他并发请求受影响 |

---

#### TC-E-003：F5 TTS 传入不存在的 voice 名称

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 F5 TTS 使用不存在的音色名称时返回业务失败 |
| **请求体** | `{"read_content": "Test content.", "chapter_title": "Title", "model": "f5tts", "voice": "nonexistent_voice", "lang": 3}` |
| **预期结果** | HTTP 200；`code`=-1；`msg` 包含 `"音色不存在"` |
| **校验点** | 返回明确的错误提示，而非服务崩溃 |

---

#### TC-E-004：包含特殊字符的文本

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证包含特殊字符（引号、破折号、省略号、emoji）的文本能正常处理 |
| **请求体** | `{"read_content": "He said: \"Hello—wait...\" 😊 She replied, 'Are you OK?'", "chapter_title": "Special Chars", "model": "minimax", "voice": "<有效voice_id>", "lang": 3}` |
| **预期结果** | HTTP 200；`code`=0，或 `code`=-1 但有明确错误信息 |
| **校验点** | 服务不崩溃，特殊字符不导致响应格式异常 |

---

#### TC-E-005：仅包含换行符的 read_content

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证纯换行符（无实际文本）的处理 |
| **请求体** | `{"read_content": "\n\n\n", "chapter_title": "Title", "model": "minimax", "voice": "<有效voice_id>"}` |
| **预期结果** | 取决于引擎，可能返回成功（仅标题被朗读）或返回 `code: -1` |
| **校验点** | 服务不崩溃 |

---

#### TC-E-006：不传 model 字段（使用默认值）

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证不传 model 时默认使用 minimax |
| **请求体** | `{"read_content": "Test.", "chapter_title": "Title", "voice": "<有效voice_id>"}` |
| **预期结果** | HTTP 200；`code`=0（使用 minimax 处理） |
| **校验点** | 功能正常，等同于 model="minimax" |

---

#### TC-E-007：不传 lang 字段（使用默认值）

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证不传 lang 时默认使用 3（英文） |
| **请求体** | `{"read_content": "Hello.", "chapter_title": "Title", "model": "minimax", "voice": "<有效voice_id>"}` |
| **预期结果** | HTTP 200；`code`=0 |
| **校验点** | 音频朗读语言为英文 |

---

#### TC-E-008：cos_path 为 null

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 cos_path 传 null 时使用默认路径 |
| **请求体** | `{"read_content": "Test.", "chapter_title": "Title", "model": "minimax", "voice": "<有效voice_id>", "cos_path": null}` |
| **预期结果** | HTTP 200；`code`=0；`audio_url` 路径为 `audiobook/{task_id}.mp3` |
| **校验点** | 路径格式正确 |

---

#### TC-E-009：Content-Type 不是 application/json

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证发送非 JSON 格式请求时的行为 |
| **请求体** | `Content-Type: text/plain`，请求体为纯文本 |
| **预期结果** | HTTP 422 或 HTTP 415 |
| **校验点** | 返回合理的错误提示 |

---

### 4.5 响应校验测试

#### TC-R-001：成功响应结构完整性

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证成功响应的 JSON 结构包含所有必需字段 |
| **请求体** | 正常请求 |
| **预期结果** | HTTP 200；JSON 包含 `code`, `msg`, `audio_url`, `audio_length`, `metadata_url` 五个字段 |
| **校验点** | 1. 无多余字段<br>2. 无缺失字段<br>3. 各字段类型正确 |

---

#### TC-R-002：audio_url 格式校验

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 audio_url 的格式 |
| **条件** | 使用默认 cos_path |
| **预期结果** | `audio_url` 格式为 `https://reader-audio-1382266829.cos.ap-hongkong.myqcloud.com/audiobook/{8位hex}.mp3` |
| **校验点** | 1. 域名为香港 CDN<br>2. 文件扩展名为 `.mp3`<br>3. 路径以 `audiobook/` 开头 |

---

#### TC-R-003：audio_length 合理性校验

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 audio_length 与文本长度基本成正比 |
| **请求体** | 分别发送 10 词、50 词、200 词的文本 |
| **预期结果** | `audio_length` 随文本长度增加而增大，且所有值 > 0 |
| **校验点** | `audio_length(50词)` > `audio_length(10词)` |

---

#### TC-R-004：metadata_url 引擎差异校验

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证不同引擎的 metadata_url 行为 |
| **测试方法** | 分别用 minimax、elevenlabs、f5tts、higgs 发送相同请求 |
| **预期结果** | minimax/f5tts/higgs：`metadata_url` 非空字符串；elevenlabs：`metadata_url` 为空字符串 `""` |
| **校验点** | elevenlabs 不会返回 metadata URL |

---

#### TC-R-005：metadata JSON 结构校验（minimax）

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 metadata JSON 的结构和字段完整性 |
| **前置条件** | 使用 minimax 模型成功合成 |
| **测试方法** | 下载 metadata_url 指向的 JSON 文件 |
| **预期结果** | JSON 为数组，每个元素包含 `id`, `startMs`, `endMs`, `paraIndex`, `startOffset`, `endOffset`, `text`；`startMs` < `endMs`；`text` 非空 |
| **校验点** | 1. 数组非空<br>2. 各字段类型正确<br>3. 时间戳递增且无重叠 |

---

#### TC-R-006：metadata JSON 结构校验（f5tts/higgs）

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 f5tts/higgs 模型的 metadata 结构 |
| **前置条件** | 使用 f5tts 或 higgs 模型成功合成 |
| **测试方法** | 下载 metadata_url 指向的 JSON 文件 |
| **预期结果** | 结构与 minimax 相同，格式为 `[{"id": ..., "startMs": ..., ...}]` |
| **校验点** | 字段结构与 minimax 一致 |

---

#### TC-R-007：失败响应结构完整性

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证业务失败时响应的 JSON 结构 |
| **条件** | 触发业务失败（如非法 voice 导致 F5 TTS 失败） |
| **预期结果** | HTTP 200；`code`=-1；`msg` 非空错误描述；`audio_url`=""；`audio_length`=0；`metadata_url`="" |
| **校验点** | 1. 失败时不返回部分结果<br>2. `code`=-1 而非 0<br>3. audio_length 为 0 而非 null |

---

#### TC-R-008：audio_url 可访问性

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证返回的 audio_url 确实可以下载音频文件 |
| **前置条件** | 合成成功（`code`=0） |
| **测试方法** | 对 `audio_url` 发起 HTTP GET 请求 |
| **预期结果** | HTTP 200 或 206；Content-Type 为 `audio/mpeg` 或 `audio/mp3`；文件大小 > 0 |
| **校验点** | 文件可完整下载 |

---

## 5. 测试数据参考

### 5.1 voice 参数参考值

| 引擎 | 测试用 voice 值 | 说明 |
|------|----------------|------|
| minimax | 联系管理员获取 | MiniMax 平台的 voice_id |
| elevenlabs | 联系管理员获取 | ElevenLabs 平台的 voice_id |
| f5tts | `audiobook_female_2` | 预配置的音色名称 |
| higgs | `audiobook_female_2` | 预配置的音色名称（克隆模式） |

### 5.2 测试文本模板

**短文本**（< 100 字符）：
```
The sun rose over the quiet village, casting golden light across the rooftops.
```

**中等文本**（~300 字符）：
```
The old library stood at the end of the cobblestone street, its windows dark and its doors always slightly ajar. No one could remember the last time anyone had gone inside. The townspeople spoke of it in hushed tones, as if the building itself were listening. Sarah had walked past it a hundred times, but today was different. Today, she pushed the door open and stepped inside.
```

**多段落文本**（用于测试段落分隔）：
```
Paragraph one with some content.\n\nParagraph two with different content.\n\nParagraph three with more content.
```

---

## 6. 附录

### 6.1 测试环境信息

| 配置项 | 值 |
|--------|-----|
| 服务端口 | 80 |
| 最大并发数 | 16（`TTS_MAX_CONCURRENT`） |
| 线程池大小 | 16（`TTS_THREAD_POOL_SIZE`） |
| 并发排队超时 | 30 秒 |
| 失败后冷却时间 | 60 秒 |
| 音频输出目录 | `/data/audiobook/` |

### 6.2 常见错误码速查

| HTTP 状态码 | code | 场景 |
|-------------|------|------|
| 200 | 0 | 合成成功 |
| 200 | -1 | 合成失败（TTS 引擎异常） |
| 400 | - | 不支持的 model 参数 |
| 422 | - | 请求参数校验失败 |
| 503 | - | 并发超限 |
