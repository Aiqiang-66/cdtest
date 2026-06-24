"""
听书 TTS 长文本功能测试：3000-4000字符 → TTS → Whisper转写 → WER
"""
import json, os, sys, time, requests, urllib3

urllib3.disable_warnings()

URL = "http://ai-audiobook-api-none-new-dev.changdu.ltd/api/tts/synthesize"
OUTPUT_DIR = r"d:\python\dmx\cdtest\tools\test_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# Step 1: 准备 3000-4000 字符英文文本
# ============================================================
print("=" * 60)
print("  Higgs TTS 长文本功能测试 (3000-4000字符)")
print("=" * 60)

# 从物料文件加载长文本
txt_path = r"d:\python\dmx\cdtest\docs\需求文档\听书测试物料\txt文本\8FA4C02F-DE32-4569-908E-DF05A9715BD8.txt"
with open(txt_path, "r", encoding="utf-16") as f:
    full_text = f.read()

# 截取 3000-4000 字符
target_len = 3500
# 找到最近的句子边界
cut_point = full_text.rfind(".", 0, target_len + 500)
if cut_point == -1 or cut_point < 3000:
    cut_point = target_len
else:
    cut_point += 1  # 包含句号

source_text = full_text[:cut_point].strip()
print(f"\n[Step1] 原文: {len(source_text)} 字符, {len(source_text.split())} 词")
print(f"  预览: {source_text[:150]}...")
print(f"  结尾: ...{source_text[-150:]}")

# ============================================================
# Step 2: 调用 Higgs TTS API
# ============================================================
print(f"\n[Step2] 调用 Higgs TTS API...")
t0 = time.time()
resp = requests.post(URL, json={
    "read_content": source_text,
    "chapter_title": "Long Chapter Test",
    "model": "higgs",
    "voice": "audiobook_female_2",
    "lang": 3
}, timeout=600, verify=False)

tts_latency = time.time() - t0
print(f"  HTTP {resp.status_code}, 耗时 {tts_latency:.1f}s")

if resp.status_code != 200:
    print(f"  ❌ 失败: {resp.text}")
    sys.exit(1)

data = resp.json()
if data.get("code") != 0:
    print(f"  ❌ 业务失败: {data}")
    sys.exit(1)

print(f"  ✅ 合成成功!")
print(f"  audio_url: {data['audio_url'][:100]}...")
print(f"  audio_length: {data['audio_length']}ms ({data['audio_length']/1000:.1f}s)")
print(f"  metadata_url: {data.get('metadata_url', 'N/A')[:100]}...")

# ============================================================
# Step 3: 下载音频
# ============================================================
print(f"\n[Step3] 下载音频...")
for attempt in range(5):
    resp2 = requests.get(data["audio_url"], timeout=120, verify=False)
    if resp2.status_code == 200 and len(resp2.content) > 1000:
        break
    print(f"  重试 {attempt+1}/5: HTTP {resp2.status_code}, size={len(resp2.content)}")
    time.sleep(3)

audio_path = os.path.join(OUTPUT_DIR, "long_test_audio.mp3")
with open(audio_path, "wb") as f:
    f.write(resp2.content)
print(f"  ✅ 下载完成: {len(resp2.content)/1024:.1f} KB")

# ============================================================
# Step 4: Whisper 转写
# ============================================================
print(f"\n[Step4] Whisper 转写 (faster-whisper base)...")
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
from faster_whisper import WhisperModel

model = WhisperModel("base", device="cpu", compute_type="int8",
                     download_root=r"d:\python\dmx\cdtest\tools\whisper_models",
                     local_files_only=True)

t0 = time.time()
segments_raw, info = model.transcribe(audio_path, language="en",
                                      beam_size=5, word_timestamps=True,
                                      vad_filter=True)

whisper_parts = []
whisper_segments = []
for seg in segments_raw:
    whisper_parts.append(seg.text.strip())
    whisper_segments.append({
        "start": round(seg.start, 3),
        "end": round(seg.end, 3),
        "text": seg.text.strip()
    })

whisper_latency = time.time() - t0
hypothesis = " ".join(whisper_parts)

print(f"  ✅ 转写完成: {len(whisper_segments)} 片段, 耗时 {whisper_latency:.1f}s")
print(f"  检测语言: {info.language} (置信度: {info.language_probability:.2%})")
print(f"  转录文本预览: {hypothesis[:200]}...")

# ============================================================
# Step 5: 计算 WER + 详细分析
# ============================================================
print(f"\n[Step5] 计算准确率...")

ref_words = source_text.lower().split()
hyp_words = hypothesis.lower().split()

