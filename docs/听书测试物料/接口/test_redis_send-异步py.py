"""
操作任务队列的函数库，可独立调用每个步骤。

用法:
    from tests.test_redis_send import create_task, get_task_status, get_task_result, poll_task

    task_id = create_task(base_url="https://ai-main-none.changdu.vip")
    status = get_task_status(task_id)
    result = get_task_result(task_id)
"""

import hashlib
import hmac
import base64
import json
import os
import time
from typing import Optional

import requests

# ── 默认配置 ────────────────────────────────────────────────────
PROD_BASE_URL = "https://ai-main-none.changdu.vip"
DEV_BASE_URL = "https://ai-main-none-dev.changdu.ltd"
# 密钥**只从环境变量读取**：调用接口前先设置，例如 PowerShell：
#   $env:TTS_SECRET_KEY = '<测试环境密钥>'
# 不要写进代码/文档/仓库（SKILL.md 工程规范 §1）
SECRET_KEY = os.environ.get("TTS_SECRET_KEY")


def _require_key() -> str:
    """调用接口前必须已设置 TTS_SECRET_KEY（纯本地 import 本模块不需要）。"""
    if not SECRET_KEY:
        raise SystemExit("缺少环境变量 TTS_SECRET_KEY：调用接口前请先设置（PowerShell: "
                         "$env:TTS_SECRET_KEY = '<key>'）")
    return SECRET_KEY

# ── 默认测试数据 ────────────────────────────────────────────────
DEFAULT_EXT_DATA = {
    "read_content": "Hello world. This is a test for F5 TTS synthesis.",
    "chapter_title": "Chapter 1",
    "model": "higgs",
    "lang": 3,
    "voice": "audiobook_female_2",
    "speed": 1.0,
    "volume": 1.0,
    "cos_path": "",
}

DEFAULT_PAYLOAD = {
    "ext": json.dumps(DEFAULT_EXT_DATA),
    "taskType": 74,
    "priority": 0,
    "retry_times": 1,
    "cool_time": 600,
}


# ═════════════════════════════════════════════════════════════════
#  签名 & 请求
# ═════════════════════════════════════════════════════════════════

def sign(text: str) -> str:
    """HMAC-SHA256 → Base64"""
    body_bytes = text.encode("utf-8")
    key_bytes = _require_key().encode("utf-8")
    h = hmac.new(key_bytes, digestmod=hashlib.sha256)
    h.update(body_bytes)
    return base64.b64encode(h.digest()).decode()


def signed_post(url: str, payload: dict, timeout: int = 30) -> requests.Response:
    """带签名的 POST 请求"""
    body = json.dumps(payload)
    headers = {"sign": sign(body), "Content-Type": "application/json"}
    return requests.post(url, data=body.encode("utf-8"), headers=headers, timeout=timeout)


# ═════════════════════════════════════════════════════════════════
#  Step 1: 创建任务
# ═════════════════════════════════════════════════════════════════

def create_task(
    ext_data: Optional[dict] = None,
    priority: int = 0,
    retry_times: int = 1,
    cool_time: int = 600,
    base_url: str = PROD_BASE_URL,
) -> int:
    """创建 TTS 任务并返回 taskId。

    Args:
        ext_data: TTSRequest 参数，为 None 时用默认测试数据
        priority: 优先级，0=普通（走 UniversalTransparent_74），1=优先（走 :High）
        retry_times: 失败重试次数
        cool_time: 冷却时间（秒）
        base_url: API 根地址

    Returns:
        task_id (int)

    Raises:
        RuntimeError: 接口返回 code != 200
    """
    if ext_data is None:
        ext_data = DEFAULT_EXT_DATA

    payload = {
        "ext": json.dumps(ext_data),
        "taskType": 74,
        "priority": priority,
        "retry_times": retry_times,
        "cool_time": cool_time,
    }

    url = f"{base_url}/Video/CreateUniversalTransparent"
    print(f"[create_task] POST {url}")
    print(f"[create_task] ext: {json.dumps(ext_data, ensure_ascii=False)}")

    resp = signed_post(url, payload)
    body = resp.json()

    if body.get("code") != 200:
        raise RuntimeError(f"创建任务失败: code={body.get('code')}, msg={body.get('msg')}")

    task_id = body["data"]
    print(f"[create_task] ✅ taskId = {task_id}")
    return task_id


# ═════════════════════════════════════════════════════════════════
#  Step 2: 查询状态（单次）
# ═════════════════════════════════════════════════════════════════

