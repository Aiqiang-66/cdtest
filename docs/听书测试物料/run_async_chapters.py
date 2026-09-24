import os
"""
整章发送（异步任务队列版）：德语5章 + 俄语5章，共10个任务，文件名中文标注。
基于 test_redis_send 的任务队列模式。
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

# ── 配置 ──
DEV_BASE_URL = "https://ai-main-none-dev.changdu.ltd"
SECRET_KEY = os.environ["TTS_SECRET_KEY"]
OUT = Path(r'd:\python\dmx\cdtest\docs\需求文档\听书测试物料\mp3')
TXT = Path(r'd:\python\dmx\cdtest\docs\需求文档\听书测试物料\txt文本')
POLL_INTERVAL = 10
POLL_TIMEOUT = 1200  # 20分钟

# ── 签名 ──
def sign(text: str) -> str:
    h = hmac.new(SECRET_KEY.encode(), text.encode(), hashlib.sha256)
    return base64.b64encode(h.digest()).decode()

def signed_post(url: str, payload: dict, timeout: int = 30) -> dict:
    body = json.dumps(payload)
    headers = {"sign": sign(body), "Content-Type": "application/json"}
    resp = requests.post(url, data=body.encode(), headers=headers, timeout=timeout)
    return resp.json()

# ── 创建任务 ──
def create_task(ext_data: dict) -> int:
    payload = {"ext": json.dumps(ext_data), "taskType": 74, "priority": 0, "retry_times": 1, "cool_time": 600}
    url = f"{DEV_BASE_URL}/Video/CreateUniversalTransparent"
    body = signed_post(url, payload)
    if body.get("code") != 200:
        raise RuntimeError(f"创建失败: {body}")
    return body["data"]

# ── 查询状态 ──
def get_task_status(task_id: int) -> dict:
    url = f"{DEV_BASE_URL}/Task/GetAllTaskStatus"
    body = signed_post(url, {"taskType": 74, "taskIds": [task_id]})
    if body.get("code") != 200:
        raise RuntimeError(f"查询失败: {body}")
    lst = body.get("data", [])
    return lst[0] if lst else {}

# ── 轮询等待 ──
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
        if status == 2:  # 成功
            return info
        elif status == 3:  # 失败
            print(f"  [{label}] 失败: {info.get('comment', '')}")
            return None
        time.sleep(POLL_INTERVAL)
    print(f"  [{label}] 超时")
    return None

# ── 下载文件 ──
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

# ── 处理单个章节 ──
def process_chapter(title: str, content: str, lang: int, voice: str, label: str):
    print(f"\n[{label}] 创建任务 ({len(content)} 字符, ~{len(content.split())} 词)")
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
    configs = [
        ('20000 Leagues Under the Sea - 德语.txt', r'KAPITEL\s+[IVXLCDM]+', 1, 'German_female', '德语'),
        ('20000 Leagues Under the Sea - 俄语.txt', r'ГЛАВА\s+[IVXLCDM]+', 1, 'Russian_female', '俄语'),
    ]

    all_tasks = []
    for fname, pat, lang, voice, cn_name in configs:
        text = (TXT / fname).read_text(encoding='utf-8')
        matches = list(re.finditer(pat, text))
        for i, m in enumerate(matches):
            title = m.group().strip()
            start = m.end()
            end = matches[i+1].start() if i+1 < len(matches) else len(text)
            content = text[start:end].strip()
            ch_num = title.split()[-1]
            label = f'{cn_name}_第{ch_num}章'
            all_tasks.append((title, content, lang, voice, label))

    print(f"共 {len(all_tasks)} 个任务")
    print("=" * 50)

    success = 0
    for title, content, lang, voice, label in all_tasks:
        if process_chapter(title, content, lang, voice, label):
            success += 1

    print(f"\n{'='*50}")
    print(f"完成: {success}/{len(all_tasks)} 成功")

if __name__ == "__main__":
    main()
