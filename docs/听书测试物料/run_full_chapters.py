"""整章发送：德语5章 + 俄语5章，共10个任务，文件名中文标注"""
import re, json, requests
from pathlib import Path

API = 'http://ai-audiobook-api-none-new-dev.changdu.ltd/api/tts/synthesize'
OUT = Path(r'd:\python\dmx\cdtest\docs\需求文档\听书测试物料\mp3')
TXT = Path(r'd:\python\dmx\cdtest\docs\需求文档\听书测试物料\txt文本')

configs = [
    ('20000 Leagues Under the Sea - 德语.txt', r'KAPITEL\s+[IVXLCDM]+', 1, 'German_female', '德语'),
    ('20000 Leagues Under the Sea - 俄语.txt', r'ГЛАВА\s+[IVXLCDM]+', 1, 'Russian_female', '俄语'),
]

for fname, pat, lang, voice, cn_name in configs:
    text = (TXT / fname).read_text(encoding='utf-8')
    matches = list(re.finditer(pat, text))
    print(f'\n{"="*50}')
    print(f'{cn_name}: {len(matches)} 章')
    print(f'{"="*50}')

    for i, m in enumerate(matches):
        title = m.group().strip()
        start = m.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        content = text[start:end].strip()
        ch_num = title.split()[-1]  # I, II, III...
        label = f'{cn_name}_第{ch_num}章'
        print(f'\n[{i+1}/{len(matches)}] {label} ({len(content)} 字符, ~{len(content.split())} 词)')

        resp = requests.post(API, json={
            'read_content': content,
            'chapter_title': title,
            'model': 'higgs', 'lang': lang, 'voice': voice,
        }, timeout=900)
        d = resp.json()
        if d.get('code') != 0:
            print(f'  失败: {d}')
            continue
        print(f'  合成成功: {d["audio_length"]/1000:.1f}s')

        # mp3
        r = requests.get(d['audio_url'], timeout=120)
        (OUT / f'{label}.mp3').write_bytes(r.content)
        print(f'  [OK] {label}.mp3 ({len(r.content)} bytes)')

        # json + srt
        r = requests.get(d['metadata_url'], timeout=120)
        (OUT / f'{label}.json').write_bytes(r.content)
        segs = json.loads(r.text)
        lines = []
        for s in segs:
            idx = s.get('id', 0) + 1
            sm = s.get('startMs', 0); em = s.get('endMs', 0)
            t = s.get('text', '').strip()
            if not t: continue
            def fms(ms):
                h=ms//3600000; m=(ms%3600000)//60000; sec=(ms%60000)//1000
                return f'{h:02d}:{m:02d}:{sec:02d},{ms%1000:03d}'
            lines.append(str(idx)); lines.append(f'{fms(sm)} --> {fms(em)}')
            lines.append(t); lines.append('')
        (OUT / f'{label}.srt').write_text('\n'.join(lines), encoding='utf-8')
        print(f'  [OK] {label}.srt ({len([l for l in lines if l and l[0].isdigit()])} 条)')

print('\n全部完成!')
