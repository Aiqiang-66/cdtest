"""
pyset 全语言测试：用 en 模型切分所有语言文本
对比：API / 换行 / pysbd / pyset(en降级)
"""
import json,time,re,requests
from pathlib import Path
from pysbd import Segmenter
from pyset import TokenBoundaryDetector

SENTENCE_URL='https://cuda-merge-server-audiobook.changdu.vip/sentence_spliter'
TXT=Path(r'd:\python\dmx\cdtest\docs\听书测试物料\txt文本')
OUT=Path(r'd:\python\dmx\cdtest\docs\听书测试物料\mp3\0730_切句对比_pyset全语言')
OUT.mkdir(parents=True,exist_ok=True)

def split_by_api(text,lang_code):
    try:
        r=requests.post(SENTENCE_URL,json={'text':text,'language_code':lang_code},timeout=30)
        elapsed=r.elapsed.total_seconds()
        if r.status_code==200:
            return r.json().get('sentences',[]), elapsed, lang_code
        else:
            r2=requests.post(SENTENCE_URL,json={'text':text,'language_code':'en'},timeout=30)
            elapsed2=r2.elapsed.total_seconds()
            if r2.status_code==200:
                return r2.json().get('sentences',[]), elapsed2, 'en(fallback)'
    except Exception as e:
        print(f'    API异常: {e}')
    return [],0,lang_code

def split_by_newline(text):
    return [p.strip() for p in text.split('\n') if p.strip()]

def split_by_pysbd(text,lang_code):
    pysbd_lang_map={'en':'en','de':'de','ru':'ru','es':'es','fr':'fr','pt':'en'}
    use_lang=pysbd_lang_map.get(lang_code,'en')
    t0=time.time()
    try:
        seg=Segmenter(language=use_lang,clean=False)
        sents=[s.strip() for s in seg.segment(text) if s.strip()]
        return sents, time.time()-t0, use_lang
    except:
        return [], time.time()-t0, use_lang

def split_by_pyset(text):
    t0=time.time()
    try:
        detector=TokenBoundaryDetector(language="en")
        sents=[s.strip() for s in detector.split(text) if s.strip()]
        return sents, time.time()-t0
    except Exception as e:
        print(f'    pyset异常: {e}')
        return [], time.time()-t0

def stats(parts):
    if not parts: return 0,0,0,0
    cnt=len(parts)
    avg=sum(len(p) for p in parts)/cnt
    return cnt,avg,min(len(p) for p in parts),max(len(p) for p in parts)

configs=[
    ('EN-英语.txt',              None, '英语', 'en', 'utf-16'),
    ('德语-Sein Verrat machte mich zur Milliardärsgattin.txt', r'#Chapter\d+\s+No\.\d+', '德语', 'de', 'utf-8'),
    ('俄语-Молниеносный брак с отцом моей лучшей подруги.txt', r'#Chapter\d+\s+\d+', '俄语', 'ru', 'utf-8'),
    ('西语-Matrimonio relámpago con el padre de mi mejor amiga.txt', r'#Chapter\d+\s+\d+', '西语', 'es', 'utf-8'),
    ('葡语-Casamento Relâmpago com o Pai da Minha Melhor Amiga.txt', r'#Chapter\d+\s+\d+', '葡语', 'pt', 'utf-8'),
    ('法语-Mariage éclair avec le père de ma meilleure amie.txt', r'#Chapter\d+\s+\d+', '法语', 'fr', 'utf-8'),
]

all_results=[]

for fname,pat,cn_name,lang_code,encoding in configs:
    text=(TXT/fname).read_text(encoding=encoding)
    
    if pat is None:
        chapters=[(None,0,len(text))]
    else:
        chapters_list=list(re.finditer(pat,text))
        chapters=[(m.group(0),m.end(),chapters_list[i+1].start() if i+1<len(chapters_list) else len(text)) for i,m in enumerate(chapters_list[:10])]
    
    for ch_num,start,end in chapters:
        content=text[start:end].strip()
        if len(content)<100: continue
        
        label=f'{cn_name}_Ch{ch_num}'
        
        # 1. API
        api_sents,api_elapsed,used_code=split_by_api(content,lang_code)
        api_cnt,api_avg,api_min,api_max=stats(api_sents)
        
        # 2. 换行符
        t0=time.time()
        nl_parts=split_by_newline(content)
        nl_time=time.time()-t0
        nl_cnt,nl_avg,nl_min,nl_max=stats(nl_parts)
        
        # 3. pysbd
        pysbd_sents,pysbd_time,pysbd_lang=split_by_pysbd(content,lang_code)
        pysbd_cnt,pysbd_avg,pysbd_min,pysbd_max=stats(pysbd_sents)
        
        # 4. pyset (全部用en)
        pyset_sents,pyset_time=split_by_pyset(content)
        pyset_cnt,pyset_avg,pyset_min,pyset_max=stats(pyset_sents)
        
        # 保存
        (OUT/f'{label}_api.txt').write_text('\n'.join(api_sents) if api_sents else content,encoding='utf-8')
        (OUT/f'{label}_newline.txt').write_text('\n'.join(nl_parts),encoding='utf-8')
        (OUT/f'{label}_pysbd.txt').write_text('\n'.join(pysbd_sents) if pysbd_sents else content,encoding='utf-8')
        (OUT/f'{label}_pyset.txt').write_text('\n'.join(pyset_sents) if pyset_sents else content,encoding='utf-8')
        
        print(f'[{cn_name}] 第{ch_num}章 ({len(content)}字符)')
        print(f'  API:    {api_cnt:>4}句, 均长{api_avg:>5.0f}字, 耗时{api_elapsed:>6.3f}s, 句长{api_min}-{api_max}')
        print(f'  换行:   {nl_cnt:>4}段, 均长{nl_avg:>5.0f}字, 耗时{nl_time:>6.3f}s, 段长{nl_min}-{nl_max}')
        print(f'  pysbd:  {pysbd_cnt:>4}句, 均长{pysbd_avg:>5.0f}字, 耗时{pysbd_time:>6.3f}s, 句长{pysbd_min}-{pysbd_max}')
        print(f'  pyset:  {pyset_cnt:>4}句, 均长{pyset_avg:>5.0f}字, 耗时{pyset_time:>6.3f}s, 句长{pyset_min}-{pyset_max}')
        
        all_results.append({
            'lang':cn_name,'ch':ch_num,'chars':len(content),
            'api_cnt':api_cnt,'api_avg':api_avg,'api_time':api_elapsed,'api_min':api_min,'api_max':api_max,
            'nl_cnt':nl_cnt,'nl_avg':nl_avg,'nl_time':nl_time,'nl_min':nl_min,'nl_max':nl_max,
            'pysbd_cnt':pysbd_cnt,'pysbd_avg':pysbd_avg,'pysbd_time':pysbd_time,'pysbd_min':pysbd_min,'pysbd_max':pysbd_max,
            'pyset_cnt':pyset_cnt,'pyset_avg':pyset_avg,'pyset_time':pyset_time,'pyset_min':pyset_min,'pyset_max':pyset_max,
        })