def get_task_status(
    task_id: int,
    base_url: str = PROD_BASE_URL,
) -> dict:
    """单次查询任务状态。

    Args:
        task_id: 任务 ID
        base_url: API 根地址

    Returns:
        任务信息 dict，包含 taskStatus、progress、comment 等字段。
        未查到数据时返回空 dict。

    Raises:
        RuntimeError: 接口返回 code != 200
    """
    url = f"{base_url}/Task/GetAllTaskStatus"  # 跟 redis_main.py 保持一致
    payload = {"taskType": 74, "taskIds": [task_id]}

    resp = signed_post(url, payload)
    body = resp.json()

    if body.get("code") != 200:
        raise RuntimeError(f"查询状态失败: code={body.get('code')}, msg={body.get('msg')}")

    task_list = body.get("data", [])
    if task_list:
        return task_list[0]
    return {}


# ═════════════════════════════════════════════════════════════════
#  Step 3: 等待完成
# ═════════════════════════════════════════════════════════════════

# 注意：下面是 **redis_main.py 内部**用的状态码；而**接口查询返回的 `taskStatus`** 是：
#   2 = 成功（带 audio_url / metadata_url） · 3 = 失败 · 67 = 处理中
# 判定口径以 `01_规范与用例\SKILL.md`（本仓库为 docs\听书测试物料\SKILL.md）为准——不要混用两套状态码。
STATUS_PENDING = 0       # 排队中（内部）
STATUS_PROCESSING = 1    # 处理中（内部）
STATUS_SUCCESS = 2       # 完成
STATUS_FAILED = 3        # 失败

# taskStatus=-1 / 2 / 3 会被 redis_main.py xack 跳过（第 125 行）


def poll_task(
    task_id: int,
    poll_interval: float = 5.0,
    poll_timeout: float = 600.0,
    base_url: str = PROD_BASE_URL,
    on_status = None,
) -> dict:
    """轮询直到任务完成或失败。

    Args:
        task_id: 任务 ID
        poll_interval: 轮询间隔（秒）
        poll_timeout: 最大等待时间（秒）
        base_url: API 根地址
        on_status: 可选回调，每次查询时调用 on_status(status, progress)

    Returns:
        最终的任务信息 dict

    Raises:
        TimeoutError: 超过 poll_timeout 仍为完成
    """
    deadline = time.time() + poll_timeout

    while time.time() < deadline:
        try:
            info = get_task_status(task_id, base_url=base_url)
        except RuntimeError as e:
            print(f"[poll_task] 查询出错: {e}，继续等待...")
            time.sleep(poll_interval)
            continue

        if not info:
            print(f"[poll_task] 返回数据为空，继续等待...")
            time.sleep(poll_interval)
            continue

        status = info.get("taskStatus")
        progress = info.get("progress", "—")
        elapsed = int(time.time() - deadline + poll_timeout)

        print(f"[poll_task] [{elapsed}s] taskStatus={status}, progress={progress}")

        if on_status:
            on_status(status, progress)

        if status == STATUS_SUCCESS:
            print(f"[poll_task] ✅ 任务完成")
            return info
        elif status == STATUS_FAILED:
            print(f"[poll_task] ❌ 任务失败: {info.get('comment', '无错误信息')}")
            return info

        time.sleep(poll_interval)

    raise TimeoutError(f"超时：已等待 {poll_timeout}s，任务仍未完成")


# ═════════════════════════════════════════════════════════════════
#  Step 4: 获取结果（创建 + 等待完成）
# ═════════════════════════════════════════════════════════════════

def get_task_result(
    ext_data: Optional[dict] = None,
    priority: int = 0,
    poll_interval: float = 5.0,
    poll_timeout: float = 600.0,
    base_url: str = PROD_BASE_URL,
) -> dict:
    """创建任务并等待完成，一步到位。

    Args:
        ext_data: TTSRequest 参数，为 None 时用默认测试数据
        priority: 优先级
        poll_interval: 轮询间隔（秒）
        poll_timeout: 最大等待时间（秒）
        base_url: API 根地址

    Returns:
        最终的任务信息 dict
    """
    task_id = create_task(ext_data=ext_data, priority=priority, base_url=base_url)
    return poll_task(task_id, poll_interval=poll_interval, poll_timeout=poll_timeout, base_url=base_url)


# ═════════════════════════════════════════════════════════════════
#  main — 快速验证
# ═════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  一键测试：创建任务 → 轮询结果")
    print("=" * 60)

    try:
        result = get_task_result(priority=0, base_url=DEV_BASE_URL)  # 0=普通队列, 1=优先队列
        print(f"\n最终结果:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
    except TimeoutError as e:
        print(f"\n⏰ {e}")
    except RuntimeError as e:
        print(f"\n❌ {e}")

    # res = get_task_status(640874,DEV_BASE_URL)
    # print(res)

if __name__ == "__main__":
    main()
