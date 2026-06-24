"""
TTS 音频下载 + Whisper 转写 + 准确率测试
从 TTS API 获取音频，下载到本地，用 Whisper 转写，计算 WER
"""
import json, os, sys, time, requests, urllib3
from pathlib import Path

urllib3.disable_warnings()

URL = "http://ai-audiobook-api-none-new-dev.changdu.ltd/api/tts/synthesize"
OUTPUT_DIR = r"d:\python\dmx\cdtest\tools\test_output\accuracy_test"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 加载原文
txt_path = r"d:\python\dmx\cdtest\docs\需求文档\听书测试物料\txt文本\8FA4C02F-DE32-4569-908E-DF05A9715BD8.txt"
with open(txt_path, "r", encoding="utf-16") as f:
    SOURCE_TEXT = f.read()
# 截取约 3500 字符
cut = SOURCE_TEXT.rfind(".", 0, 3500) + 1
SOURCE_TEXT = SOURCE_TEXT[:cut].strip()

print("=" * 60)
print("  TTS 音频下载 + 准确率测试")
print(f"  原文: {len(SOURCE_TEXT)} 字符, {len(SOURCE_TEXT.split())} 词")
print("=" * 60)

# ============================================================
# Step 1: 调用 TTS API
# ============================================================
print("\n[Step1] 调用 Higgs TTS API...")
t0 = time.time()
resp = requests.post(URL, json={
    "read_content": SOURCE_TEXT,
    "chapter_title": "Accuracy Test",
    "model": "higgs",
    "voice": "audiobook_female_2",
    "lang": 3
}, timeout=600, verify=False)

tts_latency = time.time() - t0
if resp.status_code != 200 or resp.json().get("code") != 0:
    print(f"  ❌ 失败: {resp.text[:300]}")
    sys.exit(1)

data = resp.json()
print(f"  ✅ 合成成功! 耗时 {tts_latency:.1f}s")
print(f"  audio_url: {data['audio_url']}")
print(f"  audio_length: {data['audio_length']}ms ({data['audio_length']/1000:.1f}s)")
print(f"  metadata_url: {data.get('metadata_url', 'N/A')}")

# ============================================================
# Step 2: 下载音频
# ============================================================
print(f"\n[Step2] 下载音频...")
audio_path = os.path.join(OUTPUT_DIR, "tts_audio.mp3")
for attempt in range(5):
    resp2 = requests.get(data["audio_url"], timeout=120, verify=False)
    if resp2.status_code == 200 and len(resp2.content) > 1000:
        break
    print(f"  重试 {attempt+1}/5...")
    time.sleep(3)

with open(audio_path, "wb") as f:
    f.write(resp2.content)
print(f"  ✅ 音频已保存: {audio_path} ({len(resp2.content)/1024:.1f} KB)")

# ============================================================
# Step 3: 下载 metadata
# ============================================================
print(f"\n[Step3] 下载 metadata...")
meta_path = os.path.join(OUTPUT_DIR, "tts_metadata.json")
if data.get("metadata_url"):
    resp3 = requests.get(data["metadata_url"], timeout=30, verify=False)
    if resp3.status_code == 200:
        metadata = resp3.json()
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        print(f"  ✅ metadata 已保存: {meta_path} ({len(metadata)} 片段)")
        
        # 校验时间戳
        ts_errors = 0
        for i, item in enumerate(metadata):
            if item["startMs"] >= item["endMs"]:
                ts_errors += 1
            if i > 0 and metadata[i-1]["endMs"] > item["startMs"] + 100:
                ts_errors += 1
        print(f"  时间戳校验: {'✅ 通过' if ts_errors == 0 else f'❌ {ts_errors} 错误'}")
    else:
        print(f"  ❌ 下载失败: HTTP {resp3.status_code}")

# ============================================================
# Step 4: 保存原文
# ============================================================
source_path = os.path.join(OUTPUT_DIR, "source_text.txt")
with open(source_path, "w", encoding="utf-8") as f:
    f.write(SOURCE_TEXT)
print(f"\n[Step4] 原文已保存: {source_path}")

# ============================================================
# Step 5: Whisper 转写
# ============================================================
print(f"\n[Step5] Whisper 转写...")
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

# 保存转录文本
transcript_path = os.path.join(OUTPUT_DIR, "whisper_transcript.txt")
with open(transcript_path, "w", encoding="utf-8") as f:
    f.write(hypothesis)

