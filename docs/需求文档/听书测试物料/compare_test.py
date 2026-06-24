import re
import os
import json
import difflib

def extract_text_from_srt(srt_path):
    """从SRT文件中提取纯文本内容（去掉时间码和序号）"""
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    lines = content.split('\n')
    text_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if re.match(r'^\d+$', line):
            continue
        if re.match(r'^\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}', line):
            continue
        text_lines.append(line)
    return ' '.join(text_lines)

def extract_srt_with_timestamps(srt_path):
    """从SRT文件中提取带时间轴的条目列表 [(start, end, text), ...]"""
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 按空行分割条目
    blocks = re.split(r'\n\s*\n', content.strip())
    entries = []
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 2:
            continue
        # 跳过序号行，找时间轴行
        time_line = None
        text_lines = []
        for line in lines:
            line = line.strip()
            if re.match(r'^\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}', line):
                time_line = line
            elif not re.match(r'^\d+$', line) and line:
                text_lines.append(line)
        
        if time_line and text_lines:
            match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', time_line)
            if match:
                entries.append({
                    'start': match.group(1),
                    'end': match.group(2),
                    'text': ' '.join(text_lines)
                })
    return entries

def split_sentences(text):
    """将文本按句子分割"""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

def normalize_for_compare(text):
    """标准化文本用于对比"""
    text = re.sub(r'[^\w\s]', ' ', text)
    text = text.lower()
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def find_timestamp_for_text(srt_entries, text_snippet):
    """根据文本片段查找对应的SRT时间轴"""
    text_norm = normalize_for_compare(text_snippet)
    # 找包含该文本的条目
    best_match = None
    best_overlap = 0
    
    for entry in srt_entries:
        entry_norm = normalize_for_compare(entry['text'])
        # 计算文本重叠度
        if text_norm in entry_norm or entry_norm in text_norm:
            return f"{entry['start']} --> {entry['end']}"
        
        # 计算词重叠
        text_words = set(text_norm.split())
        entry_words = set(entry_norm.split())
        overlap = len(text_words & entry_words)
        if overlap > best_overlap:
            best_overlap = overlap
            best_match = entry
    
    if best_match and best_overlap > 0:
        return f"{best_match['start']} --> {best_match['end']}"
    return "(无对应时间轴)"
    text = text.lower()
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def word_error_rate(ref_words, hyp_words):
    """计算WER"""
    n, m = len(ref_words), len(hyp_words)
    if n == 0:
        return {'ref_count': 0, 'hyp_count': m, 'errors': m, 'substitutions': 0, 'deletions': 0, 'insertions': m, 'accuracy': 0, 'differences': []}
    
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref_words[i-1] == hyp_words[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1]) + 1
    
    i, j = n, m
    alignments = []
    while i > 0 or j > 0:
        if i > 0 and j > 0 and ref_words[i-1] == hyp_words[j-1]:
            alignments.append(('C', ref_words[i-1], hyp_words[j-1]))
            i -= 1; j -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i-1][j-1] + 1:
            alignments.append(('S', ref_words[i-1], hyp_words[j-1]))
            i -= 1; j -= 1
        elif i > 0 and dp[i][j] == dp[i-1][j] + 1:
            alignments.append(('D', ref_words[i-1], ''))
            i -= 1
        else:
            alignments.append(('I', '', hyp_words[j-1]))
            j -= 1
    alignments.reverse()
    
    errors = dp[n][m]
    accuracy = ((n - errors) / n * 100) if n > 0 else 100
    
    diffs = []
    for idx, (op, ref, hyp) in enumerate(alignments):
        if op != 'C':
            diffs.append({'op': op, 'ref': ref, 'hyp': hyp})
    
    return {
        'ref_count': n, 'hyp_count': m, 'errors': errors,
        'substitutions': sum(1 for a in alignments if a[0] == 'S'),
        'deletions': sum(1 for a in alignments if a[0] == 'D'),
        'insertions': sum(1 for a in alignments if a[0] == 'I'),
        'accuracy': round(accuracy, 2), 'differences': diffs
    }

