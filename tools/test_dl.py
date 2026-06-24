import requests

url = 'https://reader-audio-1382266829.cos.ap-hongkong.myqcloud.com/audiobook/67f709a3.mp3'
resp = requests.get(url, timeout=30)
print(f"Status: {resp.status_code}")
print(f"Content-Type: {resp.headers.get('Content-Type')}")
print(f"Content-Length: {resp.headers.get('Content-Length')}")
print(f"Body length: {len(resp.content)}")
print(f"First 100 bytes: {resp.content[:100]}")

# 保存
with open(r"d:\python\dmx\cdtest\tools\test_output\test_dl.mp3", "wb") as f:
    f.write(resp.content)
print(f"Saved: {len(resp.content)} bytes")
