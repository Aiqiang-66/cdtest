"""
听书 TTS 完整测试执行脚本
用法: python run_tests.py [--phase 1|2|3|4|5|all]
"""
import json, os, sys, time, requests, urllib3, statistics, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter, defaultdict
from datetime import datetime

urllib3.disable_warnings()

# ============================================================
# 配置
# ============================================================
URL = "http://ai-audiobook-api-none-new-dev.changdu.ltd/api/tts/synthesize"
OUTPUT_DIR = r"d:\python\dmx\cdtest\tools\test_output"
MODEL = "higgs"
VOICE = "audiobook_female_2"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 测试文本
TEXTS = {
    "en_short": "The sun rose over the quiet village, casting golden light across the rooftops. Birds began their morning songs.",
    "en_medium": "The old library stood at the end of the cobblestone street, its windows dark and its doors always slightly ajar. No one could remember the last time anyone had gone inside. The townspeople spoke of it in hushed tones, as if the building itself were listening. Sarah had walked past it a hundred times, but today was different. Today, she pushed the door open and stepped inside. The air was thick with dust and the scent of old paper.",
    "en_long": None,  # 从文件加载
    "zh_short": "太阳从东方升起，金色的光芒洒满了整个村庄。鸟儿开始在枝头歌唱，新的一天开始了。",
    "zh_medium": "老街的尽头有一座古老的图书馆，它的窗户总是黑着的，门也总是半掩着。镇上的人们提起它时总是压低了声音，仿佛那栋建筑本身在偷听。小林从这里路过无数次，但今天不同。今天，她推开门走了进去。空气中弥漫着灰尘和旧书的气味。",
}

# 加载长文本
txt_path = r"d:\python\dmx\cdtest\docs\需求文档\听书测试物料\txt文本\8FA4C02F-DE32-4569-908E-DF05A9715BD8.txt"
with open(txt_path, "r", encoding="utf-16") as f:
    TEXTS["en_long"] = f.read()

