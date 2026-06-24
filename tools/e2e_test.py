"""
听书 TTS 主流程端到端测试
流程: 原文 → TTS API → 下载音频 → Whisper 转写 → 对比原文(WER) → 对比metadata
"""
import json, os, sys, time, requests, urllib3
from pathlib import Path

urllib3.disable_warnings()

# ============================================================
# 配置
# ============================================================
TTS_URL = os.environ.get("TTS_URL", "http://ai-audiobook-api-none-new-dev.changdu.ltd/api/tts/synthesize")
MATERIAL_DIR = r"d:\python\dmx\cdtest\docs\需求文档\听书测试物料"
OUTPUT_DIR = r"d:\python\dmx\cdtest\tools\test_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# Step 1: 读取原文
# ============================================================
def load_source_text():
    """加载英文测试文本"""
    txt_path = os.path.join(MATERIAL_DIR, "txt文本", "8FA4C02F-DE32-4569-908E-DF05A9715BD8.txt")
    with open(txt_path, "r", encoding="utf-16") as f:
        text = f.read()
    print(f"[Step1] 原文加载: {len(text)} 字符")
    print(f"  预览: {text[:100]}...")
    return text


# ============================================================
# Step 2: 调用 TTS API 合成音频
# ============================================================
def call_tts_api(text, model="f5tts", voice="audiobook_female_2", lang=3):
    """调用 TTS API"""
    payload = {
        "read_content": text,
        "chapter_title": "Test Chapter",
        "model": model,
        "voice": voice,
        "lang": lang
    }
    
    print(f"\n[Step2] 调用 TTS API...")
    print(f"  URL: {TTS_URL}")
    print(f"  model: {model}, voice: {voice}, lang: {lang}")
    print(f"  text length: {len(text)} chars")
    
    t0 = time.time()
    try:
        resp = requests.post(TTS_URL, json=payload, timeout=300, verify=False)
        elapsed = time.time() - t0
        print(f"  HTTP {resp.status_code}, 耗时 {elapsed:.1f}s")
        
        if resp.status_code == 200:
            data = resp.json()
            code = data.get("code", -999)
            if code == 0:
                print(f"  ✅ 合成成功!")
                print(f"  audio_url: {data['audio_url'][:100]}...")
                print(f"  audio_length: {data['audio_length']}ms ({data['audio_length']/1000:.1f}s)")
                print(f"  metadata_url: {data.get('metadata_url', 'N/A')[:100]}...")
                return data
            else:
                print(f"  ❌ 业务失败: code={code}, msg={data.get('msg')}")
                return None
        else:
            print(f"  ❌ HTTP错误: {resp.status_code}")
            print(f"  {resp.text[:300]}")
            return None
    except requests.exceptions.ConnectionError:
        print(f"  ❌ 连接失败! 请确认 TTS 服务是否在 {TTS_URL} 运行")
        return None
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        return None


# ============================================================
# Step 3: 下载音频文件
# ============================================================
def download_audio(audio_url, task_id="test"):
    """下载音频到本地"""
    print(f"\n[Step3] 下载音频...")
    audio_path = os.path.join(OUTPUT_DIR, f"{task_id}.mp3")
    
    t0 = time.time()
    resp = requests.get(audio_url, timeout=120, verify=False)
    elapsed = time.time() - t0
    
    if resp.status_code == 200:
        with open(audio_path, "wb") as f:
            f.write(resp.content)
        size_mb = len(resp.content) / 1024 / 1024
        print(f"  ✅ 下载完成: {size_mb:.1f} MB, 耗时 {elapsed:.1f}s")
        print(f"  路径: {audio_path}")
        return audio_path
    else:
        print(f"  ❌ 下载失败: HTTP {resp.status_code}")
        return None


