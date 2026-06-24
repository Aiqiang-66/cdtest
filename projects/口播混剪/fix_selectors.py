import re
path = r'D:\python\dmx\cdtest\projects\口播混剪\run_p0_file.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换 el-select 为 ant-select 相关
content = content.replace('.el-select-dropdown', '.ant-select-dropdown')
content = content.replace('.el-select-dropdown__item', '.ant-select-item-option')
content = content.replace('.is-disabled', '.ant-select-item-option-disabled')
content = content.replace('.el-select__input', '.ant-select-selection-search-input')
content = content.replace("未找到 el-select", "未找到 ant-select")
content = content.replace("无el-select", "无ant-select")
content = content.replace('popperClass', 'placeholder')

# 去掉emoji
content = content.replace('\u274c', 'X')  # ❌
content = content.replace('\u2714', '+')  # ✔
content = content.replace('\u26a0', '!')  # ⚠
content = content.replace('\ud83d\udccb', '[>]')  # 📋
content = content.replace('\ud83d\udca1', '[!]')  # 💡

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('替换完成')
