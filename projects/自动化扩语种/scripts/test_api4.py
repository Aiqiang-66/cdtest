import requests
import json
import os

# 获取Token
token = os.environ.get('API_TOKEN', '')

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json',
    'Referer': 'https://sc-test.changdu.ltd/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# 测试扩语种API
print("=== 测试扩语种API ===")

# 1. 获取选择项 (POST)
url1 = "https://adassetserver-cn-new-dev.changdu.ltd/api/AIMixedClip/Task/GetSelectItems"
r1 = requests.post(url1, headers=headers, timeout=30)
print(f"GetSelectItems Status: {r1.status_code}")
print(f"Response: {r1.text[:1000]}")

# 2. 获取标签 (POST)
print("\n=== 获取标签 ===")
url2 = "https://adassetserver-cn-new-dev.changdu.ltd/api/Common/GetTags"
r2 = requests.post(url2, headers=headers, timeout=30)
print(f"GetTags Status: {r2.status_code}")
print(f"Response: {r2.text[:1000]}")

# 3. 获取代号信息 (POST)
print("\n=== 获取代号信息 ===")
url3 = "https://adassetserver-cn-new-dev.changdu.ltd/api/Common/GetTgtCodeInfo"
r3 = requests.post(url3, headers=headers, timeout=30)
print(f"GetTgtCodeInfo Status: {r3.status_code}")
print(f"Response: {r3.text[:1000]}")
