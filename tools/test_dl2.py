import requests, urllib3
urllib3.disable_warnings()

# 先调API
resp = requests.post('http://ai-audiobook-api-none-new-dev.changdu.ltd/api/tts/synthesize', json={
    'read_content': 'Hello world test.',
    'chapter_title': 'Test',
    'model': 'higgs',
    'voice': 'audiobook_female_2',
    'lang': 3
}, timeout=120, verify=False)
data = resp.json()
print(f"code={data['code']}")
print(f"audio_url={data['audio_url']}")

# 立即下载
resp2 = requests.get(data['audio_url'], timeout=30, verify=False)
print(f"Download: HTTP {resp2.status_code}, size={len(resp2.content)} bytes")
