"""
稳定性测试: 16并发持续2小时
- 每30秒统计一次成功率/延迟
- 记录所有失败详情
- 输出稳定性报告
"""
import time, requests, urllib3, statistics, threading, json, os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

urllib3.disable_warnings()

URL = "http://ai-audiobook-api-none-new-dev.changdu.ltd/api/tts/synthesize"
OUTPUT_DIR = r"d:\python\dmx\cdtest\tools\test_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

CONCURRENCY = 16
DURATION_HOURS = 2
DURATION_SECONDS = DURATION_HOURS * 3600
STATS_INTERVAL = 30  # 每30秒输出一次统计

# 加载英文长文本
txt_path = r"d:\python\dmx\cdtest\docs\需求文档\听书测试物料\txt文本\8FA4C02F-DE32-4569-908E-DF05A9715BD8.txt"
with open(txt_path, "r", encoding="utf-16") as f:
    full_text = f.read()
cut = full_text.rfind(".", 0, 3500) + 1
EN_LONG = full_text[:cut].strip()
print(f"英文长文本: {len(EN_LONG)} 字符, {len(EN_LONG.split())} 词")

# 全局统计
stats_lock = threading.Lock()
stats = {
    "success": 0,
    "fail_503": 0,
    "fail_other": 0,
    "latencies": [],
    "failures": [],  # 失败详情
    "start_time": None,
    "end_time": None,
}

stop_flag = threading.Event()

