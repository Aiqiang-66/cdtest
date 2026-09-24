import os
"""
同一本书同一章节（第II章），5种语言同时下发，对比生成耗时。
"""
import hashlib, hmac, base64, json, time, re, requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import os

_TTS_KEY = os.environ.get("TTS_SECRET_KEY")
if not _TTS_KEY:
    raise SystemExit(
        "缺少环境变量 TTS_SECRET_KEY（测试环境密钥，请勿写入代码；设置后重试，例如：\n"
        "  在 PowerShell 里先设置环境变量 TTS_SECRET_KEY（值由项目统一管理）后再运行")

DEV_BASE_URL = "https://ai-main-none-dev.changdu.ltd"
SECRET_KEY = os.environ["TTS_SECRET_KEY"]
TXT = Path(r'd:\python\dmx\cdtest\docs\听书测试物料\txt文本')
OUT = Path(r'd:\python\dmx\cdtest\docs\听书测试物料\mp3\0724_同章多语言')
OUT.mkdir(parents=True, exist_ok=True)
POLL_INTERVAL = 5
POLL_TIMEOUT = 1200

def sign(text: str) -> str:
    h = hmac.new(SECRET_KEY.encode(), text.encode(), hashlib.sha256)
    return base64.b64encode(h.digest()).decode()

def signed_post(url: str, payload: dict, timeout: int = 30) -> dict:
    body = json.dumps(payload)
    headers = {"sign": sign(body), "Content-Type": "application/json"}
    resp = requests.post(url, data=body.encode(), headers=headers, timeout=timeout)
    return resp.json()

def create_task(ext_data: dict) -> int:
    payload = {"ext": json.dumps(ext_data), "taskType": 74, "priority": 0, "retry_times": 1, "cool_time": 600}
    body = signed_post(f"{DEV_BASE_URL}/Video/CreateUniversalTransparent", payload)
    if body.get("code") != 200:
        raise RuntimeError(f"创建失败: {body}")
    return body["data"]

def get_task_status(task_id: int) -> dict:
    body = signed_post(f"{DEV_BASE_URL}/Task/GetAllTaskStatus", {"taskType": 74, "taskIds": [task_id]})
    if body.get("code") != 200:
        raise RuntimeError(f"查询失败: {body}")
    lst = body.get("data", [])
    return lst[0] if lst else {}

def poll_and_download(task_id: int, label: str) -> dict:
    start = time.time()
    deadline = start + POLL_TIMEOUT
    result = None
    while time.time() < deadline:
        info = get_task_status(task_id)
        if not info:
            time.sleep(POLL_INTERVAL)
            continue
        status = info.get("taskStatus")
        elapsed = int(time.time() - start)
        if elapsed % 15 < POLL_INTERVAL:
            print(f"  [{label}] [{elapsed}s] status={status}")
        if status == 2:
            result = info
            break
        elif status == 3:
            print(f"  [{label}] 失败: {info.get('comment', '')}")
            break
        time.sleep(POLL_INTERVAL)
    
    elapsed = time.time() - start
    if not result:
        print(f"  [{label}] 超时/失败")
        return {'label': label, 'taskId': task_id, 'ok': False, 'elapsed': elapsed}
    
    data_str = result.get("data", "{}")
    data = json.loads(data_str) if isinstance(data_str, str) else data_str
    audio_url = data.get("audio_url", "")
    meta_url = data.get("metadata_url", "")
    mp3_size = 0
    subs = 0

    if audio_url:
        r = requests.get(audio_url, timeout=120)
        (OUT / f"{label}.mp3").write_bytes(r.content)
        mp3_size = len(r.content)
    if meta_url:
        r = requests.get(meta_url, timeout=120)
        (OUT / f"{label}.json").write_bytes(r.content)
        segs = json.loads(r.text)
        lines = []
        for s in segs:
            idx = s.get("id", 0) + 1
            sm, em = s.get("startMs", 0), s.get("endMs", 0)
            t = s.get("text", "").strip()
            if not t: continue
            def fms(ms):
                h=ms//3600000; m=(ms%3600000)//60000; sec=(ms%60000)//1000
                return f'{h:02d}:{m:02d}:{sec:02d},{ms%1000:03d}'
            lines.append(str(idx)); lines.append(f'{fms(sm)} --> {fms(em)}')
            lines.append(t); lines.append('')
        (OUT / f"{label}.srt").write_text('\n'.join(lines), encoding='utf-8')
        subs = len([l for l in lines if l and l[0].isdigit()])
    
    print(f"  [{label}] 完成! {elapsed:.1f}s, mp3={mp3_size:,}B, subs={subs}")
    return {'label': label, 'taskId': task_id, 'ok': True, 'elapsed': elapsed, 'mp3_size': mp3_size, 'subs': subs}

