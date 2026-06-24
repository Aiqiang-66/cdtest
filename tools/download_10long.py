"""
10个长文本TTS任务下载
文案: 从两个txt文件提取的10个不重叠片段 (3000-4000字符/段)
并发: 8, 输出: mp3目录
"""
import time, requests, urllib3, threading, json, os, re
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

# 生成10个不重叠的3000-4000字符片段
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

print(f"=" * 60)
print(f"  10个长文本 TTS 任务")
print(f"  文案段数: {len(chunks)}, 每段 3000-4000 字符")
print(f"  输出目录: {OUTPUT_DIR}")
print(f"=" * 60)

# 提交任务
def submit_task(chunk_text, idx):
    """提交TTS任务，返回task_id"""
    resp = requests.post(URL, json={
        "read_content": chunk_text,
        "chapter_title": f"LongText-{idx+1:02d}",
        "model": "higgs",
        "voice": "audiobook_female_2",
        "lang": 3
    }, timeout=600, verify=False)
    data = resp.json()
    if data.get("code") == 0:
        return data["audio_url"], data["metadata_url"]
    else:
        raise Exception(f"API error: {data}")

def download_file(url, save_path, retries=5):
    """下载文件，带重试"""
    for attempt in range(retries):
        try:
            resp = requests.get(url, timeout=120, verify=False)
            if resp.status_code == 200:
                with open(save_path, "wb") as f:
                    f.write(resp.content)
                return len(resp.content)
            else:
                print(f"    HTTP {resp.status_code}, retry {attempt+1}/{retries}")
        except Exception as e:
            print(f"    Error: {e}, retry {attempt+1}/{retries}")
        time.sleep(3)
    return 0

def process_one(idx, chunk_text):
    """处理单个任务: 提交 -> 等待 -> 下载"""
    t0 = time.time()
    try:
        audio_url, meta_url = submit_task(chunk_text, idx)
        submit_time = time.time() - t0
        
        # 提取task_id
        task_id = audio_url.split("/")[-1].replace(".mp3", "")
        
        # 下载音频
        t1 = time.time()
        mp3_path = os.path.join(OUTPUT_DIR, f"{task_id}.mp3")
        mp3_size = download_file(audio_url, mp3_path)
        dl_time = time.time() - t1
        
        # 下载metadata
        t2 = time.time()
        json_path = os.path.join(OUTPUT_DIR, f"{task_id}.json")
        json_size = download_file(meta_url, json_path)
        
        # 保存源文本
        source_path = os.path.join(OUTPUT_DIR, f"{task_id}_source.txt")
        with open(source_path, "w", encoding="utf-8") as f:
            f.write(chunk_text)
        
        total_time = time.time() - t0
        return {
            "idx": idx + 1,
            "task_id": task_id,
            "mp3_kb": round(mp3_size / 1024),
            "total_s": round(total_time, 1),
            "submit_s": round(submit_time, 1),
            "chars": len(chunk_text),
            "success": True
        }
    except Exception as e:
        return {
            "idx": idx + 1,
            "task_id": "FAILED",
            "error": str(e)[:100],
            "success": False
        }

print(f"\n开始 {CONCURRENCY} 并发下载 {len(chunks)} 个任务...")

results = []
with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
    futures = {executor.submit(process_one, i, chunks[i]): i for i in range(len(chunks))}
    for f in as_completed(futures):
        r = f.result()
        results.append(r)
        if r["success"]:
            print(f"  ✅ 任务{r['idx']:02d}: {r['task_id']} | {r['mp3_kb']}KB | {r['total_s']}s | {r['submit_s']}s | {r['chars']}chars")
        else:
            print(f"  ❌ 任务{r['idx']:02d}: {r['error']}")

results.sort(key=lambda x: x["idx"])

success_count = sum(1 for r in results if r["success"])
fail_count = len(results) - success_count
total_time = max(r.get("total_s", 0) for r in results) if results else 0

print(f"\n{'=' * 60}")
print(f"  下载完成!")
print(f"  成功: {success_count}/{len(chunks)}, 失败: {fail_count}")
print(f"  总耗时: {total_time:.0f}s")
print(f"{'=' * 60}")

# 保存映射表
manifest = []
for r in results:
    if r["success"]:
        manifest.append({
            "idx": r["idx"],
            "task_id": r["task_id"],
            "mp3_file": f"{r['task_id']}.mp3",
            "json_file": f"{r['task_id']}.json",
            "source_file": f"{r['task_id']}_source.txt",
            "chars": r["chars"],
            "mp3_kb": r["mp3_kb"]
        })

manifest_path = os.path.join(OUTPUT_DIR, "_manifest_long.json")
with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)
print(f"映射表: {manifest_path}")