# ============================================================
# 工具函数
# ============================================================
def call_tts(read_content, chapter_title="Test", lang=3):
    """调用 TTS API，返回 (success, latency, result)"""
    t0 = time.time()
    try:
        resp = requests.post(URL, json={
            "read_content": read_content,
            "chapter_title": chapter_title,
            "model": MODEL,
            "voice": VOICE,
            "lang": lang
        }, timeout=300, verify=False)
        latency = time.time() - t0
        if resp.status_code == 200:
            data = resp.json()
            return data.get("code") == 0, latency, data
        return False, latency, {"error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return False, time.time() - t0, {"error": str(e)}


def download_audio(audio_url, max_retries=5):
    """下载音频，返回本地路径（COS 可能有上传延迟，加重试）"""
    path = os.path.join(OUTPUT_DIR, "last_audio.mp3")
    for attempt in range(max_retries):
        resp = requests.get(audio_url, timeout=120, verify=False)
        if resp.status_code == 200 and len(resp.content) > 1000:
            with open(path, "wb") as f:
                f.write(resp.content)
            print(f"  下载完成: {len(resp.content)/1024:.1f} KB (尝试 {attempt+1} 次)")
            return path
        print(f"  下载重试 {attempt+1}/{max_retries}: HTTP {resp.status_code}, size={len(resp.content)}")
        time.sleep(3)
    raise Exception(f"Download failed after {max_retries} retries")


def transcribe_and_wer(audio_path, reference_text, lang="en"):
    """Whisper 转写 + 计算 WER"""
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    from faster_whisper import WhisperModel
    
    model = WhisperModel("base", device="cpu", compute_type="int8",
                         download_root=r"d:\python\dmx\cdtest\tools\whisper_models",
                         local_files_only=True)
    
    segments_raw, info = model.transcribe(audio_path, language=lang,
                                          beam_size=5, word_timestamps=True,
                                          vad_filter=True)
    
    hyp_parts = []
    for seg in segments_raw:
        hyp_parts.append(seg.text.strip())
    hypothesis = " ".join(hyp_parts)
    
    # 计算 WER
    ref_words = reference_text.lower().split()
    hyp_words = hypothesis.lower().split()
    m, n = len(ref_words), len(hyp_words)
    dp = [[0]*(n+1) for _ in range(m+1)]
    for i in range(m+1): dp[i][0] = i
    for j in range(n+1): dp[0][j] = j
    for i in range(1, m+1):
        for j in range(1, n+1):
            cost = 0 if ref_words[i-1] == hyp_words[j-1] else 1
            dp[i][j] = min(dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+cost)
    
    wer = dp[m][n] / max(len(ref_words), 1)
    return {"wer": round(wer*100, 2), "hypothesis": hypothesis, "language": info.language}


# ============================================================
# Phase 1: 功能正确性 (快速冒烟)
# ============================================================
def phase1_smoke():
    """快速冒烟：英文+中文各1条，验证基本流程"""
    print("=" * 60)
    print("Phase 1: 功能冒烟测试")
    print("=" * 60)
    
    results = []
    tests = [
        ("EN Short", TEXTS["en_short"], "Test EN", 3),
        ("ZH Short", TEXTS["zh_short"], "测试中文", 1),
    ]
    
    for name, text, title, lang in tests:
        print(f"\n[{name}] 发送请求... (text: {len(text)} chars)")
        ok, lat, data = call_tts(text, title, lang)
        status = "✅" if ok else "❌"
        print(f"  {status} latency={lat:.1f}s, code={data.get('code')}, audio_length={data.get('audio_length',0)}ms")
        
        if ok and data.get("audio_url"):
            print(f"  audio_url: {data['audio_url'][:80]}...")
            print(f"  metadata_url: {data.get('metadata_url','N/A')[:80]}...")
        
        results.append({"name": name, "ok": ok, "latency": lat, "data": data})
    
    passed = sum(1 for r in results if r["ok"])
    print(f"\nPhase 1 结果: {passed}/{len(results)} 通过")
    return results


# ============================================================
# Phase 2: 完整性 - WER/漏词率
# ============================================================
def phase2_integrity():
    """英文+中文 WER 测试"""
    print("\n" + "=" * 60)
    print("Phase 2: 完整性测试 (WER/漏词率)")
    print("=" * 60)
    
    results = []
    tests = [
        ("EN Short", TEXTS["en_short"], "Test", 3, "en"),
        ("EN Medium", TEXTS["en_medium"], "Test", 3, "en"),
        ("ZH Short", TEXTS["zh_short"], "测试", 1, "zh"),
        ("ZH Medium", TEXTS["zh_medium"], "测试", 1, "zh"),
    ]
    
    for name, text, title, lang, asr_lang in tests:
        print(f"\n[{name}] 合成中... ({len(text)} chars)")
        ok, lat, data = call_tts(text, title, lang)
        if not ok:
            print(f"  ❌ 合成失败: {data}")
            results.append({"name": name, "ok": False})
            continue
        
        print(f"  ✅ 合成完成 ({lat:.1f}s), 下载音频...")
        audio_path = download_audio(data["audio_url"])
        
        print(f"  Whisper 转写中...")
        wer_result = transcribe_and_wer(audio_path, text, asr_lang)
        print(f"  WER: {wer_result['wer']}%, 语言: {wer_result['language']}")
        
        results.append({"name": name, "ok": True, "latency": lat, "wer": wer_result["wer"], "audio_length_ms": data["audio_length"]})
    
    print(f"\nPhase 2 结果:")
    for r in results:
        if r["ok"]:
            print(f"  {r['name']}: WER={r['wer']}%, latency={r['latency']:.1f}s")
        else:
            print(f"  {r['name']}: FAILED")
    return results


# ============================================================
# Phase 3: 吞吐率
# ============================================================
def phase3_throughput(concurrency=8, duration_minutes=5):
    """吞吐率测试"""
    print("\n" + "=" * 60)
    print(f"Phase 3: 吞吐率测试 (并发={concurrency}, 时长={duration_minutes}min)")
    print("=" * 60)
    
    text = TEXTS["en_medium"]
    completed = 0
    failed = 0
    latencies = []
    lock = threading.Lock()
    start_time = time.time()
    end_time = start_time + duration_minutes * 60
    
    def worker():
        nonlocal completed, failed
        while time.time() < end_time:
            ok, lat, data = call_tts(text, "Throughput Test", 3)
            with lock:
                if ok:
                    completed += 1
                    latencies.append(lat)
                else:
                    failed += 1
    
    print(f"  启动 {concurrency} 个并发 worker...")
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(worker) for _ in range(concurrency)]
        # 每分钟打印进度
        while time.time() < end_time:
            time.sleep(60)
            elapsed = (time.time() - start_time) / 60
            with lock:
                print(f"  [{elapsed:.0f}min] 完成={completed}, 失败={failed}, 吞吐率≈{completed/elapsed*60:.0f}/h")
        for f in as_completed(futures):
            f.result()
    
    actual_hours = (time.time() - start_time) / 3600
    throughput = completed / actual_hours if actual_hours > 0 else 0
    
    result = {
        "concurrency": concurrency,
        "duration_minutes": duration_minutes,
        "completed": completed,
        "failed": failed,
        "throughput_per_hour": round(throughput),
        "avg_latency": round(statistics.mean(latencies), 1) if latencies else 0,
        "p95_latency": round(sorted(latencies)[int(len(latencies)*0.95)], 1) if latencies else 0,
        "p99_latency": round(sorted(latencies)[int(len(latencies)*0.99)], 1) if latencies else 0,
    }
    
    print(f"\nPhase 3 结果:")
    print(f"  完成任务: {completed}")
    print(f"  失败任务: {failed}")
    print(f"  吞吐率: {result['throughput_per_hour']} 任务/小时")
    print(f"  平均延迟: {result['avg_latency']}s")
    print(f"  P95延迟: {result['p95_latency']}s")
    print(f"  P99延迟: {result['p99_latency']}s")
    return result


