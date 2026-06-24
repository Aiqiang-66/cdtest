import requests
import json
import os

token = os.environ.get('API_TOKEN', '')

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json',
    'Referer': 'https://sc-test.changdu.ltd/',
}

# Test 1: GET burn resource list (via page API)
print("=== Test 1: GET /task/burn-resource (page) ===")
url = 'https://sc-test.changdu.ltd/task/burn-resource'
params = {'isEnabled': 1, 'pageIndex': 1, 'pageSize': 30, 'ratio': 916, 'resourceType': 1, 'tgtType': 2}
r = requests.get(url, params=params, headers=headers, allow_redirects=False)
print(f"Status: {r.status_code}")
print(f"Content-Type: {r.headers.get('Content-Type', 'N/A')}")
print(f"Location: {r.headers.get('Location', 'N/A')}")

# Test 2: POST BatchAdd watermark (asset server API)
print("\n=== Test 2: POST /api/BurnResourceTask/BatchAdd ===")
url2 = 'https://adassetserver-cn-new-test1.changdu.ltd/api/BurnResourceTask/BatchAdd'
body = {"resourceType": 1, "tgtType": 2, "ratios": [916, 45], "core": 1, "tgtIds": ["14583322"]}
r2 = requests.post(url2, json=body, headers=headers)
print(f"Status: {r2.status_code}")
print(f"Response: {r2.text[:500]}")
