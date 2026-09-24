import os
"""逐个串行测试500/1000词"""
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
    while time.time()-st<600:
        info=sp(f'{DEV}/Task/GetAllTaskStatus',{'taskType':74,'taskIds':[tid]})['data'][0]
        s=info.get('taskStatus')
        if s==2: break
        elif s==3: print(' FAIL'); return None
        time.sleep(5)
    elapsed=time.time()-st
    print(f' -> {elapsed:.1f}s')
    return elapsed

done={'英语':(19.7,63.1),'葡语':(26.4,None)}

configs=[
    ('德语','20000 Leagues Under the Sea - 德语.txt',r'KAPITEL\s+I\b',1,'German_female'),
    ('俄语','20000 Leagues Under the Sea - 俄语.txt',r'ГЛАВА\s+I\b',1,'Russian_female'),
    ('西语','20000 Leagues Under the Sea - Spanish(西语).txt',r'CAP[IÍ]TULO\s+I\b',4,'Spanish_female'),
    ('葡语','20000 Leagues Under the Sea - Portuguese(葡语).txt',r'CAP[IÍ]TULO\s+I\b',5,'Portuguese_female'),
    ('法语','20000 Leagues Under the Sea - French(法语).txt',r'CHAPITRE\s+II\b',6,'French_female'),
]

results={}
for cn_name,fname,pat,lang,voice in configs:
    text=open(r'd:\python\dmx\cdtest\docs\听书测试物料\txt文本\\'+fname,encoding='utf-8').read()
    matches=list(re.finditer(pat,text))
    for i,m in enumerate(matches):
        end=matches[i+1].start() if i+1<len(matches) else len(text)
        content=text[m.end():end].strip()
        if len(content)>1000:
            words=content.split()
            w500=' '.join(words[:500])
            w1000=' '.join(words[:1000])
            
            if cn_name not in done or done[cn_name][0] is None:
                print(f'\n[{cn_name}] 500词')
                t=test_one(f'{cn_name}_500',w500,lang,voice)
                results[(cn_name,'500')]=t
            else:
                results[(cn_name,'500')]=done[cn_name][0]
            
            if cn_name not in done or done[cn_name][1] is None:
                print(f'[{cn_name}] 1000词')
                t=test_one(f'{cn_name}_1000',w1000,lang,voice)
                results[(cn_name,'1000')]=t
            else:
                results[(cn_name,'1000')]=done[cn_name][1]
            break

print('\n' + '='*50)
print('汇总：500词/1000词 串行重测')
print('='*50)
print(f'{"语言":6s} {"500词":>8s} {"1000词":>8s}')
print('-'*30)
for cn_name in ['英语','德语','俄语','西语','葡语','法语']:
    t500=results.get((cn_name,'500'))
    t1000=results.get((cn_name,'1000'))
    print(f'{cn_name:6s} {f"{t500:.1f}s" if t500 else "N/A":>8s} {f"{t1000:.1f}s" if t1000 else "N/A":>8s}')
