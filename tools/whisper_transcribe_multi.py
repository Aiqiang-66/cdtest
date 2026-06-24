"""
AI Audiobook TTS - 语音转文字工具（多后端版）
支持：
  1. Faster-Whisper 本地模型（需先下载）
  2. Google Web Speech API（免费，无需模型）
  3. 生成 SRT 字幕 + 计算 WER
"""
import json, os, sys, time, argparse, tempfile, subprocess
from pathlib import Path

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "transcripts")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# 后端 1: Faster-Whisper（本地模型）
# ============================================================
def transcribe_faster_whisper(audio_path, model_size="base", language=None, task="transcribe"):
    """使用 Faster-Whisper 本地模型转录"""
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    from faster_whisper import WhisperModel
    
    print(f"[*] 加载 Faster-Whisper 模型: {model_size}")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    
    segments_raw, info = model.transcribe(
        audio_path, language=language, task=task,
        beam_size=5, word_timestamps=True, vad_filter=True
    )
    
    segments = []
    full_text = []
    for seg in segments_raw:
        words = []
        if seg.words:
            for w in seg.words:
                words.append({"word": w.word, "start": round(w.start,3), "end": round(w.end,3)})
        segments.append({"id": len(segments), "start": round(seg.start,3), "end": round(seg.end,3), "text": seg.text.strip(), "words": words})
        full_text.append(seg.text.strip())
    
    return {
        "text": " ".join(full_text),
        "segments": segments,
        "language": info.language,
        "duration": round(info.duration, 1),
        "backend": "faster-whisper"
    }


# ============================================================
# 后端 2: Google Web Speech API（免费）
# ============================================================
def transcribe_google(audio_path, language="en-US"):
    """使用 Google Web Speech API 转录（免费，需网络）"""
    import speech_recognition as sr
    from pydub import AudioSegment
    
    print(f"[*] 使用 Google Web Speech API (语言: {language})")
    
    # 转换为 WAV 格式（Google API 要求）
    audio = AudioSegment.from_file(audio_path)
    
    # 如果音频太长（>60s），分段处理
    chunk_length_ms = 30000  # 30 秒一段
    chunks = []
    for i in range(0, len(audio), chunk_length_ms):
        chunks.append(audio[i:i+chunk_length_ms])
    
    print(f"[*] 音频分为 {len(chunks)} 段处理")
    
    recognizer = sr.Recognizer()
    all_segments = []
    time_offset = 0.0
    
    for i, chunk in enumerate(chunks):
        # 导出为临时 WAV
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            chunk.export(tmp.name, format="wav")
            tmp_path = tmp.name
        
        try:
            with sr.AudioFile(tmp_path) as source:
                audio_data = recognizer.record(source)
            
            text = recognizer.recognize_google(audio_data, language=language)
            
            chunk_duration = len(chunk) / 1000.0
            all_segments.append({
                "id": i,
                "start": round(time_offset, 3),
                "end": round(time_offset + chunk_duration, 3),
                "text": text,
                "words": []
            })
            print(f"  段 {i+1}/{len(chunks)}: {text[:80]}...")
            
        except sr.UnknownValueError:
            print(f"  段 {i+1}/{len(chunks)}: [无法识别]")
        except sr.RequestError as e:
            print(f"  段 {i+1}/{len(chunks)}: [API错误: {e}]")
        finally:
            os.unlink(tmp_path)
        
        time_offset += chunk_duration
    
    full_text = " ".join(s["text"] for s in all_segments)
    return {
        "text": full_text,
        "segments": all_segments,
        "language": language,
        "duration": round(len(audio) / 1000.0, 1),
        "backend": "google"
    }


# ============================================================
# 后端 3: OpenAI Whisper API（需 API Key）
# ============================================================
def transcribe_openai_api(audio_path, api_key=None, language=None):
    """使用 OpenAI Whisper API 转录"""
    import requests
    
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("需要 OPENAI_API_KEY")
    
    print(f"[*] 使用 OpenAI Whisper API")
    
    with open(audio_path, "rb") as f:
        resp = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": f},
            data={"model": "whisper-1", "response_format": "verbose_json",
                  "language": language, "timestamp_granularities": ["word"]}
        )
    
    data = resp.json()
    segments = []
    for seg in data.get("segments", []):
        words = [{"word": w["word"], "start": w["start"], "end": w["end"]} for w in seg.get("words", [])]
        segments.append({"id": seg["id"], "start": seg["start"], "end": seg["end"], "text": seg["text"].strip(), "words": words})
    
    return {
        "text": data["text"],
        "segments": segments,
        "language": data.get("language", language),
        "duration": round(data.get("duration", 0), 1),
        "backend": "openai-api"
    }