def send_task():
    """发送单个TTS任务，返回 (success, latency, error_info)"""
    t0 = time.time()
    try:
        resp = requests.post(URL, json={
            "read_content": EN_LONG,
            "chapter_title": f"Stability-{int(t0)}",
            "model": "higgs",
            "voice": "audiobook_female_2",
            "lang": 3
        }, timeout=600, verify=False)
        lat = time.time() - t0
        if resp.status_code == 200 and resp.json().get("code") == 0:
            return ("success", lat, None)
        elif resp.status_code == 503:
            return ("fail_503", lat, f"HTTP 503: {resp.text[:200]}")
        else:
            return ("fail_other", lat, f"HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        lat = time.time() - t0
        return ("fail_other", lat, str(e)[:200])

def worker():
    """持续发送任务直到停止信号"""
    while not stop_flag.is_set():
        result, lat, err = send_task()
        with stats_lock:
            if result == "success":
                stats["success"] += 1
                stats["latencies"].append(lat)
            elif result == "fail_503":
                stats["fail_503"] += 1
                stats["failures"].append({"time": datetime.now().isoformat(), "type": "503", "error": err, "latency": lat})
            else:
                stats["fail_other"] += 1
                stats["failures"].append({"time": datetime.now().isoformat(), "type": "other", "error": err, "latency": lat})

def stats_reporter():
    """每30秒输出统计快照"""
    last_snapshot = {"success": 0, "fail_503": 0, "fail_other": 0}
    while not stop_flag.is_set():
        time.sleep(STATS_INTERVAL)
        with stats_lock:
            now = datetime.now()
            elapsed = (now - stats["start_time"]).total_seconds()
            remaining = DURATION_SECONDS - elapsed
            
            # 增量
            delta_success = stats["success"] - last_snapshot["success"]
            delta_503 = stats["fail_503"] - last_snapshot["fail_503"]
            delta_other = stats["fail_other"] - last_snapshot["fail_other"]
            delta_total = delta_success + delta_503 + delta_other
            
            total_done = stats["success"] + stats["fail_503"] + stats["fail_other"]
            error_rate = (stats["fail_503"] + stats["fail_other"]) / total_done * 100 if total_done > 0 else 0
            
            # 最近30秒的QPS
            qps_30s = delta_total / STATS_INTERVAL if STATS_INTERVAL > 0 else 0
            
            # 延迟统计
            if stats["latencies"]:
                recent_lats = stats["latencies"][-max(1, delta_success):] if delta_success > 0 else stats["latencies"][-100:]
                avg_lat = statistics.mean(recent_lats)
                p95_lat = sorted(recent_lats)[int(len(recent_lats)*0.95)] if len(recent_lats) >= 20 else avg_lat
            else:
                avg_lat = p95_lat = 0
            
            last_snapshot = {"success": stats["success"], "fail_503": stats["fail_503"], "fail_other": stats["fail_other"]}
        
        elapsed_min = elapsed / 60
        remaining_min = remaining / 60
        print(f"[{now.strftime('%H:%M:%S')}] ⏱ {elapsed_min:.0f}min/{DURATION_HOURS*60:.0f}min | "
              f"30s: ✅{delta_success} ❌503:{delta_503} ❌其他:{delta_other} | "
              f"累计: ✅{stats['success']} ❌{stats['fail_503']+stats['fail_other']} | "
              f"错误率:{error_rate:.1f}% | QPS(30s):{qps_30s:.2f} | "
              f"Avg:{avg_lat:.1f}s P95:{p95_lat:.1f}s | 剩余:{remaining_min:.0f}min")


print("=" * 60)
print(f"  稳定性测试: {CONCURRENCY}并发 × {DURATION_HOURS}小时")
print(f"  文本: {len(EN_LONG)} 字符")
print(f"  开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# 预热
print("\n[预热]...")
resp = requests.post(URL, json={
    "read_content": "Hello world.",
    "chapter_title": "Warmup",
    "model": "higgs", "voice": "audiobook_female_2", "lang": 3
}, timeout=120, verify=False)
print(f"  预热完成: HTTP {resp.status_code}")

# 启动
stats["start_time"] = datetime.now()

# 启动16个worker线程
workers = []
for i in range(CONCURRENCY):
    t = threading.Thread(target=worker, name=f"worker-{i}")
    t.daemon = True
    t.start()
    workers.append(t)

# 启动统计报告线程
reporter = threading.Thread(target=stats_reporter, daemon=True)
reporter.start()

# 等待2小时
try:
    time.sleep(DURATION_SECONDS)
except KeyboardInterrupt:
    print("\n⚠️ 手动中断")

# 停止
stop_flag.set()
print("\n⏳ 等待所有worker完成当前任务...")
for t in workers:
    t.join(timeout=120)

stats["end_time"] = datetime.now()
total_elapsed = (stats["end_time"] - stats["start_time"]).total_seconds()

# 最终统计
total_done = stats["success"] + stats["fail_503"] + stats["fail_other"]
error_rate = (stats["fail_503"] + stats["fail_other"]) / total_done * 100 if total_done > 0 else 0
qps = total_done / total_elapsed if total_elapsed > 0 else 0
success_qps = stats["success"] / total_elapsed if total_elapsed > 0 else 0

print("\n" + "=" * 65)
print("  📊 稳定性测试最终报告")
print("=" * 65)
print(f"  并发数:       {CONCURRENCY}")
print(f"  计划时长:     {DURATION_HOURS} 小时")
print(f"  实际时长:     {total_elapsed/3600:.2f} 小时 ({total_elapsed:.0f}s)")
print(f"  总任务数:     {total_done}")
print(f"  成功:         {stats['success']} ({stats['success']/total_done*100:.1f}%)" if total_done > 0 else "  成功: 0")
print(f"  失败(503):    {stats['fail_503']}")
print(f"  失败(其他):   {stats['fail_other']}")
print(f"  错误率:       {error_rate:.2f}%")
print(f"  总QPS:        {qps:.3f}")
print(f"  成功QPS:      {success_qps:.3f}")
print(f"  吞吐量:       {success_qps*3600:.0f} 任务/小时")

if stats["latencies"]:
    sorted_lats = sorted(stats["latencies"])
    print(f"  平均延迟:     {statistics.mean(stats['latencies']):.1f}s")
    print(f"  中位延迟:     {statistics.median(stats['latencies']):.1f}s")
    print(f"  P95延迟:      {sorted_lats[int(len(sorted_lats)*0.95)]:.1f}s")
    print(f"  P99延迟:      {sorted_lats[int(len(sorted_lats)*0.99)]:.1f}s")
    print(f"  最小延迟:     {min(stats['latencies']):.1f}s")
    print(f"  最大延迟:     {max(stats['latencies']):.1f}s")

# 失败详情
if stats["failures"]:
    print(f"\n  失败详情 (共 {len(stats['failures'])} 条):")
    for f in stats["failures"][:20]:
        print(f"    [{f['time']}] {f['type']}: {f['error'][:100]}")
    if len(stats["failures"]) > 20:
        print(f"    ... 还有 {len(stats['failures'])-20} 条")

# 保存报告
report = {
    "test_type": "stability",
    "concurrency": CONCURRENCY,
    "planned_duration_hours": DURATION_HOURS,
    "actual_duration_s": total_elapsed,
    "start_time": stats["start_time"].isoformat(),
    "end_time": stats["end_time"].isoformat(),
    "total_tasks": total_done,
    "success": stats["success"],
    "fail_503": stats["fail_503"],
    "fail_other": stats["fail_other"],
    "error_rate_pct": round(error_rate, 2),
    "total_qps": round(qps, 3),
    "success_qps": round(success_qps, 3),
    "tasks_per_hour": round(success_qps * 3600),
    "latency": {
        "avg_s": round(statistics.mean(stats["latencies"]), 1) if stats["latencies"] else 0,
        "median_s": round(statistics.median(stats["latencies"]), 1) if stats["latencies"] else 0,
        "p95_s": round(sorted(stats["latencies"])[int(len(stats["latencies"])*0.95)], 1) if stats["latencies"] else 0,
        "p99_s": round(sorted(stats["latencies"])[int(len(stats["latencies"])*0.99)], 1) if stats["latencies"] else 0,
        "min_s": round(min(stats["latencies"]), 1) if stats["latencies"] else 0,
        "max_s": round(max(stats["latencies"]), 1) if stats["latencies"] else 0,
    },
    "failures": stats["failures"][:100],  # 最多保存100条
}

report_path = os.path.join(OUTPUT_DIR, f"stability_{CONCURRENCY}c_{DURATION_HOURS}h_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
json.dump(report, open(report_path, "w"), indent=2, ensure_ascii=False)
print(f"\n📄 报告已保存: {report_path}")

# 稳定性评级
if error_rate == 0:
    grade = "⭐⭐⭐⭐⭐ 完美"
elif error_rate < 1:
    grade = "⭐⭐⭐⭐ 优秀"
elif error_rate < 5:
    grade = "⭐⭐⭐ 良好"
elif error_rate < 10:
    grade = "⭐⭐ 一般"
else:
    grade = "⭐ 差"
print(f"  稳定性评级: {grade}")
