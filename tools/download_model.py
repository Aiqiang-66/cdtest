"""下载 faster-whisper 模型文件（支持断点续传）"""
import requests, os, time, sys

# 禁用 SSL 警告
import urllib3
urllib3.disable_warnings()

MODEL_REPO = "Systran/faster-whisper-base"
BASE_URL = f"https://hf-mirror.com/{MODEL_REPO}/resolve/main"
SNAPSHOT = "d01c3014881c9c6f3133c182f3d2887eb6ca1c789a7538c5c007196857a0a6a9"
TARGET_DIR = rf"d:\python\dmx\cdtest\tools\whisper_models\models--Systran--faster-whisper-base\snapshots\{SNAPSHOT}"

FILES = [
    "config.json",
    "tokenizer.json", 
    "model.bin",
    "vocabulary.txt",
    "preprocessor_config.json",
]

os.makedirs(TARGET_DIR, exist_ok=True)

for filename in FILES:
    url = f"{BASE_URL}/{filename}"
    target = os.path.join(TARGET_DIR, filename)
    
    # 检查是否已存在
    if os.path.exists(target):
        size_mb = os.path.getsize(target) / 1024 / 1024
        print(f"[SKIP] {filename} ({size_mb:.1f} MB) - already exists")
        continue
    
    print(f"[DOWNLOAD] {filename} ...")
    
    # 断点续传
    headers = {}
    existing_size = 0
    incomplete = target + ".incomplete"
    if os.path.exists(incomplete):
        existing_size = os.path.getsize(incomplete)
        headers["Range"] = f"bytes={existing_size}-"
        print(f"  Resuming from {existing_size/1024/1024:.1f} MB")
    
    # 下载
    session = requests.Session()
    retries = 0
    max_retries = 10
    
    while retries < max_retries:
        try:
            resp = session.get(url, headers=headers, stream=True, timeout=30, verify=False)
            
            if resp.status_code in (200, 206):
                total = existing_size + int(resp.headers.get("content-length", 0))
                downloaded = existing_size
                
                mode = "ab" if existing_size > 0 else "wb"
                with open(incomplete, mode) as f:
                    for chunk in resp.iter_content(chunk_size=1024*1024):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            pct = downloaded / total * 100 if total > 0 else 0
                            print(f"\r  {downloaded/1024/1024:.1f} / {total/1024/1024:.1f} MB ({pct:.0f}%)", end="")
                
                # 下载完成，重命名
                os.rename(incomplete, target)
                print(f"\n[OK] {filename} ({os.path.getsize(target)/1024/1024:.1f} MB)")
                break
            else:
                print(f"\n[ERR] HTTP {resp.status_code}")
                retries += 1
                time.sleep(5)
                
        except Exception as e:
            retries += 1
            print(f"\n[RETRY {retries}/{max_retries}] {e}")
            time.sleep(10)
            # 更新断点
            if os.path.exists(incomplete):
                existing_size = os.path.getsize(incomplete)
                headers["Range"] = f"bytes={existing_size}-"
    
    if retries >= max_retries:
        print(f"\n[FAIL] {filename} - max retries exceeded")

print("\nDone! Checking files...")
for f in FILES:
    path = os.path.join(TARGET_DIR, f)
    if os.path.exists(path):
        print(f"  [OK] {f} ({os.path.getsize(path)/1024/1024:.1f} MB)")
    else:
        print(f"  [MISS] {f}")
