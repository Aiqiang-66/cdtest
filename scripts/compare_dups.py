import json
from collections import defaultdict

# Parse MCP response
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
print(f"Total cases: {len(cases)}")

# Group by (module, name)
groups = defaultdict(list)
for c in cases:
    mod = c.get('module', '')
    name = c.get('caseName', '')
    groups[(mod, name)].append(c)

# Only keep groups with > 1 case
dup_groups = {k: v for k, v in groups.items() if len(v) > 1}
print(f"Duplicate groups (same module + same name): {len(dup_groups)}")

# Compare fields within each group
# Key fields to compare (exclude id, timestamps)
compare_fields = [
    'businessType', 'system', 'module', 'testType', 'priority',
    'platform', 'core', 'appLanguage', 'appVersion', 'serverVersion',
    'testEnvironment', 'requirementVersion',
    'precondition', 'testSteps', 'expectedResult',
    'testData', 'verificationPoint'
]

# Analyze each dup group
identical_groups = []       # All fields identical -> TRUE REDUNDANCY
different_groups = []       # Some fields differ -> NEED REVIEW

for (mod, name), dup_cases in sorted(dup_groups.items()):
    # Compare all fields
    all_same = True
    diff_fields = []

    for field in compare_fields:
        values = [c.get(field, '') for c in dup_cases]
        # Normalize: convert lists to tuples for comparison
        values_normalized = []
        for v in values:
            if isinstance(v, list):
                values_normalized.append(tuple(sorted(v)) if v else ())
            else:
                values_normalized.append(v)

        if len(set(values_normalized)) > 1:
            all_same = False
            diff_fields.append(field)

    if all_same:
        identical_groups.append((mod, name, dup_cases))
    else:
        different_groups.append((mod, name, dup_cases, diff_fields))

print(f"\nIdentical (TRUE redundant): {len(identical_groups)} groups, {sum(len(c) for _,_,c in identical_groups)} cases")
print(f"Different (need review): {len(different_groups)} groups, {sum(len(c) for _,_,c,_ in different_groups)} cases")

# Extra copies count
identical_extra = sum(len(c) - 1 for _,_,c in identical_groups)
different_extra = sum(len(c) - 1 for _,_,c,_ in different_groups)
print(f"\nIdentical extra copies: {identical_extra}")
print(f"Different extra copies: {different_extra}")

# Generate report
lines = []
lines.append('# 雷霆素材系统 — 重名用例逐字段对比分析')
lines.append('')
lines.append(f'> 分析时间: 2026-06-23')
lines.append(f'> 重名组总数: {len(dup_groups)} | 完全一致: {len(identical_groups)} 组 | 内容不同: {len(different_groups)} 组')
lines.append('')

lines.append('## 一、判定标准')
lines.append('')
lines.append('| 分类 | 判定条件 | 结论 |')
lines.append('|------|----------|------|')
lines.append('| 🔴 **真冗余** | 同名同模块 + 所有字段值完全一致 | 可以安全去重，保留 1 条即可 |')
lines.append('| 🟡 **需确认** | 同名同模块 + 但 testSteps/expectedResult/testData 等存在差异 | 可能是不同场景，需优化用例名称加以区分 |')
lines.append('')

lines.append('## 二、总体统计')
lines.append('')
lines.append('| 维度 | 数值 |')
lines.append('|------|------|')
lines.append(f'| 总用例数 | {len(cases)} |')
lines.append(f'| 重名组数（同模块+同名称） | {len(dup_groups)} |')
lines.append(f'| 🔴 完全一致（真冗余）组数 | {len(identical_groups)} |')
lines.append(f'| 🔴 真冗余额外条数 | {identical_extra} |')
lines.append(f'| 🔴 **真冗余率** | **{identical_extra/len(cases)*100:.1f}%** |')
lines.append(f'| 🟡 内容有差异（需确认）组数 | {len(different_groups)} |')
lines.append(f'| 🟡 内容有差异额外条数 | {different_extra} |')
lines.append('')

# Detail: Identical
lines.append('---')
lines.append('')
lines.append('## 三、🔴 完全一致的重名用例（真冗余 — 可安全去重）')
lines.append('')
lines.append(f'共 **{len(identical_groups)}** 组，每组内所有对比字段完全相同，属于重复录入。')
lines.append('')
lines.append('| 序号 | 模块 | 用例名称 | 重复次数 | 额外冗余条数 | 优先级 |')
lines.append('|------|------|----------|----------|-------------|--------|')
for i, (mod, name, dup_cases) in enumerate(identical_groups, 1):
    prio = dup_cases[0].get('priority', '')
    lines.append(f'| {i} | {mod} | {name} | {len(dup_cases)} | {len(dup_cases)-1} | {prio} |')
lines.append('')

# Detail: Different - with field-level diff
lines.append('---')
lines.append('')
lines.append('## 四、🟡 内容有差异的重名用例（需确认是否为不同场景）')
lines.append('')
lines.append(f'共 **{len(different_groups)}** 组，同名同模块但字段内容不完全相同，需逐条确认。')
lines.append('')

for i, (mod, name, dup_cases, diff_fields) in enumerate(different_groups, 1):
    lines.append(f'### {i}. {mod} › {name}（{len(dup_cases)} 条，差异字段: {", ".join(diff_fields)}）')
    lines.append('')

    # Show each case side by side on differing fields
    for j, c in enumerate(dup_cases, 1):
        lines.append(f'**副本 {j}** (ID: `{c.get("id","")[:8]}...`)')
        lines.append('')
        lines.append('| 字段 | 值 |')
        lines.append('|------|-----|')
        for field in diff_fields:
            val = c.get(field, '')
            if isinstance(val, list):
                val = ', '.join(str(x) for x in val) if val else '(空)'
            elif val == '' or val is None:
                val = '(空)'
            lines.append(f'| {field} | {val} |')
        lines.append('')

    lines.append('---')
    lines.append('')

# Summary
lines.append('## 五、结论与建议')
lines.append('')
lines.append(f'### 🔴 真冗余（{len(identical_groups)} 组 / {identical_extra} 条）')
lines.append('')
lines.append('这些同名用例的所有关键字段（前置条件、测试步骤、预期结果、测试数据、验证点）完全一致，')
lines.append('属于纯粹的重复录入。**建议在 MCP 知识库中保留 1 条，删除其余 {identical_extra} 条。**')
lines.append('')
lines.append(f'### 🟡 需确认（{len(different_groups)} 组 / {different_extra} 条）')
lines.append('')
lines.append('这些同名用例虽然名称相同，但测试步骤、预期结果或测试数据存在差异，')
lines.append('可能是不同测试场景的用例，只是命名不够精确。**建议人工逐条确认后，优化用例名称以体现差异点。**')
lines.append('')

outpath = 'd:/python/dmx/cdtest/雷霆素材系统-重名用例逐字段对比报告.md'
with open(outpath, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print(f'\nReport saved to: {outpath}')