# ============================================================
# 通用工具函数
# ============================================================
def save_results(result, audio_path, output_dir=OUTPUT_DIR):
    """保存转录结果"""
    audio_name = Path(audio_path).stem
    
    # 纯文本
    txt_path = os.path.join(output_dir, f"{audio_name}_transcript.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(result["text"])
    print(f"[*] 文本: {txt_path}")
    
    # SRT 字幕
    srt_path = os.path.join(output_dir, f"{audio_name}_subtitle.srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(result["segments"], 1):
            start_ts = _format_timestamp(seg["start"])
            end_ts = _format_timestamp(seg["end"])
            f.write(f"{i}\n{start_ts} --> {end_ts}\n{seg['text']}\n\n")
    print(f"[*] 字幕: {srt_path}")
    
    # JSON
    json_path = os.path.join(output_dir, f"{audio_name}_full.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[*] JSON: {json_path}")
    
    return txt_path, srt_path, json_path


def _format_timestamp(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def calculate_wer(reference_text, hypothesis_text):
    """计算词错误率"""
    ref_words = reference_text.lower().split()
    hyp_words = hypothesis_text.lower().split()
    m, n = len(ref_words), len(hyp_words)
    dp = [[0]*(n+1) for _ in range(m+1)]
    for i in range(m+1): dp[i][0] = i
    for j in range(n+1): dp[0][j] = j
    for i in range(1, m+1):
        for j in range(1, n+1):
            cost = 0 if ref_words[i-1] == hyp_words[j-1] else 1
            dp[i][j] = min(dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+cost)
    wer = dp[m][n] / max(len(ref_words), 1)
    return {"wer": round(wer, 4), "distance": dp[m][n], "ref_words": len(ref_words)}


# ============================================================
# 主程序
# ============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="语音转文字工具（多后端）")
    parser.add_argument("audio", nargs="?", help="音频文件路径")
    parser.add_argument("--backend", default="google", choices=["google","whisper","openai"],
                        help="转录后端: google(免费)/whisper(本地)/openai(API)")
    parser.add_argument("--model", default="base", help="Whisper 模型大小")
    parser.add_argument("--language", default="en-US", help="语言代码")
    parser.add_argument("--task", default="transcribe", choices=["transcribe","translate"])
    parser.add_argument("--reference", default=None, help="参考文本（计算WER）")
    parser.add_argument("--api-key", default=None, help="OpenAI API Key")
    
    args = parser.parse_args()
    
    if not args.audio:
        print("用法:")
        print("  python whisper_transcribe_multi.py audio.mp3")
        print("  python whisper_transcribe_multi.py audio.mp3 --backend whisper --model base")
        print("  python whisper_transcribe_multi.py audio.mp3 --backend google --language zh-CN")
        print("  python whisper_transcribe_multi.py audio.mp3 --reference original.txt")
        sys.exit(0)
    
    # 转录
    t0 = time.time()
    
    if args.backend == "google":
        result = transcribe_google(args.audio, args.language)
    elif args.backend == "whisper":
        result = transcribe_faster_whisper(args.audio, args.model, args.language, args.task)
    elif args.backend == "openai":
        result = transcribe_openai_api(args.audio, args.api_key, args.language)
    else:
        print(f"未知后端: {args.backend}")
        sys.exit(1)
    
    elapsed = time.time() - t0
    print(f"\n[OK] 转录完成！耗时 {elapsed:.1f}s, 后端: {result['backend']}")
    print(f"    文本预览: {result['text'][:200]}...")
    
    # 保存
    save_results(result, args.audio)
    
    # WER
    if args.reference:
        if os.path.exists(args.reference):
            with open(args.reference, "r", encoding="utf-8") as f:
                ref_text = f.read()
        else:
            ref_text = args.reference
        wer = calculate_wer(ref_text, result["text"])
        print(f"\n[*] WER: {wer['wer']*100:.2f}% (距离={wer['distance']}, 参考词数={wer['ref_words']})")
