import os
"""
随机下发5个任务：德语/俄语/西语/葡语/法语各一个完整章节
异步任务队列模式（taskType=74）
"""
import hashlib, hmac, base64, json, time, re, requests, random
from pathlib import Path

import os

_TTS_KEY = os.environ.get("TTS_SECRET_KEY")
if not _TTS_KEY:
    raise SystemExit(
        "缺少环境变量 TTS_SECRET_KEY（测试环境密钥，请勿写入代码；设置后重试，例如：\n"
        "  在 PowerShell 里先设置环境变量 TTS_SECRET_KEY（值由项目统一管理）后再运行")

# ── 配置 ──
DEV_BASE_URL = "https://ai-main-none-dev.changdu.ltd"
SECRET_KEY = os.environ["TTS_SECRET_KEY"]
TXT = Path(r'd:\python\dmx\cdtest\docs\听书测试物料\txt文本')
OUT = Path(r'd:\python\dmx\cdtest\docs\听书测试物料\mp3')
POLL_INTERVAL = 10
POLL_TIMEOUT = 1200

# ── 签名 ──
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
    url = f"{DEV_BASE_URL}/Video/CreateUniversalTransparent"
    body = signed_post(url, payload)
    if body.get("code") != 200:
        raise RuntimeError(f"创建失败: {body}")
    return body["data"]

def get_task_status(task_id: int) -> dict:
    url = f"{DEV_BASE_URL}/Task/GetAllTaskStatus"
    body = signed_post(url, {"taskType": 74, "taskIds": [task_id]})
    if body.get("code") != 200:
        raise RuntimeError(f"查询失败: {body}")
    lst = body.get("data", [])
    return lst[0] if lst else {}

def poll_task(task_id: int, label: str) -> dict | None:
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        info = get_task_status(task_id)
        if not info:
            time.sleep(POLL_INTERVAL)
            continue
        status = info.get("taskStatus")
        elapsed = int(time.time() - deadline + POLL_TIMEOUT)
        print(f"  [{label}] [{elapsed}s] status={status}")
        if status == 2:
            return info
        elif status == 3:
            print(f"  [{label}] 失败: {info.get('comment', '')}")
            return None
        time.sleep(POLL_INTERVAL)
    print(f"  [{label}] 超时")
    return None

def download_files(result: dict, label: str):
    data_str = result.get("data", "{}")
    data = json.loads(data_str) if isinstance(data_str, str) else data_str
    audio_url = data.get("audio_url", "")
    meta_url = data.get("metadata_url", "")

    if audio_url:
        r = requests.get(audio_url, timeout=120)
        (OUT / f"{label}.mp3").write_bytes(r.content)
        print(f"  [OK] {label}.mp3 ({len(r.content)} bytes)")

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
        print(f"  [OK] {label}.srt ({len([l for l in lines if l and l[0].isdigit()])} 条)")

def process_chapter(title: str, content: str, lang: int, voice: str, label: str):
    print(f"\n[{label}] 创建任务 ({len(content)} 字符)")
    try:
        task_id = create_task({
            "read_content": content,
            "chapter_title": title,
            "model": "higgs",
            "lang": lang,
            "voice": voice,
        })
        print(f"  taskId={task_id}")
        result = poll_task(task_id, label)
        if result:
            download_files(result, label)
            return True
    except Exception as e:
        print(f"  [{label}] 异常: {e}")
    return False

# ── 主流程 ──
def main():
    # 5种语言配置：文件名、章节正则、lang、voice、中文名
    configs = [
        ('20000 Leagues Under the Sea - 德语.txt',    r'KAPITEL\s+[IVXLCDM]+',   1, 'German_female',    '德语'),
        ('20000 Leagues Under the Sea - 俄语.txt',    r'ГЛАВА\s+[IVXLCDM]+',    1, 'Russian_female',   '俄语'),
        ('20000 Leagues Under the Sea - Spanish(西语).txt', r'CAP[IÍ]TULO\s+[IVXLCDM]+', 4, 'Spanish_female', '西语'),
        ('20000 Leagues Under the Sea - Portuguese(葡语).txt', r'CAP[IÍ]TULO\s+[IVXLCDM]+', 5, 'Portuguese_female', '葡语'),
        ('20000 Leagues Under the Sea - French(法语).txt', r'CHAPITRE\s+[IVXLCDM]+', 6, 'French_female', '法语'),
    ]

    tasks = []
    for fname, pat, lang, voice, cn_name in configs:
        text = (TXT / fname).read_text(encoding='utf-8')
        matches = list(re.finditer(pat, text))
        # 随机选一个章节
        i = random.randint(0, len(matches) - 1)
        m = matches[i]
        title = m.group().strip()
        start = m.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        content = text[start:end].strip()
        ch_num = title.split()[-1]
        label = f'{cn_name}_第{ch_num}章'
        tasks.append((title, content, lang, voice, label))
        print(f"[选择] {cn_name}: {title} ({len(content)} 字符)")

    print(f"\n共 {len(tasks)} 个任务，开始下发...")
    print("=" * 50)

    success = 0
    for title, content, lang, voice, label in tasks:
        if process_chapter(title, content, lang, voice, label):
            success += 1

    print(f"\n{'='*50}")
    print(f"完成: {success}/{len(tasks)} 成功")

if __name__ == "__main__":
    random.seed(time.time())
    main()
