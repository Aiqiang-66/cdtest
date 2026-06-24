import requests
import json
import os

# 获取Token
token = os.environ.get('API_TOKEN', '')

headers = {
    'Authorization': f'Bearer {token}',
    'Referer': 'https://sc-test.changdu.ltd/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# 测试上传视频
print("=== 测试上传视频 ===")

video_path = r"D:\spy\C4\海剧\X2035\X2035$EN$时尚$热门$916$.mp4"
filename = os.path.basename(video_path)

# 尝试上传到AIMixedClip API
url = "https://adassetserver-cn-new-dev.changdu.ltd/api/AIMixedClip/Task/UploadVideo"

try:
    with open(video_path, 'rb') as f:
        files = {'file': (filename, f, 'video/mp4')}
        r = requests.post(url, files=files, headers=headers, timeout=120)
        print(f"UploadVideo Status: {r.status_code}")
        print(f"Response: {r.text[:1000]}")
except Exception as e:
    print(f"Error: {e}")

# 尝试其他上传API
print("\n=== 尝试其他上传API ===")
url2 = "https://adassetserver-cn-new-dev.changdu.ltd/api/AIMixedClip/Upload"
try:
    with open(video_path, 'rb') as f:
        files = {'file': (filename, f, 'video/mp4')}
        r2 = requests.post(url2, files=files, headers=headers, timeout=120)
        print(f"Upload Status: {r2.status_code}")
        print(f"Response: {r2.text[:1000]}")
except Exception as e:
    print(f"Error: {e}")