def main():
    configs = [
        ('20000 Leagues Under the Sea - 德语.txt',           r'KAPITEL\s+[IVXLCDM]+',   1, 'German_female',    '德语'),
        ('20000 Leagues Under the Sea - 俄语.txt',           r'ГЛАВА\s+[IVXLCDM]+',    1, 'Russian_female',   '俄语'),
        ('20000 Leagues Under the Sea - Spanish(西语).txt',   r'CAP[IÍ]TULO\s+[IVXLCDM]+', 4, 'Spanish_female', '西语'),
        ('20000 Leagues Under the Sea - Portuguese(葡语).txt', r'CAP[IÍ]TULO\s+[IVXLCDM]+', 5, 'Portuguese_female', '葡语'),
        ('20000 Leagues Under the Sea - French(法语).txt',    r'CHAPITRE\s+[IVXLCDM]+', 6, 'French_female',   '法语'),
    ]

    tasks = []
    for fname, pat, lang, voice, cn_name in configs:
        text = (TXT / fname).read_text(encoding='utf-8')
        matches = list(re.finditer(pat, text))
        m = matches[1]  # 统一取第II章（索引1）
        title = m.group().strip()
        start = m.end()
        end = matches[2].start() if len(matches) > 2 else len(text)
        content = text[start:end].strip()
        label = f'{cn_name}_第{title.split()[-1]}章'
        tasks.append((title, content, lang, voice, label))
        print(f"[准备] {label} ({len(content)} 字符)")

    print(f"\n创建 {len(tasks)} 个任务...")
    task_infos = []
    for title, content, lang, voice, label in tasks:
        task_id = create_task({
            "read_content": content, "chapter_title": title,
            "model": "higgs", "lang": lang, "voice": voice,
        })
        task_infos.append((task_id, label, len(content)))
        print(f"  [{label}] taskId={task_id}")

    print(f"\n并发轮询 {len(task_infos)} 个任务...")
    print("=" * 60)
    
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(poll_and_download, tid, label): label for tid, label, _ in task_infos}
        for future in as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda x: x['label'])
    chars_map = {label: chars for _, label, chars in task_infos}

    print(f"\n{'='*60}")
    print("汇总：同一本书第II章，各语言生成耗时对比")
    print(f"{'='*60}")
    print(f"{'语言':22s} {'taskId':>8s} {'字符':>6s} {'耗时':>8s} {'mp3大小':>10s} {'字幕':>5s}")
    print("-" * 65)
    for r in results:
        label = r['label']
        tid = str(r['taskId'])
        chars = chars_map.get(label, 0)
        if r['ok']:
            print(f"{label:22s} {tid:>8s} {chars:>6,} {r['elapsed']:>7.1f}s {r['mp3_size']:>10,} {r['subs']:>5}")
        else:
            print(f"{label:22s} {tid:>8s} {chars:>6,} {r['elapsed']:>7.1f}s {'FAIL':>10s}")

    ok_results = [r for r in results if r['ok']]
    if ok_results:
        print(f"\n耗时排名（从快到慢）：")
        for i, r in enumerate(sorted(ok_results, key=lambda x: x['elapsed'])):
            print(f"  {i+1}. {r['label']}: {r['elapsed']:.1f}s")

if __name__ == "__main__":
    main()
