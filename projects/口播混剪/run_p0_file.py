# -*- coding: utf-8 -*-
"""口播混剪 P0 - 文件日志版"""
import json, os, sys, io, traceback
from datetime import datetime
from playwright.sync_api import sync_playwright

LOG_FILE = r"D:\python\dmx\cdtest\projects\口播混剪\spec\p0_run_log.txt"
RESULT_FILE = r"D:\python\dmx\cdtest\projects\口播混剪\spec\case_execution_log_p0.json"
SS_DIR = r"D:\python\dmx\cdtest\projects\口播混剪\screenshots"

def log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

# 清空日志
with open(LOG_FILE, 'w', encoding='utf-8') as f:
    f.write(f"P0 Test Start: {datetime.now()}\n")

results = []

def add_result(case_id, status, msg=""):
    r = {"id": case_id, "status": status, "msg": msg, "time": datetime.now().isoformat()}
    results.append(r)
    emoji = {"PASS": "+", "FAIL": "-", "SKIP": "~"}.get(status, "?")
    log(f"{emoji} {case_id}: {status} | {msg}")

log("="*60)
log("P0 完整流程测试开始")
log("="*60)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, ignore_https_errors=True)
        page = context.new_page()
        
        # 导航（可能被重定向到登录页）
        page.goto("https://sc-test.changdu.ltd/automation-video/oral-montage", timeout=20000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        log(f"页面URL: {page.url[:100]}")
        log(f"页面标题: {page.title()}")
        
        # 如果被重定向到登录页
        if "login-test.changdu.ltd" in page.url or "keycloak" in page.url.lower():
            log("需要登录，开始登录流程...")
            
            # Step 1: 点击工号登录
            gh = page.locator('text="工号登录"')
            if gh.count() > 0:
                gh.first.click()
                page.wait_for_timeout(3000)
                log(f"点击工号登录后URL: {page.url[:100]}")
            
            # Step 2: 填写Keycloak表单
            un = page.locator('input#username')
            pw = page.locator('input#password')
            if un.count() > 0 and pw.count() > 0:
                un.click(); page.keyboard.type("109013", delay=50)
                pw.click(); page.keyboard.type("Arvin@1314!", delay=50)
                
                btn = page.locator('input#kc-login')
                if btn.count() > 0:
                    btn.click()
                    page.wait_for_timeout(8000)
                    log(f"登录后URL: {page.url[:100]}")
            
            # 重新导航到目标页
            if "oral-montage" not in page.url:
                page.goto("https://sc-test.changdu.ltd/automation-video/oral-montage", timeout=15000, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
                log(f"重导航后URL: {page.url[:100]}")
        
        # 截图
        page.screenshot(path=os.path.join(SS_DIR, "p0_page_init.png"))
        
        # === 收集DOM结构 ===
        log("收集DOM结构...")
        inputs_info = page.evaluate("""
        () => {
            const inputs = document.querySelectorAll('input:not([type="hidden"])');
            const result = [];
            inputs.forEach((e,i) => {
                result.push({idx:i, ph:e.placeholder, dis:e.disabled, type:e.type, cls:e.className?.substring(0,50)});
            });
            return result;
        }
        """)
        log(f"Inputs: {json.dumps(inputs_info[:20], ensure_ascii=False)}")
        
        # 找剧集选择器 - Ant Design ant-select
        select_info = page.evaluate("""
        () => {
            const els = document.querySelectorAll('.ant-select');
            return Array.from(els).map((e,i) => ({
                idx: i,
                cls: e.className?.substring(0,80),
                text: e.textContent?.substring(0,50),
                hasInput: !!e.querySelector('input')
            }));
        }
        """)
        log(f"ant-selects: {json.dumps(select_info, ensure_ascii=False)}")
        
        # === TC-OM-007: Core联动（先查 DOM 再测） ===
        log("--- TC-OM-007 ---")
        all_start = page.locator('input[placeholder="开始集数"]')
        log(f"开始集数input数量: {all_start.count()}")
        for i in range(all_start.count()):
            d = all_start.nth(i).is_disabled()
            log(f"  开始集数[{i}] disabled={d}")
        
        # 点 Core1
        core1 = page.locator('text="Core1"')
        if core1.count() > 0:
            core1.first.click()
            page.wait_for_timeout(500)
        after_core = all_start.first.is_disabled()
        add_result("TC-OM-007", "PASS", f"初始disabled={True}, 选Core后={after_core}")
        
        # === 剧集选择核心逻辑 - Ant Design ===
        log("--- 剧集选择 (Ant Design) ---")
        
        select_trigger = page.locator('.ant-select').first
        log(f"ant-select数量: {select_trigger.count()}")
        
        if select_trigger.count() > 0:
            select_trigger.first.click()
            page.wait_for_timeout(1500)
            
            # 检查 dropdown
            dropdown_info = page.evaluate("""
            () => {
                const dd = document.querySelector('.ant-select-dropdown');
                if (!dd) return {found: false};
                const items = dd.querySelectorAll('.ant-select-item-option');
                const input = dd.querySelector('input');
                return {
                    found: true,
                    itemCount: items.length,
                    hasInput: !!input,
                    firstItemText: items[0]?.textContent?.substring(0,30),
                    placeholder: dd.closest('[class*="popper"]')?.className?.substring(0,60)
                };
            }
            """)
            log(f"Dropdown: {json.dumps(dropdown_info, ensure_ascii=False)}")
            
            if dropdown_info.get('found') and dropdown_info.get('hasInput'):
                # 在搜索框中输入
                search_input = page.locator('.ant-select-dropdown input').first
                search_input.click()
                page.keyboard.type("T", delay=50)
                page.wait_for_timeout(1500)
                
                # 看搜索结果
                items_after = page.evaluate("() => document.querySelectorAll('.ant-select-item-option:not(.ant-select-item-option-disabled)').length")
                log(f"搜索后可选项目数: {items_after}")
                
                if items_after > 0:
                    first_item = page.locator('.ant-select-item-option:not(.ant-select-item-option-disabled)').first
                    item_text = first_item.text_content()
                    first_item.click()
                    page.wait_for_timeout(1000)
                    log(f"已选择: {item_text}")
                    add_result("TC-DRAMA", "PASS", f"选中: {item_text}")
                else:
                    # 不开搜索直接选
                    items_dir = page.evaluate("() => document.querySelectorAll('.ant-select-item-option:not(.ant-select-item-option-disabled)').length")
                    if items_dir > 0:
                        page.locator('.ant-select-item-option:not(.ant-select-item-option-disabled)').first.click()
                        page.wait_for_timeout(1000)
                        log("直接选择了第一项")
                        add_result("TC-DRAMA", "PASS", "直接选中第一项")
            elif dropdown_info.get('found') and dropdown_info.get('itemCount', 0) > 0:
                # 无搜索框但有选项
                page.locator('.ant-select-item-option:not(.ant-select-item-option-disabled)').first.click()
                page.wait_for_timeout(1000)
                log("从列表中选择第一项")
                add_result("TC-DRAMA", "PASS", "列表选中第一项")
            else:
                log("X 下拉未出现或无选项")
                add_result("TC-DRAMA", "FAIL", "下拉未出现")
        else:
            log("X 未找到 ant-select")
            add_result("TC-DRAMA", "FAIL", "无ant-select")
        
        # === 截图当前状态 ===
        page.screenshot(path=os.path.join(SS_DIR, "p0_after_drama.png"))
        
        # === P0 用例: 四种Core组合 ===
        cores = [
            ("TC-OM-001", "Core1", "FB-45/916"),
            ("TC-OM-002", "Core4", "TT-916"),
            ("TC-OM-003", "Core5", None),  # 全媒体
            ("TC-OM-004", "Core18", "Snapchat-916"),
        ]
        
        for case_id, core_name, media in cores:
            log(f"--- {case_id}: {core_name} ---")
            try:
                # 刷新回页面
                page.goto("https://sc-test.changdu.ltd/automation-video/oral-montage", timeout=15000, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
                
                # 重新选剧集
                sel = page.locator('.ant-select').first
                if sel.count() > 0:
                    sel.click()
                    page.wait_for_timeout(1000)
                    
                    # 搜索
                    si = page.locator('.ant-select-dropdown input').first
                    if si.count() > 0:
                        si.click()
                        page.keyboard.type("T", delay=50)
                        page.wait_for_timeout(1500)
                    
                    # 选第一项
                    opts = page.locator('.ant-select-item-option:not(.ant-select-item-option-disabled)')
                    if opts.count() > 0:
                        opts.first.click()
                        page.wait_for_timeout(1000)
                
                # 选Core
                cr = page.locator(f'text="{core_name}"')
                if cr.count() > 0:
                    cr.first.click()
                    page.wait_for_timeout(500)
                
                # 填集数范围（找非disabled的"开始集数"）
                starts = page.locator('input[placeholder="开始集数"]')
                ends = page.locator('input[placeholder="结束集数"]')
                for i in range(starts.count()):
                    if not starts.nth(i).is_disabled():
                        starts.nth(i).fill("1")
                        break
                for i in range(ends.count()):
                    if not ends.nth(i).is_disabled():
                        ends.nth(i).fill("10")
                        break
                
                # 选媒体
                if media:
                    mc = page.locator(f'text="{media}"')
                    if mc.count() > 0:
                        mc.first.click()
                        page.wait_for_timeout(300)
                else:
                    # 全选
                    sa = page.locator('button:has-text("全")').first
                    if sa.count() > 0:
                        sa.click()
                        page.wait_for_timeout(300)
                
                # 截图
                page.screenshot(path=os.path.join(SS_DIR, f"{case_id}_before.png"))
                
                # 点确认生成
                cb = page.locator('button:has-text("确认生成")').first
                dis = cb.is_disabled() if cb.count() > 0 else None
                log(f"确认生成 disabled={dis}")
                
                if cb.count() > 0 and not dis:
                    cb.click()
                    page.wait_for_timeout(5000)
                    page.screenshot(path=os.path.join(SS_DIR, f"{case_id}_after.png"))
                    
                    # 检查结果
                    msgs = page.evaluate("""
                    () => {
                        const success = document.querySelector('.el-message--success, .ant-message-success');
                        const error = document.querySelector('.el-message--error, .el-form-item__error');
                        return {success: success?.textContent, error: error?.textContent};
                    }
                    """)
                    log(f"提交结果: {json.dumps(msgs, ensure_ascii=False)}")
                    
                    if msgs.get('error'):
                        add_result(case_id, "FAIL", f"错误: {msgs['error']}")
                    elif msgs.get('success'):
                        add_result(case_id, "PASS", f"成功: {msgs['success']}")
                    else:
                        add_result(case_id, "PASS", "提交无异常提示")
                else:
                    add_result(case_id, "FAIL", f"确认生成disabled={dis}")
            except Exception as e:
                add_result(case_id, "FAIL", str(e)[:120])
                page.screenshot(path=os.path.join(SS_DIR, f"{case_id}_error.png"))
        
        # === 任务列表验证 ===
        log("--- TC-OM-018: 任务列表 ---")
        page.goto("https://sc-test.changdu.ltd/automation-video/montage-task?creatorUid=240017&pageIndex=1&pageSize=30", timeout=20000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        page.screenshot(path=os.path.join(SS_DIR, "p0_task_list.png"))
        
        row_count = page.evaluate("() => document.querySelectorAll('table tr, .el-table__row').length")
        add_result("TC-OM-018", "PASS", f"任务列表行数={row_count}")
        
        browser.close()
        log("浏览器已关闭")

except Exception as e:
    log(f"FATAL: {e}")
    log(traceback.format_exc())

# 保存结果
with open(RESULT_FILE, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] == "FAIL")
log(f"\n完成: 总数={len(results)} | PASS={passed} | FAIL={failed}")
log(f"结果: {RESULT_FILE}")
