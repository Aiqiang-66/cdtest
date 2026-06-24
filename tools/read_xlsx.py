import zipfile, xml.etree.ElementTree as ET

xlsx_path = r'd:\python\dmx\cdtest\docs\IDP\个人发展计划（IDP.xlsx'
with zipfile.ZipFile(xlsx_path, 'r') as z:
    # 读取共享字符串
    with z.open('xl/sharedStrings.xml') as f:
        tree = ET.parse(f)
        root = tree.getroot()
        ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        strings = []
        for si in root.findall('.//ns:si', ns):
            text = ''.join(t.text or '' for t in si.findall('.//ns:t', ns))
            strings.append(text)
    
    # 读取sheet1
    with z.open('xl/worksheets/sheet1.xml') as f:
        tree = ET.parse(f)
        root = tree.getroot()
        for row in root.findall('.//ns:row', ns):
            cells = []
            for c in row.findall('ns:c', ns):
                ref = c.get('r')
                t = c.get('t')
                v = c.find('ns:v', ns)
                val = v.text if v is not None else ''
                if t == 's' and val:
                    idx = int(val)
                    val = strings[idx] if idx < len(strings) else val
                cells.append(f'{ref}={val[:100]}')
            print(f'Row {row.get("r")}: | '.join(cells))
            print('---')
