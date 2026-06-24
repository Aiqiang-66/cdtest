import json, re
from collections import Counter, defaultdict
from difflib import SequenceMatcher

# 1. Parse MCP response
filepath = 'C:/Users/aiqiang/.claude/projects/d--python-dmx-cdtest/73aeee23-c13b-4437-9aae-1ae32b8b319e/tool-results/bzqrgry2q.txt'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Parse SSE format
# Find "data: " marker and extract until next "event:" or end of string
data_start = content.find('data: ')
if data_start == -1:
    raise ValueError("No 'data: ' found in MCP response")

# Find the JSON start after "data: "
json_start = data_start + len('data: ')
data_end = content.find('\nevent:', json_start)
if data_end == -1:
    data_end = len(content)
raw_json = content[json_start:data_end].strip()

# Parse outer JSON-RPC response
outer = json.loads(raw_json)
# Extract inner cases JSON from the text field
inner_json = outer['result']['content'][0]['text']
cases_data = json.loads(inner_json)
cases = cases_data['cases']
print(f"Total cases loaded: {len(cases)}")

# 2. Build analysis data structures
modules = defaultdict(list)
name_counts = Counter()
name_to_cases = defaultdict(list)

for c in cases:
    mod = c.get('module', '未分类')
    modules[mod].append(c)
    name = c.get('caseName', '')
    name_counts[name] += 1
    name_to_cases[name].append(c)

# 3. Duplicate analysis

# 3a. Exact name duplicates
exact_dup_names = {k: v for k, v in name_counts.items() if v > 1}
exact_dup_cases_count = sum(v for v in exact_dup_names.values())

# 3b. Near-duplicate names (similarity >= 0.85)
all_names = sorted(name_counts.keys())
near_dup_pairs = []
seen_pairs = set()
for i, n1 in enumerate(all_names):
    for n2 in all_names[i+1:]:
        if n1 == n2:
            continue
        ratio = SequenceMatcher(None, n1, n2).ratio()
        if ratio >= 0.85 and ratio < 1.0:
            pair_key = (n1, n2) if n1 < n2 else (n2, n1)
            if pair_key not in seen_pairs:
                seen_pairs.add(pair_key)
                near_dup_pairs.append((n1, n2, ratio))

# 3c. Same module + same name prefix duplicates (common in the data)
module_name_dups = defaultdict(list)
for c in cases:
    mod = c.get('module', '')
    name = c.get('caseName', '')
    key = (mod, name)
    module_name_dups[key].append(c)

module_dup_keys = {k: v for k, v in module_name_dups.items() if len(v) > 1}

# 4. Priority distribution
priority_dist = Counter(c.get('priority', '?') for c in cases)
test_type_dist = Counter(c.get('testType', '?') for c in cases)
business_type_dist = Counter(c.get('businessType', '?') for c in cases)

# 5. Module-level stats
module_stats = []
for mod, cl in modules.items():
    p0 = sum(1 for c in cl if c.get('priority') == 'P0')
    p1 = sum(1 for c in cl if c.get('priority') == 'P1')
    p2 = sum(1 for c in cl if c.get('priority') == 'P2')
    p3 = sum(1 for c in cl if c.get('priority') == 'P3')
    # Check intra-module duplicates
    names_in_mod = [c.get('caseName', '') for c in cl]
    name_counter_in_mod = Counter(names_in_mod)
    intra_dups = sum(1 for v in name_counter_in_mod.values() if v > 1)
    module_stats.append({
        'module': mod, 'count': len(cl), 'p0': p0, 'p1': p1, 'p2': p2, 'p3': p3,
        'intra_dups': intra_dups
    })

module_stats.sort(key=lambda x: x['count'], reverse=True)

# 6. Generate report
lines = []
lines.append('# 雷霆素材系统 — 测试用例全量分析报告')
lines.append('')
lines.append(f'> **生成时间**: 2026-06-23')
lines.append(f'> **数据来源**: MCP Test Case Knowledge Base (`searchTestCases`, system=雷霆素材系统)')
lines.append(f'> **分析工具**: cdtest v3.5.2')
lines.append('')
lines.append('---')
lines.append('')
lines.append('## 一、总体概览')
lines.append('')
lines.append('| 指标 | 数值 |')
lines.append('|------|------|')
lines.append(f'| 用例总数 | **{len(cases)}** |')
lines.append(f'| 功能模块数 | **{len(modules)}** |')
lines.append(f'| 平均每模块用例数 | {len(cases)/len(modules):.1f} |')
lines.append(f'| 业务类型 | {dict(business_type_dist)} |')
lines.append('')
lines.append('### 优先级分布')
lines.append('')
lines.append('| 优先级 | 用例数 | 占比 |')
lines.append('|--------|--------|------|')
for p in ['P0', 'P1', 'P2', 'P3']:
    cnt = priority_dist.get(p, 0)
    pct = cnt / len(cases) * 100
    lines.append(f'| {p} | {cnt} | {pct:.1f}% |')
