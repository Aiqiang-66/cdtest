import re
import os
from pydub import AudioSegment

def extract_srt_with_timestamps(srt_path):
    """从SRT文件中提取带时间轴的条目列表"""
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocks = re.split(r'\n\s*\n', content.strip())
    entries = []
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 2:
            continue
        time_line = None
        text_lines = []
        for line in lines:
            line = line.strip()
            if re.match(r'^\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}', line):
                time_line = line
            elif not re.match(r'^\d+$', line) and line:
                text_lines.append(line)
        
        if time_line and text_lines:
            match = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})', time_line)
            if match:
                start_ms = int(match.group(1))*3600000 + int(match.group(2))*60000 + int(match.group(3))*1000 + int(match.group(4))
                end_ms = int(match.group(5))*3600000 + int(match.group(6))*60000 + int(match.group(7))*1000 + int(match.group(8))
                entries.append({
                    'start_ms': start_ms, 'end_ms': end_ms,
                    'start_str': f"{match.group(1)}:{match.group(2)}:{match.group(3)},{match.group(4)}",
                    'end_str': f"{match.group(5)}:{match.group(6)}:{match.group(7)},{match.group(8)}",
                    'text': ' '.join(text_lines)
                })
    return entries

def normalize(text):
    text = re.sub(r'[^\w\s]', ' ', text)
    text = text.lower()
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_report_diff_blocks(report_path):
    """从对比报告中提取每个有差异段落的详细信息"""
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 按段落分割
    blocks = re.split(r'\n(?=--- 段落 )', content)
    
    diff_blocks = []
    for block in blocks:
        if '[~] 有差异' not in block:
            continue
        
        # 提取时间轴
        ts_match = re.search(r'\| (\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})', block)
        if not ts_match:
            continue
        
        start_str = ts_match.group(1)
        end_str = ts_match.group(2)
        
        # 提取翻译文本
        ref_match = re.search(r'【翻译文本】: (.+)', block)
        ref_text = ref_match.group(1).strip() if ref_match else ""
        
        # 提取SRT文本
        srt_match = re.search(r'【SRT文本】  : (.+)', block)
        srt_text = srt_match.group(1).strip() if srt_match else ""
        
        # 提取差异词
        diff_words = []
        for line in block.split('\n'):
            dm = re.match(r'\s*\[(替换|缺少|多余)\]\s*翻译文本=\'([^\']*)\'\s*->\s*SRT=\'([^\']*)\'', line)
            if dm:
                diff_words.append({'type': dm.group(1), 'ref': dm.group(2), 'srt': dm.group(3)})
        
        # 提取准确率
        acc_match = re.search(r'本段准确率: ([\d.-]+)%', block)
        accuracy = float(acc_match.group(1)) if acc_match else 0
        
        diff_blocks.append({
            'start_str': start_str, 'end_str': end_str,
            'ref_text': ref_text, 'srt_text': srt_text,
            'diff_words': diff_words, 'accuracy': accuracy
        })
    
    return diff_blocks

def merge_diff_blocks(blocks, gap_ms=500):
    """合并时间相近的差异段落"""
    if not blocks:
        return []
    
    # 转换为带毫秒的
    for b in blocks:
        h1, m1, s1_ms = b['start_str'].split(':')
        s1, ms1 = s1_ms.split(',')
        b['start_ms'] = int(h1)*3600000 + int(m1)*60000 + int(s1)*1000 + int(ms1)
        
        h2, m2, s2_ms = b['end_str'].split(':')
        s2, ms2 = s2_ms.split(',')
        b['end_ms'] = int(h2)*3600000 + int(m2)*60000 + int(s2)*1000 + int(ms2)
    
    blocks.sort(key=lambda x: x['start_ms'])
    merged = [blocks[0].copy()]
    
    for b in blocks[1:]:
        last = merged[-1]
        if b['start_ms'] - last['end_ms'] <= gap_ms:
            last['end_ms'] = max(last['end_ms'], b['end_ms'])
            last['end_str'] = b['end_str']
            # 合并文本
            if b['ref_text'] and b['ref_text'] != '(无对应)':
                if last['ref_text'] and last['ref_text'] != '(无对应)':
                    last['ref_text'] += ' ' + b['ref_text']
                else:
                    last['ref_text'] = b['ref_text']
            if b['srt_text'] and b['srt_text'] != '(无对应)':
                if last['srt_text'] and last['srt_text'] != '(无对应)':
                    last['srt_text'] += ' ' + b['srt_text']
                else:
                    last['srt_text'] = b['srt_text']
            last['diff_words'].extend(b['diff_words'])
            # 取平均准确率
            last['accuracy'] = (last['accuracy'] + b['accuracy']) / 2
        else:
            merged.append(b.copy())
    
    return merged

