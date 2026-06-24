"""
Whisper转写 + SRT比对测试 v2
策略: 全文整体比对 + 逐句差异定位
1. 用 faster-whisper 转写 mp3 生成识别版 SRT
2. 原始SRT全文 vs Whisper全文 逐词对齐
3. 定位到原始SRT的具体段落，报告差异
"""
import os, sys, time, json, re, argparse
from pathlib import Path
from datetime import datetime
import difflib

MP3_DIR = r"d:\python\dmx\cdtest\docs\需求文档\听书测试物料\mp3"
OUTPUT_DIR = r"d:\python\dmx\cdtest\tools\test_output\srt_compare"
MODEL_DIR = r"d:\python\dmx\cdtest\tools\whisper_models"
MODEL_SIZE = "base"
LANGUAGE = "en"
DEVICE = "cpu"
COMPUTE_TYPE = "int8"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"


def parse_srt(srt_path):
    if not os.path.exists(srt_path):
        return []
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    pattern = re.compile(
        r'(\d+)\s*\n'
        r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\s*\n'
        r'((?:(?!\n\n).)+)',
        re.MULTILINE | re.DOTALL
    )
    segments = []
    for m in pattern.finditer(content):
        segments.append({
            "index": int(m.group(1)),
            "start": m.group(2),
            "end": m.group(3),
            "text": m.group(4).strip().replace('\n', ' ')
        })
    return segments


def normalize_text(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text


def find_diff_regions(orig_text, whisper_text):
    """用 difflib.SequenceMatcher 找出差异区域"""
    matcher = difflib.SequenceMatcher(None, orig_text, whisper_text)
    regions = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != 'equal':
            regions.append({
                "tag": tag,
                "orig_span": orig_text[i1:i2],
                "whisper_span": whisper_text[j1:j2],
                "orig_start": i1,
                "orig_end": i2,
            })
    return regions


def map_diff_to_srt_segments(orig_srt, diff_regions):
    """将差异区域映射到原始 SRT 的具体段落"""
    full_text = ""
    seg_offsets = []
    for seg in orig_srt:
        start = len(full_text)
        full_text += seg["text"] + " "
        end = len(full_text)
        seg_offsets.append((start, end, seg["index"], seg["start"], seg["end"], seg["text"]))
    
    error_segments = {}
    for region in diff_regions:
        r_start = region["orig_start"]
        r_end = region["orig_end"]
        for start, end, seg_idx, seg_start_ts, seg_end_ts, seg_text in seg_offsets:
            if r_start < end and r_end > start:
                if seg_idx not in error_segments:
                    error_segments[seg_idx] = {
                        "orig_index": seg_idx,
                        "orig_timestamp": f"{seg_start_ts} --> {seg_end_ts}",
                        "orig_text": seg_text,
                        "diffs": []
                    }
                overlap_start = max(r_start, start)
                overlap_end = min(r_end, end)
                local_start = overlap_start - start
                local_end = overlap_end - start
                error_segments[seg_idx]["diffs"].append({
                    "tag": region["tag"],
                    "orig_part": seg_text[local_start:local_end].strip(),
                    "whisper_part": region["whisper_span"],
                    "position": f"char {local_start}-{local_end}"
                })
    
    return list(error_segments.values())


def transcribe_with_whisper(model, mp3_path):
    segments_raw, info = model.transcribe(
        mp3_path, language=LANGUAGE, task="transcribe",
        beam_size=5, word_timestamps=True, vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500)
    )
    segments = []
    for seg in segments_raw:
        segments.append({"start": seg.start, "end": seg.end, "text": seg.text.strip()})
    return {"segments": segments, "language": info.language, "duration": info.duration}


