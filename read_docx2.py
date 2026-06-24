import zipfile, re

path = r'D:\python\dmx\cdtest\docs\需求文档\雷霆系统海剧新增TT小程序需求.docx'
with zipfile.ZipFile(path) as z:
    with z.open('word/document.xml') as f:
        content = f.read().decode('utf-8')
        text = re.sub(r'<[^>]+>', ' ', content)
        text = re.sub(r'\s+', ' ', text).strip()
        print(text[:30000])