def generate_compare_text(block, index, prefix):
    """为单个片段生成对比文本"""
    lines = []
    lines.append("=" * 70)
    lines.append(f"  错误片段对比 #{index:02d}  |  {prefix}")
    lines.append(f"  时间轴: {block['start_str']} --> {block['end_str']}")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"【翻译文本(参考)】")
    lines.append(f"  {block['ref_text']}")
    lines.append("")
    lines.append(f"【SRT文本(ASR识别)】")
    lines.append(f"  {block['srt_text']}")
    lines.append("")
    
    if block['diff_words']:
        lines.append(f"【差异词详情】(共 {len(block['diff_words'])} 处)")
        lines.append("-" * 50)
        lines.append(f"  {'类型':<6} {'翻译文本':<20} {'SRT文本':<20}")
        lines.append("-" * 50)
        for dw in block['diff_words']:
            ref_d = dw['ref'] if dw['ref'] else '(空)'
            srt_d = dw['srt'] if dw['srt'] else '(空)'
            lines.append(f"  {dw['type']:<6} {ref_d:<20} {srt_d:<20}")
    
    lines.append("")
    return '\n'.join(lines)

def process_all(base_path, output_base):
    file_names = ['1', '2', '3', '4']
    report_dir = os.path.join(base_path, '..', '对比报告')
    
    all_summary = []
    
    for name in file_names:
        print(f"\n{'='*60}")
        print(f"处理: {name}")
        print(f"{'='*60}")
        
        mp3_path = os.path.join(base_path, f'{name}.mp3')
        report_path = os.path.join(report_dir, f'{name}_对比报告.txt')
        
        if not os.path.exists(mp3_path):
            print(f"  MP3 not found, skipping")
            continue
        if not os.path.exists(report_path):
            print(f"  Report not found, skipping")
            continue
        
        output_dir = os.path.join(output_base, name)
        os.makedirs(output_dir, exist_ok=True)
        
        # 解析报告
        blocks = parse_report_diff_blocks(report_path)
        print(f"  差异段落: {len(blocks)}")
        
        if not blocks:
            continue
        
        # 合并
        merged = merge_diff_blocks(blocks, gap_ms=500)
        print(f"  合并后: {len(merged)} 个片段")
        
        # 加载音频
        audio = AudioSegment.from_mp3(mp3_path)
        total_ms = len(audio)
        
        # 生成汇总文本
        summary_lines = []
        summary_lines.append(f"【{name}】差异片段汇总")
        summary_lines.append(f"  共 {len(merged)} 个片段")
        summary_lines.append("")
        
        for i, block in enumerate(merged):
            # 截取音频
            start = max(0, block['start_ms'] - 200)
            end = min(total_ms, block['end_ms'] + 200)
            clip = audio[start:end]
            
            start_label = block['start_str'].replace(',', '_').replace(':', '-')
            end_label = block['end_str'].replace(',', '_').replace(':', '-')
            base_filename = f"{name}_{i+1:02d}_{start_label}--{end_label}"
            
            # 导出mp3
            mp3_filename = f"{base_filename}.mp3"
            mp3_filepath = os.path.join(output_dir, mp3_filename)
            clip.export(mp3_filepath, format="mp3", bitrate="128k")
            
            # 生成对比文本
            txt_filename = f"{base_filename}.txt"
            txt_filepath = os.path.join(output_dir, txt_filename)
            txt_content = generate_compare_text(block, i+1, name)
            with open(txt_filepath, 'w', encoding='utf-8') as f:
                f.write(txt_content)
            
            print(f"  [{i+1:02d}] {block['start_str']} --> {block['end_str']}")
            print(f"        mp3: {mp3_filename}")
            print(f"        txt: {txt_filename}")
            
            summary_lines.append(f"  [{i+1:02d}] {block['start_str']} --> {block['end_str']}")
            summary_lines.append(f"        {mp3_filename}")
            summary_lines.append(f"        {txt_filename}")
            summary_lines.append("")
        
        # 写汇总
        summary_path = os.path.join(output_dir, f'{name}_汇总.txt')
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(summary_lines))
        
        all_summary.append(f"{name}: {len(merged)} 个片段")
    
    # 总汇总
    total_path = os.path.join(output_base, '截取汇总.txt')
    with open(total_path, 'w', encoding='utf-8') as f:
        f.write("音频截取汇总\n")
        f.write("=" * 50 + "\n")
        for s in all_summary:
            f.write(f"  {s}\n")
        f.write(f"\n输出目录: {output_base}\n")
    
    print(f"\n{'='*60}")
    print(f"全部完成!")
    print(f"输出目录: {output_base}")

if __name__ == '__main__':
    base_path = r'd:\python\dmx\cdtest\docs\需求文档\听书测试物料\mp3'
    output_base = os.path.join(base_path, '..', '截取音频')
    process_all(base_path, output_base)