# 保存 SRT 字幕
srt_path = os.path.join(OUTPUT_DIR, "whisper_subtitle.srt")
with open(srt_path, "w", encoding="utf-8") as f:
    for i, seg in enumerate(whisper_segments, 1):
        def fmt(sec):
            h = int(sec // 3600); m = int((sec % 3600) // 60)
            s = int(sec % 60); ms = int((sec % 1) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        f.write(f"{i}\n{fmt(seg['start'])} --> {fmt(seg['end'])}\n{seg['text']}\n\n")

print(f"  ✅ 转写完成: {len(whisper_segments)} 片段, 耗时 {whisper_latency:.1f}s")
print(f"  转录文本: {transcript_path}")
print(f"  SRT字幕: {srt_path}")

# ============================================================
# Step 6: 计算 WER
# ============================================================
print(f"\n[Step6] 计算准确率...")

ref_words = SOURCE_TEXT.lower().split()
hyp_words = hypothesis.lower().split()

m, n = len(ref_words), len(hyp_words)
dp = [[0]*(n+1) for _ in range(m+1)]
for i in range(m+1): dp[i][0] = i
for j in range(n+1): dp[0][j] = j
for i in range(1, m+1):
    for j in range(1, n+1):
        cost = 0 if ref_words[i-1] == hyp_words[j-1] else 1
        dp[i][j] = min(dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+cost)

# 回溯统计
i, j = m, n
dels = ins = subs = 0
while i > 0 or j > 0:
    if i > 0 and j > 0 and ref_words[i-1] == hyp_words[j-1]:
        i -= 1; j -= 1
    elif i > 0 and j > 0 and dp[i][j] == dp[i-1][j-1] + 1:
        subs += 1; i -= 1; j -= 1
    elif i > 0 and dp[i][j] == dp[i-1][j] + 1:
        dels += 1; i -= 1
    else:
        ins += 1; j -= 1

wer = dp[m][n] / max(len(ref_words), 1)

# ============================================================
# 生成报告
# ============================================================
report = {
    "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
    "model": "higgs",
    "voice": "audiobook_female_2",
    "source_chars": len(SOURCE_TEXT),
    "source_words": len(ref_words),
    "tts_latency_s": round(tts_latency, 1),
    "audio_length_ms": data["audio_length"],
    "audio_length_s": data["audio_length"] / 1000,
    "rtf": round(tts_latency / (data["audio_length"]/1000), 2),
    "whisper_latency_s": round(whisper_latency, 1),
    "whisper_segments": len(whisper_segments),
    "hypothesis_words": len(hyp_words),
    "wer_percent": round(wer * 100, 2),
    "accuracy_percent": round(100 - wer * 100, 2),
    "deletions": dels,
    "insertions": ins,
    "substitutions": subs,
    "deletion_rate": round(dels / len(ref_words) * 100, 2),
    "insertion_rate": round(ins / len(ref_words) * 100, 2),
    "substitution_rate": round(subs / len(ref_words) * 100, 2),
    "metadata_segments": len(metadata) if 'metadata' in dir() else 0,
    "files": {
        "audio": audio_path,
        "source": source_path,
        "transcript": transcript_path,
        "srt": srt_path,
        "metadata": meta_path if 'meta_path' in dir() else "N/A",
    }
}

report_path = os.path.join(OUTPUT_DIR, "accuracy_report.json")
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"\n{'='*60}")
print(f"  📊 准确率测试结果")
print(f"{'='*60}")
print(f"  原文: {len(SOURCE_TEXT)} 字符, {len(ref_words)} 词")
print(f"  TTS 耗时: {tts_latency:.1f}s, 音频: {data['audio_length']/1000:.1f}s")
print(f"  Whisper 耗时: {whisper_latency:.1f}s")
print(f"")
print(f"  WER: {wer*100:.2f}%")
print(f"  准确率: {100-wer*100:.2f}%")
print(f"  漏词: {dels} ({dels/len(ref_words)*100:.1f}%)")
print(f"  多词: {ins} ({ins/len(ref_words)*100:.1f}%)")
print(f"  替换: {subs} ({subs/len(ref_words)*100:.1f}%)")
print(f"")
print(f"  📁 文件保存在: {OUTPUT_DIR}")
print(f"     {os.path.basename(audio_path)}")
print(f"     {os.path.basename(source_path)}")
print(f"     {os.path.basename(transcript_path)}")
print(f"     {os.path.basename(srt_path)}")
print(f"     {os.path.basename(report_path)}")
print(f"{'='*60}")
