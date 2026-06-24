path = r'D:\python\dmx\cdtest\projects\口播混剪\run_p0_file.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# .el-select 但还没被替换的
content = content.replace(".el-select'", ".ant-select'")
content = content.replace('.el-select ', '.ant-select ')
content = content.replace(".el-select.", ".ant-select.")

# 混选: ant-select-dropdown__item 应该改为 ant-select-item-option
content = content.replace('.ant-select-dropdown__item', '.ant-select-item-option')

print('Done')
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
