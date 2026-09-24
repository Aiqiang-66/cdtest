"""
XR3切句对比测试 v2：保存接口原始返回JSON + 耗时
每个章节保存3个文件：
- xxx_raw.json: 接口原始返回 {"sentences":[...], "elapsed":xxx}
- xxx_model.txt: 模型切句结果（\n拼接）
- xxx_newline.txt: \n分段结果（\n拼接）
"""
import json,time,re,requests
from pathlib import Path

SENTENCE_URL='https://cuda-merge-server-audiobook.changdu.vip/sentence_spliter'
TXT=Path(r'd:\python\dmx\cdtest\docs\听书测试物料\txt文本')
OUT=Path(r'd:\python\dmx\cdtest\docs\听书测试物料\mp3\0730_切句对比')
OUT.mkdir(parents=True,exist_ok=True)

LANG_MAP={1:'zh',2:'zh',3:'en',4:'es',5:'pt',6:'fr',7:'ru',16:'de'}

def split_by_model(text,lang_code):
    code=LANG_MAP.get(lang_code,'en')
    used_code=code
    if code!='en': used_code='en'
    try:
        r=requests.post(SENTENCE_URL,json={'text':text,'language_code':used_code},timeout=30)
        elapsed=r.elapsed.total_seconds()
        if r.status_code==200:
            data=r.json()
            return data.get('sentences',[]), elapsed, used_code
    except Exception as e:
        print(f'    切句异常: {e}')
    return None,0,used_code

def split_by_newline(text):
    return [p.strip() for p in text.split('\n') if p.strip()]

configs=[
    ('XR3 - EN.txt',r'\[(\d+)\]',1,'英语','en'),
    ('XR3 - DE.txt',r'\[(\d+)\]',1,'德语','de'),
    ('XR3 - RU.txt',r'\[(\d+)\]',1,'俄语','ru'),
    ('XR3 - SP.txt',r'\[(\d+)\]',4,'西语','es'),
    ('XR3 - PT.txt',r'\[(\d+)\]',5,'葡语','pt'),
    ('XR3 - FR.txt',r'\[(\d+)\]',6,'法语','fr'),
]

all_results=[]

for fname,pat,lang,cn_name,lang_code in configs:
    text=(TXT/fname).read_text(encoding='utf-8')
    chapters=list(re.finditer(pat,text))
    
    for i in range(min(10,len(chapters))):
        m=chapters[i]
        ch_num=m.group(1)
        start=m.end()
        end=chapters[i+1].start() if i+1<len(chapters) else len(text)
        content=text[start:end].strip()
        if len(content)<100: continue
        
        model_sents,model_time,used_code=split_by_model(content,lang)
        newline_parts=split_by_newline(content)
        
        label=f'{cn_name}_Ch{ch_num}'
        
        # 保存接口原始返回JSON
        raw_data={
            'language_code':used_code,
            'elapsed':model_time,
            'sentences':model_sents if model_sents else [],
            'sentence_count':len(model_sents) if model_sents else 0,
        }
        (OUT/f'{label}_raw.json').write_text(json.dumps(raw_data,indent=2,ensure_ascii=False),encoding='utf-8')
        
        # 保存模型切句txt
        model_joined='\n'.join(model_sents) if model_sents else content
        (OUT/f'{label}_model.txt').write_text(model_joined,encoding='utf-8')
        
        # 保存换行分段txt
        newline_joined='\n'.join(newline_parts)
        (OUT/f'{label}_newline.txt').write_text(newline_joined,encoding='utf-8')
        
        if model_sents:
            model_count=len(model_sents)
            model_avg=sum(len(s) for s in model_sents)/model_count
            model_lens=[len(s) for s in model_sents]
        else:
            model_count=0; model_avg=0; model_lens=[]
        
        newline_count=len(newline_parts)
        newline_avg=sum(len(p) for p in newline_parts)/newline_count if newline_parts else 0
        newline_lens=[len(p) for p in newline_parts]
        
        print(f'[{cn_name}] 第{ch_num}章 ({len(content)}字符) code={used_code}')
        print(f'  模型切句: {model_count}句, 均长{model_avg:.0f}字, 耗时{model_time:.3f}s')
        print(f'  换行分段: {newline_count}段, 均长{newline_avg:.0f}字')
        print(f'  模型句长范围: {min(model_lens)}-{max(model_lens)}' if model_lens else '  模型句长: N/A')
        print(f'  换行段长范围: {min(newline_lens)}-{max(newline_lens)}')
        
        all_results.append({
            'lang':cn_name,'ch':ch_num,'chars':len(content),'used_code':used_code,
            'model_count':model_count,'model_avg':model_avg,'model_time':model_time,
            'model_min':min(model_lens) if model_lens else 0,'model_max':max(model_lens) if model_lens else 0,
            'nl_count':newline_count,'nl_avg':newline_avg,
            'nl_min':min(newline_lens),'nl_max':max(newline_lens),
        })

print('\n'+'='*90)
print('汇总：XR3切句对比测试（接口原始返回）')
print('='*90)
print(f'{"语言":6s} {"章":4s} {"code":5s} {"字符":>6s} {"模型句数":>6s} {"均长":>5s} {"耗时":>7s} {"句长范围":>12s} {"换行段数":>6s} {"均长":>5s} {"段长范围":>12s}')
print('-'*95)
for r in all_results:
    ml_range=f'{r["model_min"]}-{r["model_max"]}' if r['model_count']>0 else 'N/A'
    nl_range=f'{r["nl_min"]}-{r["nl_max"]}'
    print(f'{r["lang"]:6s} {r["ch"]:4s} {r["used_code"]:5s} {r["chars"]:>6,} {r["model_count"]:>6} {r["model_avg"]:>5.0f} {r["model_time"]:>6.3f}s {ml_range:>12s} {r["nl_count"]:>6} {r["nl_avg"]:>5.0f} {nl_range:>12s}')

print('\n--- 按语言汇总 ---')
for lang_name in ['英语','德语','俄语','西语','葡语','法语']:
    lr=[r for r in all_results if r['lang']==lang_name]
    if lr:
        avg_mc=sum(r['model_count'] for r in lr)/len(lr)
        avg_nc=sum(r['nl_count'] for r in lr)/len(lr)
        avg_mt=sum(r['model_time'] for r in lr)/len(lr)
        avg_ma=sum(r['model_avg'] for r in lr)/len(lr)
        avg_na=sum(r['nl_avg'] for r in lr)/len(lr)
        print(f'{lang_name}: 均{avg_mc:.0f}句(均长{avg_ma:.0f}字), 均{avg_nc:.0f}段(均长{avg_na:.0f}字), 均耗时{avg_mt:.3f}s')

print(f'\n输出目录: {OUT}')
print('文件格式: _raw.json(接口原始返回), _model.txt(模型切句), _newline.txt(换行分段)')