# ============================================================
# Step 4: Whisper 转写
# ============================================================
def transcribe_with_whisper(audio_path, language="en"):
    """用 Faster-Whisper 转写音频"""
    print(f"\n[Step4] Whisper 转写...")
    
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    from faster_whisper import WhisperModel
    
    model = WhisperModel("base", device="cpu", compute_type="int8",
                         download_root=r"d:\python\dmx\cdtest\tools\whisper_models",
                         local_files_only=True)
    
    t0 = time.time()
    segments_raw, info = model.transcribe(audio_path, language=language,
                                          beam_size=5, word_timestamps=True,
                                          vad_filter=True)
    
    segments = []
    full_text_parts = []
    for seg in segments_raw:
        segments.append({
            "start": round(seg.start, 3),
            "end": round(seg.end, 3),
            "text": seg.text.strip()
        })
        full_text_parts.append(seg.text.strip())
    
    elapsed = time.time() - t0
    full_text = " ".join(full_text_parts)
    
    print(f"  ✅ 转写完成: {len(segments)} 片段, 耗时 {elapsed:.1f}s")
    print(f"  检测语言: {info.language} (置信度: {info.language_probability:.2%})")
    print(f"  转录文本预览: {full_text[:150]}...")
    
    return full_text, segments, info


# ============================================================
# Step 5: 计算 WER
# ============================================================
def calculate_wer(reference, hypothesis):
    """计算词错误率"""
    ref_words = reference.lower().split()
    hyp_words = hypothesis.lower().split()
    
    m, n = len(ref_words), len(hyp_words)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if ref_words[i-1] == hyp_words[j-1] else 1
            dp[i][j] = min(dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + cost)
    
    distance = dp[m][n]
    wer = distance / max(len(ref_words), 1)
    
    # 统计错误类型
    # 回溯找具体错误
    i, j = m, n
    deletions, insertions, substitutions = 0, 0, 0
    while i > 0 or j > 0:
        if i > 0 and j > 0 and ref_words[i-1] == hyp_words[j-1]:
            i -= 1; j -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i-1][j-1] + 1:
            substitutions += 1; i -= 1; j -= 1
        elif i > 0 and dp[i][j] == dp[i-1][j] + 1:
            deletions += 1; i -= 1
        else:
            insertions += 1; j -= 1
    
    return {
        "wer": round(wer, 4),
        "wer_percent": round(wer * 100, 2),
        "distance": distance,
        "ref_words": len(ref_words),
        "hyp_words": len(hyp_words),
        "deletions": deletions,
        "insertions": insertions,
        "substitutions": substitutions
    }


# ============================================================
# Step 6: 对比 metadata 时间戳
# ============================================================
def validate_metadata(original_text, metadata_url):
    """下载并校验 metadata"""
    print(f"\n[Step6] 校验 metadata...")
    
    resp = requests.get(metadata_url, timeout=30, verify=False)
    if resp.status_code != 200:
        print(f"  ❌ 下载失败: HTTP {resp.status_code}")
        return None
    
    metadata = resp.json()
    print(f"  metadata 片段数: {len(metadata)}")
    
    # 校验时间戳单调性
    ts_errors = []
    for i, item in enumerate(metadata):
        if item["startMs"] >= item["endMs"]:
            ts_errors.append(f"Item {i}: startMs >= endMs")
        if i > 0 and metadata[i-1]["endMs"] > item["startMs"] + 100:
            ts_errors.append(f"Overlap at {i}")
    
    # 校验 offset 一致性
    offset_errors = []
    for i, item in enumerate(metadata):
        extracted = original_text[item["startOffset"]:item["endOffset"]]
        if extracted != item["text"]:
            offset_errors.append(f"Item {i}: offset mismatch")
    
    # 拼接 metadata 文本
    meta_text = " ".join(item["text"] for item in metadata)
    
    result = {
        "total_segments": len(metadata),
        "timestamp_errors": len(ts_errors),
        "offset_errors": len(offset_errors),
        "timestamp_ok": len(ts_errors) == 0,
        "offset_ok": len(offset_errors) == 0,
        "meta_text_length": len(meta_text),
        "audio_duration_ms": metadata[-1]["endMs"] if metadata else 0,
    }
    
    if ts_errors:
        print(f"  ⚠️ 时间戳错误: {ts_errors[:3]}")
    else:
        print(f"  ✅ 时间戳单调性: 通过")
    
    if offset_errors:
        print(f"  ⚠️ Offset错误: {offset_errors[:3]}")
    else:
        print(f"  ✅ Offset一致性: 通过")
    
    print(f"  音频总时长: {result['audio_duration_ms']}ms ({result['audio_duration_ms']/1000:.1f}s)")
    
    return result


