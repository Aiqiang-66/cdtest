import json, os
from collections import Counter, defaultdict
from difflib import SequenceMatcher

# Parse MCP response - same as before
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
print(f"Total cases loaded: {len(cases)}")

# Build analysis
name_counts = Counter()
name_to_modules = defaultdict(set)
module_name_counts = defaultdict(list)  # (module, name) -> [cases]

for c in cases:
    name = c.get('caseName', '')
    mod = c.get('module', '')
    name_counts[name] += 1
    name_to_modules[name].add(mod)
    module_name_counts[(mod, name)].append(c)

# Categorize duplicates
# Type 1: Exact same (module, name) - TRUE duplicate within same module
true_dups = {k: v for k, v in module_name_counts.items() if len(v) > 1}
true_dup_count = sum(len(v) - 1 for v in true_dups.values())  # extra copies

# Type 2: Same name across different modules - EXPECTED pattern (e.g., "页面加载" in every module)
cross_module_names = {k for k, v in name_counts.items() if len(name_to_modules[k]) > 1}
cross_module_count = sum(name_counts[k] - 1 for k in cross_module_names)

# Type 3: Same name within same module only (true intra-module dup)
intra_only_dups = {k: v for k, v in true_dups.items() if len(name_to_modules[k[1]]) == 1}

# Build modules dict
modules = defaultdict(list)
for c in cases:
    mod = c.get('module', '未分类')
    modules[mod].append(c)

print(f"\n=== Duplicate Analysis Results ===")
print(f"True intra-module duplicates (same name in same module): {len(true_dups)} duplicate groups, {true_dup_count} extra copies")
print(f"Cross-module shared names (expected): {len(cross_module_names)} names shared across modules")
print(f"Total modules: {len(modules)}")
print(f"Most common names:")
for name, cnt in name_counts.most_common(20):
    mods = name_to_modules[name]
    print(f"  '{name}': {cnt} times across {len(mods)} modules")


# Write detailed dup report
lines = []
lines.append('# 雷霆素材系统 — 用例重复性深度分析')
lines.append('')
lines.append('## 一、重复性分类定义')
lines.append('')
lines.append('| 重复类型 | 定义 | 是否为问题 |')
lines.append('|----------|------|-----------|')
lines.append('| **模块内重名** | 同一模块下存在完全相同的用例名称 | 🔴 需要关注 |')
lines.append('| **跨模块同名** | 不同模块存在相同用例名称（如"页面加载"） | 🟡 通常是合理的通用测试模式 |')
lines.append('| **高相似度** | 不同用例名称相似度 ≥ 85% | 🟠 需人工确认是否为冗余 |')
lines.append('')

lines.append('## 二、核心指标')
lines.append('')
lines.append('| 指标 | 数值 | 说明 |')
lines.append('|------|------|------|')
lines.append(f'| 总用例数 | {len(cases)} | |')
lines.append(f'| 唯一用例名称数 | {len(name_counts)} | |')
lines.append(f'| 跨模块共享的名称数 | {len(cross_module_names)} | 如"页面加载"出现在多个模块 |')
lines.append(f'| 模块内真重名组数 | {len(true_dups)} | 同一模块内名称完全相同的用例组 |')
lines.append(f'| 模块内真重名多余条数 | {true_dup_count} | 除去每组的首条，多余的条数 |')
lines.append(f'| **真实重复率** | **{true_dup_count/len(cases)*100:.1f}%** | 模块内重名多余条数/总条数 |')
lines.append(f'| 跨模块同名率 | {sum(name_counts[n] for n in cross_module_names)/len(cases)*100:.1f}% | 属于共享名称的用例占比 |')
lines.append('')

# Cross-module name distribution
lines.append('## 三、跨模块共享用例名称 Top 30（合理模式）')
lines.append('')
lines.append('| 排名 | 用例名称 | 出现次数 | 跨越模块数 | 示例模块 |')
lines.append('|------|----------|----------|-----------|----------|')
for i, (name, cnt) in enumerate(name_counts.most_common(30), 1):
    mods = sorted(name_to_modules[name])
    mod_examples = '、'.join(mods[:3])
    if len(mods) > 3:
        mod_examples += f' 等{len(mods)}个'
    dup_in_mod = sum(1 for (m, n), v in module_name_counts.items() if n == name and len(v) > 1)
    lines.append(f'| {i} | {name} | {cnt} | {len(mods)} | {mod_examples} |')
lines.append('')

# True duplicates detail
lines.append('## 四、模块内真重名用例明细（需关注）')
lines.append('')
if true_dups:
    # Sort by dup count
    sorted_true_dups = sorted(true_dups.items(), key=lambda x: -len(x[1]))
    lines.append(f'共 **{len(true_dups)}** 组模块内重名，额外重复 **{true_dup_count}** 条')
    lines.append('')
    lines.append('| 序号 | 模块 | 用例名称 | 重复次数 | 额外条数 |')
    lines.append('|------|------|----------|----------|----------|')
    for i, ((mod, name), dup_cases) in enumerate(sorted_true_dups, 1):
        extra = len(dup_cases) - 1
        lines.append(f'| {i} | {mod} | {name} | {len(dup_cases)} | {extra} |')
    lines.append('')

# High near-duplicate pairs
lines.append('## 五、高相似度用例对（相似度 ≥ 85%）')
lines.append('')
all_names = sorted(name_counts.keys())
near_dup_pairs = []
seen = set()
for i, n1 in enumerate(all_names):
    for n2 in all_names[i+1:]:
        if n1 == n2:
            continue
        ratio = SequenceMatcher(None, n1, n2).ratio()
        if ratio >= 0.85:
            pair = (n1, n2) if n1 < n2 else (n2, n1)
            if pair not in seen:
                seen.add(pair)
                near_dup_pairs.append((n1, n2, ratio))

near_dup_sorted = sorted(near_dup_pairs, key=lambda x: -x[2])
lines.append(f'共 **{len(near_dup_sorted)}** 对高相似度用例')
lines.append('')
lines.append('| 序号 | 用例名称 A | 用例名称 B | 相似度 |')
lines.append('|------|-----------|-----------|--------|')
for i, (n1, n2, ratio) in enumerate(near_dup_sorted[:50], 1):
    lines.append(f'| {i} | {n1} | {n2} | {ratio:.0%} |')
lines.append('')

# Summary
lines.append('---')
lines.append('')
lines.append('## 六、总结与建议')
lines.append('')
lines.append(f'1. **真实重复率仅 {true_dup_count/len(cases)*100:.1f}%**（{true_dup_count}条），主要集中在少数模块内')
lines.append(f'2. **跨模块同名是合理设计**：{len(cross_module_names)} 个通用用例名称（如"页面加载""列表查询"）被 {len(modules)} 个模块复用，这是模块化测试策略的正常体现')
lines.append(f'3. **需关注的模块内重名**：{len(true_dups)} 组，建议逐条核实是否为误创建')
if near_dup_sorted:
    top_near = near_dup_sorted[:5]
    lines.append(f'4. **高相似度用例对**：{len(near_dup_sorted)} 对，Top5 为：')
    for n1, n2, r in top_near:
        lines.append(f'   - `{n1}` ↔ `{n2}` ({r:.0%})')

outpath = 'd:/python/dmx/cdtest/雷霆素材系统-用例重复性分析报告.md'
with open(outpath, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print(f'\nDetailed report saved to: {outpath}')
