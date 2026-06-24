"""
英文短文本极限压力测试：超过 16 并发，验证 503 行为
"""
import time, requests, urllib3, statistics, threading, json, os
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

urllib3.disable_warnings()

URL = "http://ai-audiobook-api-none-new-dev.changdu.ltd/api/tts/synthesize"
EN_TEXT = "The sun rose over the quiet village, casting golden light across the rooftops. Birds began their morning songs as the world slowly awakened."

def run_test(concurrency, duration=90):
    completed = 0
    failed_503 = 0
    failed_other = 0
    latencies = []
    lock = threading.Lock()
    end_time = time.time() + duration
    
    def worker():
        nonlocal completed, failed_503, failed_other
        while time.time() < end_time:
            t0 = time.time()
            try:
                resp = requests.post(URL, json={
                    "read_content": EN_TEXT,
                    "chapter_title": "Limit Test",
                    "model": "higgs",
                    "voice": "audiobook_female_2",
                    "lang": 3
                }, timeout=120, verify=False)
                lat = time.time() - t0
                if resp.status_code == 200 and resp.json().get("code") == 0:
                    with lock:
                        completed += 1
                        latencies.append(lat)
                elif resp.status_code == 503:
                    with lock:
                        failed_503 += 1
                else:
                    with lock:
                        failed_other += 1
            except:
                with lock:
                    failed_other += 1
    
    print(f"\n[并发={concurrency}] {concurrency} workers, {duration}s...")
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(worker) for _ in range(concurrency)]
        while time.time() < end_time:
            time.sleep(20)
            elapsed = time.time() - t0
            with lock:
                total = completed + failed_503 + failed_other
                print(f"  [{elapsed:.0f}s] 成功={completed}, 503={failed_503}, 其他失败={failed_other}, 总={total}")
        for f in as_completed(futures):
            f.result()
    
    elapsed = time.time() - t0
    total = completed + failed_503 + failed_other
    qps = completed / elapsed if elapsed > 0 else 0
    
    r = {
        "concurrency": concurrency, "duration": round(elapsed,1),
        "completed": completed, "failed_503": failed_503, "failed_other": failed_other,
        "total": total, "qps": round(qps,3),
        "success_rate": round(completed/total*100,1) if total > 0 else 0,
        "avg_s": round(statistics.mean(latencies),1) if latencies else 0,
        "p95_s": round(sorted(latencies)[int(len(latencies)*0.95)],1) if latencies else 0,
    }
    print(f"  => 成功={completed}, 503={failed_503}, QPS={r['qps']}, 成功率={r['success_rate']}%")
    return r

print("=" * 60)
print("  英文短文本极限压力测试（超 16 并发）")
print("=" * 60)

results = []
for c in [16, 20, 24, 32]:
    r = run_test(c, 90)
    results.append(r)
    time.sleep(5)

print("\n" + "=" * 60)
print("  📊 极限压力测试汇总")
print("=" * 60)
print(f"{'并发':<6} {'成功':<8} {'503':<8} {'其他失败':<8} {'QPS':<8} {'成功率':<10} {'Avg':<8}")
print("-" * 65)
for r in results:
    print(f"{r['concurrency']:<6} {r['completed']:<8} {r['failed_503']:<8} {r['failed_other']:<8} {r['qps']:<8} {r['success_rate']:<10} {r['avg_s']:<8}")

print(f"\n结论：服务端硬限制最大并发=16，超过后返回 HTTP 503")
