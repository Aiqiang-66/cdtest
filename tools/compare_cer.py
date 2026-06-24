import json

with open(r'd:\python\dmx\cdtest\tools\transcripts\47928cf8_large_full.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

with open(r'd:\python\dmx\cdtest\docs\需求文档\听书测试物料\mp3\47928cf8.json', 'r', encoding='utf-8') as f:
    meta = json.load(f)

ref_text = ''.join(item['text'].strip() for item in meta)
hyp_text = data['text']

# 字符级 CER
ref_chars = list(ref_text.replace(' ', '').replace(',', '').replace('.', ''))
hyp_chars = list(hyp_text.replace(' ', '').replace(',', '').replace('.', ''))

m, n = len(ref_chars), len(hyp_chars)
dp = [[0]*(n+1) for _ in range(m+1)]
for i in range(m+1): dp[i][0] = i
for j in range(n+1): dp[0][j] = j
for i in range(1, m+1):
    for j in range(1, n+1):
        cost = 0 if ref_chars[i-1] == hyp_chars[j-1] else 1
        dp[i][j] = min(dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+cost)

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
print('Large-v3 vs Base 中文 CER 对比')
print('='*50)
print(f"Large-v3 CER: {cer*100:.2f}% (准确率: {100-cer*100:.2f}%)")
print(f"Base    CER: 29.13% (准确率: 70.87%)")
print(f"提升: {29.13-cer*100:.1f} 个百分点")
print(f"")
print(f"Large 耗时: {data['processing_time']}s (base: 31.6s)")
print(f"Large 片段: {len(data['segments'])} (base: 51)")
print(f"")
print(f"--- Large 转录预览 ---")
print(data['text'][:400])
