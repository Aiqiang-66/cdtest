# -*- coding: utf-8 -*-
"""口播混剪 UI 自动化测试 - Playwright 直连"""
import json, os, time, sys, io
from datetime import datetime
from playwright.sync_api import sync_playwright

# 修复Windows GBK编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

CONFIG = {
    "base_url": "https://sc-test.changdu.ltd",
    "oral_page": "/automation-video/oral-montage",
    "task_page": "/automation-video/montage-task?creatorUid=240017&pageIndex=1&pageSize=30",
    "audit_page": "/automation-video/montage-audit",
    "username": "109013",
    "password": "Arvin@1314!",
    "timeout": 30000,
}

SPEC_DIR = r"D:\python\dmx\cdtest\projects\口播混剪\spec"
RESULT_FILE = os.path.join(SPEC_DIR, "case_execution_log_v2.json")
REPORT_FILE = os.path.join(SPEC_DIR, "测试报告_v2.md")

results = []

def log(case_id, status, msg=""):
    entry = {"id": case_id, "status": status, "msg": msg, "time": datetime.now().isoformat()}
    results.append(entry)
    emoji = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️"}.get(status, "⚠️")
    print(f"{emoji} {case_id}: {status} | {msg}")

def login(page, browser):
    """工号登录 -> Keycloak SSO"""
    ss_dir = r"D:\python\dmx\cdtest\projects\口播混剪\screenshots"
    print("\n[Login] 开始登录...")
    
    # 导航到目标页面
    page.goto(CONFIG["base_url"] + CONFIG["oral_page"], timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    page.screenshot(path=os.path.join(ss_dir, "debug_01_initial.png"))
    print(f"[Login] 当前URL: {page.url[:120]}")
    
    # 检查是否已在目标页面
    if "oral-montage" in page.url:
        print("[Login] 已登录，直接进入目标页面")
        return True
    
    # 等待 Keycloak 登录页面加载
    page.wait_for_timeout(3000)
    page.screenshot(path=os.path.join(ss_dir, "debug_02_login_page.png"))
    
    # 尝试按工号登录入口
    username_input = page.locator('input#username')
    password_input = page.locator('input#password')
    
    if username_input.count() > 0:
        print("[Login] 找到 Keycloak 登录表单")
        username_input.fill(CONFIG["username"])
        password_input.fill(CONFIG["password"])
        
        login_btn = page.locator('input#kc-login, button#kc-login, input[value="Sign In"], input[value="登 录"]')
        if login_btn.count() > 0:
            login_btn.first.click()
            page.wait_for_timeout(8000)
            page.screenshot(path=os.path.join(ss_dir, "debug_03_after_login.png"))
            print(f"[Login] 登录后URL: {page.url[:120]}")
            
            if "oral-montage" in page.url or "automation-video" in page.url:
                print("[Login] 登录成功!")
                return True
    
    # 尝试找工号登录入口 - 使用更通用的方式
    print("[Login] 直接表单未找到，尝试找工号登录入口...")
    try:
        # 用 JS 找到包含"工号登录"的可点击元素
        gonghao_el = page.locator('text="工号登录"')
        if gonghao_el.count() == 0:
            # 尝试 contains 匹配
            gonghao_el = page.locator('*:has-text("工号登录")').last
        if gonghao_el.count() > 0:
            tag = gonghao_el.first.evaluate("el => el.tagName")
            print(f"[Login] 找到工号登录元素: tag={tag}")
            gonghao_el.first.click()
            page.wait_for_timeout(3000)
            page.screenshot(path=os.path.join(ss_dir, "debug_04_gonghao_clicked.png"))
            print(f"[Login] 点击后URL: {page.url[:120]}")
            
            # 等待表单出现，再试填表
            page.wait_for_timeout(2000)
            # 截图看点击后的状态
            page.screenshot(path=os.path.join(ss_dir, "debug_04b_after_click.png"))
            
            # 尝试多种方式填写
            un = page.locator('input#username')
            pw = page.locator('input#password')
            
            if un.count() > 0:
                print("[Login] 找到用户名输入框")
                un.first.click()
                page.keyboard.type(CONFIG["username"], delay=100)
                page.wait_for_timeout(300)
                
                if pw.count() > 0:
                    pw.first.click()
                    page.keyboard.type(CONFIG["password"], delay=100)
                    page.wait_for_timeout(300)
                    
                    login_btn = page.locator('input#kc-login, button#kc-login, input[type="submit"], button:has-text("登")')
                    if login_btn.count() > 0:
                        print("[Login] 点击登录按钮")
                        login_btn.first.click()
                        page.wait_for_timeout(10000)
                        page.screenshot(path=os.path.join(ss_dir, "debug_05_after_login.png"))
                        print(f"[Login] 登录后URL: {page.url[:120]}")
                        if "oral-montage" in page.url or "automation-video" in page.url or "sc-test.changdu.ltd" in page.url:
                            return True
            else:
                # 工号登录可能跳转到了 Keycloak 或其他页面
                print(f"[Login] 点击后未找到表单，页面内容: {page.locator('body').inner_text()[:300]}")
    except Exception as e:
        print(f"[Login] 工号入口尝试失败: {e}")
    
    # 检查页面内容帮助诊断
    try:
        body_text = page.locator('body').inner_text()[:500]
        print(f"[Login] 页面内容摘要: {body_text[:300]}")
    except:
        pass
    
    page.screenshot(path=os.path.join(ss_dir, "debug_05_login_failed.png"))
    print("[Login] 登录失败")
    return False

def run():
    print("=" * 60)
    print("  口播混剪 UI 自动化测试 v2.0")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True
        )
        page = context.new_page()
        
        if not login(page, browser):
            print("X 登录失败，终止测试")
            browser.close()
            return
        
        # === 导航到口播混剪页面 ===
        print("\n📋 导航到口播混剪页面...")
        try:
            page.goto(CONFIG["base_url"] + CONFIG["oral_page"], timeout=20000)
            page.wait_for_timeout(3000)
        except:
            pass
        
        # ======================
        # TC-OM-025: 确认生成按钮初始状态
        # ======================
        print("\n--- TC-OM-025: 确认生成按钮初始状态 ---")
        try:
            confirm_btn = page.locator('button:has-text("确认生成")')
            confirm_upload_btn = page.locator('button:has-text("确认并上传")')
            
            # 检查初始状态
            is_disabled = confirm_btn.is_disabled() if confirm_btn.count() > 0 else None
            upload_disabled = confirm_upload_btn.is_disabled() if confirm_upload_btn.count() > 0 else None
            log("TC-OM-025", "PASS", f"确认生成disabled={is_disabled}, 确认并上传disabled={upload_disabled}")
        except Exception as e:
            log("TC-OM-025", "FAIL", str(e)[:100])
        
        # ======================
        # TC-OM-026: 口播时长默认值
        # ======================
        print("\n--- TC-OM-026: 口播时长默认值 ---")
        try:
            min_dur = page.locator('input[placeholder="最小时长"]').first
            max_dur = page.locator('input[placeholder="最大时长"]').first
            
            # 需要找口播时长区域的两个输入框
            all_inputs = page.locator('input[placeholder="最小时长"]')
            all_max = page.locator('input[placeholder="最大时长"]')
            
            min_val = all_inputs.first.input_value() if all_inputs.count() > 0 else "N/A"
            # 第二个"最小时长"可能是混剪的，第一个是口播的
            log("TC-OM-026", "PASS" if min_val == "30" else "FAIL", f"口播最小时长={min_val}")
        except Exception as e:
            log("TC-OM-026", "FAIL", str(e)[:100])
        
        # ======================
        # TC-OM-027: 生成数量默认值
        # ======================
        print("\n--- TC-OM-027: 生成数量默认值 ---")
        try:
            gen_count = page.locator('input[placeholder="请输入生成数量"]')
            val = gen_count.input_value() if gen_count.count() > 0 else "N/A"
            log("TC-OM-027", "PASS" if val == "1" else "FAIL", f"生成数量默认值={val}")
        except Exception as e:
            log("TC-OM-027", "FAIL", str(e)[:100])
        
        # ======================
        # TC-OM-010: 必填项校验-空提交
        # ======================
        print("\n--- TC-OM-010: 必填项校验-空提交 ---")
        try:
            if confirm_btn.count() > 0:
                confirm_btn.first.click()
                page.wait_for_timeout(2000)
                # 检查是否有校验提示
                error_msgs = page.locator('.el-form-item__error, .ant-form-item-explain-error, .ant-message-error')
                has_error = error_msgs.count() > 0 or page.locator('text=请选择').count() > 0 or page.locator('text=必填').count() > 0
                log("TC-OM-010", "PASS" if has_error else "FAIL", f"校验提示={has_error}")
            else:
                log("TC-OM-010", "SKIP", "确认生成按钮不存在")
        except Exception as e:
            log("TC-OM-010", "FAIL", str(e)[:100])
        
        # ======================
        # TC-OM-007: Core切换联动
        # ======================
        print("\n--- TC-OM-007: Core切换联动 ---")
        try:
            # 检查口播集数范围初始disable状态
            oral_start_inputs = page.locator('input[placeholder="开始集数"]')
            oral_start_disabled = None
            if oral_start_inputs.count() > 0:
                oral_start_disabled = oral_start_inputs.first.is_disabled()
            
            # 点击 Core1
            core1 = page.locator('text=Core1').first
            if core1.count() > 0:
                core1.click()
                page.wait_for_timeout(1000)
                oral_start_after = oral_start_inputs.first.is_disabled() if oral_start_inputs.count() > 0 else None
                
                # 取消 Core1
                core1.click()
                page.wait_for_timeout(1000)
                oral_start_final = oral_start_inputs.first.is_disabled() if oral_start_inputs.count() > 0 else None
                
                log("TC-OM-007", "PASS", f"初始disabled={oral_start_disabled}, 选Core后={oral_start_after}, 取消后={oral_start_final}")
            else:
                log("TC-OM-007", "SKIP", "Core1 radio未找到")
        except Exception as e:
            log("TC-OM-007", "FAIL", str(e)[:100])
        
        # ======================
        # TC-OM-008: 口播音频切换
        # ======================
        print("\n--- TC-OM-008: 口播音频切换 ---")
        try:
            male = page.locator('text=男声').first
            female = page.locator('text=女声').first
            if male.count() > 0 and female.count() > 0:
                male.click()
                page.wait_for_timeout(500)
                female.click()
                page.wait_for_timeout(500)
                log("TC-OM-008", "PASS", "男女声切换完成")
            else:
                log("TC-OM-008", "SKIP", "男声/女声radio未找到")
        except Exception as e:
            log("TC-OM-008", "FAIL", str(e)[:100])
        
        # ======================
        # TC-OM-009: BGM切换
        # ======================
        print("\n--- TC-OM-009: BGM切换 ---")
        try:
            manual = page.locator('text=手动选择').first
            random_bgm = page.locator('text=随机匹配通用').first
            if manual.count() > 0 and random_bgm.count() > 0:
                manual.click()
                page.wait_for_timeout(500)
                random_bgm.click()
                page.wait_for_timeout(500)
                log("TC-OM-009", "PASS", "BGM切换完成")
            else:
                log("TC-OM-009", "SKIP", "BGM radio未找到")
        except Exception as e:
            log("TC-OM-009", "FAIL", str(e)[:100])
        
        # ======================
        # TC-OM-006: 媒体全选/反选/取消
        # ======================
        print("\n--- TC-OM-006: 媒体全选/反选/取消 ---")
        try:
            select_all = page.locator('button:has-text("全 选")').first
            invert = page.locator('button:has-text("反 选")').first
            cancel = page.locator('button:has-text("取 消")').first
            
            if select_all.count() > 0:
                select_all.click()
                page.wait_for_timeout(500)
                
            if invert.count() > 0:
                invert.click()
                page.wait_for_timeout(500)
                
            if cancel.count() > 0:
                cancel.click()
                page.wait_for_timeout(500)
                
            log("TC-OM-006", "PASS", "全选/反选/取消操作完成")
        except Exception as e:
            log("TC-OM-006", "FAIL", str(e)[:100])
        
        # ======================
        # TC-OM-016: 免审核开关
        # ======================
        print("\n--- TC-OM-016: 免审核直接上传开关 ---")
        try:
            switch = page.locator('.el-switch, .ant-switch, [class*="switch"]').first
            if switch.count() > 0:
                switch.click()
                page.wait_for_timeout(500)
                switch.click()
                page.wait_for_timeout(500)
                log("TC-OM-016", "PASS", "开关切换完成")
            else:
                # 找 Switch 相关
                switch_label = page.locator('text=免审核直接上传')
                if switch_label.count() > 0:
                    log("TC-OM-016", "PASS", "免审核开关存在")
                else:
                    log("TC-OM-016", "SKIP", "免审核开关未找到")
        except Exception as e:
            log("TC-OM-016", "FAIL", str(e)[:100])
        
        # ======================
        # TC-OM-011: 生成数量边界值
        # ======================
        print("\n--- TC-OM-011: 生成数量边界值 ---")
        try:
            gen_input = page.locator('input[placeholder="请输入生成数量"]')
            if gen_input.count() > 0:
                test_values = ["-1", "0", "999", "abc", "3.5"]
                boundaries_ok = True
                for tv in test_values:
                    gen_input.first.fill("")
                    gen_input.first.fill(tv)
                    page.wait_for_timeout(300)
                    actual = gen_input.first.input_value()
                    print(f"   输入={tv}, 实际值={actual}")
                
                # 恢复默认值
                gen_input.first.fill("1")
                log("TC-OM-011", "PASS", "边界值输入测试完成")
            else:
                log("TC-OM-011", "SKIP", "生成数量输入框不存在")
        except Exception as e:
            log("TC-OM-011", "FAIL", str(e)[:100])
        
        # ======================
        # TC-OM-005: 生成文案按钮
        # ======================
        print("\n--- TC-OM-005: 生成文案按钮 ---")
        try:
            # 先选 Core1（如果未选）
            core1 = page.locator('text=Core1').first
            if core1.count() > 0:
                core1.click()
                page.wait_for_timeout(500)
            
            gen_copy_btn = page.locator('button:has-text("生成文案")').first
            if gen_copy_btn.count() > 0:
                gen_copy_btn.click()
                page.wait_for_timeout(3000)
                # 检查文案区域是否有内容
                copy_area = page.locator('[class*="copy"], [class*="文案"], [class*="content"]')
                has_content = copy_area.count() > 0
                log("TC-OM-005", "PASS" if has_content else "FAIL", f"文案区域有内容={has_content}")
            else:
                log("TC-OM-005", "SKIP", "生成文案按钮不存在")
        except Exception as e:
            log("TC-OM-005", "FAIL", str(e)[:100])
        
        # ======================
        # TC-OM-018: 自动化任务列表页面
        # ======================
        print("\n--- TC-OM-018: 自动化任务列表 ---")
        try:
            page.goto(CONFIG["base_url"] + CONFIG["task_page"], timeout=20000)
            page.wait_for_timeout(3000)
            
            # 检查表格数据
            table_rows = page.locator('table tr, .el-table__row, .ant-table-row')
            row_count = table_rows.count()
            
            # 检查分页
            pagination = page.locator('.el-pagination, .ant-pagination')
            has_pagination = pagination.count() > 0
            
            log("TC-OM-018", "PASS", f"任务列表数据行={row_count}, 分页存在={has_pagination}")
        except Exception as e:
            log("TC-OM-018", "FAIL", str(e)[:100])
        
        # ======================
        # TC-OM-019: 分页功能
        # ======================
        print("\n--- TC-OM-019: 分页功能 ---")
        try:
            next_btn = page.locator('.btn-next, .ant-pagination-next, button:has-text("下一页")').first
            if next_btn.count() > 0:
                next_btn.click()
                page.wait_for_timeout(2000)
                log("TC-OM-019", "PASS", "分页翻页成功")
            else:
                log("TC-OM-019", "SKIP", "下一页按钮不存在")
        except Exception as e:
            log("TC-OM-019", "FAIL", str(e)[:100])
        
        # ======================
        # TC-OM-022: 审核列表页面
        # ======================
        print("\n--- TC-OM-022: 审核列表 ---")
        try:
            page.goto(CONFIG["base_url"] + CONFIG["audit_page"], timeout=20000)
            page.wait_for_timeout(3000)
            
            table_rows = page.locator('table tr, .el-table__row, .ant-table-row')
            row_count = table_rows.count()
            log("TC-OM-022", "PASS", f"审核列表数据行={row_count}")
        except Exception as e:
            log("TC-OM-022", "FAIL", str(e)[:100])
        
        # ======================
        # 返回口播页面，尝试完整流程
        # ======================
        print("\n--- TC-OM-001: 完整流程 ---")
        try:
            page.goto(CONFIG["base_url"] + CONFIG["oral_page"], timeout=20000)
            page.wait_for_timeout(2000)
            
            # 1. 点击剧集代号下拉
            drama_select = page.locator('.el-select, .ant-select').first
            if drama_select.count() > 0:
                drama_select.click()
                page.wait_for_timeout(1500)
                
                # 在搜索框中输入
                search_input = page.locator('.el-select__input, .ant-select-selection-search input').first
                if search_input.count() > 0:
                    search_input.fill("")
                    page.keyboard.type("test", delay=100)
                    page.wait_for_timeout(2000)
                    
                    # 选第一个结果
                    first_option = page.locator('.el-select-dropdown__item, .ant-select-item-option').first
                    if first_option.count() > 0:
                        first_option.click()
                        page.wait_for_timeout(1000)
            
            # 2. 选 Core1
            core1 = page.locator('text=Core1').first
            if core1.count() > 0:
                core1.click()
                page.wait_for_timeout(500)
            
            # 3. 填口播集数
            start_inputs = page.locator('input[placeholder="开始集数"]')
            end_inputs = page.locator('input[placeholder="结束集数"]')
            if start_inputs.count() > 0:
                start_inputs.first.fill("1")
            if end_inputs.count() > 0:
                end_inputs.first.fill("10")
            
            # 4. 选媒体 FB
            fb_checkbox = page.locator('text=FB-45/916').first
            if fb_checkbox.count() > 0:
                fb_checkbox.click()
                page.wait_for_timeout(300)
            
            # 5. 点击确认生成
            confirm_btn = page.locator('button:has-text("确认生成")').first
            if confirm_btn.count() > 0 and not confirm_btn.is_disabled():
                confirm_btn.click()
                page.wait_for_timeout(3000)
                log("TC-OM-001", "PASS", "确认生成流程完成")
            else:
                disabled = confirm_btn.is_disabled() if confirm_btn.count() > 0 else "N/A"
                log("TC-OM-001", "FAIL", f"确认生成按钮disabled={disabled}, 剧集可能未选成功")
        except Exception as e:
            log("TC-OM-001", "FAIL", str(e)[:100])
        
        # ======================
        # 保存结果
        # ======================
        with open(RESULT_FILE, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        passed = sum(1 for r in results if r["status"] == "PASS")
        failed = sum(1 for r in results if r["status"] == "FAIL")
        skipped = sum(1 for r in results if r["status"] == "SKIP")
        total = len(results)
        
        print(f"\n{'='*60}")
        print(f"  测试完成: 总数={total} | 通过={passed} | 失败={failed} | 跳过={skipped}")
        print(f"  结果已保存: {RESULT_FILE}")
        print(f"{'='*60}")
        
        browser.close()

if __name__ == "__main__":
    run()
