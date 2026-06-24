import json
from collections import defaultdict

filepath = 'C:/Users/aiqiang/.claude/projects/d--python-dmx-cdtest/73aeee23-c13b-4437-9aae-1ae32b8b319e/tool-results/bzqrgry2q.txt'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

data_start = content.find('data: ')
json_start = data_start + len('data: ')
data_end = content.find('\nevent:', json_start)
if data_end == -1:
    data_end = len(content)
raw_json = content[json_start:data_end].strip()

outer = json.loads(raw_json)
inner_json = outer['result']['content'][0]['text']
cases_data = json.loads(inner_json)
cases = cases_data['cases']

# Group by (module, name)
groups = defaultdict(list)
for c in cases:
    mod = c.get('module', '')
    name = c.get('caseName', '')
    groups[(mod, name)].append(c)

dup_groups = {k: v for k, v in groups.items() if len(v) > 1}

# Sort by dup count desc and take representative samples
sorted_dups = sorted(dup_groups.items(), key=lambda x: -len(x[1]))

# Pick diverse samples: one with 6 copies, one with 5, one with 3, one with 2
samples = []
for (mod, name), dup_cases in sorted_dups:
    n = len(dup_cases)
    if n == 6 and not any(s[2] == 6 for s in samples):
        samples.append((mod, name, dup_cases, 6))
    elif n == 5 and not any(s[2] == 5 for s in samples):
        samples.append((mod, name, dup_cases, 5))
    elif n == 3 and not any(s[2] == 3 for s in samples):
        samples.append((mod, name, dup_cases, 3))
    elif n == 2 and not any(s[2] == 2 for s in samples):
        samples.append((mod, name, dup_cases, 2))
    if len(samples) >= 4:
        break

print("=" * 80)
print("抽查样本：从 479 组重名用例中抽取 4 组典型样本")
print("=" * 80)

for mod, name, dup_cases, n in samples:
    print(f"\n{'='*80}")
    print(f"模块: {mod}")
    print(f"用例名称: {name}")
    print(f"重复次数: {n}")
    print(f"{'='*80}")

    # Print each copy's full details
    for i, c in enumerate(dup_cases, 1):
        print(f"\n--- 副本 {i}/{n} ---")
        print(f"  UUID:       {c.get('id', '?')}")
        print(f"  创建时间:   {c.get('createdAt', '?')}")
        print(f"  更新时间:   {c.get('updatedAt', '?')}")
        print(f"  业务类型:   {c.get('businessType', '?')}")
        print(f"  系统:       {c.get('system', '?')}")
        print(f"  模块:       {c.get('module', '?')}")
        print(f"  测试类型:   {c.get('testType', '?')}")
        print(f"  优先级:     {c.get('priority', '?')}")
        print(f"  需求版本:   {c.get('requirementVersion', '?')}")
        print(f"  前置条件:   {c.get('precondition', '?')}")
        print(f"  测试步骤:   {c.get('testSteps', '?')}")
        print(f"  预期结果:   {c.get('expectedResult', '?')}")
        print(f"  测试数据:   {c.get('testData', '?')}")
        print(f"  验证点:     {c.get('verificationPoint', '?')}")

    # Summary: are they identical?
    uuids = [c.get('id') for c in dup_cases]
    created_times = [c.get('createdAt') for c in dup_cases]
    print(f"\n>>> UUID 对比 (全部不同 = 独立DB记录): {uuids}")
    print(f">>> 创建时间对比: {created_times}")

print(f"\n{'='*80}")
print("结论: 请检查以上样本中，同名用例的各字段是否完全一致")
print("如果是 → 确认为冗余，可以删除")
print("如果否 → 请告诉我差异在哪里，我重新分析")
print("=" * 80)
