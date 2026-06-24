import json

# 读取 Whisper 转录结果
with open(r'd:\python\dmx\cdtest\tools\transcripts\39173052_full.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 读取 metadata
with open(r'd:\python\dmx\cdtest\docs\需求文档\听书测试物料\mp3\39173052.json', 'r') as f:
    meta = json.load(f)

# 用 metadata 拼接原文
meta_text = ' '.join(item['text'] for item in meta)
ref_words = meta_text.lower().split()
hyp_words = data['full_text'].lower().split()

# WER
m, n = len(ref_words), len(hyp_words)
dp = [[0]*(n+1) for _ in range(m+1)]
for i in range(m+1): dp[i][0] = i
for j in range(n+1): dp[0][j] = j
for i in range(1, m+1):
    for j in range(1, n+1):
        cost = 0 if ref_words[i-1] == hyp_words[j-1] else 1
        dp[i][j] = min(dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+cost)

# 回溯
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

print('='*50)
print('39173052 音频 Whisper 转写结果')
print('='*50)
print(f"音频时长: {data['duration']}s")
print(f"Whisper耗时: {data['processing_time']}s, RTF: {data['rtf']}x")
print(f"Whisper片段: {len(data['segments'])}")
print(f"metadata片段: {len(meta)}")
print(f"")
print(f"参考词数: {len(ref_words)}")
print(f"转录词数: {len(hyp_words)}")
print(f"WER: {wer*100:.2f}%")
print(f"准确率: {100-wer*100:.2f}%")
print(f"删除(漏词): {dels} ({dels/len(ref_words)*100:.1f}%)")
print(f"插入(多词): {ins} ({ins/len(ref_words)*100:.1f}%)")
print(f"替换: {subs} ({subs/len(ref_words)*100:.1f}%)")
