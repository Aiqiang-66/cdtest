"""
AI Audiobook TTS - 语音转文字（ASR）工具
使用 Faster-Whisper (CTranslate2) 将音频转录为文本
优势：更快、更省内存、支持 hf-mirror 镜像下载
"""
import json
import os
import sys
import time
import argparse
from pathlib import Path

# ============================================================
# 配置
# ============================================================
MODEL_SIZE = "base"  # tiny/base/small/medium/large-v3
MODEL_DIR = os.path.join(os.path.dirname(__file__), "whisper_models")
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "test_audio")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "transcripts")

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 使用 hf-mirror 镜像（国内加速）
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"


def download_model(model_size="base", device="cpu", compute_type="int8"):
    """下载并加载 Faster-Whisper 模型"""
    from faster_whisper import WhisperModel
    
    model_sizes = {
        "tiny": "tiny",
        "base": "base", 
        "small": "small",
        "medium": "medium",
        "large": "large-v3"
    }
    size_name = model_sizes.get(model_size, model_size)
    
    print(f"[*] 加载模型: {size_name} (device={device}, compute_type={compute_type})")
    print(f"[*] 模型缓存目录: {MODEL_DIR}")
    print(f"[*] 下载源: https://hf-mirror.com")
    
    t0 = time.time()
    model = WhisperModel(
        size_name,
        device=device,
        compute_type=compute_type,
        download_root=MODEL_DIR,
        local_files_only=False
    )
    elapsed = time.time() - t0
    print(f"[OK] 模型加载完成，耗时 {elapsed:.1f}s")
    return model


def transcribe_audio(model, audio_path, language=None, task="transcribe"):
    """
    转录音频文件
    
    Args:
        model: Faster-Whisper 模型实例
        audio_path: 音频文件路径
        language: 语言代码（None=自动检测）
        task: 'transcribe' 或 'translate'
    
    Returns:
        dict: 包含 text, segments, language, duration
    """
    print(f"\n{'='*60}")
    print(f"[*] 音频文件: {audio_path}")
    print(f"[*] 任务类型: {task}")
    print(f"[*] 指定语言: {language or '自动检测'}")
    
    file_size = os.path.getsize(audio_path) / 1024 / 1024
    print(f"[*] 文件大小: {file_size:.1f} MB")
    
    t0 = time.time()
    
    # Faster-Whisper 参数
    segments_raw, info = model.transcribe(
        audio_path,
        language=language,
        task=task,
        beam_size=5,
        word_timestamps=True,
        vad_filter=True,  # 过滤静音
        vad_parameters=dict(
            min_silence_duration_ms=500,
        )
    )
    
    # 收集结果
    segments = []
    full_text_parts = []
    
    for seg in segments_raw:
        words = []
        if seg.words:
            for w in seg.words:
                words.append({
                    "word": w.word,
                    "start": round(w.start, 3),
                    "end": round(w.end, 3),
                    "probability": round(w.probability, 3)
                })
        
        segments.append({
            "id": len(segments),
            "start": round(seg.start, 3),
            "end": round(seg.end, 3),
            "text": seg.text.strip(),
            "words": words,
            "avg_logprob": round(seg.avg_logprob, 3)
        })
        full_text_parts.append(seg.text.strip())
    
    elapsed = time.time() - t0
    audio_duration = info.duration
    rtf = elapsed / audio_duration if audio_duration > 0 else 0
    
    result = {
        "text": " ".join(full_text_parts),
        "segments": segments,
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
        "duration": round(audio_duration, 1),
        "processing_time": round(elapsed, 1),
        "rtf": round(rtf, 2)
    }
    
    print(f"\n[OK] 转录完成！")
    print(f"    音频时长: {audio_duration:.1f}s")
    print(f"    处理耗时: {elapsed:.1f}s")
    print(f"    实时率(RTF): {rtf:.2f}x")
    print(f"    检测语言: {info.language} (置信度: {info.language_probability:.2%})")
    print(f"    片段数量: {len(segments)}")
    
    return result


