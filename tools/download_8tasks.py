"""
8并发下载 TTS 音频+metadata，保存到 mp3 目录，按任务ID区分
"""
import json, os, time, requests, urllib3, threading
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings()

URL = "http://ai-audiobook-api-none-new-dev.changdu.ltd/api/tts/synthesize"
OUTPUT_DIR = r"d:\python\dmx\cdtest\docs\需求文档\听书测试物料\mp3"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 加载中文文本
txt_path = r"d:\python\dmx\cdtest\docs\需求文档\听书测试物料\txt文本\中文.txt"
with open(txt_path, "r", encoding="utf-8") as f:
    ZH_TEXT = f.read()

print("=" * 60)
print(f"  8并发下载 TTS 音频+metadata")
print(f"  中文文本: {len(ZH_TEXT)} 字符")
print(f"  输出目录: {OUTPUT_DIR}")
print("=" * 60)

results = []
lock = threading.Lock()

def download_task(task_id):
    """单个任务：调API → 下载音频+metadata"""
    t0 = time.time()
    try:
        # 调 TTS API
        resp = requests.post(URL, json={
            "read_content": ZH_TEXT,
            "chapter_title": f"人工审核{task_id}",
            "model": "higgs",
            "voice": "audiobook_female_2",
            "lang": 1
        }, timeout=600, verify=False)
        
        if resp.status_code != 200:
            return {"task_id": task_id, "status": "fail", "error": f"HTTP {resp.status_code}"}
        
        data = resp.json()
        if data.get("code") != 0:
            return {"task_id": task_id, "status": "fail", "error": data.get("msg", "unknown")}
        
        audio_url = data["audio_url"]
        metadata_url = data.get("metadata_url", "")
        task_hash = audio_url.split("/")[-1].replace(".mp3", "")
        
        # 下载音频
        for attempt in range(5):
            r = requests.get(audio_url, timeout=120, verify=False)
            if r.status_code == 200 and len(r.content) > 1000:
                break
            time.sleep(3)
        
        audio_path = os.path.join(OUTPUT_DIR, f"{task_hash}.mp3")
        with open(audio_path, "wb") as f:
            f.write(r.content)
        
        # 下载 metadata
        meta_path = os.path.join(OUTPUT_DIR, f"{task_hash}.json")
        if metadata_url:
            r2 = requests.get(metadata_url, timeout=30, verify=False)
            if r2.status_code == 200:
                with open(meta_path, "w", encoding="utf-8") as f:
                    f.write(r2.text)
        
        latency = time.time() - t0
        return {
            "task_id": task_id,
            "status": "ok",
            "hash": task_hash,
            "audio_size_kb": len(r.content) / 1024,
            "audio_length_s": data["audio_length"] / 1000,
            "latency_s": round(latency, 1)
        }
    except Exception as e:
        return {"task_id": task_id, "status": "fail", "error": str(e)}

print("\n开始 8 并发下载...")
t0 = time.time()
with ThreadPoolExecutor(max_workers=8) as executor:
    futures = {executor.submit(download_task, i): i for i in range(1, 9)}
    for f in as_completed(futures):
        r = f.result()
        with lock:
            results.append(r)
            if r["status"] == "ok":
                print(f"  ✅ 任务{r['task_id']}: {r['hash']} | {r['audio_size_kb']:.0f}KB | {r['audio_length_s']:.0f}s | {r['latency_s']}s")
            else:
                print(f"  ❌ 任务{r['task_id']}: {r['error']}")

elapsed = time.time() - t0

# 汇总
ok = [r for r in results if r["status"] == "ok"]
fail = [r for r in results if r["status"] != "ok"]

print(f"\n{'='*60}")
print(f"  下载完成!")
print(f"  成功: {len(ok)}/8, 失败: {len(fail)}")
print(f"  总耗时: {elapsed:.0f}s")
print(f"  文件保存在: {OUTPUT_DIR}")
print(f"{'='*60}")

# 列出文件
print("\n已下载文件:")
for f in sorted(os.listdir(OUTPUT_DIR)):
    path = os.path.join(OUTPUT_DIR, f)
    size = os.path.getsize(path)
    print(f"  {f} ({size/1024:.0f} KB)")