# ============================================================
# 主流程
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  听书 TTS 主流程端到端测试")
    print("=" * 60)
    
    # Step 1: 加载原文
    source_text = load_source_text()
    
    # Step 2: 调用 TTS API
    tts_result = call_tts_api(source_text)
    if not tts_result:
        print("\n❌ TTS API 调用失败，测试终止")
        print("请确认:")
        print("  1. TTS 服务是否已启动?")
        print(f"  2. 服务地址是否正确? (当前: {TTS_URL})")
        print("  3. 可设置环境变量: set TTS_URL=http://实际地址/api/tts/synthesize")
        sys.exit(1)
    
    # Step 3: 下载音频
    task_id = tts_result.get("audio_url", "test").split("/")[-1].replace(".mp3", "")
    audio_path = download_audio(tts_result["audio_url"], task_id)
    if not audio_path:
        print("\n❌ 音频下载失败")
        sys.exit(1)
    
    # Step 4: Whisper 转写
    whisper_text, whisper_segments, whisper_info = transcribe_with_whisper(audio_path)
    
    # Step 5: 计算 WER
    print(f"\n[Step5] 计算 WER...")
    wer_result = calculate_wer(source_text, whisper_text)
    print(f"  WER: {wer_result['wer_percent']}%")
    print(f"  参考词数: {wer_result['ref_words']}, 转录词数: {wer_result['hyp_words']}")
    print(f"  删除(漏词): {wer_result['deletions']}, 插入(多词): {wer_result['insertions']}, 替换: {wer_result['substitutions']}")
    
    # Step 6: 校验 metadata
    metadata_result = None
    if tts_result.get("metadata_url"):
        metadata_result = validate_metadata(source_text, tts_result["metadata_url"])
    
    # ============================================================
    # 生成报告
    # ============================================================
    report = {
        "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tts_url": TTS_URL,
        "model": "f5tts",
        "voice": "audiobook_female_2",
        "source_text_length": len(source_text),
        "source_text_preview": source_text[:200],
        "tts_result": {
            "audio_url": tts_result["audio_url"],
            "audio_length_ms": tts_result["audio_length"],
            "audio_length_s": tts_result["audio_length"] / 1000,
            "metadata_url": tts_result.get("metadata_url"),
        },
        "whisper": {
            "language": whisper_info.language,
            "language_probability": whisper_info.language_probability,
            "segments": len(whisper_segments),
            "transcribed_text_preview": whisper_text[:200],
        },
        "wer": wer_result,
        "metadata_validation": metadata_result,
        "overall_status": "PASS" if wer_result["wer_percent"] < 10 and (metadata_result is None or metadata_result["timestamp_ok"]) else "WARN"
    }
    
    report_path = os.path.join(OUTPUT_DIR, f"e2e_report_{task_id}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"  测试完成!")
    print(f"  整体状态: {report['overall_status']}")
    print(f"  WER: {wer_result['wer_percent']}%")
    if metadata_result:
        print(f"  时间戳: {'✅' if metadata_result['timestamp_ok'] else '❌'}")
        print(f"  Offset: {'✅' if metadata_result['offset_ok'] else '❌'}")
    print(f"  报告: {report_path}")
    print(f"  音频: {audio_path}")
    print(f"{'='*60}")
