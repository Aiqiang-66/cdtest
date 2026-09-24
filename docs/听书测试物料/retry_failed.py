import os
"""补跑失败的3个任务：西语IV、葡语IV、法语I"""
import re, json, time, hashlib, hmac, base64, requests
from pathlib import Path

import os

_TTS_KEY = os.environ.get("TTS_SECRET_KEY")
if not _TTS_KEY:
    raise SystemExit(
        "缺少环境变量 TTS_SECRET_KEY（测试环境密钥，请勿写入代码；设置后重试，例如：\n"
        "  在 PowerShell 里先设置环境变量 TTS_SECRET_KEY（值由项目统一管理）后再运行")

SECRET_KEY = os.environ["TTS_SECRET_KEY"]
BASE = 'https://ai-main-none-dev.changdu.ltd'
OUT = Path(r'd:\python\dmx\cdtest\docs\需求文档\听书测试物料\mp3')
TXT = Path(r'd:\python\dmx\cdtest\docs\需求文档\听书测试物料\txt文本')

def sign(text):
    h = hmac.new(SECRET_KEY.encode(), text.encode(), hashlib.sha256)
    return base64.b64encode(h.digest()).decode()

def signed_post(url, payload, timeout=30):
    body = json.dumps(payload)
    headers = {'sign': sign(body), 'Content-Type': 'application/json'}
    return requests.post(url, data=body.encode(), headers=headers, timeout=timeout).json()

tasks = [
    ('20000 Leagues Under the Sea - French(法语).txt', r'(?:^|\n)(CHAPITRE\s+(?:PREMIER|[IVXLCDM]+))', 6, 'French_female', '法语', 0),
]

for fname, pat, lang, voice, cn_name, ch_idx in tasks:
    text = (TXT / fname).read_text(encoding='utf-8')
    matches = list(re.finditer(pat, text))
    m = matches[ch_idx]
    title = m.group().strip()
    start = m.end()
    end = matches[ch_idx+1].start() if ch_idx+1 < len(matches) else len(text)
    content = text[start:end].strip()
    ch_num = ['I','II','III','IV','V'][ch_idx]
    label = f'{cn_name}_第{ch_num}章'
    print(f'[{label}] ({len(content)} 字符, ~{len(content.split())} 词)')

    ext = {'read_content': content, 'chapter_title': title, 'model': 'higgs', 'lang': lang, 'voice': voice}
    r = signed_post(f'{BASE}/Video/CreateUniversalTransparent', {'ext': json.dumps(ext), 'taskType': 74, 'priority': 0, 'retry_times': 1, 'cool_time': 600})
    if r.get('code') != 200:
        print(f'  创建失败: {r}')
        continue
    task_id = r['data']
    print(f'  taskId={task_id}')

    deadline = time.time() + 1200
    while time.time() < deadline:
        r = signed_post(f'{BASE}/Task/GetAllTaskStatus', {'taskType': 74, 'taskIds': [task_id]})
        info = r['data'][0] if r.get('data') else {}
        status = info.get('taskStatus')
        elapsed = int(time.time() - deadline + 1200)
        print(f'  [{elapsed}s] status={status}')
        if status == 2:
            break
        elif status == 3:
            print(f'  失败: {info.get("comment", "")}')
            break
        time.sleep(10)
    else:
        print('  超时')
        continue

    if status != 2:
        continue

    data = json.loads(info.get('data', '{}'))
    r = requests.get(data['audio_url'], timeout=180)
    (OUT / f'{label}.mp3').write_bytes(r.content)
    print(f'  [OK] {label}.mp3 ({len(r.content)} bytes)')

    r = requests.get(data['metadata_url'], timeout=180)
    (OUT / f'{label}.json').write_bytes(r.content)
    segs = json.loads(r.text)
    lines = []
    for s in segs:
        idx = s.get('id', 0) + 1
        sm, em = s.get('startMs', 0), s.get('endMs', 0)
        t = s.get('text', '').strip()
        if not t: continue
        def fms(ms):
            h=ms//3600000; m=(ms%3600000)//60000; sec=(ms%60000)//1000
            return f'{h:02d}:{m:02d}:{sec:02d},{ms%1000:03d}'
        lines.append(str(idx)); lines.append(f'{fms(sm)} --> {fms(em)}')
        lines.append(t); lines.append('')
    (OUT / f'{label}.srt').write_text('\n'.join(lines), encoding='utf-8')
    print(f'  [OK] {label}.srt ({len([l for l in lines if l and l[0].isdigit()])} 条)')
    print()

print('补跑完成!')
