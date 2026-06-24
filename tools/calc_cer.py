import json

# 读取 Whisper 转录
with open(r'd:\python\dmx\cdtest\tools\transcripts\47928cf8_full.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 读取 metadata 作为参考
with open(r'd:\python\dmx\cdtest\docs\需求文档\听书测试物料\mp3\47928cf8.json', 'r', encoding='utf-8') as f:
    meta = json.load(f)

# 拼接参考文本
ref_text = ''.join(item['text'].strip() for item in meta)
hyp_text = data['full_text']

# 中文用字符级 CER
ref_chars = list(ref_text.replace(' ', ''))
hyp_chars = list(hyp_text.replace(' ', ''))

m, n = len(ref_chars), len(hyp_chars)
dp = [[0]*(n+1) for _ in range(m+1)]
for i in range(m+1): dp[i][0] = i
for j in range(n+1): dp[0][j] = j
for i in range(1, m+1):
    for j in range(1, n+1):
        cost = 0 if ref_chars[i-1] == hyp_chars[j-1] else 1
        dp[i][j] = min(dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+cost)

# 回溯
i, j = m, n
dels = ins = subs = 0
while i > 0 or j > 0:
    if i > 0 and j > 0 and ref_chars[i-1] == hyp_chars[j-1]:
        i -= 1; j -= 1
    elif i > 0 and j > 0 and dp[i][j] == dp[i-1][j-1] + 1:
        subs += 1; i -= 1; j -= 1
    elif i > 0 and dp[i][j] == dp[i-1][j] + 1:
        dels += 1; i -= 1
    else:
        ins += 1; j -= 1

cer = dp[m][n] / max(len(ref_chars), 1)

print('='*50)
print('47928cf8 中文音频 Whisper 转写结果')
print('='*50)
print(f"音频时长: {data['duration']}s")
print(f"Whisper耗时: {data['processing_time']}s, RTF: {data['rtf']}x")
print(f"Whisper片段: {len(data['segments'])}")
print(f"metadata片段: {len(meta)}")
print(f"")
print(f"参考字符数: {len(ref_chars)}")
print(f"转录字符数: {len(hyp_chars)}")
print(f"CER (字错误率): {cer*100:.2f}%")
print(f"准确率: {100-cer*100:.2f}%")
print(f"删除(漏字): {dels} ({dels/len(ref_chars)*100:.1f}%)")
print(f"插入(多字): {ins} ({ins/len(ref_chars)*100:.1f}%)")
print(f"替换: {subs} ({subs/len(ref_chars)*100:.1f}%)")
print(f"")
print(f"--- 转录文本预览 ---")
print(hyp_text[:300])
print(f"--- 参考文本预览 ---")
print(ref_text[:300])