# 汇总
print('\n'+'='*150)
print('汇总：API vs 换行 vs pysbd vs pyset（全语言，pyset用en降级）')
print('='*150)
print(f'{"语言":6s} {"章":20s} {"字符":>7s} | {"API":>5s} {"均长":>5s} {"耗时":>7s} {"范围":>12s} | {"换行":>5s} {"均长":>5s} {"耗时":>7s} {"范围":>12s} | {"pysbd":>5s} {"均长":>5s} {"耗时":>7s} {"范围":>12s} | {"pyset":>5s} {"均长":>5s} {"耗时":>7s} {"范围":>12s}')
print('-'*150)
for r in all_results:
    print(f'{r["lang"]:6s} {str(r["ch"] or ""):20s} {r["chars"]:>7,} | {r["api_cnt"]:>5} {r["api_avg"]:>5.0f} {r["api_time"]:>6.3f}s {r["api_min"]}-{r["api_max"]:>4} | {r["nl_cnt"]:>5} {r["nl_avg"]:>5.0f} {r["nl_time"]:>6.3f}s {r["nl_min"]}-{r["nl_max"]:>4} | {r["pysbd_cnt"]:>5} {r["pysbd_avg"]:>5.0f} {r["pysbd_time"]:>6.3f}s {r["pysbd_min"]}-{r["pysbd_max"]:>4} | {r["pyset_cnt"]:>5} {r["pyset_avg"]:>5.0f} {r["pyset_time"]:>6.3f}s {r["pyset_min"]}-{r["pyset_max"]:>4}')

# 按语言汇总
print('\n--- 按语言汇总 ---')
for lang_name in ['英语','德语','俄语','西语','葡语','法语']:
    lr=[r for r in all_results if r['lang']==lang_name]
    if not lr: continue
    n=len(lr)
    print(f'\n{lang_name} ({n}章):')
    api_ok=[r for r in lr if r['api_cnt']>0]
    if api_ok:
        print(f'  API:    均{sum(r["api_cnt"] for r in api_ok)/len(api_ok):.0f}句, 均长{sum(r["api_avg"] for r in api_ok)/len(api_ok):.0f}字, 均耗时{sum(r["api_time"] for r in api_ok)/len(api_ok):.3f}s')
    print(f'  换行:   均{sum(r["nl_cnt"] for r in lr)/n:.0f}段, 均长{sum(r["nl_avg"] for r in lr)/n:.0f}字, 均耗时{sum(r["nl_time"] for r in lr)/n:.4f}s')
    pysbd_ok=[r for r in lr if r['pysbd_cnt']>0]
    if pysbd_ok:
        print(f'  pysbd:  均{sum(r["pysbd_cnt"] for r in pysbd_ok)/len(pysbd_ok):.0f}句, 均长{sum(r["pysbd_avg"] for r in pysbd_ok)/len(pysbd_ok):.0f}字, 均耗时{sum(r["pysbd_time"] for r in pysbd_ok)/len(pysbd_ok):.4f}s')
    pyset_ok=[r for r in lr if r['pyset_cnt']>0]
    if pyset_ok:
        print(f'  pyset:  均{sum(r["pyset_cnt"] for r in pyset_ok)/len(pyset_ok):.0f}句, 均长{sum(r["pyset_avg"] for r in pyset_ok)/len(pyset_ok):.0f}字, 均耗时{sum(r["pyset_time"] for r in pyset_ok)/len(pyset_ok):.4f}s (en降级)')

print(f'\n输出目录: {OUT}')
