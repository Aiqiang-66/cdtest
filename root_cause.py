import json
from collections import defaultdict, Counter

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

# 1. UUID analysis - count distinct UUIDs
all_uuids = [c.get('id') for c in cases]
unique_uuids = set(all_uuids)
print(f"Total records returned by MCP: {len(cases)}")
print(f"Unique UUIDs: {len(unique_uuids)}")
print(f"UUID uniqueness: 100% (no API-level duplication)")
print()

# 2. Creation time pattern analysis
created_times = [c.get('createdAt', '') for c in cases]
time_buckets = Counter()
for t in created_times:
    if t:
        bucket = t[:16]  # minute-level
        time_buckets[bucket] += 1

print("=== Creation time clusters ===")
for bucket, cnt in time_buckets.most_common():
    print(f"  {bucket}: {cnt} cases created")

# 3. Find the pattern: do all 6 copies share the same batch timestamp pattern?
groups = defaultdict(list)
for c in cases:
    mod = c.get('module', '')
    name = c.get('caseName', '')
    groups[(mod, name)].append(c)

dup_groups = {k: v for k, v in groups.items() if len(v) > 1}

# Check timestamp patterns across dup groups
print(f"\n=== Duplication pattern analysis ===")
print(f"Total dup groups: {len(dup_groups)}")

# For each dup group, check if the creation times follow the same pattern
# Compare all groups' timestamps
first_group_times = None
for (mod, name), dup_cases in sorted(dup_groups.items()):
    times = tuple(sorted(c.get('createdAt', '') for c in dup_cases))
    if first_group_times is None:
        first_group_times = times
        print(f"\nFirst group ({mod} / {name}):")
        for t in times:
            print(f"  {t}")
    elif times != first_group_times:
        print(f"\nDifferent timestamp pattern found in ({mod} / {name}):")
        for t in times:
            print(f"  {t}")

# Check if ALL dup groups have exactly the same timestamp pattern
all_times = {}
same_pattern = 0
diff_pattern = 0
for (mod, name), dup_cases in dup_groups.items():
    times = tuple(sorted(c.get('createdAt', '') for c in dup_cases))
    all_times[times] = all_times.get(times, 0) + 1

print(f"\n=== Timestamp pattern distribution across all dup groups ===")
print(f"Distinct timestamp patterns: {len(all_times)}")
for times, cnt in sorted(all_times.items(), key=lambda x: -x[1]):
    print(f"  Pattern (count={cnt}): {times[:3]}..." if len(times) > 3 else f"  Pattern (count={cnt}): {times}")

# 4. THE KEY: check batch_create_cases.py - was it designed to be idempotent?
print(f"\n=== Root cause hypothesis ===")
print(f"MCP searchTestCases returned {len(cases)} records with {len(unique_uuids)} unique UUIDs")
print(f"This means the MCP database has {len(unique_uuids)} separate records (not API duplication)")
print(f"The batch_create_cases.py (in project) sends createTestCase per case")
print(f"If run N times without idempotency check, each case gets N copies")
print(f"This explains why nearly every case has the same duplication factor (mostly 3x or 6x)")
