"""
英文长文本阶梯式极限压力测试
文本: 3977字符/677词, 阶梯: 1→2→4→8→12→16→20→24→32
每阶梯跑完一批任务后统计成功率，错误率>10%则停止
"""
import time, requests, urllib3, statistics, threading, json, os
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings()

URL = "http://ai-audiobook-api-none-new-dev.changdu.ltd/api/tts/synthesize"
OUTPUT_DIR = r"d:\python\dmx\cdtest\tools\test_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 加载长文本
txt_path = r"d:\python\dmx\cdtest\docs\需求文档\听书测试物料\txt文本\8FA4C02F-DE32-4569-908E-DF05A9715BD8.txt"
with open(txt_path, "r", encoding="utf-16") as f:
    full_text = f.read()
# 截取约 3500 字符
cut = full_text.rfind(".", 0, 3500) + 1
EN_LONG = full_text[:cut].strip()
print(f"英文长文本: {len(EN_LONG)} 字符, {len(EN_LONG.split())} 词")
print(f"预览: {EN_LONG[:100]}...")

STOP_ERROR_RATE = 0.10  # 错误率超过 10% 停止

def run_step(concurrency, tasks_per_worker=3):
    """
    每阶梯: 并发数 × 每worker任务数 = 总任务数
    等所有任务完成后统计成功率
    """
    total = concurrency * tasks_per_worker
    results = {"success": 0, "fail_503": 0, "fail_other": 0, "latencies": []}
    lock = threading.Lock()
    
    def worker():
        for _ in range(tasks_per_worker):
            t0 = time.time()
            try:
                resp = requests.post(URL, json={
                    "read_content": EN_LONG,
                    "chapter_title": f"Stress L{concurrency}",
                    "model": "higgs",
                    "voice": "audiobook_female_2",
                    "lang": 3
                }, timeout=600, verify=False)
                lat = time.time() - t0
                if resp.status_code == 200 and resp.json().get("code") == 0:
                    with lock:
                        results["success"] += 1
                        results["latencies"].append(lat)
                elif resp.status_code == 503:
                    with lock:
                        results["fail_503"] += 1
                else:
                    with lock:
                        results["fail_other"] += 1
            except Exception as e:
                with lock:
                    results["fail_other"] += 1
    
    print(f"\n[并发={concurrency}] 发送 {total} 个任务...")
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(worker) for _ in range(concurrency)]
        for f in as_completed(futures):
            f.result()
    elapsed = time.time() - t0
    
    total_done = results["success"] + results["fail_503"] + results["fail_other"]
    error_rate = (results["fail_503"] + results["fail_other"]) / total_done if total_done > 0 else 0
    qps = results["success"] / elapsed if elapsed > 0 else 0
    
    r = {
        "concurrency": concurrency,
        "total_tasks": total,
        "success": results["success"],
        "fail_503": results["fail_503"],
        "fail_other": results["fail_other"],
        "error_rate": round(error_rate * 100, 1),
        "qps": round(qps, 3),
        "tasks_per_hour": round(qps * 3600),
        "elapsed_s": round(elapsed, 1),
        "avg_s": round(statistics.mean(results["latencies"]), 1) if results["latencies"] else 0,
        "p95_s": round(sorted(results["latencies"])[int(len(results["latencies"])*0.95)], 1) if results["latencies"] else 0,
        "p99_s": round(sorted(results["latencies"])[int(len(results["latencies"])*0.99)], 1) if results["latencies"] else 0,
    }
    
    print(f"  ✅ 成功={r['success']}, 503={r['fail_503']}, 其他失败={r['fail_other']}")
    print(f"  📊 错误率={r['error_rate']}%, QPS={r['qps']}, 吞吐={r['tasks_per_hour']}/h, 耗时={r['elapsed_s']}s")
    print(f"  ⏱ Avg={r['avg_s']}s, P95={r['p95_s']}s, P99={r['p99_s']}s")
    
    return r


print("=" * 60)
print("  英文长文本阶梯式极限压力测试")
print(f"  文本: {len(EN_LONG)} 字符, 停止条件: 错误率 > {STOP_ERROR_RATE*100}%")
print("=" * 60)

# 预热
print("\n[预热]...")
resp = requests.post(URL, json={
    "read_content": "Hello world.",
    "chapter_title": "Warmup",
    "model": "higgs", "voice": "audiobook_female_2", "lang": 3
}, timeout=120, verify=False)
print(f"  预热完成: HTTP {resp.status_code}")

results = []
stopped_early = False

for c in [1, 2, 4, 8, 12, 16, 20, 24, 32]:
    # 低并发多跑几个任务，高并发少跑（因为慢）
    tasks_per = 4 if c <= 4 else (3 if c <= 12 else 2)
    r = run_step(c, tasks_per)
    results.append(r)
    
    if r["error_rate"] > STOP_ERROR_RATE * 100:
        print(f"\n⛔ 错误率 {r['error_rate']}% 超过阈值 {STOP_ERROR_RATE*100}%，停止加压！")
        stopped_early = True
        break
    
    if c < 32:
        time.sleep(5)

# 汇总
print("\n" + "=" * 65)
print("  📊 长文本极限压力测试汇总")
print("=" * 65)
print(f"{'并发':<6} {'任务':<6} {'成功':<6} {'503':<6} {'错误率':<8} {'QPS':<8} {'任务/h':<8} {'Avg':<8} {'P95':<8} {'P99':<8}")
print("-" * 80)
for r in results:
    print(f"{r['concurrency']:<6} {r['total_tasks']:<6} {r['success']:<6} {r['fail_503']:<6} "
          f"{r['error_rate']:<8} {r['qps']:<8} {r['tasks_per_hour']:<8} "
          f"{r['avg_s']:<8} {r['p95_s']:<8} {r['p99_s']:<8}")

if stopped_early:
    print(f"\n⛔ 在并发={results[-1]['concurrency']} 时触发停止条件")

# 找最优并发（QPS最高且错误率<5%）
valid = [r for r in results if r["error_rate"] < 5]
if valid:
    best = max(valid, key=lambda r: r["qps"])
    print(f"\n✅ 推荐并发: {best['concurrency']} (QPS={best['qps']}, 吞吐={best['tasks_per_hour']}/h, 错误率={best['error_rate']}%)")

# 计算稳定性测试任务数
if valid:
    target_hours = 24
    stability_tasks = best["tasks_per_hour"] * target_hours
    print(f"\n📐 稳定性测试建议: {best['concurrency']}并发 × 24小时 ≈ {stability_tasks} 任务")

json.dump(results, open(os.path.join(OUTPUT_DIR, "stress_long_en.json"), "w"), indent=2, ensure_ascii=False)
