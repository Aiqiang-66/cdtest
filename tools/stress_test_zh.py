"""
中文长文本 TTS 压力测试：3000-4000字符，阶梯并发，测 QPS
"""
import time, requests, urllib3, statistics, threading, json, os
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

urllib3.disable_warnings()

URL = "http://ai-audiobook-api-none-new-dev.changdu.ltd/api/tts/synthesize"
OUTPUT_DIR = r"d:\python\dmx\cdtest\tools\test_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 加载中文文本
txt_path = r"d:\python\dmx\cdtest\docs\需求文档\听书测试物料\txt文本\中文.txt"
with open(txt_path, "r", encoding="utf-8") as f:
    ZH_TEXT = f.read()

print(f"中文文本: {len(ZH_TEXT)} 字符")
print(f"预览: {ZH_TEXT[:80]}...")

# ============================================================
# 阶梯并发测试
# ============================================================
def run_concurrency_test(concurrency, duration_seconds=120):
    """指定并发数，跑固定时长，统计 QPS/成功率/延迟"""
    completed = 0
    failed = 0
    latencies = []
    lock = threading.Lock()
    start_time = time.time()
    end_time = start_time + duration_seconds
    
    def worker():
        nonlocal completed, failed
        while time.time() < end_time:
            t0 = time.time()
            try:
                resp = requests.post(URL, json={
                    "read_content": ZH_TEXT,
                    "chapter_title": "压力测试",
                    "model": "higgs",
                    "voice": "audiobook_female_2",
                    "lang": 1
                }, timeout=600, verify=False)
                lat = time.time() - t0
                if resp.status_code == 200 and resp.json().get("code") == 0:
                    with lock:
                        completed += 1
                        latencies.append(lat)
                else:
                    with lock:
                        failed += 1
            except Exception as e:
                with lock:
                    failed += 1
    
    print(f"\n[并发={concurrency}] 启动 {concurrency} 个 worker, 持续 {duration_seconds}s...")
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(worker) for _ in range(concurrency)]
        # 每 30 秒打印进度
        while time.time() < end_time:
            time.sleep(30)
            elapsed = time.time() - t0
            with lock:
                qps = completed / elapsed if elapsed > 0 else 0
                print(f"  [{elapsed:.0f}s] 完成={completed}, 失败={failed}, QPS≈{qps:.2f}")
        for f in as_completed(futures):
            f.result()
    
    elapsed = time.time() - t0
    qps = completed / elapsed if elapsed > 0 else 0
    
    result = {
        "concurrency": concurrency,
        "duration_s": round(elapsed, 1),
        "completed": completed,
        "failed": failed,
        "qps": round(qps, 3),
        "avg_latency_s": round(statistics.mean(latencies), 1) if latencies else 0,
        "p50_latency_s": round(sorted(latencies)[len(latencies)//2], 1) if latencies else 0,
        "p95_latency_s": round(sorted(latencies)[int(len(latencies)*0.95)], 1) if latencies else 0,
        "p99_latency_s": round(sorted(latencies)[int(len(latencies)*0.99)], 1) if latencies else 0,
        "min_latency_s": round(min(latencies), 1) if latencies else 0,
        "max_latency_s": round(max(latencies), 1) if latencies else 0,
    }
    
    print(f"  结果: QPS={result['qps']}, 成功={completed}, 失败={failed}, "
          f"Avg={result['avg_latency_s']}s, P95={result['p95_latency_s']}s")
    return result


# ============================================================
# 主程序
# ============================================================
print("=" * 60)
print("  中文长文本 TTS 压力测试 (Higgs, 2482字符)")
print("=" * 60)

# 先跑一个预热请求
print("\n[预热] 发送单个请求...")
t0 = time.time()
resp = requests.post(URL, json={
    "read_content": ZH_TEXT[:500],
    "chapter_title": "预热",
    "model": "higgs",
    "voice": "audiobook_female_2",
    "lang": 1
}, timeout=300, verify=False)
print(f"  预热完成: HTTP {resp.status_code}, 耗时 {time.time()-t0:.1f}s")

# 阶梯测试: 1, 2, 4, 8, 12, 16 并发
results = []
for c in [1, 2, 4, 8, 12, 16]:
    # 低并发跑 90s，高并发跑 120s
    duration = 90 if c <= 4 else 120
    r = run_concurrency_test(c, duration)
    results.append(r)
    # 阶梯间休息 10 秒
    if c < 16:
        print("  冷却 10s...")
        time.sleep(10)

# ============================================================
# 汇总报告
# ============================================================
print("\n" + "=" * 60)
print("  📊 压力测试汇总")
print("=" * 60)
print(f"{'并发':<6} {'完成':<8} {'失败':<6} {'QPS':<8} {'Avg':<8} {'P50':<8} {'P95':<8} {'P99':<8}")
print("-" * 60)
for r in results:
    print(f"{r['concurrency']:<6} {r['completed']:<8} {r['failed']:<6} "
          f"{r['qps']:<8} {r['avg_latency_s']:<8} {r['p50_latency_s']:<8} "
          f"{r['p95_latency_s']:<8} {r['p99_latency_s']:<8}")

# 找最大 QPS
max_qps = max(results, key=lambda r: r['qps'])
print(f"\n🔥 最大 QPS: {max_qps['qps']} (并发={max_qps['concurrency']})")

# 保存报告
report_path = os.path.join(OUTPUT_DIR, "stress_test_zh.json")
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"报告: {report_path}")