# ============================================================
# Phase 4: 稳定性 - 大批量成功率
# ============================================================
def phase4_stability(total_tasks=100, concurrency=8):
    """大批量任务成功率统计"""
    print("\n" + "=" * 60)
    print(f"Phase 4: 稳定性测试 (总任务={total_tasks}, 并发={concurrency})")
    print("=" * 60)
    
    text = TEXTS["en_medium"]
    results = {"success": 0, "fail": 0, "errors": Counter(), "latencies": []}
    lock = threading.Lock()
    
    def do_task(task_id):
        ok, lat, data = call_tts(text, f"Stability {task_id}", 3)
        with lock:
            if ok:
                results["success"] += 1
                results["latencies"].append(lat)
            else:
                results["fail"] += 1
                results["errors"][data.get("msg", data.get("error", "unknown"))] += 1
        return ok
    
    task_ids = list(range(total_tasks))
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {executor.submit(do_task, i): i for i in task_ids}
        for i, f in enumerate(as_completed(futures)):
            if (i + 1) % 10 == 0:
                with lock:
                    print(f"  进度: {i+1}/{total_tasks}, 成功={results['success']}, 失败={results['fail']}")
    
    total = results["success"] + results["fail"]
    success_rate = results["success"] / total * 100 if total > 0 else 0
    
    print(f"\nPhase 4 结果:")
    print(f"  总任务: {total}")
    print(f"  成功: {results['success']} ({success_rate:.1f}%)")
    print(f"  失败: {results['fail']} ({100-success_rate:.1f}%)")
    if results["latencies"]:
        print(f"  平均延迟: {statistics.mean(results['latencies']):.1f}s")
        print(f"  P95延迟: {sorted(results['latencies'])[int(len(results['latencies'])*0.95)]:.1f}s")
    if results["errors"]:
        print(f"  错误分布: {dict(results['errors'].most_common(5))}")
    
    return {"total": total, "success_rate": round(success_rate, 2), **results}


# ============================================================
# Phase 5: 中英文对比
# ============================================================
def phase5_lang_compare():
    """中英文吞吐率+WER对比"""
    print("\n" + "=" * 60)
    print("Phase 5: 中英文对比")
    print("=" * 60)
    
    results = {}
    for lang_name, text, lang in [("EN", TEXTS["en_medium"], 3), ("ZH", TEXTS["zh_medium"], 1)]:
        print(f"\n[{lang_name}] 合成+WER...")
        ok, lat, data = call_tts(text, f"Compare {lang_name}", lang)
        if not ok:
            print(f"  ❌ 失败")
            results[lang_name] = {"ok": False}
            continue
        
        audio_path = download_audio(data["audio_url"])
        asr_lang = "en" if lang == 3 else "zh"
        wer_result = transcribe_and_wer(audio_path, text, asr_lang)
        
        results[lang_name] = {
            "ok": True,
            "latency": round(lat, 1),
            "audio_length_ms": data["audio_length"],
            "wer": wer_result["wer"],
            "text_length": len(text)
        }
        print(f"  ✅ latency={lat:.1f}s, WER={wer_result['wer']}%, audio={data['audio_length']}ms")
    
    return results


# ============================================================
# 主入口
# ============================================================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="TTS 完整测试")
    parser.add_argument("--phase", default="all", choices=["1","2","3","4","5","all"],
                        help="执行阶段: 1=冒烟 2=WER 3=吞吐率 4=稳定性 5=中英文对比 all=全部")
    parser.add_argument("--concurrency", type=int, default=8, help="并发数")
    parser.add_argument("--duration", type=int, default=5, help="吞吐率测试时长(分钟)")
    parser.add_argument("--tasks", type=int, default=100, help="稳定性测试任务数")
    args = parser.parse_args()
    
    all_results = {
        "test_time": datetime.now().isoformat(),
        "model": MODEL,
        "voice": VOICE,
        "url": URL,
    }
    
    if args.phase in ("1", "all"):
        all_results["phase1_smoke"] = phase1_smoke()
    
    if args.phase in ("2", "all"):
        all_results["phase2_integrity"] = phase2_integrity()
    
    if args.phase in ("3", "all"):
        all_results["phase3_throughput"] = phase3_throughput(args.concurrency, args.duration)
    
    if args.phase in ("4", "all"):
        all_results["phase4_stability"] = phase4_stability(args.tasks, args.concurrency)
    
    if args.phase in ("5", "all"):
        all_results["phase5_lang_compare"] = phase5_lang_compare()
    
    # 保存报告
    report_path = os.path.join(OUTPUT_DIR, f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n{'='*60}")
    print(f"  全部测试完成！报告: {report_path}")
    print(f"{'='*60}")