def segments_to_srt(segments):
    lines = []
    for i, seg in enumerate(segments, 1):
        h = int(seg["start"] // 3600)
        m = int((seg["start"] % 3600) // 60)
        s = int(seg["start"] % 60)
        ms = int((seg["start"] % 1) * 1000)
        start_ts = f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        h = int(seg["end"] // 3600)
        m = int((seg["end"] % 3600) // 60)
        s = int(seg["end"] % 60)
        ms = int((seg["end"] % 1) * 1000)
        end_ts = f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        lines.append(f"{i}")
        lines.append(f"{start_ts} --> {end_ts}")
        lines.append(seg["text"])
        lines.append("")
    return "\n".join(lines)


def generate_report(results, output_dir, model_size):
    report_lines = []
    report_lines.append(f"# AI Audiobook TTS - Whisper SRT 比对测试报告")
    report_lines.append(f"")
    report_lines.append(f"**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"**Whisper 模型**: {model_size}")
    report_lines.append(f"**测试文件数**: {len(results)}")
    report_lines.append(f"")
    
    total_orig_words = sum(r["orig_word_count"] for r in results)
    total_errors = sum(r["total_errors"] for r in results)
    overall_wer = total_errors / total_orig_words if total_orig_words > 0 else 0
    files_with_errors = sum(1 for r in results if r["error_segments"] > 0)
    
    report_lines.append(f"## 汇总统计")
    report_lines.append(f"")
    report_lines.append(f"| 指标 | 数值 |")
    report_lines.append(f"|------|------|")
    report_lines.append(f"| 测试文件总数 | {len(results)} |")
    report_lines.append(f"| 原始总词数 | {total_orig_words} |")
    report_lines.append(f"| 识别错误总词数 | {total_errors} |")
    report_lines.append(f"| **整体 WER** | **{overall_wer*100:.2f}%** |")
    report_lines.append(f"| **整体准确率** | **{(1-overall_wer)*100:.2f}%** |")
    report_lines.append(f"| 有错误的文件数 | {files_with_errors}/{len(results)} |")
    report_lines.append(f"")
    
    report_lines.append(f"## 逐文件汇总")
    report_lines.append(f"")
    report_lines.append(f"| 文件名 | 原始词数 | 错误词数 | WER | 准确率 | 错误段数/总段数 |")
    report_lines.append(f"|--------|----------|----------|-----|--------|-----------------|")
    for r in results:
        report_lines.append(
            f"| {r['filename']} | {r['orig_word_count']} | {r['total_errors']} | "
            f"{r['wer']*100:.2f}% | {r['accuracy']:.2f}% | "
            f"{r['error_segments']}/{r['total_segments']} |"
        )
    report_lines.append(f"")
    
    report_lines.append(f"## 错误段落详情")
    report_lines.append(f"")
    
    for r in results:
        if r["error_segments"] == 0:
            continue
        report_lines.append(f"### 文件: {r['filename']}")
        report_lines.append(f"")
        report_lines.append(f"- 原始词数: {r['orig_word_count']}, 错误词数: {r['total_errors']}, WER: {r['wer']*100:.2f}%")
        report_lines.append(f"")
        
        for err in r["error_details"]:
            report_lines.append(f"#### 原始SRT段落 {err['orig_index']}")
            report_lines.append(f"")
            report_lines.append(f"**时间戳**: `{err['orig_timestamp']}`")
            report_lines.append(f"")
            report_lines.append(f"**原始SRT文本**:")
            report_lines.append(f"```")
            report_lines.append(err['orig_text'])
            report_lines.append(f"```")
            report_lines.append(f"")
            for d in err["diffs"]:
                tag_label = {"replace": "替换", "delete": "缺失", "insert": "多余"}.get(d["tag"], d["tag"])
                report_lines.append(f"**差异类型**: {tag_label} ({d['position']})")
                report_lines.append(f"")
                report_lines.append(f"- 原始: `{d['orig_part']}`")
                report_lines.append(f"- Whisper识别: `{d['whisper_part']}`")
                report_lines.append(f"")
            report_lines.append(f"---")
            report_lines.append(f"")
    
    report_path = os.path.join(output_dir, f"srt_compare_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    return report_path


def main():
    parser = argparse.ArgumentParser(description="Whisper SRT 比对测试 v2")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--model", default=MODEL_SIZE)
    parser.add_argument("--device", default=DEVICE)
    parser.add_argument("--lang", default="en", help="语言过滤: en/zh/all")
    args = parser.parse_args()
    
    model_size = args.model
    
    mp3_files = []
    for f in sorted(os.listdir(MP3_DIR)):
        if f.endswith(".mp3"):
            base = f[:-4]
            srt_path = os.path.join(MP3_DIR, f"{base}.srt")
            if os.path.exists(srt_path):
                # 语言过滤
                if args.lang != "all":
                    with open(srt_path, "r", encoding="utf-8") as fh:
                        first_line = fh.read(300)
                    has_chinese = any('\u4e00' <= c <= '\u9fff' for c in first_line)
                    if args.lang == "en" and has_chinese:
                        continue
                    if args.lang == "zh" and not has_chinese:
                        continue
                mp3_files.append((base, os.path.join(MP3_DIR, f), srt_path))
    
    if args.limit > 0:
        mp3_files = mp3_files[:args.limit]
    
    print(f"=" * 60)
    print(f"  Whisper SRT 比对测试 v2 (全文对齐)")
    print(f"  模型: {args.model}, 文件数: {len(mp3_files)}")
    print(f"=" * 60)
    
    print(f"\n[*] 加载 Whisper 模型 ({args.model})...")
    from faster_whisper import WhisperModel
    model = WhisperModel(args.model, device=args.device, compute_type=COMPUTE_TYPE,
                         download_root=MODEL_DIR, local_files_only=False)
    print(f"[OK] 模型加载完成")
    
    results = []
    whisper_srt_dir = os.path.join(OUTPUT_DIR, "whisper_srt")
    os.makedirs(whisper_srt_dir, exist_ok=True)
    
    for idx, (base, mp3_path, orig_srt_path) in enumerate(mp3_files):
        print(f"\n{'='*60}")
        print(f"[{idx+1}/{len(mp3_files)}] 处理: {base}")
        
        orig_srt = parse_srt(orig_srt_path)
        orig_full_text = " ".join(seg["text"] for seg in orig_srt)
        orig_words = normalize_text(orig_full_text).split()
        print(f"  原始 SRT: {len(orig_srt)} 段, {len(orig_words)} 词")
        
        t0 = time.time()
        whisper_result = transcribe_with_whisper(model, mp3_path)
        elapsed = time.time() - t0
        whisper_full_text = " ".join(seg["text"] for seg in whisper_result["segments"])
        whisper_words = normalize_text(whisper_full_text).split()
        print(f"  Whisper: {len(whisper_result['segments'])} 段, {len(whisper_words)} 词, 耗时 {elapsed:.1f}s")
        
        whisper_srt_text = segments_to_srt(whisper_result["segments"])
        whisper_srt_path = os.path.join(whisper_srt_dir, f"{base}_whisper.srt")
        with open(whisper_srt_path, "w", encoding="utf-8") as f:
            f.write(whisper_srt_text)
        
        norm_orig = normalize_text(orig_full_text)
        norm_whisper = normalize_text(whisper_full_text)
        diff_regions = find_diff_regions(norm_orig, norm_whisper)
        error_details = map_diff_to_srt_segments(orig_srt, diff_regions)
        
        orig_word_list = norm_orig.split()
        whisper_word_list = norm_whisper.split()
        m, n = len(orig_word_list), len(whisper_word_list)
        dp = [[0]*(n+1) for _ in range(m+1)]
        for i in range(m+1):
            dp[i][0] = i
        for j in range(n+1):
            dp[0][j] = j
        for i in range(1, m+1):
            for j in range(1, n+1):
                cost = 0 if orig_word_list[i-1] == whisper_word_list[j-1] else 1
                dp[i][j] = min(dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+cost)
        
        total_errors = dp[m][n]
        wer = total_errors / m if m > 0 else 0
        
        print(f"  比对: WER={wer*100:.2f}%, 准确率={(1-wer)*100:.2f}%, 错误段={len(error_details)}/{len(orig_srt)}")
        
        results.append({
            "filename": base,
            "orig_word_count": m,
            "whisper_word_count": n,
            "total_errors": total_errors,
            "wer": round(wer, 4),
            "accuracy": round((1-wer)*100, 2),
            "total_segments": len(orig_srt),
            "error_segments": len(error_details),
            "error_details": error_details,
        })
    
    print(f"\n{'='*60}")
    print(f"[*] 生成比对报告...")
    report_path = generate_report(results, OUTPUT_DIR, model_size)
    print(f"[OK] 报告: {report_path}")
    
    json_path = os.path.join(OUTPUT_DIR, f"srt_compare_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"[OK] JSON: {json_path}")
    
    total_orig = sum(r["orig_word_count"] for r in results)
    total_err = sum(r["total_errors"] for r in results)
    overall_wer = total_err / total_orig if total_orig > 0 else 0
    print(f"\n📊 整体 WER: {overall_wer*100:.2f}%, 准确率: {(1-overall_wer)*100:.2f}%")


if __name__ == "__main__":
    main()
