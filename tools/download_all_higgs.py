"""
从txt文本文件夹的两个文件提取文案，用higgs模型下发TTS任务并下载
包含: 10个长文本(3000-4000字符) + 2个爆音文案
"""
import time, requests, urllib3, json, os, re
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings()

URL = "http://ai-audiobook-api-none-new-dev.changdu.ltd/api/tts/synthesize"
OUTPUT_DIR = r"d:\python\dmx\cdtest\docs\需求文档\听书测试物料\mp3"
CONCURRENCY = 8

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 加载两个txt文件
path1 = r"d:\python\dmx\cdtest\docs\需求文档\听书测试物料\txt文本\8FA4C02F-DE32-4569-908E-DF05A9715BD8.txt"
path2 = r"d:\python\dmx\cdtest\docs\需求文档\听书测试物料\txt文本\His Unwanted Wife_ The Genius Artist Returns.txt"

with open(path1, "r", encoding="utf-16") as f:
    text1 = f.read()
with open(path2, "r", encoding="utf-8") as f:
    text2 = f.read()

full = text1 + "\n\n" + text2

# 按句子分割
sentences = full.replace('?', '.').replace('!', '.').split('.')
sentences = [s.strip() + '.' for s in sentences if s.strip()]

# 生成10个不重叠的3000-4000字符长文本片段
chunks = []
i = 0
while i < len(sentences) and len(chunks) < 10:
    chunk = ''
    start_i = i
    while i < len(sentences) and len(chunk) + len(sentences[i]) < 4000:
        chunk += sentences[i] + ' '
        i += 1
    if len(chunk) >= 3000:
        chunks.append(chunk.strip())
    else:
        i = start_i + 1

# 添加两个爆音文案
with open(r"d:\python\dmx\cdtest\tools\temp_text22.txt", "r", encoding="utf-8") as f:
    chunks.append(f.read())
with open(r"d:\python\dmx\cdtest\tools\temp_text23.txt", "r", encoding="utf-8") as f:
    chunks.append(f.read())

print(f"=" * 60)
print(f"  Higgs TTS v3 批量任务下发")
print(f"  长文本: 10段, 爆音: 2段, 共 {len(chunks)} 段")
print(f"  输出目录: {OUTPUT_DIR}")
print(f"=" * 60)

for j, c in enumerate(chunks):
    label = f"22-爆音" if j == 10 else ("23-爆音" if j == 11 else f"Chunk-{j+1:02d}")
    print(f"  [{label}] {len(c)} chars, {len(c.split())} words")

def download_file(url, save_path, retries=5):
    for attempt in range(retries):
        try:
            resp = requests.get(url, timeout=120, verify=False)
            if resp.status_code == 200:
                with open(save_path, "wb") as f:
                    f.write(resp.content)
                return len(resp.content)
        except Exception as e:
            print(f"    Error: {e}, retry {attempt+1}/{retries}")
        time.sleep(3)
    return 0

def process_one(idx, chunk_text):
    t0 = time.time()
    label = f"22-爆音" if idx == 10 else ("23-爆音" if idx == 11 else f"Chunk-{idx+1:02d}")
    try:
        resp = requests.post(URL, json={
            "read_content": chunk_text,
            "chapter_title": label,
            "model": "higgs",
            "voice": "audiobook_female_2",
            "lang": 3
        }, timeout=600, verify=False)
        data = resp.json()
        if data.get("code") != 0:
            return {"idx": idx+1, "label": label, "success": False, "error": data.get("msg", "unknown")}
        
        audio_url = data["audio_url"]
        meta_url = data["metadata_url"]
        task_id = audio_url.split("/")[-1].replace(".mp3", "")
        submit_time = time.time() - t0
        
        # 下载音频
        mp3_path = os.path.join(OUTPUT_DIR, f"{task_id}.mp3")
        mp3_size = download_file(audio_url, mp3_path)
        
        # 下载metadata
        json_path = os.path.join(OUTPUT_DIR, f"{task_id}.json")
        download_file(meta_url, json_path)
        
        # 保存源文本
        source_path = os.path.join(OUTPUT_DIR, f"{task_id}_source.txt")
        with open(source_path, "w", encoding="utf-8") as f:
            f.write(chunk_text)
        
        total_time = time.time() - t0
        return {
            "idx": idx+1, "label": label, "task_id": task_id,
            "mp3_kb": round(mp3_size/1024), "total_s": round(total_time,1),
            "submit_s": round(submit_time,1), "chars": len(chunk_text), "success": True
        }
    except Exception as e:
        return {"idx": idx+1, "label": label, "success": False, "error": str(e)[:100]}

print(f"\n开始 {CONCURRENCY} 并发下载 {len(chunks)} 个任务...")

results = []
with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
    futures = {executor.submit(process_one, i, chunks[i]): i for i in range(len(chunks))}
    for f in as_completed(futures):
        r = f.result()
        results.append(r)
        if r["success"]:
            print(f"  ✅ {r['label']}: {r['task_id']} | {r['mp3_kb']}KB | {r['total_s']}s | {r['chars']}chars")
        else:
            print(f"  ❌ {r['label']}: {r['error']}")

results.sort(key=lambda x: x["idx"])
success_count = sum(1 for r in results if r["success"])

print(f"\n{'=' * 60}")
print(f"  下载完成! 成功: {success_count}/{len(chunks)}")
print(f"{'=' * 60}")
