"""
下发22和23两个爆音SRT的英文文案TTS任务并下载
"""
import time, requests, urllib3, json, os
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings()

URL = "http://ai-audiobook-api-none-new-dev.changdu.ltd/api/tts/synthesize"
OUTPUT_DIR = r"d:\python\dmx\cdtest\docs\需求文档\听书测试物料\mp3"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 读取文案
with open(r"d:\python\dmx\cdtest\tools\temp_text22.txt", "r", encoding="utf-8") as f:
    text22 = f.read()
with open(r"d:\python\dmx\cdtest\tools\temp_text23.txt", "r", encoding="utf-8") as f:
    text23 = f.read()

tasks = [
    ("22-爆音", text22),
    ("23-爆音", text23),
]

print(f"=" * 60)
print(f"  下发2个爆音SRT文案TTS任务")
print(f"  22: {len(text22)} chars, 23: {len(text23)} chars")
print(f"=" * 60)

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

def process_one(label, text):
    t0 = time.time()
    try:
        resp = requests.post(URL, json={
            "read_content": text,
            "chapter_title": label,
            "model": "higgs",
            "voice": "audiobook_female_2",
            "lang": 3
        }, timeout=600, verify=False)
        data = resp.json()
        if data.get("code") != 0:
            return {"label": label, "success": False, "error": data.get("msg", "unknown")}
        
        audio_url = data["audio_url"]
        meta_url = data["metadata_url"]
        task_id = audio_url.split("/")[-1].replace(".mp3", "")
        submit_time = time.time() - t0
        
        # 下载音频
        t1 = time.time()
        mp3_path = os.path.join(OUTPUT_DIR, f"{task_id}.mp3")
        mp3_size = download_file(audio_url, mp3_path)
        
        # 下载metadata
        json_path = os.path.join(OUTPUT_DIR, f"{task_id}.json")
        download_file(meta_url, json_path)
        
        # 保存源文本
        source_path = os.path.join(OUTPUT_DIR, f"{task_id}_source.txt")
        with open(source_path, "w", encoding="utf-8") as f:
            f.write(text)
        
        total_time = time.time() - t0
        return {
            "label": label,
            "task_id": task_id,
            "mp3_kb": round(mp3_size / 1024),
            "total_s": round(total_time, 1),
            "submit_s": round(submit_time, 1),
            "chars": len(text),
            "success": True
        }
    except Exception as e:
        return {"label": label, "success": False, "error": str(e)[:100]}

results = []
with ThreadPoolExecutor(max_workers=2) as executor:
    futures = {executor.submit(process_one, label, text): label for label, text in tasks}
    for f in as_completed(futures):
        r = f.result()
        results.append(r)
        if r["success"]:
            print(f"  ✅ {r['label']}: {r['task_id']} | {r['mp3_kb']}KB | {r['total_s']}s | {r['chars']}chars")
        else:
            print(f"  ❌ {r['label']}: {r['error']}")

print(f"\n完成! 成功: {sum(1 for r in results if r['success'])}/2")
