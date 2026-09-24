import os
"""TTS 测试：英语完整章节 → 生产环境 → 下载 MP3"""
import json,hashlib,hmac,base64,time,requests
from pathlib import Path

import os

_TTS_KEY = os.environ.get("TTS_SECRET_KEY")
if not _TTS_KEY:
    raise SystemExit(
        "缺少环境变量 TTS_SECRET_KEY（测试环境密钥，请勿写入代码；设置后重试，例如：\n"
        "  在 PowerShell 里先设置环境变量 TTS_SECRET_KEY（值由项目统一管理）后再运行")

SECRET_KEY=os.environ["TTS_SECRET_KEY"]
BASE_URL='https://ai-main-none.changdu.vip'
OUT=Path(r'd:\python\dmx\cdtest\docs\听书测试物料\mp3\0730_tts_test')
OUT.mkdir(parents=True,exist_ok=True)

text=Path(r'd:\python\dmx\cdtest\docs\听书测试物料\txt文本\EN-英语.txt').read_text(encoding='utf-16')
print(f'文本长度: {len(text)} 字符')

def sign(t):
    h=hmac.new(SECRET_KEY.encode(),t.encode(),hashlib.sha256)
    return base64.b64encode(h.digest()).decode()

def signed_post(url,payload,timeout=30):
    body=json.dumps(payload)
    headers={'sign':sign(body),'Content-Type':'application/json'}
    return requests.post(url,data=body.encode(),headers=headers,timeout=timeout)

ext={
    'read_content':text,
    'chapter_title':'EN_Chapter1',
    'model':'f5tts',
    'lang':3,
    'voice':'audiobook_female_2',
    'speed':1.0,
    'volume':1.0,
    'cos_path':'',
}
payload={'ext':json.dumps(ext),'taskType':74,'priority':0,'retry_times':1,'cool_time':600}

print('创建任务...')
r=signed_post(f'{BASE_URL}/Video/CreateUniversalTransparent',payload)
resp=r.json()
print(f'code={resp["code"]}, taskId={resp["data"]}')
task_id=resp['data']

print('等待完成...')
deadline=time.time()+600
result={}
while time.time()<deadline:
    time.sleep(5)
    p2={'taskType':74,'taskIds':[task_id]}
    r2=signed_post(f'{BASE_URL}/Task/GetAllTaskStatus',p2)
    data=r2.json().get('data',[])
    info=data[0] if data else {}
    status=info.get('taskStatus')
    progress=info.get('progress','-')
    elapsed=int(time.time()-deadline+600)
    print(f'  [{elapsed}s] status={status}, progress={progress}')
    if status==2:
        print('任务完成!')
        result=info
        break
    elif status==3:
        print(f'任务失败: {info.get("comment","")}')
        result=info
        break
else:
    print('超时')

(OUT/'task_result.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
print(f'结果已保存: {OUT}/task_result.json')

# 下载MP3
cos_path=result.get('cosPath','') or result.get('cos_path','') or result.get('resultUrl','')
print(f'cosPath: {cos_path}')
if cos_path:
    mp3_url=cos_path if cos_path.startswith('http') else f'https://{cos_path}'
    print(f'下载: {mp3_url}')
    try:
        mp3=requests.get(mp3_url,timeout=60)
        if mp3.status_code==200:
            (OUT/'output.mp3').write_bytes(mp3.content)
            print(f'MP3已保存: {OUT}/output.mp3 ({len(mp3.content)} bytes)')
        else:
            print(f'下载失败: {mp3.status_code}')
    except Exception as e:
        print(f'下载异常: {e}')
else:
    print('完整result字段:')
    for k,v in result.items():
        print(f'  {k}: {str(v)[:300]}')
