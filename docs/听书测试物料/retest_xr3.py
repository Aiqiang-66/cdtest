import os
"""串行重测XR3第1章6语言"""
import hashlib,hmac,base64,json,time,re,requests

import os

_TTS_KEY = os.environ.get("TTS_SECRET_KEY")
if not _TTS_KEY:
    raise SystemExit(
        "缺少环境变量 TTS_SECRET_KEY（测试环境密钥，请勿写入代码；设置后重试，例如：\n"
        "  在 PowerShell 里先设置环境变量 TTS_SECRET_KEY（值由项目统一管理）后再运行")

DEV='https://ai-main-none-dev.changdu.ltd'
SK=os.environ["TTS_SECRET_KEY"]
def sign(t): return base64.b64encode(hmac.new(SK.encode(),t.encode(),hashlib.sha256).digest()).decode()
def sp(u,p):
    body=json.dumps(p)
    return requests.post(u,data=body.encode(),headers={'sign':sign(body),'Content-Type':'application/json'},timeout=60).json()

def test_one(label, content, lang, voice):
    tid=sp(f'{DEV}/Video/CreateUniversalTransparent',{'ext':json.dumps({'read_content':content,'chapter_title':'Ch1','model':'higgs','lang':lang,'voice':voice}),'taskType':74,'priority':0,'retry_times':1,'cool_time':600})['data']
    print(f'  taskId={tid}', end='', flush=True)
    st=time.time()
    while time.time()-st<1200:
        info=sp(f'{DEV}/Task/GetAllTaskStatus',{'taskType':74,'taskIds':[tid]})['data'][0]
        s=info.get('taskStatus')
        if s==2: break
        elif s==3: print(' FAIL'); return None
        time.sleep(5)
    elapsed=time.time()-st
    print(f' -> {elapsed:.1f}s')
    return elapsed

configs=[
    ('英语','XR3 - EN.txt',r'=== Chapter\s+1\b',1,'English_female'),
    ('德语','XR3 - DE.txt',r'=== Kapitel\s+1\b',1,'German_female'),
    ('俄语','XR3 - RU.txt',r'=== Глава\s+1\b',1,'Russian_female'),
    ('西语','XR3 - SP.txt',r'=== Capítulo\s+1\b',4,'Spanish_female'),
    ('葡语','XR3 - PT.txt',r'=== Capítulo\s+1\b',5,'Portuguese_female'),
    ('法语','XR3 - FR.txt',r'=== Chapitre\s+1\b',6,'French_female'),
]

results=[]
for cn_name,fname,pat,lang,voice in configs:
    text=open(r'd:\python\dmx\cdtest\docs\听书测试物料\txt文本\\'+fname,encoding='utf-8').read()
    m=re.search(pat,text)
    matches=list(re.finditer(pat,text))
    end=matches[1].start() if len(matches)>1 else len(text)
    content=text[m.end():end].strip()
    print(f'\n[{cn_name}] XR3第1章 ({len(content)}字符)')
    t=test_one(f'{cn_name}_XR3_Ch1',content,lang,voice)
    if t: results.append((cn_name,len(content),t))

print('\n' + '='*55)
print('汇总：XR3第1章 串行重测')
print('='*55)
print(f'{"排名":4s} {"语言":6s} {"字符数":>8s} {"耗时":>8s}')
print('-'*30)
for i,(cn_name,chars,t) in enumerate(sorted(results,key=lambda x:x[2])):
    print(f'{i+1:4d} {cn_name:6s} {chars:>8,} {t:>7.1f}s')
