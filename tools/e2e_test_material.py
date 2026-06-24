"""
听书 TTS 主流程端到端测试（使用已有物料）
流程: 原文 → 已有音频 → Whisper 转写 → 对比原文(WER) → 对比已有metadata
"""
import json, os, sys, time, requests, urllib3
from pathlib import Path

urllib3.disable_warnings()

MATERIAL_DIR = r"d:\python\dmx\cdtest\docs\需求文档\听书测试物料"
OUTPUT_DIR = r"d:\python\dmx\cdtest\tools\test_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 已有物料路径
TXT_PATH = os.path.join(MATERIAL_DIR, "txt文本", "8FA4C02F-DE32-4569-908E-DF05A9715BD8.txt")
JSON_PATH = os.path.join(MATERIAL_DIR, "mp3", "23c6a2d3.json")
SRT_PATH = os.path.join(MATERIAL_DIR, "srt文件", "23c6a2d3.srt")

# 从 JSON 中提取 audio_url（metadata 是数组，需要从 TTS API 响应中获取）
# 这里假设 audio_url 需要从 TTS API 获取，或者已有 mp3 文件
# 先检查是否有 mp3 文件
MP3_DIR = os.path.join(MATERIAL_DIR, "mp3")


def find_audio():
    """查找音频文件"""
    # 检查 mp3 目录
    for f in os.listdir(MP3_DIR):
        if f.endswith('.mp3'):
            return os.path.join(MP3_DIR, f)
    
    # 检查 JSON 中是否有 audio_url
    for f in os.listdir(MP3_DIR):
        if f.endswith('.json'):
            with open(os.path.join(MP3_DIR, f), 'r') as fh:
                data = json.load(fh)
            if isinstance(data, dict) and 'audio_url' in data:
                return data['audio_url']
    
    return None


# ============================================================
# Step 1: 加载原文
# ============================================================
print("=" * 60)
print("  听书 TTS 主流程测试（已有物料）")
print("=" * 60)

print(f"\n[Step1] 加载原文...")
with open(TXT_PATH, "r", encoding="utf-16") as f:
    source_text = f.read()
print(f"  原文: {len(source_text)} 字符")
print(f"  预览: {source_text[:120]}...")

# ============================================================
# Step 2: 加载已有 metadata
# ============================================================
print(f"\n[Step2] 加载已有 metadata...")
with open(JSON_PATH, "r") as f:
    metadata = json.load(f)
print(f"  metadata 片段数: {len(metadata)}")
print(f"  音频总时长: {metadata[-1]['endMs']}ms ({metadata[-1]['endMs']/1000:.1f}s)")

# 拼接 metadata 文本
meta_text = " ".join(item["text"] for item in metadata)
print(f"  metadata 文本长度: {len(meta_text)} 字符")

# 校验 metadata 时间戳
ts_errors = []
for i, item in enumerate(metadata):
    if item["startMs"] >= item["endMs"]:
        ts_errors.append(i)
    if i > 0 and metadata[i-1]["endMs"] > item["startMs"] + 100:
        ts_errors.append(i)
print(f"  时间戳错误: {len(ts_errors)} 处" + (" ✅" if len(ts_errors) == 0 else " ❌"))

# 校验 offset
offset_errors = 0
for i, item in enumerate(metadata):
    extracted = source_text[item["startOffset"]:item["endOffset"]]
    if extracted != item["text"]:
        offset_errors += 1
print(f"  Offset错误: {offset_errors} 处" + (" ✅" if offset_errors == 0 else " ❌"))

# ============================================================
# Step 3: 查找/下载音频
# ============================================================
print(f"\n[Step3] 获取音频...")
audio_source = find_audio()

if audio_source is None:
    print("  ⚠️ 未找到本地音频文件，也没有 audio_url")
    print("  将跳过 Whisper 转写步骤")
    audio_path = None
elif audio_source.startswith("http"):
    print(f"  下载音频: {audio_source[:100]}...")
    audio_path = os.path.join(OUTPUT_DIR, "test_audio.mp3")
    resp = requests.get(audio_source, timeout=120, verify=False)
    if resp.status_code == 200:
        with open(audio_path, "wb") as f:
            f.write(resp.content)
        print(f"  ✅ 下载完成: {len(resp.content)/1024/1024:.1f} MB")
    else:
        print(f"  ❌ 下载失败: HTTP {resp.status_code}")
        audio_path = None
else:
    audio_path = audio_source
    print(f"  本地音频: {audio_path}")
    print(f"  大小: {os.path.getsize(audio_path)/1024/1024:.1f} MB")

