# -*- coding: utf-8 -*-
r"""获取海阅（AdAssetServer）Bearer Token —— token 约 10 小时过期，需定期重取。

原理：用 Playwright 打开 sc-test.changdu.ltd（Keycloak 工号登录），
      切换到目标环境并触发一次 adassetserver 请求，从请求头抓取 Authorization: Bearer。

凭据来源（按优先级，**不写入源码**）：
  1) 环境变量  HAIYUE_USER / HAIYUE_PWD
  2) 本技能目录下 .secrets.json  {"user":"...","password":"..."}
     （从 .secrets.example.json 复制；已被 .gitignore 忽略，不入库）

用法:
    python get_token.py                        # 默认 env=test1
    python get_token.py --env dev
    python get_token.py --out D:\python\dmx\cdtest\temp_token_prod.txt
    python get_token.py --verify-only --token-file <path>

退出码: 0 成功 / 1 失败
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()

SKILL_DIR = Path(__file__).resolve().parent.parent
SECRETS = SKILL_DIR / ".secrets.json"
BASE = "https://sc-test.changdu.ltd"
DEFAULT_OUT = Path(r"D:\python\dmx\cdtest\temp_token_prod.txt")

# 环境名 -> 触发环境切换时 UI 上的文案
ENVS = ("dev", "test1", "test5", "cd-2")


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_creds() -> tuple[str, str]:
    user = os.environ.get("HAIYUE_USER")
    pwd = os.environ.get("HAIYUE_PWD")
    if user and pwd:
        return user, pwd
    if SECRETS.is_file():
        d = json.loads(SECRETS.read_text(encoding="utf-8"))
        user, pwd = d.get("user"), d.get("password")
        if user and pwd:
            return user, pwd
    raise SystemExit(
        "未找到凭据。请设置环境变量 HAIYUE_USER / HAIYUE_PWD，\n"
        f"或复制 .secrets.example.json 为 {SECRETS.name} 并填入 user/password。"
    )


def token_exp(token: str):
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload)).get("exp")
    except Exception:
        return None


def report(token: str, out: Path | None) -> int:
    exp = token_exp(token)
    if exp is None:
        log(f"token 长度 {len(token)}，无法解析 exp")
    else:
        left = (exp - time.time()) / 3600.0
        log(f"token 长度 {len(token)}，剩余 {left:.2f} 小时（exp={exp}）")
        if left <= 0:
            log("❌ token 已过期")
            return 1
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(token, encoding="utf-8")
        log(f"已写入 {out}")
    return 0


def fetch_token(env: str, user: str, pwd: str, headless: bool) -> str | None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit("缺少 playwright：& \"D:\\python\\python.exe\" -m pip install playwright && playwright install msedge")

    caught: dict[str, str] = {}

    def on_req(req):
        if "adassetserver-" in req.url:
            auth = req.headers.get("authorization", "")
            if auth.startswith("Bearer ") and len(auth[7:]) > 500:
                caught["v"] = auth[7:]
                log(f"已捕获 token（来源 {req.url.split('/api/')[0]}，长度 {len(auth[7:])}）")

    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=headless,
                              args=["--disable-password-manager"])
        ctx = b.new_context(viewport={"width": 1920, "height": 1080})
        page = ctx.new_page()
        page.set_default_timeout(60000)
        page.on("request", on_req)

        log(f"打开 {BASE}")
        page.goto(BASE + "/automation/create-make-material", wait_until="domcontentloaded")
        try:
            page.get_by_text("工号登录", exact=False).first.wait_for(state="visible", timeout=8000)
            page.get_by_text("工号登录", exact=False).first.click()
        except Exception:
            pass
        page.wait_for_timeout(1500)

        if page.locator("#username").count():
            log("Keycloak 登录中")
            page.fill("#username", user)
            page.fill("#password", pwd)
            page.click("#kc-login")
            try:
                page.wait_for_url(lambda u: "keycloak" not in u and "login-test" not in u, timeout=30000)
            except Exception:
                pass
        page.wait_for_timeout(3000)

        # 切换环境（UI 上是 一级菜单 dev -> 二级菜单 <env>）
        try:
            page.goto(BASE + "/home", wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            page.get_by_text("dev", exact=True).click()
            page.wait_for_timeout(600)
            page.get_by_text(env, exact=True).first.click()
            page.wait_for_timeout(2000)
            log(f"已切换到环境 {env}")
        except Exception as e:
            log(f"⚠️ 环境切换未完成（{type(e).__name__}），继续尝试抓取")

        # 触发一次 adassetserver 请求
        try:
            page.goto(BASE + "/task/list", wait_until="domcontentloaded")
            page.wait_for_timeout(5000)
            page.reload()
            page.wait_for_timeout(5000)
        except Exception:
            pass
        b.close()

    return caught.get("v")


def verify(token: str, base: str) -> bool:
    try:
        r = requests.post(f"{base}/api/Common/GetTgtCodeInfo",
                          headers={"Authorization": "Bearer " + token,
                                   "Content-Type": "application/json",
                                   "Referer": "https://sc-test.changdu.ltd/",
                                   "User-Agent": "Mozilla/5.0"},
                          json={"tgtType": 1}, timeout=20, verify=False)
        ok = r.status_code == 200 and '"code":200' in r.text.replace(" ", "")
        log(f"校验 {base} -> HTTP {r.status_code} {'✅ 可用' if ok else '⚠️ 响应异常：' + r.text[:160]}")
        return ok
    except Exception as e:
        log(f"校验 {base} 失败：{type(e).__name__}: {e}")
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="获取海阅 Bearer Token")
    ap.add_argument("--env", choices=ENVS, default="test1", help="目标环境（默认 test1）")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"token 输出文件（默认 {DEFAULT_OUT}）")
    ap.add_argument("--headless", action="store_true", help="无头模式（默认有头，便于人工过验证码）")
    ap.add_argument("--verify-only", action="store_true", help="只校验已有 token，不重新获取")
    ap.add_argument("--token-file", type=Path, help="配合 --verify-only 指定 token 文件")
    ap.add_argument("--base", default="https://adassetserver-cn-new-test1.changdu.ltd",
                    help="校验用的接口基址")
    a = ap.parse_args()

    if a.verify_only:
        f = a.token_file or a.out
        if not f.is_file():
            raise SystemExit(f"token 文件不存在：{f}")
        token = f.read_text(encoding="utf-8").strip()
        rc = report(token, None)
        verify(token, a.base)
        return rc

    user, pwd = load_creds()
    log(f"账号 {user} | 环境 {a.env} | 有头模式 {not a.headless}")
    token = fetch_token(a.env, user, pwd, a.headless)
    if not token:
        log("❌ 未捕获到 token。可能原因：登录失败 / 验证码 / 环境切换未完成。")
        return 1
    rc = report(token, a.out)
    verify(token, a.base)
    return rc


if __name__ == "__main__":
    sys.exit(main())
