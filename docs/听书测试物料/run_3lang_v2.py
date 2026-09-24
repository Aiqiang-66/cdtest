import os
"""重新跑西语/葡语/法语 各5章，共15个任务，检查淡入淡出问题"""
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

configs = [
    ('20000 Leagues Under the Sea - Spanish(西语).txt', r'(?:^|\n)(CAP[IÍ]TULO\s+\w+)', 4, 'Spanish_female', '西语'),
    ('20000 Leagues Under the Sea - Portuguese(葡语).txt', r'(?:^|\n)(CAP[IÍ]TULO\s+\w+)', 5, 'Portuguese_female', '葡语'),
    ('20000 Leagues Under the Sea - French(法语).txt', r'(?:^|\n)(CHAPITRE\s+(?:PREMIER|[IVXLCDM]+))', 6, 'French_female', '法语'),
]

total = 0
success = 0
for fname, pat, lang, voice, cn_name in configs:
    text = (TXT / fname).read_text(encoding='utf-8')
    matches = list(re.finditer(pat, text))
    print(f'\n{"="*50}')
    print(f'{cn_name}: {len(matches)} 章, 取前5章')
    print(f'{"="*50}')

    for i, m in enumerate(matches[:5]):
        title = m.group().strip()
        start = m.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        content = text[start:end].strip()
        ch_num = ['I','II','III','IV','V'][i]
        label = f'{cn_name}_第{ch_num}章'
        total += 1
        print(f'\n[{total}/15] {label} ({len(content)} 字符, ~{len(content.split())} 词)')

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
        lang_dir = OUT / cn_name
        lang_dir.mkdir(parents=True, exist_ok=True)
        (lang_dir / f'{label}.mp3').write_bytes(r.content)
        print(f'  [OK] {label}.mp3 ({len(r.content)} bytes)')

        r = requests.get(data['metadata_url'], timeout=180)
        (lang_dir / f'{label}.json').write_bytes(r.content)
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
        (lang_dir / f'{label}.srt').write_text('\n'.join(lines), encoding='utf-8')
        print(f'  [OK] {label}.srt ({len([l for l in lines if l and l[0].isdigit()])} 条)')
        success += 1

print(f'\n{"="*50}')
print(f'完成: {success}/{total} 成功')
