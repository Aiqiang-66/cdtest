import json, os

# 查看 TTS API 响应
json_path = r'd:\python\dmx\cdtest\docs\需求文档\听书测试物料\mp3\23c6a2d3.json'
with open(json_path, 'r') as f:
    data = json.load(f)

print("=== TTS API 响应 ===")
print(f"Type: {type(data).__name__}")
if isinstance(data, list):
    print(f"Length: {len(data)}")
    print(f"First item: {data[0] if data else 'empty'}")
    if len(data) > 0 and isinstance(data[0], dict):
        print(f"Keys: {list(data[0].keys())}")
else:
    print(f"code: {data.get('code')}")
    print(f"msg: {data.get('msg')}")
    print(f"audio_url: {data.get('audio_url', 'N/A')[:120]}")
    print(f"audio_length: {data.get('audio_length')} ms")
    print(f"metadata_url: {data.get('metadata_url', 'N/A')[:120]}")

# 查看 SRT 文件
srt_path = r'd:\python\dmx\cdtest\docs\需求文档\听书测试物料\srt文件\23c6a2d3.srt'
if os.path.exists(srt_path):
    with open(srt_path, 'r', encoding='utf-8') as f:
        srt = f.read()
    print(f"\n=== SRT 文件 ({len(srt)} chars) ===")
    print(srt[:800])

# 查看 json2srt 脚本
script_path = r'd:\python\dmx\cdtest\docs\需求文档\听书测试物料\文本转srt脚本\json2srt.py'
if os.path.exists(script_path):
    with open(script_path, 'r', encoding='utf-8') as f:
        script = f.read()
    print(f"\n=== json2srt.py ===")
    print(script[:1500])