def generate_single_report(name, srt_text, ref_text, srt_entries, output_dir):
    """为单个文件生成逐段对比报告（含SRT时间轴）"""
    srt_sentences = split_sentences(srt_text)
    ref_sentences = split_sentences(ref_text)
    
    # 整体WER
    srt_norm = normalize_for_compare(srt_text)
    ref_norm = normalize_for_compare(ref_text)
    overall_result = word_error_rate(ref_norm.split(), srt_norm.split())
    
    lines = []
    lines.append("=" * 80)
    lines.append(f"  逐段对比报告: {name}")
    lines.append(f"  SRT(ASR识别) vs 翻译文本(人工参考)")
    lines.append("=" * 80)
    lines.append("")
    lines.append("【整体统计】")
    lines.append(f"  翻译文本词数: {overall_result['ref_count']}")
    lines.append(f"  SRT词数:      {overall_result['hyp_count']}")
    lines.append(f"  错误总数:     {overall_result['errors']}")
    lines.append(f"  替换: {overall_result['substitutions']}  删除: {overall_result['deletions']}  插入: {overall_result['insertions']}")
    lines.append(f"  词准确率:     {overall_result['accuracy']}%")
    lines.append(f"  WER:          {round(100 - overall_result['accuracy'], 2)}%")
    lines.append("")
    
    matcher = difflib.SequenceMatcher(None, ref_sentences, srt_sentences)
    
    lines.append("=" * 80)
    lines.append("  逐段对比详情")
    lines.append("=" * 80)
    lines.append("")
    lines.append("图例: [=] 一致  [~] 有差异  [+] 仅翻译文本有  [-] 仅SRT有")
    lines.append("")
    
    seq_num = 0
    diff_count = 0
    total_segments = 0
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for k in range(i1, i2):
                total_segments += 1
                seq_num += 1
                srt_s = srt_sentences[j1 + k - i1]
                ts = find_timestamp_for_text(srt_entries, srt_s)
                lines.append(f"--- 段落 {seq_num} [=] 一致 | {ts} ---")
                lines.append(f"  翻译文本: {ref_sentences[k][:200]}")
                lines.append(f"  SRT文本:   {srt_s[:200]}")
                lines.append("")
        
        elif tag == 'replace':
            for k in range(max(i2 - i1, j2 - j1)):
                total_segments += 1
                seq_num += 1
                diff_count += 1
                ref_s = ref_sentences[i1 + k] if i1 + k < i2 else "(无对应)"
                srt_s = srt_sentences[j1 + k] if j1 + k < j2 else "(无对应)"
                
                ts = find_timestamp_for_text(srt_entries, srt_s) if srt_s != "(无对应)" else "(无对应时间轴)"
                
                ref_n = normalize_for_compare(ref_s)
                srt_n = normalize_for_compare(srt_s)
                sent_result = word_error_rate(ref_n.split(), srt_n.split()) if ref_n else {'accuracy': 0, 'errors': 0, 'differences': []}
                
                lines.append(f"--- 段落 {seq_num} [~] 有差异 | {ts} | 本段准确率: {sent_result['accuracy']}% ---")
                lines.append(f"  【翻译文本】: {ref_s}")
                lines.append(f"  【SRT文本】  : {srt_s}")
                if sent_result['differences']:
                    lines.append(f"  差异词:")
                    for d in sent_result['differences']:
                        op_label = {'S': '替换', 'D': '缺少', 'I': '多余'}[d['op']]
                        lines.append(f"    [{op_label}] 翻译文本='{d['ref']}' -> SRT='{d['hyp']}'")
                lines.append("")
        
        elif tag == 'delete':
            for k in range(i1, i2):
                total_segments += 1
                seq_num += 1
                diff_count += 1
                lines.append(f"--- 段落 {seq_num} [+] 仅翻译文本有 | (无对应时间轴) ---")
                lines.append(f"  【翻译文本】: {ref_sentences[k]}")
                lines.append(f"  【SRT文本】  : (缺失)")
                lines.append("")
        
        elif tag == 'insert':
            for k in range(j1, j2):
                total_segments += 1
                seq_num += 1
                diff_count += 1
                srt_s = srt_sentences[k]
                ts = find_timestamp_for_text(srt_entries, srt_s)
                lines.append(f"--- 段落 {seq_num} [-] 仅SRT有 | {ts} ---")
                lines.append(f"  【翻译文本】: (缺失)")
                lines.append(f"  【SRT文本】  : {srt_s}")
                lines.append("")
    
    lines.append("=" * 80)
    lines.append(f"  汇总: 共 {total_segments} 段, 一致 {total_segments - diff_count} 段, 有差异 {diff_count} 段")
    lines.append(f"  整体词准确率: {overall_result['accuracy']}%")
    lines.append("=" * 80)
    
    report_path = os.path.join(output_dir, f'{name}_对比报告.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    return report_path, overall_result

def generate_summary(all_results, output_dir):
    """生成汇总报告"""
    lines = []
    lines.append("=" * 80)
    lines.append("  汇总报告: SRT(ASR识别) vs 翻译文本(参考)")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"{'文件名':<15} {'参考词数':<10} {'SRT词数':<10} {'错误':<8} {'替换':<6} {'删除':<6} {'插入':<6} {'准确率':<10}")
    lines.append("-" * 75)
    
    total_errors = 0
    total_words = 0
    total_accuracy = 0
    valid_count = 0
    
    for name, result in all_results.items():
        lines.append(f"{name:<15} {result['ref_count']:<10} {result['hyp_count']:<10} {result['errors']:<8} {result['substitutions']:<6} {result['deletions']:<6} {result['insertions']:<6} {result['accuracy']:<10.2f}%")
        total_errors += result['errors']
        total_words += result['ref_count']
        total_accuracy += result['accuracy']
        valid_count += 1
    
    lines.append("-" * 75)
    if valid_count > 0:
        avg_accuracy = total_accuracy / valid_count
        overall_wer = (total_errors / total_words * 100) if total_words > 0 else 0
        lines.append(f"{'【汇总】':<15} {total_words:<10} {'':<10} {total_errors:<8} {'':<6} {'':<6} {'':<6} {avg_accuracy:<10.2f}%")
        lines.append("")
        lines.append(f"  文件数量: {valid_count}")
        lines.append(f"  平均词准确率: {avg_accuracy:.2f}%")
        lines.append(f"  总体WER: {overall_wer:.2f}%")
    lines.append("=" * 80)
    
    summary_path = os.path.join(output_dir, '汇总报告.txt')
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return summary_path

