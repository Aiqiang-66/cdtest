import requests
import json
import os

# 获取Token
token = os.environ.get('API_TOKEN', '')

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json',
    'Referer': 'https://sc-test.changdu.ltd/',
}

# 测试扩语种API
print("=== 测试扩语种API ===")

# 尝试上传文件
url = "https://adassetserver-cn-new-test1.changdu.ltd/api/AIMixedClipTask/UploadVideo"

# 读取视频文件
video_path = r"D:\spy\C4\海剧\X2035\X2035$EN$时尚$热门$916$.mp4"

try:
    with open(video_path, 'rb') as f:
        files = {'file': (video_path.split('\\')[-1], f, 'video/mp4')}
        r = requests.post(url, files=files, headers=headers, timeout=60)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text[:500]}")
except Exception as e:
    print(f"Error: {e}")

# 尝试其他API
print("\n=== 尝试其他API ===")
url2 = "https://adassetserver-cn-new-test1.changdu.ltd/api/AIMixedClipTask/GetTaskList"
r2 = requests.get(url2, headers=headers, timeout=30)
print(f"Status: {r2.status_code}")
print(f"Response: {r2.text[:500]}")