# Levenshtein 距离
m, n = len(ref_words), len(hyp_words)
dp = [[0]*(n+1) for _ in range(m+1)]
for i in range(m+1): dp[i][0] = i
for j in range(n+1): dp[0][j] = j
for i in range(1, m+1):
    for j in range(1, n+1):
        cost = 0 if ref_words[i-1] == hyp_words[j-1] else 1
        dp[i][j] = min(dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+cost)

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

wer = dp[m][n] / max(len(ref_words), 1)

# 句级准确率
ref_sentences = [s.strip() for s in source_text.replace("?", ".").replace("!", ".").split(".") if s.strip()]
hyp_sentences = [s.strip() for s in hypothesis.replace("?", ".").replace("!", ".").split(".") if s.strip()]
sentences_ok = 0
for rs in ref_sentences:
    rs_words = set(rs.lower().split())
    for hs in hyp_sentences:
        hs_words = set(hs.lower().split())
        overlap = len(rs_words & hs_words) / max(len(rs_words), 1)
        if overlap > 0.6:
            sentences_ok += 1
            break
sentence_accuracy = sentences_ok / max(len(ref_sentences), 1) * 100

# ============================================================
# Step 6: 下载并校验 metadata
# ============================================================
print(f"\n[Step6] 校验 metadata...")
meta_ok = False
meta_segments = 0
if data.get("metadata_url"):
    resp3 = requests.get(data["metadata_url"], timeout=30, verify=False)
    if resp3.status_code == 200:
        metadata = resp3.json()
        meta_segments = len(metadata)
        # 校验时间戳
        ts_errors = 0
        for idx, item in enumerate(metadata):
            if item["startMs"] >= item["endMs"]:
                ts_errors += 1
            if idx > 0 and metadata[idx-1]["endMs"] > item["startMs"] + 100:
                ts_errors += 1
        meta_ok = ts_errors == 0
        print(f"  metadata 片段: {meta_segments}, 时间戳错误: {ts_errors}")
        print(f"  音频总时长: {metadata[-1]['endMs']}ms ({metadata[-1]['endMs']/1000:.1f}s)")
    else:
        print(f"  ❌ 下载失败: HTTP {resp3.status_code}")

# ============================================================
# 输出报告
# ============================================================
print(f"\n{'='*60}")
print(f"  📊 测试结果汇总")
print(f"{'='*60}")
print(f"  原文长度: {len(source_text)} 字符, {len(ref_words)} 词")
print(f"  TTS 耗时: {tts_latency:.1f}s")
print(f"  音频时长: {data['audio_length']/1000:.1f}s")
print(f"  RTF: {tts_latency / (data['audio_length']/1000):.2f}x")
print(f"")
print(f"  Whisper 耗时: {whisper_latency:.1f}s")
print(f"  转录词数: {len(hyp_words)}")
print(f"")
print(f"  📈 准确率:")
print(f"  WER (词错误率): {wer*100:.2f}%")
print(f"  准确率: {100-wer*100:.2f}%")
print(f"  删除(漏词): {deletions} ({deletions/len(ref_words)*100:.1f}%)")
print(f"  插入(多词): {insertions} ({insertions/len(ref_words)*100:.1f}%)")
print(f"  替换: {substitutions} ({substitutions/len(ref_words)*100:.1f}%)")
print(f"  句级准确率: {sentence_accuracy:.1f}% ({sentences_ok}/{len(ref_sentences)})")
print(f"")
print(f"  📁 metadata: {meta_segments} 片段, 时间戳 {'✅' if meta_ok else '❌'}")
print(f"{'='*60}")

# 保存报告
report = {
    "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
    "model": "higgs",
    "source_chars": len(source_text),
    "source_words": len(ref_words),
    "tts_latency_s": round(tts_latency, 1),
    "audio_length_ms": data["audio_length"],
    "audio_length_s": data["audio_length"] / 1000,
    "rtf": round(tts_latency / (data["audio_length"]/1000), 2),
    "whisper_latency_s": round(whisper_latency, 1),
    "hypothesis_words": len(hyp_words),
    "wer_percent": round(wer*100, 2),
    "accuracy_percent": round(100-wer*100, 2),
    "deletions": deletions,
    "insertions": insertions,
    "substitutions": substitutions,
    "deletion_rate": round(deletions/len(ref_words)*100, 2),
    "insertion_rate": round(insertions/len(ref_words)*100, 2),
    "substitution_rate": round(substitutions/len(ref_words)*100, 2),
    "sentence_accuracy": round(sentence_accuracy, 1),
    "metadata_segments": meta_segments,
    "metadata_ok": meta_ok,
}

report_path = os.path.join(OUTPUT_DIR, "long_text_report.json")
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"\n报告已保存: {report_path}")
