"""
30个不重复英文长文本 TTS 任务，下载音频+metadata 到 mp3 目录
"""
import json, os, time, requests, urllib3, threading
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings()

URL = "http://ai-audiobook-api-none-new-dev.changdu.ltd/api/tts/synthesize"
OUTPUT_DIR = r"d:\python\dmx\cdtest\docs\需求文档\听书测试物料\mp3"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 生成30个不重叠文案
path1 = r"d:\python\dmx\cdtest\docs\需求文档\听书测试物料\txt文本\8FA4C02F-DE32-4569-908E-DF05A9715BD8.txt"
path2 = r"d:\python\dmx\cdtest\docs\需求文档\听书测试物料\txt文本\His Unwanted Wife_ The Genius Artist Returns.txt"
with open(path1, "r", encoding="utf-16") as f: text1 = f.read()
with open(path2, "r", encoding="utf-8") as f: text2 = f.read()
full = text1 + "\n\n" + text2

sentences = full.replace("?",".").replace("!",".").split(".")
sentences = [s.strip() + "." for s in sentences if s.strip()]

chunks = []
i = 0
while i < len(sentences) and len(chunks) < 30:
    chunk = ""
    start_i = i
    while i < len(sentences) and len(chunk) + len(sentences[i]) < 2800:
        chunk += sentences[i] + " "
        i += 1
    if len(chunk) >= 1800:
        chunks.append(chunk.strip())
    else:
        i = start_i + 1

print("=" * 60)
print(f"  30个不重复英文长文本 TTS 任务")
print(f"  文案段数: {len(chunks)}, 每段 1800-2800 字符")
print(f"  输出目录: {OUTPUT_DIR}")
print("=" * 60)

# 保存文案映射
manifest = {}
for idx, chunk in enumerate(chunks):
    manifest[idx] = {"chars": len(chunk), "words": len(chunk.split()), "preview": chunk[:80]}

results = []
lock = threading.Lock()

def download_task(task_id, read_content):
    t0 = time.time()
    try:
        resp = requests.post(URL, json={
            "read_content": read_content,
            "chapter_title": f"CrossCheck {task_id+1}",
            "model": "higgs",
            "voice": "audiobook_female_2",
            "lang": 3
        }, timeout=600, verify=False)
        
        if resp.status_code != 200:
            return {"task_id": task_id, "status": "fail", "error": f"HTTP {resp.status_code}"}
        data = resp.json()
        if data.get("code") != 0:
            return {"task_id": task_id, "status": "fail", "error": data.get("msg","unknown")}
        
        audio_url = data["audio_url"]
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
        if data.get("metadata_url"):
            r2 = requests.get(data["metadata_url"], timeout=30, verify=False)
            if r2.status_code == 200:
                with open(meta_path, "w", encoding="utf-8") as f:
                    f.write(r2.text)
        
        # 保存原文
        txt_path = os.path.join(OUTPUT_DIR, f"{task_hash}_source.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(read_content)
        
        latency = time.time() - t0
        return {
            "task_id": task_id, "status": "ok", "hash": task_hash,
            "audio_kb": len(r.content)/1024, "audio_s": data["audio_length"]/1000,
            "latency_s": round(latency,1), "chars": len(read_content)
        }
    except Exception as e:
        return {"task_id": task_id, "status": "fail", "error": str(e)}

print(f"\n开始 8 并发下载 {len(chunks)} 个任务...")
t0 = time.time()
with ThreadPoolExecutor(max_workers=8) as executor:
    futures = {executor.submit(download_task, i, chunks[i]): i for i in range(len(chunks))}
    for f in as_completed(futures):
        r = f.result()
        with lock:
            results.append(r)
            if r["status"] == "ok":
                print(f"  ✅ 任务{r['task_id']+1:02d}: {r['hash']} | {r['audio_kb']:.0f}KB | {r['audio_s']:.0f}s | {r['latency_s']}s | {r['chars']}chars")
            else:
                print(f"  ❌ 任务{r['task_id']+1:02d}: {r['error']}")

elapsed = time.time() - t0
ok = [r for r in results if r["status"]=="ok"]
fail = [r for r in results if r["status"]!="ok"]

print(f"\n{'='*60}")
print(f"  下载完成!")
print(f"  成功: {len(ok)}/{len(chunks)}, 失败: {len(fail)}")
print(f"  总耗时: {elapsed:.0f}s")
print(f"{'='*60}")

# 保存映射表
manifest_path = os.path.join(OUTPUT_DIR, "_manifest.json")
manifest_data = {"total": len(chunks), "success": len(ok), "failed": len(fail), "tasks": {}}
for r in results:
    if r["status"] == "ok":
        manifest_data["tasks"][r["hash"]] = {
            "task_id": r["task_id"] + 1,
            "audio_kb": round(r["audio_kb"], 0),
            "audio_s": round(r["audio_s"], 0),
            "latency_s": r["latency_s"],
            "chars": r["chars"],
            "source_file": f"{r['hash']}_source.txt"
        }
with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(manifest_data, f, ensure_ascii=False, indent=2)
print(f"\n映射表: {manifest_path}")
