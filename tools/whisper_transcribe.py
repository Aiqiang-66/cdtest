"""
AI Audiobook TTS - 语音转文字（ASR）工具
使用 OpenAI Whisper 模型将音频文件转录为文本
支持：字幕时间戳生成、WER计算、多语言
"""
import whisper
import json
import os
import sys
import time
import argparse
from pathlib import Path

# ============================================================
# 配置
# ============================================================
MODEL_SIZE = "base"  # tiny/base/small/medium/large
MODEL_DIR = os.path.join(os.path.dirname(__file__), "whisper_models")
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "test_audio")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "transcripts")

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def download_model(model_size="base"):
    """下载 Whisper 模型到本地"""
    print(f"[*] 加载模型: {model_size}（首次使用会自动下载 ~{_model_size_mb(model_size)}MB）")
    print(f"[*] 模型缓存目录: {MODEL_DIR}")
    
    # 设置模型下载目录
    os.environ["XDG_CACHE_HOME"] = MODEL_DIR
    
    t0 = time.time()
    model = whisper.load_model(model_size, download_root=MODEL_DIR)
    elapsed = time.time() - t0
    print(f"[OK] 模型加载完成，耗时 {elapsed:.1f}s")
    return model


def _model_size_mb(size):
    """各模型大小参考"""
    sizes = {"tiny": 75, "base": 145, "small": 488, "medium": 1536, "large": 3072}
    return sizes.get(size, "?")


def transcribe_audio(model, audio_path, language=None, task="transcribe"):
    """
    转录音频文件
    
    Args:
        model: whisper 模型实例
        audio_path: 音频文件路径
        language: 语言代码（None=自动检测），如 'en', 'zh', 'ja'
        task: 'transcribe'（转录为同语言）或 'translate'（翻译为英文）
    
    Returns:
        dict: 包含 text, segments, language 等信息
    """
    print(f"\n{'='*60}")
    print(f"[*] 音频文件: {audio_path}")
    print(f"[*] 任务类型: {task}")
    print(f"[*] 指定语言: {language or '自动检测'}")
    
    file_size = os.path.getsize(audio_path) / 1024 / 1024
    print(f"[*] 文件大小: {file_size:.1f} MB")
    
    t0 = time.time()
    
    options = {
        "task": task,
        "verbose": True,
        "word_timestamps": True,  # 词级时间戳
    }
    if language:
        options["language"] = language
    
    result = model.transcribe(audio_path, **options)
    
    elapsed = time.time() - t0
    audio_duration = result.get("duration", 0)
    rtf = elapsed / audio_duration if audio_duration > 0 else 0
    
    print(f"\n[OK] 转录完成！")
    print(f"    音频时长: {audio_duration:.1f}s")
    print(f"    处理耗时: {elapsed:.1f}s")
    print(f"    实时率(RTF): {rtf:.2f}x (越小越快)")
    print(f"    检测语言: {result.get('language', 'unknown')}")
    print(f"    片段数量: {len(result.get('segments', []))}")
    
    return result


def save_results(result, audio_path, output_dir=OUTPUT_DIR):
    """保存转录结果"""
    audio_name = Path(audio_path).stem
    
    # 1. 保存纯文本
    txt_path = os.path.join(output_dir, f"{audio_name}_transcript.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(result["text"])
    print(f"[*] 纯文本已保存: {txt_path}")
    
    # 2. 保存带时间戳的 SRT 字幕
    srt_path = os.path.join(output_dir, f"{audio_name}_subtitle.srt")
    segments = result.get("segments", [])
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            start_ts = _format_timestamp(seg["start"])
            end_ts = _format_timestamp(seg["end"])
            f.write(f"{i}\n{start_ts} --> {end_ts}\n{seg['text'].strip()}\n\n")
    print(f"[*] SRT字幕已保存: {srt_path}")
    
    # 3. 保存完整 JSON（含词级时间戳）
    json_path = os.path.join(output_dir, f"{audio_name}_full.json")
    # 转换 segments 为可序列化格式
    output = {
        "audio_path": audio_path,
        "language": result.get("language"),
        "duration": result.get("duration"),
        "full_text": result["text"],
        "segments": []
    }
    for seg in segments:
        words = []
        for w in seg.get("words", []):
            words.append({
                "word": w["word"],
                "start": round(w["start"], 3),
                "end": round(w["end"], 3),
                "confidence": round(w.get("confidence", 0), 3)
            })
        output["segments"].append({
            "id": seg["id"],
            "start": round(seg["start"], 3),
            "end": round(seg["end"], 3),
            "text": seg["text"].strip(),
            "words": words
        })
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"[*] 完整JSON已保存: {json_path}")
    
    return txt_path, srt_path, json_path


