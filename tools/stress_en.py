"""
英文短文本 TTS 压力测试：阶梯并发，测峰值 QPS
"""
import time, requests, urllib3, statistics, threading, json, os
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings()

URL = "http://ai-audiobook-api-none-new-dev.changdu.ltd/api/tts/synthesize"
OUTPUT_DIR = r"d:\python\dmx\cdtest\tools\test_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

EN_TEXT = "The sun rose over the quiet village, casting golden light across the rooftops. Birds began their morning songs as the world slowly awakened. A gentle breeze carried the scent of fresh bread from the bakery down the street."

print(f"英文文本: {len(EN_TEXT)} 字符, {len(EN_TEXT.split())} 词")

def run_test(concurrency, duration=90):
    completed = 0
    failed = 0
    latencies = []
    lock = threading.Lock()
    end_time = time.time() + duration
    
    def worker():
        nonlocal completed, failed
        while time.time() < end_time:
            t0 = time.time()
            try:
                resp = requests.post(URL, json={
                    "read_content": EN_TEXT,
                    "chapter_title": "Stress Test",
                    "model": "higgs",
                    "voice": "audiobook_female_2",
                    "lang": 3
                }, timeout=300, verify=False)
                lat = time.time() - t0
                if resp.status_code == 200 and resp.json().get("code") == 0:
                    with lock:
                        completed += 1
                        latencies.append(lat)
                else:
                    with lock:
                        failed += 1
            except:
                with lock:
                    failed += 1
    
    print(f"\n[并发={concurrency}] {concurrency} workers, {duration}s...")
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(worker) for _ in range(concurrency)]
        while time.time() < end_time:
            time.sleep(20)
            elapsed = time.time() - t0
            with lock:
                print(f"  [{elapsed:.0f}s] done={completed}, fail={failed}, qps≈{completed/elapsed:.3f}" if elapsed > 0 else "")
        for f in as_completed(futures):
            f.result()
    
    elapsed = time.time() - t0
    qps = completed / elapsed if elapsed > 0 else 0
    r = {
        "concurrency": concurrency, "duration": round(elapsed,1),
        "completed": completed, "failed": failed, "qps": round(qps,3),
        "avg_s": round(statistics.mean(latencies),1) if latencies else 0,
        "p50_s": round(sorted(latencies)[len(latencies)//2],1) if latencies else 0,
        "p95_s": round(sorted(latencies)[int(len(latencies)*0.95)],1) if latencies else 0,
    }
    print(f"  => QPS={r['qps']}, avg={r['avg_s']}s, p95={r['p95_s']}s")
    return r

print("=" * 60)
print("  英文短文本 TTS 压力测试")
print("=" * 60)

# 预热
print("\n[预热]...")
resp = requests.post(URL, json={"read_content":"Hello.","chapter_title":"Warmup","model":"higgs","voice":"audiobook_female_2","lang":3}, timeout=60, verify=False)
print(f"  预热完成: HTTP {resp.status_code}, {time.time()-t0 if False else ''}")

results = []
for c in [1, 2, 4, 8, 12, 16]:
    r = run_test(c, 90 if c <= 4 else 120)
    results.append(r)
    if c < 16:
        time.sleep(5)

# 汇总
print("\n" + "=" * 60)
print("  📊 英文压力测试汇总")
print("=" * 60)
print(f"{'并发':<6} {'完成':<8} {'失败':<6} {'QPS':<10} {'Avg':<8} {'P50':<8} {'P95':<8}")
print("-" * 60)
for r in results:
    print(f"{r['concurrency']:<6} {r['completed']:<8} {r['failed']:<6} {r['qps']:<10} {r['avg_s']:<8} {r['p50_s']:<8} {r['p95_s']:<8}")

best = max(results, key=lambda r: r['qps'])
print(f"\n🔥 峰值 QPS: {best['qps']} (并发={best['concurrency']})")
print(f"   任务/小时: {best['qps']*3600:.0f}")

json.dump(results, open(os.path.join(OUTPUT_DIR, "stress_en.json"), "w"), indent=2)