lines.append(f'| **合计** | **{len(cases)}** | **100%** |')
lines.append('')
lines.append('### 测试类型分布')
lines.append('')
lines.append('| 测试类型 | 用例数 | 占比 |')
lines.append('|----------|--------|------|')
for tt, cnt in test_type_dist.most_common():
    pct = cnt / len(cases) * 100
    lines.append(f'| {tt} | {cnt} | {pct:.1f}% |')
lines.append('')

# 7. Duplicate analysis section
lines.append('---')
lines.append('')
lines.append('## 二、🔴 用例重复性分析')
lines.append('')
lines.append('### 2.1 完全重名用例')
lines.append('')
lines.append(f'| 指标 | 数值 |')
lines.append(f'|------|------|')
lines.append(f'| 存在重名的用例名称数 | **{len(exact_dup_names)}** |')
lines.append(f'| 涉及的重名用例总条数 | **{exact_dup_cases_count}** |')
lines.append(f'| 重名率（重名条数/总条数） | **{exact_dup_cases_count/len(cases)*100:.1f}%** |')
lines.append(f'| 唯一用例名称数 | **{len(name_counts) - len(exact_dup_names)}** |')
lines.append(f'| 用例名称唯一率 | **{(len(name_counts) - len(exact_dup_names))/len(name_counts)*100:.1f}%** |')
lines.append('')

if exact_dup_names:
    lines.append('### 2.2 完全重名用例明细')
    lines.append('')
    lines.append('| 序号 | 用例名称 | 重复次数 | 涉及模块 |')
    lines.append('|------|----------|----------|----------|')
    for i, (name, cnt) in enumerate(sorted(exact_dup_names.items(), key=lambda x: -x[1]), 1):
        mods = set(c.get('module', '?') for c in name_to_cases[name])
        mod_str = '、'.join(sorted(mods))
        lines.append(f'| {i} | {name} | {cnt} | {mod_str} |')
    lines.append('')

# 3. Near duplicates
lines.append('### 2.3 高度相似用例（相似度 ≥ 85%）')
lines.append('')
lines.append(f'| 指标 | 数值 |')
lines.append(f'|------|------|')
lines.append(f'| 高度相似用例对数 | **{len(near_dup_pairs)}** |')
lines.append('')

if near_dup_pairs:
    lines.append('**Top 30 高度相似用例对：**')
    lines.append('')
    lines.append('| 序号 | 用例名称 A | 用例名称 B | 相似度 |')
    lines.append('|------|-----------|-----------|--------|')
    top_near = sorted(near_dup_pairs, key=lambda x: -x[2])[:30]
    for i, (n1, n2, ratio) in enumerate(top_near, 1):
        lines.append(f'| {i} | {n1} | {n2} | {ratio:.0%} |')
    lines.append('')

# 4. Intra-module duplicates
lines.append('### 2.4 模块内重名用例')
lines.append('')
intra_dup_modules = [m for m in module_stats if m['intra_dups'] > 0]
lines.append(f'存在模块内重名的模块数: **{len(intra_dup_modules)}** / {len(modules)}')
lines.append('')

if intra_dup_modules:
    lines.append('| 模块 | 用例总数 | 模块内重名数 |')
    lines.append('|------|----------|-------------|')
    for m in sorted(intra_dup_modules, key=lambda x: -x['intra_dups']):
        lines.append(f'| {m["module"]} | {m["count"]} | {m["intra_dups"]} |')
    lines.append('')

# 5. Duplicate summary
lines.append('### 2.5 重复性总结')
lines.append('')
lines.append(f'| 重复类型 | 数量 | 占比 |')
lines.append(f'|----------|------|------|')
lines.append(f'| 完全重名用例（条数） | {exact_dup_cases_count} | {exact_dup_cases_count/len(cases)*100:.1f}% |')
lines.append(f'| 完全重名用例名称（个） | {len(exact_dup_names)} | {len(exact_dup_names)/len(name_counts)*100:.1f}% |')
lines.append(f'| 高度相似用例对 | {len(near_dup_pairs)} | — |')
lines.append(f'| 存在模块内重名的模块 | {len(intra_dup_modules)} | {len(intra_dup_modules)/len(modules)*100:.1f}% |')
lines.append('')