def _format_timestamp(seconds):
    """秒数转 SRT 时间戳格式 HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def calculate_wer(reference_text, hypothesis_text):
    """
    计算词错误率 (Word Error Rate)
    WER = (S + D + I) / N
    """
    try:
        import jiwer
        wer = jiwer.wer(reference_text, hypothesis_text)
        return {"wer": round(wer, 4), "method": "jiwer"}
    except ImportError:
        # 简易实现
        ref_words = reference_text.lower().split()
        hyp_words = hypothesis_text.lower().split()
        
        # Levenshtein 距离
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
        return {"wer": round(wer, 4), "method": "levenshtein", "distance": distance, "ref_words": len(ref_words)}


def compare_with_metadata(whisper_result, metadata_path):
    """
    对比 Whisper 转录结果与 TTS metadata
    
    Args:
        whisper_result: whisper 转录结果
        metadata_path: TTS API 返回的 metadata JSON 文件路径
    
    Returns:
        dict: 对比分析结果
    """
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    
    whisper_text = whisper_result["text"]
    whisper_segments = whisper_result.get("segments", [])
    
    # 拼接 metadata 文本
    meta_text = " ".join(item.get("text", "") for item in metadata)
    
    # 计算 WER
    wer_result = calculate_wer(meta_text, whisper_text)
    
    # 时间戳对比
    meta_duration = metadata[-1]["endMs"] / 1000 if metadata else 0
    whisper_duration = whisper_result.get("duration", 0)
    
    return {
        "wer": wer_result,
        "metadata_duration_ms": meta_duration * 1000,
        "whisper_duration_s": whisper_duration,
        "duration_diff_s": abs(meta_duration - whisper_duration),
        "metadata_segments": len(metadata),
        "whisper_segments": len(whisper_segments),
        "metadata_text_length": len(meta_text),
        "whisper_text_length": len(whisper_text),
    }


# ============================================================
# 主程序
# ============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Whisper 语音转文字工具")
    parser.add_argument("audio", nargs="?", help="音频文件路径")
    parser.add_argument("--model", default="base", choices=["tiny","base","small","medium","large"],
                        help="模型大小 (默认: base)")
    parser.add_argument("--language", default=None, help="语言代码 (如 en/zh/ja，默认自动检测)")
    parser.add_argument("--task", default="transcribe", choices=["transcribe","translate"],
                        help="transcribe=转录同语言, translate=翻译为英文")
    parser.add_argument("--metadata", default=None, help="TTS metadata JSON 路径（用于对比）")
    parser.add_argument("--reference", default=None, help="参考文本（用于计算WER）")
    parser.add_argument("--download-only", action="store_true", help="仅下载模型")
    
    args = parser.parse_args()
    
    # 下载模型
    model = download_model(args.model)
    
    if args.download_only:
        print("[OK] 模型下载完成")
        sys.exit(0)
    
    if not args.audio:
        print("\n用法示例:")
        print("  python whisper_transcribe.py audio.mp3")
        print("  python whisper_transcribe.py audio.mp3 --model small --language en")
        print("  python whisper_transcribe.py audio.mp3 --task translate")
        print("  python whisper_transcribe.py audio.mp3 --metadata metadata.json")
        print("  python whisper_transcribe.py audio.mp3 --reference original.txt")
        print("  python whisper_transcribe.py --download-only --model base")
        sys.exit(0)
    
    # 转录
    result = transcribe_audio(model, args.audio, args.language, args.task)
    
    # 保存结果
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
