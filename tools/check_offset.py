import json

path = r'd:\python\dmx\cdtest\docs\需求文档\听书测试物料\mp3\23c6a2d3.json'
with open(path) as f:
    meta = json.load(f)

txt_path = r'd:\python\dmx\cdtest\docs\需求文档\听书测试物料\txt文本\8FA4C02F-DE32-4569-908E-DF05A9715BD8.txt'
with open(txt_path, 'r', encoding='utf-16') as f:
    source = f.read()

print("=== Offset 分析 ===")
for i in [0, 1, 2, 10, 50, 100, 125]:
    item = meta[i]
    extracted = source[item['startOffset']:item['endOffset']]
    match = "✅" if extracted == item['text'] else "❌"
    print(f"[{i}] offset=[{item['startOffset']}:{item['endOffset']}] {match}")
    print(f"    extracted: \"{extracted[:80]}\"")
    print(f"    metadata:  \"{item['text'][:80]}\"")

# 检查是否是编码问题导致 offset 计算偏差
print(f"\n=== 编码分析 ===")
print(f"source[0:10] raw: {repr(source[:10])}")
print(f"source[0:10]: '{source[:10]}'")
print(f"meta[0] text: '{meta[0]['text']}'")
print(f"meta[0] offset: [{meta[0]['startOffset']}:{meta[0]['endOffset']}]")
print(f"source[0:9]: '{source[0:9]}'")
print(f"source[0:10]: '{source[0:10]}'")
print(f"source[0:11]: '{source[0:11]}'")