# 8. Module details
lines.append('---')
lines.append('')
lines.append('## 三、模块用例分布（按用例数降序 Top 50）')
lines.append('')
lines.append('| 排名 | 功能模块 | 用例数 | P0 | P1 | P2 | P3 | 模块内重名 |')
lines.append('|------|---------|--------|----|----|----|----|-----------|')
for i, m in enumerate(module_stats[:50], 1):
    dup_flag = f'⚠️{m["intra_dups"]}' if m['intra_dups'] > 0 else '✓'
    lines.append(f'| {i} | {m["module"]} | {m["count"]} | {m["p0"]} | {m["p1"]} | {m["p2"]} | {m["p3"]} | {dup_flag} |')
lines.append(f'| ... | 其余 {len(module_stats)-50} 个模块 | ... | ... | ... | ... | ... | ... |')
lines.append('')

# 9. All modules with dups
lines.append('---')
lines.append('')
lines.append('## 四、全部模块用例清单（含重复性标记）')
lines.append('')
lines.append('| 序号 | 功能模块 | 用例数 | P0 | P1 | P2 | P3 | 模块内重名 | 去重率 |')
lines.append('|------|---------|--------|----|----|----|----|-----------|--------|')
for i, m in enumerate(module_stats, 1):
    dup_flag = f'⚠️ {m["intra_dups"]}' if m['intra_dups'] > 0 else '✓ 无'
    dedup_rate = (1 - m['intra_dups'] / m['count']) * 100 if m['count'] > 0 else 100
    lines.append(f'| {i} | {m["module"]} | {m["count"]} | {m["p0"]} | {m["p1"]} | {m["p2"]} | {m["p3"]} | {dup_flag} | {dedup_rate:.0f}% |')
lines.append(f'| **合计** | **{len(modules)} 个模块** | **{len(cases)}** | **{priority_dist.get("P0",0)}** | **{priority_dist.get("P1",0)}** | **{priority_dist.get("P2",0)}** | **{priority_dist.get("P3",0)}** | | |')
lines.append('')

# 10. Full case listing by module
lines.append('---')
lines.append('')
lines.append('## 五、用例明细（按模块分组，含用例名称+优先级+测试类型）')
lines.append('')
for mod in sorted(modules.keys()):
    cl = modules[mod]
    # Check intra-module dups here too
    mod_names = [c.get('caseName', '') for c in cl]
    mod_name_counter = Counter(mod_names)
    mod_dup_names = {k: v for k, v in mod_name_counter.items() if v > 1}

    dup_label = f' 🔴含{sum(mod_dup_names.values()) - len(mod_dup_names)}条重名' if mod_dup_names else ''
    lines.append(f'### {mod}（{len(cl)} 条）{dup_label}')
    lines.append('')
    lines.append('| 序号 | 用例名称 | 优先级 | 测试类型 | 业务类型 |')
    lines.append('|------|---------|--------|----------|----------|')
    for j, c in enumerate(cl, 1):
        name = c.get('caseName', '')
        prio = c.get('priority', '')
        ttype = c.get('testType', '')
        btype = c.get('businessType', '')
        dup_mark = ' 🔴重名' if name in mod_dup_names else ''
        lines.append(f'| {j} | {name}{dup_mark} | {prio} | {ttype} | {btype} |')
    lines.append('')

# Write report
outpath = 'd:/python/dmx/cdtest/雷霆素材系统-测试用例分析报告.md'
with open(outpath, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f'\nReport saved to: {outpath}')
print(f'Total lines: {len(lines)}')
print(f'\n=== Duplicate Analysis Summary ===')
print(f'Exact duplicate names: {len(exact_dup_names)}')
print(f'Exact duplicate cases count: {exact_dup_cases_count}')
print(f'Duplicate rate (by cases): {exact_dup_cases_count/len(cases)*100:.1f}%')
print(f'Near-duplicate pairs (>=85%): {len(near_dup_pairs)}')
print(f'Modules with intra-module dups: {len(intra_dup_modules)}')
print(f'Unique case names: {len(name_counts) - len(exact_dup_names)}')
print(f'Name uniqueness rate: {(len(name_counts) - len(exact_dup_names))/len(name_counts)*100:.1f}%')
