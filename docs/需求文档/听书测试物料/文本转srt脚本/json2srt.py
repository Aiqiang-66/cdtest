"""将 TTS metadata JSON 转换为 SRT 字幕文件。

用法:
    # 单个文件转换
    python json2srt.py <json_path> [srt_path]

    # 批量转换文件夹内所有 JSON（排除 _manifest.json）
    python json2srt.py --batch <folder_path>

    json_path: metadata JSON 文件路径（必填）
    srt_path:  输出 SRT 文件路径（可选，默认替换扩展名为 .srt）
"""

import json
import sys
import os
import glob


def ms_to_srt_time(ms: int) -> str:
    """毫秒 → SRT 时间格式 HH:MM:SS,mmm"""
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    ms_remain = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms_remain:03d}"


def json_to_srt(json_path: str, srt_path: str | None = None) -> str:
    """读取 metadata JSON，写入 SRT 文件，返回输出路径。"""
    if not os.path.isfile(json_path):
        raise FileNotFoundError(f"JSON 文件不存在: {json_path}")

    if srt_path is None:
        srt_path = os.path.splitext(json_path)[0] + ".srt"

    with open(json_path, "r", encoding="utf-8") as f:
        segments = json.load(f)

    lines = []
    for seg in segments:
        idx = seg.get("id", 0) + 1
        start = ms_to_srt_time(seg["startMs"])
        end = ms_to_srt_time(seg["endMs"])
        text = seg.get("text", "").strip()

        if not text:
            continue

        lines.append(f"{idx}")
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")  # 空行分隔

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"✓ 已生成 SRT: {srt_path}  ({len([l for l in lines if l and l[0].isdigit()])} 条字幕)")
    return srt_path


def batch_convert(folder_path: str) -> None:
    """批量转换文件夹内所有 JSON 文件（排除 _manifest.json）。"""
    if not os.path.isdir(folder_path):
        raise NotADirectoryError(f"文件夹不存在: {folder_path}")

    json_files = glob.glob(os.path.join(folder_path, "*.json"))
    # 排除 _manifest.json
    json_files = [f for f in json_files if os.path.basename(f) != "_manifest.json"]

    if not json_files:
        print("未找到可转换的 JSON 文件。")
        return

    print(f"找到 {len(json_files)} 个 JSON 文件，开始批量转换...\n")
    success = 0
    for jf in sorted(json_files):
        try:
            srt_path = os.path.splitext(jf)[0] + ".srt"
            json_to_srt(jf, srt_path)
            success += 1
        except Exception as e:
            print(f"✗ 转换失败: {jf}  - {e}")

    print(f"\n批量转换完成: {success}/{len(json_files)} 成功")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--batch":
        if len(sys.argv) < 3:
            print("用法: python json2srt.py --batch <folder_path>")
            sys.exit(1)
        batch_convert(sys.argv[2])
    else:
        json_file = r"C:\Users\weizhikai\Downloads\23c6a2d3.json"
        srt_file = r"C:\Users\weizhikai\Downloads\23c6a2d3.srt"
        json_to_srt(json_file, srt_file)