if __name__ == '__main__':
    base_path = r'd:\python\dmx\cdtest\docs\需求文档\听书测试物料\mp3'
    output_dir = os.path.join(base_path, '..', '对比报告')
    os.makedirs(output_dir, exist_ok=True)
    
    file_names = ['1', '2', '3', '4']
    
    all_results = {}
    
    for name in file_names:
        srt_path = os.path.join(base_path, f'{name}.srt')
        ref_path = os.path.join(base_path, f'{name}.翻译文本.srt')
        
        if not os.path.exists(srt_path):
            print(f"[{name}] SRT not found, skipping")
            continue
        if not os.path.exists(ref_path):
            print(f"[{name}] 翻译文本 not found, skipping")
            continue
        
        srt_text = extract_text_from_srt(srt_path)
        srt_entries = extract_srt_with_timestamps(srt_path)
        with open(ref_path, 'r', encoding='utf-8') as f:
            ref_text = f.read()
        
        report_path, result = generate_single_report(name, srt_text, ref_text, srt_entries, output_dir)
        all_results[name] = result
        print(f"[{name}] 报告已生成: {report_path}")
        print(f"        准确率: {result['accuracy']}%, 差异词: {len(result['differences'])}处")
    
    summary_path = generate_summary(all_results, output_dir)
    print(f"\n汇总报告: {summary_path}")
    print(f"所有报告保存在: {output_dir}")