# ============================================================
# Step 4: Whisper 转写
# ============================================================
if audio_path and os.path.exists(audio_path):
    print(f"\n[Step4] Whisper 转写...")
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    from faster_whisper import WhisperModel
    
    model = WhisperModel("base", device="cpu", compute_type="int8",
                         download_root=r"d:\python\dmx\cdtest\tools\whisper_models",
                         local_files_only=True)
    
    t0 = time.time()
    segments_raw, info = model.transcribe(audio_path, language="en",
                                          beam_size=5, word_timestamps=True,
                                          vad_filter=True)
    
    whisper_segments = []
    whisper_text_parts = []
    for seg in segments_raw:
        whisper_segments.append({
            "start": round(seg.start, 3),
            "end": round(seg.end, 3),
            "text": seg.text.strip()
        })
        whisper_text_parts.append(seg.text.strip())
    
    elapsed = time.time() - t0
    whisper_text = " ".join(whisper_text_parts)
    
    print(f"  ✅ 转写完成: {len(whisper_segments)} 片段, 耗时 {elapsed:.1f}s")
    print(f"  检测语言: {info.language} (置信度: {info.language_probability:.2%})")
    print(f"  转录文本预览: {whisper_text[:150]}...")
else:
    print(f"\n[Step4] 跳过 Whisper 转写（无音频文件）")
    whisper_text = None
    whisper_segments = []

# ============================================================
# Step 5: 计算 WER
# ============================================================
if whisper_text:
    print(f"\n[Step5] 计算 WER...")
    
    ref_words = source_text.lower().split()
    hyp_words = whisper_text.lower().split()
    
    m, n = len(ref_words), len(hyp_words)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1): dp[i][0] = i
    for j in range(n + 1): dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if ref_words[i-1] == hyp_words[j-1] else 1
            dp[i][j] = min(dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + cost)
    
    distance = dp[m][n]
    wer = distance / max(len(ref_words), 1)
    
    # 回溯统计错误类型
    i, j = m, n
    deletions = insertions = substitutions = 0
    while i > 0 or j > 0:
        if i > 0 and j > 0 and ref_words[i-1] == hyp_words[j-1]:
            i -= 1; j -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i-1][j-1] + 1:
            substitutions += 1; i -= 1; j -= 1
        elif i > 0 and dp[i][j] == dp[i-1][j] + 1:
            deletions += 1; i -= 1
        else:
            insertions += 1; j -= 1
    
    print(f"  WER: {wer*100:.2f}%")
    print(f"  参考词数: {len(ref_words)}, 转录词数: {len(hyp_words)}")
    print(f"  删除(漏词): {deletions}, 插入(多词): {insertions}, 替换: {substitutions}")
    print(f"  漏词率: {deletions/len(ref_words)*100:.2f}%")
    print(f"  多词率: {insertions/len(ref_words)*100:.2f}%")
else:
    wer = None
    deletions = insertions = substitutions = 0

# ============================================================
# Step 6: 对比 metadata 时间戳 vs Whisper 时间戳
# ============================================================
if whisper_segments and metadata:
    print(f"\n[Step6] 对比时间戳...")
    meta_duration = metadata[-1]["endMs"] / 1000
    whisper_duration = whisper_segments[-1]["end"]
    diff = abs(meta_duration - whisper_duration)
    print(f"  metadata 时长: {meta_duration:.1f}s")
    print(f"  Whisper 时长: {whisper_duration:.1f}s")
    print(f"  差异: {diff:.1f}s ({diff/meta_duration*100:.1f}%)")

# ============================================================
# 生成报告
# ============================================================
report = {
    "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
    "source_text_length": len(source_text),
    "source_text_preview": source_text[:200],
    "metadata": {
        "segments": len(metadata),
        "duration_ms": metadata[-1]["endMs"],
        "duration_s": metadata[-1]["endMs"] / 1000,
        "timestamp_errors": len(ts_errors),
        "offset_errors": offset_errors,
    },
    "whisper": {
        "segments": len(whisper_segments),
        "duration_s": whisper_segments[-1]["end"] if whisper_segments else 0,
        "transcribed_text_preview": whisper_text[:200] if whisper_text else "",
    } if whisper_text else None,
    "wer": {
        "wer_percent": round(wer * 100, 2) if wer else None,
        "ref_words": len(ref_words) if whisper_text else 0,
        "hyp_words": len(hyp_words) if whisper_text else 0,
        "deletions": deletions,
        "insertions": insertions,
        "substitutions": substitutions,
    } if whisper_text else None,
}

report_path = os.path.join(OUTPUT_DIR, "e2e_report_material.json")
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"\n{'='*60}")
print(f"  测试完成!")
if whisper_text:
    print(f"  WER: {wer*100:.2f}%")
    print(f"  漏词率: {deletions/len(ref_words)*100:.2f}%")
print(f"  metadata 时间戳: {'✅' if len(ts_errors) == 0 else '❌ ' + str(len(ts_errors)) + ' errors'}")
print(f"  metadata Offset: {'✅' if offset_errors == 0 else '❌ ' + str(offset_errors) + ' errors'}")
print(f"  报告: {report_path}")
print(f"{'='*60}")