def save_results(result, audio_path, output_dir=OUTPUT_DIR):
    """保存转录结果"""
    audio_name = Path(audio_path).stem
    
    # 1. 纯文本
    txt_path = os.path.join(output_dir, f"{audio_name}_transcript.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(result["text"])
    print(f"[*] 纯文本: {txt_path}")
    
    # 2. SRT 字幕
    srt_path = os.path.join(output_dir, f"{audio_name}_subtitle.srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(result["segments"], 1):
            start_ts = _format_timestamp(seg["start"])
            end_ts = _format_timestamp(seg["end"])
            f.write(f"{i}\n{start_ts} --> {end_ts}\n{seg['text']}\n\n")
    print(f"[*] SRT字幕: {srt_path}")
    
    # 3. 完整 JSON
    json_path = os.path.join(output_dir, f"{audio_name}_full.json")
    output = {
        "audio_path": audio_path,
        "language": result["language"],
        "language_probability": result["language_probability"],
        "duration": result["duration"],
        "processing_time": result["processing_time"],
        "rtf": result["rtf"],
        "full_text": result["text"],
        "segments": result["segments"]
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"[*] 完整JSON: {json_path}")
    
    return txt_path, srt_path, json_path


def _format_timestamp(seconds):
    """秒数转 SRT 时间戳 HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def calculate_wer(reference_text, hypothesis_text):
    """计算词错误率"""
    try:
        import jiwer
        wer = jiwer.wer(reference_text, hypothesis_text)
        return {"wer": round(wer, 4), "method": "jiwer"}
    except ImportError:
        ref_words = reference_text.lower().split()
        hyp_words = hypothesis_text.lower().split()
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
        return {"wer": round(wer, 4), "method": "levenshtein", "distance": distance}


def compare_with_metadata(whisper_result, metadata_path):
    """对比 Whisper 转录与 TTS metadata"""
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    
    whisper_text = whisper_result["text"]
    meta_text = " ".join(item.get("text", "") for item in metadata)
    wer_result = calculate_wer(meta_text, whisper_text)
    
    meta_duration = metadata[-1]["endMs"] / 1000 if metadata else 0
    whisper_duration = whisper_result.get("duration", 0)
    
    return {
        "wer": wer_result,
        "metadata_duration_ms": meta_duration * 1000,
        "whisper_duration_s": whisper_duration,
        "duration_diff_s": abs(meta_duration - whisper_duration),
        "metadata_segments": len(metadata),
        "whisper_segments": len(whisper_result.get("segments", [])),
    }


# ============================================================
# 主程序
# ============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Faster-Whisper 语音转文字工具")
    parser.add_argument("audio", nargs="?", help="音频文件路径")
    parser.add_argument("--model", default="base", choices=["tiny","base","small","medium","large"],
                        help="模型大小 (默认: base)")
    parser.add_argument("--language", default=None, help="语言代码 (en/zh/ja，默认自动检测)")
    parser.add_argument("--task", default="transcribe", choices=["transcribe","translate"],
                        help="transcribe=转录, translate=翻译为英文")
    parser.add_argument("--device", default="cpu", choices=["cpu","cuda"],
                        help="推理设备 (默认: cpu)")
    parser.add_argument("--compute", default="int8", choices=["int8","float16","float32"],
                        help="计算精度 (默认: int8)")
    parser.add_argument("--metadata", default=None, help="TTS metadata JSON 路径")
    parser.add_argument("--reference", default=None, help="参考文本（计算WER）")
    parser.add_argument("--download-only", action="store_true", help="仅下载模型")
    
    args = parser.parse_args()
    
    # 下载模型
    model = download_model(args.model, args.device, args.compute)
    
    if args.download_only:
        print("[OK] 模型下载完成")
        sys.exit(0)
    
    if not args.audio:
        print("\n用法示例:")
        print("  python whisper_transcribe_fast.py audio.mp3")
        print("  python whisper_transcribe_fast.py audio.mp3 --model small --language en")
        print("  python whisper_transcribe_fast.py audio.mp3 --task translate")
        print("  python whisper_transcribe_fast.py audio.mp3 --metadata metadata.json")
        print("  python whisper_transcribe_fast.py audio.mp3 --reference original.txt")
        print("  python whisper_transcribe_fast.py --download-only --model base")
        sys.exit(0)
    
    # 转录
    result = transcribe_audio(model, args.audio, args.language, args.task)
    
    # 保存
    txt_path, srt_path, json_path = save_results(result, args.audio)
    
    # 对比 metadata
    if args.metadata and os.path.exists(args.metadata):
        print(f"\n{'='*60}")
        print("[*] 对比 TTS Metadata...")
        comparison = compare_with_metadata(result, args.metadata)
        print(json.dumps(comparison, indent=2, ensure_ascii=False))
    
    # 计算 WER
    if args.reference:
        print(f"\n{'='*60}")
        print("[*] 计算 WER...")
        if os.path.exists(args.reference):
            with open(args.reference, "r", encoding="utf-8") as f:
                ref_text = f.read()
        else:
            ref_text = args.reference
        wer_result = calculate_wer(ref_text, result["text"])
        print(f"WER: {wer_result['wer']*100:.2f}%")
        print(f"方法: {wer_result['method']}")
    
    print(f"\n[OK] 全部完成！")
    print(f"    文本: {txt_path}")
    print(f"    字幕: {srt_path}")
    print(f"    详情: {json_path}")
