"""
通用TTS任务下发+下载脚本 (higgs模型)
- 自动json转srt
- 按序号重命名: N.mp3, N.srt, N_source.txt
"""
import time, requests, urllib3, json, os, re, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings()

URL = "http://ai-audiobook-api-none-new-dev.changdu.ltd/api/tts/synthesize"
OUTPUT_DIR = r"d:\python\dmx\cdtest\docs\需求文档\听书测试物料\mp3"
JSON2SRT = r"d:\python\dmx\cdtest\docs\需求文档\听书测试物料\文本转srt脚本\json2srt.py"
CONCURRENCY = 8
MODEL = "higgs"
VOICE = "audiobook_female_2"
LANG = 3

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# 文案来源: 章节 + 爆音
# ============================================================
path2 = r"d:\python\dmx\cdtest\docs\需求文档\听书测试物料\txt文本\His Unwanted Wife_ The Genius Artist Returns.txt"
with open(path2, "r", encoding="utf-8") as f:
    text2 = f.read()

# 按章节分割
chapters = re.split(r'\n\s*Chapter\s+(\d+)\s*\n', text2)
chapter_texts = {}
for i in range(1, len(chapters)-1, 2):
    ch_num = int(chapters[i])
    chapter_texts[ch_num] = chapters[i+1].strip()

# 取 Chapter 11-15 五个章节
chunks = []
for ch in [11, 12, 13, 14, 15]:
    if ch in chapter_texts:
        chunks.append(chapter_texts[ch])

# 添加爆音文案
with open(r"d:\python\dmx\cdtest\tools\temp_text22.txt", "r", encoding="utf-8") as f:
    chunks.append(f.read())
with open(r"d:\python\dmx\cdtest\tools\temp_text23.txt", "r", encoding="utf-8") as f:
    chunks.append(f.read())

print(f"=" * 60)
print(f"  {MODEL.upper()} TTS 批量任务下发")
print(f"  共 {len(chunks)} 段, 并发: {CONCURRENCY}")
print(f"=" * 60)

# ============================================================
# 工具函数
# ============================================================
def download_file(url, save_path, retries=5):
    for attempt in range(retries):
        try:
            resp = requests.get(url, timeout=120, verify=False)
            if resp.status_code == 200:
                with open(save_path, "wb") as f:
                    f.write(resp.content)
                return len(resp.content)
        except Exception as e:
            print(f"    Download retry {attempt+1}/{retries}: {e}")
        time.sleep(3)
    return 0

def json_to_srt(json_path):
    """内置转换，不依赖外部脚本"""
    srt_path = json_path.replace(".json", ".srt")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            segments = json.load(f)
        lines = []
        for seg in segments:
            idx = seg.get("id", 0) + 1
            start_ms = seg["startMs"]
            end_ms = seg["endMs"]
            h1, m1 = divmod(start_ms, 3600000); m1, s1 = divmod(m1, 60000); s1, ms1 = divmod(s1, 1000)
            h2, m2 = divmod(end_ms, 3600000); m2, s2 = divmod(m2, 60000); s2, ms2 = divmod(s2, 1000)
            start_ts = f"{h1:02d}:{m1:02d}:{s1:02d},{ms1:03d}"
            end_ts = f"{h2:02d}:{m2:02d}:{s2:02d},{ms2:03d}"
            text = seg.get("text", "").strip()
            if not text:
                continue
            lines.append(f"{idx}")
            lines.append(f"{start_ts} --> {end_ts}")
            lines.append(text)
            lines.append("")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return srt_path
    except Exception as e:
        print(f"    SRT转换失败: {e}")
        return None

def get_next_index():
    """获取下一个可用序号"""
    existing = []
    for f in os.listdir(OUTPUT_DIR):
        m = re.match(r'^(\d+)\.(mp3|srt|json)$', f)
        if m:
            existing.append(int(m.group(1)))
        m = re.match(r'^(\d+)_source\.txt$', f)
        if m:
            existing.append(int(m.group(1)))
    return max(existing) + 1 if existing else 1

# ============================================================
# 处理单个任务
# ============================================================
def process_one(idx, chunk_text):
    t0 = time.time()
    label = f"22-爆音" if idx == 5 else ("23-爆音" if idx == 6 else f"Chapter-{11+idx}")
    try:
        resp = requests.post(URL, json={
            "read_content": chunk_text,
            "chapter_title": label,
            "model": MODEL,
            "voice": VOICE,
            "lang": LANG
        }, timeout=600, verify=False)
        data = resp.json()
        if data.get("code") != 0:
            return {"idx": idx+1, "label": label, "success": False, "error": data.get("msg", "unknown")}
        
        audio_url = data["audio_url"]
        meta_url = data["metadata_url"]
        task_id = audio_url.split("/")[-1].replace(".mp3", "")
        submit_time = time.time() - t0
        
        # 下载到临时文件
        tmp_mp3 = os.path.join(OUTPUT_DIR, f"_tmp_{task_id}.mp3")
        tmp_json = os.path.join(OUTPUT_DIR, f"_tmp_{task_id}.json")
        mp3_size = download_file(audio_url, tmp_mp3)
        download_file(meta_url, tmp_json)
        
        # JSON转SRT
        tmp_srt = json_to_srt(tmp_json)
        
        # 获取序号并重命名
        seq = get_next_index()
        final_mp3 = os.path.join(OUTPUT_DIR, f"{seq}.mp3")
        final_srt = os.path.join(OUTPUT_DIR, f"{seq}.srt")
        final_txt = os.path.join(OUTPUT_DIR, f"{seq}_source.txt")
        
        os.rename(tmp_mp3, final_mp3)
        if tmp_srt:
            os.rename(tmp_srt, final_srt)
        os.remove(tmp_json)  # 删除json，只保留srt
        
        # 保存源文本
        with open(final_txt, "w", encoding="utf-8") as f:
            f.write(chunk_text)
        
        total_time = time.time() - t0
        return {
            "idx": idx+1, "label": label, "seq": seq,
            "mp3_kb": round(mp3_size/1024), "total_s": round(total_time,1),
            "chars": len(chunk_text), "success": True
        }
    except Exception as e:
        return {"idx": idx+1, "label": label, "success": False, "error": str(e)[:100]}

# ============================================================
# 执行
# ============================================================
print(f"\n开始 {CONCURRENCY} 并发下载...")

results = []
with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
    futures = {executor.submit(process_one, i, chunks[i]): i for i in range(len(chunks))}
    for f in as_completed(futures):
        r = f.result()
        results.append(r)
        if r["success"]:
            print(f"  ✅ {r['label']} -> {r['seq']}.mp3/.srt/_source.txt | {r['mp3_kb']}KB | {r['total_s']}s")
        else:
            print(f"  ❌ {r['label']}: {r['error']}")

results.sort(key=lambda x: x["idx"])
success_count = sum(1 for r in results if r["success"])

print(f"\n{'=' * 60}")
print(f"  完成! 成功: {success_count}/{len(chunks)}")
print(f"  文件格式: N.mp3 / N.srt / N_source.txt")
print(f"{'=' * 60}")
