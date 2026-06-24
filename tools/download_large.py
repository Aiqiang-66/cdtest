"""下载 faster-whisper large-v3 模型（中文识别更好）"""
import requests, os, time, urllib3
urllib3.disable_warnings()

MODEL = "Systran/faster-whisper-large-v3"
BASE_URL = f"https://hf-mirror.com/{MODEL}/resolve/main"
TARGET_DIR = r"d:\python\dmx\cdtest\tools\whisper_models\models--Systran--faster-whisper-large-v3\snapshots\large-v3"
os.makedirs(TARGET_DIR, exist_ok=True)

FILES = [
    "config.json",
    "tokenizer.json",
    "model.bin",
    "vocabulary.txt",
    "preprocessor_config.json",
]

for filename in FILES:
    url = f"{BASE_URL}/{filename}"
    target = os.path.join(TARGET_DIR, filename)
    
    if os.path.exists(target):
        size_mb = os.path.getsize(target) / 1024 / 1024
        print(f"[SKIP] {filename} ({size_mb:.1f} MB)")
        continue
    
    print(f"[DOWNLOAD] {filename} ...")
    headers = {}
    incomplete = target + ".incomplete"
    existing = os.path.getsize(incomplete) if os.path.exists(incomplete) else 0
    if existing > 0:
        headers["Range"] = f"bytes={existing}-"
        print(f"  Resuming from {existing/1024/1024:.1f} MB")
    
    session = requests.Session()
    retries = 0
    while retries < 10:
        try:
            resp = session.get(url, headers=headers, stream=True, timeout=60, verify=False)
            if resp.status_code in (200, 206):
                total = existing + int(resp.headers.get("content-length", 0))
                downloaded = existing
                mode = "ab" if existing > 0 else "wb"
                with open(incomplete, mode) as f:
                    for chunk in resp.iter_content(chunk_size=1024*1024):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total > 0:
                                print(f"\r  {downloaded/1024/1024:.1f} / {total/1024/1024:.1f} MB ({downloaded/total*100:.0f}%)", end="")
                os.rename(incomplete, target)
                print(f"\n[OK] {filename} ({os.path.getsize(target)/1024/1024:.1f} MB)")
                break
            else:
                print(f"\n[ERR] HTTP {resp.status_code}")
                retries += 1
                time.sleep(5)
        except Exception as e:
            retries += 1
            print(f"\n[RETRY {retries}/10] {e}")
            time.sleep(10)
            if os.path.exists(incomplete):
                existing = os.path.getsize(incomplete)
                headers["Range"] = f"bytes={existing}-"

print("\nDone!")
for f in FILES:
    path = os.path.join(TARGET_DIR, f)
    if os.path.exists(path):
        print(f"  [OK] {f} ({os.path.getsize(path)/1024/1024:.1f} MB)")
    else:
        print(f"  [MISS] {f}")
